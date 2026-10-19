from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Literal

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conformance import stack, testroms
from conformance.printed import (
    CALL_LOW,
    JUMP_LOW,
    JUMP_THROUGH_OUTPUT,
    a_jump,
    a_return,
)
from upd7725 import MODELS

SMALLER = "upd7725"

LARGER = "upd96050"


def a_program(placed: dict[int, int], model: str = SMALLER) -> list[int]:
    words = [0] * MODELS[model].program_words
    for at, word in placed.items():
        words[at] = word
    return words


def an_image(
    placed: dict[int, int], model: str = SMALLER, order: Literal["big", "little"] = "big"
) -> bytes:
    body = b"".join(word.to_bytes(3, order) for word in a_program(placed, model))
    return body + bytes(MODELS[model].table_words * 2)


def nested(depth: int) -> dict[int, int]:
    placed = {0: a_jump(CALL_LOW, 0x10), 1: a_jump(JUMP_LOW, 1)}
    for level in range(1, depth):
        placed[0x10 * level] = a_jump(CALL_LOW, 0x10 * (level + 1))
        placed[0x10 * level + 1] = a_return()
    placed[0x10 * depth] = a_return()
    return placed


def an_entry(name: str, image: bytes, canonical: bytes) -> dict[str, Any]:
    return {
        "id": name,
        "sha256": stack.digest(image),
        "canonicalSha256": stack.digest(canonical),
    }


def a_library(entries: list[dict[str, Any]], held: dict[str, Any] | None = None) -> Path:
    where = Path(tempfile.mkdtemp())
    (where / "testroms.json").write_text(json.dumps({"cartridges": entries}))
    (where / "measured.json").write_text(json.dumps(held or {}))
    (where / "images").mkdir()
    return where


def placing(where: Path, **images: bytes) -> None:
    for name, image in images.items():
        (where / "images" / name).write_bytes(image)


def running(where: Path, *argv: str) -> tuple[int, list[str]]:
    said: list[str] = []
    code = testroms.main(
        [*argv],
        said.append,
        where / "testroms.json",
        where / "measured.json",
    )
    return code, said


def recorded() -> dict[str, Any]:
    held: dict[str, Any] = json.loads(testroms.MEASURED.read_text())
    return held


class LayoutTest(unittest.TestCase):
    def test_reversing_every_word_turns_a_low_byte_first_dump_into_the_canonical_image(
        self,
    ) -> None:
        # Arrange
        placed = nested(2)

        # Act
        found = testroms.reordered(an_image(placed, order="little"), SMALLER)

        # Assert
        self.assertEqual(found, an_image(placed))

    def test_table_words_are_reversed_two_bytes_at_a_time(self) -> None:
        # Arrange
        image = an_image({})[:-2] + b"\x34\x12"

        # Act
        found = testroms.reordered(image, SMALLER)

        # Assert
        self.assertEqual(found[-2:], b"\x12\x34")

    def test_each_part_is_told_apart_by_the_length_of_its_image(self) -> None:
        # Arrange
        sizes = (8192, 53248, 8193)

        # Act
        found = [testroms.model_for(size) for size in sizes]

        # Assert
        self.assertEqual(found, [SMALLER, LARGER, None])


class MeasureTest(unittest.TestCase):
    def test_calls_within_the_printed_levels_are_within(self) -> None:
        # Arrange
        image = an_image(nested(4))

        # Act
        found = testroms.measure(image)

        # Assert
        self.assertEqual((found or {}).get("deepest"), 4)
        self.assertEqual((found or {}).get("verdict"), testroms.WITHIN)

    def test_one_call_past_them_is_beyond(self) -> None:
        # Arrange
        image = an_image(nested(5))

        # Act
        found = testroms.measure(image)

        # Assert
        self.assertEqual((found or {}).get("verdict"), testroms.BEYOND)

    def test_a_jump_through_the_output_register_cannot_be_bounded(self) -> None:
        # Arrange
        image = an_image({0: a_jump(JUMP_THROUGH_OUTPUT)}, LARGER)

        # Act
        found = testroms.measure(image)

        # Assert
        self.assertEqual((found or {}).get("indirect"), [0])
        self.assertEqual((found or {}).get("verdict"), testroms.UNBOUNDED)

    def test_an_image_of_no_part_is_not_measured(self) -> None:
        # Arrange
        image = bytes(100)

        # Act
        found = testroms.measure(image)

        # Assert
        self.assertIsNone(found)


