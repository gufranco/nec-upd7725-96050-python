from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import upd7725
from conformance.printed import a_part, fact

WIDE = "upd96050"

NARROW = "upd7725"


def widest(name: str) -> int:
    bits: int = fact(name)["value"]
    return (1 << bits) - 1


class FetchTest(unittest.TestCase):
    def test_the_counter_moves_on_by_one_instruction(self) -> None:
        # Arrange
        found = a_part()

        # Act
        found.step()

        # Assert
        self.assertEqual(found.registers.pc, 1)

    def test_a_counter_at_the_end_of_the_store_comes_back_to_the_start(self) -> None:
        # Arrange
        found = a_part()
        found.registers.pc = widest("programCounterBits")

        # Act
        found.step()

        # Assert
        self.assertEqual(found.registers.pc, 0)


class RunTest(unittest.TestCase):
    def test_running_takes_as_many_instructions_as_it_was_asked_for(self) -> None:
        # Arrange
        found = a_part()

        # Act
        found.run_for(5)

        # Assert
        self.assertEqual(found.registers.pc, 5)

    def test_running_none_takes_none(self) -> None:
        # Arrange
        found = a_part()

        # Act
        found.run_for(0)

        # Assert
        self.assertEqual(found.registers.pc, 0)


class NarrowPartTest(unittest.TestCase):
    def test_the_smaller_part_has_a_narrower_counter(self) -> None:
        # Arrange
        found = upd7725.Cpu(NARROW, fill=0)

        # Act
        found.registers.pc = 0xFFFF

        # Assert
        self.assertEqual(found.registers.pc, widest("programCounterBits"))

    def test_and_a_narrower_pointer(self) -> None:
        # Arrange
        found = upd7725.Cpu(NARROW, fill=0)

        # Act
        found.registers.dp = 0xFFFF

        # Assert
        self.assertEqual(found.registers.dp, widest("dataPointerBits"))


class PowerOnTest(unittest.TestCase):
    def test_a_newly_built_part_does_not_start_at_zero(self) -> None:
        # Arrange
        model = WIDE

        # Act
        found = upd7725.Cpu(model, fill=0)

        # Assert
        settled = [found.registers.pc, found.registers.a, found.registers.b]
        self.assertNotEqual(settled, [0, 0, 0])

    def test_the_same_seed_gives_the_same_rubbish_twice(self) -> None:
        # Arrange
        one = upd7725.Cpu(WIDE, fill=0, seed=7)

        # Act
        other = upd7725.Cpu(WIDE, fill=0, seed=7)

        # Assert
        self.assertEqual(one.registers.pc, other.registers.pc)

    def test_a_different_seed_gives_different_rubbish(self) -> None:
        # Arrange
        one = upd7725.Cpu(WIDE, fill=0, seed=7)

        # Act
        other = upd7725.Cpu(WIDE, fill=0, seed=8)

        # Assert
        self.assertNotEqual(one.registers.pc, other.registers.pc)

    def test_the_stack_holds_rubbish_too(self) -> None:
        # Arrange
        model = WIDE

        # Act
        found = upd7725.Cpu(model, fill=0)

        # Assert
        self.assertNotEqual(list(found.registers.stack), [0] * len(found.registers.stack))

    def test_a_reset_puts_the_counter_where_the_data_sheet_says(self) -> None:
        # Arrange
        found = upd7725.Cpu(WIDE, fill=0)

        # Act
        found.reset()

        # Assert
        self.assertEqual(found.registers.pc, fact("resetSetsProgramCounterTo")["value"])

    def test_and_returns_the_part_so_it_can_be_built_and_reset_at_once(self) -> None:
        # Arrange
        found = upd7725.Cpu(WIDE, fill=0)

        # Act
        returned = found.reset()

        # Assert
        self.assertIs(returned, found)

    def test_a_reset_leaves_the_accumulators_holding_what_they_held(self) -> None:
        # Arrange
        found = upd7725.Cpu(WIDE, fill=0)
        before = found.registers.a

        # Act
        found.reset()

        # Assert
        self.assertEqual(found.registers.a, before)

    def test_a_reset_costs_the_pulse_the_data_sheet_requires(self) -> None:
        # Arrange
        found = a_part()
        before = found.cycles

        # Act
        found.reset()

        # Assert
        self.assertEqual(found.cycles - before, fact("resetPulseCycles")["value"])


