import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from upd7725 import errors, models


class CatalogueTest(unittest.TestCase):
    def test_the_package_names_every_processor_it_covers(self) -> None:
        self.assertEqual(set(models.MODELS), {"upd7725", "upd96050"})

    def test_a_model_says_how_wide_each_of_its_three_registers_is(self) -> None:
        found = models.describe("upd7725")

        self.assertEqual((found.counter_bits, found.table_bits, found.pointer_bits), (11, 10, 8))

    def test_each_store_is_exactly_as_long_as_its_register_can_reach(self) -> None:
        for found in models.MODELS.values():
            self.assertEqual(found.program_words, 1 << found.counter_bits, found.name)
            self.assertEqual(found.table_words, 1 << found.table_bits, found.name)
            self.assertEqual(found.scratch_words, 1 << found.pointer_bits, found.name)

    def test_a_model_name_is_matched_however_it_is_written(self) -> None:
        for written in ("UPD7725", "upd-7725", "uPD_7725", "7725"):
            self.assertEqual(models.describe(written).name, "upd7725")

    def test_a_processor_the_package_does_not_have_is_refused_by_name(self) -> None:
        with self.assertRaises(errors.UnknownModelError):
            models.describe("upd7720")

    def test_and_the_refusal_says_why_rather_than_only_that(self) -> None:
        with self.assertRaises(errors.UnknownModelError) as raised:
            models.describe("upd7720")

        self.assertIn("reference", str(raised.exception))

    def test_a_name_nothing_here_recognises_is_refused_with_the_list(self) -> None:
        """Neither an alias nor a part named as deliberately unmodelled.

        The two refusals read differently on purpose: one says why a known part
        is absent, and this one says what the package does have, because a caller
        who typed something unrecognisable needs the list rather than a reason.
        """
        with self.assertRaises(errors.UnknownModelError) as raised:
            models.describe("nothing-like-a-part-number")

        self.assertIn("upd7725", str(raised.exception))
        self.assertIn("upd96050", str(raised.exception))

    def test_the_stack_pointer_follows_from_the_depth(self) -> None:
        """A four-level stack is reached by two bits, an eight-level one by three.

        It is derived rather than declared so the two cannot disagree, which is
        worth a check because a second number is exactly what would drift.
        """
        self.assertEqual(models.describe("upd7725").stack_pointer_bits, 2)
        self.assertEqual(models.describe("upd96050").stack_pointer_bits, 3)

    def test_every_refusal_carries_a_reason(self) -> None:
        for name, why in models.NOT_MODELLED.items():
            self.assertTrue(why, name)

    def test_a_model_prints_as_its_name_and_its_widths(self) -> None:
        printed = repr(models.describe("upd96050"))

        self.assertIn("upd96050", printed)
        self.assertIn("14", printed)

    def test_a_model_says_what_it_is(self) -> None:
        self.assertTrue(models.describe("upd7725").summary)


class BuildTest(unittest.TestCase):
    def test_a_processor_is_built_from_its_model(self) -> None:
        built = models.describe("upd7725").build(fill=0)

        self.assertEqual(len(built.stores.program), 2048)

    def test_options_reach_the_processor_that_gets_built(self) -> None:
        built = models.describe("upd7725").build(fill=0xABCD)

        self.assertEqual(built.stores.scratch[0], 0xABCD)


if __name__ == "__main__":
    unittest.main()
