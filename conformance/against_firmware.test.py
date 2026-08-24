import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conformance import against_firmware

PRESENT = against_firmware.available()

WHY = against_firmware.WHY_NOT


class AvailabilityTest(unittest.TestCase):
    def test_an_empty_directory_offers_nothing(self) -> None:
        self.assertEqual(against_firmware.available(Path(tempfile.mkdtemp())), ())

    def test_a_directory_that_is_not_there_offers_nothing_either(self) -> None:
        self.assertEqual(against_firmware.available(Path("/nowhere/at/all")), ())

    def test_the_reason_it_offers_nothing_names_where_it_looked(self) -> None:
        self.assertIn("firmware", WHY.lower())

    def test_and_names_the_setting_that_points_it_somewhere_else(self) -> None:
        self.assertIn("UPD7725_FIRMWARE_DIR", WHY)


class SummaryTest(unittest.TestCase):
    def test_a_comparison_that_found_nothing_says_nothing(self) -> None:
        self.assertEqual(against_firmware.summary({}), ())

    def test_and_one_that_found_something_says_how_much(self) -> None:
        found = against_firmware.summary({1: (), 2: ()})

        self.assertIn("2 of", found[0])

    def test_a_comparison_needs_both_masks_to_say_anything(self) -> None:
        self.assertEqual(against_firmware.compare_revisions(()), {})


class ReportTest(unittest.TestCase):
    def test_a_run_with_nothing_present_still_reports_rather_than_failing(self) -> None:
        self.assertEqual(against_firmware.run([], where=Path(tempfile.mkdtemp())), 0)

    def test_an_option_it_does_not_know_is_reported(self) -> None:
        self.assertEqual(against_firmware.main(["--nonsense"]), 2)

    def test_an_option_it_does_not_know_is_refused(self) -> None:
        with self.assertRaises(against_firmware.Usage):
            against_firmware.options(["--nonsense"])

    def test_an_option_with_no_value_is_refused(self) -> None:
        with self.assertRaises(against_firmware.Usage):
            against_firmware.options(["--instructions"])

    def test_the_number_of_instructions_can_be_set(self) -> None:
        self.assertEqual(against_firmware.options(["--instructions", "7"]).instructions, 7)


@unittest.skipUnless(PRESENT, WHY)
class BootTest(unittest.TestCase):
    def test_every_image_present_reaches_a_state_where_it_waits_for_the_console(self) -> None:
        for identity, path in PRESENT:
            console = against_firmware.booted(identity, path)

            self.assertTrue(console.asking, identity.part)

    def test_every_image_present_runs_without_leaving_its_own_stores(self) -> None:
        for identity, path in PRESENT:
            console = against_firmware.booted(identity, path)
            console.chip.run_for(against_firmware.DEFAULT_INSTRUCTIONS)

            self.assertLess(
                console.chip.registers.pc, len(console.chip.stores.program), identity.part
            )

    def test_a_full_run_over_what_is_present_reports_clean(self) -> None:
        self.assertEqual(against_firmware.run([]), 0)


@unittest.skipUnless(
    {identity.part for identity, _ in PRESENT} >= {"dsp1", "dsp1b"},
    "both masks of the DSP-1 are needed to compare them",
)
class RevisionTest(unittest.TestCase):
    def test_the_two_masks_of_the_dsp1_do_not_answer_the_same_way(self) -> None:
        found = against_firmware.compare_revisions(PRESENT)

        self.assertTrue(found, "the two masks answered identically to every command tried")


if __name__ == "__main__":
    unittest.main()
