from __future__ import annotations

import platform
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, override


def installed_version(where: Path | None = None) -> str:
    found = re.search(
        r"""VERSION\s*[:=][^"']*["']([^"']+)["']""",
        (where or Path(__file__).resolve().parent / "version.py").read_text(),
    )
    return found.group(1) if found else "unknown"


ROOT = Path(__file__).resolve().parent.parent

VERSION = installed_version()


if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from upd7725 import environment, models  # noqa: E402

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Callable, Sequence

    from .core import Cpu

OLDEST_PYTHON = (3, 12)


class Finding:
    def __init__(self, name: str, ok: bool, detail: str, advice: str | None = None) -> None:
        self.name = name
        self.ok = ok
        self.detail = detail
        self.advice = advice

    @property
    def line(self) -> str:
        return f"  {'ok  ' if self.ok else '   !'}  {self.name}: {self.detail}"

    @property
    def report(self) -> str:
        if self.ok or not self.advice:
            return self.line
        return f"{self.line}\n         {self.advice}"

    @override
    def __repr__(self) -> str:
        return f"<Finding {self.name} {'ok' if self.ok else 'not ok'}>"


def _python() -> Finding:
    return Finding(
        "python",
        sys.version_info[:2] >= OLDEST_PYTHON,
        f"{platform.python_version()} on {platform.system()} {platform.machine()}",
        f"this package needs {OLDEST_PYTHON[0]}.{OLDEST_PYTHON[1]} or newer",
    )


def _package() -> Finding:
    return Finding("package", True, f"upd7725 {VERSION}")


def _default_build(name: str) -> Cpu:
    return models.lookup(name).build()


def _processor(name: str, build: Callable[[str], Cpu]) -> Finding:
    try:
        core = build(name)
        core.reset()
    except Exception as trouble:
        return Finding(
            name,
            False,
            f"{type(trouble).__name__}: {trouble}",
            "this is the core failing to build rather than anything to do with an"
            " image; the line above is what it said",
        )
    described = models.lookup(name)
    return Finding(
        name,
        True,
        f"{described.program_words} program words, {described.table_words} table,"
        f" {described.scratch_words} scratch, resets to word {core.registers.pc}",
    )


def examine(
    build: Callable[[str], Cpu] = _default_build,
) -> list[Finding]:
    found = [_python(), _package()]
    found.extend(_processor(name, build) for name in sorted(models.MODELS))
    return found


def report(found: Sequence[Finding]) -> list[str]:
    unwell = [one for one in found if not one.ok]
    lines = [f"upd7725 {VERSION} on {platform.python_version()}, {platform.system()}", ""]
    lines.append("  the machine")
    lines.extend(environment.lines(ROOT))
    lines.append("")
    lines.append("  this package")
    lines.extend(one.report for one in found)
    lines.append("")
    if unwell:
        lines.append(f"  {len(unwell)} of {len(found)} checks did not pass")
    else:
        lines.append(f"  {len(found)} checks, nothing to report")
    return lines


def main(
    argv: Sequence[str] = (),
    examine: Callable[..., Sequence[Finding]] = examine,
    say: Callable[[str], object] = print,
) -> int:
    found = examine()
    for line in report(found):
        say(line)
    return 1 if any(not one.ok for one in found) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
