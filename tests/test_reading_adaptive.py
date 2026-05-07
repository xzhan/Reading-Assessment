"""Tests for passage-level adaptive reading decisions."""

from __future__ import annotations

import unittest

from backend.pet_reading_api.adaptive import next_anchor_lexile, starting_anchor_for_grade
from backend.pet_reading_api.seed_data import READING_PASSAGES


class ReadingAdaptiveTest(unittest.TestCase):
    def test_starting_anchor_uses_grade(self) -> None:
        self.assertEqual(starting_anchor_for_grade(6), 700)
        self.assertEqual(starting_anchor_for_grade(7), 800)
        self.assertEqual(starting_anchor_for_grade(8), 900)
        self.assertEqual(starting_anchor_for_grade(None), 800)

    def test_next_anchor_moves_by_accuracy(self) -> None:
        self.assertEqual(next_anchor_lexile(current_anchor=800, accuracy=1.0), 925)
        self.assertEqual(next_anchor_lexile(current_anchor=800, accuracy=0.8), 850)
        self.assertEqual(next_anchor_lexile(current_anchor=800, accuracy=0.6), 725)
        self.assertEqual(next_anchor_lexile(current_anchor=800, accuracy=0.2), 650)

    def test_next_anchor_clamps_to_mvp_range(self) -> None:
        self.assertEqual(next_anchor_lexile(current_anchor=1050, accuracy=1.0), 1100)
        self.assertEqual(next_anchor_lexile(current_anchor=525, accuracy=0.2), 500)

    def test_seed_data_has_required_skills_per_passage(self) -> None:
        required = {
            "main_idea",
            "detail",
            "inference",
            "vocabulary_context",
            "structure_author_purpose",
        }
        for passage in READING_PASSAGES:
            skills = {item["skill"] for item in passage["items"]}
            self.assertEqual(skills, required)
            self.assertEqual(len(passage["items"]), 5)

    def test_seed_data_includes_promoted_vocab_quest_passages(self) -> None:
        promoted = [passage for passage in READING_PASSAGES if passage["id"].startswith("rp_vq_")]

        self.assertEqual(len(promoted), 10)
        promoted_ids = {passage["id"] for passage in promoted}
        self.assertIn("rp_vq_253ea7923758", promoted_ids)
        self.assertIn("rp_vq_3fcd767f3e99", promoted_ids)
        self.assertEqual({passage["band_label"] for passage in promoted}, {"VocabQuest"})
        for passage in promoted:
            self.assertEqual(passage["metadata"]["source"], "vocab_quest_promoted")


if __name__ == "__main__":
    unittest.main()
