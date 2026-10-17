from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from typing import TYPE_CHECKING, Any, override

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import upd7725
from conformance.printed import (
    ADD,
    FROM_B,
    FROM_BUS,
    TO_A,
    TO_B,
    TO_NOWHERE,
    an_operation,
)

if TYPE_CHECKING:
    from conformance.printed import Part

HARDWARE = Path(__file__).resolve().parent / "hardware.json"


def declared() -> dict[str, Any]:
    held = json.loads(HARDWARE.read_text())
    assert isinstance(held, dict), f"{HARDWARE} does not hold an object"
    return held


def facts_for(part: str) -> dict[str, Any]:
    for one in declared()["parts"]:
        if one["part"] == part:
            found = one["facts"]
            assert isinstance(found, dict), f"{part} declares no facts"
            return found
    raise AssertionError(f"{part} is not in {HARDWARE.name}")


def verified_sheets() -> list[tuple[str, dict[str, Any]]]:
    return [
        (one["part"], one["documents"]["dataSheet"])
        for one in declared()["parts"]
        if one["verified"]
    ]


class DocumentTest(unittest.TestCase):
    def test_the_verified_part_names_the_document_it_was_read_from(self) -> None:
        # Arrange
        named = ("publisher", "title", "kind", "date", "readOn")

        # Act
        missing = [
            f"{part}: {one}"
            for part, sheet in verified_sheets()
            for one in named
            if one not in sheet
        ]

        # Assert
        self.assertEqual(missing, [])

    def test_and_pins_it_by_digest_so_the_reading_can_be_repeated(self) -> None:
        # Arrange
        sheets = verified_sheets()

        # Act
        digests = [sheet["sha256"] for _, sheet in sheets]

        # Assert
        for digest in digests:
            self.assertRegex(digest, r"^[0-9a-f]{64}$")

    def test_and_says_how_the_printed_number_relates_to_the_file(self) -> None:
        # Arrange
        sheets = verified_sheets()

        # Act
        missing = [part for part, sheet in sheets if "pageNumbering" not in sheet]

        # Assert
        self.assertEqual(missing, [])

    def test_every_fact_carries_the_words_it_came_from(self) -> None:
        # Arrange
        facts = facts_for("upd7725")

        # Act
        short = [name for name, fact in facts.items() if len(fact.get("quote", "")) <= 20]

        # Assert
        self.assertEqual(short, [])

    def test_and_where_those_words_are_printed(self) -> None:
        # Arrange
        pages = declared()["parts"][0]["documents"]["dataSheet"]["pdfPages"]

        # Act
        astray = [
            name
            for name, fact in facts_for("upd7725").items()
            if not isinstance(fact.get("section"), str)
            and not (isinstance(fact.get("page"), int) and 1 <= fact["page"] < pages)
        ]

        # Assert
        self.assertEqual(astray, [])

    def test_an_unverified_part_says_so_and_says_what_would_settle_it(self) -> None:
        # Arrange
        unverified = [one for one in declared()["parts"] if not one["verified"]]

        # Act
        found = [(one["documents"], "howToSettleIt" in one["unverified"]) for one in unverified]

        # Assert
        self.assertEqual(found, [({}, True)])

    def test_the_authority_order_is_written_down(self) -> None:
        # Arrange
        authority = declared()["authority"]

        # Act
        order = authority["order"]

        # Assert
        self.assertGreaterEqual(len(order), 2)


class LookupTest(unittest.TestCase):
    def test_asking_for_a_part_the_file_does_not_carry_says_so(self) -> None:
        # Arrange
        absent = "upd7720"

        # Act
        with self.assertRaises(AssertionError) as raised:
            facts_for(absent)

        # Assert
        self.assertIn(absent, str(raised.exception))


class CycleTest(unittest.TestCase):
    def test_the_document_gives_one_clock_per_instruction(self) -> None:
        # Arrange
        facts = facts_for("upd7725")

        # Act
        clocks = facts["clocksPerInstruction"]["value"]

        # Assert
        self.assertEqual(clocks, 1)

    def test_and_says_every_instruction_takes_the_same_one(self) -> None:
        # Arrange
        facts = facts_for("upd7725")

        # Act
        same = facts["everyInstructionSameLength"]["value"]

        # Assert
        self.assertTrue(same)

    def test_so_one_step_is_one_cycle(self) -> None:
        # Arrange
        chip = upd7725.Cpu("upd7725", fill=0)

        # Act
        chip.step()

        # Assert
        self.assertEqual(chip.cycles, 1)

    def test_and_a_run_of_many_is_that_many_cycles(self) -> None:
        # Arrange
        chip = upd7725.Cpu("upd7725", fill=0)

        # Act
        chip.run_for(1000)

        # Assert
        self.assertEqual(chip.cycles, 1000)

    def test_a_part_that_has_run_nothing_has_spent_no_cycles(self) -> None:
        # Arrange
        name = "upd7725"

        # Act
        chip = upd7725.Cpu(name, fill=0)

        # Assert
        self.assertEqual(chip.cycles, 0)

    def test_the_cycle_time_and_the_clock_it_belongs_to_agree(self) -> None:
        # Arrange
        cycle = facts_for("upd7725")["instructionCycleNanoseconds"]

        # Act
        derived = 1e9 / cycle["atClockHz"]

        # Assert
        self.assertAlmostEqual(derived, cycle["value"], places=0)

    def test_the_rated_clock_is_recorded_separately_from_any_board(self) -> None:
        # Arrange
        facts = facts_for("upd7725")

        # Act
        rated = facts["maximumClockHz"]["value"]

        # Assert
        self.assertGreater(rated, 8_000_000)

    def test_the_earlier_part_of_the_family_is_recorded_for_contrast(self) -> None:
        # Arrange
        parts = declared()["parts"]

        # Act
        earlier = [
            one["predecessorForContrast"]["clocksPerInstruction"]
            for one in parts
            if one["part"] == "upd7725"
        ]

        # Assert
        self.assertEqual(earlier, [2])


