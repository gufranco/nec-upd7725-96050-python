import sys
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from upd7725 import core, errors, models


def a_processor(**options: Any) -> "core.Cpu":
    """A part in a stated starting state, because these are instruction tests.

    Construction scrambles every register, which is what the silicon does and
    what the power-on tests check. An instruction test that started there would
    be asserting against whatever the seed produced, so this settles the part
    first and says so: reset defines the counter, and everything an instruction
    reads is put to a known value here rather than assumed to arrive as one.
    """
    found = core.Cpu(models.describe("upd96050"), fill=0, **options).reset()
    registers = found.registers
    registers.rp = registers.dp = registers.sp = 0
    registers.k = registers.l = registers.m = registers.n = 0
    registers.a = registers.b = 0
    registers.tr = registers.trb = registers.dr = 0
    registers.si = registers.so = 0
    for slot in range(len(registers.stack)):
        registers.stack[slot] = 0
    return found


def an_operation(
    alu: int = 0,
    pselect: int = 0,
    asl: int = 0,
    dpl: int = 0,
    dphm: int = 0,
    rpdcr: int = 0,
    src: int = 0,
    dst: int = 0,
) -> int:
    return (
        pselect << 20 | alu << 16 | asl << 15 | dpl << 13 | dphm << 9 | rpdcr << 8 | src << 4 | dst
    )


def a_load(value: int, dst: int) -> int:
    return 3 << 22 | (value & 0xFFFF) << 6 | dst


def a_jump(branch: int, address: int = 0, bank: int = 0) -> int:
    return 2 << 22 | branch << 13 | address << 2 | bank


class FetchTest(unittest.TestCase):
    def test_the_counter_moves_on_by_one_instruction(self) -> None:
        found = a_processor()

        found.step()

        self.assertEqual(found.registers.pc, 1)

    def test_a_counter_at_the_end_of_the_store_comes_back_to_the_start(self) -> None:
        found = a_processor()
        found.registers.pc = found.registers.counter_mask

        found.step()

        self.assertEqual(found.registers.pc, 0)


class RunTest(unittest.TestCase):
    def test_running_takes_as_many_instructions_as_it_was_asked_for(self) -> None:
        found = a_processor()

        found.run_for(5)

        self.assertEqual(found.registers.pc, 5)

    def test_running_none_takes_none(self) -> None:
        found = a_processor()

        found.run_for(0)

        self.assertEqual(found.registers.pc, 0)


class MoveTest(unittest.TestCase):
    def test_a_load_puts_its_word_where_it_was_told(self) -> None:
        found = a_processor()
        found.stores.program[0] = a_load(0x1234, core.TO_A)

        found.step()

        self.assertEqual(found.registers.word("a"), 0x1234)

    def test_a_load_into_nothing_changes_nothing(self) -> None:
        found = a_processor()
        found.stores.program[0] = a_load(0x1234, core.TO_NOWHERE)

        found.step()

        self.assertEqual(found.registers.word("a"), 0)

    def test_loading_the_data_register_asks_the_console_for_attention(self) -> None:
        found = a_processor()
        found.stores.program[0] = a_load(0x1234, core.TO_DATA)

        found.step()

        self.assertTrue(found.registers.sr.rqm)

    def test_loading_the_status_cannot_reach_the_bits_the_part_owns(self) -> None:
        found = a_processor()
        found.registers.sr.rqm = True
        found.stores.program[0] = a_load(0x0000, core.TO_STATUS)

        found.step()

        self.assertTrue(found.registers.sr.rqm)

    def test_but_reaches_the_ones_it_does_not(self) -> None:
        found = a_processor()
        found.stores.program[0] = a_load(0x0001, core.TO_STATUS)

        found.step()

        self.assertTrue(found.registers.sr.p0)

    def test_one_destination_loads_a_multiplicand_and_fetches_the_other(self) -> None:
        found = a_processor()
        found.registers.rp = 3
        found.stores.table[3] = 0xBEEF
        found.stores.program[0] = a_load(0x1234, core.TO_K_AND_TABLE)

        found.step()

        self.assertEqual(found.registers.word("k"), 0x1234)
        self.assertEqual(found.registers.word("l"), 0xBEEF)

    def test_and_the_mirror_of_it_reads_from_the_far_half_of_the_scratch(self) -> None:
        found = a_processor()
        found.registers.dp = 1
        found.stores.scratch[0x41] = 0xCAFE
        found.stores.program[0] = a_load(0x1234, core.TO_L_AND_SCRATCH)

        found.step()

        self.assertEqual(found.registers.word("l"), 0x1234)
        self.assertEqual(found.registers.word("k"), 0xCAFE)

    def test_a_load_into_the_scratch_writes_where_the_pointer_says(self) -> None:
        found = a_processor()
        found.registers.dp = 7
        found.stores.program[0] = a_load(0x5678, core.TO_SCRATCH)

        found.step()

        self.assertEqual(found.stores.scratch[7], 0x5678)


