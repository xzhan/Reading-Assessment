"""Hybrid evaluation pipeline for PET Writing."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .features import extract_features, fallback_sentence_suggestions
from .llm_client import LLMCallResult, LLMClientError, OpenAICompatibleLLMClient
from .trainable_scorer import TrainableScorerArtifact


SCORE_REFINEMENT_SYSTEM_PROMPT = """You are a careful PET Writing scoring assistant.

You are given:
- the PET writing prompt
- the student's essay
- structured linguistic features
- conservative baseline scores

Rules:
- stay aligned to PET-style rubric dimensions
- never invent evidence that is not grounded in the essay or features
- adjust each dimension score by at most 0.75 from the baseline
- keep every dimension between 0 and 5
- overall score must equal the sum of the four dimensions
- keep feedback concise and exam-oriented
- return JSON only
"""

FEEDBACK_SYSTEM_PROMPT = """You are a PET Writing coach generating grounded feedback.

Rules:
- use the provided scoring evidence and student essay
- feedback must be specific, short, and actionable
- do not give a full model essay
- sentence suggestions must quote real text from the student's essay
- return JSON only
"""

COMPARISON_SYSTEM_PROMPT = """You compare two PET Writing drafts.

Rules:
- use only the provided drafts and score deltas
- explain what improved and what still needs work
- keep the summary short and student-friendly
- return JSON only
"""


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def round_score(value: float) -> float:
    return round(clamp(value, 0.0, 5.0), 2)


class WritingEvaluationPipeline:
    """Hybrid scorer with optional trainable model and LLM refinement."""

    def __init__(
        self,
        mode: str | None = None,
        llm_client: Any | None = None,
        trained_scorer: TrainableScorerArtifact | None = None,
        trained_model_path: str | None = None,
    ):
        normalized_mode = (mode or os.getenv("PET_WRITING_LLM_MODE", "off")).strip().lower()
        self.mode = normalized_mode if normalized_mode in {"off", "feedback", "hybrid"} else "off"
        self.llm_client = llm_client if llm_client is not None else OpenAICompatibleLLMClient.from_env()
        self.trained_scorer = trained_scorer or self._load_trained_scorer(trained_model_path or os.getenv("PET_WRITING_MODEL_PATH"))

    def evaluate(
        self,
        *,
        prompt: dict[str, Any],
        text: str,
        time_spent_sec: int,
        word_count_client: int | None = None,
    ) -> dict[str, Any]:
        analysis = extract_features(prompt, text, time_spent_sec)
        score_payload, score_model_name = self._baseline_scores(prompt, analysis)
        model_runs = [
            self._internal_run(
                stage="extract_features",
                model_name="feature-engine-v1",
                input_payload={
                    "prompt_id": prompt["id"],
                    "text_length": len(text),
                    "time_spent_sec": time_spent_sec,
                },
                output_payload={
                    "signals": analysis["signals"],
                    "evidence": analysis["evidence"],
                    "feature_vector": analysis["feature_vector"],
                },
            ),
            self._internal_run(
                stage="predict_scores",
                model_name=score_model_name,
                input_payload={
                    "prompt_id": prompt["id"],
                    "word_count_client": word_count_client,
                    "signals": analysis["signals"],
                    "feature_vector": analysis["feature_vector"],
                },
                output_payload=score_payload,
            ),
        ]

        llm_feedback_seed: dict[str, Any] = {}
        if self.mode == "hybrid" and self._llm_enabled():
            refined_scores, llm_run = self._refine_scores_with_llm(prompt, text, analysis, score_payload)
            model_runs.append(llm_run)
            if llm_run["status"] == "completed" and refined_scores:
                score_payload = refined_scores
                llm_feedback_seed = {
                    "strengths": llm_run["output_payload"].get("strengths", []),
                    "priority_issues": llm_run["output_payload"].get("priority_issues", []),
                    "rewrite_focus": llm_run["output_payload"].get("rewrite_focus"),
                    "scoring_notes": llm_run["output_payload"].get("scoring_notes", []),
                }

        feedback_payload = self._local_feedback(prompt, text, analysis, score_payload, llm_feedback_seed)
        if self.mode in {"feedback", "hybrid"} and self._llm_enabled():
            refined_feedback, llm_run = self._generate_feedback_with_llm(prompt, text, analysis, score_payload, feedback_payload)
            model_runs.append(llm_run)
            if llm_run["status"] == "completed" and refined_feedback:
                feedback_payload = refined_feedback

        review_payload = self._build_review_payload(
            prompt=prompt,
            analysis=analysis,
            score_payload=score_payload,
        )

        return {
            "score_payload": score_payload,
            "review_payload": review_payload,
            "feedback_payload": feedback_payload,
            "model_runs": model_runs,
        }

    def summarize_comparison(
        self,
        *,
        prompt: dict[str, Any],
        base_text: str,
        compare_text: str,
        base_scores: dict[str, Any],
        compare_scores: dict[str, Any],
    ) -> dict[str, Any]:
        local_summary = self._local_comparison(base_scores, compare_scores)
        if self.mode in {"feedback", "hybrid"} and self._llm_enabled():
            summary, llm_run = self._generate_comparison_with_llm(
                prompt=prompt,
                base_text=base_text,
                compare_text=compare_text,
                base_scores=base_scores,
                compare_scores=compare_scores,
                local_summary=local_summary,
            )
            if llm_run["status"] == "completed" and summary:
                return {"comparison_payload": summary, "model_runs": [llm_run]}
            return {"comparison_payload": local_summary, "model_runs": [llm_run]}
        return {"comparison_payload": local_summary, "model_runs": []}

    def prescore(
        self,
        *,
        prompt: dict[str, Any],
        text: str,
        time_spent_sec: int,
        word_count_client: int | None = None,
    ) -> dict[str, Any]:
        analysis = extract_features(prompt, text, time_spent_sec)
        score_payload, score_model_name = self._baseline_scores(prompt, analysis)
        review_payload = self._build_review_payload(
            prompt=prompt,
            analysis=analysis,
            score_payload=score_payload,
        )
        feedback_payload = self._local_feedback(prompt, text, analysis, score_payload, {})
        return {
            "score_payload": score_payload,
            "review_payload": review_payload,
            "feedback_payload": feedback_payload,
            "model_runs": [
                self._internal_run(
                    stage="extract_features",
                    model_name="feature-engine-v1",
                    input_payload={
                        "prompt_id": prompt["id"],
                        "text_length": len(text),
                        "time_spent_sec": time_spent_sec,
                    },
                    output_payload={
                        "signals": analysis["signals"],
                        "evidence": analysis["evidence"],
                        "feature_vector": analysis["feature_vector"],
                    },
                ),
                self._internal_run(
                    stage="prescore",
                    model_name=score_model_name,
                    input_payload={
                        "prompt_id": prompt["id"],
                        "word_count_client": word_count_client,
                        "signals": analysis["signals"],
                        "feature_vector": analysis["feature_vector"],
                    },
                    output_payload={
                        "scores": score_payload["scores"],
                        "review": review_payload,
                    },
                ),
            ],
        }

    def _baseline_scores(self, prompt: dict[str, Any], analysis: dict[str, Any]) -> tuple[dict[str, Any], str]:
        if self.trained_scorer is not None:
            trained_scores = self.trained_scorer.predict(analysis["feature_vector"])
            score_payload = {
                "scores": trained_scores,
                "signals": analysis["signals"],
                "evidence": analysis["evidence"],
            }
            return score_payload, self.trained_scorer.version

        signals = analysis["signals"]
        evidence = analysis["evidence"]
        task_score = round_score(
            1.0
            + (signals["task_coverage"] * 2.5)
            + (0.75 if evidence["within_target_word_count"] else 0.3)
            + (0.45 if signals["word_count"] >= prompt["target_word_count_min"] else 0.0)
        )
        org_score = round_score(
            1.2
            + min(signals["paragraph_count"], 3) * 0.75
            + min(signals["connectors"], 5) * 0.18
            + (signals["sentence_variety"] * 0.9)
            - (signals["long_sentence_ratio"] * 0.6)
        )
        grammar_score = round_score(
            4.6
            - (signals["grammar_error_rate"] * 4.2)
            - (evidence["lowercase_sentence_starts"] * 0.15)
            - (0.5 if signals["word_count"] < prompt["target_word_count_min"] else 0.0)
        )
        lexical_penalty = 0.15 * len(evidence["repeated_words"])
        lexical_score = round_score(
            1.4
            + (signals["lexical_diversity"] * 3.9)
            + (signals["sentence_variety"] * 0.35)
            - lexical_penalty
        )
        overall = round(task_score + org_score + grammar_score + lexical_score, 2)
        readiness = self._readiness_label(overall)
        confidence = round(
            clamp(
                0.6
                + (signals["word_count"] / max(150.0, float(prompt["target_word_count_max"])))
                + (signals["task_coverage"] * 0.12)
                - (signals["off_topic_risk"] * 0.05),
                0.58,
                0.94,
            ),
            3,
        )
        dimension_confidence = {
            "task_achievement": round(clamp(confidence + 0.02, 0.55, 0.96), 3),
            "organization_coherence": round(clamp(confidence - 0.01, 0.55, 0.96), 3),
            "grammar_control": round(clamp(confidence - 0.03, 0.55, 0.96), 3),
            "lexical_range_accuracy": round(clamp(confidence - 0.01, 0.55, 0.96), 3),
        }
        return (
            {
                "scores": {
                    "overall": overall,
                    "readiness": readiness,
                    "confidence": confidence,
                    "dimensions": {
                        "task_achievement": task_score,
                        "organization_coherence": org_score,
                        "grammar_control": grammar_score,
                        "lexical_range_accuracy": lexical_score,
                    },
                    "dimension_confidence": dimension_confidence,
                },
                "signals": signals,
                "evidence": evidence,
            },
            "heuristic-rubric-v1",
        )

    def _refine_scores_with_llm(
        self,
        prompt: dict[str, Any],
        text: str,
        analysis: dict[str, Any],
        score_payload: dict[str, Any],
    ) -> tuple[dict[str, Any] | None, dict[str, Any]]:
        input_payload = {
            "prompt": {
                "title": prompt["title"],
                "instructions": prompt["instructions"],
                "task_type": prompt["task_type"],
            },
            "essay": text,
            "baseline_scores": score_payload["scores"],
            "signals": analysis["signals"],
            "evidence": analysis["evidence"],
        }
        run_base = self._failed_run("llm_score_refinement", input_payload)
        try:
            result = self.llm_client.complete_json(
                system_prompt=SCORE_REFINEMENT_SYSTEM_PROMPT,
                user_prompt=self._score_refinement_prompt(prompt, text, analysis, score_payload),
                temperature=0.1,
            )
            run_base.update(self._llm_run_to_dict(result, input_payload, stage="llm_score_refinement"))
            merged = self._merge_refined_scores(score_payload, result.output_payload)
            return merged, run_base
        except LLMClientError as exc:
            run_base["error_message"] = str(exc)
            return None, run_base

    def _generate_feedback_with_llm(
        self,
        prompt: dict[str, Any],
        text: str,
        analysis: dict[str, Any],
        score_payload: dict[str, Any],
        fallback_feedback: dict[str, Any],
    ) -> tuple[dict[str, Any] | None, dict[str, Any]]:
        input_payload = {
            "prompt": {
                "title": prompt["title"],
                "instructions": prompt["instructions"],
                "task_type": prompt["task_type"],
            },
            "essay": text,
            "scores": score_payload["scores"],
            "signals": analysis["signals"],
            "fallback_feedback": fallback_feedback,
        }
        run_base = self._failed_run("llm_feedback_generation", input_payload)
        try:
            result = self.llm_client.complete_json(
                system_prompt=FEEDBACK_SYSTEM_PROMPT,
                user_prompt=self._feedback_prompt(prompt, text, analysis, score_payload, fallback_feedback),
                temperature=0.2,
            )
            run_base.update(self._llm_run_to_dict(result, input_payload, stage="llm_feedback_generation"))
            merged = self._merge_feedback(text, fallback_feedback, result.output_payload)
            return merged, run_base
        except LLMClientError as exc:
            run_base["error_message"] = str(exc)
            return None, run_base

    def _generate_comparison_with_llm(
        self,
        *,
        prompt: dict[str, Any],
        base_text: str,
        compare_text: str,
        base_scores: dict[str, Any],
        compare_scores: dict[str, Any],
        local_summary: dict[str, Any],
    ) -> tuple[dict[str, Any] | None, dict[str, Any]]:
        input_payload = {
            "prompt": {"title": prompt["title"], "task_type": prompt["task_type"]},
            "base_text": base_text,
            "compare_text": compare_text,
            "base_scores": base_scores,
            "compare_scores": compare_scores,
            "local_summary": local_summary,
        }
        run_base = self._failed_run("llm_comparison_generation", input_payload)
        try:
            result = self.llm_client.complete_json(
                system_prompt=COMPARISON_SYSTEM_PROMPT,
                user_prompt=self._comparison_prompt(prompt, base_text, compare_text, base_scores, compare_scores, local_summary),
                temperature=0.2,
            )
            run_base.update(self._llm_run_to_dict(result, input_payload, stage="llm_comparison_generation"))
            payload = {
                "score_delta": local_summary["score_delta"],
                "improved": self._safe_string_list(result.output_payload.get("improved"), fallback=local_summary["improved"]),
                "still_needs_work": self._safe_string_list(
                    result.output_payload.get("still_needs_work"), fallback=local_summary["still_needs_work"]
                ),
            }
            return payload, run_base
        except LLMClientError as exc:
            run_base["error_message"] = str(exc)
            return None, run_base

    def _merge_refined_scores(self, baseline: dict[str, Any], refinement: dict[str, Any]) -> dict[str, Any]:
        original = baseline["scores"]["dimensions"]
        raw_dims = refinement.get("dimension_scores", {})
        if not isinstance(raw_dims, dict):
            return baseline
        merged_dims: dict[str, float] = {}
        for key, base_score in original.items():
            proposed = raw_dims.get(key, base_score)
            try:
                proposed_value = float(proposed)
            except (TypeError, ValueError):
                proposed_value = base_score
            merged_dims[key] = round_score(clamp(proposed_value, base_score - 0.75, base_score + 0.75))
        overall = round(sum(merged_dims.values()), 2)
        readiness = refinement.get("readiness") or self._readiness_label(overall)
        confidence_boost = refinement.get("confidence_boost", 0.0)
        try:
            confidence_boost_value = float(confidence_boost)
        except (TypeError, ValueError):
            confidence_boost_value = 0.0
        confidence = round(clamp(baseline["scores"]["confidence"] + confidence_boost_value, 0.58, 0.96), 3)
        dimension_confidence = {
            key: round(clamp(value + 0.01, 0.55, 0.97), 3)
            for key, value in baseline["scores"]["dimension_confidence"].items()
        }
        merged = {
            "scores": {
                "overall": overall,
                "readiness": readiness,
                "confidence": confidence,
                "dimensions": merged_dims,
                "dimension_confidence": dimension_confidence,
            },
            "signals": baseline["signals"],
            "evidence": dict(baseline["evidence"]),
        }
        merged["evidence"]["llm_scoring_notes"] = self._safe_string_list(refinement.get("scoring_notes"), fallback=[])
        return merged

    def _local_feedback(
        self,
        prompt: dict[str, Any],
        text: str,
        analysis: dict[str, Any],
        score_payload: dict[str, Any],
        llm_feedback_seed: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        llm_feedback_seed = llm_feedback_seed or {}
        dimensions = score_payload["scores"]["dimensions"]
        signals = analysis["signals"]
        evidence = analysis["evidence"]
        sorted_dims = sorted(dimensions.items(), key=lambda item: item[1], reverse=True)
        strengths = self._safe_string_list(llm_feedback_seed.get("strengths"), fallback=[])
        strength_messages = {
            "task_achievement": "You covered most of the required content points.",
            "organization_coherence": "Your ideas are organized clearly enough for the reader to follow.",
            "grammar_control": "Most sentences are understandable and grammar errors do not often block meaning.",
            "lexical_range_accuracy": "Your vocabulary is more varied than a basic PET template response.",
        }
        for dimension, score in sorted_dims:
            if score >= 3.5 and len(strengths) < 2:
                strengths.append(strength_messages[dimension])
        if not strengths:
            strengths = [
                "You stayed focused on the task and produced a complete draft.",
                "There is enough content here to improve through rewriting.",
            ]
        priority_issues = self._safe_string_list(llm_feedback_seed.get("priority_issues"), fallback=[])
        if signals["word_count"] < prompt["target_word_count_min"]:
            priority_issues.append("Write a little more so you can develop each idea properly.")
        if evidence["missing_content_points"]:
            priority_issues.append(
                "Add the missing task point about " + ", ".join(evidence["missing_content_points"][:2]) + "."
            )
        if dimensions["organization_coherence"] < 3.5:
            priority_issues.append("Use clearer paragraph transitions so the reader can follow your ideas more easily.")
        if dimensions["grammar_control"] < 3.5:
            priority_issues.append("Fix grammar errors in tense, articles, or verb forms before rewriting.")
        if evidence["repeated_words"]:
            priority_issues.append(
                "Replace repeated words such as "
                + ", ".join(evidence["repeated_words"][:2])
                + " with more precise vocabulary."
            )
        if not priority_issues:
            priority_issues = ["Make your ending respond more directly to the writing purpose."]
        priority_issues = list(dict.fromkeys(priority_issues))[:3]
        while len(priority_issues) < 3:
            priority_issues.append("Make your ending respond more directly to the writing purpose.")

        rewrite_focus = llm_feedback_seed.get("rewrite_focus")
        if rewrite_focus not in dimensions:
            rewrite_focus = min(dimensions.items(), key=lambda item: item[1])[0]
        rewrite_task = self._rewrite_task_for_focus(prompt, rewrite_focus, evidence)

        sentence_suggestions = analysis["sentence_suggestions"] or fallback_sentence_suggestions(text)
        for index, item in enumerate(sentence_suggestions, start=1):
            item["sort_order"] = index
        return {
            "strengths": strengths[:2],
            "priority_issues": priority_issues,
            "sentence_suggestions": sentence_suggestions[:3],
            "rewrite_task": rewrite_task,
        }

    def _build_review_payload(
        self,
        *,
        prompt: dict[str, Any],
        analysis: dict[str, Any],
        score_payload: dict[str, Any],
    ) -> dict[str, Any]:
        signals = analysis["signals"]
        evidence = analysis["evidence"]
        scores = score_payload["scores"]
        reasons: list[str] = []

        if signals["word_count"] < prompt["target_word_count_min"]:
            reasons.append("below_target_word_count")
        elif signals["word_count"] > prompt["target_word_count_max"]:
            reasons.append("above_target_word_count")

        if signals["task_coverage"] < 0.67:
            reasons.append("low_task_coverage")
        if signals["off_topic_risk"] >= 0.45:
            reasons.append("off_topic_risk")
        if scores["confidence"] < 0.72:
            reasons.append("low_overall_confidence")
        if min(scores["dimension_confidence"].values()) < 0.68:
            reasons.append("low_dimension_confidence")
        if evidence["lowercase_sentence_starts"] >= 2:
            reasons.append("surface_quality_risk")

        unique_reasons = list(dict.fromkeys(reasons))
        return {
            "needs_review": bool(unique_reasons),
            "review_status": "required" if unique_reasons else "not_required",
            "review_reason_codes": unique_reasons,
        }

    def _merge_feedback(self, text: str, fallback: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        strengths = self._safe_string_list(payload.get("strengths"), fallback=fallback["strengths"])[:2]
        priority_issues = self._safe_string_list(payload.get("priority_issues"), fallback=fallback["priority_issues"])[:3]
        rewrite_task = payload.get("rewrite_task")
        if not isinstance(rewrite_task, dict) or not rewrite_task.get("title") or not rewrite_task.get("instruction"):
            rewrite_task = fallback["rewrite_task"]
        sentence_suggestions = self._safe_sentence_suggestions(
            text, payload.get("sentence_suggestions"), fallback=fallback["sentence_suggestions"]
        )
        for index, item in enumerate(sentence_suggestions, start=1):
            item["sort_order"] = index
        return {
            "strengths": strengths,
            "priority_issues": priority_issues,
            "sentence_suggestions": sentence_suggestions[:3],
            "rewrite_task": rewrite_task,
        }

    def _local_comparison(self, base_scores: dict[str, Any], compare_scores: dict[str, Any]) -> dict[str, Any]:
        base_dimensions = base_scores["dimensions"]
        compare_dimensions = compare_scores["dimensions"]
        score_delta = {
            "overall": round(compare_scores["overall"] - base_scores["overall"], 2),
            "task_achievement": round(compare_dimensions["task_achievement"] - base_dimensions["task_achievement"], 2),
            "organization_coherence": round(
                compare_dimensions["organization_coherence"] - base_dimensions["organization_coherence"], 2
            ),
            "grammar_control": round(compare_dimensions["grammar_control"] - base_dimensions["grammar_control"], 2),
            "lexical_range_accuracy": round(
                compare_dimensions["lexical_range_accuracy"] - base_dimensions["lexical_range_accuracy"], 2
            ),
        }
        improved = []
        still_needs_work = []
        for key, value in score_delta.items():
            if key == "overall":
                continue
            label = key.replace("_", " ").title()
            if value > 0:
                improved.append(f"{label} improved by {value:.2f} points.")
            else:
                still_needs_work.append(f"{label} still needs more improvement.")
        if not improved:
            improved = ["You produced a second draft, which is the right next step for improvement."]
        if not still_needs_work:
            still_needs_work = ["Keep checking task completion and clarity in the next piece of writing."]
        return {
            "score_delta": score_delta,
            "improved": improved,
            "still_needs_work": still_needs_work,
        }

    def _rewrite_task_for_focus(self, prompt: dict[str, Any], focus: str, evidence: dict[str, Any]) -> dict[str, str]:
        missing = evidence.get("missing_content_points", [])
        templates = {
            "task_achievement": {
                "title": "Rewrite for fuller task response",
                "instruction": (
                    f"Rewrite the essay in {prompt['target_word_count_min']}-{prompt['target_word_count_max']} words. "
                    + (
                        "Make sure you clearly answer the missing point about " + ", ".join(missing[:2]) + "."
                        if missing
                        else "Make sure every required content point is answered clearly."
                    )
                ),
            },
            "organization_coherence": {
                "title": "Rewrite for better cohesion",
                "instruction": (
                    f"Rewrite the essay in {prompt['target_word_count_min']}-{prompt['target_word_count_max']} words. "
                    "Use clearer paragraphing and add linking words between ideas."
                ),
            },
            "grammar_control": {
                "title": "Rewrite for better grammar control",
                "instruction": (
                    f"Rewrite the essay in {prompt['target_word_count_min']}-{prompt['target_word_count_max']} words. "
                    "Check tense, articles, and verb forms before you submit again."
                ),
            },
            "lexical_range_accuracy": {
                "title": "Rewrite for stronger vocabulary",
                "instruction": (
                    f"Rewrite the essay in {prompt['target_word_count_min']}-{prompt['target_word_count_max']} words. "
                    "Try to replace repeated words with more precise alternatives."
                ),
            },
        }
        return templates[focus]

    def _load_trained_scorer(self, path: str | None) -> TrainableScorerArtifact | None:
        if not path:
            return None
        artifact_path = Path(path)
        if not artifact_path.exists():
            return None
        try:
            return TrainableScorerArtifact.load(artifact_path)
        except Exception:
            return None

    def _llm_enabled(self) -> bool:
        return bool(self.llm_client) and hasattr(self.llm_client, "is_enabled") and self.llm_client.is_enabled()

    @staticmethod
    def _internal_run(stage: str, model_name: str, input_payload: dict[str, Any], output_payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "stage": stage,
            "provider": "internal",
            "model_name": model_name,
            "model_version": "v1",
            "input_payload": input_payload,
            "output_payload": output_payload,
            "latency_ms": 0,
            "status": "completed",
            "error_message": None,
        }

    def _failed_run(self, stage: str, input_payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "stage": stage,
            "provider": "openai-compatible",
            "model_name": getattr(self.llm_client, "model", "unknown"),
            "model_version": None,
            "input_payload": input_payload,
            "output_payload": {},
            "latency_ms": None,
            "status": "failed",
            "error_message": None,
        }

    @staticmethod
    def _llm_run_to_dict(result: LLMCallResult, input_payload: dict[str, Any], stage: str) -> dict[str, Any]:
        return {
            "stage": stage,
            "provider": result.provider,
            "model_name": result.model_name,
            "model_version": result.model_version,
            "input_payload": input_payload,
            "output_payload": result.output_payload,
            "latency_ms": result.latency_ms,
            "status": "completed",
            "error_message": None,
        }

    @staticmethod
    def _safe_string_list(value: Any, fallback: list[str]) -> list[str]:
        if isinstance(value, list):
            cleaned = [item.strip() for item in value if isinstance(item, str) and item.strip()]
            if cleaned:
                return cleaned
        return list(fallback)

    def _safe_sentence_suggestions(
        self,
        text: str,
        value: Any,
        fallback: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if isinstance(value, list):
            suggestions = []
            lowered_text = text.lower()
            for item in value:
                if not isinstance(item, dict):
                    continue
                original = item.get("original")
                suggestion = item.get("suggestion")
                reason = item.get("reason")
                if not all(isinstance(piece, str) and piece.strip() for piece in [original, suggestion, reason]):
                    continue
                if original.strip().lower() not in lowered_text:
                    continue
                suggestions.append(
                    {
                        "issue_type": item.get("issue_type", "revision"),
                        "original": original.strip(),
                        "suggestion": suggestion.strip(),
                        "reason": reason.strip(),
                        "evidence": item.get("evidence", {"source": "llm"}),
                    }
                )
            if suggestions:
                return suggestions
        return list(fallback)

    @staticmethod
    def _readiness_label(overall_score: float) -> str:
        if overall_score >= 15:
            return "on_track"
        if overall_score >= 11:
            return "borderline"
        return "below_target"

    @staticmethod
    def _score_refinement_prompt(
        prompt: dict[str, Any],
        text: str,
        analysis: dict[str, Any],
        score_payload: dict[str, Any],
    ) -> str:
        return (
            "Return JSON with keys: dimension_scores, confidence_boost, readiness, scoring_notes, "
            "strengths, priority_issues, rewrite_focus.\n\n"
            f"Prompt:\n{prompt['title']}\n{prompt['instructions']}\n\n"
            f"Essay:\n{text}\n\n"
            f"Signals:\n{analysis['signals']}\n\n"
            f"Evidence:\n{analysis['evidence']}\n\n"
            f"Baseline scores:\n{score_payload['scores']}\n"
        )

    @staticmethod
    def _feedback_prompt(
        prompt: dict[str, Any],
        text: str,
        analysis: dict[str, Any],
        score_payload: dict[str, Any],
        fallback_feedback: dict[str, Any],
    ) -> str:
        return (
            "Return JSON with keys: strengths, priority_issues, sentence_suggestions, rewrite_task.\n\n"
            f"Prompt:\n{prompt['title']}\n{prompt['instructions']}\n\n"
            f"Essay:\n{text}\n\n"
            f"Scores:\n{score_payload['scores']}\n\n"
            f"Signals:\n{analysis['signals']}\n\n"
            f"Fallback feedback:\n{fallback_feedback}\n"
        )

    @staticmethod
    def _comparison_prompt(
        prompt: dict[str, Any],
        base_text: str,
        compare_text: str,
        base_scores: dict[str, Any],
        compare_scores: dict[str, Any],
        local_summary: dict[str, Any],
    ) -> str:
        return (
            "Return JSON with keys: improved, still_needs_work.\n\n"
            f"Prompt:\n{prompt['title']}\n{prompt['instructions']}\n\n"
            f"Draft one:\n{base_text}\n\n"
            f"Draft two:\n{compare_text}\n\n"
            f"Draft one scores:\n{base_scores}\n\n"
            f"Draft two scores:\n{compare_scores}\n\n"
            f"Local summary:\n{local_summary}\n"
        )
