"""Tests for the trainable scorer artifact and training pipeline."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.pet_writing_api.features import extract_features
from backend.pet_writing_api.trainable_scorer import train_artifact, TrainableScorerArtifact


PROMPT = {
    "id": "wp_pet_email_001",
    "task_type": "email",
    "title": "Write an email to your English friend",
    "instructions": "Write about your club, why you like it, and invite your friend to visit.",
    "target_word_count_min": 100,
    "target_word_count_max": 140,
    "metadata": {
        "content_points": [
            ["club", "music", "sports"],
            ["because", "enjoy", "like"],
            ["invite", "visit", "join"],
        ]
    },
}


def make_sample(index: int, text: str, labels: dict[str, float]) -> dict:
    analysis = extract_features(PROMPT, text, 800 + (index * 30))
    return {
        "sample_id": f"sample_{index}",
        "prompt": PROMPT,
        "text": text,
        "labels": labels,
        "feature_vector": analysis["feature_vector"],
    }


class TrainableScorerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.dataset = [
            make_sample(
                1,
                "Dear Sam, I joined the music club because I enjoy singing. Please visit next week.",
                {"task_achievement": 4, "organization_coherence": 3, "grammar_control": 4, "lexical_range_accuracy": 3},
            ),
            make_sample(
                2,
                "Dear Sam, I joined the sports club because it is fun and healthy. Please join us next week.",
                {"task_achievement": 4, "organization_coherence": 3, "grammar_control": 4, "lexical_range_accuracy": 3},
            ),
            make_sample(
                3,
                "Dear Sam, I joined the drama club because I like acting. I want to invite you to visit us soon.",
                {"task_achievement": 4, "organization_coherence": 4, "grammar_control": 4, "lexical_range_accuracy": 4},
            ),
            make_sample(
                4,
                "I joined club. It good. You come.",
                {"task_achievement": 2, "organization_coherence": 1, "grammar_control": 1, "lexical_range_accuracy": 1},
            ),
            make_sample(
                5,
                "Dear Sam, I joined the science club because I enjoy building things. First, we meet on Monday. Please visit us next week.",
                {"task_achievement": 5, "organization_coherence": 4, "grammar_control": 4, "lexical_range_accuracy": 4},
            ),
            make_sample(
                6,
                "Dear Sam, I joined the art club because I like painting and making posters. You should visit because it is creative and friendly.",
                {"task_achievement": 4, "organization_coherence": 4, "grammar_control": 4, "lexical_range_accuracy": 4},
            ),
            make_sample(
                7,
                "The club is nice but I do not explain enough ideas.",
                {"task_achievement": 2, "organization_coherence": 2, "grammar_control": 3, "lexical_range_accuracy": 2},
            ),
            make_sample(
                8,
                "Dear Sam, I joined the music club because I really enjoy singing and meeting new friends. Please come and visit next week.",
                {"task_achievement": 5, "organization_coherence": 4, "grammar_control": 4, "lexical_range_accuracy": 4},
            ),
            make_sample(
                9,
                "Dear Sam, I joined the coding club because I like solving problems. We meet every Friday, and you should join us sometime.",
                {"task_achievement": 4, "organization_coherence": 4, "grammar_control": 4, "lexical_range_accuracy": 4},
            ),
            make_sample(
                10,
                "Club good. Because fun. You come.",
                {"task_achievement": 1, "organization_coherence": 1, "grammar_control": 1, "lexical_range_accuracy": 1},
            ),
        ]

    def test_train_and_save_artifact(self) -> None:
        artifact = train_artifact(self.dataset, epochs=300, learning_rate=0.04, val_ratio=0.2, seed=7)
        prediction = artifact.predict(self.dataset[0]["feature_vector"])
        self.assertIn("dimensions", prediction)
        self.assertIn("overall", prediction)
        self.assertGreaterEqual(prediction["overall"], 0)

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "artifact.json"
            artifact.save(path)
            loaded = TrainableScorerArtifact.load(path)
            re_pred = loaded.predict(self.dataset[0]["feature_vector"])
            self.assertEqual(re_pred["readiness"], prediction["readiness"])
            self.assertEqual(set(re_pred["dimensions"].keys()), set(prediction["dimensions"].keys()))


if __name__ == "__main__":
    unittest.main()
