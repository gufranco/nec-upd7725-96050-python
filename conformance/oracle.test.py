import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import instructions
import oracle
import reference


class PreparationTest(unittest.TestCase):
    def test_the_seed_decides_what_every_store_holds(self):
        chip = oracle.prepared(0x1234, 1)

        self.assertEqual(
            chip.dataRAM[7],
            instructions.word_at(0x1234, instructions.AT_SCRATCH + 7) & 0xFFFF,
        )

    def test_and_what_every_register_holds(self):
        chip = oracle.prepared(0x1234, 1)

        self.assertEqual(
            chip.regs.pc, instructions.word_at(0x1234, instructions.AT_REGISTERS) & 0x3FFF
        )

    def test_the_part_decides_how_far_the_counter_reaches(self):
        narrow = oracle.prepared(0x1234, 0)
        wide = oracle.prepared(0x1234, 1)

        self.assertEqual(narrow.regs.pc_mask, 0x7FF)
        self.assertEqual(wide.regs.pc_mask, 0x3FFF)

    def test_the_multiplicands_keep_their_sign(self):
        chip = oracle.prepared(0xFFFF0000, 1)

        self.assertEqual(chip.regs.k, reference.i16(chip.regs.k))

    def test_nothing_starts_clear(self):
        chip = oracle.prepared(0x99, 1)

        self.assertTrue(chip.dataRAM.started(3))
        self.assertTrue(chip.programROM[5])


class SourcedTest(unittest.TestCase):
    def test_a_store_is_as_long_as_the_part_it_stands_for(self):
        chip = oracle.prepared(1, 1)

        self.assertEqual(len(chip.dataRAM), reference.DATA_WORDS)


class AnswerTest(unittest.TestCase):
    def test_an_answer_is_the_width_a_state_has(self):
        self.assertEqual(len(oracle.answer(1, 1, 0)), instructions.WIDTH)

    def test_the_same_case_answers_the_same_way(self):
        self.assertEqual(oracle.answer(5, 0, 0x1234), oracle.answer(5, 0, 0x1234))

    def test_a_scratch_write_is_reported_with_its_address(self):
        seed, part = 7, 1
        chip = oracle.prepared(seed, part)
        where = chip.regs.dp

        found = oracle.answer(seed, part, 3 << 22 | 0xBEEF << 6 | 15)

        self.assertEqual(found[-16:-14], "01")
        self.assertEqual(found[-14:-11], f"{where:03x}")

    def test_a_write_of_what_was_already_there_is_no_change_at_all(self):
        seed, part = 7, 1
        chip = oracle.prepared(seed, part)
        already = chip.dataRAM.started(chip.regs.dp)

        found = oracle.answer(seed, part, 3 << 22 | already << 6 | 15)

        self.assertEqual(found[-16:-14], "00")

    def test_answering_many_cases_answers_one_state_each(self):
        cases = [instructions.case_for(index) for index in range(4)]

        self.assertEqual(len(oracle.answers(cases)), 4)


class AgainstRecordedTest(unittest.TestCase):
    def test_the_transliteration_reproduces_what_the_original_left_behind(self):
        corpus = instructions.load()
        states = instructions.decoded(corpus)

        for index in range(corpus["cases"]):
            expected = states[index * instructions.PACKED : (index + 1) * instructions.PACKED].hex()

            self.assertEqual(
                oracle.answer(*instructions.case_for(index)), expected, f"case {index}"
            )


if __name__ == "__main__":
    unittest.main()