class SourceTest(unittest.TestCase):
    def test_every_source_is_reachable(self) -> None:
        for source in range(16):
            found = a_processor()
            found.stores.program[0] = an_operation(src=source, dst=core.TO_TR)

            found.step()

            self.assertIsInstance(found.registers.tr, int, source)

    def test_reading_the_data_register_asks_the_console_for_attention(self) -> None:
        found = a_processor()
        found.stores.program[0] = an_operation(src=core.FROM_DATA_AND_ASK, dst=core.TO_TR)

        found.step()

        self.assertTrue(found.registers.sr.rqm)

    def test_reading_it_the_other_way_does_not(self) -> None:
        found = a_processor()
        found.stores.program[0] = an_operation(src=core.FROM_DATA, dst=core.TO_TR)

        found.step()

        self.assertFalse(found.registers.sr.rqm)

    def test_the_saturating_source_answers_the_larger_value_while_the_sign_is_clear(self) -> None:
        found = a_processor()
        found.stores.program[0] = an_operation(src=core.FROM_SATURATION, dst=core.TO_TR)

        found.step()

        self.assertEqual(found.registers.tr, 0x8000)

    def test_and_one_less_once_it_is_set(self) -> None:
        found = a_processor()
        found.flags_a.s1 = True
        found.stores.program[0] = an_operation(src=core.FROM_SATURATION, dst=core.TO_TR)

        found.step()

        self.assertEqual(found.registers.tr, 0x7FFF)


