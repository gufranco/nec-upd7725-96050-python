"""The two addresses the console sees, and the handshake across them.

This is the whole of what a Super Nintendo can observe of this part. One address
is a data register and the other is a status word, and the only thing the console
learns about the program running inside is one bit: whether the part is waiting
for it.

The handshake is the awkward part and the reason this is its own module. The data
register is a word wide but the console is a byte wide, so a transfer is two
accesses, and which half comes next is state the part holds rather than something
the console can see. A model that ignores that reads the same byte twice and gets
a plausible wrong answer instead of an error.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Iterable

    from .core import Core

DATA = 0

STATUS = 1

DEFAULT_LIMIT = 200000


class NeverReady(Exception):
    pass


class Console:
    """The console's side of the two registers, and the waiting between them."""

    def __init__(self, chip: Core) -> None:
        self.chip = chip

    @property
    def asking(self) -> bool:
        """Whether the part is waiting for the console rather than working."""
        return bool(self.chip.registers.sr.rqm)

    def settle(self, limit: int = DEFAULT_LIMIT) -> int:
        """Run until the part asks for attention, and say how long that took."""
        for step in range(limit):
            if self.asking:
                return step
            self.chip.step()
        raise NeverReady(f"the part did not ask for attention within {limit} instructions")

    def read(self, address: int) -> int:
        if address == STATUS:
            return int(self.chip.registers.sr) >> 8
        if address == DATA:
            return self._read_data()
        return 0

    def write(self, address: int, value: int) -> None:
        if address == DATA:
            self._write_data(value & 0xFF)

    def _read_data(self) -> int:
        registers = self.chip.registers
        status = registers.sr

        if status.drc:
            status.rqm = False
            return registers.dr & 0xFF
        if not status.drs:
            status.drs = True
            return registers.dr & 0xFF

        status.rqm = False
        status.drs = False
        return registers.dr >> 8 & 0xFF

    def _write_data(self, value: int) -> None:
        registers = self.chip.registers
        status = registers.sr

        if status.drc:
            status.rqm = False
            registers.dr = registers.dr & 0xFF00 | value
            return
        if not status.drs:
            status.drs = True
            registers.dr = registers.dr & 0xFF00 | value
            return

        status.rqm = False
        status.drs = False
        registers.dr = value << 8 | registers.dr & 0x00FF

    def send_bytes(self, values: Iterable[int], limit: int = DEFAULT_LIMIT) -> None:
        """Hand the part one byte at a time, waiting for it to ask for each."""
        for value in values:
            self.settle(limit)
            self.write(DATA, value)

    def take_bytes(self, count: int, limit: int = DEFAULT_LIMIT) -> bytes:
        """Take that many bytes back, waiting for the part to offer each."""
        found = []
        for _ in range(count):
            self.settle(limit)
            found.append(self.read(DATA))
        return bytes(found)

    def send(self, word: int, limit: int = DEFAULT_LIMIT) -> None:
        """One word, low half first, which is the order the part expects."""
        self.send_bytes((word & 0xFF, word >> 8 & 0xFF), limit)

    def take(self, limit: int = DEFAULT_LIMIT) -> int:
        """One word, put back together from the two halves."""
        low, high = self.take_bytes(2, limit)
        return high << 8 | low
