"""That this repository carries what the family standard says it carries.

FAMILY.md is prose, and prose drifts away from the thing it describes unless
something holds the two together. This is that something, for the parts of the
standard a check can settle: the files, the models a reader is shown how to
build, and the number of tests the readme advertises.
"""

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from upd7725 import MODELS  # noqa: E402

FAMILY = (ROOT / "FAMILY.md").read_text()

README = (ROOT / "README.md").read_text()


class SharedFileTest(unittest.TestCase):
    def test_the_standard_names_every_file_this_repository_must_carry(self) -> None:
        rows = re.findall(r"^\| `([^`]+)` \|", FAMILY, re.M)
        promised = [row for row in rows if "/" in row or row.endswith(".md")]

        missing = [row for row in promised if not (ROOT / row).exists()]

        self.assertEqual(missing, [])

    def test_and_there_is_something_to_check(self) -> None:
        rows = re.findall(r"^\| `([^`]+)` \|", FAMILY, re.M)

        self.assertGreater(len([row for row in rows if row.endswith(".md")]), 0)


class DocumentedModelTest(unittest.TestCase):
    """That the readme shows how to build every part the package accepts.

    A model nobody can find in the readme is a model nobody uses. The check is
    for the constructor call rather than the bare name, because a name in prose
    tells a reader the part exists and a call tells them how to reach it, and the
    second is what they came for.
    """

    def test_every_model_has_a_worked_construction(self) -> None:
        undocumented = [name for name in MODELS if f'Processor("{name}")' not in README]

        self.assertEqual(undocumented, [])

    def test_and_every_alias_is_named_beside_it(self) -> None:
        unnamed = [
            alias for model in MODELS.values() for alias in model.aliases if alias not in README
        ]

        self.assertEqual(unnamed, [])


class ClaimedCountTest(unittest.TestCase):
    """That the number of tests the readme advertises is the number there are.

    A count in prose is a claim about the repository, and a claim nothing checks
    is one that drifts silently until a reader believes something false. This one
    had drifted before the check existed.

    Counted from the source rather than by running the suites, because a test
    that runs every other test to check a number would cost minutes to answer a
    question worth milliseconds. The two agree: unittest reports one test per
    def test_, and nothing here generates cases at runtime.
    """

    def counted(self) -> int:
        """Every test in the directories the pipeline runs, and nowhere else.

        Scoped rather than swept for a reason. docs/ is not in the repository, so
        a sweep of the whole tree counts files a fresh checkout does not have and
        the number disagrees with itself depending on which machine asks.
        """
        return sum(
            len(re.findall(r"^\s+def test_", found.read_text(), re.M))
            for directory in ("upd7725", "conformance")
            for found in sorted((ROOT / directory).glob("**/*.test.py"))
        )

    def test_the_readme_advertises_the_number_of_tests_there_are(self) -> None:
        claimed = re.search(r"\*\*([\d,]+)\*\* tests", README)

        assert claimed is not None
        self.assertEqual(int(claimed.group(1).replace(",", "")), self.counted())


if __name__ == "__main__":
    unittest.main()
