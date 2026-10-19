from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conformance.printed import (
    FROM_A,
    FROM_B,
    FROM_DATA,
    FROM_DATA_AND_ASK,
    FROM_K,
    FROM_L,
    FROM_POINTER,
    FROM_SATURATION,
    FROM_SCRATCH,
    FROM_SERIAL_HIGH,
    FROM_SERIAL_LOW,
    FROM_STATUS,
    FROM_TABLE,
    FROM_TABLE_POINTER,
    FROM_TR,
    FROM_TRB,
    POINTER_CLEAR,
    POINTER_DOWN,
    POINTER_UP,
    TO_A,
    TO_B,
    TO_DATA,
    TO_K,
    TO_K_AND_TABLE,
    TO_L,
    TO_L_AND_SCRATCH,
    TO_NOWHERE,
    TO_POINTER,
    TO_SCRATCH,
    TO_SERIAL_HIGH,
    TO_SERIAL_LOW,
    TO_STATUS,
    TO_TABLE_POINTER,
    TO_TR,
    TO_TRB,
    a_load,
    a_part,
    an_operation,
)

if TYPE_CHECKING:
    from conformance.printed import Part


EVERY_SOURCE_READS = {
    FROM_TRB: 0x1111,
    FROM_A: 0x2222,
    FROM_B: 0x3333,
    FROM_TR: 0x4444,
    FROM_POINTER: 0x55,
    FROM_TABLE_POINTER: 0x66,
    FROM_TABLE: 0x7777,
    FROM_SATURATION: 0x8000,
    FROM_DATA_AND_ASK: 0x9999,
    FROM_DATA: 0x9999,
    FROM_STATUS: 0x0003,
    FROM_SERIAL_HIGH: 0xAAAA,
    FROM_SERIAL_LOW: 0x5555,
    FROM_K: 0xBBBB,
    FROM_L: 0xCCCC,
    FROM_SCRATCH: 0xDDDD,
}

EVERY_DESTINATION_HOLDS = {
    TO_A: ("a", 0x1234),
    TO_B: ("b", 0x1234),
    TO_TR: ("tr", 0x1234),
    TO_POINTER: ("dp", 0x34),
    TO_TABLE_POINTER: ("rp", 0x234),
    TO_SERIAL_LOW: ("so", 0x1234),
    TO_SERIAL_HIGH: ("so", 0x1234),
    TO_K: ("k", 0x1234),
    TO_L: ("l", 0x1234),
    TO_TRB: ("trb", 0x1234),
}


def landed_in(destination: int) -> int:
    found = a_part()
    found.stores.program[0] = a_load(0x1234, destination)
    found.step()
    name = EVERY_DESTINATION_HOLDS[destination][0]
    return int(getattr(found.registers, name)) & 0xFFFF


def holding_a_distinct_word_everywhere() -> Part:
    found = a_part()
    registers = found.registers
    registers.trb = 0x1111
    registers.a = 0x2222
    registers.b = 0x3333
    registers.tr = 0x4444
    registers.dp = 0x55
    registers.rp = 0x66
    found.stores.table[0x66] = 0x7777
    registers.dr = 0x9999
    registers.sr.assign(0x0003)
    registers.si = 0xAAAA
    registers.k = 0xBBBB
    registers.l = 0xCCCC
    found.stores.scratch[0x55] = 0xDDDD
    return found


def moved_by(source: int) -> int:
    found = holding_a_distinct_word_everywhere()
    found.stores.program[0] = an_operation(src=source, dst=TO_TR)
    found.step()
    return found.registers.tr


