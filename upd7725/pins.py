from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Sequence

    from .registers import Registers, Status

WIDE = 16

NARROW = 8

WORD_MASK = 0xFFFF

TOP_BIT = 15


def serial_width(narrow: bool) -> int:
    return NARROW if narrow else WIDE


def reversed_bits(word: int, width: int) -> int:
    turned = 0
    for place in range(width):
        turned |= (word >> place & 1) << (width - 1 - place)
    return word & ~((1 << width) - 1) & WORD_MASK | turned


def queued(word: int, width: int, msb_first: bool) -> int:
    kept = word & (1 << width) - 1
    ordered = kept if msb_first else reversed_bits(kept, width)
    return ordered << (WIDE - width)


class Pins:
    __slots__ = (
        "_seen",
        "bits_in",
        "bits_out",
        "drq",
        "msb_first",
        "sck",
        "shifting_in",
        "shifting_out",
        "si",
        "sien",
        "so",
        "soen",
        "sorq",
    )

    def __init__(self) -> None:
        self.sck = False
        self.si = 0
        self.sien = True
        self.soen = True
        self.so: int | None = None
        self.sorq = False
        self.drq = False
        self.msb_first = True
        self.shifting_in = 0
        self.bits_in = 0
        self.shifting_out = 0
        self.bits_out = 0
        self._seen = False

    def power_on(self, undefined: Sequence[int]) -> None:
        self.shifting_in = undefined[0] & WORD_MASK
        self.bits_in = undefined[1] % WIDE
        self.shifting_out = undefined[2] & WORD_MASK
        self.bits_out = undefined[3] % (WIDE + 1)

    def sample(self, registers: Registers) -> None:
        level = self.sck
        if level == self._seen:
            return
        self._seen = level
        if level:
            self._rising(registers)
        else:
            self._falling(registers.sr, registers.so)

    def _rising(self, registers: Registers) -> None:
        status = registers.sr
        self.sorq = status.soack or self.bits_out > 0
        if not self.sien:
            self._take(registers, status)

    def _take(self, registers: Registers, status: Status) -> None:
        width = serial_width(status.sic)
        self.shifting_in = (self.shifting_in << 1 | self.si & 1) & WORD_MASK
        self.bits_in += 1
        if self.bits_in < width:
            return
        registers.si = self.shifting_in & (1 << width) - 1
        status.siack = True
        self.bits_in = 0

    def _falling(self, status: Status, word: int) -> None:
        if self.soen or (self.bits_out == 0 and not status.soack):
            self.so = None
            return
        if self.bits_out == 0:
            width = serial_width(status.soc)
            self.shifting_out = queued(word, width, self.msb_first)
            self.bits_out = width
            status.soack = False
        self.so = self.shifting_out >> TOP_BIT & 1
        self.shifting_out = self.shifting_out << 1 & WORD_MASK
        self.bits_out -= 1
