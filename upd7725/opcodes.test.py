from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import upd7725
from conformance.printed import TO_NOWHERE, a_load

if TYPE_CHECKING:
    from conformance.printed import Part

WORD_REGISTERS = ("a", "b")

PLAIN_REGISTERS = ("tr", "trb", "k", "l", "dr")

LOADED = 0x1234


def disagreeing(chip: Part, named: str, wanted: int) -> list[str]:
    if named in WORD_REGISTERS:
        held = chip.registers.word(named)
    elif named in PLAIN_REGISTERS:
        held = getattr(chip.registers, named)
    else:
        return []
    return [] if held == wanted else [f"{named} holds {held:#06x}"]


def a_part() -> Part:
    return upd7725.Cpu("upd96050", fill=0).reset()


def stepped(word: int) -> Part:
    chip = a_part()
    chip.stores.load_program(word.to_bytes(3, "big"))
    chip.step()
    return chip


class FormTest(unittest.TestCase):
    def test_a_word_with_no_fields_set_moves_nothing_and_computes_nothing(self) -> None:
        # Arrange
        word = 0x000000

        # Act
        found = upd7725.decode(word)

        # Assert
        self.assertEqual(found.text, "nop trb->none")

    def test_a_return_word_carries_nothing_else(self) -> None:
        # Arrange
        word = 0x400000

        # Act
        found = upd7725.decode(word)

        # Assert
        self.assertEqual(found.text, "rt")

    def test_a_load_word_names_its_immediate_and_where_it_goes(self) -> None:
        # Arrange
        word = 0xC00A81

        # Act
        found = upd7725.decode(word)

        # Assert
        self.assertEqual(found.text, "ld $002A,a")

    def test_a_jump_through_the_output_register_has_no_target_to_name(self) -> None:
        # Arrange
        word = 0x800000

        # Act
        found = upd7725.decode(word)

        # Assert
        self.assertEqual(found.text, "jmpso")

    def test_every_word_decodes_to_something(self) -> None:
        # Arrange
        generator = random.Random(20260824)
        words = [generator.randrange(1 << 24) for _ in range(4000)]

        # Act
        texts = [upd7725.decode(word).text for word in words]

        # Assert
        self.assertNotIn("", texts)


class AgreementTest(unittest.TestCase):
    def test_the_named_destination_is_the_one_the_core_writes(self) -> None:
        # Arrange
        words = [a_load(LOADED, destination) for destination in range(16)]

        # Act
        named = [upd7725.decode(word).text.split(",")[-1] for word in words]

        # Assert
        wrong = [
            problem
            for word, name in zip(words, named, strict=True)
            for problem in disagreeing(stepped(word), name, LOADED)
        ]
        self.assertEqual(wrong, [])

    def test_and_the_reader_of_that_names_a_register_holding_the_wrong_thing(self) -> None:
        # Arrange
        chip = a_part()
        chip.registers.a = 0

        # Act
        found = disagreeing(chip, "a", LOADED)

        # Assert
        self.assertEqual(found, ["a holds 0x0000"])

    def test_and_a_load_to_nowhere_leaves_every_register_alone(self) -> None:
        # Arrange
        chip = a_part()
        chip.stores.load_program(a_load(0xFFFF, TO_NOWHERE).to_bytes(3, "big"))
        before = (chip.registers.word("a"), chip.registers.word("b"), chip.registers.tr)

        # Act
        chip.step()

        # Assert
        self.assertEqual(
            (chip.registers.word("a"), chip.registers.word("b"), chip.registers.tr), before
        )


class ReadingTest(unittest.TestCase):
    def test_a_run_of_words_is_read_in_order_from_the_address_given(self) -> None:
        # Arrange
        words = [0x400000, 0x400000]

        # Act
        found = list(upd7725.disassemble(words, address=0x100))

        # Assert
        self.assertEqual([one.address for one in found], [0x100, 0x101])

    def test_each_one_keeps_the_word_it_came_from(self) -> None:
        # Arrange
        words = [0xC00A81]

        # Act
        found = list(upd7725.disassemble(words))

        # Assert
        self.assertEqual(found[0].raw, 0xC00A81)

    def test_an_instruction_describes_itself_when_printed(self) -> None:
        # Arrange
        found = upd7725.decode(0x400000)

        # Act
        printed = repr(found)

        # Assert
        self.assertEqual(printed, "<Instruction 0000 rt>")

    def test_reading_an_empty_program_yields_nothing(self) -> None:
        # Arrange
        words: list[int] = []

        # Act
        found = list(upd7725.disassemble(words))

        # Assert
        self.assertEqual(found, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
