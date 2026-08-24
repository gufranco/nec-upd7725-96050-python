import json
import sys
import unittest
from pathlib import Path
from typing import Any, override

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import reference

from upd7725 import models
from upd7725.flags import Flags

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


class DocumentTest(unittest.TestCase):
    """That the file names its source well enough for somebody to go and check."""

    def test_the_verified_part_names_the_document_it_was_read_from(self) -> None:
        for one in declared()["parts"]:
            if not one["verified"]:
                continue
            for named in ("publisher", "title", "kind", "date", "readOn"):
                self.assertIn(named, one["document"], one["part"])

    def test_and_pins_it_by_digest_so_the_reading_can_be_repeated(self) -> None:
        for one in declared()["parts"]:
            if not one["verified"]:
                continue
            self.assertRegex(one["document"]["sha256"], r"^[0-9a-f]{64}$", one["part"])

    def test_and_says_how_the_printed_number_relates_to_the_file(self) -> None:
        for one in declared()["parts"]:
            if not one["verified"]:
                continue
            self.assertIn("pageNumbering", one["document"], one["part"])

    def test_every_fact_carries_the_words_it_came_from(self) -> None:
        for name, fact in facts_for("upd7725").items():
            self.assertIn("quote", fact, name)
            self.assertGreater(len(fact["quote"]), 20, name)

    def test_and_the_page_those_words_are_printed_on(self) -> None:
        pages = declared()["parts"][0]["document"]["pdfPages"]
        for name, fact in facts_for("upd7725").items():
            self.assertIsInstance(fact.get("page"), int, name)
            self.assertGreaterEqual(fact["page"], 1, name)
            self.assertLess(fact["page"], pages, name)

    def test_an_unverified_part_says_so_and_says_what_would_settle_it(self) -> None:
        for one in declared()["parts"]:
            if one["verified"]:
                continue
            self.assertIsNone(one["document"], one["part"])
            self.assertIn("howToSettleIt", one["unverified"], one["part"])

    def test_the_authority_order_is_written_down(self) -> None:
        self.assertGreaterEqual(len(declared()["authority"]["order"]), 2)


class LookupTest(unittest.TestCase):
    def test_asking_for_a_part_the_file_does_not_carry_says_so(self) -> None:
        with self.assertRaises(AssertionError) as raised:
            facts_for("upd7720")

        self.assertIn("upd7720", str(raised.exception))


class WidthTest(unittest.TestCase):
    """That the model is built to the widths the manufacturer printed.

    This is the gate the datasheet becomes. A figure quoted in prose rots quietly;
    a figure something reads and compares cannot.
    """

    def test_the_program_counter_is_as_wide_as_the_document_says(self) -> None:
        facts = facts_for("upd7725")

        self.assertEqual(
            models.describe("upd7725").counter_bits, facts["programCounterBits"]["value"]
        )

    def test_and_addresses_as_many_words(self) -> None:
        facts = facts_for("upd7725")

        self.assertEqual(models.describe("upd7725").program_words, facts["programWords"]["value"])

    def test_the_table_pointer_is_as_wide_as_the_document_says(self) -> None:
        facts = facts_for("upd7725")

        self.assertEqual(models.describe("upd7725").table_bits, facts["romPointerBits"]["value"])

    def test_and_addresses_as_many_table_words(self) -> None:
        facts = facts_for("upd7725")

        self.assertEqual(models.describe("upd7725").table_words, facts["dataRomWords"]["value"])

    def test_the_scratch_pointer_is_as_wide_as_the_document_says(self) -> None:
        facts = facts_for("upd7725")

        self.assertEqual(models.describe("upd7725").pointer_bits, facts["dataPointerBits"]["value"])

    def test_and_addresses_as_many_scratch_words(self) -> None:
        facts = facts_for("upd7725")

        self.assertEqual(models.describe("upd7725").scratch_words, facts["dataRamWords"]["value"])


class StackTest(unittest.TestCase):
    """The one the field gets wrong, so the one worth pinning hardest."""

    def test_the_stack_is_as_deep_as_the_document_says(self) -> None:
        facts = facts_for("upd7725")

        self.assertEqual(models.describe("upd7725").stack_levels, facts["stackLevels"]["value"])

    def test_the_reference_holds_the_same_depth_as_the_model(self) -> None:
        self.assertEqual(
            reference.STACK_LEVELS[reference.UPD7725], models.describe("upd7725").stack_levels
        )

    def test_a_pointer_that_wide_reaches_every_slot_and_no_further(self) -> None:
        model = models.describe("upd7725")

        self.assertEqual(1 << model.stack_pointer_bits, model.stack_levels)

    def test_the_document_admits_it_does_not_say_what_a_fifth_call_does(self) -> None:
        self.assertIn("notStated", facts_for("upd7725")["stackLevels"])

    def test_the_larger_part_holds_more_and_is_not_claimed_as_verified(self) -> None:
        larger = models.describe("upd96050")

        self.assertGreater(larger.stack_levels, models.describe("upd7725").stack_levels)
        for one in declared()["parts"]:
            if one["part"] == "upd96050":
                self.assertFalse(one["verified"])


