from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import upd7725
from conformance.printed import (
    ADD,
    DECREMENT,
    FROM_BUS,
    FROM_TR,
    INCREMENT,
    OR,
    SHIFT_LEFT,
    SHIFT_RIGHT,
    a_part,
    an_operation,
)

if TYPE_CHECKING:
    from conformance.printed import Part

EVERY_FLAG = 0x3F

OV1 = 0x02

S0 = 0x10

S1 = 0x20


def ready(alu: int, left: int, right: int = 0, flags: int = 0, asl: int = 0) -> Part:
    part = a_part()
    part.registers.a = part.registers.b = left
    part.registers.tr = right
    part.flags_a = upd7725.Flags.of(flags)
    part.flags_b = upd7725.Flags.of(flags)
    part.stores.program[0] = an_operation(alu=alu, pselect=FROM_BUS, asl=asl, src=FROM_TR)
    return part


class ShapeTest(unittest.TestCase):
    def test_a_fresh_set_holds_nothing(self) -> None:
        # Arrange
        found = upd7725.Flags()

        # Act
        word = int(found)

        # Assert
        self.assertEqual(word, 0)

    def test_each_bit_sits_where_the_readme_packs_it(self) -> None:
        # Arrange
        places = {"ov0": 0, "ov1": 1, "z": 2, "c": 3, "s0": 4, "s1": 5}
        held = {name: upd7725.Flags() for name in places}

        # Act
        for name, found in held.items():
            setattr(found, name, True)

        # Assert
        self.assertEqual(
            {name: int(found) for name, found in held.items()},
            {name: 1 << place for name, place in places.items()},
        )

    def test_a_set_reads_back_the_word_it_was_built_from(self) -> None:
        # Arrange
        word = 0x2A

        # Act
        found = upd7725.Flags.of(word)

        # Assert
        self.assertEqual((int(found), found.ov1, found.c, found.s1), (0x2A, True, True, True))

    def test_a_word_wider_than_the_set_keeps_only_the_bits_that_exist(self) -> None:
        # Arrange
        word = 0xFFFF

        # Act
        found = upd7725.Flags.of(word)

        # Assert
        self.assertEqual(int(found), 0x3F)

    def test_a_copy_does_not_share_with_what_it_came_from(self) -> None:
        # Arrange
        first = upd7725.Flags.of(EVERY_FLAG)
        second = first.copy()

        # Act
        second.z = False

        # Assert
        self.assertEqual((int(first), int(second)), (0x3F, 0x3B))

    def test_a_set_prints_the_bits_it_holds(self) -> None:
        # Arrange
        found = upd7725.Flags.of(EVERY_FLAG)

        # Act
        printed = repr(found)

        # Assert
        self.assertEqual(printed, "<Flags ov0 ov1 z c s0 s1>")

    def test_and_says_so_when_it_holds_none(self) -> None:
        # Arrange
        found = upd7725.Flags()

        # Act
        printed = repr(found)

        # Assert
        self.assertEqual(printed, "<Flags none>")


class ArithmeticTest(unittest.TestCase):
    def test_a_result_of_zero_sets_the_zero_bit(self) -> None:
        # Arrange
        part = ready(DECREMENT, 1)

        # Act
        part.step()

        # Assert
        self.assertEqual((part.registers.a, part.flags_a.z), (0, True))

    def test_a_result_with_its_top_bit_set_is_negative(self) -> None:
        # Arrange
        part = ready(OR, 0, 0x8000)

        # Act
        part.step()

        # Assert
        self.assertEqual((part.flags_a.s0, part.flags_a.z), (True, False))

    def test_the_second_sign_follows_the_first_while_no_overflow_is_held(self) -> None:
        # Arrange
        part = ready(ADD, 0, 0x8000)

        # Act
        part.step()

        # Assert
        self.assertEqual((part.flags_a.s0, part.flags_a.s1), (True, True))

    def test_but_a_held_overflow_keeps_it_where_it_was(self) -> None:
        # Arrange
        part = ready(ADD, 0, 0x8000, flags=OV1)

        # Act
        part.step()

        # Assert
        self.assertEqual((part.flags_a.s0, part.flags_a.s1), (True, False))

    def test_an_operation_on_b_records_its_flags_on_b_alone(self) -> None:
        # Arrange
        part = ready(DECREMENT, 1, asl=1)

        # Act
        part.step()

        # Assert
        self.assertEqual((int(part.flags_a), part.flags_b.z), (0, True))


class LogicTest(unittest.TestCase):
    def test_a_logical_operation_resets_both_overflows_and_the_carry(self) -> None:
        # Arrange
        part = ready(OR, 0x1234, 0x0001, flags=EVERY_FLAG)

        # Act
        part.step()

        # Assert
        flags = part.flags_a
        self.assertEqual((flags.ov0, flags.ov1, flags.c), (False, False, False))


class CarryTest(unittest.TestCase):
    def test_adding_two_positives_that_do_not_wrap_carries_nothing(self) -> None:
        # Arrange
        part = ready(ADD, 1, 1)

        # Act
        part.step()

        # Assert
        flags = part.flags_a
        self.assertEqual((part.registers.a, flags.c, flags.ov0), (2, False, False))

    def test_a_sum_that_leaves_the_word_carries(self) -> None:
        # Arrange
        part = ready(ADD, 0xFFFF, 1)

        # Act
        part.step()

        # Assert
        self.assertEqual((part.registers.a, part.flags_a.c), (0, True))

    def test_two_positives_that_land_negative_overflow(self) -> None:
        # Arrange
        part = ready(INCREMENT, 0x7FFF)

        # Act
        part.step()

        # Assert
        self.assertEqual((part.registers.word("a"), part.flags_a.ov0), (0x8000, True))

    def test_a_second_overflow_while_one_is_held_watches_the_two_signs(self) -> None:
        # Arrange
        part = ready(ADD, 0x7FFF, 1, flags=OV1 | S0 | S1)

        # Act
        part.step()

        # Assert
        self.assertTrue(part.flags_a.ov1)

    def test_and_clears_it_when_they_have_parted(self) -> None:
        # Arrange
        part = ready(ADD, 0x7FFF, 1, flags=OV1 | S0)

        # Act
        part.step()

        # Assert
        self.assertFalse(part.flags_a.ov1)

    def test_an_overflow_with_none_held_records_the_new_one(self) -> None:
        # Arrange
        part = ready(ADD, 0x7FFF, 1)

        # Act
        part.step()

        # Assert
        self.assertEqual((part.flags_a.ov0, part.flags_a.ov1), (True, True))


class ShiftTest(unittest.TestCase):
    def test_shifting_right_carries_the_bit_that_fell_off(self) -> None:
        # Arrange
        part = ready(SHIFT_RIGHT, 0x0001, flags=EVERY_FLAG)

        # Act
        part.step()

        # Assert
        flags = part.flags_a
        self.assertEqual((flags.c, flags.ov0, flags.ov1), (True, False, False))

    def test_shifting_left_carries_the_bit_that_fell_off_the_other_end(self) -> None:
        # Arrange
        part = ready(SHIFT_LEFT, 0x8000, flags=EVERY_FLAG)

        # Act
        part.step()

        # Assert
        flags = part.flags_a
        self.assertEqual((flags.c, flags.ov0, flags.ov1), (True, False, False))


if __name__ == "__main__":
    unittest.main()
