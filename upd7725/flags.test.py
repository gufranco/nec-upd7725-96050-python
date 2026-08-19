import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from upd7725 import flags


class ShapeTest(unittest.TestCase):
    def test_a_fresh_set_holds_nothing(self):
        self.assertEqual(int(flags.Flags()), 0)

    def test_each_bit_sits_where_the_part_puts_it(self):
        for name, place in (
            ("ov0", 0),
            ("ov1", 1),
            ("z", 2),
            ("c", 3),
            ("s0", 4),
            ("s1", 5),
        ):
            found = flags.Flags()
            setattr(found, name, True)

            self.assertEqual(int(found), 1 << place, name)

    def test_a_set_reads_back_the_word_it_was_built_from(self):
        self.assertEqual(int(flags.Flags.of(0x2A)), 0x2A)

    def test_a_word_wider_than_the_set_keeps_only_the_bits_that_exist(self):
        self.assertEqual(int(flags.Flags.of(0xFFFF)), 0x3F)

    def test_a_copy_does_not_share_with_what_it_came_from(self):
        first = flags.Flags.of(0x3F)
        second = first.copy()
        second.z = False

        self.assertTrue(first.z)

    def test_a_set_prints_the_bits_it_holds(self):
        printed = repr(flags.Flags.of(0x3F))

        self.assertIn("ov0", printed)
        self.assertIn("s1", printed)

    def test_and_says_so_when_it_holds_none(self):
        self.assertIn("none", repr(flags.Flags()))


class ArithmeticTest(unittest.TestCase):
    def test_a_result_of_zero_sets_the_zero_bit(self):
        found = flags.Flags()

        flags.record_result(found, 0)

        self.assertTrue(found.z)

    def test_a_result_with_its_top_bit_set_is_negative(self):
        found = flags.Flags()

        flags.record_result(found, 0x8000)

        self.assertTrue(found.s0)

    def test_the_second_sign_follows_the_first_while_no_overflow_is_held(self):
        found = flags.Flags()

        flags.record_result(found, 0x8000)

        self.assertTrue(found.s1)

    def test_but_a_held_overflow_freezes_it_where_it_was(self):
        found = flags.Flags.of(0)
        found.ov1 = True
        found.s1 = False

        flags.record_result(found, 0x8000)

        self.assertFalse(found.s1)


class LogicTest(unittest.TestCase):
    def test_a_logical_operation_clears_both_overflows_and_the_carry(self):
        found = flags.Flags.of(0x3F)

        flags.record_logic(found)

        self.assertEqual((found.ov0, found.ov1, found.c), (False, False, False))


class CarryTest(unittest.TestCase):
    def test_adding_two_positives_that_do_not_wrap_carries_nothing(self):
        found = flags.Flags()

        flags.record_addition(found, 1, 1, 2, adding=True)

        self.assertFalse(found.c)
        self.assertFalse(found.ov0)

    def test_a_sum_that_leaves_the_word_carries(self):
        found = flags.Flags()

        flags.record_addition(found, 0xFFFF, 1, 0, adding=True)

        self.assertTrue(found.c)

    def test_two_positives_that_land_negative_overflow(self):
        found = flags.Flags()
        flags.record_result(found, 0x8000)

        flags.record_addition(found, 0x7FFF, 1, 0x8000, adding=True)

        self.assertTrue(found.ov0)

    def test_a_second_overflow_while_one_is_held_watches_the_two_signs(self):
        found = flags.Flags()
        found.ov1 = True
        found.s0 = True
        found.s1 = True

        flags.record_addition(found, 0x7FFF, 1, 0x8000, adding=True)

        self.assertTrue(found.ov1)

    def test_and_clears_it_when_they_have_parted(self):
        found = flags.Flags()
        found.ov1 = True
        found.s0 = True
        found.s1 = False

        flags.record_addition(found, 0x7FFF, 1, 0x8000, adding=True)

        self.assertFalse(found.ov1)

    def test_an_overflow_with_none_held_records_the_new_one(self):
        found = flags.Flags()

        flags.record_addition(found, 0x7FFF, 1, 0x8000, adding=True)

        self.assertTrue(found.ov1)


class ShiftTest(unittest.TestCase):
    def test_shifting_right_carries_the_bit_that_fell_off(self):
        found = flags.Flags.of(0x3F)

        flags.record_right_shift(found, 0x0001)

        self.assertTrue(found.c)
        self.assertFalse(found.ov0)

    def test_shifting_left_carries_the_bit_that_fell_off_the_other_end(self):
        found = flags.Flags.of(0x3F)

        flags.record_left_shift(found, 0x8000)

        self.assertTrue(found.c)
        self.assertFalse(found.ov1)


if __name__ == "__main__":
    unittest.main()
