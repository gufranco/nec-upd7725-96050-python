import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from upd7725 import firmware, models


def an_image(program_words=2048, data_words=1024, filler=0xAB):
    return bytes([filler]) * (program_words * 3 + data_words * 2)


class ManifestTest(unittest.TestCase):
    def test_the_manifest_names_every_part_the_package_can_run(self):
        named = {entry["part"] for entry in firmware.manifest()["artifacts"]}

        self.assertIn("st011", named)
        self.assertIn("dsp1", named)

    def test_each_part_names_the_processor_it_runs_on(self):
        for entry in firmware.manifest()["artifacts"]:
            self.assertIn(entry["processor"], models.MODELS, entry["part"])

    def test_each_part_names_a_size_its_two_stores_add_up_to(self):
        for entry in firmware.manifest()["artifacts"]:
            self.assertEqual(
                entry["programWords"] * 3 + entry["dataWords"] * 2, entry["bytes"], entry["part"]
            )

    def test_each_part_carries_at_least_one_digest(self):
        for entry in firmware.manifest()["artifacts"]:
            self.assertTrue(entry["accepted"], entry["part"])

    def test_every_digest_is_a_whole_sha256(self):
        for entry in firmware.manifest()["artifacts"]:
            for accepted in entry["accepted"]:
                self.assertEqual(len(accepted["sha256"]), 64, entry["part"])

    def test_the_manifest_carries_no_run_of_bytes_longer_than_a_digest(self):
        def strings(held):
            if isinstance(held, str):
                yield held
            elif isinstance(held, dict):
                for value in held.values():
                    yield from strings(value)
            elif isinstance(held, list):
                for value in held:
                    yield from strings(value)

        runs = [
            text.strip()
            for text in strings(firmware.manifest())
            if len(text.strip()) > 64
            and all(letter in "0123456789abcdefABCDEF" for letter in text.strip())
        ]

        self.assertEqual(runs, [])

    def test_a_manifest_can_be_read_from_somewhere_else(self):
        where = Path(tempfile.mkdtemp()) / "other.json"
        where.write_text(json.dumps({"artifacts": []}))

        self.assertEqual(firmware.manifest(where)["artifacts"], [])


class IdentifyTest(unittest.TestCase):
    def test_an_image_the_manifest_knows_is_named(self):
        image = an_image()
        digest = hashlib.sha256(image).hexdigest()
        catalogue = {
            "artifacts": [
                {
                    "part": "made-up",
                    "processor": "upd7725",
                    "bytes": len(image),
                    "programWords": 2048,
                    "dataWords": 1024,
                    "accepted": [{"revision": "one", "sha256": digest}],
                }
            ]
        }

        self.assertEqual(firmware.identify(image, catalogue).part, "made-up")

    def test_and_the_revision_it_turned_out_to_be(self):
        image = an_image()
        digest = hashlib.sha256(image).hexdigest()
        catalogue = {
            "artifacts": [
                {
                    "part": "made-up",
                    "processor": "upd7725",
                    "bytes": len(image),
                    "programWords": 2048,
                    "dataWords": 1024,
                    "accepted": [{"revision": "one", "sha256": digest}],
                }
            ]
        }

        self.assertEqual(firmware.identify(image, catalogue).revision, "one")

    def test_an_image_of_the_right_size_and_the_wrong_content_says_so(self):
        catalogue = {
            "artifacts": [
                {
                    "part": "made-up",
                    "processor": "upd7725",
                    "bytes": 8192,
                    "programWords": 2048,
                    "dataWords": 1024,
                    "accepted": [{"revision": "one", "sha256": "0" * 64}],
                }
            ]
        }

        with self.assertRaises(firmware.Unrecognised) as raised:
            firmware.identify(an_image(), catalogue)

        self.assertIn("altered", str(raised.exception))

    def test_an_image_of_no_size_the_manifest_knows_says_that_instead(self):
        catalogue = {"artifacts": []}

        with self.assertRaises(firmware.Unrecognised) as raised:
            firmware.identify(b"\x00" * 7, catalogue)

        self.assertIn("7", str(raised.exception))

    def test_the_report_always_carries_the_digest_that_was_computed(self):
        with self.assertRaises(firmware.Unrecognised) as raised:
            firmware.identify(b"\x00" * 7, {"artifacts": []})

        self.assertIn(hashlib.sha256(b"\x00" * 7).hexdigest(), str(raised.exception))


class IdentityTest(unittest.TestCase):
    def test_an_identity_prints_as_the_part_it_names(self):
        found = firmware.Identity("dsp1", "upd7725", "DSP-1", 2048, 1024)

        self.assertIn("dsp1", repr(found))
        self.assertIn("DSP-1", repr(found))


class LoadTest(unittest.TestCase):
    def test_a_loaded_image_fills_the_program_store(self):
        chip = models.describe("upd7725").build(fill=0)
        image = bytes(range(256)) * 32 + bytes(2048)

        firmware.load(chip, image[: 2048 * 3] + image[: 1024 * 2])

        self.assertEqual(chip.stores.program[0], 0x000102)

    def test_and_the_table_after_it(self):
        chip = models.describe("upd7725").build(fill=0)
        program = bytes(2048 * 3)
        table = bytes([0xAA, 0xBB]) * 1024

        firmware.load(chip, program + table)

        self.assertEqual(chip.stores.table[0], 0xAABB)

    def test_an_image_that_does_not_match_the_processor_is_refused(self):
        chip = models.describe("upd7725").build(fill=0)

        with self.assertRaises(firmware.WrongShape):
            firmware.load(chip, bytes(53248))


class FoundTest(unittest.TestCase):
    def test_a_directory_with_nothing_in_it_yields_nothing(self):
        self.assertEqual(list(firmware.found(Path(tempfile.mkdtemp()))), [])

    def test_a_directory_that_is_not_there_yields_nothing_either(self):
        self.assertEqual(list(firmware.found(Path("/nowhere/at/all"))), [])

    def test_a_file_the_manifest_knows_is_yielded_with_its_name(self):
        where = Path(tempfile.mkdtemp())
        image = an_image()
        (where / "made-up.bin").write_bytes(image)
        catalogue = {
            "artifacts": [
                {
                    "part": "made-up",
                    "processor": "upd7725",
                    "bytes": len(image),
                    "programWords": 2048,
                    "dataWords": 1024,
                    "accepted": [{"revision": "one", "sha256": hashlib.sha256(image).hexdigest()}],
                }
            ]
        }

        found = list(firmware.found(where, catalogue))

        self.assertEqual(found[0][0].part, "made-up")

    def test_a_file_the_manifest_does_not_know_is_passed_over(self):
        where = Path(tempfile.mkdtemp())
        (where / "nonsense.bin").write_bytes(b"\x00" * 99)

        self.assertEqual(list(firmware.found(where, {"artifacts": []})), [])

    def test_the_directory_comes_from_the_environment_when_one_is_named(self):
        self.assertEqual(firmware.directory({"UPD7725_FIRMWARE_DIR": "/x"}), Path("/x"))

    def test_and_from_the_repository_when_none_is(self):
        self.assertEqual(firmware.directory({}).name, "firmware")


if __name__ == "__main__":
    unittest.main()
