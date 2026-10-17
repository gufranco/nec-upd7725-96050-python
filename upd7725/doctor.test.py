from __future__ import annotations

import importlib
import re
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path
from typing import TYPE_CHECKING, NoReturn

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import upd7725
from upd7725 import doctor

if TYPE_CHECKING:
    from conformance.printed import Part


class Complaint(Exception):
    pass


def a_finding(
    name: str = "something", ok: bool = True, detail: str = "detail", advice: str | None = None
) -> doctor.Finding:
    return doctor.Finding(name, ok, detail, advice)


def boom(_name: str) -> NoReturn:
    raise Complaint("the core exploded")


def complain() -> NoReturn:
    raise Complaint("the pin did nothing")


def a_part_whose_reset_fails(name: str) -> Part:
    part = upd7725.Cpu(name)
    part.on_cycle = complain
    return part


class FindingTest(unittest.TestCase):
    def test_a_finding_says_what_was_checked(self) -> None:
        # Arrange
        name = "the image"

        # Act
        found = a_finding(name=name)

        # Assert
        self.assertEqual(found.name, "the image")

    def test_and_whether_it_was_well(self) -> None:
        # Arrange
        verdicts = (True, False)

        # Act
        found = [a_finding(ok=verdict).ok for verdict in verdicts]

        # Assert
        self.assertEqual(found, [True, False])

    def test_a_healthy_finding_prints_with_a_mark_that_says_so(self) -> None:
        # Arrange
        found = a_finding(ok=True)

        # Act
        line = found.line

        # Assert
        self.assertIn("ok", line)

    def test_and_an_unhealthy_one_prints_differently(self) -> None:
        # Arrange
        found = a_finding(ok=False)

        # Act
        line = found.line

        # Assert
        self.assertNotIn("ok", line)

    def test_every_finding_carries_what_it_actually_saw(self) -> None:
        # Arrange
        found = a_finding(detail="8192 bytes")

        # Act
        line = found.line

        # Assert
        self.assertIn("8192 bytes", line)

    def test_an_unhealthy_finding_says_what_to_do_about_it(self) -> None:
        # Arrange
        found = a_finding(ok=False, advice="go and look")

        # Act
        printed = found.report

        # Assert
        self.assertIn("go and look", printed)

    def test_a_healthy_one_carries_no_advice(self) -> None:
        # Arrange
        found = a_finding(ok=True, advice="x")

        # Act
        printed = found.report

        # Assert
        self.assertEqual(printed, a_finding(ok=True).line)

    def test_a_finding_prints_as_itself(self) -> None:
        # Arrange
        found = a_finding()

        # Act
        printed = repr(found)

        # Assert
        self.assertIn("something", printed)


class ExamineTest(unittest.TestCase):
    def test_the_examination_produces_findings(self) -> None:
        # Arrange
        examine = doctor.examine

        # Act
        found = examine()

        # Assert
        self.assertGreater(len(found), 0)

    def test_it_reports_the_python_it_is_running_on(self) -> None:
        # Arrange
        examine = doctor.examine

        # Act
        found = examine()

        # Assert
        self.assertIn("python", [one.name for one in found])

    def test_and_the_version_of_this_package(self) -> None:
        # Arrange
        examine = doctor.examine

        # Act
        found = [one for one in examine() if one.name == "package"]

        # Assert
        self.assertIn("upd7725", found[0].detail)

    def test_the_package_line_is_not_confused_with_the_part_of_the_same_name(self) -> None:
        # Arrange
        examine = doctor.examine

        # Act
        names = [one.name for one in examine()]

        # Assert
        self.assertEqual(names.count("upd7725"), 1)

    def test_and_one_finding_per_processor_it_covers(self) -> None:
        # Arrange
        covered = sorted(upd7725.MODELS)

        # Act
        names = [one.name for one in doctor.examine()]

        # Assert
        self.assertEqual([model for model in covered if model not in names], [])

    def test_every_finding_carries_a_detail(self) -> None:
        # Arrange
        examine = doctor.examine

        # Act
        found = examine()

        # Assert
        self.assertEqual([one.name for one in found if not one.detail], [])

    def test_a_processor_that_will_not_build_is_reported_rather_than_hidden(self) -> None:
        # Arrange
        build = boom

        # Act
        found = doctor.examine(build=build)

        # Assert
        self.assertEqual(sorted(one.name for one in found if not one.ok), sorted(upd7725.MODELS))

    def test_a_processor_that_builds_reports_where_the_reset_left_it(self) -> None:
        # Arrange
        examine = doctor.examine

        # Act
        found = [one for one in examine() if one.name == "upd7725"]

        # Assert
        self.assertIn("resets to word 0", found[0].detail)

    def test_a_processor_that_will_not_reset_is_reported_as_broken(self) -> None:
        # Arrange
        build = a_part_whose_reset_fails

        # Act
        found = doctor.examine(build=build)

        # Assert
        self.assertEqual(sorted(one.name for one in found if not one.ok), sorted(upd7725.MODELS))

    def test_and_the_report_carries_what_it_said_and_what_kind(self) -> None:
        # Arrange
        found = doctor.examine(build=a_part_whose_reset_fails)

        # Act
        text = "\n".join(one.report for one in found)

        # Assert
        self.assertIn("Complaint: the pin did nothing", text)


