from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conformance import stack
from conformance.printed import (
    CALL_HIGH,
    CALL_LOW,
    FROM_A,
    JUMP_HIGH,
    JUMP_IF_ZERO_A,
    JUMP_LOW,
    JUMP_THROUGH_OUTPUT,
    TO_STATUS,
    a_jump,
    a_load,
    a_return,
    an_operation,
)

LARGER = "upd96050"

PROGRAM_BYTES = 16384 * 3

TABLE_BYTES = 2048 * 2

INTERRUPT = 0x100


def a_program(placed: dict[int, int]) -> list[int]:
    words = [0] * 16384
    for at, word in placed.items():
        words[at] = word
    return words


def an_image(placed: dict[int, int]) -> bytes:
    body = b"".join(word.to_bytes(3, "big") for word in a_program(placed))
    return body + bytes(TABLE_BYTES)


def a_file(image: bytes) -> str:
    where = Path(tempfile.mkdtemp()) / "image.bin"
    where.write_bytes(image)
    return str(where)


def spinning(at: int) -> int:
    return a_jump(JUMP_LOW, at & 0x7FF, at >> 11 & 0x3)


class DepthTest(unittest.TestCase):
    def test_a_program_that_calls_nothing_uses_no_level(self) -> None:
        # Arrange
        words = a_program({0: spinning(0)})

        # Act
        found = stack.census(words, LARGER)

        # Assert
        self.assertEqual((found.from_reset, found.reached), (0, 1))

    def test_each_nested_call_adds_one_level(self) -> None:
        # Arrange
        words = a_program(
            {
                0: a_jump(CALL_LOW, 0x10),
                1: spinning(1),
                0x10: a_jump(CALL_LOW, 0x20),
                0x11: a_return(),
                0x20: a_jump(CALL_LOW, 0x30),
                0x21: a_return(),
                0x30: a_return(),
            }
        )

        # Act
        found = stack.census(words, LARGER)

        # Assert
        self.assertEqual(found.from_reset, 3)

    def test_both_ways_out_of_a_condition_are_followed(self) -> None:
        # Arrange
        words = a_program(
            {
                0: a_jump(JUMP_IF_ZERO_A, 0x40),
                1: spinning(1),
                0x40: a_jump(CALL_LOW, 0x50),
                0x41: spinning(0x41),
                0x50: a_return(),
            }
        )

        # Act
        found = stack.census(words, LARGER)

        # Assert
        self.assertEqual(found.from_reset, 1)

    def test_a_call_into_the_far_half_lands_there(self) -> None:
        # Arrange
        words = a_program(
            {
                0: a_jump(CALL_HIGH, 0x10),
                1: spinning(1),
                0x2010: a_jump(CALL_LOW, 0x20),
                0x2011: a_return(),
                0x20: a_return(),
            }
        )

        # Act
        found = stack.census(words, LARGER)

        # Assert
        self.assertEqual(found.from_reset, 2)

    def test_a_jump_into_the_far_half_is_followed(self) -> None:
        # Arrange
        words = a_program(
            {0: a_jump(JUMP_HIGH, 0x10), 0x2010: a_jump(CALL_LOW, 0x20), 0x20: a_return()}
        )

        # Act
        found = stack.census(words, LARGER)

        # Assert
        self.assertEqual(found.from_reset, 1)

    def test_the_interrupt_routine_is_measured_on_its_own(self) -> None:
        # Arrange
        words = a_program(
            {
                0: spinning(0),
                INTERRUPT: a_jump(CALL_LOW, 0x110),
                INTERRUPT + 1: a_return(),
                0x110: a_return(),
            }
        )

        # Act
        found = stack.census(words, LARGER)

        # Assert
        self.assertEqual((found.from_interrupt, found.deepest), (1, 0))

    def test_an_enabled_interrupt_stacks_on_the_deepest_point(self) -> None:
        # Arrange
        words = a_program(
            {
                0: a_load(0x0080, TO_STATUS),
                1: a_jump(CALL_LOW, 0x10),
                2: spinning(2),
                0x10: a_return(),
                INTERRUPT: a_return(),
            }
        )

        # Act
        found = stack.census(words, LARGER)

        # Assert
        self.assertEqual((found.enables_interrupts, found.deepest), (True, 2))

    def test_a_status_load_without_the_enable_bit_enables_nothing(self) -> None:
        # Arrange
        words = a_program({0: a_load(0x0001, TO_STATUS), 1: spinning(1)})

        # Act
        found = stack.census(words, LARGER)

        # Assert
        self.assertFalse(found.enables_interrupts)

    def test_a_register_moved_into_the_status_word_may_enable_them(self) -> None:
        # Arrange
        words = a_program({0: an_operation(src=FROM_A, dst=TO_STATUS), 1: spinning(1)})

        # Act
        found = stack.census(words, LARGER)

        # Assert
        self.assertTrue(found.enables_interrupts)

    def test_a_call_to_itself_is_named_rather_than_counted(self) -> None:
        # Arrange
        words = a_program({0: a_jump(CALL_LOW, 0x10), 0x10: a_jump(CALL_LOW, 0x10)})

        # Act
        found = stack.census(words, LARGER)

        # Assert
        self.assertEqual(found.recursive, (0x10,))

    def test_a_jump_through_the_output_register_is_named(self) -> None:
        # Arrange
        words = a_program({0: a_jump(JUMP_THROUGH_OUTPUT)})

        # Act
        found = stack.census(words, LARGER)

        # Assert
        self.assertEqual(found.indirect, (0,))


class ReportTest(unittest.TestCase):
    def test_a_program_within_the_levels_passes(self) -> None:
        # Arrange
        said: list[str] = []
        image = a_file(an_image({0: a_jump(CALL_LOW, 0x10), 1: spinning(1), 0x10: a_return()}))

        # Act
        code = stack.main([image], say=said.append)

        # Assert
        self.assertEqual((code, said[-1]), (0, "  every image stays within 8 levels"))

    def test_one_past_them_fails_and_says_so(self) -> None:
        # Arrange
        said: list[str] = []
        image = a_file(an_image({0: a_jump(CALL_LOW, 0x10), 1: spinning(1), 0x10: a_return()}))

        # Act
        code = stack.main([image], levels=0, say=said.append)

        # Assert
        self.assertEqual(
            (code, said[-1]), (1, "  ! an image needs more than 0 levels or cannot be bounded")
        )

    def test_an_image_it_cannot_bound_fails(self) -> None:
        # Arrange
        said: list[str] = []
        image = a_file(an_image({0: a_jump(JUMP_THROUGH_OUTPUT)}))

        # Act
        code = stack.main([image], say=said.append)

        # Assert
        self.assertEqual(code, 1)

    def test_naming_no_image_is_refused(self) -> None:
        # Arrange
        said: list[str] = []

        # Act
        code = stack.main([], say=said.append)

        # Assert
        self.assertEqual((code, said), (2, ["  nothing to measure: name at least one image"]))

    def test_a_file_of_the_wrong_length_is_refused(self) -> None:
        # Arrange
        said: list[str] = []
        image = a_file(bytes(PROGRAM_BYTES))

        # Act
        code = stack.main([image], say=said.append)

        # Assert
        self.assertEqual(code, 2)

    def test_each_image_is_named_by_its_digest(self) -> None:
        # Arrange
        said: list[str] = []
        image = an_image({0: spinning(0)})

        # Act
        stack.main([a_file(image)], say=said.append)

        # Assert
        self.assertIn(stack.digest(image)[:16], said[0])


if __name__ == "__main__":
    unittest.main()
