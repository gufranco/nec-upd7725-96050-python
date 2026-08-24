import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from upd7725 import errors, memory


class ShapeTest(unittest.TestCase):
    def test_each_store_is_as_long_as_it_was_asked_to_be(self) -> None:
        found = memory.Stores(program_words=2048, table_words=1024, scratch_words=256)

        self.assertEqual(len(found.program), 2048)
        self.assertEqual(len(found.table), 1024)
        self.assertEqual(len(found.scratch), 256)

    def test_a_store_starts_holding_what_it_was_told_to_hold(self) -> None:
        found = memory.Stores(program_words=4, table_words=4, scratch_words=4, fill=0xAB)

        self.assertEqual(found.scratch[0], 0xAB)

    def test_and_starts_clear_when_that_is_what_was_asked(self) -> None:
        found = memory.Stores(program_words=4, table_words=4, scratch_words=4, fill=0)

        self.assertEqual(found.scratch[0], 0)


class WidthTest(unittest.TestCase):
    def test_a_program_word_is_twenty_four_bits_wide(self) -> None:
        found = memory.Stores(program_words=4, table_words=4, scratch_words=4)

        found.program[0] = 0x1FFFFFF

        self.assertEqual(found.program[0], 0xFFFFFF)

    def test_a_table_word_is_sixteen(self) -> None:
        found = memory.Stores(program_words=4, table_words=4, scratch_words=4)

        found.table[0] = 0x1FFFF

        self.assertEqual(found.table[0], 0xFFFF)

    def test_and_so_is_a_scratch_word(self) -> None:
        found = memory.Stores(program_words=4, table_words=4, scratch_words=4)

        found.scratch[0] = 0x1FFFF

        self.assertEqual(found.scratch[0], 0xFFFF)

    def test_a_negative_word_is_kept_as_the_bits_it_stands_for(self) -> None:
        found = memory.Stores(program_words=4, table_words=4, scratch_words=4)

        found.scratch[0] = -1

        self.assertEqual(found.scratch[0], 0xFFFF)


class AddressTest(unittest.TestCase):
    def test_an_address_past_the_end_comes_back_to_the_start(self) -> None:
        found = memory.Stores(program_words=4, table_words=4, scratch_words=4)

        found.scratch[4] = 0x1234

        self.assertEqual(found.scratch[0], 0x1234)

    def test_and_reads_from_there_too(self) -> None:
        found = memory.Stores(program_words=4, table_words=4, scratch_words=4)
        found.scratch[1] = 0x4321

        self.assertEqual(found.scratch[5], 0x4321)

    def test_a_store_says_how_long_it_is(self) -> None:
        found = memory.Stores(program_words=8, table_words=4, scratch_words=4)

        self.assertEqual(len(found.program), 8)


class ByteAccessTest(unittest.TestCase):
    def test_the_console_reads_the_low_half_of_a_scratch_word_first(self) -> None:
        found = memory.Stores(program_words=4, table_words=4, scratch_words=4)
        found.scratch[0] = 0xBEEF

        self.assertEqual(found.read_byte(0), 0xEF)

    def test_and_the_high_half_from_the_odd_address_beside_it(self) -> None:
        found = memory.Stores(program_words=4, table_words=4, scratch_words=4)
        found.scratch[0] = 0xBEEF

        self.assertEqual(found.read_byte(1), 0xBE)

    def test_writing_a_byte_leaves_the_other_half_alone(self) -> None:
        found = memory.Stores(program_words=4, table_words=4, scratch_words=4)
        found.scratch[0] = 0xBEEF

        found.write_byte(0, 0x12)

        self.assertEqual(found.scratch[0], 0xBE12)

    def test_and_the_same_the_other_way_round(self) -> None:
        found = memory.Stores(program_words=4, table_words=4, scratch_words=4)
        found.scratch[0] = 0xBEEF

        found.write_byte(1, 0x12)

        self.assertEqual(found.scratch[0], 0x12EF)


