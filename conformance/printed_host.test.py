import sys
import unittest
from itertools import takewhile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conformance.printed import TOP_WORD, a_load, a_part, an_operation, fact
from upd7725 import core
from upd7725.ports import DATA, STATUS, Host

WORD_BITS = 16

HALF = 8

DATA_WORD = 0xBEEF

DRAIN_LIMIT = 16


def transfer_status_after(writes: int) -> int:
    chip = a_part()
    chip.registers.sr.rqm = True
    host = Host(chip)
    for _ in range(writes):
        host.write(DATA, 0x5A)
    return host.read(STATUS) << HALF


def status_word_with(place: int) -> int:
    chip = a_part()
    chip.registers.sr.assign(1 << place)
    return int(chip.registers.sr)


def drained(host: Host) -> list[int]:
    return [host.read(DATA) for _ in takewhile(lambda _: host.asking, range(DRAIN_LIMIT))]


class HostFactTest(unittest.TestCase):
    def test_nothing_a_host_reads_is_wider_than_the_printed_bus(self) -> None:
        # Arrange
        bits = fact("hostInterfaceBusBits")["value"]
        chip = a_part()
        chip.registers.dr = TOP_WORD
        chip.registers.sr.assign(TOP_WORD)
        host = Host(chip)

        # Act
        found = {host.read(port) for port in (DATA, STATUS)}

        # Assert
        self.assertEqual(max(found), (1 << bits) - 1)

    def test_a_sixteen_bit_word_crosses_the_bus_a_bus_width_at_a_time(self) -> None:
        # Arrange
        bits = fact("parallelInterfaceIsEightBit")["value"]
        chip = a_part()
        chip.stores.program[0] = a_load(DATA_WORD, core.TO_DATA)
        chip.step()

        # Act
        found = drained(Host(chip))

        # Assert
        self.assertEqual(
            found,
            [DATA_WORD >> at & (1 << bits) - 1 for at in range(0, WORD_BITS, bits)],
        )

    def test_the_select_line_picks_the_data_or_the_status_register(self) -> None:
        # Arrange
        select = fact("statusDataRegisterSelect")["value"]
        chip = a_part()
        chip.registers.dr = 0x00A5
        chip.registers.sr.drc = True
        chip.registers.sr.rqm = True
        host = Host(chip)

        # Act
        found = (host.read(select["status"]), host.read(select["data"]))

        # Assert
        self.assertEqual(found, (0x84, 0xA5))

    def test_each_status_flag_sits_at_its_printed_bit(self) -> None:
        # Arrange
        places = fact("statusRegisterBits")["value"]

        # Act
        found = {name: status_word_with(place) for name, place in places.items()}

        # Assert
        self.assertEqual(found, {name: 1 << place for name, place in places.items()})

    def test_the_host_reads_the_printed_number_of_status_bits_from_the_top(self) -> None:
        # Arrange
        width = fact("statusReadWidth")["value"]
        word = 0x8201
        chip = a_part()
        chip.registers.sr.assign(word)

        # Act
        found = Host(chip).read(STATUS)

        # Assert
        self.assertEqual(found, word >> WORD_BITS - width)

    def test_the_program_reading_the_data_register_raises_the_request(self) -> None:
        # Arrange
        printed = fact("requestBitSemantics")["value"]
        chip = a_part()
        chip.stores.program[0] = an_operation(src=core.FROM_DATA_AND_ASK)

        # Act
        chip.step()

        # Assert
        self.assertEqual(int(chip.registers.sr.rqm), printed["internalTransfer"])

    def test_the_program_writing_the_data_register_raises_the_request(self) -> None:
        # Arrange
        printed = fact("requestBitSemantics")["value"]
        chip = a_part()
        chip.stores.program[0] = a_load(DATA_WORD, core.TO_DATA)

        # Act
        chip.step()

        # Assert
        self.assertEqual(int(chip.registers.sr.rqm), printed["internalTransfer"])

    def test_a_host_read_lowers_the_request(self) -> None:
        # Arrange
        printed = fact("requestBitSemantics")["value"]
        chip = a_part()
        chip.registers.sr.drc = True
        chip.registers.sr.rqm = True

        # Act
        Host(chip).read(DATA)

        # Assert
        self.assertEqual(int(chip.registers.sr.rqm), printed["externalTransfer"])

    def test_a_host_write_lowers_the_request(self) -> None:
        # Arrange
        printed = fact("requestBitSemantics")["value"]
        chip = a_part()
        chip.registers.sr.drc = True
        chip.registers.sr.rqm = True

        # Act
        Host(chip).write(DATA, 0x5A)

        # Assert
        self.assertEqual(int(chip.registers.sr.rqm), printed["externalTransfer"])

    def test_the_transfer_status_rises_after_the_first_byte(self) -> None:
        # Arrange
        printed = fact("transferHalfSemantics")["value"]
        place = fact("statusRegisterBits")["value"]["DRS"]

        # Act
        status = transfer_status_after(1)

        # Assert
        self.assertEqual(status >> place & 1, printed["afterFirstByte"])

    def test_the_transfer_status_falls_after_both_bytes(self) -> None:
        # Arrange
        printed = fact("transferHalfSemantics")["value"]
        place = fact("statusRegisterBits")["value"]["DRS"]

        # Act
        status = transfer_status_after(2)

        # Assert
        self.assertEqual(status >> place & 1, printed["afterBothBytes"])


if __name__ == "__main__":
    unittest.main()
