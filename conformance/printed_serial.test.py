from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conformance.printed import (
    FROM_DATA,
    FROM_DATA_AND_ASK,
    FROM_SERIAL_HIGH,
    FROM_SERIAL_LOW,
    TO_A,
    TO_DATA,
    TO_SERIAL_HIGH,
    TO_SERIAL_LOW,
    a_load,
    a_part,
    an_operation,
    fact,
)
from upd7725 import DATA, Host

if TYPE_CHECKING:
    from conformance.printed import Part

WORD = 0x8C31

WIDE = 16

ORDERS = {"firstBitHighest": True, "firstBitLowest": False}

SENT = {"highestFirst": True, "lowestFirst": False}

DESTINATIONS = {"SOL": TO_SERIAL_LOW, "SOM": TO_SERIAL_HIGH}

SOURCES = {"SIM": FROM_SERIAL_HIGH, "SIL": FROM_SERIAL_LOW}


def quiet() -> Part:
    chip = a_part()
    pins = chip.pins
    pins.bits_in = pins.bits_out = pins.shifting_in = pins.shifting_out = 0
    return chip


def bits_of(word: int, width: int) -> list[int]:
    return [word >> place & 1 for place in reversed(range(width))]


def level(chip: Part, high: bool) -> None:
    chip.pins.sck = high
    chip.step()


def clock_in(chip: Part, bits: list[int]) -> None:
    chip.pins.sien = False
    for bit in bits:
        chip.pins.si = bit
        level(chip, False)
        level(chip, True)


def clock_out(chip: Part, edges: int) -> list[int | None]:
    chip.pins.soen = False
    seen: list[int | None] = []
    for _ in range(edges):
        level(chip, True)
        level(chip, False)
        seen.append(chip.pins.so)
    return seen


def run(chip: Part, word: int) -> None:
    chip.stores.program[chip.registers.pc] = word
    chip.step()


def bits_until_acknowledged(narrow: bool) -> int:
    chip = quiet()
    chip.registers.sr.sic = narrow
    chip.pins.sien = False
    seen = []
    for _ in range(WIDE):
        level(chip, False)
        level(chip, True)
        seen.append(chip.registers.sr.siack)
    return seen.index(True) + 1


def bits_sent(narrow: bool) -> int:
    chip = quiet()
    chip.registers.sr.soc = narrow
    run(chip, a_load(0xFFFF, TO_SERIAL_HIGH))
    return sum(1 for bit in clock_out(chip, WIDE + 1) if bit is not None)


def word_read_as(source: int) -> int:
    chip = quiet()
    clock_in(chip, bits_of(WORD, WIDE))
    run(chip, an_operation(src=source, dst=TO_A))
    return chip.registers.word("a")


