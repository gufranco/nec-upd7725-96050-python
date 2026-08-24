import sys
import unittest
from collections.abc import Callable
from pathlib import Path
from typing import Any, NoReturn

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from upd7725 import doctor


class Complaint(Exception):
    pass


def a_finding(
    name: str = "something", ok: bool = True, detail: str = "detail", advice: str | None = None
) -> "doctor.Finding":
    return doctor.Finding(name, ok, detail, advice)


class FindingTest(unittest.TestCase):
    def test_a_finding_says_what_was_checked(self) -> None:
        self.assertEqual(a_finding(name="the image").name, "the image")

    def test_and_whether_it_was_well(self) -> None:
        self.assertTrue(a_finding(ok=True).ok)
        self.assertFalse(a_finding(ok=False).ok)

    def test_a_healthy_finding_prints_with_a_mark_that_says_so(self) -> None:
        self.assertIn("ok", a_finding(ok=True).line)

    def test_and_an_unhealthy_one_prints_differently(self) -> None:
        self.assertNotIn("ok", a_finding(ok=False).line)

    def test_every_finding_carries_what_it_actually_saw(self) -> None:
        self.assertIn("8192 bytes", a_finding(detail="8192 bytes").line)

    def test_an_unhealthy_finding_says_what_to_do_about_it(self) -> None:
        self.assertIn("go and look", a_finding(ok=False, advice="go and look").report)

    def test_a_healthy_one_carries_no_advice(self) -> None:
        self.assertEqual(a_finding(ok=True, advice="x").report, a_finding(ok=True).line)

    def test_a_finding_prints_as_itself(self) -> None:
        self.assertIn("something", repr(a_finding()))


class ExamineTest(unittest.TestCase):
    def test_the_examination_produces_findings(self) -> None:
        self.assertTrue(doctor.examine())

    def test_it_reports_the_python_it_is_running_on(self) -> None:
        self.assertIn("python", [one.name for one in doctor.examine()])

    def test_and_the_version_of_this_package(self) -> None:
        found = [one for one in doctor.examine() if one.name == "package"]

        self.assertIn("upd7725", found[0].detail)

    def test_the_package_line_is_not_confused_with_the_part_of_the_same_name(self) -> None:
        names = [one.name for one in doctor.examine()]

        self.assertEqual(names.count("upd7725"), 1)

    def test_and_one_finding_per_processor_it_covers(self) -> None:
        from upd7725 import models

        names = [one.name for one in doctor.examine()]

        for model in models.MODELS:
            self.assertIn(model, names, model)

    def test_and_where_it_looks_for_images(self) -> None:
        self.assertIn("looking in", [one.name for one in doctor.examine()])

    def test_and_what_the_manifest_declares(self) -> None:
        self.assertIn("declared", [one.name for one in doctor.examine()])

    def test_an_absent_manifest_is_reported_rather_than_raised(self) -> None:
        def missing() -> NoReturn:
            raise FileNotFoundError(2, "No such file or directory")

        found = doctor._declared(missing)

        self.assertTrue(found.ok)
        self.assertIn("normal state of an install", found.detail)

    def test_a_manifest_that_will_not_parse_is_reported_rather_than_hidden(self) -> None:
        def broken() -> NoReturn:
            raise Complaint("the manifest exploded")

        found = doctor._declared(broken)

        self.assertFalse(found.ok)
        self.assertIn("Complaint: the manifest exploded", found.detail)

    def test_every_finding_carries_a_detail(self) -> None:
        for one in doctor.examine():
            self.assertTrue(one.detail, one.name)

    def test_a_processor_that_will_not_build_is_reported_rather_than_hidden(self) -> None:
        def boom(_name: str) -> NoReturn:
            raise Complaint("the core exploded")

        found = doctor.examine(build=boom)

        self.assertTrue(any(not one.ok for one in found))

    def test_and_the_report_carries_what_it_said_and_what_kind(self) -> None:
        def boom(_name: str) -> NoReturn:
            raise Complaint("the core exploded")

        text = "\n".join(one.report for one in doctor.examine(build=boom))

        self.assertIn("the core exploded", text)
        self.assertIn("Complaint", text)


class ImageTest(unittest.TestCase):
    def test_a_machine_with_no_image_says_so_rather_than_listing_none(self) -> None:
        found = doctor.examine(search=lambda: [])

        self.assertIn("no images", " ".join(one.detail for one in found))

    def test_and_that_is_not_treated_as_a_failure(self) -> None:
        found = doctor.examine(search=lambda: [])

        held = [one for one in found if one.name == "images"]
        self.assertTrue(held)
        self.assertTrue(held[0].ok)

    def test_a_search_that_itself_throws_is_reported(self) -> None:
        def boom() -> NoReturn:
            raise Complaint("the search exploded")

        text = "\n".join(one.report for one in doctor.examine(search=boom))

        self.assertIn("the search exploded", text)


