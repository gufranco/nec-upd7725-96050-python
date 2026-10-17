from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import upd7725
from conformance.printed import TO_DATA, a_load

if TYPE_CHECKING:
    from conformance.printed import Part

ALWAYS_ASKING = a_load(0, TO_DATA)

NEITHER_REGISTER = 0x7


def connected(fill: int = 0) -> tuple[Part, upd7725.Host]:
    chip = upd7725.Cpu("upd7725", fill=fill).reset()
    registers = chip.registers
    registers.rp = registers.dp = registers.sp = 0
    registers.k = registers.l = registers.m = registers.n = 0
    registers.a = registers.b = 0
    registers.tr = registers.trb = registers.dr = 0
    registers.si = registers.so = 0
    for slot in range(len(registers.stack)):
        registers.stack[slot] = 0
    return chip, upd7725.Host(chip)


class AddressTest(unittest.TestCase):
    def test_the_host_sees_the_data_register_at_zero_and_the_status_at_one(self) -> None:
        # Arrange
        cpu = upd7725.Cpu("upd7725", fill=0)
        cpu.registers.dr = 0x1234
        cpu.registers.sr.assign(0x8400)
        host = upd7725.Host(cpu)

        # Act
        read = (host.read(1), host.read(0))

        # Assert
        self.assertEqual((upd7725.STATUS, upd7725.DATA, read), (1, 0, (0x84, 0x34)))


class StatusTest(unittest.TestCase):
    def test_the_host_reads_the_top_half_of_the_status_word(self) -> None:
        # Arrange
        chip, host = connected()
        chip.registers.sr.rqm = True

        # Act
        read = host.read(upd7725.STATUS)

        # Assert
        self.assertEqual(read, 0x80)

    def test_writing_the_status_from_outside_does_nothing(self) -> None:
        # Arrange
        chip, host = connected()

        # Act
        host.write(upd7725.STATUS, 0xFF)

        # Assert
        self.assertEqual((int(chip.registers.sr), chip.registers.dr), (0, 0))

    def test_the_part_says_when_it_wants_attention(self) -> None:
        # Arrange
        chip, host = connected()
        chip.registers.sr.rqm = True

        # Act
        asking = host.asking

        # Assert
        self.assertTrue(asking)

    def test_and_says_nothing_while_it_does_not(self) -> None:
        # Arrange
        _, host = connected()

        # Act
        asking = host.asking

        # Assert
        self.assertFalse(asking)


class TransferTest(unittest.TestCase):
    def test_a_wide_transfer_takes_the_low_half_first(self) -> None:
        # Arrange
        chip, host = connected()
        chip.registers.sr.rqm = True

        # Act
        host.send_bytes([0x34, 0x12], limit=1)

        # Assert
        self.assertEqual((chip.registers.dr, chip.registers.sr.rqm), (0x1234, False))

    def test_the_first_half_of_a_wide_write_leaves_the_high_half_alone(self) -> None:
        # Arrange
        chip, host = connected()
        chip.registers.dr = 0xAB00

        # Act
        host.write(upd7725.DATA, 0x34)

        # Assert
        self.assertEqual((chip.registers.dr, chip.registers.sr.drs), (0xAB34, True))

    def test_and_hands_it_back_the_same_way_round(self) -> None:
        # Arrange
        chip, host = connected()
        chip.registers.dr = 0x1234
        chip.registers.sr.rqm = True

        # Act
        read = host.take_bytes(2, limit=1)

        # Assert
        self.assertEqual(read, bytes([0x34, 0x12]))

    def test_a_narrow_transfer_moves_one_half_at_a_time(self) -> None:
        # Arrange
        chip, host = connected()
        chip.registers.dr = 0xAB00
        chip.registers.sr.drc = True
        chip.registers.sr.rqm = True

        # Act
        host.write(upd7725.DATA, 0x34)

        # Assert
        self.assertEqual((chip.registers.dr, chip.registers.sr.rqm), (0xAB34, False))

    def test_and_reads_the_same_way(self) -> None:
        # Arrange
        chip, host = connected()
        chip.registers.dr = 0x1234
        chip.registers.sr.drc = True
        chip.registers.sr.rqm = True

        # Act
        read = host.read(upd7725.DATA)

        # Assert
        self.assertEqual((read, chip.registers.sr.rqm), (0x34, False))

    def test_the_first_half_of_a_wide_read_keeps_the_part_asking(self) -> None:
        # Arrange
        chip, host = connected()
        chip.registers.sr.rqm = True

        # Act
        host.read(upd7725.DATA)

        # Assert
        self.assertEqual((chip.registers.sr.rqm, chip.registers.sr.drs), (True, True))

    def test_finishing_a_wide_read_stops_the_part_asking(self) -> None:
        # Arrange
        chip, host = connected()
        chip.registers.sr.rqm = True
        host.read(upd7725.DATA)

        # Act
        host.read(upd7725.DATA)

        # Assert
        self.assertEqual((chip.registers.sr.rqm, chip.registers.sr.drs), (False, False))

    def test_an_address_that_is_neither_register_reads_nothing(self) -> None:
        # Arrange
        chip, host = connected()
        chip.registers.dr = 0xFFFF
        chip.registers.sr.assign(0xFFFF)

        # Act
        read = host.read(NEITHER_REGISTER)

        # Assert
        self.assertEqual(read, 0)

    def test_and_writing_to_it_changes_nothing(self) -> None:
        # Arrange
        chip, host = connected()

        # Act
        host.write(NEITHER_REGISTER, 0xFF)

        # Assert
        self.assertEqual((chip.registers.dr, int(chip.registers.sr)), (0, 0))


