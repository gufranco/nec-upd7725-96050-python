from typing import override

WORD = 0x10000

SIGN = 0x8000

STACK_DEPTH = 4

STACK_MASK = STACK_DEPTH - 1

SIGNED = ("k", "l", "m", "n", "a", "b")

UNSIGNED = ("si", "so", "tr", "trb", "dr")

STATUS_PLACES = (
    ("p0", 0),
    ("p1", 1),
    ("ei", 7),
    ("sic", 8),
    ("soc", 9),
    ("drc", 10),
    ("dma", 11),
    ("usf0", 13),
    ("usf1", 14),
    ("rqm", 15),
)

TRANSFER_PLACE = 12

WRITABLE_BY_INSTRUCTION = 0x907C


def signed(word: int) -> int:
    return word - WORD if word & SIGN else word


class Status:
    __slots__ = (
        "dma",
        "drc",
        "drs",
        "ei",
        "p0",
        "p1",
        "rqm",
        "siack",
        "sic",
        "so_reserved",
        "soack",
        "soc",
        "usf0",
        "usf1",
    )

    def __init__(self) -> None:
        self.p0 = False
        self.p1 = False
        self.ei = False
        self.sic = False
        self.soc = False
        self.drc = False
        self.dma = False
        self.usf0 = False
        self.usf1 = False
        self.rqm = False
        self.drs = False
        self.siack = False
        self.soack = False
        self.so_reserved = False

    def assign(self, word: int) -> None:
        self.p0 = bool(word >> 0 & 1)
        self.p1 = bool(word >> 1 & 1)
        self.ei = bool(word >> 7 & 1)
        self.sic = bool(word >> 8 & 1)
        self.soc = bool(word >> 9 & 1)
        self.drc = bool(word >> 10 & 1)
        self.dma = bool(word >> 11 & 1)
        self.usf0 = bool(word >> 13 & 1)
        self.usf1 = bool(word >> 14 & 1)
        self.rqm = bool(word >> 15 & 1)
        self.drs = bool(word >> TRANSFER_PLACE & 1)

    def __int__(self) -> int:
        word = (
            int(self.p0) << 0
            | int(self.p1) << 1
            | int(self.ei) << 7
            | int(self.sic) << 8
            | int(self.soc) << 9
            | int(self.drc) << 10
            | int(self.dma) << 11
            | int(self.usf0) << 13
            | int(self.usf1) << 14
            | int(self.rqm) << 15
        )
        if self.drs and not self.drc:
            word |= 1 << TRANSFER_PLACE
        return word

    @override
    def __repr__(self) -> str:
        held = [name for name, _ in STATUS_PLACES if getattr(self, name)]
        return f"<Status {' '.join(held) if held else 'none'}>"


class Registers:
    __slots__ = (
        "_a",
        "_b",
        "_dp",
        "_k",
        "_l",
        "_m",
        "_n",
        "_pc",
        "_rp",
        "_sp",
        "counter_mask",
        "dr",
        "pointer_mask",
        "si",
        "so",
        "sr",
        "stack",
        "stack_mask",
        "table_mask",
        "tr",
        "trb",
    )

    def __init__(
        self,
        counter_bits: int,
        table_bits: int,
        pointer_bits: int,
        stack_levels: int = STACK_DEPTH,
    ) -> None:
        self.counter_mask = (1 << counter_bits) - 1
        self.table_mask = (1 << table_bits) - 1
        self.pointer_mask = (1 << pointer_bits) - 1
        self.stack_mask = stack_levels - 1
        self.stack = [0] * stack_levels
        self._pc = 0
        self._rp = 0
        self._dp = 0
        self._sp = 0
        self._k = 0
        self._l = 0
        self._m = 0
        self._n = 0
        self._a = 0
        self._b = 0
        self.si = 0
        self.so = 0
        self.tr = 0
        self.trb = 0
        self.dr = 0
        self.sr = Status()

    @property
    def pc(self) -> int:
        return self._pc

    @pc.setter
    def pc(self, value: int) -> None:
        self._pc = value & self.counter_mask

    @property
    def rp(self) -> int:
        return self._rp

    @rp.setter
    def rp(self, value: int) -> None:
        self._rp = value & self.table_mask

    @property
    def dp(self) -> int:
        return self._dp

    @dp.setter
    def dp(self, value: int) -> None:
        self._dp = value & self.pointer_mask

    @property
    def sp(self) -> int:
        return self._sp

    @sp.setter
    def sp(self, value: int) -> None:
        self._sp = value & self.stack_mask

    @property
    def k(self) -> int:
        return self._k

    @k.setter
    def k(self, value: int) -> None:
        self._k = signed(value & 0xFFFF)

    @property
    def l(self) -> int:  # noqa: E743
        return self._l

    @l.setter
    def l(self, value: int) -> None:  # noqa: E743
        self._l = signed(value & 0xFFFF)

    @property
    def m(self) -> int:
        return self._m

    @m.setter
    def m(self, value: int) -> None:
        self._m = signed(value & 0xFFFF)

    @property
    def n(self) -> int:
        return self._n

    @n.setter
    def n(self, value: int) -> None:
        self._n = signed(value & 0xFFFF)

    @property
    def a(self) -> int:
        return self._a

    @a.setter
    def a(self, value: int) -> None:
        self._a = signed(value & 0xFFFF)

    @property
    def b(self) -> int:
        return self._b

    @b.setter
    def b(self, value: int) -> None:
        self._b = signed(value & 0xFFFF)

    def word(self, name: str) -> int:
        found = getattr(self, name)
        if not isinstance(found, int):
            raise AttributeError(name)
        return found & 0xFFFF
