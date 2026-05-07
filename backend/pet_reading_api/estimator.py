"""Deterministic Lexile-like reading estimate logic."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


SKILLS = (
    "main_idea",
    "detail",
    "inference",
    "vocabulary_context",
    "structure_author_purpose",
)
MIN_VALID_PASSAGES = 6


def estimate_reading_level(
    *,
    responses: list[dict[str, Any]],
    passages_completed: int,
    duration_seconds: int,
) -> dict[str, Any]:
    flags = _validity_flags(responses, passages_completed, duration_seconds)
    buckets = _bucket_accuracy(responses)
    lower, upper, status = _estimate_range(buckets, responses)
    practice_lower = max(500, lower - 70)
    practice_upper = max(practice_lower, min(1100, upper - 60))
    confidence = _confidence_label(flags, buckets, passages_completed)
    domain_scores = _domain_scores(responses)

    if status == "above_target_range":
        flags.append("ABOVE_TARGET_RANGE")
    if status == "below_target_range":
        flags.append("BELOW_TARGET_RANGE")

    return {
        "estimated_lower_lexile": lower,
        "estimated_upper_lexile": upper,
        "practice_lower_lexile": practice_lower,
        "practice_upper_lexile": practice_upper,
        "cefr_estimate": _cefr_for_midpoint((lower + upper) // 2),
        "confidence_label": confidence,
        "range_status": status,
        "validity_flags": sorted(set(flags)),
        "domain_scores": domain_scores,
        "bucket_summary": buckets,
        "summary": _summary_text(lower, upper, status),
        "recommendations": _recommendations(practice_lower, practice_upper, status),
    }


def _validity_flags(responses: list[dict[str, Any]], passages_completed: int, duration_seconds: int) -> list[str]:
    flags: list[str] = []
    if passages_completed < MIN_VALID_PASSAGES:
        flags.append("TOO_FEW_PASSAGES")
    if duration_seconds < 600:
        flags.append("TOO_FAST_OVERALL")
    rushed = [item for item in responses if int(item.get("time_seconds", 0)) < 5]
    if responses and len(rushed) / len(responses) >= 0.3:
        flags.append("MANY_RUSHED_ITEMS")
    return flags


def _bucket_accuracy(responses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for item in responses:
        lexile = int(item["estimated_item_lexile"])
        bucket = (lexile // 100) * 100
        grouped[bucket].append(item)

    summary: list[dict[str, Any]] = []
    for bucket in sorted(grouped):
        items = grouped[bucket]
        correct = sum(1 for item in items if bool(item.get("correct")))
        total = len(items)
        accuracy = correct / total if total else 0.0
        summary.append(
            {
                "bucket_start": bucket,
                "bucket_end": bucket + 99,
                "correct": correct,
                "total": total,
                "accuracy": round(accuracy, 3),
                "status": _bucket_status(accuracy),
            }
        )
    return summary


def _bucket_status(accuracy: float) -> str:
    if accuracy >= 0.85:
        return "mastered"
    if accuracy >= 0.70:
        return "readable"
    if accuracy >= 0.50:
        return "challenge"
    return "too_difficult"


def _estimate_range(buckets: list[dict[str, Any]], responses: list[dict[str, Any]]) -> tuple[int, int, str]:
    if not buckets:
        return 500, 650, "below_target_range"

    readable = [bucket for bucket in buckets if bucket["status"] in {"mastered", "readable"}]
    difficult = [bucket for bucket in buckets if bucket["status"] in {"challenge", "too_difficult"}]

    if readable and readable[-1]["bucket_start"] >= 1000 and not difficult:
        return 1000, 1100, "above_target_range"
    if difficult and difficult[0]["bucket_start"] <= 500 and not readable:
        return 500, 650, "below_target_range"

    readable_bucket_starts = {bucket["bucket_start"] for bucket in readable}
    correct_lexiles = [
        int(item["estimated_item_lexile"])
        for item in responses
        if bool(item.get("correct")) and (int(item["estimated_item_lexile"]) // 100) * 100 in readable_bucket_starts
    ]
    stable_level = max(correct_lexiles) if correct_lexiles else buckets[0]["bucket_start"]
    failed_buckets = [bucket for bucket in buckets if bucket["correct"] == 0]
    challenge_level = failed_buckets[0]["bucket_start"] if failed_buckets else min(1100, stable_level + 200)
    lower = max(500, stable_level - 50)
    upper = min(1100, challenge_level + 50)
    if upper <= lower:
        upper = min(1100, lower + 150)
    return lower, upper, "in_target_range"


def _domain_scores(responses: list[dict[str, Any]]) -> dict[str, int]:
    points: dict[str, float] = {skill: 0.0 for skill in SKILLS}
    possible: dict[str, float] = {skill: 0.0 for skill in SKILLS}
    for item in responses:
        skill = str(item["skill"])
        if skill not in points:
            continue
        weight = _difficulty_weight(int(item["estimated_item_lexile"]))
        possible[skill] += weight
        if bool(item.get("correct")):
            points[skill] += weight
    return {
        skill: round((points[skill] / possible[skill]) * 100) if possible[skill] else 0
        for skill in SKILLS
    }


def _difficulty_weight(lexile: int) -> float:
    if lexile < 650:
        return 1.0
    if lexile < 800:
        return 1.2
    if lexile < 950:
        return 1.4
    return 1.6


def _confidence_label(flags: list[str], buckets: list[dict[str, Any]], passages_completed: int) -> str:
    if flags:
        return "Low"
    statuses = {bucket["status"] for bucket in buckets}
    if passages_completed >= 4 and len(buckets) >= 3 and "challenge" not in statuses:
        return "High"
    return "Medium"


def _cefr_for_midpoint(midpoint: int) -> str:
    if midpoint < 650:
        return "A2-"
    if midpoint < 800:
        return "A2"
    if midpoint < 950:
        return "A2+"
    return "B1"


def _summary_text(lower: int, upper: int, status: str) -> str:
    if status == "above_target_range":
        return "The student performed strongly at the top of this assessment range."
    if status == "below_target_range":
        return "The student struggled with the foundation texts in this assessment range."
    return f"The student is estimated to read independently around {lower}L-{upper}L with normal support."


def _recommendations(practice_lower: int, practice_upper: int, status: str) -> list[str]:
    if status == "above_target_range":
        return ["Use the advanced version covering 1000L-1300L."]
    if status == "below_target_range":
        return ["Use the foundation version covering 300L-650L."]
    return [
        f"Read {practice_lower}L-{practice_upper}L texts independently.",
        f"Use {practice_upper}L-{min(1100, practice_upper + 100)}L texts with teacher support.",
    ]
