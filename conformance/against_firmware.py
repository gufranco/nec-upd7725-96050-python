"""Run the parts themselves, from images their owner supplies.

Nothing here is a gate, and it is not meant to be. The gate is
`conformance/instructions.py`, which settles every instruction against recordings
and needs no firmware at all. This is the layer above it: a real program, written
by the people who made the part, exercising sequences nobody would think to
generate.

It is deliberately opt-in and deliberately silent when nothing is there. Point
`UPD7725_FIRMWARE_DIR` at a directory holding images you already own and it runs;
leave it alone and every check reports as skipped, which is the honest state of a
check that cannot run rather than a pass it did not earn.

Usage:
    python3 conformance/against_firmware.py [--instructions N]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from upd7725 import firmware, models, ports

DEFAULT_INSTRUCTIONS = 200000

SETTLE_LIMIT = 100000

COMMANDS = 0x100

REVISION_ARGUMENTS = (
    (
        0xF5,
        0x0F,
        0xA7,
        0xC8,
        0xB6,
        0x81,
        0x83,
        0x51,
        0xC3,
        0xFD,
        0xB8,
        0x41,
        0xB8,
        0x0A,
        0x3C,
        0x19,
    ),
    (
        0x94,
        0x5B,
        0xF7,
        0x2B,
        0xA0,
        0xB2,
        0x94,
        0x68,
        0x07,
        0xFC,
        0x1D,
        0x60,
        0xC4,
        0xFE,
        0x1A,
        0x73,
    ),
)
"""Two argument sets the two masks answer differently on.

Most arguments make the two agree, which is why finding a disagreement needed a
search rather than a guess: whatever the later mask corrected, the earlier one
gets right for the common case. These two were found by sweeping random sets and
kept because they reach the case where it does not.
"""

REVISION_READS = 12

WHY_NOT = (
    "no firmware image was found: this checks the parts themselves, and their"
    " programs belong to whoever wrote them, so a copy you already own goes in the"
    " firmware directory of this repository, in the one beside it when this is a"
    " submodule, or wherever UPD7725_FIRMWARE_DIR points"
)


class Usage(Exception):
    pass


class Options:
    def __init__(self, instructions=DEFAULT_INSTRUCTIONS):
        self.instructions = instructions


def available(where=None):
    """Every image the manifest recognises, wherever it is looked for.

    A directory can be named outright, which is what a test does. Otherwise every
    place in the search path is looked at, so this works the same whether the
    package is checked out on its own or sits inside a project that keeps its own
    images beside it.
    """
    if where is not None:
        return tuple(firmware.found(where))
    return tuple(firmware.search())


def booted(identity, path):
    """A part carrying that image, run until it first waits for the console."""
    chip = models.describe(identity.processor).build(fill=0)
    firmware.load(chip, path.read_bytes(), identity)
    console = ports.Console(chip)
    console.settle(SETTLE_LIMIT)
    return console


def _answer(identity, path, command, arguments, reads=REVISION_READS):
    console = booted(identity, path)
    console.send_bytes([command, *arguments], SETTLE_LIMIT)
    return console.take_bytes(reads, SETTLE_LIMIT)


def compare_revisions(present):
    """Which commands the two masks of the DSP-1 answer differently."""
    by_part = {identity.part: (identity, path) for identity, path in present}
    if not {"dsp1", "dsp1b"} <= set(by_part):
        return {}

    differ = {}
    for arguments in REVISION_ARGUMENTS:
        for command in range(COMMANDS):
            first = _answer(*by_part["dsp1"], command, arguments)
            second = _answer(*by_part["dsp1b"], command, arguments)
            if first != second:
                differ.setdefault(command, (arguments, first, second))
    return differ


def options(argv):
    chosen = Options()
    rest = list(argv)
    while rest:
        item = rest.pop(0)
        if item != "--instructions":
            raise Usage(f"unknown option {item}")
        if not rest:
            raise Usage(f"{item} needs a value")
        chosen.instructions = int(rest.pop(0))
    return chosen


def summary(differ):
    """The closing line, and none at all when there was no pair to compare."""
    if not differ:
        return ()
    return (
        f"  the two masks of the DSP-1 answer differently on {len(differ)} of"
        f" {COMMANDS} command bytes",
    )


def lines_for(present, instructions):
    """One line per image, and whatever the comparison between masks found."""
    if not present:
        return (f"  skipped: {WHY_NOT}",)

    found = []
    for identity, path in present:
        console = booted(identity, path)
        console.chip.run(instructions)
        found.append(
            f"  {identity.part:6s} {identity.revision:7s} on {identity.processor}:"
            f" {instructions:,} instructions, still inside its own program store"
        )

    return (*found, *summary(compare_revisions(present)))


def run(argv, where=None):
    chosen = options(argv)
    print(*lines_for(available(where), chosen.instructions), sep="\n")
    return 0


def main(argv):
    try:
        return run(argv)
    except Usage as error:
        print(error)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
