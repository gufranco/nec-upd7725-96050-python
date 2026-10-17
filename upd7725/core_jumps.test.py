from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import upd7725
from conformance.printed import (
    ADD,
    CALL_HIGH,
    CALL_LOW,
    FROM_BUS,
    FROM_TR,
    JUMP_HIGH,
    JUMP_IF_ASKING,
    JUMP_IF_CARRY_A,
    JUMP_IF_CARRY_B,
    JUMP_IF_INPUT_ACK,
    JUMP_IF_NO_CARRY_A,
    JUMP_IF_NO_CARRY_B,
    JUMP_IF_NO_INPUT_ACK,
    JUMP_IF_NO_OUTPUT_ACK,
    JUMP_IF_NO_OVERFLOW_A0,
    JUMP_IF_NO_OVERFLOW_A1,
    JUMP_IF_NO_OVERFLOW_B0,
    JUMP_IF_NO_OVERFLOW_B1,
    JUMP_IF_NOT_ASKING,
    JUMP_IF_NOT_SIGN_A0,
    JUMP_IF_NOT_SIGN_A1,
    JUMP_IF_NOT_SIGN_B0,
    JUMP_IF_NOT_SIGN_B1,
    JUMP_IF_NOT_ZERO_A,
    JUMP_IF_NOT_ZERO_B,
    JUMP_IF_OUTPUT_ACK,
    JUMP_IF_OVERFLOW_A0,
    JUMP_IF_OVERFLOW_A1,
    JUMP_IF_OVERFLOW_B0,
    JUMP_IF_OVERFLOW_B1,
    JUMP_IF_POINTER_EMPTY,
    JUMP_IF_POINTER_FULL,
    JUMP_IF_POINTER_NOT_EMPTY,
    JUMP_IF_POINTER_NOT_FULL,
    JUMP_IF_SIGN_A0,
    JUMP_IF_SIGN_A1,
    JUMP_IF_SIGN_B0,
    JUMP_IF_SIGN_B1,
    JUMP_IF_ZERO_A,
    JUMP_IF_ZERO_B,
    JUMP_LOW,
    JUMP_THROUGH_OUTPUT,
    a_jump,
    a_return,
    fact,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from conformance.printed import Part

FAR_HALF = 0x2000

TARGET = 0x100

NEXT = 1

FLAG_CONDITIONS = (
    (JUMP_IF_CARRY_A, JUMP_IF_NO_CARRY_A, "flags_a", "c"),
    (JUMP_IF_CARRY_B, JUMP_IF_NO_CARRY_B, "flags_b", "c"),
    (JUMP_IF_ZERO_A, JUMP_IF_NOT_ZERO_A, "flags_a", "z"),
    (JUMP_IF_ZERO_B, JUMP_IF_NOT_ZERO_B, "flags_b", "z"),
    (JUMP_IF_OVERFLOW_A0, JUMP_IF_NO_OVERFLOW_A0, "flags_a", "ov0"),
    (JUMP_IF_OVERFLOW_B0, JUMP_IF_NO_OVERFLOW_B0, "flags_b", "ov0"),
    (JUMP_IF_OVERFLOW_A1, JUMP_IF_NO_OVERFLOW_A1, "flags_a", "ov1"),
    (JUMP_IF_OVERFLOW_B1, JUMP_IF_NO_OVERFLOW_B1, "flags_b", "ov1"),
    (JUMP_IF_SIGN_A0, JUMP_IF_NOT_SIGN_A0, "flags_a", "s0"),
    (JUMP_IF_SIGN_B0, JUMP_IF_NOT_SIGN_B0, "flags_b", "s0"),
    (JUMP_IF_SIGN_A1, JUMP_IF_NOT_SIGN_A1, "flags_a", "s1"),
    (JUMP_IF_SIGN_B1, JUMP_IF_NOT_SIGN_B1, "flags_b", "s1"),
)

STATUS_CONDITIONS = (
    (JUMP_IF_INPUT_ACK, JUMP_IF_NO_INPUT_ACK, "siack"),
    (JUMP_IF_OUTPUT_ACK, JUMP_IF_NO_OUTPUT_ACK, "soack"),
    (JUMP_IF_ASKING, JUMP_IF_NOT_ASKING, "rqm"),
)

POINTER_CONDITIONS = (
    (JUMP_IF_POINTER_EMPTY, JUMP_IF_POINTER_NOT_EMPTY, 0x30, 0x31),
    (JUMP_IF_POINTER_FULL, JUMP_IF_POINTER_NOT_FULL, 0x3F, 0x3E),
)


def a_wide_part() -> Part:
    found = upd7725.Cpu("upd96050", fill=0).reset()
    registers = found.registers
    registers.rp = registers.dp = registers.sp = 0
    registers.k = registers.l = registers.m = registers.n = 0
    registers.a = registers.b = 0
    registers.tr = registers.trb = registers.dr = 0
    registers.si = registers.so = 0
    registers.sr.assign(0)
    for slot in range(len(registers.stack)):
        registers.stack[slot] = 0
    found.flags_a = upd7725.Flags()
    found.flags_b = upd7725.Flags()
    return found


def landing(branch: int, prepare: Callable[[Part], None]) -> int:
    found = a_wide_part()
    prepare(found)
    found.stores.program[0] = a_jump(branch, address=TARGET)
    found.step()
    return found.registers.pc


def every_condition() -> list[tuple[int, Callable[[Part], None], int]]:
    found: list[tuple[int, Callable[[Part], None], int]] = []
    for taken, refused, owner, name in FLAG_CONDITIONS:
        for value in (True, False):

            def holding(part: Part, owner: str = owner, name: str = name, v: bool = value) -> None:
                setattr(getattr(part, owner), name, v)

            found.append((taken, holding, TARGET if value else NEXT))
            found.append((refused, holding, NEXT if value else TARGET))
    for taken, refused, name in STATUS_CONDITIONS:
        for value in (True, False):

            def signalled(part: Part, name: str = name, v: bool = value) -> None:
                setattr(part.registers.sr, name, v)

            found.append((taken, signalled, TARGET if value else NEXT))
            found.append((refused, signalled, NEXT if value else TARGET))
    for taken, refused, meets, misses in POINTER_CONDITIONS:
        for pointer, holds in ((meets, True), (misses, False)):

            def pointing(part: Part, at: int = pointer) -> None:
                part.registers.dp = at

            found.append((taken, pointing, TARGET if holds else NEXT))
            found.append((refused, pointing, NEXT if holds else TARGET))
    return found


def left_alone(part: Part) -> None:
    part.registers.sr.assign(0)


class JumpTest(unittest.TestCase):
    def test_an_unconditional_jump_lands_where_it_was_pointed(self) -> None:
        # Arrange
        found = a_wide_part()
        found.stores.program[0] = a_jump(JUMP_LOW, address=0x122, bank=1)

        # Act
        found.step()

        # Assert
        self.assertEqual(found.registers.pc, 0x0922)

    def test_the_far_jump_lands_in_the_far_half(self) -> None:
        # Arrange
        found = a_wide_part()
        found.stores.program[0] = a_jump(JUMP_HIGH, address=0x123)

        # Act
        found.step()

        # Assert
        self.assertEqual(found.registers.pc, FAR_HALF | 0x123)

    def test_a_call_leaves_the_way_back_on_the_stack(self) -> None:
        # Arrange
        found = a_wide_part()
        found.stores.program[0] = a_jump(CALL_LOW, address=0x100)

        # Act
        found.step()

        # Assert
        self.assertEqual(
            (found.registers.pc, found.registers.stack[0], found.registers.sp), (0x100, 1, 1)
        )

    def test_and_the_far_call_does_the_same(self) -> None:
        # Arrange
        found = a_wide_part()
        found.stores.program[0] = a_jump(CALL_HIGH, address=0x100)

        # Act
        found.step()

        # Assert
        self.assertEqual(
            (found.registers.pc, found.registers.stack[0], found.registers.sp),
            (FAR_HALF | 0x100, 1, 1),
        )

    def test_a_jump_through_the_output_register_goes_where_it_points(self) -> None:
        # Arrange
        found = a_wide_part()
        found.registers.so = 0x321
        found.stores.program[0] = a_jump(JUMP_THROUGH_OUTPUT)

        # Act
        found.step()

        # Assert
        self.assertEqual(found.registers.pc, 0x321)

    def test_a_condition_that_does_not_hold_carries_on_to_the_next_instruction(self) -> None:
        # Arrange
        found = a_wide_part()
        found.stores.program[0] = a_jump(JUMP_IF_CARRY_A, address=TARGET)

        # Act
        found.step()

        # Assert
        self.assertEqual(found.registers.pc, NEXT)

    def test_and_one_that_does_takes_the_branch(self) -> None:
        # Arrange
        found = a_wide_part()
        found.flags_a.c = True
        found.stores.program[0] = a_jump(JUMP_IF_CARRY_A, address=TARGET)

        # Act
        found.step()

        # Assert
        self.assertEqual(found.registers.pc, TARGET)

    def test_every_condition_the_part_has_branches_exactly_when_it_holds(self) -> None:
        # Arrange
        cases = every_condition()

        # Act
        found = [landing(branch, prepare) for branch, prepare, _ in cases]

        # Assert
        self.assertEqual(found, [expected for _, _, expected in cases])

    def test_a_branch_code_the_part_does_not_have_carries_on(self) -> None:
        # Arrange
        branch = 0x1FF

        # Act
        found = landing(branch, left_alone)

        # Assert
        self.assertEqual(found, NEXT)

    def test_the_pointer_conditions_read_only_the_low_nibble(self) -> None:
        # Arrange
        found = a_wide_part()
        found.registers.dp = 0x7F
        found.stores.program[0] = a_jump(JUMP_IF_POINTER_FULL, address=TARGET)

        # Act
        found.step()

        # Assert
        self.assertEqual(found.registers.pc, TARGET)


class ReturnTest(unittest.TestCase):
    def test_a_return_takes_the_way_back_off_the_stack(self) -> None:
        # Arrange
        found = a_wide_part()
        found.registers.sp = 1
        found.registers.stack[0] = 0x321
        found.stores.program[0] = a_return()

        # Act
        found.step()

        # Assert
        self.assertEqual((found.registers.pc, found.registers.sp), (0x321, 0))

    def test_and_still_does_everything_a_plain_operation_would(self) -> None:
        # Arrange
        found = a_wide_part()
        found.registers.sp = 1
        found.registers.a = 2
        found.registers.tr = 3
        found.stores.program[0] = a_return(alu=ADD, pselect=FROM_BUS, src=FROM_TR)

        # Act
        found.step()

        # Assert
        self.assertEqual(found.registers.word("a"), 5)


class InterruptTest(unittest.TestCase):
    def enabled(self) -> Part:
        found = a_wide_part()
        found.registers.sr.ei = True
        return found

    def test_a_request_is_refused_while_the_enable_bit_is_clear(self) -> None:
        # Arrange
        found = a_wide_part()

        # Act
        taken = found.irq()

        # Assert
        self.assertFalse(taken)

    def test_and_the_counter_stays_where_it_was(self) -> None:
        # Arrange
        found = a_wide_part()
        before = found.registers.pc

        # Act
        found.irq()

        # Assert
        self.assertEqual(found.registers.pc, before)

    def test_an_enabled_part_takes_it(self) -> None:
        # Arrange
        found = self.enabled()

        # Act
        taken = found.irq()

        # Assert
        self.assertTrue(taken)

    def test_and_continues_at_the_address_the_document_names(self) -> None:
        # Arrange
        found = self.enabled()

        # Act
        found.irq()

        # Assert
        self.assertEqual(found.registers.pc, fact("interruptVector")["value"])

    def test_the_counter_it_was_about_to_run_from_is_pushed(self) -> None:
        # Arrange
        found = self.enabled()
        found.registers.pc = 0x123

        # Act
        found.irq()

        # Assert
        self.assertEqual((found.registers.stack[0], found.registers.sp), (0x123, 1))

    def test_taking_it_costs_the_one_cycle_an_instruction_costs(self) -> None:
        # Arrange
        found = self.enabled()
        before = found.cycles

        # Act
        found.irq()

        # Assert
        self.assertEqual(found.cycles - before, fact("clocksPerInstruction")["value"])

    def test_a_line_already_raised_is_not_a_fresh_request(self) -> None:
        # Arrange
        found = self.enabled()
        found.irq()

        # Act
        taken = found.irq()

        # Assert
        self.assertFalse(taken)

    def test_but_lowering_it_first_makes_the_next_one_fresh(self) -> None:
        # Arrange
        found = self.enabled()
        found.irq()
        found.lower_irq()

        # Act
        taken = found.irq()

        # Assert
        self.assertTrue(taken)

    def test_a_refusal_leaves_the_line_raised_as_a_device_would(self) -> None:
        # Arrange
        found = a_wide_part()

        # Act
        found.irq()

        # Assert
        self.assertTrue(found.irq_line)


if __name__ == "__main__":
    unittest.main()
