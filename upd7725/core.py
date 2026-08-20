"""Fetch, and the four instruction forms the processor has.

The top two bits of every word choose the form. One does arithmetic and a move at
once, one does that and then returns, one branches, and one loads a constant. That
is the entire instruction set, and it is why a part this small can carry programs
as different as a road renderer and a shogi player.

Two things about it are worth knowing before reading further. Every instruction
ends with a multiply, whether or not the instruction asked for one, because the
multiplier is wired to two registers and runs continuously. And the arithmetic
form performs its move after its arithmetic, so the value it moves is the one that
was read at the start rather than the one the arithmetic just produced.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .flags import (
    Flags,
    record_addition,
    record_left_shift,
    record_logic,
    record_result,
    record_right_shift,
)
from .memory import Stores
from .registers import Registers

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Callable

    from .models import Model

WORD = 0x10000

WORD_MASK = 0xFFFF

SIGN = 0x8000

FORM_SHIFT = 22

OPERATE = 0
RETURN = 1
JUMP = 2
LOAD = 3

FROM_TRB = 0
FROM_A = 1
FROM_B = 2
FROM_TR = 3
FROM_POINTER = 4
FROM_TABLE_POINTER = 5
FROM_TABLE = 6
FROM_SATURATION = 7
FROM_DATA_AND_ASK = 8
FROM_DATA = 9
FROM_STATUS = 10
FROM_SERIAL_HIGH = 11
FROM_SERIAL_LOW = 12
FROM_K = 13
FROM_L = 14
FROM_SCRATCH = 15

TO_NOWHERE = 0
TO_A = 1
TO_B = 2
TO_TR = 3
TO_POINTER = 4
TO_TABLE_POINTER = 5
TO_DATA = 6
TO_STATUS = 7
TO_SERIAL_LOW = 8
TO_SERIAL_HIGH = 9
TO_K = 10
TO_K_AND_TABLE = 11
TO_L_AND_SCRATCH = 12
TO_L = 13
TO_TRB = 14
TO_SCRATCH = 15

OR = 1
AND = 2
XOR = 3
SUBTRACT = 4
ADD = 5
SUBTRACT_WITH_BORROW = 6
ADD_WITH_CARRY = 7
DECREMENT = 8
INCREMENT = 9
NEGATE = 10
SHIFT_RIGHT = 11
SHIFT_LEFT = 12
SHIFT_LEFT_TWICE = 13
SHIFT_LEFT_FOUR_TIMES = 14
SWAP_HALVES = 15

LOGICAL = frozenset({OR, AND, XOR, NEGATE, SHIFT_LEFT_TWICE, SHIFT_LEFT_FOUR_TIMES, SWAP_HALVES})
ARITHMETIC = frozenset({SUBTRACT, ADD, SUBTRACT_WITH_BORROW, ADD_WITH_CARRY, DECREMENT, INCREMENT})

POINTER_HOLD = 0
POINTER_UP = 1
POINTER_DOWN = 2
POINTER_CLEAR = 3

POINTER_LOW = 0x0F
POINTER_HIGH = 0xF0
POINTER_HIGH_SHIFT = 4

FAR_HALF = 0x2000

BANK_SHIFT = 11

SCRATCH_FAR_HALF = 0x40

STATUS_KEPT = 0x907C
STATUS_TAKEN = WORD_MASK & ~STATUS_KEPT

MULTIPLY_SHIFT = 15

JUMP_THROUGH_OUTPUT = 0x000
JUMP_IF_NO_CARRY_A = 0x080
JUMP_IF_CARRY_A = 0x082
JUMP_IF_NO_CARRY_B = 0x084
JUMP_IF_CARRY_B = 0x086
JUMP_IF_NOT_ZERO_A = 0x088
JUMP_IF_ZERO_A = 0x08A
JUMP_IF_NOT_ZERO_B = 0x08C
JUMP_IF_ZERO_B = 0x08E
JUMP_IF_NO_OVERFLOW_A0 = 0x090
JUMP_IF_OVERFLOW_A0 = 0x092
JUMP_IF_NO_OVERFLOW_B0 = 0x094
JUMP_IF_OVERFLOW_B0 = 0x096
JUMP_IF_NO_OVERFLOW_A1 = 0x098
JUMP_IF_OVERFLOW_A1 = 0x09A
JUMP_IF_NO_OVERFLOW_B1 = 0x09C
JUMP_IF_OVERFLOW_B1 = 0x09E
JUMP_IF_NOT_SIGN_A0 = 0x0A0
JUMP_IF_SIGN_A0 = 0x0A2
JUMP_IF_NOT_SIGN_B0 = 0x0A4
JUMP_IF_SIGN_B0 = 0x0A6
JUMP_IF_NOT_SIGN_A1 = 0x0A8
JUMP_IF_SIGN_A1 = 0x0AA
JUMP_IF_NOT_SIGN_B1 = 0x0AC
JUMP_IF_SIGN_B1 = 0x0AE
JUMP_IF_POINTER_EMPTY = 0x0B0
JUMP_IF_POINTER_NOT_EMPTY = 0x0B1
JUMP_IF_POINTER_FULL = 0x0B2
JUMP_IF_POINTER_NOT_FULL = 0x0B3
JUMP_IF_NO_INPUT_ACK = 0x0B4
JUMP_IF_INPUT_ACK = 0x0B6
JUMP_IF_NO_OUTPUT_ACK = 0x0B8
JUMP_IF_OUTPUT_ACK = 0x0BA
JUMP_IF_NOT_ASKING = 0x0BC
JUMP_IF_ASKING = 0x0BE
JUMP_LOW = 0x100
JUMP_HIGH = 0x101
CALL_LOW = 0x140
CALL_HIGH = 0x141

BRANCHES: dict[int, Callable[[Core], bool]] = {
    JUMP_IF_NO_CARRY_A: lambda chip: not chip.flags_a.c,
    JUMP_IF_CARRY_A: lambda chip: chip.flags_a.c,
    JUMP_IF_NO_CARRY_B: lambda chip: not chip.flags_b.c,
    JUMP_IF_CARRY_B: lambda chip: chip.flags_b.c,
    JUMP_IF_NOT_ZERO_A: lambda chip: not chip.flags_a.z,
    JUMP_IF_ZERO_A: lambda chip: chip.flags_a.z,
    JUMP_IF_NOT_ZERO_B: lambda chip: not chip.flags_b.z,
    JUMP_IF_ZERO_B: lambda chip: chip.flags_b.z,
    JUMP_IF_NO_OVERFLOW_A0: lambda chip: not chip.flags_a.ov0,
    JUMP_IF_OVERFLOW_A0: lambda chip: chip.flags_a.ov0,
    JUMP_IF_NO_OVERFLOW_B0: lambda chip: not chip.flags_b.ov0,
    JUMP_IF_OVERFLOW_B0: lambda chip: chip.flags_b.ov0,
    JUMP_IF_NO_OVERFLOW_A1: lambda chip: not chip.flags_a.ov1,
    JUMP_IF_OVERFLOW_A1: lambda chip: chip.flags_a.ov1,
    JUMP_IF_NO_OVERFLOW_B1: lambda chip: not chip.flags_b.ov1,
    JUMP_IF_OVERFLOW_B1: lambda chip: chip.flags_b.ov1,
    JUMP_IF_NOT_SIGN_A0: lambda chip: not chip.flags_a.s0,
    JUMP_IF_SIGN_A0: lambda chip: chip.flags_a.s0,
    JUMP_IF_NOT_SIGN_B0: lambda chip: not chip.flags_b.s0,
    JUMP_IF_SIGN_B0: lambda chip: chip.flags_b.s0,
    JUMP_IF_NOT_SIGN_A1: lambda chip: not chip.flags_a.s1,
    JUMP_IF_SIGN_A1: lambda chip: chip.flags_a.s1,
    JUMP_IF_NOT_SIGN_B1: lambda chip: not chip.flags_b.s1,
    JUMP_IF_SIGN_B1: lambda chip: chip.flags_b.s1,
    JUMP_IF_POINTER_EMPTY: lambda chip: (chip.registers.dp & POINTER_LOW) == 0x00,
    JUMP_IF_POINTER_NOT_EMPTY: lambda chip: (chip.registers.dp & POINTER_LOW) != 0x00,
    JUMP_IF_POINTER_FULL: lambda chip: (chip.registers.dp & POINTER_LOW) == POINTER_LOW,
    JUMP_IF_POINTER_NOT_FULL: lambda chip: (chip.registers.dp & POINTER_LOW) != POINTER_LOW,
    JUMP_IF_NO_INPUT_ACK: lambda chip: not chip.registers.sr.siack,
    JUMP_IF_INPUT_ACK: lambda chip: chip.registers.sr.siack,
    JUMP_IF_NO_OUTPUT_ACK: lambda chip: not chip.registers.sr.soack,
    JUMP_IF_OUTPUT_ACK: lambda chip: chip.registers.sr.soack,
    JUMP_IF_NOT_ASKING: lambda chip: not chip.registers.sr.rqm,
    JUMP_IF_ASKING: lambda chip: chip.registers.sr.rqm,
}


class Core:
    """One processor, its registers, its flags and its three stores."""

    model: Model
    registers: Registers
    stores: Stores
    flags_a: Flags
    flags_b: Flags
    cycles: int

    def __init__(
        self,
        model: Model,
        fill: int | None = 0,
        sources: dict[str, Callable[[int], int]] | None = None,
    ) -> None:
        self.model = model
        self.registers = Registers(
            counter_bits=model.counter_bits,
            table_bits=model.table_bits,
            pointer_bits=model.pointer_bits,
            stack_levels=model.stack_levels,
        )
        self.stores = Stores(
            program_words=model.program_words,
            table_words=model.table_words,
            scratch_words=model.scratch_words,
            fill=fill,
            sources=sources,
        )
        self.flags_a = Flags()
        self.flags_b = Flags()
        self.cycles = 0

    def step(self) -> None:
        """One instruction, and the multiply that follows every one of them.

        One instruction is one cycle on this part, so the count kept here is a
        cycle count and not merely an instruction count. That is the
        manufacturer's figure rather than a convenience: "Since the 77C25
        executes an instruction in one external clock cycle", and "All
        instructions execute in one instruction cycle". Nothing here has to carry
        a per-instruction cycle table, because the part does not have one.
        """
        opcode = self.stores.program[self.registers.pc]
        self.registers.pc += 1

        form = opcode >> FORM_SHIFT
        if form == OPERATE:
            self._operate(opcode)
        elif form == RETURN:
            self._return(opcode)
        elif form == JUMP:
            self._jump(opcode)
        else:
            self._load(opcode)

        self._multiply()
        self.cycles += 1

    def run(self, instructions: int) -> None:
        for _ in range(instructions):
            self.step()

    def _multiply(self) -> None:
        product = self.registers.k * self.registers.l
        self.registers.m = product >> MULTIPLY_SHIFT
        self.registers.n = product << 1

    def _operate(self, opcode: int) -> None:
        pselect = opcode >> 20 & 0x3
        alu = opcode >> 16 & 0xF
        asl = opcode >> 15 & 0x1
        dpl = opcode >> 13 & 0x3
        dphm = opcode >> 9 & 0xF
        rpdcr = opcode >> 8 & 0x1
        source = opcode >> 4 & 0xF
        destination = opcode & 0xF

        moving = self._read(source)

        if alu:
            self._compute(alu, pselect, asl, moving)

        self._load(moving << 6 | destination)

        if destination != TO_POINTER:
            self._step_pointer(dpl, dphm)
        if destination != TO_TABLE_POINTER and rpdcr:
            self.registers.rp -= 1

    def _return(self, opcode: int) -> None:
        self._operate(opcode)
        self.registers.sp -= 1
        self.registers.pc = self.registers.stack[self.registers.sp]

    def _jump(self, opcode: int) -> None:
        branch = opcode >> 13 & 0x1FF
        address = opcode >> 2 & 0x7FF
        bank = opcode & 0x3

        target = (self.registers.pc & FAR_HALF | bank << BANK_SHIFT | address) & 0x3FFF

        if branch == JUMP_THROUGH_OUTPUT:
            self.registers.pc = self.registers.so
        elif branch == JUMP_LOW:
            self.registers.pc = target & ~FAR_HALF
        elif branch == JUMP_HIGH:
            self.registers.pc = target | FAR_HALF
        elif branch in (CALL_LOW, CALL_HIGH):
            self.registers.stack[self.registers.sp] = self.registers.pc
            self.registers.sp += 1
            self.registers.pc = target | FAR_HALF if branch == CALL_HIGH else target & ~FAR_HALF
        else:
            taken = BRANCHES.get(branch)
            if taken is not None and taken(self):
                self.registers.pc = target

    def _read(self, source: int) -> int:
        registers = self.registers
        if source == FROM_TRB:
            return registers.trb
        if source == FROM_A:
            return registers.word("a")
        if source == FROM_B:
            return registers.word("b")
        if source == FROM_TR:
            return registers.tr
        if source == FROM_POINTER:
            return registers.dp
        if source == FROM_TABLE_POINTER:
            return registers.rp
        if source == FROM_TABLE:
            return self.stores.table[registers.rp]
        if source == FROM_SATURATION:
            return SIGN - int(self.flags_a.s1)
        if source == FROM_DATA_AND_ASK:
            registers.sr.rqm = True
            return registers.dr
        if source == FROM_DATA:
            return registers.dr
        if source == FROM_STATUS:
            return int(registers.sr)
        if source in (FROM_SERIAL_HIGH, FROM_SERIAL_LOW):
            return registers.si
        if source == FROM_K:
            return registers.word("k")
        if source == FROM_L:
            return registers.word("l")
        return self.stores.scratch[registers.dp]

    def _compute(self, alu: int, pselect: int, asl: int, moving: int) -> None:
        registers = self.registers

        if pselect == 0:
            right = self.stores.scratch[registers.dp]
        elif pselect == 1:
            right = moving
        elif pselect == 2:
            right = registers.word("m")
        else:
            right = registers.word("n")

        if asl:
            left = registers.word("b")
            flags = self.flags_b.copy()
            carry = int(self.flags_a.c)
        else:
            left = registers.word("a")
            flags = self.flags_a.copy()
            carry = int(self.flags_b.c)

        result, right = _apply(alu, left, right, carry)

        record_result(flags, result)
        if alu in LOGICAL:
            record_logic(flags)
        elif alu in ARITHMETIC:
            record_addition(flags, left, right, result, adding=bool(alu & 1))
        elif alu == SHIFT_RIGHT:
            record_right_shift(flags, left)
        else:
            record_left_shift(flags, left)

        if asl:
            registers.b = result
            self.flags_b = flags
        else:
            registers.a = result
            self.flags_a = flags

    def _load(self, opcode: int) -> None:
        value = opcode >> 6 & WORD_MASK
        destination = opcode & 0xF
        registers = self.registers

        if destination == TO_NOWHERE:
            return
        if destination == TO_A:
            registers.a = value
        elif destination == TO_B:
            registers.b = value
        elif destination == TO_TR:
            registers.tr = value
        elif destination == TO_POINTER:
            registers.dp = value
        elif destination == TO_TABLE_POINTER:
            registers.rp = value
        elif destination == TO_DATA:
            registers.dr = value
            registers.sr.rqm = True
        elif destination == TO_STATUS:
            registers.sr.assign(int(registers.sr) & STATUS_KEPT | value & STATUS_TAKEN)
        elif destination in (TO_SERIAL_LOW, TO_SERIAL_HIGH):
            registers.so = value
        elif destination == TO_K:
            registers.k = value
        elif destination == TO_K_AND_TABLE:
            registers.k = value
            registers.l = self.stores.table[registers.rp]
        elif destination == TO_L_AND_SCRATCH:
            registers.l = value
            registers.k = self.stores.scratch[registers.dp | SCRATCH_FAR_HALF]
        elif destination == TO_L:
            registers.l = value
        elif destination == TO_TRB:
            registers.trb = value
        else:
            self.stores.scratch[registers.dp] = value

    def _step_pointer(self, dpl: int, dphm: int) -> None:
        registers = self.registers
        pointer = registers.dp

        if dpl == POINTER_UP:
            pointer = (pointer & POINTER_HIGH) + (pointer + 1 & POINTER_LOW)
        elif dpl == POINTER_DOWN:
            pointer = (pointer & POINTER_HIGH) + (pointer - 1 & POINTER_LOW)
        elif dpl == POINTER_CLEAR:
            pointer = pointer & POINTER_HIGH

        if dpl != POINTER_HOLD:
            registers.dp = pointer
        registers.dp = registers.dp ^ dphm << POINTER_HIGH_SHIFT


def _apply(alu: int, left: int, right: int, carry: int) -> tuple[int, int]:
    """The result, and the operand the flags should be told about.

    Two of the sixteen replace their operand with one before the flags are set,
    because stepping by one is a sum with a constant rather than with whatever
    happened to be selected.
    """
    if alu == OR:
        return (left | right) & WORD_MASK, right
    if alu == AND:
        return left & right & WORD_MASK, right
    if alu == XOR:
        return (left ^ right) & WORD_MASK, right
    if alu == SUBTRACT:
        return (left - right) & WORD_MASK, right
    if alu == ADD:
        return (left + right) & WORD_MASK, right
    if alu == SUBTRACT_WITH_BORROW:
        return (left - right - carry) & WORD_MASK, right
    if alu == ADD_WITH_CARRY:
        return (left + right + carry) & WORD_MASK, right
    if alu == DECREMENT:
        return (left - 1) & WORD_MASK, 1
    if alu == INCREMENT:
        return (left + 1) & WORD_MASK, 1
    if alu == NEGATE:
        return ~left & WORD_MASK, right
    if alu == SHIFT_RIGHT:
        return (left >> 1 | left & SIGN) & WORD_MASK, right
    if alu == SHIFT_LEFT:
        return (left << 1 | carry) & WORD_MASK, right
    if alu == SHIFT_LEFT_TWICE:
        return (left << 2 | 3) & WORD_MASK, right
    if alu == SHIFT_LEFT_FOUR_TIMES:
        return (left << 4 | 15) & WORD_MASK, right
    return (left << 8 | left >> 8) & WORD_MASK, right
