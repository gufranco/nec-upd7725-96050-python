from __future__ import annotations

import contextlib
import random
import sys
import threading
import unittest
from pathlib import Path
from typing import TYPE_CHECKING, Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import upd7725

if TYPE_CHECKING:
    from conformance.printed import Part

FAILURE = "something went wrong inside an instruction"

BUDGET = 4

PATIENCE_SECONDS = 10.0


def a_processor() -> Part:
    return upd7725.Cpu("upd96050", fill=0).reset()


def explode() -> None:
    raise ValueError(FAILURE)


def stepped(instructions: int) -> tuple[int, int, int]:
    chip = a_processor()
    for _ in range(instructions):
        chip.step()
    return chip.steps, chip.cycles, chip.registers.pc


def within(call: Any) -> tuple[str, Any]:
    outcome: list[tuple[str, Any]] = []

    def attempt() -> None:
        try:
            outcome.append(("returned", call()))
        except Exception as raised:  # noqa: BLE001
            outcome.append(("raised", raised))

    worker = threading.Thread(target=attempt, daemon=True)
    worker.start()
    worker.join(PATIENCE_SECONDS)
    return outcome[0] if outcome else ("still running", None)


PROGRAM_SEED = 7725

PROGRAM_WORDS = 64

RANDOM_INSTRUCTIONS = 24


def a_random_program() -> Part:
    chip = upd7725.Cpu("upd96050", fill=0)
    chip.stores.load_program(random.Random(PROGRAM_SEED).randbytes(PROGRAM_WORDS * 3))
    return chip.reset()


def observed(chip: Part) -> tuple[Any, ...]:
    registers = chip.registers
    names = ("pc", "rp", "dp", "sp", "k", "l", "m", "n", "a", "b", "tr", "trb", "dr", "si", "so")
    scratch = chip.stores.scratch
    return (
        tuple(getattr(registers, name) for name in names),
        tuple(registers.stack),
        int(registers.sr),
        int(chip.flags_a),
        int(chip.flags_b),
        chip.cycles,
        chip.steps,
        tuple(scratch[index] for index in range(len(scratch))),
    )


def after_steps(instructions: int) -> tuple[int, tuple[Any, ...]]:
    chip = a_random_program()
    spent = sum(chip.step() for _ in range(instructions))
    return spent, observed(chip)


def every_prefix_stepped() -> list[tuple[Any, ...]]:
    return [after_steps(count)[1] for count in range(1, RANDOM_INSTRUCTIONS + 1)]


def every_prefix_ticked(closing: bool) -> list[tuple[Any, ...]]:
    return [
        after_ticks(after_steps(count)[0], closing) for count in range(1, RANDOM_INSTRUCTIONS + 1)
    ]


def after_ticks(budget: int, closing: bool) -> tuple[Any, ...]:
    chip = a_random_program()
    clock = upd7725.Clock(chip)
    try:
        clock.run_for(budget)
        if closing:
            clock.close()
        return observed(chip)
    finally:
        clock.close()


class TickTest(unittest.TestCase):
    def a_clock(self, chip: Part) -> upd7725.Clock:
        clock = upd7725.Clock(chip)
        self.addCleanup(clock.close)
        return clock

    def test_a_tick_spends_exactly_one_cycle(self) -> None:
        # Arrange
        chip = a_processor()
        clock = self.a_clock(chip)
        before = chip.cycles

        # Act
        clock.tick()

        # Assert
        self.assertEqual((clock.cycles, chip.cycles - before), (1, 1))

    def test_a_tick_reports_the_running_total(self) -> None:
        # Arrange
        clock = self.a_clock(a_processor())
        clock.tick()

        # Act
        found = clock.tick()

        # Assert
        self.assertEqual(found, 2)

    def test_a_budget_spends_exactly_what_was_asked(self) -> None:
        # Arrange
        chip = a_processor()
        clock = self.a_clock(chip)
        before = chip.cycles

        # Act
        spent = clock.run_for(7)

        # Assert
        self.assertEqual((spent, chip.cycles - before), (7, 7))

    def test_the_part_advances_one_instruction_per_cycle(self) -> None:
        # Arrange
        chip = a_processor()
        clock = self.a_clock(chip)

        # Act
        clock.run_for(4)

        # Assert
        self.assertEqual(chip.registers.pc, 4)

    def test_the_part_is_suspended_between_cycles(self) -> None:
        # Arrange
        chip = a_processor()
        clock = self.a_clock(chip)
        before = chip.cycles

        # Act
        clock.tick()

        # Assert
        self.assertEqual((chip.cycles - before, chip.registers.pc), (1, 1))

    def test_a_clock_names_the_part_it_drives(self) -> None:
        # Arrange
        chip = a_processor()

        # Act
        clock = self.a_clock(chip)

        # Assert
        self.assertEqual((clock.cpu, clock.cycles, clock.closed), (chip, 0, False))


