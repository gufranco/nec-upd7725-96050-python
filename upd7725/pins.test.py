from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import upd7725
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
)

if TYPE_CHECKING:
    from conformance.printed import Part

SEED = 0x7725

WIDE = 16

NARROW = 8

SAMPLE = 0xB39C


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


def written(chip: Part, word: int, destination: int) -> None:
    chip.stores.program[chip.registers.pc] = a_load(word, destination)
    chip.step()


def clock_out(chip: Part, edges: int) -> list[int | None]:
    chip.pins.soen = False
    seen: list[int | None] = []
    for _ in range(edges):
        level(chip, True)
        level(chip, False)
        seen.append(chip.pins.so)
    return seen


def moved(chip: Part, source: int) -> int:
    chip.stores.program[chip.registers.pc] = an_operation(src=source, dst=TO_A)
    chip.step()
    return chip.registers.word("a")


class SerialInputTest(unittest.TestCase):
    def test_a_whole_word_shifted_in_lands_first_bit_highest(self) -> None:
        # Arrange
        word = random.Random(SEED).getrandbits(WIDE)
        chip = quiet()

        # Act
        clock_in(chip, bits_of(word, WIDE))

        # Assert
        self.assertEqual((chip.registers.si, chip.registers.sr.siack), (word, True))

    def test_one_bit_short_of_a_word_is_not_acknowledged(self) -> None:
        # Arrange
        chip = quiet()

        # Act
        clock_in(chip, bits_of(SAMPLE, WIDE)[:-1])

        # Assert
        self.assertEqual((chip.registers.si, chip.registers.sr.siack), (0, False))

    def test_an_eight_bit_word_completes_after_eight_bits(self) -> None:
        # Arrange
        chip = quiet()
        chip.registers.sr.sic = True

        # Act
        clock_in(chip, bits_of(0xA7, NARROW))

        # Assert
        self.assertEqual((chip.registers.si, chip.registers.sr.siack), (0xA7, True))

    def test_nothing_shifts_in_while_the_input_enable_is_high(self) -> None:
        # Arrange
        chip = quiet()
        chip.pins.si = 1

        # Act
        for _ in range(WIDE):
            level(chip, False)
            level(chip, True)

        # Assert
        self.assertEqual((chip.pins.bits_in, chip.pins.shifting_in), (0, 0))

    def test_a_clock_held_high_shifts_only_once(self) -> None:
        # Arrange
        chip = quiet()
        chip.pins.sien = False
        chip.pins.si = 1

        # Act
        for _ in range(4):
            level(chip, True)

        # Assert
        self.assertEqual(chip.pins.bits_in, 1)

    def test_reading_the_high_form_gives_the_word_as_it_arrived(self) -> None:
        # Arrange
        chip = quiet()
        clock_in(chip, bits_of(SAMPLE, WIDE))

        # Act
        found = moved(chip, FROM_SERIAL_HIGH)

        # Assert
        self.assertEqual((found, chip.registers.sr.siack), (SAMPLE, False))

    def test_reading_the_low_form_gives_it_bit_reversed(self) -> None:
        # Arrange
        chip = quiet()
        clock_in(chip, bits_of(0x8001 | 0x0006, WIDE))

        # Act
        found = moved(chip, FROM_SERIAL_LOW)

        # Assert
        self.assertEqual((found, chip.registers.sr.siack), (0xE001, False))

    def test_in_eight_bit_mode_only_the_low_byte_is_reversed(self) -> None:
        # Arrange
        chip = quiet()
        chip.registers.sr.sic = True
        chip.registers.si = 0x1201

        # Act
        found = moved(chip, FROM_SERIAL_LOW)

        # Assert
        self.assertEqual(found, 0x1280)


class SerialOutputTest(unittest.TestCase):
    def test_writing_the_output_register_sets_its_acknowledge(self) -> None:
        # Arrange
        chip = quiet()

        # Act
        written(chip, SAMPLE, TO_SERIAL_HIGH)

        # Assert
        self.assertEqual((chip.registers.so, chip.registers.sr.soack), (SAMPLE, True))

    def test_the_request_rises_on_the_next_rising_clock(self) -> None:
        # Arrange
        chip = quiet()
        written(chip, SAMPLE, TO_SERIAL_HIGH)
        before = chip.pins.sorq

        # Act
        level(chip, True)

        # Assert
        self.assertEqual((before, chip.pins.sorq), (False, True))

    def test_the_high_form_sends_the_top_bit_first(self) -> None:
        # Arrange
        chip = quiet()
        written(chip, SAMPLE, TO_SERIAL_HIGH)

        # Act
        seen = clock_out(chip, WIDE)

        # Assert
        self.assertEqual(seen, bits_of(SAMPLE, WIDE))

    def test_the_low_form_sends_the_bottom_bit_first(self) -> None:
        # Arrange
        chip = quiet()
        written(chip, SAMPLE, TO_SERIAL_LOW)

        # Act
        seen = clock_out(chip, WIDE)

        # Assert
        self.assertEqual(seen, list(reversed(bits_of(SAMPLE, WIDE))))

    def test_eight_bit_mode_sends_eight_bits_and_then_lets_go(self) -> None:
        # Arrange
        chip = quiet()
        chip.registers.sr.soc = True
        written(chip, 0x12C5, TO_SERIAL_HIGH)

        # Act
        seen = clock_out(chip, NARROW + 1)

        # Assert
        self.assertEqual(seen, [*bits_of(0xC5, NARROW), None])

    def test_the_first_falling_clock_takes_the_word_and_clears_the_acknowledge(self) -> None:
        # Arrange
        chip = quiet()
        written(chip, SAMPLE, TO_SERIAL_HIGH)

        # Act
        clock_out(chip, 1)

        # Assert
        self.assertEqual((chip.registers.sr.soack, chip.pins.bits_out), (False, WIDE - 1))

    def test_the_request_falls_on_the_rising_clock_after_the_last_bit(self) -> None:
        # Arrange
        chip = quiet()
        written(chip, SAMPLE, TO_SERIAL_HIGH)
        clock_out(chip, WIDE)
        held = chip.pins.sorq

        # Act
        level(chip, True)

        # Assert
        self.assertEqual((held, chip.pins.sorq), (True, False))

    def test_a_word_written_during_a_transfer_follows_it_without_a_gap(self) -> None:
        # Arrange
        chip = quiet()
        written(chip, 0x0000, TO_SERIAL_HIGH)
        clock_out(chip, 2)
        written(chip, 0xFFFF, TO_SERIAL_HIGH)

        # Act
        seen = clock_out(chip, WIDE)

        # Assert
        self.assertEqual((seen, chip.pins.sorq), ([0] * 14 + [1, 1], True))

    def test_the_output_floats_while_its_enable_is_high(self) -> None:
        # Arrange
        chip = quiet()
        written(chip, SAMPLE, TO_SERIAL_HIGH)

        # Act
        level(chip, True)
        level(chip, False)

        # Assert
        self.assertEqual((chip.pins.so, chip.registers.sr.soack), (None, True))

    def test_with_nothing_written_the_output_floats(self) -> None:
        # Arrange
        chip = quiet()

        # Act
        seen = clock_out(chip, 2)

        # Assert
        self.assertEqual((seen, chip.pins.sorq), ([None, None], False))