class ArithmeticTest(unittest.TestCase):
    def test_adding_lands_in_the_accumulator_that_was_chosen(self) -> None:
        found = a_processor()
        found.registers.a = 2
        found.stores.program[0] = an_operation(alu=core.ADD, pselect=1, src=core.FROM_TR)
        found.registers.tr = 3

        found.step()

        self.assertEqual(found.registers.word("a"), 5)

    def test_and_in_the_other_one_when_that_is_what_was_chosen(self) -> None:
        found = a_processor()
        found.registers.b = 2
        found.registers.tr = 3
        found.stores.program[0] = an_operation(alu=core.ADD, pselect=1, asl=1, src=core.FROM_TR)

        found.step()

        self.assertEqual(found.registers.word("b"), 5)

    def test_the_carry_comes_from_the_accumulator_that_was_not_chosen(self) -> None:
        found = a_processor()
        found.registers.a = 0
        found.registers.tr = 0
        found.flags_b.c = True
        found.stores.program[0] = an_operation(alu=core.ADD_WITH_CARRY, pselect=1, src=core.FROM_TR)

        found.step()

        self.assertEqual(found.registers.word("a"), 1)

    def test_the_negation_ignores_its_other_operand(self) -> None:
        found = a_processor()
        found.registers.a = 0x0F0F
        found.stores.program[0] = an_operation(alu=core.NEGATE, pselect=1, src=core.FROM_TR)

        found.step()

        self.assertEqual(found.registers.word("a"), 0xF0F0)

    def test_the_byte_swap_exchanges_the_halves(self) -> None:
        found = a_processor()
        found.registers.a = 0x1234
        found.stores.program[0] = an_operation(alu=core.SWAP_HALVES)

        found.step()

        self.assertEqual(found.registers.word("a"), 0x3412)

    def test_the_arithmetic_shift_keeps_the_sign(self) -> None:
        found = a_processor()
        found.registers.a = 0x8000
        found.stores.program[0] = an_operation(alu=core.SHIFT_RIGHT)

        found.step()

        self.assertEqual(found.registers.word("a"), 0xC000)

    def test_the_double_shift_fills_from_below(self) -> None:
        found = a_processor()
        found.registers.a = 0
        found.stores.program[0] = an_operation(alu=core.SHIFT_LEFT_TWICE)

        found.step()

        self.assertEqual(found.registers.word("a"), 3)

    def test_the_quadruple_shift_fills_further(self) -> None:
        found = a_processor()
        found.registers.a = 0
        found.stores.program[0] = an_operation(alu=core.SHIFT_LEFT_FOUR_TIMES)

        found.step()

        self.assertEqual(found.registers.word("a"), 15)

    def test_decrementing_takes_one_away(self) -> None:
        found = a_processor()
        found.registers.a = 5
        found.stores.program[0] = an_operation(alu=core.DECREMENT)

        found.step()

        self.assertEqual(found.registers.word("a"), 4)

    def test_incrementing_puts_one_back(self) -> None:
        found = a_processor()
        found.registers.a = 5
        found.stores.program[0] = an_operation(alu=core.INCREMENT)

        found.step()

        self.assertEqual(found.registers.word("a"), 6)

    def test_an_operation_of_zero_leaves_the_accumulator_alone(self) -> None:
        found = a_processor()
        found.registers.a = 0x1234
        found.stores.program[0] = an_operation(alu=0, pselect=1, src=core.FROM_TR)

        found.step()

        self.assertEqual(found.registers.word("a"), 0x1234)

    def test_every_operand_choice_is_reachable(self) -> None:
        for pselect in range(4):
            found = a_processor()
            found.stores.program[0] = an_operation(alu=core.ADD, pselect=pselect)

            found.step()

            self.assertEqual(found.registers.word("a"), 0, pselect)

    def test_every_operation_is_reachable(self) -> None:
        for alu in range(16):
            found = a_processor()
            found.stores.program[0] = an_operation(alu=alu)

            found.step()

            self.assertIsInstance(found.registers.word("a"), int, alu)


class PointerTest(unittest.TestCase):
    def test_the_low_nibble_of_the_pointer_can_be_stepped_forward(self) -> None:
        found = a_processor()
        found.registers.dp = 0x1F
        found.stores.program[0] = an_operation(dpl=core.POINTER_UP)

        found.step()

        self.assertEqual(found.registers.dp, 0x10)

    def test_and_backward(self) -> None:
        found = a_processor()
        found.registers.dp = 0x10
        found.stores.program[0] = an_operation(dpl=core.POINTER_DOWN)

        found.step()

        self.assertEqual(found.registers.dp, 0x1F)

    def test_and_cleared_without_disturbing_the_rest(self) -> None:
        found = a_processor()
        found.registers.dp = 0x37
        found.stores.program[0] = an_operation(dpl=core.POINTER_CLEAR)

        found.step()

        self.assertEqual(found.registers.dp, 0x30)

    def test_the_high_nibble_is_turned_over_rather_than_set(self) -> None:
        found = a_processor()
        found.registers.dp = 0x30
        found.stores.program[0] = an_operation(dphm=0x1)

        found.step()

        self.assertEqual(found.registers.dp, 0x20)

    def test_a_move_that_writes_the_pointer_leaves_it_where_it_landed(self) -> None:
        found = a_processor()
        found.registers.tr = 0x25
        found.stores.program[0] = an_operation(dpl=core.POINTER_CLEAR, src=core.FROM_TR, dst=4)

        found.step()

        self.assertEqual(found.registers.dp, 0x25)

    def test_the_table_pointer_steps_back_when_it_is_asked_to(self) -> None:
        found = a_processor()
        found.registers.rp = 5
        found.stores.program[0] = an_operation(rpdcr=1)

        found.step()

        self.assertEqual(found.registers.rp, 4)

    def test_but_not_when_the_move_wrote_it(self) -> None:
        found = a_processor()
        found.registers.tr = 9
        found.stores.program[0] = an_operation(rpdcr=1, src=core.FROM_TR, dst=5)

        found.step()

        self.assertEqual(found.registers.rp, 9)


