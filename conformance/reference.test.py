import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conformance import reference


class WordsTest(unittest.TestCase):
    """What this reference needs a block of words to be."""

    def test_a_plain_list_is_one(self) -> None:
        self.assertIsInstance([0, 0, 0], reference.Words)

    def test_and_so_is_something_that_answers_by_index_without_holding_anything(self) -> None:
        self.assertIsInstance(_Answered(), reference.Words)

    def test_something_that_cannot_be_written_to_is_not(self) -> None:
        self.assertNotIsInstance(_ReadOnly(), reference.Words)

    def test_a_fresh_processor_starts_with_blocks_that_satisfy_it(self) -> None:
        chip = reference.Upd96050()

        for block in (chip.programROM, chip.dataROM, chip.dataRAM):
            self.assertIsInstance(block, reference.Words)


class StandInTest(unittest.TestCase):
    """The stand-ins themselves, since a double nobody drives proves nothing."""

    def test_one_that_answers_by_index_gives_back_what_it_was_asked_for(self) -> None:
        self.assertEqual(_Answered()[3], 3)

    def test_and_says_how_long_it_is(self) -> None:
        self.assertEqual(len(_Answered()), 4)

    def test_and_remembers_a_write(self) -> None:
        held = _Answered()

        held[2] = 9

        self.assertEqual(held.last, (2, 9))

    def test_a_read_only_one_answers_and_measures_but_takes_nothing(self) -> None:
        held = _ReadOnly()

        self.assertEqual((held[1], len(held)), (1, 4))


class _Answered:
    def __len__(self) -> int:
        return 4

    def __getitem__(self, at: int) -> int:
        return at

    def __setitem__(self, at: int, value: int) -> None:
        self.last = (at, value)


class _ReadOnly:
    def __len__(self) -> int:
        return 4

    def __getitem__(self, at: int) -> int:
        return at


class WordTest(unittest.TestCase):
    def test_a_word_of_sixteen_bits_keeps_sixteen(self) -> None:
        self.assertEqual(reference.n16(0x1FFFF), 0xFFFF)

    def test_a_word_of_twenty_four_keeps_twenty_four(self) -> None:
        self.assertEqual(reference.n24(0x1FFFFFF), 0xFFFFFF)

    def test_a_signed_word_takes_the_sign_of_its_top_bit(self) -> None:
        self.assertEqual(reference.i16(0x8000), -0x8000)

    def test_and_leaves_a_small_one_alone(self) -> None:
        self.assertEqual(reference.i16(0x7FFF), 0x7FFF)


class RevisionTest(unittest.TestCase):
    def test_the_smaller_part_has_the_narrower_registers(self) -> None:
        found = reference.Upd96050(reference.UPD7725)

        self.assertEqual(found.regs.pc_mask, 0x7FF)

    def test_and_the_larger_one_reaches_further(self) -> None:
        found = reference.Upd96050(reference.UPD96050)

        self.assertEqual(found.regs.pc_mask, 0x3FFF)

    def test_a_revision_it_does_not_know_is_refused(self) -> None:
        with self.assertRaises(reference.UnknownRevision):
            reference.Upd96050("nonsense")


class StatusTest(unittest.TestCase):
    def test_the_transfer_bit_reads_back_while_the_word_is_wide(self) -> None:
        found = reference.Status()
        found.drs = 1

        self.assertEqual(int(found) >> 12 & 1, 1)

    def test_but_reads_as_clear_once_the_word_is_narrow(self) -> None:
        found = reference.Status()
        found.drs = 1
        found.drc = 1

        self.assertEqual(int(found) >> 12 & 1, 0)