class MoveTest(unittest.TestCase):
    def test_a_load_puts_its_word_where_it_was_told(self) -> None:
        # Arrange
        found = a_part()
        found.stores.program[0] = a_load(0x1234, TO_A)

        # Act
        found.step()

        # Assert
        self.assertEqual(found.registers.word("a"), 0x1234)

    def test_every_destination_receives_the_word_at_its_own_width(self) -> None:
        # Arrange
        destinations = sorted(EVERY_DESTINATION_HOLDS)

        # Act
        found = {destination: landed_in(destination) for destination in destinations}

        # Assert
        self.assertEqual(found, {key: value for key, (_, value) in EVERY_DESTINATION_HOLDS.items()})

    def test_a_load_into_nothing_changes_nothing(self) -> None:
        # Arrange
        found = a_part()
        found.stores.program[0] = a_load(0x1234, TO_NOWHERE)

        # Act
        found.step()

        # Assert
        self.assertEqual((found.registers.word("a"), found.registers.word("b")), (0, 0))

    def test_loading_the_data_register_asks_the_host_for_attention(self) -> None:
        # Arrange
        found = a_part()
        found.stores.program[0] = a_load(0x1234, TO_DATA)

        # Act
        found.step()

        # Assert
        self.assertEqual((found.registers.dr, found.registers.sr.rqm), (0x1234, True))

    def test_loading_the_status_cannot_reach_the_bits_the_part_owns(self) -> None:
        # Arrange
        found = a_part()
        found.registers.sr.rqm = True
        found.stores.program[0] = a_load(0x0000, TO_STATUS)

        # Act
        found.step()

        # Assert
        self.assertTrue(found.registers.sr.rqm)

    def test_but_reaches_the_ones_it_does_not(self) -> None:
        # Arrange
        found = a_part()
        found.stores.program[0] = a_load(0x0001, TO_STATUS)

        # Act
        found.step()

        # Assert
        self.assertTrue(found.registers.sr.p0)

    def test_one_destination_loads_a_multiplicand_and_fetches_the_other(self) -> None:
        # Arrange
        found = a_part()
        found.registers.rp = 3
        found.stores.table[3] = 0xBEEF
        found.stores.program[0] = a_load(0x1234, TO_K_AND_TABLE)

        # Act
        found.step()

        # Assert
        self.assertEqual((found.registers.word("k"), found.registers.word("l")), (0x1234, 0xBEEF))

    def test_and_the_mirror_of_it_reads_from_the_far_half_of_the_scratch(self) -> None:
        # Arrange
        found = a_part()
        found.registers.dp = 1
        found.stores.scratch[0x41] = 0xCAFE
        found.stores.program[0] = a_load(0x1234, TO_L_AND_SCRATCH)

        # Act
        found.step()

        # Assert
        self.assertEqual((found.registers.word("l"), found.registers.word("k")), (0x1234, 0xCAFE))

    def test_a_load_into_the_scratch_writes_where_the_pointer_says(self) -> None:
        # Arrange
        found = a_part()
        found.registers.dp = 7
        found.stores.program[0] = a_load(0x5678, TO_SCRATCH)

        # Act
        found.step()

        # Assert
        self.assertEqual(found.stores.scratch[7], 0x5678)


class SourceTest(unittest.TestCase):
    def test_every_source_reads_the_register_its_field_names(self) -> None:
        # Arrange
        sources = sorted(EVERY_SOURCE_READS)

        # Act
        found = {source: moved_by(source) for source in sources}

        # Assert
        self.assertEqual(found, EVERY_SOURCE_READS)

    def test_reading_the_data_register_asks_the_host_for_attention(self) -> None:
        # Arrange
        found = a_part()
        found.stores.program[0] = an_operation(src=FROM_DATA_AND_ASK, dst=TO_TR)

        # Act
        found.step()

        # Assert
        self.assertTrue(found.registers.sr.rqm)

    def test_reading_it_the_other_way_does_not(self) -> None:
        # Arrange
        found = a_part()
        found.stores.program[0] = an_operation(src=FROM_DATA, dst=TO_TR)

        # Act
        found.step()

        # Assert
        self.assertFalse(found.registers.sr.rqm)

    def test_reading_either_serial_input_form_clears_its_acknowledge(self) -> None:
        # Arrange
        parts = []
        for source in (FROM_SERIAL_HIGH, FROM_SERIAL_LOW):
            part = a_part()
            part.registers.sr.siack = True
            part.stores.program[0] = an_operation(src=source, dst=TO_TR)
            parts.append(part)

        # Act
        for part in parts:
            part.step()

        # Assert
        self.assertEqual([part.registers.sr.siack for part in parts], [False, False])

    def test_writing_either_serial_output_form_sets_its_acknowledge(self) -> None:
        # Arrange
        parts = []
        for destination in (TO_SERIAL_LOW, TO_SERIAL_HIGH):
            part = a_part()
            part.stores.program[0] = a_load(0x1234, destination)
            parts.append(part)

        # Act
        for part in parts:
            part.step()

        # Assert
        self.assertEqual([part.registers.sr.soack for part in parts], [True, True])

    def test_the_saturating_source_answers_the_larger_value_while_the_sign_is_clear(self) -> None:
        # Arrange
        found = a_part()
        found.stores.program[0] = an_operation(src=FROM_SATURATION, dst=TO_TR)

        # Act
        found.step()

        # Assert
        self.assertEqual(found.registers.tr, 0x8000)

    def test_and_one_less_once_it_is_set(self) -> None:
        # Arrange
        found = a_part()
        found.flags_a.s1 = True
        found.stores.program[0] = an_operation(src=FROM_SATURATION, dst=TO_TR)

        # Act
        found.step()

        # Assert
        self.assertEqual(found.registers.tr, 0x7FFF)


