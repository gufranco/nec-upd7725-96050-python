"""That a part can be driven a cycle at a time, and let go cleanly afterwards.

What is worth pinning here is not the arithmetic. It is that the worker thread
is genuinely suspended between cycles rather than replaying them afterwards,
that a failure inside the part reaches the caller instead of dying quietly on a
thread nobody is watching, and that closing gives the part back untouched.
"""

import sys
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from upd7725 import Clock, ClockClosed, core, models


def a_processor() -> "core.Cpu":
    """A settled part, so a tick advances a program rather than rubbish."""
    return core.Cpu(models.describe("upd96050"), fill=0).reset()


class TickTest(unittest.TestCase):
    def test_a_tick_spends_exactly_one_cycle(self) -> None:
        chip = a_processor()

        before = chip.cycles

        with Clock(chip) as clock:
            clock.tick()

        self.assertEqual((clock.cycles, chip.cycles - before), (1, 1))

    def test_a_tick_reports_the_running_total(self) -> None:
        chip = a_processor()

        with Clock(chip) as clock:
            clock.tick()
            found = clock.tick()

        self.assertEqual(found, 2)

    def test_a_budget_spends_exactly_what_was_asked(self) -> None:
        chip = a_processor()

        with Clock(chip) as clock:
            spent = clock.run_for(7)

        self.assertEqual(spent, 7)

    def test_the_part_advances_one_instruction_per_cycle(self) -> None:
        chip = a_processor()

        with Clock(chip) as clock:
            clock.run_for(4)

        self.assertEqual(chip.registers.pc, 4)

    def test_the_worker_is_suspended_between_cycles(self) -> None:
        chip = a_processor()

        before = chip.cycles

        with Clock(chip) as clock:
            clock.tick()
            resting = chip.cycles - before
            counter = chip.registers.pc

        self.assertEqual((resting, counter), (1, 1))


class IterationTest(unittest.TestCase):
    def test_a_clock_can_be_iterated(self) -> None:
        chip = a_processor()

        with Clock(chip) as clock:
            found = [next(clock) for _ in range(3)]

        self.assertEqual(found, [1, 2, 3])

    def test_iteration_ends_when_the_clock_is_closed(self) -> None:
        chip = a_processor()
        clock = Clock(chip)
        clock.close()

        self.assertEqual(list(clock), [])

    def test_the_clock_is_its_own_iterator(self) -> None:
        chip = a_processor()

        with Clock(chip) as clock:
            self.assertIs(iter(clock), clock)


class ClosingTest(unittest.TestCase):
    def test_a_closed_clock_refuses_to_tick(self) -> None:
        chip = a_processor()
        clock = Clock(chip)
        clock.close()

        with self.assertRaises(ClockClosed):
            clock.tick()

    def test_closing_twice_is_not_an_error(self) -> None:
        chip = a_processor()
        clock = Clock(chip)
        clock.close()

        clock.close()

        self.assertTrue(clock.closed)

    def test_closing_gives_the_part_its_hook_back(self) -> None:
        chip = a_processor()
        watcher: Any = lambda: None  # noqa: E731
        chip.on_cycle = watcher
        clock = Clock(chip)

        clock.close()

        self.assertIs(chip.on_cycle, watcher)


class FailureTest(unittest.TestCase):
    def test_a_failure_inside_the_part_reaches_the_driver(self) -> None:
        chip = a_processor()
        clock = Clock(chip)
        clock.tick()

        def explode() -> None:
            raise ValueError("something went wrong inside an instruction")

        chip.on_cycle = explode
        try:
            with self.assertRaises(ValueError):
                clock.tick()
        finally:
            clock.close()

    def test_and_the_clock_refuses_to_go_on_afterwards(self) -> None:
        chip = a_processor()
        clock = Clock(chip)
        clock.tick()

        def explode() -> None:
            raise ValueError("something went wrong inside an instruction")

        chip.on_cycle = explode
        with self.assertRaises(ValueError):
            clock.tick()

        try:
            with self.assertRaises(ClockClosed):
                clock.tick()
        finally:
            clock.close()


if __name__ == "__main__":
    unittest.main()
