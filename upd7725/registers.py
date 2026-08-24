"""Everything the processor holds between one instruction and the next.

Three of the registers are narrower on the smaller part than on the larger one,
and the widths are the only difference between the two: the instruction set,
the flags and the status word are identical. So the widths arrive at construction
rather than being written into the arithmetic, and every store masks itself.

Six registers are signed. They are the two accumulators, the two multiplicands
and the two halves of the product, and a model that keeps them unsigned agrees
with the part until the first negative multiply and then stops.
"""

from typing import override

WORD = 0x10000

SIGN = 0x8000

STACK_DEPTH = 4
"""How many return addresses the smaller part holds.

Four, because NEC says four: "The SPI+ contains a four-level program stack for
efficient program usage and interrupt handling", and the block diagram beside it
draws the slots labelled 0 to 3. Every implementation of this family in the field
carries sixteen, which is where this started too, and none of them is the part.

What a fifth consecutive call does is not in the document. A two-bit pointer
wrapping to slot zero is what the width implies, and that is what happens below,
but it is an inference from the width rather than a figure anybody printed.

The larger part of the family holds more, and that number has no manufacturer's
document behind it. Both live in models.py so the part decides, and
conformance/hardware.json records which of the two is verified.
"""

STACK_MASK = STACK_DEPTH - 1
"""The default when a caller does not say, which is the smaller part's."""

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
"""The bits an instruction may not set, because the part owns them."""


def signed(word: int) -> int:
    return word - WORD if word & SIGN else word


class Status:
    """The word the host reads to find out whether the part wants attention.

    The ten bits are declared rather than set in a loop over their names. A loop
    is shorter and costs every reader and every checker the ability to see that
    the bits exist: `sr.rqm` and a misspelling of it are the same thing to a loop.
    """

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
        """Take every bit the part defines, and nothing between them.

        The three acknowledgements are not among them. They are state the part
        holds and never puts in the word the host reads, so a write to the
        register cannot set them and reading the word back cannot see them.
        """
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
    """The whole register file, at the widths the part being modelled has.

    Every register is declared. An earlier version kept the six signed ones in a
    dictionary reached through `__getattr__`, which is four fewer lines and hides
    the most important structure in this package from every reader and every
    checker: a misspelt register name read as zero instead of raising, and a
    renamed one broke nothing until something ran.

    The six signed registers are properties rather than plain attributes because
    a store has to narrow to sixteen bits and re-sign. That is the part's
    behaviour: it holds two accumulators, two multiplicands and the two halves of
    a product as signed values, and a model that keeps them unsigned agrees with
    the part until the first negative multiply.

    The slots finish that reasoning for writes. Declaring every register stopped a
    misspelt read from answering zero; without slots a misspelt write is still
    accepted in silence, setting a stray attribute while the register meant keeps
    whatever it held. Both halves of the mistake now raise.
    """

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
        """A signed register read back as the sixteen bits it actually holds."""
        found = getattr(self, name)
        if not isinstance(found, int):
            raise AttributeError(name)
        return found & 0xFFFF
