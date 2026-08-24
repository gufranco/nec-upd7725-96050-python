import sys
import unittest
from collections.abc import Sequence
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conformance import differential
from conformance.instructions import PARTS, case_for


def agreeing(_seed: int, _part: int, _opcode: int) -> str:
    return "same"


def disagreeing_on(index: int) -> Any:
    def answered(seed: int, part: int, opcode: int) -> str:
        return "other" if seed == case_for(index)[0] else "same"

    return answered


class CaseTest(unittest.TestCase):
    """Which case a number stands for, which is what makes a run repeatable."""

    def test_a_number_names_the_same_case_every_time(self) -> None:
        self.assertEqual(case_for(7), case_for(7))

    def test_two_numbers_name_different_cases(self) -> None:
        self.assertNotEqual(case_for(7), case_for(8))

    def test_a_case_names_a_part_the_family_has(self) -> None:
        _seed, part, _opcode = case_for(1_000_000)

        self.assertIn(part, range(len(PARTS)))

    def test_and_an_instruction_word_the_part_could_hold(self) -> None:
        _seed, _part, opcode = case_for(1_000_000)

        self.assertLessEqual(opcode, 0xFFFFFF)

    def test_numbers_past_the_settled_range_still_name_cases(self) -> None:
        far = case_for(50_000_000)

        self.assertEqual(len(far), 3)


class SweepTest(unittest.TestCase):
    """Model against reference, live, over a range of cases."""

    def test_two_that_agree_everywhere_report_nothing(self) -> None:
        found = differential.sweep(3, model=agreeing, reference=agreeing)

        self.assertEqual(found.disagreements, ())
        self.assertTrue(found.agrees)

    def test_and_say_how_many_cases_they_agreed_on(self) -> None:
        found = differential.sweep(3, model=agreeing, reference=agreeing)

        self.assertEqual(found.checked, 3)

    def test_one_case_where_they_differ_is_reported(self) -> None:
        found = differential.sweep(3, model=agreeing, reference=disagreeing_on(1))

        self.assertFalse(found.agrees)
        self.assertEqual(len(found.disagreements), 1)

    def test_and_names_the_case_number_that_produced_it(self) -> None:
        found = differential.sweep(3, model=agreeing, reference=disagreeing_on(2))

        self.assertEqual(found.disagreements[0].index, 2)

    def test_and_carries_the_case_so_it_can_be_run_again_on_its_own(self) -> None:
        found = differential.sweep(3, model=agreeing, reference=disagreeing_on(2))

        self.assertEqual(found.disagreements[0].case, case_for(2))

    def test_and_what_each_side_said(self) -> None:
        found = differential.sweep(3, model=agreeing, reference=disagreeing_on(0))

        self.assertEqual(found.disagreements[0].model, "same")
        self.assertEqual(found.disagreements[0].reference, "other")

    def test_a_run_can_start_from_a_case_other_than_the_first(self) -> None:
        found = differential.sweep(2, first=1, model=agreeing, reference=disagreeing_on(0))

        self.assertTrue(found.agrees)

    def test_a_run_of_no_cases_checks_nothing_and_agrees(self) -> None:
        found = differential.sweep(0, model=agreeing, reference=disagreeing_on(0))

        self.assertEqual(found.checked, 0)
        self.assertTrue(found.agrees)

    def test_a_run_stops_reporting_after_the_limit_but_keeps_counting(self) -> None:
        def always_other(_seed: int, _part: int, _opcode: int) -> str:
            return "other"

        found = differential.sweep(9, model=agreeing, reference=always_other, keep=2)

        self.assertEqual(len(found.disagreements), 2)
        self.assertEqual(found.disagreed, 9)


class BudgetTest(unittest.TestCase):
    """A run bounded by time rather than by a count."""

    def test_a_clock_that_has_run_out_stops_the_sweep(self) -> None:
        ticks = iter([0.0, 0.0, 99.0])

        found = differential.sweep(
            100, model=agreeing, reference=agreeing, seconds=1.0, clock=lambda: next(ticks)
        )

        self.assertEqual(found.checked, 1)

    def test_a_clock_inside_the_budget_does_not(self) -> None:
        found = differential.sweep(
            3, model=agreeing, reference=agreeing, seconds=1.0, clock=lambda: 0.0
        )

        self.assertEqual(found.checked, 3)

    def test_no_budget_means_the_clock_is_never_asked(self) -> None:
        asked: list[int] = []

        def counting() -> float:
            asked.append(1)
            return 0.0

        counting()

        differential.sweep(3, model=agreeing, reference=agreeing, clock=counting)

        self.assertEqual(asked, [1])