class ReportTest(unittest.TestCase):
    def test_the_report_has_a_line_for_every_finding(self) -> None:
        # Arrange
        found = doctor.examine()

        # Act
        lines = doctor.report(found)

        # Assert
        self.assertGreaterEqual(len(lines), len(found))

    def test_it_opens_with_something_that_says_what_it_is(self) -> None:
        # Arrange
        found = doctor.examine()

        # Act
        lines = doctor.report(found)

        # Assert
        self.assertIn("upd7725", lines[0])

    def test_an_unhealthy_run_says_how_many_did_not_pass(self) -> None:
        # Arrange
        found = [a_finding(ok=False)]

        # Act
        lines = doctor.report(found)

        # Assert
        self.assertEqual(lines[-1], "  1 of 1 checks did not pass")

    def test_a_healthy_run_says_there_is_nothing_to_report(self) -> None:
        # Arrange
        found = [a_finding(ok=True)]

        # Act
        lines = doctor.report(found)

        # Assert
        self.assertEqual(lines[-1], "  1 checks, nothing to report")


class EntryTest(unittest.TestCase):
    def test_a_healthy_run_reports_success(self) -> None:
        # Arrange
        healthy = [a_finding(ok=True)]

        # Act
        code = doctor.main([], examine=lambda **_: healthy, say=lambda _: None)

        # Assert
        self.assertEqual(code, 0)

    def test_an_unhealthy_one_reports_failure(self) -> None:
        # Arrange
        unhealthy = [a_finding(ok=False)]

        # Act
        code = doctor.main([], examine=lambda **_: unhealthy, say=lambda _: None)

        # Assert
        self.assertEqual(code, 1)

    def test_the_report_is_printed_rather_than_kept(self) -> None:
        # Arrange
        said: list[str] = []

        # Act
        doctor.main([], examine=lambda **_: [a_finding(ok=True)], say=said.append)

        # Assert
        self.assertEqual(said[-1], "  1 checks, nothing to report")

    def test_a_real_run_says_something_about_this_machine(self) -> None:
        # Arrange
        said: list[str] = []

        # Act
        doctor.main([], say=said.append)

        # Assert
        self.assertIn("upd7725", " ".join(said))


class RunAsAFileTest(unittest.TestCase):
    def test_run_as_a_file_from_outside_the_repository_it_ends_with_its_verdict(self) -> None:
        # Arrange
        script = doctor.ROOT / "upd7725" / "doctor.py"
        elsewhere = tempfile.mkdtemp()

        # Act
        finished = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            check=False,
            text=True,
            cwd=elsewhere,
            timeout=120,
        )

        # Assert
        self.assertEqual(finished.stderr, "")
        self.assertRegex(finished.stdout.splitlines()[-1], r"^  \d+ (of \d+ )?checks")


class PathTest(unittest.TestCase):
    def test_the_repository_is_put_on_the_path_when_it_is_not_already_there(self) -> None:
        # Arrange
        held = [one for one in sys.path if one != str(doctor.ROOT)]

        # Act
        with unittest.mock.patch.object(sys, "path", held):
            importlib.reload(doctor)

        # Assert
        self.assertIn(str(doctor.ROOT), held)

    def test_the_version_is_read_out_of_the_file_rather_than_imported(self) -> None:
        # Arrange
        found = re.search(
            r'VERSION[^"\']*"([^"]+)"', (doctor.ROOT / "upd7725" / "version.py").read_text()
        )
        assert found is not None

        # Act
        read = doctor.installed_version()

        # Assert
        self.assertEqual((read, doctor.VERSION), (found.group(1), found.group(1)))

    def test_a_version_file_naming_nothing_reads_as_unknown(self) -> None:
        # Arrange
        where = Path(tempfile.mkdtemp()) / "version.py"
        where.write_text("NOTHING = 1\n")

        # Act
        read = doctor.installed_version(where)

        # Assert
        self.assertEqual(read, "unknown")


if __name__ == "__main__":
    unittest.main()
