"""Look at this machine and say what is actually here, so a report can be believed.

Almost everything that goes wrong with a package like this is the part not being
the one the reporter thinks it is. Two processors share one instruction set here
and differ in how wide their registers and stores are, so a result that looks
wrong is very often the right answer from the other one.

So this looks, and prints what it found in a form that can be pasted into an
issue as it stands.

Two rules shape the rest. Nothing is hidden: a check that fails says what it saw,
and a check that itself throws is caught and reported as what it threw, named by
type, because a report that says everything is well on a machine where something
is not is worse than no report. And nothing is inferred: every line is something
looked at just now rather than something that ought to be true.
"""

from __future__ import annotations

import platform
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, override


def _version(where: Path | None = None) -> str:
    """The package version, read out of the file beside this one.

    Read rather than imported. Importing it would go through the package, and a
    package that will not import is one of the things this exists to report.
    """
    found = re.search(
        r"""VERSION\s*[:=][^"']*["']([^"']+)["']""",
        (where or Path(__file__).resolve().parent / "version.py").read_text(),
    )
    return found.group(1) if found else "unknown"


ROOT = Path(__file__).resolve().parent.parent

VERSION = _version()


if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from upd7725 import models  # noqa: E402

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Callable, Sequence

    from .core import Cpu

OLDEST_PYTHON = (3, 12)


class Finding:
    """One thing that was looked at, and what was there."""

    def __init__(self, name: str, ok: bool, detail: str, advice: str | None = None) -> None:
        self.name = name
        self.ok = ok
        self.detail = detail
        self.advice = advice

    @property
    def line(self) -> str:
        """The one-line form, which is what a reader scans."""
        return f"  {'ok  ' if self.ok else '   !'}  {self.name}: {self.detail}"

    @property
    def report(self) -> str:
        """The same, with what to do about it when there is something to do."""
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
    """The distribution, labelled so it cannot be mistaken for the part.

    This package and one of the parts it models share the name `upd7725`, so
    labelling both with it puts two different things under one word in a report
    somebody else has to read.
    """
    return Finding("package", True, f"upd7725 {VERSION}")


def _default_build(name: str) -> Cpu:
    return models.lookup(name).build()


def _processor(name: str, build: Callable[[str], Cpu]) -> Finding:
    """Whether that processor builds, saying exactly what stopped it if not."""
    try:
        core = build(name)
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
        f" {described.scratch_words} scratch, starts at word {core.registers.pc}",
    )


def examine(
    build: Callable[[str], Cpu] = _default_build,
) -> list[Finding]:
    """Everything worth looking at on this machine, in the order a reader wants it."""
    found = [_python(), _package()]
    found.extend(_processor(name, build) for name in sorted(models.MODELS))
    return found


def report(found: Sequence[Finding]) -> list[str]:
    """The lines a person pastes into an issue."""
    unwell = [one for one in found if not one.ok]
    lines = [f"upd7725 {VERSION} on {platform.python_version()}, {platform.system()}", ""]
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
