from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from typing import TYPE_CHECKING, Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import upd7725
from conformance import reference
from conformance.printed import (
    CALL_LOW,
    TO_POINTER,
    TOP_WORD,
    a_jump,
    a_load,
    an_operation,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from conformance.printed import Part

HARDWARE = Path(__file__).resolve().parent / "hardware.json"

CALL_LIMIT = 64


def declared() -> dict[str, Any]:
    held: dict[str, Any] = json.loads(HARDWARE.read_text())
    return held


def facts_for(part: str) -> dict[str, Any]:
    found: dict[str, Any] = next(one for one in declared()["parts"] if one["part"] == part)["facts"]
    return found


def a_quiet(name: str) -> Part:
    return upd7725.Cpu(name, fill=0).reset()


def counter_bits(name: str) -> int:
    part = a_quiet(name)
    part.registers.pc = TOP_WORD
    return int(part.registers.pc).bit_length()


def program_words(name: str) -> int:
    return len(a_quiet(name).stores.program)


def table_bits(name: str) -> int:
    part = a_quiet(name)
    part.registers.rp = 0
    part.stores.program[part.registers.pc] = an_operation(rpdcr=1)
    part.step()
    return int(part.registers.rp).bit_length()


def table_words(name: str) -> int:
    return len(a_quiet(name).stores.table)


def pointer_bits(name: str) -> int:
    part = a_quiet(name)
    part.stores.program[part.registers.pc] = a_load(TOP_WORD, TO_POINTER)
    part.step()
    return int(part.registers.dp).bit_length()


def scratch_words(name: str) -> int:
    return len(a_quiet(name).stores.scratch)


def stack_levels(name: str) -> int:
    part = a_quiet(name)
    for at in range(CALL_LIMIT):
        part.stores.program[at] = a_jump(CALL_LOW, at + 1)
    part.registers.sp = 0
    part.run_until(lambda chip: chip.steps > 0 and chip.registers.sp == 0, limit=CALL_LIMIT)
    return int(part.steps)


MEASURED: dict[str, Callable[[str], int]] = {
    "programWords": program_words,
    "programCounterBits": counter_bits,
    "dataRomWords": table_words,
    "romPointerBits": table_bits,
    "dataRamWords": scratch_words,
    "dataPointerBits": pointer_bits,
    "stackLevels": stack_levels,
}


class WidthTest(unittest.TestCase):
    def test_the_program_counter_is_as_wide_as_the_document_says(self) -> None:
        # Arrange
        printed = facts_for("upd7725")["programCounterBits"]["value"]

        # Act
        found = counter_bits("upd7725")

        # Assert
        self.assertEqual(found, printed)

    def test_and_addresses_as_many_words(self) -> None:
        # Arrange
        printed = facts_for("upd7725")["programWords"]["value"]

        # Act
        found = program_words("upd7725")

        # Assert
        self.assertEqual(found, printed)

    def test_the_table_pointer_is_as_wide_as_the_document_says(self) -> None:
        # Arrange
        printed = facts_for("upd7725")["romPointerBits"]["value"]

        # Act
        found = table_bits("upd7725")

        # Assert
        self.assertEqual(found, printed)

    def test_and_addresses_as_many_table_words(self) -> None:
        # Arrange
        printed = facts_for("upd7725")["dataRomWords"]["value"]

        # Act
        found = table_words("upd7725")

        # Assert
        self.assertEqual(found, printed)

    def test_the_scratch_pointer_is_as_wide_as_the_document_says(self) -> None:
        # Arrange
        printed = facts_for("upd7725")["dataPointerBits"]["value"]

        # Act
        found = pointer_bits("upd7725")

        # Assert
        self.assertEqual(found, printed)

    def test_and_addresses_as_many_scratch_words(self) -> None:
        # Arrange
        printed = facts_for("upd7725")["dataRamWords"]["value"]

        # Act
        found = scratch_words("upd7725")

        # Assert
        self.assertEqual(found, printed)


class StackTest(unittest.TestCase):
    def test_the_stack_is_as_deep_as_the_document_says(self) -> None:
        # Arrange
        printed = facts_for("upd7725")["stackLevels"]["value"]

        # Act
        found = stack_levels("upd7725")

        # Assert
        self.assertEqual(found, printed)

    def test_the_reference_holds_the_same_depth_as_the_model(self) -> None:
        # Arrange
        held = reference.STACK_LEVELS[reference.UPD7725]

        # Act
        found = stack_levels("upd7725")

        # Assert
        self.assertEqual(held, found)

    def test_a_pointer_that_wide_reaches_every_slot_and_no_further(self) -> None:
        # Arrange
        levels = facts_for("upd7725")["stackLevels"]["value"]
        part = a_quiet("upd7725")

        # Act
        reached = []
        for at in range(2 * levels):
            part.registers.sp = at
            reached.append(part.registers.sp)

        # Assert
        self.assertEqual(reached, [at % levels for at in range(2 * levels)])

    def test_the_document_admits_it_does_not_say_what_a_fifth_call_does(self) -> None:
        # Arrange
        facts = facts_for("upd7725")

        # Act
        printed = facts["stackLevels"]

        # Assert
        self.assertIn("notStated", printed)

    def test_the_larger_part_holds_more_and_is_not_claimed_as_verified(self) -> None:
        # Arrange
        smaller = stack_levels("upd7725")

        # Act
        larger = stack_levels("upd96050")

        # Assert
        self.assertGreater(larger, smaller)
        self.assertEqual(
            [one["verified"] for one in declared()["parts"] if one["part"] == "upd96050"], [False]
        )


def overclaimed(facts: dict[str, Any], measured: dict[str, Callable[[str], int]]) -> list[str]:
    found = []
    for name, measure in measured.items():
        fact = facts[name]
        holding = {part for part in upd7725.MODELS if measure(part) == fact["value"]}
        if set(fact["appliesTo"]) != holding:
            found.append(f"{name}: claims {fact['appliesTo']}, holds for {sorted(holding)}")
    return found


def the_facts() -> dict[str, Any]:
    held: dict[str, Any] = declared()["parts"][0]["facts"]
    return held


class PartScopeTest(unittest.TestCase):
    def test_every_fact_names_the_parts_it_governs(self) -> None:
        # Arrange
        facts = the_facts()

        # Act
        unscoped = [
            name
            for name, fact in facts.items()
            if not isinstance(fact.get("appliesTo"), list) or not fact["appliesTo"]
        ]

        # Assert
        self.assertEqual(unscoped, [])

    def test_and_every_part_it_names_is_one_the_package_builds(self) -> None:
        # Arrange
        facts = the_facts()

        # Act
        invented = sorted(
            {
                part
                for fact in facts.values()
                for part in fact["appliesTo"]
                if part not in upd7725.MODELS
            }
        )

        # Assert
        self.assertEqual(invented, [])

    def test_a_fact_the_parts_disagree_on_is_not_claimed_for_both(self) -> None:
        # Arrange
        facts = the_facts()

        # Act
        found = overclaimed(facts, MEASURED)

        # Assert
        self.assertEqual(found, [])

    def test_and_a_width_widened_by_hand_would_be_reported(self) -> None:
        # Arrange
        facts = {"programWords": {"value": 2048, "appliesTo": ["upd7725", "upd96050"]}}

        # Act
        found = overclaimed(facts, {"programWords": program_words})

        # Assert
        self.assertEqual(
            found, ["programWords: claims ['upd7725', 'upd96050'], holds for ['upd7725']"]
        )

    def test_a_shared_fact_reaches_both_parts(self) -> None:
        # Arrange
        facts = the_facts()

        # Act
        shared = facts["aluOperations"]["appliesTo"]

        # Assert
        self.assertEqual(sorted(shared), sorted(upd7725.MODELS))

    def test_a_fact_that_reaches_one_part_says_why(self) -> None:
        # Arrange
        facts = the_facts()

        # Act
        narrow = [
            name
            for name, fact in facts.items()
            if len(fact["appliesTo"]) < len(upd7725.MODELS) and "whyNotBoth" not in fact
        ]

        # Assert
        self.assertEqual(narrow, [])


if __name__ == "__main__":
    unittest.main()