class MultiplyTest(unittest.TestCase):
    def test_the_product_lands_in_the_two_halves_after_every_instruction(self) -> None:
        found = a_processor()
        found.registers.k = 0x4000
        found.registers.l = 0x4000

        found.step()

        self.assertEqual(found.registers.word("m"), 0x2000)
        self.assertEqual(found.registers.word("n"), 0x0000)

    def test_a_negative_multiplicand_is_treated_as_one(self) -> None:
        found = a_processor()
        found.registers.k = -1
        found.registers.l = 0x4000

        found.step()

        self.assertEqual(found.registers.word("m"), 0xFFFF)

    def test_the_low_half_carries_the_bit_the_high_half_shifted_past(self) -> None:
        found = a_processor()
        found.registers.k = 1
        found.registers.l = 1

        found.step()

        self.assertEqual(found.registers.word("n"), 2)


class JumpTest(unittest.TestCase):
    def test_an_unconditional_jump_lands_where_it_was_pointed(self) -> None:
        found = a_processor()
        found.stores.program[0] = a_jump(core.JUMP_LOW, address=0x123, bank=1)

        found.step()

        self.assertEqual(found.registers.pc, 1 << 11 | 0x123)

    def test_the_far_jump_lands_in_the_far_half(self) -> None:
        found = a_processor()
        found.stores.program[0] = a_jump(core.JUMP_HIGH, address=0x123)

        found.step()

        self.assertEqual(found.registers.pc, 0x2000 | 0x123)

    def test_a_call_leaves_the_way_back_on_the_stack(self) -> None:
        found = a_processor()
        found.stores.program[0] = a_jump(core.CALL_LOW, address=0x100)

        found.step()

        self.assertEqual(found.registers.stack[0], 1)
        self.assertEqual(found.registers.sp, 1)

    def test_and_the_far_call_does_the_same(self) -> None:
        found = a_processor()
        found.stores.program[0] = a_jump(core.CALL_HIGH, address=0x100)

        found.step()

        self.assertEqual(found.registers.pc, 0x2000 | 0x100)

    def test_a_jump_through_the_output_register_goes_where_it_points(self) -> None:
        found = a_processor()
        found.registers.so = 0x321
        found.stores.program[0] = a_jump(core.JUMP_THROUGH_OUTPUT)

        found.step()

        self.assertEqual(found.registers.pc, 0x321)

    def test_a_condition_that_does_not_hold_carries_on_to_the_next_instruction(self) -> None:
        found = a_processor()
        found.flags_a.c = False
        found.stores.program[0] = a_jump(core.JUMP_IF_CARRY_A, address=0x100)

        found.step()

        self.assertEqual(found.registers.pc, 1)

    def test_and_one_that_does_takes_the_branch(self) -> None:
        found = a_processor()
        found.flags_a.c = True
        found.stores.program[0] = a_jump(core.JUMP_IF_CARRY_A, address=0x100)

        found.step()

        self.assertEqual(found.registers.pc, 0x100)

    def test_every_condition_the_part_has_is_reachable(self) -> None:
        for branch in core.BRANCHES:
            found = a_processor()
            found.stores.program[0] = a_jump(branch, address=0x100)

            found.step()

            self.assertIsInstance(found.registers.pc, int, branch)

    def test_a_branch_code_the_part_does_not_have_carries_on(self) -> None:
        found = a_processor()
        found.stores.program[0] = a_jump(0x1FF, address=0x100)

        found.step()

        self.assertEqual(found.registers.pc, 1)

    def test_the_pointer_conditions_read_the_low_nibble(self) -> None:
        found = a_processor()
        found.registers.dp = 0x0F
        found.stores.program[0] = a_jump(core.JUMP_IF_POINTER_FULL, address=0x100)

        found.step()

        self.assertEqual(found.registers.pc, 0x100)


