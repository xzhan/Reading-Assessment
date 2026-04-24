"""Focused tests for the hybrid writing pipeline."""

from __future__ import annotations

import unittest

from backend.pet_writing_api.llm_client import LLMCallResult
from backend.pet_writing_api.pipeline import WritingEvaluationPipeline


class FakeLLMClient:
    def __init__(self) -> None:
        self.model = "fake-llm"
        self.calls = 0

    def is_enabled(self) -> bool:
        return True

    def complete_json(self, *, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> LLMCallResult:
        self.calls += 1
        if "dimension_scores" in user_prompt:
            payload = {
                "dimension_scores": {
                    "task_achievement": 4.3,
                    "organization_coherence": 4.0,
                    "grammar_control": 3.9,
                    "lexical_range_accuracy": 4.1,
                },
                "confidence_boost": 0.02,
                "readiness": "on_track",
                "strengths": ["Task response is clear.", "The vocabulary feels natural."],
                "priority_issues": ["Make the ending slightly stronger."],
                "rewrite_focus": "grammar_control",
                "scoring_notes": ["Adjusted scores conservatively based on clear task coverage."],
            }
        elif "sentence_suggestions" in user_prompt:
            payload = {
                "strengths": ["Task response is clear.", "The vocabulary feels natural."],
                "priority_issues": [
                    "Make the ending slightly stronger.",
                    "Check verb forms before submitting.",
                    "Add one more connector between ideas.",
                ],
                "sentence_suggestions": [
                    {
                        "issue_type": "grammar",
                        "original": "I joined the music club at school because I really enjoy singing and meeting new friends.",
                        "suggestion": "I joined the music club at school because I really enjoy singing and meeting new friends there.",
                        "reason": "This ending sounds slightly fuller and more natural.",
                    }
                ],
                "rewrite_task": {
                    "title": "Rewrite for better grammar control",
                    "instruction": "Rewrite the essay and check verb forms carefully before you submit again.",
                },
            }
        else:
            payload = {
                "improved": ["Grammar control improved in the second draft."],
                "still_needs_work": ["The ending can still be more direct."],
            }
        return LLMCallResult(
            provider="fake",
            model_name=self.model,
            model_version="fake-v1",
            output_payload=payload,
            latency_ms=12,
        )


class WritingPipelineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.pipeline = WritingEvaluationPipeline(mode="hybrid", llm_client=FakeLLMClient())
        self.prompt = {
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
        self.essay = (
            "Dear Sam,\n"
            "I joined the music club at school because I really enjoy singing and meeting new friends. "
            "We practise every Tuesday after class, and it is always fun.\n"
            "Please visit our club next week because I think you will like it too."
        )

    def test_hybrid_pipeline_records_llm_runs(self) -> None:
        result = self.pipeline.evaluate(prompt=self.prompt, text=self.essay, time_spent_sec=900, word_count_client=85)
        self.assertIn("score_payload", result)
        self.assertIn("feedback_payload", result)
        stages = [item["stage"] for item in result["model_runs"]]
        self.assertIn("llm_score_refinement", stages)
        self.assertIn("llm_feedback_generation", stages)
        self.assertEqual(result["feedback_payload"]["rewrite_task"]["title"], "Rewrite for better grammar control")

    def test_comparison_can_use_llm_summary(self) -> None:
        first = self.pipeline.evaluate(prompt=self.prompt, text=self.essay, time_spent_sec=900)
        second_essay = self.essay + " First, I want to show you our next performance."
        second = self.pipeline.evaluate(prompt=self.prompt, text=second_essay, time_spent_sec=1100)
        comparison = self.pipeline.summarize_comparison(
            prompt=self.prompt,
            base_text=self.essay,
            compare_text=second_essay,
            base_scores=first["score_payload"]["scores"],
            compare_scores=second["score_payload"]["scores"],
        )
        self.assertIn("comparison_payload", comparison)
        self.assertTrue(comparison["comparison_payload"]["improved"])
        self.assertEqual(comparison["model_runs"][0]["provider"], "fake")


if __name__ == "__main__":
    unittest.main()
