import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conformance import instructions

ROOT = Path(__file__).resolve().parent.parent


class WordTest(unittest.TestCase):
    def test_the_same_address_answers_the_same_word(self) -> None:
        self.assertEqual(instructions.word_at(7, 3), instructions.word_at(7, 3))

    def test_a_different_seed_answers_a_different_one(self) -> None:
        self.assertNotEqual(instructions.word_at(7, 3), instructions.word_at(8, 3))

    def test_and_so_does_a_different_address(self) -> None:
        self.assertNotEqual(instructions.word_at(7, 3), instructions.word_at(7, 4))

    def test_every_word_fits_in_thirty_two_bits(self) -> None:
        for index in range(64):
            self.assertLess(instructions.word_at(3, index), 1 << 32)

    def test_a_word_is_reachable_without_walking_to_it(self) -> None:
        far = instructions.word_at(3, 1 << 20)

        self.assertLess(far, 1 << 32)


class CaseTest(unittest.TestCase):
    def test_a_case_names_a_seed_a_part_and_an_instruction(self) -> None:
        seed, part, opcode = instructions.case_for(0)

        self.assertIsInstance(seed, int)
        self.assertIn(part, (0, 1))
        self.assertLess(opcode, 1 << 24)

    def test_the_same_index_builds_the_same_case(self) -> None:
        self.assertEqual(instructions.case_for(11), instructions.case_for(11))

    def test_every_instruction_form_is_reached(self) -> None:
        forms = {instructions.case_for(index)[2] >> 22 for index in range(instructions.SETTLED)}

        self.assertEqual(forms, {0, 1, 2, 3})

    def test_both_parts_are_reached(self) -> None:
        parts = {instructions.case_for(index)[1] for index in range(instructions.SETTLED)}

        self.assertEqual(parts, {0, 1})

    def test_every_operation_of_the_arithmetic_form_is_reached(self) -> None:
        seen = set()
        for index in range(instructions.SETTLED):
            _, _, opcode = instructions.case_for(index)
            if opcode >> 22 == 0:
                seen.add(opcode >> 16 & 0xF)

        self.assertEqual(seen, set(range(16)))

    def test_every_source_and_destination_pair_is_reached(self) -> None:
        seen = set()
        for index in range(instructions.SETTLED):
            _, _, opcode = instructions.case_for(index)
            if opcode >> 22 == 0:
                seen.add((opcode >> 4 & 0xF, opcode & 0xF))

        self.assertEqual(len(seen), 256)

    def test_every_branch_the_part_has_is_reached(self) -> None:
        seen = set()
        for index in range(instructions.SETTLED):
            _, _, opcode = instructions.case_for(index)
            if opcode >> 22 == 2:
                seen.add(opcode >> 13 & 0x1FF)

        for branch in instructions.NAMED_BRANCHES:
            self.assertIn(branch, seen)

    def test_a_case_past_the_settled_ones_is_still_built(self) -> None:
        seed, _, opcode = instructions.case_for(instructions.SETTLED + 5)

        self.assertIsInstance(seed, int)
        self.assertLess(opcode, 1 << 24)


class ReplayTest(unittest.TestCase):
    def test_replaying_a_case_answers_a_state(self) -> None:
        self.assertEqual(len(instructions.replay(*instructions.case_for(0))), instructions.WIDTH)

    def test_the_same_case_replays_the_same_way(self) -> None:
        case = instructions.case_for(3)

        self.assertEqual(instructions.replay(*case), instructions.replay(*case))

    def test_a_state_is_all_hexadecimal(self) -> None:
        found = instructions.replay(*instructions.case_for(1))

        self.assertEqual(found, found.lower())
        int(found, 16)

    def test_the_narrow_part_keeps_its_counter_inside_its_own_width(self) -> None:
        found = instructions.replay(0x1234, 0, 0)

        self.assertLess(int(found[0:4], 16), 1 << 11)

    def test_and_the_wide_part_reaches_further(self) -> None:
        counters = {int(instructions.replay(seed, 1, 0)[0:4], 16) for seed in range(1, 200)}

        self.assertTrue(any(counter >= 1 << 11 for counter in counters))


