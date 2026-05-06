"""Tests for Lexile-like reading estimate calculation."""

from __future__ import annotations

import unittest

from backend.pet_reading_api.estimator import estimate_reading_level


class ReadingEstimatorTest(unittest.TestCase):
    def test_estimates_stable_mid_range_reader(self) -> None:
        responses = [
            {"estimated_item_lexile": 675, "skill": "detail", "correct": True, "time_seconds": 35},
            {"estimated_item_lexile": 700, "skill": "main_idea", "correct": True, "time_seconds": 42},
            {"estimated_item_lexile": 775, "skill": "inference", "correct": True, "time_seconds": 55},
            {"estimated_item_lexile": 825, "skill": "vocabulary_context", "correct": True, "time_seconds": 47},
            {"estimated_item_lexile": 850, "skill": "structure_author_purpose", "correct": False, "time_seconds": 60},
            {"estimated_item_lexile": 925, "skill": "inference", "correct": False, "time_seconds": 70},
            {"estimated_item_lexile": 950, "skill": "vocabulary_context", "correct": False, "time_seconds": 65},
            {"estimated_item_lexile": 975, "skill": "detail", "correct": False, "time_seconds": 52},
        ]

        estimate = estimate_reading_level(
            responses=responses,
            passages_completed=4,
            duration_seconds=1420,
        )

        self.assertEqual(estimate["estimated_lower_lexile"], 725)
        self.assertEqual(estimate["estimated_upper_lexile"], 950)
        self.assertEqual(estimate["practice_lower_lexile"], 655)
        self.assertEqual(estimate["practice_upper_lexile"], 890)
        self.assertEqual(estimate["confidence_label"], "Medium")
        self.assertEqual(estimate["cefr_estimate"], "A2+")
        self.assertIn("detail", estimate["domain_scores"])
        self.assertGreaterEqual(estimate["domain_scores"]["detail"], 40)

    def test_flags_fast_low_effort_pattern(self) -> None:
        responses = [
            {"estimated_item_lexile": 650, "skill": "detail", "correct": False, "time_seconds": 3},
            {"estimated_item_lexile": 675, "skill": "main_idea", "correct": False, "time_seconds": 4},
            {"estimated_item_lexile": 700, "skill": "inference", "correct": True, "time_seconds": 3},
            {"estimated_item_lexile": 725, "skill": "vocabulary_context", "correct": False, "time_seconds": 4},
        ]

        estimate = estimate_reading_level(
            responses=responses,
            passages_completed=2,
            duration_seconds=480,
        )

        self.assertEqual(estimate["confidence_label"], "Low")
        self.assertIn("TOO_FEW_PASSAGES", estimate["validity_flags"])
        self.assertIn("TOO_FAST_OVERALL", estimate["validity_flags"])
        self.assertIn("MANY_RUSHED_ITEMS", estimate["validity_flags"])

    def test_marks_above_target_range(self) -> None:
        responses = [
            {"estimated_item_lexile": 950, "skill": "detail", "correct": True, "time_seconds": 45},
            {"estimated_item_lexile": 1000, "skill": "main_idea", "correct": True, "time_seconds": 48},
            {"estimated_item_lexile": 1025, "skill": "inference", "correct": True, "time_seconds": 60},
            {"estimated_item_lexile": 1075, "skill": "vocabulary_context", "correct": True, "time_seconds": 53},
            {"estimated_item_lexile": 1100, "skill": "structure_author_purpose", "correct": True, "time_seconds": 58},
        ]

        estimate = estimate_reading_level(
            responses=responses,
            passages_completed=4,
            duration_seconds=1500,
        )

        self.assertEqual(estimate["range_status"], "above_target_range")
        self.assertIn("ABOVE_TARGET_RANGE", estimate["validity_flags"])


if __name__ == "__main__":
    unittest.main()
