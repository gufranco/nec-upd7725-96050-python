"""Look at this machine and say what is actually here, so a report can be believed.

This package runs somebody else's program on a processor. That means almost
everything that goes wrong with it is one of two things: the processor is fine
and the image is not the one it was supposed to be, or there is no image at all.
Both look identical from outside, and neither is visible in a traceback.

So this looks, and prints what it found in a form that can be pasted into an
issue as it stands.

The digest of every image present is the line that matters most. Two people
running the same part and getting different answers are almost always running
different files, and the whole point of publishing digests is that the question
can be settled in one glance instead of a round trip.

Two rules shape the rest. Nothing is hidden: a check that fails says what it saw,
and a check that itself throws is caught and reported as what it threw, named by
type, because a report that says everything is well on a machine where something
is not is worse than no report. And nothing is inferred: every line is something
looked at just now rather than something that ought to be true.
"""

import platform
import sys
from pathlib import Path

from . import firmware, models
from .version import VERSION

OLDEST_PYTHON = (3, 12)


class Finding:
    """One thing that was looked at, and what was there."""

    def __init__(self, name, ok, detail, advice=None):
        self.name = name
        self.ok = ok
        self.detail = detail
        self.advice = advice

    @property
    def line(self):
        """The one-line form, which is what a reader scans."""
        return f"  {'ok  ' if self.ok else '   !'}  {self.name}: {self.detail}"

    @property
    def report(self):
        """The same, with what to do about it when there is something to do."""
        if self.ok or not self.advice:
            return self.line
        return f"{self.line}\n         {self.advice}"

    def __repr__(self):
        return f"<Finding {self.name} {'ok' if self.ok else 'not ok'}>"


def _python():
    return Finding(
        "python",
        sys.version_info[:2] >= OLDEST_PYTHON,
        f"{platform.python_version()} on {platform.system()} {platform.machine()}",
        f"this package needs {OLDEST_PYTHON[0]}.{OLDEST_PYTHON[1]} or newer",
    )


def _package():
    return Finding("upd7725", True, f"version {VERSION}")


def _default_build(name):
    return models.describe(name).build()


def _processor(name, build):
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
    described = models.describe(name)
    return Finding(
        name,
        True,
        f"{described.program_words} program words, {described.table_words} table,"
        f" {described.scratch_words} scratch, starts at word {core.registers.pc}",
    )


def _where():
    return Finding(
        "looking in",
        True,
        ", ".join(str(one) for one in firmware.directories()),
        None,
    )


def _declared():
    held = firmware.manifest()["artifacts"]
    return Finding(
        "declared", bool(held), f"{len(held)} images: " + ", ".join(one["part"] for one in held)
    )


def _images(search):
    """Every image on this machine, each with the digest that identifies it."""
    try:
        found = list(search())
    except Exception as trouble:
        return [
            Finding(
                "images",
                False,
                f"{type(trouble).__name__}: {trouble}",
                "the search itself failed rather than finding nothing; the line above"
                " is what it said",
            )
        ]
    if not found:
        return [
            Finding(
                "images",
                True,
                "no images are here, which is the normal state of a fresh checkout",
                None,
            )
        ]
    lines = [Finding("images", True, f"{len(found)} present")]
    for identity, path in sorted(found, key=lambda one: one[0].part):
        digest = _digest_of(path)
        lines.append(
            Finding(
                f"image {identity.part}",
                True,
                f"{identity.processor}, {Path(path).name}, sha256 {digest}",
            )
        )
    return lines


def _digest_of(path):
    """The digest of the file that is here, which is what settles a report."""
    import hashlib

    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError as trouble:
        return f"could not be read: {trouble}"


def examine(build=_default_build, search=firmware.search):
    """Everything worth looking at on this machine, in the order a reader wants it."""
    found = [_python(), _package()]
    found.extend(_processor(name, build) for name in sorted(models.MODELS))
    found.append(_where())
    found.append(_declared())
    found.extend(_images(search))
    return found


def report(found):
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


def main(argv=(), examine=examine, say=print):
    found = examine()
    for line in report(found):
        say(line)
    return 1 if any(not one.ok for one in found) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