class RunnerTest(unittest.TestCase):
    def test_with_no_folder_named_nothing_is_checked_and_it_says_so(self) -> None:
        # Arrange
        where = a_library([{"id": "a"}, {"id": "b"}])

        # Act
        code, said = running(where)

        # Assert
        self.assertEqual(code, 0)
        self.assertEqual(
            said, ["  0 of 2 test images examined: no folder named, so none was checked"]
        )

    def test_a_dump_whose_measure_matches_the_record_passes(self) -> None:
        # Arrange
        dump, canonical = an_image(nested(2), order="little"), an_image(nested(2))
        held = {"one": {**(testroms.measure(canonical) or {}), "canonicalMatches": True}}
        where = a_library([an_entry("one", dump, canonical)], held)
        placing(where, dump=dump, stranger=bytes(16))
        (where / "images" / "folder").mkdir()

        # Act
        code, said = running(where, str(where / "images"))

        # Assert
        self.assertEqual((code, said), (0, ["  1 of 1 test images examined"]))

    def test_an_image_already_in_the_canonical_layout_is_read_as_it_stands(self) -> None:
        # Arrange
        dump, canonical = an_image(nested(1), order="little"), an_image(nested(1))
        where = a_library([an_entry("one", dump, canonical)])
        placing(where, canonical=canonical)

        # Act
        code, _ = running(where, testroms.RECORDING, str(where / "images"))

        # Assert
        self.assertEqual(code, 0)
        self.assertEqual(json.loads((where / "measured.json").read_text())["one"]["deepest"], 1)

    def test_a_measure_that_moved_from_the_record_fails(self) -> None:
        # Arrange
        dump, canonical = an_image(nested(2), order="little"), an_image(nested(2))
        where = a_library([an_entry("one", dump, canonical)], {"one": {"deepest": 1}})
        placing(where, dump=dump)

        # Act
        code, said = running(where, str(where / "images"))

        # Assert
        self.assertEqual(code, 1)
        self.assertIn("! one: measured", said[1])

    def test_a_program_needing_more_levels_than_the_part_has_fails(self) -> None:
        # Arrange
        dump, canonical = an_image(nested(5), order="little"), an_image(nested(5))
        held = {"one": {**(testroms.measure(canonical) or {}), "canonicalMatches": True}}
        where = a_library([an_entry("one", dump, canonical)], held)
        placing(where, dump=dump)

        # Act
        code, said = running(where, str(where / "images"))

        # Assert
        self.assertEqual(code, 1)
        self.assertEqual(said[1:], ["  ! one: needs 5 levels, more than the part has"])

    def test_a_dump_that_does_not_reorder_into_the_named_image_fails(self) -> None:
        # Arrange
        dump, named = an_image(nested(1), order="little"), an_image(nested(3))
        held = {"one": {**(testroms.measure(an_image(nested(1))) or {}), "canonicalMatches": False}}
        where = a_library([an_entry("one", dump, named)], held)
        placing(where, dump=dump)

        # Act
        code, said = running(where, str(where / "images"))

        # Assert
        self.assertEqual(code, 1)
        self.assertEqual(said[1:], ["  ! one: reordered, it is not the image the record names"])

    def test_a_listed_digest_of_no_part_is_stepped_over(self) -> None:
        # Arrange
        odd = bytes(16)
        where = a_library([an_entry("one", odd, odd)])
        placing(where, odd=odd)

        # Act
        code, said = running(where, str(where / "images"))

        # Assert
        self.assertEqual((code, said), (0, ["  0 of 1 test images examined"]))


class TheRecordedImagesTest(unittest.TestCase):
    def test_every_program_for_the_smaller_part_fits_its_four_levels(self) -> None:
        # Arrange
        held = recorded()
        names = (
            "upd7725-91e87d11",
            "upd7725-d789cb3c",
            "upd7725-03ef4ef2",
            "upd7725-0971b08f",
            "upd7725-752d03b2",
        )

        # Act
        found = {name: (held[name]["verdict"], held[name]["canonicalMatches"]) for name in names}

        # Assert
        self.assertEqual(found, dict.fromkeys(names, (testroms.WITHIN, True)))
        self.assertEqual(max(held[name]["deepest"] for name in names), 3)
        self.assertEqual(MODELS[SMALLER].stack_levels, 4)

    def test_the_larger_parts_programs_are_bounded_where_a_walk_can_bound_them(self) -> None:
        # Arrange
        held = recorded()

        # Act
        found = [
            (
                held[name]["verdict"],
                held[name]["deepest"],
                held[name]["indirect"],
                held[name]["canonicalMatches"],
            )
            for name in ("upd96050-fa9bced8", "upd96050-8b2b3f3f")
        ]

        # Assert
        self.assertEqual(
            found, [(testroms.WITHIN, 1, [], True), (testroms.UNBOUNDED, 0, [0x13], True)]
        )


if __name__ == "__main__":
    unittest.main()
