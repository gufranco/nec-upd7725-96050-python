from __future__ import annotations

from typing import TYPE_CHECKING

from .errors import NeverReady

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Iterable

    from .core import Cpu

DATA = 0

STATUS = 1

DEFAULT_LIMIT = 200000


class Host:
    __slots__ = ("chip",)

    def __init__(self, chip: Cpu) -> None:
        self.chip = chip

    @property
    def asking(self) -> bool:
        return bool(self.chip.registers.sr.rqm)

    def settle(self, limit: int = DEFAULT_LIMIT) -> int:
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
            self._complete()
            return registers.dr & 0xFF
        if not status.drs:
            status.drs = True
            return registers.dr & 0xFF

        self._complete()
        status.drs = False
        return registers.dr >> 8 & 0xFF

    def _write_data(self, value: int) -> None:
        registers = self.chip.registers
        status = registers.sr

        if status.drc:
            self._complete()
            registers.dr = registers.dr & 0xFF00 | value
            return
        if not status.drs:
            status.drs = True
            registers.dr = registers.dr & 0xFF00 | value
            return

        self._complete()
        status.drs = False
        registers.dr = value << 8 | registers.dr & 0x00FF

    def _complete(self) -> None:
        self.chip.registers.sr.rqm = False
        self.chip.pins.drq = False

    def send_bytes(self, values: Iterable[int], limit: int = DEFAULT_LIMIT) -> None:
        for value in values:
            self.settle(limit)
            self.write(DATA, value)

    def take_bytes(self, count: int, limit: int = DEFAULT_LIMIT) -> bytes:
        found = []
        for _ in range(count):
            self.settle(limit)
            found.append(self.read(DATA))
        return bytes(found)

    def send(self, word: int, limit: int = DEFAULT_LIMIT) -> None:
        self.send_bytes((word & 0xFF, word >> 8 & 0xFF), limit)

    def take(self, limit: int = DEFAULT_LIMIT) -> int:
        low, high = self.take_bytes(2, limit)
        return high << 8 | low