class PointerTest(unittest.TestCase):
    def test_the_low_nibble_of_the_pointer_can_be_stepped_forward(self) -> None:
        # Arrange
        found = a_part()
        found.registers.dp = 0x1F
        found.stores.program[0] = an_operation(dpl=POINTER_UP)

        # Act
        found.step()

        # Assert
        self.assertEqual(found.registers.dp, 0x10)

    def test_and_backward(self) -> None:
        # Arrange
        found = a_part()
        found.registers.dp = 0x20
        found.stores.program[0] = an_operation(dpl=POINTER_DOWN)

        # Act
        found.step()

        # Assert
        self.assertEqual(found.registers.dp, 0x2F)

    def test_and_cleared_without_disturbing_the_rest(self) -> None:
        # Arrange
        found = a_part()
        found.registers.dp = 0x37
        found.stores.program[0] = an_operation(dpl=POINTER_CLEAR)

        # Act
        found.step()

        # Assert
        self.assertEqual(found.registers.dp, 0x30)

    def test_the_high_nibble_is_turned_over_rather_than_set(self) -> None:
        # Arrange
        found = a_part()
        found.registers.dp = 0x30
        found.stores.program[0] = an_operation(dphm=0x1)

        # Act
        found.step()

        # Assert
        self.assertEqual(found.registers.dp, 0x20)

    def test_a_move_that_writes_the_pointer_leaves_it_where_it_landed(self) -> None:
        # Arrange
        found = a_part()
        found.registers.tr = 0x25
        found.stores.program[0] = an_operation(dpl=POINTER_CLEAR, src=FROM_TR, dst=TO_POINTER)

        # Act
        found.step()

        # Assert
        self.assertEqual(found.registers.dp, 0x25)

    def test_the_table_pointer_steps_back_when_it_is_asked_to(self) -> None:
        # Arrange
        found = a_part()
        found.registers.rp = 5
        found.stores.program[0] = an_operation(rpdcr=1)

        # Act
        found.step()

        # Assert
        self.assertEqual(found.registers.rp, 4)

    def test_but_not_when_the_move_wrote_it(self) -> None:
        # Arrange
        found = a_part()
        found.registers.tr = 9
        found.stores.program[0] = an_operation(rpdcr=1, src=FROM_TR, dst=TO_TABLE_POINTER)

        # Act
        found.step()

        # Assert
        self.assertEqual(found.registers.rp, 9)


class MultiplyTest(unittest.TestCase):
    def test_the_product_lands_in_the_two_halves_after_every_instruction(self) -> None:
        # Arrange
        found = a_part()
        found.registers.k = 0x4000
        found.registers.l = 0x4000

        # Act
        found.step()

        # Assert
        self.assertEqual((found.registers.word("m"), found.registers.word("n")), (0x2000, 0))

    def test_a_negative_multiplicand_is_treated_as_one(self) -> None:
        # Arrange
        found = a_part()
        found.registers.k = -1
        found.registers.l = 0x4000

        # Act
        found.step()

        # Assert
        self.assertEqual(found.registers.word("m"), 0xFFFF)

    def test_the_low_half_carries_the_bit_the_high_half_shifted_past(self) -> None:
        # Arrange
        found = a_part()
        found.registers.k = 1
        found.registers.l = 1

        # Act
        found.step()

        # Assert
        self.assertEqual(found.registers.word("n"), 2)


if __name__ == "__main__":
    unittest.main()