class ClaimedCountTest(unittest.TestCase):
    """That the two figures the readme advertises are the ones there are.

    Both were bare claims: the encoding count appeared in no file but the readme,
    and the instruction count appeared in the corpus but nothing compared them.
    A figure nothing derives is a figure that drifts.
    """

    def readme(self) -> str:
        return (ROOT / "README.md").read_text()

    def test_the_readme_advertises_the_number_of_encodings_walked(self) -> None:
        claimed = re.search(r"\*\*([\d,]+)\*\* encodings walked", self.readme())

        assert claimed is not None
        self.assertEqual(
            int(claimed.group(1).replace(",", "")), len(instructions._settled_opcodes())
        )

    def test_and_the_number_of_instructions_the_corpus_holds(self) -> None:
        held = json.loads((ROOT / "conformance" / "corpus.json").read_text())
        claimed = re.search(r"\*\*([\d,]+)\*\* instructions compared", self.readme())

        assert claimed is not None
        self.assertEqual(int(claimed.group(1).replace(",", "")), held["cases"])

    def test_and_says_the_same_number_where_it_says_what_they_settled(self) -> None:
        held = json.loads((ROOT / "conformance" / "corpus.json").read_text())
        claimed = re.search(r"\*\*([\d,]+) instructions, no disagreements\*\*", self.readme())

        assert claimed is not None
        self.assertEqual(int(claimed.group(1).replace(",", "")), held["cases"])


