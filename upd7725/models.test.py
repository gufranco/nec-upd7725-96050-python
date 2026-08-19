import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from upd7725 import models


class CatalogueTest(unittest.TestCase):
    def test_the_package_names_every_processor_it_covers(self):
        self.assertEqual(set(models.MODELS), {"upd7725", "upd96050"})

    def test_a_model_says_how_wide_each_of_its_three_registers_is(self):
        found = models.describe("upd7725")

        self.assertEqual((found.counter_bits, found.table_bits, found.pointer_bits), (11, 10, 8))

    def test_the_larger_part_is_wider_in_all_three(self):
        smaller = models.describe("upd7725")
        larger = models.describe("upd96050")

        self.assertGreater(larger.counter_bits, smaller.counter_bits)
        self.assertGreater(larger.table_bits, smaller.table_bits)
        self.assertGreater(larger.pointer_bits, smaller.pointer_bits)

    def test_each_store_is_exactly_as_long_as_its_register_can_reach(self):
        for found in models.MODELS.values():
            self.assertEqual(found.program_words, 1 << found.counter_bits, found.name)
            self.assertEqual(found.table_words, 1 << found.table_bits, found.name)
            self.assertEqual(found.scratch_words, 1 << found.pointer_bits, found.name)

    def test_a_model_name_is_matched_however_it_is_written(self):
        for written in ("UPD7725", "upd-7725", "uPD_7725", "7725"):
            self.assertEqual(models.describe(written).name, "upd7725")

    def test_a_model_says_which_cartridge_parts_run_on_it(self):
        self.assertIn("st011", models.describe("upd96050").parts)

    def test_and_the_family_the_other_one_carries(self):
        self.assertIn("dsp1", models.describe("upd7725").parts)

    def test_every_part_named_belongs_to_exactly_one_processor(self):
        seen = [part for found in models.MODELS.values() for part in found.parts]

        self.assertEqual(len(seen), len(set(seen)))

    def test_a_processor_the_package_does_not_have_is_refused_by_name(self):
        with self.assertRaises(models.UnknownModelError):
            models.describe("upd7720")

    def test_and_the_refusal_says_why_rather_than_only_that(self):
        with self.assertRaises(models.UnknownModelError) as raised:
            models.describe("upd7720")

        self.assertIn("reference", str(raised.exception))

    def test_a_name_that_is_no_part_at_all_lists_what_is_available(self):
        with self.assertRaises(models.UnknownModelError) as raised:
            models.describe("nonsense")

        self.assertIn("upd7725", str(raised.exception))

    def test_every_refusal_carries_a_reason(self):
        for name, why in models.NOT_MODELLED.items():
            self.assertTrue(why, name)

    def test_a_model_prints_as_its_name_and_its_widths(self):
        printed = repr(models.describe("upd96050"))

        self.assertIn("upd96050", printed)
        self.assertIn("14", printed)

    def test_a_model_says_what_it_is(self):
        self.assertTrue(models.describe("upd7725").summary)


class CarryingTest(unittest.TestCase):
    def test_a_cartridge_part_names_the_processor_it_runs_on(self):
        self.assertEqual(models.carrying("st011").name, "upd96050")

    def test_and_the_family_the_other_processor_carries(self):
        self.assertEqual(models.carrying("DSP-4").name, "upd7725")

    def test_a_part_no_processor_here_carries_is_refused(self):
        with self.assertRaises(models.UnknownModelError):
            models.carrying("cx4")


class BuildTest(unittest.TestCase):
    def test_a_processor_is_built_from_its_model(self):
        built = models.describe("upd7725").build(fill=0)

        self.assertEqual(len(built.stores.program), 2048)

    def test_options_reach_the_processor_that_gets_built(self):
        built = models.describe("upd7725").build(fill=0xABCD)

        self.assertEqual(built.stores.scratch[0], 0xABCD)


if __name__ == "__main__":
    unittest.main()
