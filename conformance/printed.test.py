import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conformance.printed import (
    TOP_WORD,
    a_jump,
    a_load,
    a_part,
    a_powered_part,
    an_operation,
    fact,
    the_part,
)
from upd7725 import core

SEED = 7725

PAIRS = 64

WORD_BITS = 16


EVERY_FORM = (
    an_operation(),
    core.RETURN << 22,
    a_jump(core.JUMP_LOW),
    a_load(0, core.TO_NOWHERE),
)


def one_step_of(word: int) -> int:
    chip = a_part()
    chip.stores.program[0] = word
    before = chip.cycles
    chip.step()
    return chip.cycles - before


def after_increment(asl: int, top: int) -> tuple[int, int]:
    chip = a_part()
    chip.registers.a = chip.registers.b = top
    chip.stores.program[0] = an_operation(alu=core.INCREMENT, asl=asl)
    chip.step()
    return chip.registers.word("a"), chip.registers.word("b")


def packed_with(name: str) -> tuple[int, int]:
    chip = a_part()
    setattr(chip.flags_a, name.replace("A", "", 1).lower(), True)
    return int(chip.flags_a), int(chip.flags_b)


def product_of(left: int, right: int) -> int:
    chip = a_part()
    chip.registers.k = left
    chip.registers.l = right
    chip.step()
    return chip.registers.word("m") << WORD_BITS | chip.registers.word("n")


def outcome_of(alu: int) -> tuple[int, int]:
    chip = a_part()
    chip.registers.a = 0x1234
    chip.registers.dr = 0x0F0F
    chip.flags_b.c = True
    chip.stores.program[0] = an_operation(alu=alu, pselect=1, src=core.FROM_DATA)
    chip.step()
    return chip.registers.word("a"), int(chip.flags_a)


class CycleFactTest(unittest.TestCase):
    def test_one_instruction_costs_the_printed_number_of_clocks(self) -> None:
        # Arrange
        clocks = fact("clocksPerInstruction")["value"]

        # Act
        cost = one_step_of(an_operation())

        # Assert
        self.assertEqual(cost, clocks)

    def test_every_form_of_instruction_costs_the_same(self) -> None:
        # Arrange
        same = fact("everyInstructionSameLength")["value"]

        # Act
        costs = {one_step_of(word) for word in EVERY_FORM}

        # Assert
        self.assertEqual(len(costs) == 1, same)

    def test_one_instruction_lasts_the_printed_time_at_the_printed_clock(self) -> None:
        # Arrange
        printed = fact("instructionCycleNanoseconds")

        # Act
        cost = one_step_of(an_operation())

        # Assert
        self.assertEqual(round(cost * 1e9 / printed["atClockHz"]), printed["value"])

    def test_a_reset_spends_the_printed_pulse(self) -> None:
        # Arrange
        pulse = fact("resetPulseCycles")["value"]
        chip = a_powered_part()

        # Act
        chip.reset()

        # Assert
        self.assertEqual(chip.cycles, pulse)

    def test_an_instruction_does_not_take_the_earlier_parts_clocks(self) -> None:
        # Arrange
        earlier = the_part()["predecessorForContrast"]

        # Act
        cost = one_step_of(an_operation())

        # Assert
        self.assertLess(cost, earlier["clocksPerInstruction"])


class WidthFactTest(unittest.TestCase):
    def test_the_program_counter_wraps_at_the_printed_width(self) -> None:
        # Arrange
        bits = fact("programCounterBits")["value"]
        chip = a_part()
        chip.registers.pc = (1 << bits) - 1

        # Act
        chip.step()

        # Assert
        self.assertEqual(chip.registers.pc, 0)

    def test_the_program_store_holds_the_printed_words(self) -> None:
        # Arrange
        printed = fact("programWords")

        # Act
        store = a_part().stores.program

        # Assert
        self.assertEqual((len(store), store.bits), (printed["value"], printed["wordBits"]))

    def test_the_table_pointer_wraps_at_the_printed_width(self) -> None:
        # Arrange
        bits = fact("romPointerBits")["value"]
        chip = a_part()
        chip.stores.program[0] = an_operation(rpdcr=1)

        # Act
        chip.step()

        # Assert
        self.assertEqual(chip.registers.rp, (1 << bits) - 1)

    def test_the_table_holds_the_printed_words(self) -> None:
        # Arrange
        printed = fact("dataRomWords")

        # Act
        store = a_part().stores.table

        # Assert
        self.assertEqual((len(store), store.bits), (printed["value"], printed["wordBits"]))

    def test_a_loaded_scratch_pointer_keeps_the_printed_width(self) -> None:
        # Arrange
        bits = fact("dataPointerBits")["value"]
        chip = a_part()
        chip.stores.program[0] = a_load(TOP_WORD, core.TO_POINTER)

        # Act
        chip.step()

        # Assert
        self.assertEqual(chip.registers.dp, (1 << bits) - 1)

    def test_the_scratch_holds_the_printed_words(self) -> None:
        # Arrange
        printed = fact("dataRamWords")

        # Act
        store = a_part().stores.scratch

        # Assert
        self.assertEqual((len(store), store.bits), (printed["value"], printed["wordBits"]))

    def test_the_stack_keeps_as_many_return_addresses_as_it_has_levels(self) -> None:
        # Arrange
        levels = fact("stackLevels")["value"]
        chip = a_part()
        for at in range(levels):
            chip.stores.program[at] = a_jump(core.CALL_LOW, at + 1)

        # Act
        chip.run_for(levels)

        # Assert
        self.assertEqual(sorted(chip.registers.stack), list(range(1, levels + 1)))


