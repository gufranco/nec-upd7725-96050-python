"""Run one case through the ported reference and report what it left behind.

This is the other half of the comparison. `instructions.py` runs a case through
the model in `upd7725/`; this runs the same case through `reference.py`, which is
an independent implementation with a different internal shape. Both answer in the
same layout, so a disagreement names the field rather than merely the case.

The layout is not arbitrary. It was fixed by `corpus.json`, recorded from the
original implementation at the commit `pinned.json` names, before either Python
side existed. Every state this file produces is checked against those recordings,
which is what turns the port from a claim into a measurement.
"""

import sys
from collections.abc import Iterable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import instructions
import reference

REVISIONS = (reference.UPD7725, reference.UPD96050)


class Sourced:
    """A store whose untouched words are computed from the seed on first read.

    The reference indexes plain lists, and filling twenty thousand of them to read
    three is the difference between a comparison that runs in a second and one that
    runs in two minutes. This stands in for a list, answers the same way, and
    remembers what was written so the changes can be named without a second sweep.
    """

    def __init__(self, seed: int, base: int, words: int, mask: int) -> None:
        self.seed = seed
        self.base = base
        self.words = words
        self.mask = mask
        self.written: dict[int, int] = {}

    def started(self, at: int) -> int:
        return instructions.word_at(self.seed, self.base + at) & self.mask

    def __len__(self) -> int:
        return self.words

    def __getitem__(self, at: int) -> int:
        held = self.written.get(at)
        return self.started(at) if held is None else held

    def __setitem__(self, at: int, value: int) -> None:
        self.written[at] = value & self.mask

    def changed(self) -> list[tuple[int, int]]:
        return [(at, word) for at, word in sorted(self.written.items()) if word != self.started(at)]


def prepared(seed: int, part: int) -> "reference.Upd96050":
    """A reference processor holding what that seed says it holds."""
    chip = reference.Upd96050(REVISIONS[part])

    chip.programROM = Sourced(seed, instructions.AT_PROGRAM, reference.PROGRAM_WORDS, 0xFFFFFF)
    chip.dataROM = Sourced(seed, instructions.AT_TABLE, reference.DATA_WORDS, 0xFFFF)
    chip.dataRAM = Sourced(seed, instructions.AT_SCRATCH, reference.DATA_WORDS, 0xFFFF)

    for at in range(len(chip.regs.stack)):
        chip.regs.stack[at] = instructions.word_at(seed, instructions.AT_STACK + at) & 0xFFFF

    registers = chip.regs
    for place, name in enumerate(instructions.REGISTER_ORDER):
        value = instructions.word_at(seed, instructions.AT_REGISTERS + place)
        value &= instructions.REGISTER_MASKS.get(name, 0xFFFF)
        if name == "sr":
            registers.sr.assign(value)
        elif name in ("siack", "soack"):
            setattr(registers.sr, name, value)
        elif name == "flags_a":
            chip.flags_a.assign(value)
        elif name == "flags_b":
            chip.flags_b.assign(value)
        elif name in reference.SIGNED_REGISTERS:
            setattr(registers, name, reference.i16(value))
        else:
            setattr(registers, name, value)

    return chip


def answer(seed: int, part: int, opcode: int) -> str:
    """The state the reference is left in after that one instruction."""
    chip = prepared(seed, part)
    chip.programROM[chip.regs.pc] = opcode
    chip.exec()

    scratch = chip.dataRAM
    assert isinstance(scratch, Sourced), "the oracle drives its own scratch, never a plain list"
    changes = scratch.changed()
    slots = changes[: instructions.REPORTED_CHANGES]
    slots += [(0, 0)] * (instructions.REPORTED_CHANGES - len(slots))

    registers = chip.regs
    return "".join(
        (
            f"{registers.pc:04x}",
            f"{registers.rp:04x}",
            f"{registers.dp:04x}",
            f"{registers.sp:01x}",
            f"{registers.si:04x}",
            f"{registers.so:04x}",
            f"{reference.n16(registers.k):04x}",
            f"{reference.n16(registers.l):04x}",
            f"{reference.n16(registers.m):04x}",
            f"{reference.n16(registers.n):04x}",
            f"{reference.n16(registers.a):04x}",
            f"{reference.n16(registers.b):04x}",
            f"{registers.tr:04x}",
            f"{registers.trb:04x}",
            f"{registers.dr:04x}",
            f"{int(registers.sr):04x}",
            f"{int(chip.flags_a):02x}",
            f"{int(chip.flags_b):02x}",
            f"{registers.sr.siack << 1 | registers.sr.soack:01x}",
            "".join(
                f"{registers.stack[at] if at < len(registers.stack) else 0:04x}"
                for at in range(instructions.RECORDED_STACK_SLOTS)
            ),
            f"{min(len(changes), instructions.TOO_MANY_CHANGES):02x}",
            "".join(f"{at:03x}{word:04x}" for at, word in slots),
        )
    )


def answers(cases: Iterable[tuple[int, int, int]]) -> list[str]:
    return [answer(*case) for case in cases]
