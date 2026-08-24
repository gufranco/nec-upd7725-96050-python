import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import upd7725
from upd7725 import opcodes

WORD_REGISTERS = ("a", "b")

PLAIN_REGISTERS = ("tr", "trb", "k", "l", "dr")


def disagreeing(chip: upd7725.core.Cpu, named: str, wanted: int) -> list[str]:
    """A complaint when the register the disassembly named does not hold the value.

    Only the destinations that are a single register are checked. The rest write
    somewhere with a side effect of its own, a store or a pointer or the status
    word, and asserting on those would be testing the core rather than the name.
    """
    if named in WORD_REGISTERS:
        held = chip.registers.word(named)
    elif named in PLAIN_REGISTERS:
        held = getattr(chip.registers, named)
    else:
        return []
    return [] if held == wanted else [f"{named} holds {held:#06x}"]


class FormTest(unittest.TestCase):
    def test_a_word_with_no_fields_set_moves_nothing_and_computes_nothing(self) -> None:
        self.assertEqual(opcodes.decode(0x000000).text, "nop trb->none")

    def test_a_return_word_carries_nothing_else(self) -> None:
        self.assertEqual(opcodes.decode(0x400000).text, "rt")

    def test_a_load_word_names_its_immediate_and_where_it_goes(self) -> None:
        self.assertEqual(opcodes.decode(0xC00A81).text, "ld $002A,a")

    def test_a_jump_through_the_output_register_has_no_target_to_name(self) -> None:
        self.assertEqual(opcodes.decode(0x800000).text, "jmpso")

    def test_every_word_decodes_to_something(self) -> None:
        """This part has no undefined encoding, so nothing may raise."""
        generator = random.Random(20260824)

        for _ in range(4000):
            word = generator.randrange(1 << 24)
            self.assertTrue(opcodes.decode(word).text)


class AgreementTest(unittest.TestCase):
    """That the reading and the running name the same thing.

    A disassembler that disagrees with the core is worse than none: it is read
    as authority and it is wrong in exactly the cases somebody is investigating.
    So the destination it names is checked against where the core actually put
    the value, for every destination the field can hold.
    """

    def a_part(self) -> upd7725.core.Cpu:
        chip = upd7725.Cpu("upd96050", fill=0)
        chip.reset()
        return chip

    def test_the_named_destination_is_the_one_the_core_writes(self) -> None:
        wrong = []
        for destination in range(16):
            word = 0xC00000 | 0x1234 << 6 | destination
            named = opcodes.decode(word).text.split(",")[-1]

            chip = self.a_part()
            chip.stores.load_program(word.to_bytes(3, "big"))
            chip.registers.pc = 0
            chip.step()

            wrong.extend(disagreeing(chip, named, 0x1234))

        self.assertEqual(wrong, [])

    def test_and_the_reader_of_that_names_a_register_holding_the_wrong_thing(self) -> None:
        """The check has to be seen failing to be worth running."""
        chip = self.a_part()
        chip.registers.a = 0

        self.assertEqual(disagreeing(chip, "a", 0x1234), ["a holds 0x0000"])

    def test_and_a_load_to_nowhere_leaves_every_register_alone(self) -> None:
        chip = self.a_part()
        chip.stores.load_program((0xC00000 | 0xFFFF << 6 | 0).to_bytes(3, "big"))
        chip.registers.pc = 0
        before = (chip.registers.word("a"), chip.registers.word("b"), chip.registers.tr)

        chip.step()

        self.assertEqual(
            (chip.registers.word("a"), chip.registers.word("b"), chip.registers.tr), before
        )


class ReadingTest(unittest.TestCase):
    def test_a_run_of_words_is_read_in_order_from_the_address_given(self) -> None:
        found = list(opcodes.disassemble([0x400000, 0x400000], address=0x100))

        self.assertEqual([one.address for one in found], [0x100, 0x101])

    def test_each_one_keeps_the_word_it_came_from(self) -> None:
        found = list(opcodes.disassemble([0xC00A81]))

        self.assertEqual(found[0].raw, 0xC00A81)

    def test_an_instruction_describes_itself_when_printed(self) -> None:
        self.assertIn("rt", repr(opcodes.decode(0x400000)))

    def test_reading_an_empty_program_yields_nothing(self) -> None:
        self.assertEqual(list(opcodes.disassemble([])), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