class DataPathFactTest(unittest.TestCase):
    def test_each_accumulator_holds_its_own_word_of_the_printed_width(self) -> None:
        # Arrange
        printed = fact("accumulators")
        count = printed["value"]
        top = (1 << printed["bits"]) - 1

        # Act
        found = [after_increment(asl, top) for asl in range(count)]

        # Assert
        self.assertEqual(
            found,
            [tuple(0 if one == asl else top for one in range(count)) for asl in range(count)],
        )

    def test_each_printed_flag_is_its_own_bit_of_one_accumulator(self) -> None:
        # Arrange
        names = fact("flagsPerAccumulator")["value"]

        # Act
        found = [packed_with(name) for name in names]

        # Assert
        self.assertEqual(sorted(found), [(1 << place, 0) for place in range(len(names))])

    def test_the_product_lands_in_m_and_n_at_the_printed_width(self) -> None:
        # Arrange
        printed = fact("multiplier")
        half = 1 << printed["inputBits"] - 1
        source = random.Random(SEED)
        pairs = [
            (source.randrange(-half, half), source.randrange(-half, half)) for _ in range(PAIRS)
        ]

        # Act
        found = [product_of(left, right) for left, right in pairs]

        # Assert
        self.assertEqual(
            found,
            [
                (left * right << 2 * WORD_BITS - printed["productBits"]) & 0xFFFFFFFF
                for left, right in pairs
            ],
        )

    def test_the_alu_field_selects_the_printed_number_of_operations(self) -> None:
        # Arrange
        count = fact("aluOperations")["value"]

        # Act
        found = {outcome_of(alu) for alu in range(count)}

        # Assert
        self.assertEqual(len(found), count)

    def test_an_arithmetic_over_its_own_destination_leaves_the_flags(self) -> None:
        # Arrange
        superseded = fact("arithmeticSupersededByItsOwnDestination")["value"]
        chip = a_part()
        chip.registers.a = chip.registers.b = 0x7FFF
        chip.stores.program[0] = an_operation(
            alu=core.ADD, pselect=1, src=core.FROM_B, dst=core.TO_A
        )

        # Act
        chip.step()

        # Assert
        self.assertEqual(int(chip.flags_a) == 0, superseded)

    def test_a_pointer_moves_only_after_the_data_move_has_used_it(self) -> None:
        # Arrange
        order = fact("instructionElementOrder")["value"]
        chip = a_part()
        chip.registers.dp = 5
        chip.registers.rp = 9
        for at, word in ((5, 0x1111), (6, 0x2222)):
            chip.stores.scratch[at] = word
        for at, word in ((9, 0x3333), (8, 0x4444)):
            chip.stores.table[at] = word
        chip.stores.program[0] = an_operation(
            dpl=core.POINTER_UP, rpdcr=1, src=core.FROM_SCRATCH, dst=core.TO_K_AND_TABLE
        )
        late = order.index("data move") < order.index("pointer modification")

        # Act
        chip.step()

        # Assert
        self.assertEqual(
            (chip.registers.word("k"), chip.registers.word("l")),
            (0x1111, 0x3333) if late else (0x2222, 0x4444),
        )

    def test_an_interrupt_calls_the_printed_location(self) -> None:
        # Arrange
        vector = fact("interruptVector")["value"]
        chip = a_part()
        chip.registers.sr.ei = True

        # Act
        chip.irq()

        # Assert
        self.assertEqual(chip.registers.pc, vector)

    def test_a_reset_sets_the_counter_to_the_printed_value(self) -> None:
        # Arrange
        printed = fact("resetSetsProgramCounterTo")["value"]
        chip = a_powered_part()
        chip.registers.pc = 0x123

        # Act
        chip.reset()

        # Assert
        self.assertEqual(chip.registers.pc, printed)


if __name__ == "__main__":
    unittest.main()