class CorpusTest(unittest.TestCase):
    def test_the_corpus_that_ships_holds_cases(self) -> None:
        self.assertTrue(instructions.load()["cases"])

    def test_the_corpus_says_where_its_answers_came_from(self) -> None:
        self.assertIn("reference", instructions.load())

    def test_a_corpus_can_be_read_from_somewhere_else(self) -> None:
        where = Path(tempfile.mkdtemp()) / "other.json"
        where.write_text(json.dumps({"reference": "x", "cases": 0, "expected": ""}))

        self.assertEqual(instructions.load(where)["cases"], 0)

    def test_every_recorded_state_is_the_width_a_state_has(self) -> None:
        found = instructions.load()

        self.assertEqual(len(instructions.expected_of(found, 0)), instructions.WIDTH)

    def test_the_corpus_records_as_many_states_as_it_claims_cases(self) -> None:
        found = instructions.load()

        self.assertEqual(len(instructions.decoded(found)) // instructions.PACKED, found["cases"])


class ComparisonTest(unittest.TestCase):
    def test_two_identical_states_report_nothing(self) -> None:
        self.assertIsNone(instructions.disagreement("ab", "ab"))

    def test_a_state_that_differs_is_reported_with_both_sides(self) -> None:
        self.assertEqual(instructions.disagreement("ab", "ac"), ("ab", "ac"))


class AgainstCorpusTest(unittest.TestCase):
    def test_the_model_reproduces_every_state_the_reference_left(self) -> None:
        found = instructions.load()
        states = instructions.decoded(found)

        for index in range(found["cases"]):
            expected = states[index * instructions.PACKED : (index + 1) * instructions.PACKED]
            case = instructions.case_for(index)

            self.assertIsNone(
                instructions.disagreement(expected.hex(), instructions.replay(*case)),
                f"case {index}: {case}",
            )


class RunTest(unittest.TestCase):
    def test_a_full_run_reports_clean(self) -> None:
        self.assertEqual(instructions.run([]), 0)

    def test_a_corpus_whose_answers_are_wrong_makes_the_run_fail(self) -> None:
        where = Path(tempfile.mkdtemp()) / "wrong.json"
        where.write_text(
            json.dumps(
                {
                    "reference": "x",
                    "cases": 1,
                    "expected": instructions.encode(["0" * instructions.WIDTH]),
                }
            )
        )

        self.assertEqual(instructions.run(["--corpus", str(where)]), 1)

    def test_a_corpus_of_many_wrong_answers_stops_reporting_after_a_handful(self) -> None:
        where = Path(tempfile.mkdtemp()) / "wrong.json"
        wrong = instructions.REPORT_LIMIT + 3
        where.write_text(
            json.dumps(
                {
                    "reference": "x",
                    "cases": wrong,
                    "expected": instructions.encode(["0" * instructions.WIDTH] * wrong),
                }
            )
        )

        self.assertEqual(instructions.run(["--corpus", str(where)]), 1)

    def test_an_option_it_does_not_know_is_refused(self) -> None:
        with self.assertRaises(instructions.Usage):
            instructions.options(["--nonsense"])

    def test_an_option_with_no_value_is_refused(self) -> None:
        with self.assertRaises(instructions.Usage):
            instructions.options(["--corpus"])

    def test_a_case_count_is_taken_as_a_number(self) -> None:
        self.assertEqual(instructions.options(["--cases", "7"]).cases, 7)


class RecordTest(unittest.TestCase):
    def test_recording_asks_the_reference_for_every_case(self) -> None:
        found = instructions.record(3)

        self.assertEqual(found["cases"], 3)

    def test_and_says_where_the_answers_came_from(self) -> None:
        found = instructions.record(1)

        self.assertIn("reference", found)

    def test_a_recorded_state_is_the_width_a_state_has(self) -> None:
        found = instructions.record(1)

        self.assertEqual(len(instructions.expected_of(found, 0)), instructions.WIDTH)

    def test_recording_writes_the_corpus_where_it_was_asked(self) -> None:
        where = Path(tempfile.mkdtemp()) / "recorded.json"

        answered = instructions.run(["--record", "--corpus", str(where), "--cases", "2"])

        self.assertEqual(answered, 0)
        self.assertEqual(json.loads(where.read_text())["cases"], 2)

    def test_recording_over_states_that_already_exist_is_refused(self) -> None:
        where = Path(tempfile.mkdtemp()) / "recorded.json"
        instructions.run(["--record", "--corpus", str(where), "--cases", "1"])

        with self.assertRaises(instructions.Usage) as raised:
            instructions.run(["--record", "--corpus", str(where), "--cases", "1"])

        self.assertIn("--retake", str(raised.exception))

    def test_and_allowed_when_the_retake_is_deliberate(self) -> None:
        where = Path(tempfile.mkdtemp()) / "recorded.json"
        instructions.run(["--record", "--corpus", str(where), "--cases", "1"])

        answered = instructions.run(
            ["--record", "--retake", "--corpus", str(where), "--cases", "2"]
        )

        self.assertEqual(answered, 0)
        self.assertEqual(json.loads(where.read_text())["cases"], 2)

    def test_the_retake_flag_is_read_from_the_command_line(self) -> None:
        self.assertTrue(instructions.options(["--retake"]).retake)

    def test_and_is_off_when_it_is_not_given(self) -> None:
        self.assertFalse(instructions.options([]).retake)


class EncodingTest(unittest.TestCase):
    def test_a_state_survives_being_written_down_and_read_back(self) -> None:
        state = "0123456789abcdef" * (instructions.WIDTH // 16)
        written = {"expected": instructions.encode([state]), "cases": 1}

        self.assertEqual(instructions.expected_of(written, 0), state)


class EntryTest(unittest.TestCase):
    def test_a_run_from_the_command_line_returns_what_the_run_returned(self) -> None:
        self.assertEqual(instructions.main([]), 0)

    def test_an_option_it_does_not_know_is_reported(self) -> None:
        self.assertEqual(instructions.main(["--nonsense"]), 2)


if __name__ == "__main__":
    unittest.main()
