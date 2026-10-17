import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import upd7725

REFUSED_BY_NAME = ("upd7720", "upd77p25")


def refusals(names: tuple[str, ...]) -> list[str]:
    said = []
    for name in names:
        try:
            upd7725.Cpu(name)
        except upd7725.UnknownModelError as error:
            said.append(str(error))
    return said


class CatalogueTest(unittest.TestCase):
    def test_the_package_names_every_processor_it_covers(self) -> None:
        # Arrange
        catalogue = upd7725.MODELS

        # Act
        names = set(catalogue)

        # Assert
        self.assertEqual(names, {"upd7725", "upd96050"})

    def test_every_entry_is_a_model(self) -> None:
        # Arrange
        catalogue = upd7725.MODELS

        # Act
        kinds = {type(one) for one in catalogue.values()}

        # Assert
        self.assertEqual(kinds, {upd7725.Model})

    def test_a_model_says_how_wide_each_of_its_three_registers_is(self) -> None:
        # Arrange
        name = "upd7725"

        # Act
        found = upd7725.Cpu(name).model

        # Assert
        self.assertEqual((found.counter_bits, found.table_bits, found.pointer_bits), (11, 10, 8))

    def test_and_the_larger_part_says_the_same_of_its_own(self) -> None:
        # Arrange
        name = "upd96050"

        # Act
        found = upd7725.Cpu(name).model

        # Assert
        self.assertEqual((found.counter_bits, found.table_bits, found.pointer_bits), (14, 11, 11))

    def test_each_store_is_exactly_as_long_as_the_models_table_prints(self) -> None:
        # Arrange
        catalogue = upd7725.MODELS

        # Act
        sizes = {
            name: (one.program_words, one.table_words, one.scratch_words)
            for name, one in catalogue.items()
        }

        # Assert
        self.assertEqual(sizes, {"upd7725": (2048, 1024, 256), "upd96050": (16384, 2048, 2048)})

    def test_a_model_name_is_matched_however_it_is_written(self) -> None:
        # Arrange
        written = ("UPD7725", "upd-7725", "uPD_7725", "7725", " upd77c25 ")

        # Act
        found = {upd7725.Cpu(one).model.name for one in written}

        # Assert
        self.assertEqual(found, {"upd7725"})

    def test_every_alias_builds_the_part_it_belongs_to(self) -> None:
        # Arrange
        aliases = {alias: name for name, one in upd7725.MODELS.items() for alias in one.aliases}

        # Act
        found = {alias: upd7725.Cpu(alias).model.name for alias in aliases}

        # Assert
        self.assertEqual(found, aliases)

    def test_the_stack_pointer_follows_from_the_depth(self) -> None:
        # Arrange
        catalogue = upd7725.MODELS

        # Act
        found = {name: one.stack_pointer_bits for name, one in catalogue.items()}

        # Assert
        self.assertEqual(found, {"upd7725": 2, "upd96050": 3})

    def test_a_model_prints_as_its_name_and_its_widths(self) -> None:
        # Arrange
        found = upd7725.MODELS["upd96050"]

        # Act
        printed = repr(found)

        # Assert
        self.assertEqual(
            printed, "<Model upd96050, counter 14 bits, table 11, pointer 11, stack 8>"
        )

    def test_a_model_says_what_it_is(self) -> None:
        # Arrange
        found = upd7725.MODELS["upd7725"]

        # Act
        summary = found.summary

        # Assert
        self.assertIn("uPD7725", summary)