class CountedLikeAStepTest(unittest.TestCase):
    def test_a_clock_counts_the_same_instructions_and_cycles_as_stepping(self) -> None:
        # Arrange
        chip = a_processor()
        clock = upd7725.Clock(chip)
        self.addCleanup(clock.close)

        # Act
        clock.run_for(BUDGET)

        # Assert
        self.assertEqual(
            ((chip.steps, chip.cycles, chip.registers.pc), stepped(BUDGET)), ((4, 8, 4),) * 2
        )

    def test_and_still_does_once_the_clock_is_closed(self) -> None:
        # Arrange
        chip = a_processor()

        # Act
        with upd7725.Clock(chip) as clock:
            clock.run_for(BUDGET)

        # Assert
        self.assertEqual(
            ((chip.steps, chip.cycles, chip.registers.pc), stepped(BUDGET)), ((4, 8, 4),) * 2
        )


class TheLastCycleOfAnInstructionFinishesItTest(unittest.TestCase):
    def test_a_clock_leaves_the_whole_state_the_same_steps_leave(self) -> None:
        # Arrange
        expected = every_prefix_stepped()

        # Act
        found = within(lambda: every_prefix_ticked(closing=False))

        # Assert
        self.assertEqual(found, ("returned", expected))

    def test_and_so_does_a_clock_closed_on_that_cycle(self) -> None:
        # Arrange
        expected = every_prefix_stepped()

        # Act
        found = within(lambda: every_prefix_ticked(closing=True))

        # Assert
        self.assertEqual(found, ("returned", expected))


class IterationTest(unittest.TestCase):
    def test_a_clock_can_be_iterated(self) -> None:
        # Arrange
        clock = upd7725.Clock(a_processor())
        self.addCleanup(clock.close)

        # Act
        found = [next(clock) for _ in range(3)]

        # Assert
        self.assertEqual(found, [1, 2, 3])

    def test_iteration_ends_when_the_clock_is_closed(self) -> None:
        # Arrange
        clock = upd7725.Clock(a_processor())
        clock.close()

        # Act
        found = within(lambda: list(clock))

        # Assert
        self.assertEqual(found, ("returned", []))

    def test_the_clock_is_its_own_iterator(self) -> None:
        # Arrange
        clock = upd7725.Clock(a_processor())
        self.addCleanup(clock.close)

        # Act
        found = iter(clock)

        # Assert
        self.assertIs(found, clock)

    def test_leaving_a_with_block_closes_the_clock(self) -> None:
        # Arrange
        clock = upd7725.Clock(a_processor())

        # Act
        with clock:
            pass

        # Assert
        self.assertTrue(clock.closed)


class ClosingTest(unittest.TestCase):
    def test_a_closed_clock_refuses_to_tick(self) -> None:
        # Arrange
        clock = upd7725.Clock(a_processor())
        clock.close()

        # Act
        kind, raised = within(clock.tick)

        # Assert
        self.assertEqual(
            (kind, type(raised).__name__, str(raised)),
            ("raised", "ClockClosed", "this clock has been closed"),
        )

    def test_closing_twice_is_not_an_error(self) -> None:
        # Arrange
        clock = upd7725.Clock(a_processor())
        clock.close()

        # Act
        clock.close()

        # Assert
        self.assertTrue(clock.closed)

    def test_closing_gives_the_part_its_hook_back(self) -> None:
        # Arrange
        chip = a_processor()
        watcher = [].clear
        chip.on_cycle = watcher
        clock = upd7725.Clock(chip)

        # Act
        clock.close()

        # Assert
        self.assertIs(chip.on_cycle, watcher)


class FailureTest(unittest.TestCase):
    def a_failing_clock(self) -> upd7725.Clock:
        chip = a_processor()
        clock = upd7725.Clock(chip)
        self.addCleanup(clock.close)
        clock.tick()
        chip.on_cycle = explode
        return clock

    def test_a_failure_inside_the_part_reaches_the_driver(self) -> None:
        # Arrange
        clock = self.a_failing_clock()

        # Act
        with self.assertRaises(ValueError) as raised:
            clock.tick()

        # Assert
        self.assertEqual((str(raised.exception), clock.closed), (FAILURE, True))

    def test_and_the_clock_refuses_to_go_on_afterwards(self) -> None:
        # Arrange
        clock = self.a_failing_clock()
        with contextlib.suppress(ValueError):
            clock.tick()

        # Act
        with self.assertRaises(upd7725.ClockClosed) as raised:
            clock.tick()

        # Assert
        self.assertEqual(str(raised.exception), "this clock has been closed")


if __name__ == "__main__":
    unittest.main()
