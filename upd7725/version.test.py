import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import upd7725  # noqa: E402

VERSION_FILE = ROOT / "upd7725" / "version.py"


def stamped() -> str:
    line = next(
        one for one in VERSION_FILE.read_text().splitlines() if one.startswith("VERSION = ")
    )
    return line.split('"')[1]


class ConstructionTest(unittest.TestCase):
    def test_a_processor_is_built_from_the_name_of_a_part(self) -> None:
        # Arrange
        name = "upd7725"

        # Act
        built = upd7725.Cpu(name)

        # Assert
        self.assertEqual(built.model.name, "upd7725")

    def test_the_larger_part_is_built_from_its_own_name(self) -> None:
        # Arrange
        name = "upd96050"

        # Act
        built = upd7725.Cpu(name)

        # Assert
        self.assertEqual(built.model.name, "upd96050")

    def test_options_reach_the_processor_that_gets_built(self) -> None:
        # Arrange
        fill = 0xBEEF

        # Act
        built = upd7725.Cpu("upd7725", fill=fill)

        # Assert
        self.assertEqual(built.stores.scratch[0], 0xBEEF)


class VersionTest(unittest.TestCase):
    def test_the_version_is_three_numbers(self) -> None:
        # Arrange
        held = upd7725.__version__

        # Act
        parts = held.split(".")

        # Assert
        self.assertEqual(len(parts), 3)
        self.assertTrue(all(part.isdigit() for part in parts))

    def test_and_publishes_the_version_the_file_is_stamped_with(self) -> None:
        # Arrange
        held = stamped()

        # Act
        reported = upd7725.__version__

        # Assert
        self.assertEqual(reported, held)


if __name__ == "__main__":
    unittest.main()
