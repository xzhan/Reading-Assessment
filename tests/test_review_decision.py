"""Unit tests for deterministic review decision rules."""

from __future__ import annotations

import unittest

from backend.pet_writing_api.pipeline import WritingEvaluationPipeline


PROMPT = {
    "id": "pet_email_test",
    "task_type": "email",
    "title": "Write an email to your friend",
    "instructions": "Tell your friend about a club you joined, why you like it, and invite them.",
    "target_word_count_min": 100,
    "target_word_count_max": 140,
    "metadata": {
        "content_points": [
            ["club"],
            ["why", "like"],
            ["invite", "join"],
        ]
    },
}


class ReviewDecisionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.pipeline = WritingEvaluationPipeline(mode="off")

    def test_short_off_topic_draft_requires_review(self) -> None:
        result = self.pipeline.evaluate(
            prompt=PROMPT,
            text="Hello. School is good. I like lunch.",
            time_spent_sec=180,
        )

        review = result["review_payload"]
        self.assertTrue(review["needs_review"])
        self.assertIn("below_target_word_count", review["review_reason_codes"])
        self.assertIn("low_task_coverage", review["review_reason_codes"])

    def test_complete_draft_stays_out_of_review(self) -> None:
        text = (
            "Dear Sam,\n"
            "I joined the music club at school because I enjoy singing and meeting new friends. "
            "We practise every Tuesday after class, and I like it because the teacher is kind and the activities are fun. "
            "Last week, we learned two new songs, and everyone worked together very well during the rehearsal. "
            "Sometimes we also play simple instruments, which helps us improve our confidence and listen carefully to each other. "
            "Please come and join us next week because I think you will enjoy the club, meet friendly students, and feel welcome from the first day. "
            "After the meeting, we can walk home together and talk about which songs you would like to sing in the future."
        )
        result = self.pipeline.evaluate(
            prompt=PROMPT,
            text=text,
            time_spent_sec=900,
        )

        review = result["review_payload"]
        self.assertFalse(review["needs_review"])
        self.assertEqual(review["review_reason_codes"], [])


if __name__ == "__main__":
    unittest.main()
