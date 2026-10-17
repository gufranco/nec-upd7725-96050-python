import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import upd7725
from conformance.printed import fact

PRINTED_BITS = {name.lower(): place for name, place in fact("statusRegisterBits")["value"].items()}

TRANSFER_HALF = PRINTED_BITS.pop("drs")

SIGNED = ("k", "l", "m", "n", "a", "b")


class StatusTest(unittest.TestCase):
    def test_a_fresh_status_holds_nothing(self) -> None:
        # Arrange
        found = upd7725.Cpu("upd7725").registers.sr

        # Act
        word = int(found)

        # Assert
        self.assertEqual(word, 0)

    def test_each_bit_sits_where_the_data_sheet_puts_it(self) -> None:
        # Arrange
        held = {name: upd7725.Cpu("upd7725").registers.sr for name in PRINTED_BITS}

        # Act
        for name, found in held.items():
            setattr(found, name, True)

        # Assert
        self.assertEqual(
            {name: int(found) for name, found in held.items()},
            {name: 1 << place for name, place in PRINTED_BITS.items()},
        )

    def test_the_transfer_bit_reads_back_while_the_word_is_wide(self) -> None:
        # Arrange
        found = upd7725.Cpu("upd7725").registers.sr

        # Act
        found.drs = True

        # Assert
        self.assertEqual(int(found), 1 << TRANSFER_HALF)

    def test_but_reads_as_clear_once_the_word_is_narrow(self) -> None:
        # Arrange
        found = upd7725.Cpu("upd7725").registers.sr
        found.drc = True

        # Act
        found.drs = True

        # Assert
        self.assertEqual(int(found) & 1 << TRANSFER_HALF, 0)

    def test_a_status_takes_every_bit_the_part_defines(self) -> None:
        # Arrange
        found = upd7725.Cpu("upd7725").registers.sr

        # Act
        found.assign(0xFFFF)

        # Assert
        self.assertEqual(int(found), sum(1 << place for place in PRINTED_BITS.values()))

    def test_the_bits_the_data_sheet_prints_as_zero_are_not_kept(self) -> None:
        # Arrange
        found = upd7725.Cpu("upd7725").registers.sr

        # Act
        found.assign(0x007C)

        # Assert
        self.assertEqual(int(found), 0)

    def test_the_acknowledgements_are_not_part_of_the_word(self) -> None:
        # Arrange
        found = upd7725.Cpu("upd7725").registers.sr

        # Act
        found.siack = True
        found.soack = True

        # Assert
        self.assertEqual(int(found), 0)

    def test_a_status_prints_the_bits_it_holds(self) -> None:
        # Arrange
        found = upd7725.Cpu("upd7725").registers.sr
        found.rqm = True
        found.ei = True

        # Act
        printed = repr(found)

        # Assert
        self.assertEqual(printed, "<Status ei rqm>")

    def test_and_says_so_when_it_holds_none(self) -> None:
        # Arrange
        found = upd7725.Cpu("upd7725").registers.sr

        # Act
        printed = repr(found)

        # Assert
        self.assertEqual(printed, "<Status none>")


class WidthTest(unittest.TestCase):
    def test_a_counter_keeps_only_as_many_bits_as_it_has(self) -> None:
        # Arrange
        found = upd7725.Cpu("upd7725").registers

        # Act
        found.pc = 0xFFFF

        # Assert
        self.assertEqual(found.pc, 0x7FF)

    def test_the_smaller_part_has_its_own_three_widths(self) -> None:
        # Arrange
        found = upd7725.Cpu("upd7725").registers

        # Act
        found.pc = found.rp = found.dp = 0xFFFF

        # Assert
        self.assertEqual((found.pc, found.rp, found.dp), (0x7FF, 0x3FF, 0xFF))

    def test_and_the_larger_part_has_its_own(self) -> None:
        # Arrange
        found = upd7725.Cpu("upd96050").registers

        # Act
        found.pc = found.rp = found.dp = 0xFFFF

        # Assert
        self.assertEqual((found.pc, found.rp, found.dp), (0x3FFF, 0x7FF, 0x7FF))

    def test_a_counter_that_runs_past_its_end_comes_back_to_the_start(self) -> None:
        # Arrange
        found = upd7725.Cpu("upd7725").registers
        found.pc = 0x7FF

        # Act
        found.pc += 1

        # Assert
        self.assertEqual(found.pc, 0)