class TallyTest(unittest.TestCase):
    def test_a_step_reports_the_cycle_it_cost(self) -> None:
        # Arrange
        found = a_part()

        # Act
        cost = found.step()

        # Assert
        self.assertEqual(cost, fact("clocksPerInstruction")["value"])

    def test_the_cycle_count_is_cumulative(self) -> None:
        # Arrange
        found = a_part()
        before = found.cycles

        # Act
        found.run_for(4)

        # Assert
        self.assertEqual(found.cycles - before, 4)

    def test_and_survives_a_reset(self) -> None:
        # Arrange
        found = a_part()
        found.run_for(4)
        before = found.cycles

        # Act
        found.reset()

        # Assert
        self.assertGreater(found.cycles, before)

    def test_the_instruction_count_starts_again_at_a_reset(self) -> None:
        # Arrange
        found = a_part()
        found.run_for(4)

        # Act
        found.reset()

        # Assert
        self.assertEqual(found.steps, 0)

    def test_a_budget_reports_what_it_really_spent(self) -> None:
        # Arrange
        found = a_part()

        # Act
        spent = found.run_for(3)

        # Assert
        self.assertEqual(spent, 3)

    def test_a_budget_of_nothing_spends_nothing(self) -> None:
        # Arrange
        found = a_part()

        # Act
        spent = found.run_for(0)

        # Assert
        self.assertEqual(spent, 0)

    def test_every_cycle_passes_through_the_one_place(self) -> None:
        # Arrange
        found = a_part()
        seen: list[int] = []
        before = found.cycles
        found.on_cycle = lambda: seen.append(found.cycles)

        # Act
        found.run_for(3)

        # Assert
        self.assertEqual(seen, [before + 1, before + 2, before + 3])

    def test_a_part_with_no_watcher_still_counts(self) -> None:
        # Arrange
        found = a_part()
        before = found.cycles

        # Act
        found.spend()

        # Assert
        self.assertEqual(found.cycles - before, 1)

    def test_this_part_never_stops_advancing_the_program(self) -> None:
        # Arrange
        found = a_part()

        # Act
        held = found.held()

        # Assert
        self.assertFalse(held)


class BoundedRunTest(unittest.TestCase):
    def test_a_run_stops_when_the_condition_holds(self) -> None:
        # Arrange
        found = a_part()

        # Act
        returned = found.run_until(lambda chip: chip.registers.pc >= 3)

        # Assert
        self.assertIs(returned, found)
        self.assertEqual(found.steps, 3)

    def test_a_condition_already_true_costs_nothing(self) -> None:
        # Arrange
        found = a_part()

        # Act
        found.run_until(lambda chip: True)

        # Assert
        self.assertEqual(found.steps, 0)

    def test_an_unbounded_run_needs_no_limit(self) -> None:
        # Arrange
        found = a_part()

        # Act
        found.run_until(lambda chip: chip.steps >= 4)

        # Assert
        self.assertEqual(found.steps, 4)

    def test_a_condition_that_never_holds_gives_up_rather_than_hanging(self) -> None:
        # Arrange
        found = a_part()

        # Act
        with self.assertRaises(upd7725.RunLimit) as raised:
            found.run_until(lambda chip: False, limit=5)

        # Assert
        self.assertEqual(str(raised.exception), "gave up after 5 instructions at 005")


if __name__ == "__main__":
    unittest.main()