class RefusalTest(unittest.TestCase):
    def test_a_processor_the_package_does_not_have_is_refused_by_name(self) -> None:
        # Arrange
        name = "upd7720"

        # Act
        with self.assertRaises(upd7725.UnknownModelError) as raised:
            upd7725.Cpu(name)

        # Assert
        said = str(raised.exception)
        self.assertTrue(said.startswith("upd7720 is not modelled here: "), said)

    def test_and_the_refusal_says_why_rather_than_only_that(self) -> None:
        # Arrange
        name = "upd7720"

        # Act
        with self.assertRaises(upd7725.UnknownModelError) as raised:
            upd7725.Cpu(name)

        # Assert
        said = str(raised.exception)
        self.assertIn("the reference this package is measured against does not implement it", said)

    def test_every_part_refused_by_name_carries_its_own_reason(self) -> None:
        # Arrange
        names = REFUSED_BY_NAME

        # Act
        reasons = {said.partition(": ")[2] for said in refusals(names)}

        # Assert
        self.assertEqual(len(reasons), len(REFUSED_BY_NAME))
        self.assertNotIn("", reasons)

    def test_a_refused_part_is_recognised_however_it_is_written(self) -> None:
        # Arrange
        name = "uPD-77P25"

        # Act
        with self.assertRaises(upd7725.UnknownModelError) as raised:
            upd7725.Cpu(name)

        # Assert
        said = str(raised.exception)
        self.assertIn("ask for upd7725 and load the program yourself", said)

    def test_a_name_nothing_here_recognises_is_refused_with_the_list(self) -> None:
        # Arrange
        name = "nothing-like-a-part-number"

        # Act
        with self.assertRaises(upd7725.UnknownModelError) as raised:
            upd7725.Cpu(name)

        # Assert
        said = str(raised.exception)
        self.assertEqual(
            said,
            "nothing-like-a-part-number is not a processor this package covers;"
            " it has upd7725, upd96050",
        )


class BuildTest(unittest.TestCase):
    def test_a_processor_is_built_from_its_model(self) -> None:
        # Arrange
        model = upd7725.MODELS["upd7725"]

        # Act
        built = model.build(fill=0)

        # Assert
        self.assertEqual((built.model, len(built.stores.program)), (model, 2048))

    def test_options_reach_the_processor_that_gets_built(self) -> None:
        # Arrange
        model = upd7725.MODELS["upd7725"]

        # Act
        built = model.build(fill=0xABCD)

        # Assert
        self.assertEqual(built.stores.scratch[0], 0xABCD)


class QuietStoreTest(unittest.TestCase):
    def test_a_fill_puts_that_byte_everywhere(self) -> None:
        # Arrange
        fill = 0

        # Act
        part = upd7725.Cpu("upd7725", fill=fill)

        # Assert
        self.assertEqual({part.stores.read_byte(at) for at in range(0x40)}, {0})

    def test_and_this_part_defaults_to_a_cleared_store_where_its_siblings_scramble(
        self,
    ) -> None:
        # Arrange
        name = "upd7725"

        # Act
        part = upd7725.Cpu(name)

        # Assert
        self.assertEqual({part.stores.read_byte(at) for at in range(0x40)}, {0})

    def test_and_this_part_offers_no_scrambled_store_at_all(self) -> None:
        # Arrange
        cleared = upd7725.Cpu("upd7725", fill=0)

        # Act
        asked = upd7725.Cpu("upd7725", fill=None)

        # Assert
        self.assertEqual(
            {asked.stores.read_byte(at) for at in range(0x40)},
            {cleared.stores.read_byte(at) for at in range(0x40)},
        )


class NamingNoneTest(unittest.TestCase):
    def test_building_without_naming_a_model_is_refused(self) -> None:
        # Arrange
        name = None

        # Act
        with self.assertRaises(upd7725.UnknownModelError) as raised:
            upd7725.Cpu(name)

        # Assert
        said = str(raised.exception)
        self.assertTrue(said.startswith("no model was named"), said)

    def test_and_the_refusal_names_every_model_there_is(self) -> None:
        # Arrange
        name = None

        # Act
        with self.assertRaises(upd7725.UnknownModelError) as raised:
            upd7725.Cpu(name)

        # Assert
        said = str(raised.exception)
        self.assertEqual([one for one in ("upd7725", "upd96050") if one not in said], [])

    def test_nothing_named_describe_is_published(self) -> None:
        # Arrange
        package = upd7725

        # Act
        published = hasattr(package, "describe")

        # Assert
        self.assertFalse(published)

    def test_and_no_default_model_is_published_either(self) -> None:
        # Arrange
        package = upd7725

        # Act
        published = hasattr(package, "DEFAULT_MODEL")

        # Assert
        self.assertFalse(published)


if __name__ == "__main__":
    unittest.main()
