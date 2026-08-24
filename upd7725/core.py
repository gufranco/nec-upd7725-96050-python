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

from .errors import RunLimit
from .flags import (
    Flags,
    record_addition,
    record_left_shift,
    record_logic,
    record_result,
    record_right_shift,
)
from .memory import UNSET_SEED, Stores, scramble
from .registers import Registers

WORD_MASK = 0xFFFF

RESET_CYCLES = 4
"""What a reset occupies of the board's clock.

The data sheet gives the reset pin a minimum pulse width of four clock cycles,
and one clock cycle is one instruction on this part. So a reset is not free: the
line has to be held for four of them, and a host pacing against a wall has spent
that time whether or not the part advanced a program.

This is the minimum the manufacturer requires of the host rather than a count of
what the part does internally, which the document does not give. The distinction
is recorded beside the figure in hardware.json.
"""

INTERRUPT_VECTOR = 0x100
"""Where the part goes when it takes the interrupt.

"A low-to-high transition on this pin executes a call instruction to location
100H, if interrupts were previously enabled." A call, so the counter it was
about to run from is pushed and a return comes back to it.
"""

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


def _superseded(asl: int, destination: int) -> bool:
    """Whether the move overwrites the very accumulator the arithmetic would write.

    When it does, the arithmetic does not happen at all. The manufacturer is
    explicit: "if the accumulator specified in the ASL field is also specified as
    the destination of the data move, the ALU operation becomes a NOP, as the data
    move supersedes the ALU operation."

    Discarding the result is not enough, because a NOP is the one operation that
    leaves the flags alone: the document says they are "updated at the end of each
    arithmetic instruction (except NOP)". A model that runs the arithmetic and then
    overwrites the accumulator holds the right value and the wrong flags, and the
    next conditional branch reads those flags.
    """
    return destination == (TO_B if asl else TO_A)


