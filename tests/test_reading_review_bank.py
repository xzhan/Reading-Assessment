"""Tests for candidate reading-bank generation and review files."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from backend.pet_reading_api.review_bank import (
    REQUIRED_SKILLS,
    candidates_from_vocab_quest_export,
    promote_vocab_quest_candidates,
    sample_candidates,
    validate_candidate,
    write_review_files,
)


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

    def test_import_vocab_quest_export_preserves_reviewed_questions(self) -> None:
        payload = {
            "vocabQuestVersion": 1,
            "exportType": "quests",
            "sessions": [
                {
                    "id": "b385b66a-703e-44aa-acfe-a03e822fb6a7",
                    "title": "Reading Quest [Vocabulary]: PET Page 33 03261514",
                    "readingType": "PET_part_4",
                    "targetLevel": "B1",
                    "passage": (
                        "As an experienced explorer, Clara has visited every rainforest on Earth. One month, "
                        "she found herself in a remote town near the sea. Her purpose was simple: to deliver "
                        "a rare antique vase to a local businesswoman. She walked toward the heavy iron gate, "
                        "feeling the heat of the day. A local farmer kindly offered to lend her his bike, but "
                        "she declined, preferring to walk. She passed a fountain where children were playing, "
                        "a pop of color against the grey stone. Nearby, a bin was overflowing with trash, and "
                        "someone had left a loose cotton shirt on the ground. It seemed unfair that such a "
                        "beautiful place had so much litter. Clara noticed a small store with a blue logo, "
                        "which was her destination. She felt a sudden hunger, so she bought a cold cola and a "
                        "small snack. Indeed, the local life was peaceful compared to the noise of the city. "
                        "She checked her webcam to record her progress, then moved to approach the store owner. "
                        "Despite the total cost being five pounds, the owner refused payment, insisting the "
                        "service was free. It was a kind gesture, proving that genuine hospitality does still "
                        "exist in this world."
                    ),
                    "questions": [
                        {
                            "id": "q1",
                            "type": "multiple_choice",
                            "question": "What was Clara's main reason for visiting the town?",
                            "options": [
                                "To explore the local rainforest.",
                                "To deliver an antique object.",
                                "To buy a new cotton shirt.",
                                "To meet with a local farmer.",
                            ],
                            "correctAnswer": "To deliver an antique object.",
                            "explanation": "The text states her purpose was to deliver a rare antique vase.",
                            "skill": "detail",
                            "word": "purpose",
                        },
                        {
                            "id": "q2",
                            "type": "multiple_choice",
                            "question": "How did Clara feel about the litter she saw near the fountain?",
                            "options": [
                                "She thought it was necessary.",
                                "She believed it was unfair.",
                                "She wanted to clean it up.",
                                "She ignored it completely.",
                            ],
                            "correctAnswer": "She believed it was unfair.",
                            "explanation": "The passage explicitly says it seemed unfair.",
                            "skill": "detail",
                            "word": "unfair",
                        },
                        {
                            "id": "q3",
                            "type": "multiple_choice",
                            "question": "What did the store owner do when Clara tried to pay?",
                            "options": [
                                "He charged her five pounds.",
                                "He offered her a discount.",
                                "He told her it was free.",
                                "He asked for more money.",
                            ],
                            "correctAnswer": "He told her it was free.",
                            "explanation": "The owner refused payment and said the service was free.",
                            "skill": "detail",
                            "word": "free",
                        },
                        {
                            "id": "q4",
                            "type": "multiple_choice",
                            "question": "What does the word 'approach' mean in the context of the story?",
                            "options": [
                                "To start a conversation.",
                                "To move closer to someone.",
                                "To look at a map.",
                                "To leave a store.",
                            ],
                            "correctAnswer": "To move closer to someone.",
                            "explanation": "Approach means to move towards or get nearer.",
                            "skill": "vocabulary_context",
                            "word": "approach",
                        },
                        {
                            "id": "q5",
                            "type": "multiple_choice",
                            "question": "What can be inferred about Clara's character from the passage?",
                            "options": [
                                "She is a wealthy businesswoman.",
                                "She enjoys traveling to remote places.",
                                "She dislikes local traditions.",
                                "She is afraid of the sea.",
                            ],
                            "correctAnswer": "She enjoys traveling to remote places.",
                            "explanation": "As an explorer, she clearly enjoys such travel.",
                            "skill": "inference",
                            "word": "explorer",
                        },
                    ],
                    "originalVocab": [{"word": "purpose", "meaning": "purpose"}],
                    "category": "PET",
                }
            ],
        }

        candidates = candidates_from_vocab_quest_export(payload)

        self.assertEqual(len(candidates), 1)
        candidate = candidates[0]
        self.assertEqual(candidate["passage_id"], "vq_b385b66a703e")
        self.assertEqual(candidate["review_status"], "reviewed_candidate")
        self.assertEqual(candidate["source"], "vocab_quest")
        self.assertEqual(candidate["cefr_level"], "B1")
        self.assertEqual(candidate["genre"], "vocabulary")
        self.assertEqual(candidate["topic"], "PET_part_4")
        self.assertEqual(validate_candidate(candidate, strict_skill_coverage=False), [])
        self.assertIn("diagnostic_skill_coverage_incomplete", candidate["validation_flags"])
        self.assertFalse(candidate["diagnostic_ready"])
        self.assertEqual(candidate["items"][0]["correct_choice"], "B")
        self.assertEqual(candidate["items"][0]["choices"]["B"], "To deliver an antique object.")
        self.assertEqual(candidate["items"][0]["target_word"], "purpose")

    def test_import_vocab_quest_export_flags_records_that_need_repair(self) -> None:
        payload = {
            "vocabQuestVersion": 1,
            "exportType": "quests",
            "sessions": [
                {
                    "id": "short-session",
                    "title": "Reading Quest [Literature]: PET Page 66",
                    "targetLevel": "B1",
                    "passage": (
                        "Elara walked into the kitchen of the bustling cafe. The morning sun was incredibly "
                        "bright, reflecting off the polished counters. She had been searching for a job for "
                        "weeks, and today was her interview. The owner greeted her with a warm smile and "
                        "explained that the cafe was vegetarian. She needed someone reliable and quick to "
                        "learn. Elara felt nervous but confident. She described her experience cooking "
                        "vegetables and preparing salads. The owner decided to employ her immediately, and "
                        "Elara felt relief. She knew this was the start of a wonderful chapter, even though "
                        "the cafe was busy and the experienced staff around her had much to teach."
                    ),
                    "questions": [
                        {
                            "id": "q1",
                            "question": "What is the general conclusion of the passage?",
                            "options": [
                                "A job is impossible.",
                                "The cafe is closed.",
                                "Elara is hired.",
                                "The owner leaves.",
                            ],
                            "correctAnswer": "Elara gets the job.",
                            "explanation": "The owner decides to employ Elara.",
                            "skill": "conclusion",
                        },
                        {
                            "id": "q2",
                            "question": "What does the word 'employ' mean?",
                            "options": [
                                "To fire someone.",
                                "To hire someone.",
                                "To cook food.",
                                "To clean counters.",
                            ],
                            "correctAnswer": "To hire someone.",
                            "explanation": "Employ means hire.",
                            "word": "employ",
                        },
                        {
                            "id": "q3",
                            "question": "Why is Elara confident?",
                            "options": [
                                "She has cooking experience.",
                                "She owns the cafe.",
                                "She dislikes salads.",
                                "She is leaving.",
                            ],
                            "correctAnswer": "She has cooking experience.",
                            "explanation": "She has experience with vegetables and salads.",
                            "skill": "unsupported_skill",
                        },
                        {
                            "id": "q4",
                            "question": "What type of food does the cafe serve?",
                            "options": [
                                "Vegetarian food.",
                                "Seafood.",
                                "Fast food.",
                                "Meat dishes.",
                            ],
                            "correctAnswer": "Vegetarian food.",
                            "explanation": "The owner explains that the cafe is vegetarian.",
                            "skill": "detail",
                        },
                    ],
                }
            ],
        }

        candidate = candidates_from_vocab_quest_export(payload)[0]

        self.assertEqual(candidate["review_status"], "reviewed_candidate")
        self.assertEqual(len(candidate["items"]), 4)
        self.assertEqual(candidate["items"][0]["skill"], "main_idea")
        self.assertEqual(candidate["items"][1]["skill"], "vocabulary_context")
        self.assertEqual(candidate["items"][2]["skill"], "detail")
        self.assertFalse(candidate["diagnostic_ready"])
        self.assertIn("item_1_correct_answer_not_found", candidate["validation_flags"])
        self.assertIn("item_1_skill_mapped_from_conclusion", candidate["validation_flags"])
        self.assertIn("item_2_skill_inferred", candidate["validation_flags"])
        self.assertIn(
            "item_3_skill_mapped_from_unsupported_unsupported_skill",
            candidate["validation_flags"],
        )
        self.assertIn("diagnostic_item_count_not_5", candidate["validation_flags"])
        self.assertIn("diagnostic_skill_coverage_incomplete", candidate["validation_flags"])

    def test_promote_vocab_quest_candidates_repairs_near_ready_records(self) -> None:
        jsonl_path = Path("data/reading_review/vocabquest_reviewed_candidates.jsonl")
        candidates = [
            json.loads(line)
            for line in jsonl_path.read_text(encoding="utf-8").splitlines()
        ]

        promoted, skipped = promote_vocab_quest_candidates(candidates)

        self.assertEqual(len(promoted), 10)
        self.assertEqual(len(skipped), 29)
        promoted_ids = {passage["id"] for passage in promoted}
        self.assertIn("rp_vq_f7dd8057bc29", promoted_ids)
        self.assertIn("rp_vq_5f20d02399b3", promoted_ids)
        self.assertIn("rp_vq_3fcd767f3e99", promoted_ids)
        self.assertIn("rp_vq_253ea7923758", promoted_ids)
        self.assertNotIn("vq_4d34d1625dea", {candidate["passage_id"] for candidate in candidates})
        corrected_page_57 = next(
            passage for passage in promoted if passage["id"] == "rp_vq_253ea7923758"
        )
        self.assertIn("superhero", corrected_page_57["body_text"])
        self.assertEqual(
            corrected_page_57["metadata"]["source_session_id"],
            "253ea792-3758-4b20-8aff-2abee3d25213",
        )
        manually_repaired = next(
            passage for passage in promoted if passage["id"] == "rp_vq_5f20d02399b3"
        )
        self.assertEqual(manually_repaired["metadata"]["generated_missing_skill"], "")
        for passage in promoted:
            self.assertTrue(passage["id"].startswith("rp_vq_"))
            self.assertTrue(passage["passage_code"].startswith("VQ_"))
            self.assertEqual(passage["band_label"], "VocabQuest")
            self.assertEqual(passage["metadata"]["source"], "vocab_quest_promoted")
            self.assertEqual(len(passage["items"]), 5)
            self.assertEqual(
                {item["skill"] for item in passage["items"]},
                set(REQUIRED_SKILLS),
            )
            for item in passage["items"]:
                self.assertEqual(set(item["choices"]), {"A", "B", "C", "D"})
                self.assertIn(item["correct_choice"], item["choices"])
                self.assertTrue(item["rationales"][item["correct_choice"]])


if __name__ == "__main__":
    unittest.main()
