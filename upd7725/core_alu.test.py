from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conformance.printed import (
    ADD,
    ADD_WITH_CARRY,
    AND,
    DECREMENT,
    FROM_BUS,
    FROM_M,
    FROM_N,
    FROM_RAM,
    FROM_TR,
    FROM_TRB,
    INCREMENT,
    NEGATE,
    NOP,
    OR,
    SHIFT_LEFT,
    SHIFT_LEFT_FOUR_TIMES,
    SHIFT_LEFT_TWICE,
    SHIFT_RIGHT,
    SUBTRACT,
    SUBTRACT_WITH_BORROW,
    SWAP_HALVES,
    XOR,
    a_part,
    an_operation,
)

LEFT = 0x1234

RIGHT = 0x0F0F

EVERY_OPERATION_GIVES = {
    NOP: 0x1234,
    OR: 0x1F3F,
    AND: 0x0204,
    XOR: 0x1D3B,
    SUBTRACT: 0x0325,
    ADD: 0x2143,
    SUBTRACT_WITH_BORROW: 0x0325,
    ADD_WITH_CARRY: 0x2143,
    DECREMENT: 0x1233,
    INCREMENT: 0x1235,
    NEGATE: 0xEDCB,
    SHIFT_RIGHT: 0x091A,
    SHIFT_LEFT: 0x2468,
    SHIFT_LEFT_TWICE: 0x48D3,
    SHIFT_LEFT_FOUR_TIMES: 0x234F,
    SWAP_HALVES: 0x3412,
}

EVERY_OPERAND_GIVES = {FROM_RAM: 1, FROM_BUS: 2, FROM_M: 3, FROM_N: 4}


def accumulator_after(alu: int, left: int = LEFT, right: int = RIGHT) -> int:
    found = a_part()
    found.registers.a = left
    found.registers.tr = right
    found.stores.program[0] = an_operation(alu=alu, pselect=FROM_BUS, src=FROM_TR)
    found.step()
    return found.registers.word("a")


def added_from(pselect: int) -> int:
    found = a_part()
    found.stores.scratch[0] = 1
    found.registers.trb = 2
    found.registers.m = 3
    found.registers.n = 4
    found.stores.program[0] = an_operation(alu=ADD, pselect=pselect, src=FROM_TRB)
    found.step()
    return found.registers.word("a")


class ArithmeticTest(unittest.TestCase):
    def test_adding_lands_in_the_accumulator_that_was_chosen(self) -> None:
        # Arrange
        found = a_part()
        found.registers.a = 2
        found.registers.tr = 3
        found.stores.program[0] = an_operation(alu=ADD, pselect=FROM_BUS, src=FROM_TR)

        # Act
        found.step()

        # Assert
        self.assertEqual((found.registers.word("a"), found.registers.word("b")), (5, 0))

    def test_and_in_the_other_one_when_that_is_what_was_chosen(self) -> None:
        # Arrange
        found = a_part()
        found.registers.b = 2
        found.registers.tr = 3
        found.stores.program[0] = an_operation(alu=ADD, pselect=FROM_BUS, asl=1, src=FROM_TR)

        # Act
        found.step()

        # Assert
        self.assertEqual((found.registers.word("a"), found.registers.word("b")), (0, 5))

    def test_the_carry_comes_from_the_accumulator_that_was_not_chosen(self) -> None:
        # Arrange
        found = a_part()
        found.registers.tr = 0
        found.flags_b.c = True
        found.stores.program[0] = an_operation(alu=ADD_WITH_CARRY, pselect=FROM_BUS, src=FROM_TR)

        # Act
        found.step()

        # Assert
        self.assertEqual(found.registers.word("a"), 1)

    def test_the_negation_ignores_its_other_operand(self) -> None:
        # Arrange
        left = 0x0F0F

        # Act
        found = accumulator_after(NEGATE, left=left, right=0x1234)

        # Assert
        self.assertEqual(found, 0xF0F0)

    def test_the_byte_swap_exchanges_the_halves(self) -> None:
        # Arrange
        left = 0x1234

        # Act
        found = accumulator_after(SWAP_HALVES, left=left)

        # Assert
        self.assertEqual(found, 0x3412)

    def test_the_arithmetic_shift_keeps_the_sign(self) -> None:
        # Arrange
        left = 0x8000

        # Act
        found = accumulator_after(SHIFT_RIGHT, left=left)

        # Assert
        self.assertEqual(found, 0xC000)

    def test_the_double_shift_fills_from_below(self) -> None:
        # Arrange
        left = 0

        # Act
        found = accumulator_after(SHIFT_LEFT_TWICE, left=left)

        # Assert
        self.assertEqual(found, 3)

    def test_the_quadruple_shift_fills_further(self) -> None:
        # Arrange
        left = 0

        # Act
        found = accumulator_after(SHIFT_LEFT_FOUR_TIMES, left=left)

        # Assert
        self.assertEqual(found, 15)

    def test_decrementing_takes_one_away(self) -> None:
        # Arrange
        left = 5

        # Act
        found = accumulator_after(DECREMENT, left=left)

        # Assert
        self.assertEqual(found, 4)

    def test_incrementing_puts_one_back(self) -> None:
        # Arrange
        left = 5

        # Act
        found = accumulator_after(INCREMENT, left=left)

        # Assert
        self.assertEqual(found, 6)

    def test_an_operation_of_zero_leaves_the_accumulator_and_its_flags_alone(self) -> None:
        # Arrange
        found = a_part()
        found.registers.a = 0x1234
        found.registers.tr = 0x1234
        found.flags_a.z = True
        found.stores.program[0] = an_operation(alu=NOP, pselect=FROM_BUS, src=FROM_TR)

        # Act
        found.step()

        # Assert
        self.assertEqual((found.registers.word("a"), found.flags_a.z), (0x1234, True))

    def test_each_operand_choice_feeds_the_operand_its_field_names(self) -> None:
        # Arrange
        choices = sorted(EVERY_OPERAND_GIVES)

        # Act
        found = {pselect: added_from(pselect) for pselect in choices}

        # Assert
        self.assertEqual(found, EVERY_OPERAND_GIVES)

    def test_each_operation_gives_the_result_its_field_names(self) -> None:
        # Arrange
        operations = sorted(EVERY_OPERATION_GIVES)

        # Act
        found = {alu: accumulator_after(alu) for alu in operations}

        # Assert
        self.assertEqual(found, EVERY_OPERATION_GIVES)


if __name__ == "__main__":
    unittest.main()