class SerialFactTest(unittest.TestCase):
    def test_a_bit_shifts_in_on_the_printed_edge_of_the_serial_clock(self) -> None:
        # Arrange
        printed = fact("serialInputEdge")["value"]
        chip = quiet()
        chip.pins.sien = False
        counted = {}

        # Act
        level(chip, True)
        counted["rising"] = chip.pins.bits_in
        level(chip, False)
        counted["falling"] = chip.pins.bits_in - counted["rising"]

        # Assert
        self.assertEqual(counted[printed], 1)

    def test_a_bit_shifts_out_on_the_printed_edge_of_the_serial_clock(self) -> None:
        # Arrange
        printed = fact("serialOutputEdge")["value"]
        chip = quiet()
        run(chip, a_load(WORD, TO_SERIAL_HIGH))
        chip.pins.soen = False
        driven = {}

        # Act
        level(chip, True)
        driven["rising"] = chip.pins.so
        level(chip, False)
        driven["falling"] = chip.pins.so

        # Assert
        self.assertEqual(driven[printed], WORD >> 15 & 1)

    def test_an_input_word_is_as_long_as_its_control_bit_says(self) -> None:
        # Arrange
        printed = fact("serialWordWidths")["value"]

        # Act
        found = {"clear": bits_until_acknowledged(False), "set": bits_until_acknowledged(True)}

        # Assert
        self.assertEqual(found, printed)

    def test_an_output_word_is_as_long_as_its_control_bit_says(self) -> None:
        # Arrange
        printed = fact("serialWordWidths")["value"]

        # Act
        found = {"clear": bits_sent(False), "set": bits_sent(True)}

        # Assert
        self.assertEqual(found, printed)

    def test_the_two_input_sources_read_the_word_in_the_printed_orders(self) -> None:
        # Arrange
        printed = fact("serialInputBitOrder")["value"]
        arrived = bits_of(WORD, WIDE)

        # Act
        found = {name: bits_of(word_read_as(SOURCES[name]), WIDE) for name in printed}

        # Assert
        self.assertEqual(
            found,
            {
                name: arrived if ORDERS[order] else list(reversed(arrived))
                for name, order in printed.items()
            },
        )

    def test_the_two_output_destinations_send_in_the_printed_orders(self) -> None:
        # Arrange
        printed = fact("serialOutputBitOrder")["value"]
        found = {}

        # Act
        for name in printed:
            chip = quiet()
            run(chip, a_load(WORD, DESTINATIONS[name]))
            found[name] = clock_out(chip, WIDE)

        # Assert
        self.assertEqual(
            found,
            {
                name: bits_of(WORD, WIDE) if SENT[order] else list(reversed(bits_of(WORD, WIDE)))
                for name, order in printed.items()
            },
        )

    def test_the_output_request_rises_once_the_register_is_loaded(self) -> None:
        # Arrange
        printed = fact("serialOutputRequest")["value"]
        chip = quiet()
        run(chip, a_load(WORD, TO_SERIAL_HIGH))

        # Act
        level(chip, True)

        # Assert
        self.assertEqual((printed["risesWhen"], chip.pins.sorq), ("loaded", True))

    def test_and_falls_once_the_whole_word_has_gone(self) -> None:
        # Arrange
        printed = fact("serialOutputRequest")["value"]
        chip = quiet()
        run(chip, a_load(WORD, TO_SERIAL_HIGH))
        clock_out(chip, WIDE)

        # Act
        level(chip, True)

        # Assert
        self.assertEqual((printed["fallsWhen"], chip.pins.sorq), ("wholeWordTransferred", False))

    def test_a_move_to_the_output_register_sets_its_acknowledge(self) -> None:
        # Arrange
        printed = fact("serialOutputAcknowledge")["value"]
        chip = quiet()

        # Act
        run(chip, a_load(WORD, TO_SERIAL_LOW))

        # Assert
        self.assertEqual((printed["setBy"], chip.registers.sr.soack), ("a move to SO", True))

    def test_and_the_word_leaving_for_the_shifter_clears_it(self) -> None:
        # Arrange
        printed = fact("serialOutputAcknowledge")["value"]
        chip = quiet()
        run(chip, a_load(WORD, TO_SERIAL_LOW))

        # Act
        clock_out(chip, 1)

        # Assert
        self.assertEqual(
            (printed["clearedBy"], chip.registers.sr.soack),
            ("the first falling clock that takes the word", False),
        )

    def test_a_whole_word_arriving_sets_the_input_acknowledge(self) -> None:
        # Arrange
        printed = fact("serialInputAcknowledge")["value"]
        chip = quiet()

        # Act
        clock_in(chip, bits_of(WORD, WIDE))

        # Assert
        self.assertEqual(
            (printed["setBy"], chip.registers.sr.siack), ("a whole word arriving", True)
        )

    def test_and_a_move_from_the_input_register_clears_it(self) -> None:
        # Arrange
        printed = fact("serialInputAcknowledge")["value"]
        chip = quiet()
        clock_in(chip, bits_of(WORD, WIDE))

        # Act
        run(chip, an_operation(src=FROM_SERIAL_HIGH, dst=TO_A))

        # Assert
        self.assertEqual((printed["clearedBy"], chip.registers.sr.siack), ("a move from SI", False))

    def test_the_output_lets_go_while_its_enable_is_high(self) -> None:
        # Arrange
        printed = fact("serialOutputFloats")["value"]
        chip = quiet()
        run(chip, a_load(WORD, TO_SERIAL_HIGH))

        # Act
        level(chip, True)
        level(chip, False)

        # Assert
        self.assertEqual((printed, chip.pins.so), ("highImpedance", None))


class DmaFactTest(unittest.TestCase):
    def test_in_dma_mode_the_program_touching_the_data_register_raises_the_request(
        self,
    ) -> None:
        # Arrange
        printed = fact("dmaRequest")["value"]
        found = []

        # Act
        for word in (a_load(WORD, TO_DATA), an_operation(src=FROM_DATA_AND_ASK)):
            chip = quiet()
            chip.registers.sr.dma = True
            run(chip, word)
            found.append(chip.pins.drq)

        # Assert
        self.assertEqual(
            (printed["raisedBy"], found),
            ("a data register access that sets RQM, in DMA mode", [True, True]),
        )

    def test_the_access_that_completes_the_transfer_lowers_it(self) -> None:
        # Arrange
        printed = fact("dmaRequest")["value"]
        chip = quiet()
        chip.registers.sr.dma = True
        run(chip, a_load(WORD, TO_DATA))
        host = Host(chip)
        host.read(DATA)
        held = chip.pins.drq

        # Act
        host.read(DATA)

        # Assert
        self.assertEqual(
            (printed["loweredBy"], held, chip.pins.drq),
            ("the host access that completes the transfer", True, False),
        )

    def test_the_move_that_sets_no_flag_raises_no_request(self) -> None:
        # Arrange
        printed = fact("dmaRequestWithoutFlag")["value"]
        chip = quiet()
        chip.registers.sr.dma = True

        # Act
        run(chip, an_operation(src=FROM_DATA))

        # Assert
        self.assertEqual(chip.pins.drq, printed)


if __name__ == "__main__":
    unittest.main()
