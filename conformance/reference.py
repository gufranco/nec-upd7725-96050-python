from collections.abc import Callable
from typing import Protocol, runtime_checkable

WORD = 0x10000

SIGN = 0x8000

DEFAULT_STACK_LEVELS = 4

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

STACK_LEVELS = {
    UPD7725: 4,
    UPD96050: 8,
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


@runtime_checkable
class Words(Protocol):
    def __len__(self) -> int: ...

    def __getitem__(self, at: int) -> int: ...

    def __setitem__(self, at: int, value: int) -> None: ...


def n16(value: int) -> int:
    return value & 0xFFFF


def n24(value: int) -> int:
    return value & 0xFFFFFF


def i16(value: int) -> int:
    value &= 0xFFFF
    return value - WORD if value & SIGN else value


class Flag:
    __slots__ = FLAG_BITS

    ov0: int
    ov1: int
    z: int
    c: int
    s0: int
    s1: int

    def __init__(self, word: int = 0) -> None:
        self.assign(word)

    def assign(self, word: int) -> None:
        for place, name in enumerate(FLAG_BITS):
            setattr(self, name, word >> place & 1)

    def copy(self) -> "Flag":
        return Flag(int(self))

    def __int__(self) -> int:
        return sum(getattr(self, name) << place for place, name in enumerate(FLAG_BITS))


class Status:
    __slots__ = tuple(sorted({name for name, _ in STATUS_BITS} | {"drs", "siack", "soack"}))

    p0: int
    p1: int
    ei: int
    sic: int
    soc: int
    drc: int
    dma: int
    usf0: int
    usf1: int
    rqm: int
    drs: int
    siack: int
    soack: int

    def __init__(self, word: int = 0) -> None:
        self.siack = 0
        self.soack = 0
        self.assign(word)

    def assign(self, word: int) -> None:
        for name, place in STATUS_BITS:
            setattr(self, name, word >> place & 1)
        self.drs = word >> TRANSFER_BIT & 1

    def __int__(self) -> int:
        word = int(sum(getattr(self, name) << place for name, place in STATUS_BITS))
        transfer = int(bool(self.drs and not self.drc))
        return word | transfer << TRANSFER_BIT


class Registers:
    k: int
    l: int  # noqa: E741
    m: int
    n: int
    a: int
    b: int
    si: int
    so: int
    tr: int
    trb: int
    dr: int

    def __init__(
        self,
        counter_bits: int,
        table_bits: int,
        pointer_bits: int,
        stack_levels: int = DEFAULT_STACK_LEVELS,
    ) -> None:
        self.pc_mask = (1 << counter_bits) - 1
        self.rp_mask = (1 << table_bits) - 1
        self.dp_mask = (1 << pointer_bits) - 1
        self.stack_mask = stack_levels - 1
        self.stack = [0] * stack_levels
        self.sr = Status()
        self._pc = self._rp = self._dp = self._sp = 0
        for name in SIGNED_REGISTERS + PLAIN_REGISTERS:
            setattr(self, name, 0)

    @property
    def pc(self) -> int:
        return self._pc

    @pc.setter
    def pc(self, value: int) -> None:
        self._pc = value & self.pc_mask

    @property
    def rp(self) -> int:
        return self._rp

    @rp.setter
    def rp(self, value: int) -> None:
        self._rp = value & self.rp_mask

    @property
    def dp(self) -> int:
        return self._dp

    @dp.setter
    def dp(self, value: int) -> None:
        self._dp = value & self.dp_mask

    @property
    def sp(self) -> int:
        return self._sp

    @sp.setter
    def sp(self, value: int) -> None:
        self._sp = value & self.stack_mask


SOURCES: "tuple[Callable[[Upd96050], int], ...]" = (
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
    lambda chip: chip._read_serial(reversed_order=False),
    lambda chip: chip._read_serial(reversed_order=True),
    lambda chip: n16(chip.regs.k),
    lambda chip: n16(chip.regs.l),
    lambda chip: n16(chip.dataRAM[chip.regs.dp]),
)

OPERANDS: "tuple[Callable[[Upd96050, int], int], ...]" = (
    lambda chip, moving: n16(chip.dataRAM[chip.regs.dp]),
    lambda chip, moving: moving,
    lambda chip, moving: n16(chip.regs.m),
    lambda chip, moving: n16(chip.regs.n),
)

OPERATIONS: "dict[int, Callable[[int, int, int], tuple[int, int]]]" = {
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

CONDITIONS: "dict[int, Callable[[Upd96050], int]]" = {
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

ACC_A = 1

ACC_B = 2

THROUGH_OUTPUT = 0x000
JUMP_NEAR = 0x100
JUMP_FAR = 0x101
CALL_NEAR = 0x140
CALL_FAR = 0x141


class Upd96050:
    revision: str
    regs: Registers
    flags_a: Flag
    flags_b: Flag
    programROM: Words  # noqa: N815
    dataROM: Words  # noqa: N815
    dataRAM: Words  # noqa: N815

    def __init__(self, revision: str = UPD96050) -> None:
        if revision not in WIDTHS:
            raise UnknownRevision(f"{revision} is not a revision this reference has")
        self.revision = revision
        self.regs = Registers(*WIDTHS[revision], stack_levels=STACK_LEVELS[revision])
        self.flags_a = Flag()
        self.flags_b = Flag()
        self.programROM = [0] * PROGRAM_WORDS
        self.dataROM = [0] * DATA_WORDS
        self.dataRAM = [0] * DATA_WORDS

    def exec(self) -> None:
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

    def _read_serial(self, reversed_order: bool) -> int:
        self.regs.sr.siack = 0
        if not reversed_order:
            return n16(self.regs.si)
        width = 8 if self.regs.sr.sic else 16
        kept = n16(self.regs.si) >> width << width
        return kept | int(f"{self.regs.si & (1 << width) - 1:0{width}b}"[::-1], 2)

    def _read_data_and_ask(self) -> int:
        self.regs.sr.rqm = 1
        return n16(self.regs.dr)

    def _operate(self, opcode: int) -> None:
        pselect = opcode >> 20 & 0x3
        alu = opcode >> 16 & 0xF
        asl = opcode >> 15 & 0x1
        dpl = opcode >> 13 & 0x3
        dphm = opcode >> 9 & 0xF
        rpdcr = opcode >> 8 & 0x1
        source = opcode >> 4 & 0xF
        destination = opcode & 0xF

        moving = SOURCES[source](self)

        if alu and destination != (ACC_B if asl else ACC_A):
            self._arithmetic(alu, OPERANDS[pselect](self, moving), asl)

        self._move(moving << 6 | destination)

        if destination != 4:
            self._step_pointer(dpl, dphm)
        if destination != 5 and rpdcr:
            self.regs.rp -= 1

    def _arithmetic(self, alu: int, right: int, asl: int) -> None:
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

    def _return(self, opcode: int) -> None:
        self._operate(opcode)
        self.regs.sp -= 1
        self.regs.pc = self.regs.stack[self.regs.sp]

    def _branch(self, opcode: int) -> None:
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

    def _move(self, opcode: int) -> None:
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
            registers.sr.soack = 1
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

    def _step_pointer(self, dpl: int, dphm: int) -> None:
        registers = self.regs
        if dpl == 1:
            registers.dp = (registers.dp & 0xF0) + (registers.dp + 1 & 0x0F)
        elif dpl == 2:
            registers.dp = (registers.dp & 0xF0) + (registers.dp - 1 & 0x0F)
        elif dpl == 3:
            registers.dp = registers.dp & 0xF0
        registers.dp = registers.dp ^ dphm << 4

    def read_sr(self) -> int:
        return int(self.regs.sr) >> 8

    def write_sr(self, data: int) -> None:
        return

    def read_dr(self) -> int:
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

    def write_dr(self, data: int) -> None:
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

    def read_dp(self, address: int) -> int:
        word = self.dataRAM[address >> 1 & 2047]
        return word >> 8 & 0xFF if address & 1 else word & 0xFF

    def write_dp(self, address: int, data: int) -> None:
        where = address >> 1 & 2047
        word = self.dataRAM[where]
        if address & 1:
            self.dataRAM[where] = data << 8 | word & 0x00FF
        else:
            self.dataRAM[where] = word & 0xFF00 | data