class SignedTest(unittest.TestCase):
    def test_a_multiplicand_takes_the_sign_of_the_word_it_is_given(self) -> None:
        # Arrange
        found = upd7725.Cpu("upd96050").registers

        # Act
        found.k = 0xFFFF

        # Assert
        self.assertEqual(found.k, -1)

    def test_and_reads_back_unsigned_when_asked_that_way(self) -> None:
        # Arrange
        found = upd7725.Cpu("upd96050").registers
        found.k = -1

        # Act
        word = found.word("k")

        # Assert
        self.assertEqual(word, 0xFFFF)

    def test_every_signed_register_behaves_the_same_way(self) -> None:
        # Arrange
        found = upd7725.Cpu("upd96050").registers

        # Act
        for name in SIGNED:
            setattr(found, name, 0x18000)

        # Assert
        self.assertEqual(
            {name: getattr(found, name) for name in SIGNED}, dict.fromkeys(SIGNED, -0x8000)
        )

    def test_a_positive_word_reads_back_as_itself(self) -> None:
        # Arrange
        found = upd7725.Cpu("upd96050").registers

        # Act
        for name in SIGNED:
            setattr(found, name, 0x7FFF)

        # Assert
        self.assertEqual(
            {name: getattr(found, name) for name in SIGNED}, dict.fromkeys(SIGNED, 0x7FFF)
        )


class AttributeTest(unittest.TestCase):
    def test_a_name_no_register_has_is_refused(self) -> None:
        # Arrange
        found = upd7725.Cpu("upd96050").registers
        absent = "nonsense"

        # Act
        with self.assertRaises(AttributeError) as raised:
            setattr(found, absent, 1)

        # Assert
        self.assertIn("nonsense", str(raised.exception))


class WordTest(unittest.TestCase):
    def test_a_signed_register_reads_back_as_sixteen_bits(self) -> None:
        # Arrange
        found = upd7725.Cpu("upd96050").registers
        found.a = -1

        # Act
        word = found.word("a")

        # Assert
        self.assertEqual(word, 0xFFFF)

    def test_asking_for_the_status_register_this_way_is_refused(self) -> None:
        # Arrange
        found = upd7725.Cpu("upd96050").registers

        # Act
        with self.assertRaises(AttributeError) as raised:
            found.word("sr")

        # Assert
        self.assertEqual(str(raised.exception), "sr")

    def test_and_so_is_asking_for_the_stack(self) -> None:
        # Arrange
        found = upd7725.Cpu("upd96050").registers

        # Act
        with self.assertRaises(AttributeError) as raised:
            found.word("stack")

        # Assert
        self.assertEqual(str(raised.exception), "stack")


class StackTest(unittest.TestCase):
    def test_the_smaller_part_has_the_four_levels_the_data_sheet_prints(self) -> None:
        # Arrange
        printed = fact("stackLevels")["value"]

        # Act
        found = upd7725.Cpu("upd7725").registers

        # Assert
        self.assertEqual(len(found.stack), printed)

    def test_the_larger_part_is_built_with_eight(self) -> None:
        # Arrange
        name = "upd96050"

        # Act
        found = upd7725.Cpu(name).registers

        # Assert
        self.assertEqual(len(found.stack), 8)

    def test_the_pointer_wraps_at_the_last_slot_of_a_four_deep_stack(self) -> None:
        # Arrange
        found = upd7725.Cpu("upd7725").registers
        found.sp = 3

        # Act
        found.sp += 1

        # Assert
        self.assertEqual(found.sp, 0)

    def test_and_at_the_last_slot_of_an_eight_deep_one(self) -> None:
        # Arrange
        found = upd7725.Cpu("upd96050").registers
        found.sp = 7

        # Act
        found.sp += 1

        # Assert
        self.assertEqual(found.sp, 0)

    def test_a_four_deep_stack_cannot_be_pointed_past_its_last_slot(self) -> None:
        # Arrange
        found = upd7725.Cpu("upd7725").registers

        # Act
        found.sp = 9

        # Assert
        self.assertEqual(found.sp, 1)

    def test_every_slot_of_the_stack_can_be_reached(self) -> None:
        # Arrange
        found = upd7725.Cpu("upd7725").registers

        # Act
        reached = []
        for at in range(4):
            found.sp = at
            reached.append(found.sp)

        # Assert
        self.assertEqual(reached, [0, 1, 2, 3])


if __name__ == "__main__":
    unittest.main()
