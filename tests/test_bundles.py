import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from video_workflow.engine import (
    Job,
    Shot,
    Asset,
    MockProvider,
    LocalFFmpegProvider,
    ExternalProviderInterface,
)
from video_workflow.delivery import create_bundle, verify_bundle
import shutil


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.job = Job(
            "Fictional delivery",
            "Synthetic script",
            "Fixture",
            [Shot("a", 1, "a", "Synthetic caption")],
        )
        self.assets = [Asset("a", "card", ("a",), "SELF")]

    def make(self, provider=None):
        dest = self.root / "bundle"
        result = create_bundle(self.job, self.assets, provider or MockProvider(), dest)
        return dest, result

    def test_manifest_and_hashes_are_verifiable_without_approval(self):
        dest, result = self.make()
        receipt = verify_bundle(dest)
        self.assertEqual(result["state"], "HUMAN_REVIEW")
        self.assertEqual(receipt["human_approval"], "NOT_GRANTED")
        self.assertEqual(
            json.loads((dest / "report.json").read_text())["output"], "workflow.json"
        )

    def test_tampering_fails(self):
        dest, _ = self.make()
        (dest / "workflow.json").write_text("tampered")
        with self.assertRaisesRegex(ValueError, "CHECKSUM"):
            verify_bundle(dest)

    def test_unsafe_manifest_path_fails(self):
        dest, _ = self.make()
        p = dest / "manifest.json"
        m = json.loads(p.read_text())
        m["files"][0]["path"] = "../private"
        p.write_text(json.dumps(m))
        with self.assertRaisesRegex(ValueError, "PATH"):
            verify_bundle(dest)

    def test_symlink_and_unlisted_file_fail(self):
        dest, _ = self.make()
        (dest / "extra").write_text("unlisted")
        with self.assertRaisesRegex(ValueError, "UNLISTED"):
            verify_bundle(dest)
        (dest / "extra").unlink()
        (dest / "workflow.json").unlink()
        (dest / "workflow.json").symlink_to(dest / "report.json")
        with self.assertRaisesRegex(ValueError, "UNSAFE"):
            verify_bundle(dest)

    def test_existing_destination_is_preserved(self):
        dest, _ = self.make()
        before = (dest / "manifest.json").read_bytes()
        with self.assertRaises(FileExistsError):
            create_bundle(self.job, self.assets, MockProvider(), dest)
        self.assertEqual((dest / "manifest.json").read_bytes(), before)

    def test_failed_job_does_not_publish_partial_bundle(self):
        dest, result = self.make(ExternalProviderInterface())
        self.assertEqual(result["state"], "FAILED")
        self.assertFalse(dest.exists())
        self.assertEqual(list(self.root.glob(".video-job-*")), [])

    @unittest.skipUnless(
        shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg required"
    )
    def test_real_encoded_bundle_with_captions_and_qa(self):
        dest, result = self.make(LocalFFmpegProvider())
        self.assertEqual(result["state"], "HUMAN_REVIEW")
        verify_bundle(dest)
        for name in [
            "film.mp4",
            "film.srt",
            "film.ass",
            "film.timeline.json",
            "film.png",
            "report.json",
            "manifest.json",
        ]:
            self.assertTrue((dest / name).is_file())
        self.assertTrue(result["media_qa"]["full_decode"])

    def test_malformed_manifest_is_a_contract_error(self):
        dest, _ = self.make()
        p = dest / "manifest.json"
        for value in [
            None,
            [],
            {"schema_version": 1, "files": [None]},
            {
                "schema_version": 1,
                "files": [{"path": "report.json", "bytes": True, "sha256": "x" * 64}],
            },
        ]:
            with self.subTest(value=value):
                p.write_text(json.dumps(value))
                with self.assertRaises(ValueError):
                    verify_bundle(dest)
