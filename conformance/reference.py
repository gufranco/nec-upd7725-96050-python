"""The reference processor, ported to Python.

This is not the model. The model lives in `upd7725/`, and this is the independent
implementation it is checked against, ported from the one a widely used emulator
carries.

The two are deliberately built differently. This one dispatches through tables: a
source is a lookup, an operation is a lookup, a branch is a lookup. The model
branches through named conditions instead. Two implementations that share a shape
tend to share a mistake, and these two do not share a shape.

Neither of them is the evidence, though. The evidence is `corpus.json`, recorded
from the original implementation at the commit named in `pinned.json`, before this
file existed. Both this port and the model are held to those recordings, so a
mistake made here shows up as a failure here rather than as agreement with a model
that made the same one.
"""

WORD = 0x10000

SIGN = 0x8000

STACK_DEPTH = 16

PROGRAM_WORDS = 16384

DATA_WORDS = 2048

FAR_HALF = 0x2000

SCRATCH_FAR_HALF = 0x40

STATUS_KEPT_BY_THE_PART = 0x907C

UPD7725 = "uPD7725"

UPD96050 = "uPD96050"

WIDTHS = {
    UPD7725: (11, 10, 8),
    UPD96050: (14, 11, 11),
}

FLAG_BITS = ("ov0", "ov1", "z", "c", "s0", "s1")