class ConsoleTest(unittest.TestCase):
    def test_a_wide_transfer_hands_the_low_half_back_first(self) -> None:
        found = reference.Upd96050(reference.UPD96050)
        found.regs.dr = 0xBEEF

        self.assertEqual(found.read_dr(), 0xEF)

    def test_and_the_high_half_second(self) -> None:
        found = reference.Upd96050(reference.UPD96050)
        found.regs.dr = 0xBEEF
        found.read_dr()

        self.assertEqual(found.read_dr(), 0xBE)

    def test_a_narrow_transfer_hands_back_one_half_and_stops_asking(self) -> None:
        found = reference.Upd96050(reference.UPD96050)
        found.regs.dr = 0xBEEF
        found.regs.sr.drc = 1
        found.regs.sr.rqm = 1

        self.assertEqual(found.read_dr(), 0xEF)
        self.assertEqual(found.regs.sr.rqm, 0)

    def test_a_wide_write_takes_the_low_half_first(self) -> None:
        found = reference.Upd96050(reference.UPD96050)

        found.write_dr(0x12)

        self.assertEqual(found.regs.dr & 0xFF, 0x12)

    def test_and_the_high_half_of_a_write_second(self) -> None:
        found = reference.Upd96050(reference.UPD96050)

        found.write_dr(0x12)
        found.write_dr(0x34)

        self.assertEqual(found.regs.dr, 0x3412)

    def test_a_narrow_write_takes_one_half_and_stops_asking(self) -> None:
        found = reference.Upd96050(reference.UPD96050)
        found.regs.sr.drc = 1
        found.regs.sr.rqm = 1

        found.write_dr(0x12)

        self.assertEqual(found.regs.sr.rqm, 0)

    def test_the_status_the_console_reads_is_the_top_half_of_the_word(self) -> None:
        found = reference.Upd96050(reference.UPD96050)
        found.regs.sr.rqm = 1

        self.assertEqual(found.read_sr(), 0x80)

    def test_writing_the_status_from_outside_does_nothing(self) -> None:
        found = reference.Upd96050(reference.UPD96050)

        found.write_sr(0xFF)

        self.assertEqual(int(found.regs.sr), 0)

    def test_the_console_reads_the_low_half_of_a_scratch_word_from_the_even_address(self) -> None:
        found = reference.Upd96050(reference.UPD96050)
        found.dataRAM[0] = 0xBEEF

        self.assertEqual(found.read_dp(0), 0xEF)

    def test_and_the_high_half_from_the_odd_one_beside_it(self) -> None:
        found = reference.Upd96050(reference.UPD96050)
        found.dataRAM[0] = 0xBEEF

        self.assertEqual(found.read_dp(1), 0xBE)

    def test_writing_a_half_leaves_the_other_alone(self) -> None:
        found = reference.Upd96050(reference.UPD96050)
        found.dataRAM[0] = 0xBEEF

        found.write_dp(0, 0x12)

        self.assertEqual(found.dataRAM[0], 0xBE12)

    def test_and_the_same_the_other_way_round(self) -> None:
        found = reference.Upd96050(reference.UPD96050)
        found.dataRAM[0] = 0xBEEF

        found.write_dp(1, 0x12)

        self.assertEqual(found.dataRAM[0], 0x12EF)


class ExecutionTest(unittest.TestCase):
    def test_the_counter_moves_on_by_one(self) -> None:
        found = reference.Upd96050(reference.UPD96050)

        found.exec()

        self.assertEqual(found.regs.pc, 1)

    def test_every_form_is_reachable(self) -> None:
        for form in range(4):
            found = reference.Upd96050(reference.UPD96050)
            found.regs.sp = 1
            found.programROM[0] = form << 22

            found.exec()

            self.assertIsInstance(found.regs.pc, int, form)

    def test_the_product_lands_in_the_two_halves_after_every_instruction(self) -> None:
        found = reference.Upd96050(reference.UPD96050)
        found.regs.k = 0x4000
        found.regs.l = 0x4000

        found.exec()

        self.assertEqual(reference.n16(found.regs.m), 0x2000)

    def test_a_load_puts_its_word_where_it_was_told(self) -> None:
        found = reference.Upd96050(reference.UPD96050)
        found.programROM[0] = 3 << 22 | 0x1234 << 6 | 1

        found.exec()

        self.assertEqual(reference.n16(found.regs.a), 0x1234)

    def test_every_source_and_every_destination_is_reachable(self) -> None:
        for src in range(16):
            for dst in range(16):
                found = reference.Upd96050(reference.UPD96050)
                found.programROM[0] = src << 4 | dst

                found.exec()

                self.assertIsInstance(found.regs.pc, int, (src, dst))

    def test_every_operation_is_reachable(self) -> None:
        for alu in range(1, 16):
            for pselect in range(4):
                found = reference.Upd96050(reference.UPD96050)
                found.programROM[0] = pselect << 20 | alu << 16

                found.exec()

                self.assertIsInstance(found.regs.a, int, (alu, pselect))

    def test_every_branch_is_reachable(self) -> None:
        for brch in range(0x200):
            found = reference.Upd96050(reference.UPD96050)
            found.programROM[0] = 2 << 22 | brch << 13 | 0x123 << 2 | 1

            found.exec()

            self.assertIsInstance(found.regs.pc, int, brch)

    def test_a_return_takes_the_way_back_off_the_stack(self) -> None:
        found = reference.Upd96050(reference.UPD96050)
        found.regs.sp = 1
        found.regs.stack[0] = 0x321
        found.programROM[0] = 1 << 22

        found.exec()

        self.assertEqual(found.regs.pc, 0x321)

    def test_every_pointer_step_is_reachable(self) -> None:
        for dpl in range(4):
            for dphm in range(16):
                found = reference.Upd96050(reference.UPD96050)
                found.regs.dp = 0x55
                found.programROM[0] = dpl << 13 | dphm << 9

                found.exec()

                self.assertIsInstance(found.regs.dp, int, (dpl, dphm))


if __name__ == "__main__":
    unittest.main()
