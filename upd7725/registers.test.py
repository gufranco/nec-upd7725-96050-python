import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from upd7725 import registers


class StatusTest(unittest.TestCase):
    def test_a_fresh_status_holds_nothing(self):
        self.assertEqual(int(registers.Status()), 0)

    def test_each_bit_sits_where_the_part_puts_it(self):
        for name, place in (
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
        ):
            found = registers.Status()
            setattr(found, name, True)

            self.assertEqual(int(found), 1 << place, name)

    def test_the_transfer_bit_reads_back_while_the_word_is_wide(self):
        found = registers.Status()
        found.drs = True

        self.assertEqual(int(found) & 1 << 12, 1 << 12)

    def test_but_reads_as_clear_once_the_word_is_narrow(self):
        found = registers.Status()
        found.drs = True
        found.drc = True

        self.assertEqual(int(found) & 1 << 12, 0)

    def test_a_status_takes_every_bit_the_part_defines(self):
        defined = sum(1 << place for _, place in registers.STATUS_PLACES)
        found = registers.Status()

        found.assign(0xFFFF)

        self.assertEqual(int(found), defined)

    def test_the_bits_between_the_named_ones_are_not_kept(self):
        found = registers.Status()

        found.assign(0x007C)

        self.assertEqual(int(found), 0)

    def test_the_acknowledgements_are_not_part_of_the_word(self):
        found = registers.Status()
        found.siack = True
        found.soack = True

        self.assertEqual(int(found), 0)

    def test_a_status_prints_the_bits_it_holds(self):
        found = registers.Status()
        found.rqm = True

        self.assertIn("rqm", repr(found))

    def test_and_says_so_when_it_holds_none(self):
        self.assertIn("none", repr(registers.Status()))


class WidthTest(unittest.TestCase):
    def test_a_counter_keeps_only_as_many_bits_as_it_has(self):
        found = registers.Registers(counter_bits=11, table_bits=10, pointer_bits=8)

        found.pc = 0xFFFF

        self.assertEqual(found.pc, 0x7FF)

    def test_each_of_the_three_has_its_own_width(self):
        found = registers.Registers(counter_bits=14, table_bits=11, pointer_bits=11)

        found.pc = 0xFFFF
        found.rp = 0xFFFF
        found.dp = 0xFFFF

        self.assertEqual((found.pc, found.rp, found.dp), (0x3FFF, 0x7FF, 0x7FF))

    def test_a_counter_that_runs_past_its_end_comes_back_to_the_start(self):
        found = registers.Registers(counter_bits=11, table_bits=10, pointer_bits=8)
        found.pc = 0x7FF

        found.pc += 1

        self.assertEqual(found.pc, 0)


class SignedTest(unittest.TestCase):
    def test_a_multiplicand_takes_the_sign_of_the_word_it_is_given(self):
        found = registers.Registers(counter_bits=14, table_bits=11, pointer_bits=11)

        found.k = 0xFFFF

        self.assertEqual(found.k, -1)

    def test_and_reads_back_unsigned_when_asked_that_way(self):
        found = registers.Registers(counter_bits=14, table_bits=11, pointer_bits=11)
        found.k = -1

        self.assertEqual(found.word("k"), 0xFFFF)

    def test_every_signed_register_behaves_the_same_way(self):
        found = registers.Registers(counter_bits=14, table_bits=11, pointer_bits=11)

        for name in registers.SIGNED:
            setattr(found, name, 0x8000)

            self.assertEqual(getattr(found, name), -0x8000, name)


class AttributeTest(unittest.TestCase):
    def test_a_name_no_register_has_is_refused(self):
        found = registers.Registers(counter_bits=14, table_bits=11, pointer_bits=11)

        self.assertRaises(AttributeError, lambda: found.nonsense)


class StackTest(unittest.TestCase):
    def test_the_stack_is_as_deep_as_the_part_makes_it(self):
        found = registers.Registers(counter_bits=14, table_bits=11, pointer_bits=11)

        self.assertEqual(len(found.stack), registers.STACK_DEPTH)

    def test_the_stack_pointer_wraps_within_its_own_nibble(self):
        found = registers.Registers(counter_bits=14, table_bits=11, pointer_bits=11)
        found.sp = registers.STACK_DEPTH - 1

        found.sp += 1

        self.assertEqual(found.sp, 0)


if __name__ == "__main__":
    unittest.main()