STATUS_BITS = (
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

TRANSFER_BIT = 12

SIGNED_REGISTERS = ("k", "l", "m", "n", "a", "b")

PLAIN_REGISTERS = ("si", "so", "tr", "trb", "dr")


class UnknownRevision(Exception):
    pass


def n16(value):
    return value & 0xFFFF


def n24(value):
    return value & 0xFFFFFF


def i16(value):
    value &= 0xFFFF
    return value - WORD if value & SIGN else value


class Flag:
    """The six bits one accumulator carries."""

    __slots__ = FLAG_BITS

    def __init__(self, word=0):
        self.assign(word)

    def assign(self, word):
        for place, name in enumerate(FLAG_BITS):
            setattr(self, name, word >> place & 1)

    def copy(self):
        return Flag(int(self))

    def __int__(self):
        return sum(getattr(self, name) << place for place, name in enumerate(FLAG_BITS))


class Status:
    """The word the console reads, plus the two acknowledgements it never sees."""

    __slots__ = tuple(sorted({name for name, _ in STATUS_BITS} | {"drs", "siack", "soack"}))

    def __init__(self, word=0):
        self.siack = 0
        self.soack = 0
        self.assign(word)

    def assign(self, word):
        for name, place in STATUS_BITS:
            setattr(self, name, word >> place & 1)
        self.drs = word >> TRANSFER_BIT & 1

    def __int__(self):
        word = sum(getattr(self, name) << place for name, place in STATUS_BITS)
        return word | (self.drs and not self.drc) << TRANSFER_BIT


class Registers:
    """The register file, narrowed to the widths the part being modelled has."""

    def __init__(self, counter_bits, table_bits, pointer_bits):
        self.pc_mask = (1 << counter_bits) - 1
        self.rp_mask = (1 << table_bits) - 1
        self.dp_mask = (1 << pointer_bits) - 1
        self.stack = [0] * STACK_DEPTH
        self.sr = Status()
        self._pc = self._rp = self._dp = self._sp = 0
        for name in SIGNED_REGISTERS + PLAIN_REGISTERS:
            setattr(self, name, 0)

    @property
    def pc(self):
        return self._pc

    @pc.setter
    def pc(self, value):
        self._pc = value & self.pc_mask

    @property
    def rp(self):
        return self._rp

    @rp.setter
    def rp(self, value):
        self._rp = value & self.rp_mask

    @property
    def dp(self):
        return self._dp

    @dp.setter
    def dp(self, value):
        self._dp = value & self.dp_mask

    @property
    def sp(self):
        return self._sp

    @sp.setter
    def sp(self, value):
        self._sp = value & 0xF


SOURCES = (
    lambda chip: n16(chip.regs.trb),
    lambda chip: n16(chip.regs.a),
    lambda chip: n16(chip.regs.b),
    lambda chip: n16(chip.regs.tr),
    lambda chip: n16(chip.regs.dp),
    lambda chip: n16(chip.regs.rp),
    lambda chip: n16(chip.dataROM[chip.regs.rp]),
    lambda chip: n16(SIGN - chip.flags_a.s1),
    lambda chip: chip._read_data_and_ask(),
    lambda chip: n16(chip.regs.dr),
    lambda chip: n16(int(chip.regs.sr)),
    lambda chip: n16(chip.regs.si),
    lambda chip: n16(chip.regs.si),
    lambda chip: n16(chip.regs.k),
    lambda chip: n16(chip.regs.l),
    lambda chip: n16(chip.dataRAM[chip.regs.dp]),
)

OPERANDS = (
    lambda chip, moving: n16(chip.dataRAM[chip.regs.dp]),
    lambda chip, moving: moving,
    lambda chip, moving: n16(chip.regs.m),
    lambda chip, moving: n16(chip.regs.n),
)

OPERATIONS = {
    1: lambda left, right, carry: (n16(left | right), right),
    2: lambda left, right, carry: (n16(left & right), right),
    3: lambda left, right, carry: (n16(left ^ right), right),
    4: lambda left, right, carry: (n16(left - right), right),
    5: lambda left, right, carry: (n16(left + right), right),
    6: lambda left, right, carry: (n16(left - right - carry), right),
    7: lambda left, right, carry: (n16(left + right + carry), right),
    8: lambda left, right, carry: (n16(left - 1), 1),
    9: lambda left, right, carry: (n16(left + 1), 1),
    10: lambda left, right, carry: (n16(~left), right),
    11: lambda left, right, carry: (n16(left >> 1 | left & SIGN), right),
    12: lambda left, right, carry: (n16(left << 1 | carry), right),
    13: lambda left, right, carry: (n16(left << 2 | 3), right),
    14: lambda left, right, carry: (n16(left << 4 | 15), right),
    15: lambda left, right, carry: (n16(left << 8 | left >> 8), right),
}

WITHOUT_CARRY = frozenset({1, 2, 3, 10, 13, 14, 15})
WITH_CARRY = frozenset({4, 5, 6, 7, 8, 9})

CONDITIONS = {
    0x080: lambda chip: not chip.flags_a.c,
    0x082: lambda chip: chip.flags_a.c,
    0x084: lambda chip: not chip.flags_b.c,
    0x086: lambda chip: chip.flags_b.c,
    0x088: lambda chip: not chip.flags_a.z,
    0x08A: lambda chip: chip.flags_a.z,
    0x08C: lambda chip: not chip.flags_b.z,
    0x08E: lambda chip: chip.flags_b.z,
    0x090: lambda chip: not chip.flags_a.ov0,
    0x092: lambda chip: chip.flags_a.ov0,
    0x094: lambda chip: not chip.flags_b.ov0,
    0x096: lambda chip: chip.flags_b.ov0,
    0x098: lambda chip: not chip.flags_a.ov1,
    0x09A: lambda chip: chip.flags_a.ov1,
    0x09C: lambda chip: not chip.flags_b.ov1,
    0x09E: lambda chip: chip.flags_b.ov1,
    0x0A0: lambda chip: not chip.flags_a.s0,
    0x0A2: lambda chip: chip.flags_a.s0,
    0x0A4: lambda chip: not chip.flags_b.s0,
    0x0A6: lambda chip: chip.flags_b.s0,
    0x0A8: lambda chip: not chip.flags_a.s1,
    0x0AA: lambda chip: chip.flags_a.s1,
    0x0AC: lambda chip: not chip.flags_b.s1,
    0x0AE: lambda chip: chip.flags_b.s1,
    0x0B0: lambda chip: chip.regs.dp & 0x0F == 0x00,
    0x0B1: lambda chip: chip.regs.dp & 0x0F != 0x00,
    0x0B2: lambda chip: chip.regs.dp & 0x0F == 0x0F,
    0x0B3: lambda chip: chip.regs.dp & 0x0F != 0x0F,
    0x0B4: lambda chip: not chip.regs.sr.siack,
    0x0B6: lambda chip: chip.regs.sr.siack,
    0x0B8: lambda chip: not chip.regs.sr.soack,
    0x0BA: lambda chip: chip.regs.sr.soack,
    0x0BC: lambda chip: not chip.regs.sr.rqm,
    0x0BE: lambda chip: chip.regs.sr.rqm,
}

THROUGH_OUTPUT = 0x000
JUMP_NEAR = 0x100
JUMP_FAR = 0x101
CALL_NEAR = 0x140
CALL_FAR = 0x141


class Upd96050:
    """One processor of the family, at the widths its revision has."""

    def __init__(self, revision=UPD96050):
        if revision not in WIDTHS:
            raise UnknownRevision(f"{revision} is not a revision this reference has")
        self.revision = revision
        self.regs = Registers(*WIDTHS[revision])
        self.flags_a = Flag()
        self.flags_b = Flag()
        self.programROM = [0] * PROGRAM_WORDS
        self.dataROM = [0] * DATA_WORDS
        self.dataRAM = [0] * DATA_WORDS

    def exec(self):
        """One instruction, then the multiply the part runs after every one."""
        opcode = n24(self.programROM[self.regs.pc])
        self.regs.pc += 1

        form = opcode >> 22
        if form == 0:
            self._operate(opcode)
        elif form == 1:
            self._return(opcode)
        elif form == 2:
            self._branch(opcode)
        else:
            self._move(opcode)

        product = i16(self.regs.k) * i16(self.regs.l)
        self.regs.m = i16(product >> 15)
        self.regs.n = i16(product << 1)

    def _read_data_and_ask(self):
        self.regs.sr.rqm = 1
        return n16(self.regs.dr)

    def _operate(self, opcode):
        pselect = opcode >> 20 & 0x3
        alu = opcode >> 16 & 0xF
        asl = opcode >> 15 & 0x1
        dpl = opcode >> 13 & 0x3
        dphm = opcode >> 9 & 0xF
        rpdcr = opcode >> 8 & 0x1
        source = opcode >> 4 & 0xF
        destination = opcode & 0xF

        moving = SOURCES[source](self)

        if alu:
            self._arithmetic(alu, OPERANDS[pselect](self, moving), asl)

        self._move(moving << 6 | destination)

        if destination != 4:
            self._step_pointer(dpl, dphm)
        if destination != 5 and rpdcr:
            self.regs.rp -= 1

    def _arithmetic(self, alu, right, asl):
        left = n16(self.regs.b if asl else self.regs.a)
        flags = (self.flags_b if asl else self.flags_a).copy()
        carry = (self.flags_a if asl else self.flags_b).c

        result, right = OPERATIONS[alu](left, right, carry)

        flags.z = int(result == 0)
        flags.s0 = int(bool(result & SIGN))
        if not flags.ov1:
            flags.s1 = flags.s0

        if alu in WITHOUT_CARRY:
            flags.ov0 = flags.ov1 = flags.c = 0
        elif alu in WITH_CARRY:
            carries = left ^ right ^ result
            overflow = (left ^ result) & (right ^ (result if alu & 1 else left))
            held = flags.ov1
            flags.ov0 = int(bool(overflow & SIGN))
            flags.ov1 = (
                int(flags.s0 == flags.s1) if flags.ov0 and held else int(bool(flags.ov0 or held))
            )
            flags.c = int(bool((carries ^ overflow) & SIGN))
        elif alu == 11:
            flags.ov0 = flags.ov1 = 0
            flags.c = left & 1
        else:
            flags.ov0 = flags.ov1 = 0
            flags.c = left >> 15 & 1

        if asl:
            self.regs.b = i16(result)
            self.flags_b = flags
        else:
            self.regs.a = i16(result)
            self.flags_a = flags

    def _return(self, opcode):
        self._operate(opcode)
        self.regs.sp -= 1
        self.regs.pc = self.regs.stack[self.regs.sp]

    def _branch(self, opcode):
        branch = opcode >> 13 & 0x1FF
        address = opcode >> 2 & 0x7FF
        bank = opcode & 0x3

        target = (self.regs.pc & FAR_HALF | bank << 11 | address) & 0x3FFF

        if branch == THROUGH_OUTPUT:
            self.regs.pc = self.regs.so
        elif branch in CONDITIONS:
            if CONDITIONS[branch](self):
                self.regs.pc = target
        elif branch == JUMP_NEAR:
            self.regs.pc = target & ~FAR_HALF
        elif branch == JUMP_FAR:
            self.regs.pc = target | FAR_HALF
        elif branch in (CALL_NEAR, CALL_FAR):
            self.regs.stack[self.regs.sp] = self.regs.pc
            self.regs.sp += 1
            self.regs.pc = target | FAR_HALF if branch == CALL_FAR else target & ~FAR_HALF

    def _move(self, opcode):
        value = opcode >> 6 & 0xFFFF
        destination = opcode & 0xF
        registers = self.regs

        if destination == 0:
            return
        if destination == 1:
            registers.a = i16(value)
        elif destination == 2:
            registers.b = i16(value)
        elif destination == 3:
            registers.tr = value
        elif destination == 4:
            registers.dp = value
        elif destination == 5:
            registers.rp = value
        elif destination == 6:
            registers.dr = value
            registers.sr.rqm = 1
        elif destination == 7:
            kept = int(registers.sr) & STATUS_KEPT_BY_THE_PART
            registers.sr.assign(n16(kept | value & ~STATUS_KEPT_BY_THE_PART))
        elif destination in (8, 9):
            registers.so = value
        elif destination == 10:
            registers.k = i16(value)
        elif destination == 11:
            registers.k = i16(value)
            registers.l = i16(self.dataROM[registers.rp])
        elif destination == 12:
            registers.l = i16(value)
            registers.k = i16(self.dataRAM[registers.dp | SCRATCH_FAR_HALF])
        elif destination == 13:
            registers.l = i16(value)
        elif destination == 14:
            registers.trb = value
        else:
            self.dataRAM[registers.dp] = n16(value)

    def _step_pointer(self, dpl, dphm):
        registers = self.regs
        if dpl == 1:
            registers.dp = (registers.dp & 0xF0) + (registers.dp + 1 & 0x0F)
        elif dpl == 2:
            registers.dp = (registers.dp & 0xF0) + (registers.dp - 1 & 0x0F)
        elif dpl == 3:
            registers.dp = registers.dp & 0xF0
        registers.dp = registers.dp ^ dphm << 4

    def read_sr(self):
        return int(self.regs.sr) >> 8

    def write_sr(self, data):
        return

    def read_dr(self):
        status = self.regs.sr
        if status.drc:
            status.rqm = 0
            return self.regs.dr & 0xFF
        if not status.drs:
            status.drs = 1
            return self.regs.dr & 0xFF
        status.rqm = 0
        status.drs = 0
        return self.regs.dr >> 8 & 0xFF

    def write_dr(self, data):
        status = self.regs.sr
        if status.drc:
            status.rqm = 0
            self.regs.dr = self.regs.dr & 0xFF00 | data
            return
        if not status.drs:
            status.drs = 1
            self.regs.dr = self.regs.dr & 0xFF00 | data
            return
        status.rqm = 0
        status.drs = 0
        self.regs.dr = data << 8 | self.regs.dr & 0x00FF

    def read_dp(self, address):
        word = self.dataRAM[address >> 1 & 2047]
        return word >> 8 & 0xFF if address & 1 else word & 0xFF

    def write_dp(self, address, data):
        where = address >> 1 & 2047
        word = self.dataRAM[where]
        if address & 1:
            self.dataRAM[where] = data << 8 | word & 0x00FF
        else:
            self.dataRAM[where] = word & 0xFF00 | data
