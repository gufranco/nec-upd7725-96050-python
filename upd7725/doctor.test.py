import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from upd7725 import doctor


class Complaint(Exception):
    pass


def a_finding(name="something", ok=True, detail="detail", advice=None):
    return doctor.Finding(name, ok, detail, advice)


class FindingTest(unittest.TestCase):
    def test_a_finding_says_what_was_checked(self):
        self.assertEqual(a_finding(name="the image").name, "the image")

    def test_and_whether_it_was_well(self):
        self.assertTrue(a_finding(ok=True).ok)
        self.assertFalse(a_finding(ok=False).ok)

    def test_a_healthy_finding_prints_with_a_mark_that_says_so(self):
        self.assertIn("ok", a_finding(ok=True).line)

    def test_and_an_unhealthy_one_prints_differently(self):
        self.assertNotIn("ok", a_finding(ok=False).line)

    def test_every_finding_carries_what_it_actually_saw(self):
        self.assertIn("8192 bytes", a_finding(detail="8192 bytes").line)

    def test_an_unhealthy_finding_says_what_to_do_about_it(self):
        self.assertIn("go and look", a_finding(ok=False, advice="go and look").report)

    def test_a_healthy_one_carries_no_advice(self):
        self.assertEqual(a_finding(ok=True, advice="x").report, a_finding(ok=True).line)

    def test_a_finding_prints_as_itself(self):
        self.assertIn("something", repr(a_finding()))


class ExamineTest(unittest.TestCase):
    def test_the_examination_produces_findings(self):
        self.assertTrue(doctor.examine())

    def test_it_reports_the_python_it_is_running_on(self):
        self.assertIn("python", [one.name for one in doctor.examine()])

    def test_and_the_version_of_this_package(self):
        self.assertIn("upd7725", [one.name for one in doctor.examine()])

    def test_and_one_finding_per_processor_it_covers(self):
        from upd7725 import models

        names = [one.name for one in doctor.examine()]

        for model in models.MODELS:
            self.assertIn(model, names, model)

    def test_and_where_it_looks_for_images(self):
        self.assertIn("looking in", [one.name for one in doctor.examine()])

    def test_and_what_the_manifest_declares(self):
        self.assertIn("declared", [one.name for one in doctor.examine()])

    def test_every_finding_carries_a_detail(self):
        for one in doctor.examine():
            self.assertTrue(one.detail, one.name)

    def test_a_processor_that_will_not_build_is_reported_rather_than_hidden(self):
        def boom(_name):
            raise Complaint("the core exploded")

        found = doctor.examine(build=boom)

        self.assertTrue(any(not one.ok for one in found))

    def test_and_the_report_carries_what_it_said_and_what_kind(self):
        def boom(_name):
            raise Complaint("the core exploded")

        text = "\n".join(one.report for one in doctor.examine(build=boom))

        self.assertIn("the core exploded", text)
        self.assertIn("Complaint", text)


class ImageTest(unittest.TestCase):
    def test_an_image_that_is_here_is_reported_with_its_digest(self):
        found = doctor.examine()

        images = [one for one in found if one.name.startswith("image ")]
        for one in images:
            self.assertIn("sha256", one.detail)

    def test_a_machine_with_no_image_says_so_rather_than_listing_none(self):
        found = doctor.examine(search=lambda: [])

        self.assertIn("no images", " ".join(one.detail for one in found))

    def test_and_that_is_not_treated_as_a_failure(self):
        found = doctor.examine(search=lambda: [])

        held = [one for one in found if one.name == "images"]
        self.assertTrue(held)
        self.assertTrue(held[0].ok)

    def test_a_search_that_itself_throws_is_reported(self):
        def boom():
            raise Complaint("the search exploded")

        text = "\n".join(one.report for one in doctor.examine(search=boom))

        self.assertIn("the search exploded", text)


class DigestTest(unittest.TestCase):
    def test_a_file_that_is_here_reports_its_digest(self):
        import hashlib
        import tempfile

        where = Path(tempfile.mkdtemp()) / "made-up.bin"
        where.write_bytes(b"nothing anybody owns")

        self.assertEqual(
            doctor._digest_of(where), hashlib.sha256(b"nothing anybody owns").hexdigest()
        )

    def test_a_file_that_cannot_be_read_says_so_rather_than_going_quiet(self):
        found = doctor._digest_of(Path("/nowhere/at/all.bin"))

        self.assertIn("could not be read", found)


class ReportTest(unittest.TestCase):
    def test_the_report_has_a_line_for_every_finding(self):
        found = doctor.examine()

        self.assertGreaterEqual(len(doctor.report(found)), len(found))

    def test_it_opens_with_something_that_says_what_it_is(self):
        self.assertIn("upd7725", doctor.report(doctor.examine())[0])

    def test_an_unhealthy_run_says_how_many_did_not_pass(self):
        self.assertIn("1", " ".join(doctor.report([a_finding(ok=False)])))

    def test_a_healthy_run_says_there_is_nothing_to_report(self):
        self.assertIn("nothing to report", " ".join(doctor.report([a_finding(ok=True)])))


class EntryTest(unittest.TestCase):
    def test_a_healthy_run_reports_success(self):
        self.assertEqual(
            doctor.main([], examine=lambda **_: [a_finding(ok=True)], say=lambda _: None), 0
        )

    def test_an_unhealthy_one_reports_failure(self):
        self.assertEqual(
            doctor.main([], examine=lambda **_: [a_finding(ok=False)], say=lambda _: None), 1
        )

    def test_the_report_is_printed_rather_than_kept(self):
        said = []

        doctor.main([], examine=lambda **_: [a_finding(ok=True)], say=said.append)

        self.assertTrue(said)

    def test_a_real_run_says_something_about_this_machine(self):
        said = []

        doctor.main([], say=said.append)

        self.assertIn("upd7725", " ".join(said))


if __name__ == "__main__":
    unittest.main()