class PresentImageTest(unittest.TestCase):
    """That an image being present is examined on machines that hold none.

    Nobody who does not already own these parts can put one here, so most
    machines that ever run this report hold nothing at all. Leaving the
    present-image checks to whatever happens to be on the machine means they are
    exercised where it is convenient and nowhere else, and a check that only runs
    on one person's laptop is not a check.
    """

    def _one(self, where: Path) -> Callable[[], list[tuple[Any, Path]]]:
        from upd7725 import firmware

        return lambda: [(firmware.Identity("dsp1", "upd7725", "MADE UP", 8, 8), where)]

    def _made_up(self) -> Path:
        import tempfile

        where = Path(tempfile.mkdtemp()) / "made-up.bin"
        where.write_bytes(b"nothing anybody owns")
        return where

    def test_an_image_that_is_here_is_counted(self) -> None:
        found = doctor.examine(search=self._one(self._made_up()))

        held = [one for one in found if one.name == "images"]
        self.assertIn("1 present", held[0].detail)

    def test_and_reported_under_its_own_name(self) -> None:
        found = doctor.examine(search=self._one(self._made_up()))

        self.assertIn("image dsp1", [one.name for one in found])

    def test_and_carries_the_digest_of_the_file_that_is_actually_here(self) -> None:
        import hashlib

        found = doctor.examine(search=self._one(self._made_up()))

        digest = hashlib.sha256(b"nothing anybody owns").hexdigest()
        self.assertIn(digest, " ".join(one.detail for one in found))

    def test_and_the_processor_it_belongs_to(self) -> None:
        found = doctor.examine(search=self._one(self._made_up()))

        for one in found:
            if one.name == "image dsp1":
                self.assertIn("upd7725", one.detail)

    def test_a_file_that_went_away_between_finding_and_reading_says_so(self) -> None:
        found = doctor.examine(search=self._one(Path("/nowhere/at/all.bin")))

        self.assertIn("could not be read", " ".join(one.detail for one in found))


class DigestTest(unittest.TestCase):
    def test_a_file_that_is_here_reports_its_digest(self) -> None:
        import hashlib
        import tempfile

        where = Path(tempfile.mkdtemp()) / "made-up.bin"
        where.write_bytes(b"nothing anybody owns")

        self.assertEqual(
            doctor._digest_of(where), hashlib.sha256(b"nothing anybody owns").hexdigest()
        )

    def test_a_file_that_cannot_be_read_says_so_rather_than_going_quiet(self) -> None:
        found = doctor._digest_of(Path("/nowhere/at/all.bin"))

        self.assertIn("could not be read", found)


class ReportTest(unittest.TestCase):
    def test_the_report_has_a_line_for_every_finding(self) -> None:
        found = doctor.examine()

        self.assertGreaterEqual(len(doctor.report(found)), len(found))

    def test_it_opens_with_something_that_says_what_it_is(self) -> None:
        self.assertIn("upd7725", doctor.report(doctor.examine())[0])

    def test_an_unhealthy_run_says_how_many_did_not_pass(self) -> None:
        self.assertIn("1", " ".join(doctor.report([a_finding(ok=False)])))

    def test_a_healthy_run_says_there_is_nothing_to_report(self) -> None:
        self.assertIn("nothing to report", " ".join(doctor.report([a_finding(ok=True)])))


class EntryTest(unittest.TestCase):
    def test_a_healthy_run_reports_success(self) -> None:
        self.assertEqual(
            doctor.main([], examine=lambda **_: [a_finding(ok=True)], say=lambda _: None), 0
        )

    def test_an_unhealthy_one_reports_failure(self) -> None:
        self.assertEqual(
            doctor.main([], examine=lambda **_: [a_finding(ok=False)], say=lambda _: None), 1
        )

    def test_the_report_is_printed_rather_than_kept(self) -> None:
        said: list[str] = []

        doctor.main([], examine=lambda **_: [a_finding(ok=True)], say=said.append)

        self.assertTrue(said)

    def test_a_real_run_says_something_about_this_machine(self) -> None:
        said: list[str] = []

        doctor.main([], say=said.append)

        self.assertIn("upd7725", " ".join(said))


if __name__ == "__main__":
    unittest.main()
