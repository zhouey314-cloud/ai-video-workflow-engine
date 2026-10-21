"""Detect accidental drift between a reviewed artifact and its recorded hash."""
import hashlib
import json
from pathlib import Path
import unittest


class ReviewBindingTests(unittest.TestCase):
    def test_user_review_binds_exact_sample_and_keeps_machine_record(self):
        root=Path(__file__).resolve().parents[1]/'examples/original_54s'
        review=json.loads((root/'human-review.json').read_text())
        manifest=json.loads((root/'ASSET_MANIFEST.json').read_text())
        machine=json.loads((root/'sample.qa.json').read_text())
        digest=hashlib.sha256((root/review['artifact']).read_bytes()).hexdigest()
        self.assertEqual(review['status'],'APPROVED')
        self.assertEqual(digest,review['sha256'])
        self.assertEqual(digest,manifest['approved_artifact']['sha256'])
        self.assertEqual(digest,machine['artifact_sha256'])
        self.assertEqual(machine['state'],'HUMAN_REVIEW')
