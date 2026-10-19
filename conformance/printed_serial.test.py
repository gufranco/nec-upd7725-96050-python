from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conformance.printed import (
    FROM_SERIAL_HIGH,
    FROM_SERIAL_LOW,
    TO_A,
    a_part,
    an_operation,
    fact,
)

WORD = 0x8C31

WIDE = 16

ORDERS = {"firstBitHighest": True, "firstBitLowest": False}

SOURCES = {"SIM": FROM_SERIAL_HIGH, "SIL": FROM_SERIAL_LOW}


def bits_of(word: int, width: int) -> list[int]:
    return [word >> place & 1 for place in reversed(range(width))]


def word_read_as(source: int) -> int:
    chip = a_part()
    chip.registers.si = WORD
    chip.stores.program[0] = an_operation(src=source, dst=TO_A)
    chip.step()
    return chip.registers.word("a")


class SerialFactTest(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