class Core:
    """One processor, its registers, its flags and its three stores."""

    model: Model
    registers: Registers
    stores: Stores
    flags_a: Flags
    flags_b: Flags
    cycles: int
    steps: int
    on_cycle: Callable[[], None] | None
    irq_line: bool

    def __init__(
        self,
        model: Model,
        memory: Stores | None = None,
        fill: int | None = 0,
        sources: dict[str, Callable[[int], int]] | None = None,
        seed: int = UNSET_SEED,
    ) -> None:
        """A part of that model, optionally sharing stores a caller already has.

        The second parameter is called memory and is positional, so building one
        of these reads the same as building the processors in the sibling
        packages. Passing none gives the part its own stores, which is what a
        chip does: the three of them are on the die.
        """
        self.model = model
        self.registers = Registers(
            counter_bits=model.counter_bits,
            table_bits=model.table_bits,
            pointer_bits=model.pointer_bits,
            stack_levels=model.stack_levels,
        )
        self.stores = (
            Stores(
                program_words=model.program_words,
                table_words=model.table_words,
                scratch_words=model.scratch_words,
                fill=fill,
                sources=sources,
            )
            if memory is None
            else memory
        )
        self.flags_a = Flags()
        self.flags_b = Flags()
        self.cycles = 0
        self.steps = 0
        self.on_cycle = None
        self.irq_line = False
        self.power_on(seed)

    def power_on(self, seed: int = UNSET_SEED) -> None:
        """The state the part is in when the rail comes up and nothing else has.

        Every register holds something derived from the seed, the program counter
        included, so a newly built part steps rubbish from a rubbish address
        exactly as the silicon would. This is where scrambling belongs; reset
        does not do it, because a reset defines a few things and leaves the rest
        holding whatever they held.
        """
        undefined = scramble(12, seed)
        registers = self.registers
        registers.pc = undefined[0]
        registers.rp = undefined[1]
        registers.dp = undefined[2]
        registers.sp = undefined[3]
        registers.k = undefined[4]
        registers.l = undefined[5]
        registers.m = undefined[6]
        registers.n = undefined[7]
        registers.a = undefined[8]
        registers.b = undefined[9]
        registers.tr = undefined[10] & WORD_MASK
        registers.dr = undefined[11] & WORD_MASK
        for slot in range(len(registers.stack)):
            registers.stack[slot] = undefined[slot % len(undefined)] & registers.counter_mask

    def reset(self) -> Core:
        """What the document says a reset does, and nothing beyond it.

        "This input initializes the SPI+ internal logic and sets the PC to 0."
        The accumulators, the pointers and the stores keep whatever they were
        holding, because the page does not say a reset touches them and this
        model does not invent an event the part does not perform.

        It costs the four cycles the data sheet requires the reset line to be
        held for, and they appear in the tally, because a board that pulls that
        line has spent them.

        Returns the part, so a caller can build and reset in one expression
        without losing the reference.
        """
        self.registers.pc = 0
        self.steps = 0
        for _ in range(RESET_CYCLES):
            self.spend()
        return self

    def spend(self) -> None:
        """One cycle: counted once, and announced once.

        Every path that costs the part a cycle comes through here. A count kept
        in one method and a watcher called from another drift the first time
        somebody adds a cycle to only one of them, and nothing catches it.
        """
        self.cycles += 1
        if self.on_cycle is not None:
            self.on_cycle()

    def irq(self) -> bool:
        """Offer the interrupt line, and report whether the part took it.

        The pin is edge sensitive: the document says a low-to-high transition
        executes the call, so a line already high is not a fresh request and this
        returns false. That is the family's rule about inputs being levels rather
        than events, and it is the part's rule too, because a device holding its
        request high does not get served twice.

        Refused while the enable bit is clear, which is what "if interrupts were
        previously enabled" means. A refusal costs nothing and leaves the line
        raised, so the next lowering and raising is a new request.

        Taking it is a call: the counter is pushed and execution continues at
        100H. It costs one cycle, because every instruction on this part costs
        one and the document calls this one an executed call instruction.
        """
        raised = not self.irq_line
        self.irq_line = True
        if not raised or not self.registers.sr.ei:
            return False
        registers = self.registers
        registers.stack[registers.sp] = registers.pc
        registers.sp += 1
        registers.pc = INTERRUPT_VECTOR
        self.spend()
        return True

    def lower_irq(self) -> None:
        """Drop the interrupt line, so raising it again is a fresh request."""
        self.irq_line = False

    def held(self) -> bool:
        """Whether the part has stopped advancing the program.

        Always false here. The data sheet gives this part no halt, no wait and no
        stop instruction: every encoding advances the counter. The method exists
        because the family promises it, and answering honestly is better than
        leaving a caller to find out this one repository omits it.
        """
        return False

    def step(self) -> int:
        """One instruction, and the multiply that follows every one of them.

        Returns the cycles it cost, which on this part is always one. A host that
        cannot ask what an instruction cost cannot pace anything, so the figure is
        returned rather than left for the caller to assume.

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
        before = self.cycles
        self.spend()
        self.steps += 1
        return self.cycles - before

    def run_for(self, cycles: int) -> int:
        """Run a budget of cycles and report what was really spent.

        An instruction is not divisible, so the last one can carry the run past
        the budget. The overshoot is returned rather than hidden, so a host
        subtracts it from the next slice and a long run does not drift.
        """
        spent = 0
        while spent < cycles:
            spent += self.step()
        return spent

    def run_until(self, check: Callable[[Core], bool], limit: int | None = None) -> Core:
        """Step until the condition holds.

        `limit` bounds the number of instructions and raises when it is reached.
        Without one this runs as long as the part would, which for a program
        that never satisfies the condition is forever. That is what the silicon
        does, so it is what happens here unless a caller asks for otherwise.

        One instruction is one cycle on this part, so a bound on instructions
        and a bound on cycles are the same number. The signature still counts
        instructions, because that is what the two sibling cores count and a
        caller moving between them should not have to know which.
        """
        taken = 0
        while not check(self):
            self.step()
            taken += 1
            if limit is not None and taken >= limit:
                raise RunLimit(f"gave up after {taken} instructions at {self.registers.pc:03X}")
        return self

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

        if alu and not _superseded(asl, destination):
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