class CycleTest(unittest.TestCase):
    """What makes a cycle claim a claim rather than a word."""

    def test_the_document_gives_one_clock_per_instruction(self) -> None:
        self.assertEqual(facts_for("upd7725")["clocksPerInstruction"]["value"], 1)

    def test_and_says_every_instruction_takes_the_same_one(self) -> None:
        self.assertTrue(facts_for("upd7725")["everyInstructionSameLength"]["value"])

    def test_so_one_step_is_one_cycle(self) -> None:
        chip = models.describe("upd7725").build(fill=0)

        chip.step()

        self.assertEqual(chip.cycles, 1)

    def test_and_a_run_of_many_is_that_many_cycles(self) -> None:
        chip = models.describe("upd7725").build(fill=0)

        chip.run_for(1000)

        self.assertEqual(chip.cycles, 1000)

    def test_a_part_that_has_run_nothing_has_spent_no_cycles(self) -> None:
        self.assertEqual(models.describe("upd7725").build(fill=0).cycles, 0)

    def test_the_cycle_time_and_the_clock_it_belongs_to_agree(self) -> None:
        facts = facts_for("upd7725")
        cycle = facts["instructionCycleNanoseconds"]
        clock = cycle["atClockHz"]

        self.assertAlmostEqual(1e9 / clock, cycle["value"], places=0)

    def test_the_rated_clock_is_recorded_separately_from_any_board(self) -> None:
        self.assertGreater(facts_for("upd7725")["maximumClockHz"]["value"], 8_000_000)

    def test_the_earlier_part_of_the_family_is_recorded_for_contrast(self) -> None:
        for one in declared()["parts"]:
            if one["part"] != "upd7725":
                continue
            earlier = one["predecessorForContrast"]
            self.assertEqual(earlier["clocksPerInstruction"], 2)


class SupersededArithmeticTest(unittest.TestCase):
    """The rule that a move over its own accumulator cancels the arithmetic.

    Discarding the result is not the same as not computing it, because the
    difference is the flags, and the next conditional branch reads them. Both
    implementations here ran the arithmetic and overwrote it, and so did the
    emulator the corpus was recorded from.
    """

    def _run(self, destination: int, asl: int = 0) -> Any:
        chip = models.describe("upd7725").build(fill=0)
        registers = chip.registers
        registers.a = 0x7FFF
        registers.b = 0x7FFF
        chip.flags_a = Flags()
        chip.flags_b = Flags()
        registers.pc = 0
        chip.stores.program[0] = 1 << 20 | 5 << 16 | asl << 15 | 2 << 4 | destination
        chip.step()
        return chip

    def test_the_document_says_the_arithmetic_becomes_a_nop(self) -> None:
        self.assertTrue(facts_for("upd7725")["arithmeticSupersededByItsOwnDestination"]["value"])

    def test_arithmetic_into_nowhere_still_sets_the_flags(self) -> None:
        chip = self._run(destination=0)

        self.assertNotEqual(int(chip.flags_a), 0)

    def test_arithmetic_over_its_own_accumulator_sets_no_flags(self) -> None:
        chip = self._run(destination=1)

        self.assertEqual(int(chip.flags_a), 0)

    def test_and_the_moved_value_is_what_lands(self) -> None:
        chip = self._run(destination=1)

        self.assertEqual(chip.registers.word("a"), 0x7FFF)

    def test_arithmetic_over_the_other_accumulator_still_sets_the_flags(self) -> None:
        chip = self._run(destination=2)

        self.assertNotEqual(int(chip.flags_a), 0)

    def test_the_rule_follows_the_accumulator_the_arithmetic_names(self) -> None:
        chip = self._run(destination=2, asl=1)

        self.assertEqual(int(chip.flags_b), 0)

    def test_and_not_the_other_one(self) -> None:
        chip = self._run(destination=1, asl=1)

        self.assertNotEqual(int(chip.flags_b), 0)


class MultiplierTest(unittest.TestCase):
    def test_the_document_gives_a_thirty_one_bit_product(self) -> None:
        self.assertEqual(facts_for("upd7725")["multiplier"]["productBits"], 31)

    def test_and_the_low_word_carries_a_zero_in_its_lowest_bit(self) -> None:
        chip = models.describe("upd7725").build(fill=0)
        chip.registers.k = 0x7FFF
        chip.registers.l = 0x7FFF

        chip.step()

        self.assertEqual(chip.registers.word("n") & 1, 0)


class DivergenceTest(unittest.TestCase):
    """The standing of each fact, kept in the file the family reads for that.

    `hardware.json` already marks the part with no document. This checks that the
    same thing is said where a reader of any sibling repository will look for it,
    so the two cannot part company.
    """

    @override
    def setUp(self) -> None:
        here = Path(__file__).resolve().parent
        self.entries: list[dict[str, Any]] = json.loads((here / "divergences.json").read_text())[
            "divergences"
        ]

    def test_each_entry_says_which_source_the_package_follows(self) -> None:
        allowed = {"document", "reference", "corpus", "neither"}

        self.assertEqual({entry["packageFollows"] for entry in self.entries} - allowed, set())

    def test_each_entry_says_what_would_settle_it(self) -> None:
        missing = [entry["id"] for entry in self.entries if not entry.get("wouldSettleIt")]

        self.assertEqual(missing, [])

    def test_the_part_with_no_document_is_named_here_too(self) -> None:
        named = {entry["id"] for entry in self.entries}

        self.assertIn("no-document-for-the-upd96050", named)

    def test_and_it_agrees_with_the_mark_on_the_part_itself(self) -> None:
        unverified = [part for part in declared()["parts"] if not part["verified"]]

        self.assertEqual(len(unverified), 1)

    def test_the_corpus_being_a_recording_is_recorded(self) -> None:
        entry = next(
            item
            for item in self.entries
            if item["id"] == "the-corpus-was-recorded-from-an-emulator"
        )

        self.assertEqual(entry["severity"], "high")


if __name__ == "__main__":
    unittest.main()