class ReturnTest(unittest.TestCase):
    def test_a_return_takes_the_way_back_off_the_stack(self) -> None:
        found = a_processor()
        found.registers.sp = 1
        found.registers.stack[0] = 0x321
        found.stores.program[0] = 1 << 22

        found.step()

        self.assertEqual(found.registers.pc, 0x321)
        self.assertEqual(found.registers.sp, 0)

    def test_and_still_does_everything_a_plain_operation_would(self) -> None:
        found = a_processor()
        found.registers.sp = 1
        found.registers.a = 2
        found.registers.tr = 3
        found.stores.program[0] = 1 << 22 | an_operation(alu=core.ADD, pselect=1, src=core.FROM_TR)

        found.step()

        self.assertEqual(found.registers.word("a"), 5)


class NarrowPartTest(unittest.TestCase):
    def test_the_smaller_part_has_a_narrower_counter(self) -> None:
        found = core.Cpu(models.describe("upd7725"), fill=0)

        found.registers.pc = 0xFFFF

        self.assertEqual(found.registers.pc, 0x7FF)

    def test_and_a_narrower_pointer(self) -> None:
        found = core.Cpu(models.describe("upd7725"), fill=0)

        found.registers.dp = 0xFFFF

        self.assertEqual(found.registers.dp, 0xFF)


class PowerOnTest(unittest.TestCase):
    """That a part arrives holding rubbish, and that a reset is the caller's."""

    def test_a_newly_built_part_does_not_start_at_zero(self) -> None:
        found = core.Cpu(models.describe("upd96050"), fill=0)

        settled = [found.registers.pc, found.registers.a, found.registers.b]

        self.assertNotEqual(settled, [0, 0, 0])

    def test_the_same_seed_gives_the_same_rubbish_twice(self) -> None:
        one = core.Cpu(models.describe("upd96050"), fill=0, seed=7)
        other = core.Cpu(models.describe("upd96050"), fill=0, seed=7)

        self.assertEqual(one.registers.pc, other.registers.pc)

    def test_a_different_seed_gives_different_rubbish(self) -> None:
        one = core.Cpu(models.describe("upd96050"), fill=0, seed=7)
        other = core.Cpu(models.describe("upd96050"), fill=0, seed=8)

        self.assertNotEqual(one.registers.pc, other.registers.pc)

    def test_the_stack_holds_rubbish_too(self) -> None:
        found = core.Cpu(models.describe("upd96050"), fill=0)

        self.assertNotEqual(list(found.registers.stack), [0] * len(found.registers.stack))

    def test_a_reset_puts_the_counter_at_zero(self) -> None:
        found = core.Cpu(models.describe("upd96050"), fill=0)

        found.reset()

        self.assertEqual(found.registers.pc, 0)

    def test_and_returns_the_part_so_it_can_be_built_and_reset_at_once(self) -> None:
        found = core.Cpu(models.describe("upd96050"), fill=0).reset()

        self.assertIsInstance(found, core.Cpu)

    def test_a_reset_leaves_the_accumulators_holding_what_they_held(self) -> None:
        found = core.Cpu(models.describe("upd96050"), fill=0)
        before = found.registers.a

        found.reset()

        self.assertEqual(found.registers.a, before)

    def test_a_reset_costs_the_pulse_the_data_sheet_requires(self) -> None:
        found = a_processor()
        before = found.cycles

        found.reset()

        self.assertEqual(found.cycles - before, 4)


