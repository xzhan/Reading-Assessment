"""Tests for candidate reading-bank generation and review files."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from backend.pet_reading_api.review_bank import REQUIRED_SKILLS, sample_candidates, validate_candidate, write_review_files


class ReadingReviewBankTest(unittest.TestCase):
    def test_sample_candidates_are_ready_for_human_review(self) -> None:
        candidates = sample_candidates(count=2)

        self.assertEqual(len(candidates), 2)
        for candidate in candidates:
            self.assertEqual(validate_candidate(candidate), [])
            self.assertEqual(candidate["review_status"], "candidate")
            self.assertEqual(candidate["reviewer"], "")
            self.assertEqual(candidate["review_notes"], "")
            self.assertEqual({item["skill"] for item in candidate["items"]}, set(REQUIRED_SKILLS))
            self.assertEqual(len(candidate["items"]), 5)
            for item in candidate["items"]:
                self.assertEqual(set(item["choices"]), {"A", "B", "C", "D"})
                self.assertIn(item["correct_choice"], item["choices"])
                self.assertTrue(item["rationales"][item["correct_choice"]])

    def test_write_review_files_outputs_jsonl_and_csv(self) -> None:
        candidates = sample_candidates(count=2)
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = write_review_files(candidates, Path(temp_dir))
            jsonl_path = paths["jsonl"]
            csv_path = paths["csv"]

            self.assertTrue(jsonl_path.exists())
            self.assertTrue(csv_path.exists())
            jsonl_records = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(jsonl_records), 2)
            csv_text = csv_path.read_text(encoding="utf-8")
            self.assertIn("passage_id,title,anchor_lexile,review_status", csv_text)
            self.assertIn("candidate", csv_text)


if __name__ == "__main__":
    unittest.main()