class ReportTest(unittest.TestCase):
    def test_a_run_that_agrees_says_how_many_cases_it_compared(self) -> None:
        found = differential.sweep(3, model=agreeing, reference=agreeing)

        self.assertIn("3", " ".join(differential.lines_for(found)))

    def test_and_that_the_two_agreed(self) -> None:
        found = differential.sweep(3, model=agreeing, reference=agreeing)

        self.assertIn("agreed", " ".join(differential.lines_for(found)))

    def test_a_disagreement_names_the_case_and_both_answers(self) -> None:
        found = differential.sweep(3, model=agreeing, reference=disagreeing_on(1))

        lines = " ".join(differential.lines_for(found))

        self.assertIn("case 1", lines)
        self.assertIn("other", lines)

    def test_and_how_to_run_that_one_case_again(self) -> None:
        found = differential.sweep(3, model=agreeing, reference=disagreeing_on(1))

        self.assertIn("--from 1 --cases 1", " ".join(differential.lines_for(found)))

    def test_more_disagreements_than_were_kept_are_still_counted(self) -> None:
        def always_other(_seed: int, _part: int, _opcode: int) -> str:
            return "other"

        found = differential.sweep(9, model=agreeing, reference=always_other, keep=2)

        self.assertIn("7 more", " ".join(differential.lines_for(found)))


class PrintingTest(unittest.TestCase):
    def test_a_disagreement_prints_as_the_case_it_was(self) -> None:
        found = differential.sweep(3, model=agreeing, reference=disagreeing_on(1))

        self.assertIn("case 1", repr(found.disagreements[0]))

    def test_a_comparison_prints_as_what_it_compared(self) -> None:
        found = differential.sweep(3, model=agreeing, reference=disagreeing_on(1))

        self.assertIn("3 cases", repr(found))
        self.assertIn("1 disagreed", repr(found))


class OptionTest(unittest.TestCase):
    def test_a_run_with_no_options_takes_the_defaults(self) -> None:
        chosen = differential.options([])

        self.assertEqual(chosen.first, 0)
        self.assertEqual(chosen.cases, differential.DEFAULT_CASES)
        self.assertIsNone(chosen.seconds)

    def test_a_starting_case_can_be_named(self) -> None:
        self.assertEqual(differential.options(["--from", "42"]).first, 42)

    def test_so_can_a_count(self) -> None:
        self.assertEqual(differential.options(["--cases", "7"]).cases, 7)

    def test_and_a_time_budget(self) -> None:
        self.assertEqual(differential.options(["--seconds", "1.5"]).seconds, 1.5)

    def test_an_unknown_option_is_refused_by_name(self) -> None:
        with self.assertRaises(differential.Usage) as raised:
            differential.options(["--nonsense"])

        self.assertIn("--nonsense", str(raised.exception))

    def test_an_option_with_no_value_is_refused(self) -> None:
        with self.assertRaises(differential.Usage) as raised:
            differential.options(["--cases"])

        self.assertIn("--cases", str(raised.exception))


class EntryTest(unittest.TestCase):
    def _run(self, argv: Sequence[str], **held: Any) -> tuple[int, str]:
        said: list[str] = []
        code = differential.main(argv, say=said.append, **held)
        return code, " ".join(said)

    def test_a_run_where_the_two_agree_passes(self) -> None:
        code, said = self._run(["--cases", "2"], model=agreeing, reference=agreeing)

        self.assertEqual(code, 0)
        self.assertIn("agreed", said)

    def test_a_run_where_they_differ_fails_and_says_where(self) -> None:
        code, said = self._run(["--cases", "3"], model=agreeing, reference=disagreeing_on(1))

        self.assertEqual(code, 1)
        self.assertIn("case 1", said)

    def test_an_unusable_option_is_reported_rather_than_raised(self) -> None:
        code, said = self._run(["--nonsense"], model=agreeing, reference=agreeing)

        self.assertEqual(code, 2)
        self.assertIn("--nonsense", said)


class RealPartTest(unittest.TestCase):
    """The model and the reference themselves, over a handful of real cases.

    Small on purpose: this file's job is the harness, and the sweep that runs for
    long enough to find something is the one the schedule runs. A handful here
    proves the two are actually wired to each other rather than to stand-ins.
    """

    def test_the_model_and_the_reference_agree_on_the_first_cases(self) -> None:
        found = differential.sweep(24)

        self.assertTrue(found.agrees, differential.lines_for(found))

    def test_and_on_cases_far_past_the_settled_range(self) -> None:
        found = differential.sweep(8, first=40_000_000)

        self.assertTrue(found.agrees, differential.lines_for(found))


if __name__ == "__main__":
    unittest.main()