class TallyTest(unittest.TestCase):
    """That the part reports what it spent, the way the family says it must."""

    def test_a_step_reports_the_cycle_it_cost(self) -> None:
        found = a_processor()

        self.assertEqual(found.step(), 1)

    def test_the_cycle_count_is_cumulative(self) -> None:
        found = a_processor()
        before = found.cycles

        found.run_for(4)

        self.assertEqual(found.cycles - before, 4)

    def test_and_survives_a_reset(self) -> None:
        found = a_processor()
        found.run_for(4)
        before = found.cycles

        found.reset()

        self.assertGreater(found.cycles, before)

    def test_the_instruction_count_starts_again_at_a_reset(self) -> None:
        found = a_processor()
        found.run_for(4)

        found.reset()

        self.assertEqual(found.steps, 0)

    def test_a_budget_reports_what_it_really_spent(self) -> None:
        found = a_processor()

        self.assertEqual(found.run_for(3), 3)

    def test_a_budget_of_nothing_spends_nothing(self) -> None:
        found = a_processor()

        self.assertEqual(found.run_for(0), 0)

    def test_every_cycle_passes_through_the_one_place(self) -> None:
        found = a_processor()
        seen: list[int] = []
        before = found.cycles
        found.on_cycle = lambda: seen.append(found.cycles)

        found.run_for(3)

        self.assertEqual(seen, [before + 1, before + 2, before + 3])

    def test_a_part_with_no_watcher_still_counts(self) -> None:
        found = a_processor()
        before = found.cycles

        found.spend()

        self.assertEqual(found.cycles - before, 1)

    def test_this_part_never_stops_advancing_the_program(self) -> None:
        found = a_processor()

        self.assertFalse(found.held())


class BoundedRunTest(unittest.TestCase):
    def test_a_run_stops_when_the_condition_holds(self) -> None:
        found = a_processor()

        returned = found.run_until(lambda chip: chip.registers.pc >= 3)

        self.assertIs(returned, found)
        self.assertEqual(found.steps, 3)

    def test_a_condition_already_true_costs_nothing(self) -> None:
        found = a_processor()

        found.run_until(lambda chip: True)

        self.assertEqual(found.steps, 0)

    def test_an_unbounded_run_needs_no_limit(self) -> None:
        found = a_processor()

        found.run_until(lambda chip: chip.steps >= 4)

        self.assertEqual(found.steps, 4)

    def test_a_condition_that_never_holds_gives_up_rather_than_hanging(self) -> None:
        found = a_processor()

        with self.assertRaises(errors.RunLimit):
            found.run_until(lambda chip: False, limit=5)


class InterruptTest(unittest.TestCase):
    """That the pin is a line the part reads, not a method that acts."""

    def enabled(self) -> "core.Cpu":
        found = a_processor()
        found.registers.sr.ei = True
        return found

    def test_a_request_is_refused_while_the_enable_bit_is_clear(self) -> None:
        found = a_processor()

        self.assertFalse(found.irq())

    def test_and_the_counter_stays_where_it_was(self) -> None:
        found = a_processor()
        before = found.registers.pc

        found.irq()

        self.assertEqual(found.registers.pc, before)

    def test_an_enabled_part_takes_it(self) -> None:
        found = self.enabled()

        self.assertTrue(found.irq())

    def test_and_continues_at_the_address_the_document_names(self) -> None:
        found = self.enabled()

        found.irq()

        self.assertEqual(found.registers.pc, 0x100)

    def test_the_counter_it_was_about_to_run_from_is_pushed(self) -> None:
        found = self.enabled()
        found.registers.pc = 0x123
        slot = found.registers.sp

        found.irq()

        self.assertEqual(found.registers.stack[slot], 0x123)

    def test_taking_it_costs_the_one_cycle_an_instruction_costs(self) -> None:
        found = self.enabled()
        before = found.cycles

        found.irq()

        self.assertEqual(found.cycles - before, 1)

    def test_a_line_already_raised_is_not_a_fresh_request(self) -> None:
        found = self.enabled()
        found.irq()

        self.assertFalse(found.irq())

    def test_but_lowering_it_first_makes_the_next_one_fresh(self) -> None:
        found = self.enabled()
        found.irq()

        found.lower_irq()

        self.assertTrue(found.irq())

    def test_a_refusal_leaves_the_line_raised_as_a_device_would(self) -> None:
        found = a_processor()

        found.irq()

        self.assertTrue(found.irq_line)


if __name__ == "__main__":
    unittest.main()
