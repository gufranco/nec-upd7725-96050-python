import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from upd7725 import models, ports

ALWAYS_ASKING = 3 << 22 | 6
"""A store full of loads into the data register, so the part keeps asking."""


def a_console(fill: int = 0) -> "ports.Console":
    return ports.Console(models.describe("upd7725").build(fill=fill))


class StatusTest(unittest.TestCase):
    def test_the_console_reads_the_top_half_of_the_status_word(self) -> None:
        found = a_console()
        found.chip.registers.sr.rqm = True

        self.assertEqual(found.read(ports.STATUS), 0x80)

    def test_writing_the_status_from_outside_does_nothing(self) -> None:
        found = a_console()

        found.write(ports.STATUS, 0xFF)

        self.assertEqual(int(found.chip.registers.sr), 0)

    def test_the_part_says_when_it_wants_attention(self) -> None:
        found = a_console()
        found.chip.registers.sr.rqm = True

        self.assertTrue(found.asking)


class TransferTest(unittest.TestCase):
    def test_a_wide_transfer_takes_the_low_half_first(self) -> None:
        found = a_console()

        found.write(ports.DATA, 0x34)
        found.write(ports.DATA, 0x12)

        self.assertEqual(found.chip.registers.dr, 0x1234)

    def test_and_hands_it_back_the_same_way_round(self) -> None:
        found = a_console()
        found.chip.registers.dr = 0x1234

        self.assertEqual((found.read(ports.DATA), found.read(ports.DATA)), (0x34, 0x12))

    def test_a_narrow_transfer_moves_one_half_at_a_time(self) -> None:
        found = a_console()
        found.chip.registers.sr.drc = True
        found.chip.registers.sr.rqm = True

        found.write(ports.DATA, 0x34)

        self.assertEqual(found.chip.registers.dr & 0xFF, 0x34)
        self.assertFalse(found.chip.registers.sr.rqm)

    def test_and_reads_the_same_way(self) -> None:
        found = a_console()
        found.chip.registers.dr = 0x1234
        found.chip.registers.sr.drc = True
        found.chip.registers.sr.rqm = True

        self.assertEqual(found.read(ports.DATA), 0x34)
        self.assertFalse(found.chip.registers.sr.rqm)

    def test_finishing_a_wide_read_stops_the_part_asking(self) -> None:
        found = a_console()
        found.chip.registers.sr.rqm = True

        found.read(ports.DATA)
        found.read(ports.DATA)

        self.assertFalse(found.chip.registers.sr.rqm)

    def test_an_address_that_is_neither_register_reads_nothing(self) -> None:
        self.assertEqual(a_console().read(0x7), 0)

    def test_and_writing_to_it_changes_nothing(self) -> None:
        found = a_console()

        found.write(0x7, 0xFF)

        self.assertEqual(found.chip.registers.dr, 0)


class SettleTest(unittest.TestCase):
    def test_a_part_already_asking_settles_at_once(self) -> None:
        found = a_console()
        found.chip.registers.sr.rqm = True

        self.assertEqual(found.settle(), 0)

    def test_a_part_that_never_asks_gives_up_rather_than_running_forever(self) -> None:
        found = a_console()

        with self.assertRaises(ports.NeverReady):
            found.settle(limit=50)

    def test_a_part_that_asks_after_a_while_settles_when_it_does(self) -> None:
        found = a_console()
        found.chip.stores.program[0] = 3 << 22 | 0x1234 << 6 | 6

        self.assertEqual(found.settle(limit=10), 1)


class ExchangeTest(unittest.TestCase):
    def test_sending_a_word_settles_before_each_half(self) -> None:
        found = a_console()
        found.chip.registers.sr.rqm = True

        found.send(0x1234)

        self.assertEqual(found.chip.registers.dr, 0x1234)

    def test_taking_a_word_puts_the_halves_back_together(self) -> None:
        found = a_console()
        found.chip.registers.dr = 0xBEEF
        found.chip.registers.sr.rqm = True

        self.assertEqual(found.take(), 0xBEEF)

    def test_sending_bytes_sends_each_one(self) -> None:
        found = a_console(fill=ALWAYS_ASKING)
        found.chip.registers.sr.rqm = True

        found.send_bytes([0x11, 0x22])

        self.assertEqual(found.chip.registers.dr, 0x2211)

    def test_taking_bytes_takes_as_many_as_asked(self) -> None:
        found = a_console(fill=ALWAYS_ASKING)
        found.chip.registers.sr.rqm = True

        self.assertEqual(len(found.take_bytes(4)), 4)


if __name__ == "__main__":
    unittest.main()