class SettleTest(unittest.TestCase):
    def test_a_part_already_asking_settles_at_once(self) -> None:
        # Arrange
        chip, host = connected()
        chip.registers.sr.rqm = True

        # Act
        stepped = host.settle()

        # Assert
        self.assertEqual((stepped, chip.steps), (0, 0))

    def test_a_part_that_never_asks_gives_up_rather_than_running_forever(self) -> None:
        # Arrange
        chip, host = connected()

        # Act
        with self.assertRaises(upd7725.NeverReady) as raised:
            host.settle(limit=50)

        # Assert
        self.assertEqual(
            (str(raised.exception), chip.steps),
            ("the part did not ask for attention within 50 instructions", 50),
        )

    def test_a_part_that_asks_after_a_while_settles_when_it_does(self) -> None:
        # Arrange
        chip, host = connected()
        chip.stores.program[0] = a_load(0x1234, TO_DATA)

        # Act
        stepped = host.settle(limit=10)

        # Assert
        self.assertEqual((stepped, chip.registers.dr), (1, 0x1234))


class ExchangeTest(unittest.TestCase):
    def test_sending_a_word_settles_before_each_half(self) -> None:
        # Arrange
        chip, host = connected()
        chip.registers.sr.rqm = True

        # Act
        host.send(0x1234)

        # Assert
        self.assertEqual(chip.registers.dr, 0x1234)

    def test_taking_a_word_puts_the_halves_back_together(self) -> None:
        # Arrange
        chip, host = connected()
        chip.registers.dr = 0xBEEF
        chip.registers.sr.rqm = True

        # Act
        taken = host.take()

        # Assert
        self.assertEqual(taken, 0xBEEF)

    def test_sending_bytes_sends_each_one(self) -> None:
        # Arrange
        chip, host = connected(fill=ALWAYS_ASKING)
        chip.registers.sr.rqm = True

        # Act
        host.send_bytes([0x11, 0x22])

        # Assert
        self.assertEqual(chip.registers.dr, 0x2211)

    def test_taking_bytes_takes_as_many_as_asked(self) -> None:
        # Arrange
        chip, host = connected(fill=ALWAYS_ASKING)
        chip.registers.dr = 0x00AB
        chip.registers.sr.rqm = True

        # Act
        taken = host.take_bytes(4)

        # Assert
        self.assertEqual(taken, bytes([0xAB, 0x00, 0x00, 0x00]))


if __name__ == "__main__":
    unittest.main()