def after_adding(destination: int, asl: int = 0) -> Part:
    chip = upd7725.Cpu("upd7725", fill=0)
    registers = chip.registers
    registers.a = 0x1234
    registers.b = 0x7FFF
    chip.flags_a = upd7725.Flags()
    chip.flags_b = upd7725.Flags()
    registers.pc = 0
    chip.stores.program[0] = an_operation(
        alu=ADD, pselect=FROM_BUS, asl=asl, src=FROM_B, dst=destination
    )
    chip.step()
    return chip


class SupersededArithmeticTest(unittest.TestCase):
    def test_the_document_says_the_arithmetic_becomes_a_nop(self) -> None:
        # Arrange
        facts = facts_for("upd7725")

        # Act
        superseded = facts["arithmeticSupersededByItsOwnDestination"]["value"]

        # Assert
        self.assertTrue(superseded)

    def test_arithmetic_into_nowhere_still_sets_the_flags(self) -> None:
        # Arrange
        destination = TO_NOWHERE

        # Act
        chip = after_adding(destination)

        # Assert
        self.assertEqual(int(chip.flags_a), 0x33)

    def test_arithmetic_over_its_own_accumulator_sets_no_flags(self) -> None:
        # Arrange
        destination = TO_A

        # Act
        chip = after_adding(destination)

        # Assert
        self.assertEqual(int(chip.flags_a), 0)

    def test_and_the_moved_value_is_what_lands(self) -> None:
        # Arrange
        destination = TO_A

        # Act
        chip = after_adding(destination)

        # Assert
        self.assertEqual(chip.registers.word("a"), 0x7FFF)

    def test_arithmetic_over_the_other_accumulator_still_sets_the_flags(self) -> None:
        # Arrange
        destination = TO_B

        # Act
        chip = after_adding(destination)

        # Assert
        self.assertEqual(int(chip.flags_a), 0x33)

    def test_the_rule_follows_the_accumulator_the_arithmetic_names(self) -> None:
        # Arrange
        destination = TO_B

        # Act
        chip = after_adding(destination, asl=1)

        # Assert
        self.assertEqual(int(chip.flags_b), 0)

    def test_and_not_the_other_one(self) -> None:
        # Arrange
        destination = TO_A

        # Act
        chip = after_adding(destination, asl=1)

        # Assert
        self.assertEqual(int(chip.flags_b), 0x33)


class MultiplierTest(unittest.TestCase):
    def test_the_document_gives_a_thirty_one_bit_product(self) -> None:
        # Arrange
        facts = facts_for("upd7725")

        # Act
        bits = facts["multiplier"]["productBits"]

        # Assert
        self.assertEqual(bits, 31)

    def test_and_the_low_word_carries_a_zero_in_its_lowest_bit(self) -> None:
        # Arrange
        chip = upd7725.Cpu("upd7725", fill=0)
        chip.registers.k = 0x7FFF
        chip.registers.l = 0x7FFF

        # Act
        chip.step()

        # Assert
        self.assertEqual(chip.registers.word("n"), 0x0002)


class DivergenceTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        here = Path(__file__).resolve().parent
        self.entries: list[dict[str, Any]] = json.loads((here / "divergences.json").read_text())[
            "divergences"
        ]

    def test_each_entry_says_which_source_the_package_follows(self) -> None:
        # Arrange
        allowed = {"document", "reference", "corpus", "neither"}

        # Act
        followed = {entry["packageFollows"] for entry in self.entries}

        # Assert
        self.assertEqual(followed - allowed, set())

    def test_each_entry_says_what_would_settle_it(self) -> None:
        # Arrange
        entries = self.entries

        # Act
        missing = [entry["id"] for entry in entries if not entry.get("wouldSettleIt")]

        # Assert
        self.assertEqual(missing, [])

    def test_the_part_with_no_document_is_named_here_too(self) -> None:
        # Arrange
        entries = self.entries

        # Act
        named = {entry["id"] for entry in entries}

        # Assert
        self.assertIn("no-document-for-the-upd96050", named)

    def test_and_it_agrees_with_the_mark_on_the_part_itself(self) -> None:
        # Arrange
        parts = declared()["parts"]

        # Act
        unverified = [part["part"] for part in parts if not part["verified"]]

        # Assert
        self.assertEqual(unverified, ["upd96050"])

    def test_the_corpus_being_a_recording_is_recorded(self) -> None:
        # Arrange
        wanted = "the-corpus-was-recorded-from-an-emulator"

        # Act
        entry = next(item for item in self.entries if item["id"] == wanted)

        # Assert
        self.assertEqual(entry["severity"], "high")


if __name__ == "__main__":
    unittest.main()
