import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import upd7725
from upd7725 import version


class ConstructionTest(unittest.TestCase):
    def test_a_processor_is_built_from_the_name_of_a_part(self) -> None:
        self.assertEqual(upd7725.Processor("upd7725").model.name, "upd7725")

    def test_the_default_part_is_the_larger_one(self) -> None:
        self.assertEqual(upd7725.Processor().model.name, upd7725.DEFAULT_MODEL)

    def test_options_reach_the_processor_that_gets_built(self) -> None:
        self.assertEqual(upd7725.Processor(fill=0xBEEF).stores.scratch[0], 0xBEEF)


class VersionTest(unittest.TestCase):
    def test_the_package_carries_a_version(self) -> None:
        self.assertTrue(version.VERSION)

    def test_and_publishes_it_the_way_python_expects(self) -> None:
        self.assertEqual(upd7725.__version__, version.VERSION)


if __name__ == "__main__":
    unittest.main()