class DmaRequestTest(unittest.TestCase):
    def test_in_dma_mode_the_program_writing_the_data_register_raises_it(self) -> None:
        # Arrange
        chip = quiet()
        chip.registers.sr.dma = True

        # Act
        written(chip, SAMPLE, TO_DATA)

        # Assert
        self.assertTrue(chip.pins.drq)

    def test_in_dma_mode_the_program_reading_it_raises_it_too(self) -> None:
        # Arrange
        chip = quiet()
        chip.registers.sr.dma = True

        # Act
        moved(chip, FROM_DATA_AND_ASK)

        # Assert
        self.assertTrue(chip.pins.drq)

    def test_the_read_that_asks_for_no_flag_leaves_it_low(self) -> None:
        # Arrange
        chip = quiet()
        chip.registers.sr.dma = True

        # Act
        moved(chip, FROM_DATA)

        # Assert
        self.assertEqual((chip.pins.drq, chip.registers.sr.rqm), (False, False))

    def test_outside_dma_mode_it_stays_low(self) -> None:
        # Arrange
        chip = quiet()

        # Act
        written(chip, SAMPLE, TO_DATA)

        # Assert
        self.assertEqual((chip.pins.drq, chip.registers.sr.rqm), (False, True))

    def test_a_sixteen_bit_transfer_drops_it_on_the_second_byte(self) -> None:
        # Arrange
        chip = quiet()
        chip.registers.sr.dma = True
        written(chip, SAMPLE, TO_DATA)
        host = upd7725.Host(chip)

        # Act
        seen = [host.read(upd7725.DATA) for _ in range(2)]
        dropped = chip.pins.drq

        # Assert
        self.assertEqual((seen, dropped), ([SAMPLE & 0xFF, SAMPLE >> 8], False))

    def test_and_holds_it_after_the_first(self) -> None:
        # Arrange
        chip = quiet()
        chip.registers.sr.dma = True
        written(chip, SAMPLE, TO_DATA)
        host = upd7725.Host(chip)

        # Act
        host.write(upd7725.DATA, 0x5A)

        # Assert
        self.assertTrue(chip.pins.drq)

    def test_an_eight_bit_transfer_drops_it_on_its_only_byte(self) -> None:
        # Arrange
        chip = quiet()
        chip.registers.sr.dma = chip.registers.sr.drc = True
        written(chip, SAMPLE, TO_DATA)

        # Act
        upd7725.Host(chip).write(upd7725.DATA, 0x5A)

        # Assert
        self.assertFalse(chip.pins.drq)


class PowerOnTest(unittest.TestCase):
    def test_the_shift_registers_come_up_holding_what_the_seed_says(self) -> None:
        # Arrange
        seeds = (SEED, SEED + 1)

        # Act
        held = [
            (part.pins.shifting_in, part.pins.bits_in, part.pins.shifting_out, part.pins.bits_out)
            for part in (upd7725.Cpu("upd7725", seed=seed) for seed in seeds)
        ]

        # Assert
        self.assertNotEqual(held[0], held[1])

    def test_and_the_same_seed_brings_them_up_the_same(self) -> None:
        # Arrange
        parts = [upd7725.Cpu("upd7725", seed=SEED) for _ in range(2)]

        # Act
        held = [(part.pins.shifting_in, part.pins.shifting_out) for part in parts]

        # Assert
        self.assertEqual(held[0], held[1])

    def test_a_reset_leaves_them_alone(self) -> None:
        # Arrange
        chip = upd7725.Cpu("upd7725", seed=SEED)
        before = (chip.pins.shifting_in, chip.pins.bits_in)

        # Act
        chip.reset()

        # Assert
        self.assertEqual((chip.pins.shifting_in, chip.pins.bits_in), before)


if __name__ == "__main__":
    unittest.main()
