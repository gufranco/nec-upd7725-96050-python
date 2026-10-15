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

ACCUMULATORS = ("a", "b")

POINTER_STEPS = ("dpnop", "dpinc", "dpdec", "dpclr")

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

FORMS = {OPERATE: "op", JUMP: "jp", LOAD: "ld", RETURN: "rt"}


class Instruction:
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
    for step, word in enumerate(words):
        yield decode(word, address + step)
