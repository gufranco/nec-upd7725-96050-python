"""Everything the processor holds between one instruction and the next.

Three of the registers are narrower on the smaller part than on the larger one,
and the widths are the only difference between the two: the instruction set,
the flags and the status word are identical. So the widths arrive at construction
rather than being written into the arithmetic, and every store masks itself.

Six registers are signed. They are the two accumulators, the two multiplicands
and the two halves of the product, and a model that keeps them unsigned agrees
with the part until the first negative multiply and then stops.
"""

WORD = 0x10000

SIGN = 0x8000

STACK_DEPTH = 16

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
"""The bits an instruction may not set, because the part owns them."""


def signed(word):
    return word - WORD if word & SIGN else word


class Status:
    """The word the console reads to find out whether the part wants attention."""

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

    def __init__(self):
        for name in self.__slots__:
            setattr(self, name, False)

    def assign(self, word):
        """Take every bit the part defines, and nothing between them."""
        for name, place in STATUS_PLACES:
            setattr(self, name, bool(word >> place & 1))
        self.drs = bool(word >> TRANSFER_PLACE & 1)

    def __int__(self):
        word = 0
        for name, place in STATUS_PLACES:
            word |= int(getattr(self, name)) << place
        if self.drs and not self.drc:
            word |= 1 << TRANSFER_PLACE
        return word

    def __repr__(self):
        held = [name for name, _ in STATUS_PLACES if getattr(self, name)]
        return f"<Status {' '.join(held) if held else 'none'}>"


class Registers:
    """The whole register file, at the widths the part being modelled has."""

    def __init__(self, counter_bits, table_bits, pointer_bits):
        self.counter_mask = (1 << counter_bits) - 1
        self.table_mask = (1 << table_bits) - 1
        self.pointer_mask = (1 << pointer_bits) - 1
        self.stack = [0] * STACK_DEPTH
        self._pc = 0
        self._rp = 0
        self._dp = 0
        self._sp = 0
        self._signed = dict.fromkeys(SIGNED, 0)
        for name in UNSIGNED:
            setattr(self, name, 0)
        self.sr = Status()

    @property
    def pc(self):
        return self._pc

    @pc.setter
    def pc(self, value):
        self._pc = value & self.counter_mask

    @property
    def rp(self):
        return self._rp

    @rp.setter
    def rp(self, value):
        self._rp = value & self.table_mask

    @property
    def dp(self):
        return self._dp

    @dp.setter
    def dp(self, value):
        self._dp = value & self.pointer_mask

    @property
    def sp(self):
        return self._sp

    @sp.setter
    def sp(self, value):
        self._sp = value & STACK_MASK

    def word(self, name):
        """A signed register read back as the sixteen bits it actually holds."""
        return self._signed[name] & 0xFFFF

    def __getattr__(self, name):
        if name in SIGNED:
            return self._signed[name]
        raise AttributeError(name)

    def __setattr__(self, name, value):
        if name in SIGNED:
            self._signed[name] = signed(value & 0xFFFF)
            return
        object.__setattr__(self, name, value)
