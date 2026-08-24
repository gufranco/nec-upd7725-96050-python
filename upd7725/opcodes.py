"""Reading an instruction word without a processor to run it in.

A program for this part is a list of twenty-four bit words with no operands
between them, so anything that can name the fields of one word can read a whole
store. That is worth having separately from the core: a reader looking at a
program they did not write wants to know what it does before deciding to run it,
and running it changes state they may care about.

Every name here is the one the core uses, taken from the same constants, so a
disassembly and an execution cannot disagree about what a field means. The core
decides what a field does; this decides what to call it, and there is exactly one
place each answer lives.

Four forms share the top two bits. An operate word moves one value and may
compute with it; a jump word carries a condition and a target; a load word
carries sixteen bits of immediate and where to put them; a return word carries
nothing at all. The manufacturer's own field order is kept, so a reader with the
data sheet open sees the same names in the same order.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from .core import (
    FORM_SHIFT,
    JUMP,
    LOAD,
    OPERATE,
    RETURN,
)

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Iterator, Sequence

WORD_BITS = 24

ALU = (
    "nop",
    "or",
    "and",
    "xor",
    "sub",
    "add",
    "sbb",
    "adc",
    "dec",
    "inc",
    "cmp",
    "shr1",
    "shl1",
    "shl2",
    "shl4",
    "xchg",
)
"""The sixteen operations, in the order the field encodes them."""

SOURCES = (
    "trb",
    "a",
    "b",
    "tr",
    "dp",
    "rp",
    "table",
    "sgn",
    "drnf",
    "dr",
    "sr",
    "sim",
    "sil",
    "k",
    "l",
    "scratch",
)
"""Where a move reads from, by the value of the source field."""

DESTINATIONS = (
    "none",
    "a",
    "b",
    "tr",
    "dp",
    "rp",
    "dr",
    "sr",
    "sol",
    "som",
    "k",
    "klr",
    "klm",
    "l",
    "trb",
    "scratch",
)
"""Where a move writes to, by the value of the destination field."""

ACCUMULATORS = ("a", "b")
"""Which accumulator an operate word computes into, from its one bit."""

POINTER_STEPS = ("dpnop", "dpinc", "dpdec", "dpclr")
"""What the scratch pointer's low half does, by the two-bit field."""

CONDITIONS = {
    0x000: "jmpso",
    0x080: "jnca",
    0x082: "jca",
    0x084: "jncb",
    0x086: "jcb",
    0x088: "jnza",
    0x08A: "jza",
    0x08C: "jnzb",
    0x08E: "jzb",
    0x090: "jnova0",
    0x092: "jova0",
    0x094: "jnovb0",
    0x096: "jovb0",
    0x098: "jnova1",
    0x09A: "jova1",
    0x09C: "jnovb1",
    0x09E: "jovb1",
    0x0A0: "jnsa0",
    0x0A2: "jsa0",
    0x0A4: "jnsb0",
    0x0A6: "jsb0",
    0x0A8: "jnsa1",
    0x0AA: "jsa1",
    0x0AC: "jnsb1",
    0x0AE: "jsb1",
    0x0B0: "jdplz",
    0x0B1: "jdplnz",
    0x0B2: "jdplf",
    0x0B3: "jdplnf",
    0x0B4: "jnsiak",
    0x0B6: "jsiak",
    0x0B8: "jnsoak",
    0x0BA: "jsoak",
    0x0BC: "jnrqm",
    0x0BE: "jrqm",
    0x100: "jmp",
    0x101: "jmp",
    0x140: "call",
    0x141: "call",
}
"""The branch field, by the value the core dispatches on.

`jmp` and `call` appear twice because the low bit of those two selects which half
of the program store the target lands in, which the target itself already shows.
"""

FORMS = {OPERATE: "op", JUMP: "jp", LOAD: "ld", RETURN: "rt"}


class Instruction:
    """One decoded word, and where it was found."""

    __slots__ = ("address", "raw", "text")

    def __init__(self, address: int, raw: int, text: str) -> None:
        self.address = address
        self.raw = raw
        self.text = text

    @override
    def __repr__(self) -> str:
        return f"<Instruction {self.address:04X} {self.text}>"


def _operate(word: int) -> str:
    pselect = word >> 20 & 0x3
    alu = word >> 16 & 0xF
    asl = word >> 15 & 0x1
    dpl = word >> 13 & 0x3
    dphm = word >> 9 & 0xF
    rpdcr = word >> 8 & 0x1
    source = word >> 4 & 0xF
    destination = word & 0xF

    said = [ALU[alu]]
    if alu:
        said.append(ACCUMULATORS[asl])
        said.append(("ram", "idb", "m", "n")[pselect])
    said.append(f"{SOURCES[source]}->{DESTINATIONS[destination]}")
    if dpl:
        said.append(POINTER_STEPS[dpl])
    if dphm:
        said.append(f"dphm{dphm:X}")
    if rpdcr:
        said.append("rpdec")
    return " ".join(said)


def _jump(word: int) -> str:
    branch = word >> 13 & 0x1FF
    address = word >> 2 & 0x7FF
    bank = word & 0x3
    named = CONDITIONS.get(branch)
    if named is None:
        return f"jp ?{branch:03X} ${bank << 11 | address:04X}"
    if named == "jmpso":
        return "jmpso"
    return f"{named} ${bank << 11 | address:04X}"


def _load(word: int) -> str:
    return f"ld ${word >> 6 & 0xFFFF:04X},{DESTINATIONS[word & 0xF]}"


def decode(word: int, address: int = 0) -> Instruction:
    """One word, named field by field.

    A word this part cannot execute does not exist: every one of the sixteen
    million is a valid instruction of one of four forms, which is why nothing
    here raises and there is no undefined case to report.
    """
    form = word >> FORM_SHIFT & 0x3
    if form == OPERATE:
        text = _operate(word)
    elif form == RETURN:
        text = "rt"
    elif form == JUMP:
        text = _jump(word)
    else:
        text = _load(word)
    return Instruction(address, word & 0xFFFFFF, text)


def disassemble(words: Sequence[int], address: int = 0) -> Iterator[Instruction]:
    """Every word in order, from that address on.

    Words rather than bytes, because the program store is addressed by word and a
    caller holding an image has already had to decide how three bytes become one.
    """
    for step, word in enumerate(words):
        yield decode(word, address + step)