class SourceTest(unittest.TestCase):
    def test_a_word_nothing_wrote_comes_from_the_source(self) -> None:
        found = memory.Store(4, 16, source=lambda at: at * 0x1111)

        self.assertEqual(found[2], 0x2222)

    def test_a_source_word_wider_than_the_store_is_cut_to_fit(self) -> None:
        found = memory.Store(4, 16, source=lambda at: 0x1FFFF)

        self.assertEqual(found[0], 0xFFFF)

    def test_a_word_that_was_written_comes_back_instead(self) -> None:
        found = memory.Store(4, 16, source=lambda at: at)
        found[2] = 0xABCD

        self.assertEqual(found[2], 0xABCD)

    def test_a_store_names_the_words_that_are_not_what_it_started_with(self) -> None:
        found = memory.Store(4, 16, source=lambda at: at)
        found[2] = 0xABCD

        self.assertEqual(found.changed(), {2: 0xABCD})

    def test_writing_a_word_back_the_way_it_was_changes_nothing(self) -> None:
        found = memory.Store(4, 16, source=lambda at: at)
        found[2] = 2

        self.assertEqual(found.changed(), {})

    def test_the_same_holds_for_a_store_that_was_filled_rather_than_sourced(self) -> None:
        found = memory.Store(4, 16, fill=0xAA)
        found[1] = 0xAA
        found[2] = 0xBB

        self.assertEqual(found.changed(), {2: 0xBB})

    def test_a_sourced_store_can_be_handed_to_the_three_together(self) -> None:
        found = memory.Stores(
            program_words=4,
            table_words=4,
            scratch_words=4,
            sources={"scratch": lambda at: 0x1000 + at},
        )

        self.assertEqual(found.scratch[3], 0x1003)


class LoadTest(unittest.TestCase):
    def test_a_program_arrives_three_bytes_to_a_word(self) -> None:
        found = memory.Stores(program_words=2, table_words=1, scratch_words=1)

        found.load_program(bytes([0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC]))

        self.assertEqual(found.program[0], 0x123456)
        self.assertEqual(found.program[1], 0x789ABC)

    def test_a_table_arrives_two_bytes_to_a_word(self) -> None:
        found = memory.Stores(program_words=1, table_words=2, scratch_words=1)

        found.load_table(bytes([0x12, 0x34, 0x56, 0x78]))

        self.assertEqual(found.table[0], 0x1234)
        self.assertEqual(found.table[1], 0x5678)

    def test_a_program_longer_than_the_store_is_refused_rather_than_trimmed(self) -> None:
        found = memory.Stores(program_words=1, table_words=1, scratch_words=1)

        with self.assertRaises(errors.TooLarge):
            found.load_program(bytes(6))

    def test_and_so_is_a_table(self) -> None:
        found = memory.Stores(program_words=1, table_words=1, scratch_words=1)

        with self.assertRaises(errors.TooLarge):
            found.load_table(bytes(4))

    def test_a_program_that_does_not_divide_into_words_is_refused(self) -> None:
        found = memory.Stores(program_words=4, table_words=4, scratch_words=4)

        with self.assertRaises(errors.NotWholeWords):
            found.load_program(bytes(4))

    def test_and_a_table_that_does_not_divide_into_words_either(self) -> None:
        found = memory.Stores(program_words=4, table_words=4, scratch_words=4)

        with self.assertRaises(errors.NotWholeWords):
            found.load_table(bytes(3))

    def test_a_short_program_leaves_the_rest_of_the_store_as_it_was(self) -> None:
        found = memory.Stores(program_words=4, table_words=4, scratch_words=4, fill=0xABCDEF)

        found.load_program(bytes([0, 0, 0]))

        self.assertEqual(found.program[1], 0xABCDEF)

    def test_a_fill_wider_than_the_store_keeps_only_the_bits_that_fit(self) -> None:
        found = memory.Stores(program_words=1, table_words=1, scratch_words=1, fill=0xABCDEF)

        self.assertEqual(found.scratch[0], 0xCDEF)


if __name__ == "__main__":
    unittest.main()
