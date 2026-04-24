"""Shared feature extraction utilities for PET Writing."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any


WORD_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
COMMON_CONNECTORS = {
    "because",
    "however",
    "also",
    "first",
    "second",
    "finally",
    "then",
    "after",
    "before",
    "although",
    "but",
    "so",
    "therefore",
    "besides",
    "for",
    "example",
}
COMMON_MISTAKE_PATTERNS = [
    (re.compile(r"\bi very enjoy\b", re.IGNORECASE), "I really enjoy", "Use an adverb before 'enjoy'."),
    (re.compile(r"\bmore better\b", re.IGNORECASE), "better", "Do not use a double comparative."),
    (re.compile(r"\bhe go\b", re.IGNORECASE), "he goes", "Use the correct third-person singular form."),
    (re.compile(r"\bshe go\b", re.IGNORECASE), "she goes", "Use the correct third-person singular form."),
    (re.compile(r"\bi am agree\b", re.IGNORECASE), "I agree", "Use 'agree' directly without 'am'."),
]

FEATURE_NAMES = [
    "word_count",
    "paragraph_count",
    "task_coverage",
    "grammar_error_rate",
    "lexical_diversity",
    "sentence_variety",
    "off_topic_risk",
    "connectors",
    "connector_density",
    "avg_sentence_length",
    "long_sentence_ratio",
    "within_target_word_count",
    "content_hits",
    "missing_content_count",
    "repeated_word_count",
    "lowercase_sentence_starts",
    "time_spent_min",
    "task_type_email",
    "task_type_article",
]


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def words(text: str) -> list[str]:
    return WORD_RE.findall(text)


def sentences(text: str) -> list[str]:
    chunks = [part.strip() for part in SENTENCE_SPLIT_RE.split(text.strip()) if part.strip()]
    return chunks or [text.strip()]


def paragraph_count(text: str) -> int:
    paragraphs = [part.strip() for part in text.splitlines() if part.strip()]
    return max(1, len(paragraphs))


def find_sentence_suggestions(text: str) -> list[dict[str, Any]]:
    suggestions: list[dict[str, Any]] = []
    for sentence in sentences(text):
        updated = sentence
        reasons = []
        for pattern, replacement, reason in COMMON_MISTAKE_PATTERNS:
            if pattern.search(updated):
                updated = pattern.sub(replacement, updated)
                reasons.append(reason)
        if sentence and sentence[0].islower():
            updated = sentence[0].upper() + sentence[1:]
            reasons.append("Start the sentence with a capital letter.")
        if updated != sentence and reasons:
            suggestions.append(
                {
                    "issue_type": "grammar",
                    "original": sentence,
                    "suggestion": updated,
                    "reason": " ".join(dict.fromkeys(reasons)),
                    "evidence": {"pattern_based": True},
                }
            )
    return suggestions[:3]


def fallback_sentence_suggestions(text: str) -> list[dict[str, Any]]:
    parts = sentences(text)
    if not parts:
        return []
    first = parts[0]
    improved = f"First, {first[0].lower() + first[1:]}" if first else first
    return [
        {
            "issue_type": "cohesion",
            "original": first,
            "suggestion": improved,
            "reason": "A clearer opening can make the whole response easier to follow.",
            "evidence": {"fallback": True},
        }
    ]


def extract_features(prompt: dict[str, Any], text: str, time_spent_sec: int) -> dict[str, Any]:
    token_list = words(text)
    lowered_words = [word.lower() for word in token_list]
    word_count = len(token_list)
    para_count = paragraph_count(text)
    sentence_list = sentences(text)
    sentence_count = max(1, len(sentence_list))
    sentence_lengths = [len(words(sentence)) for sentence in sentence_list] or [0]
    avg_sentence_length = round(sum(sentence_lengths) / max(1, len(sentence_lengths)), 2)
    long_sentence_ratio = round(sum(1 for length in sentence_lengths if length >= 22) / max(1, sentence_count), 3)
    connectors_used = [word for word in lowered_words if word in COMMON_CONNECTORS]
    lexical_diversity = round(len(set(lowered_words)) / max(1, word_count), 3)
    repeated_words = [word for word, count in Counter(lowered_words).items() if count >= 4 and len(word) > 3][:5]
    content_groups = prompt.get("metadata", {}).get("content_points", [])
    content_hits = 0
    missing_content_points: list[str] = []
    text_lower = text.lower()
    for group in content_groups:
        if any(token.lower() in text_lower for token in group):
            content_hits += 1
        elif group:
            missing_content_points.append(group[0])
    task_coverage = round(content_hits / max(1, len(content_groups)), 3)
    sentence_suggestions = find_sentence_suggestions(text)
    grammar_error_rate = round(len(sentence_suggestions) / max(1, sentence_count), 3)
    sentence_variety = round(clamp(len(set(sentence_lengths)) / max(1, sentence_count), 0.0, 1.0), 3)
    within_target = prompt["target_word_count_min"] <= word_count <= prompt["target_word_count_max"]
    lowercase_sentence_starts = sum(1 for sentence in sentence_list if sentence and sentence[0].islower())
    off_topic_risk = round(clamp(0.85 - task_coverage, 0.0, 1.0), 3)
    signals = {
        "word_count": word_count,
        "paragraph_count": para_count,
        "task_coverage": task_coverage,
        "grammar_error_rate": grammar_error_rate,
        "lexical_diversity": lexical_diversity,
        "sentence_variety": sentence_variety,
        "off_topic_risk": off_topic_risk,
        "connectors": len(connectors_used),
        "connector_density": round(len(connectors_used) / max(1, sentence_count), 3),
        "avg_sentence_length": avg_sentence_length,
        "long_sentence_ratio": long_sentence_ratio,
        "time_spent_sec": time_spent_sec,
    }
    evidence = {
        "sentence_count": sentence_count,
        "within_target_word_count": within_target,
        "content_hits": content_hits,
        "content_groups": content_groups,
        "missing_content_points": missing_content_points,
        "repeated_words": repeated_words,
        "lowercase_sentence_starts": lowercase_sentence_starts,
    }
    vector = vectorize_features(prompt, signals, evidence)
    return {
        "signals": signals,
        "evidence": evidence,
        "sentence_suggestions": sentence_suggestions,
        "feature_vector": vector,
    }


def vectorize_features(prompt: dict[str, Any], signals: dict[str, Any], evidence: dict[str, Any]) -> dict[str, float]:
    task_type = (prompt.get("task_type") or "").lower()
    return {
        "word_count": float(signals["word_count"]),
        "paragraph_count": float(signals["paragraph_count"]),
        "task_coverage": float(signals["task_coverage"]),
        "grammar_error_rate": float(signals["grammar_error_rate"]),
        "lexical_diversity": float(signals["lexical_diversity"]),
        "sentence_variety": float(signals["sentence_variety"]),
        "off_topic_risk": float(signals["off_topic_risk"]),
        "connectors": float(signals["connectors"]),
        "connector_density": float(signals["connector_density"]),
        "avg_sentence_length": float(signals["avg_sentence_length"]),
        "long_sentence_ratio": float(signals["long_sentence_ratio"]),
        "within_target_word_count": 1.0 if evidence["within_target_word_count"] else 0.0,
        "content_hits": float(evidence["content_hits"]),
        "missing_content_count": float(len(evidence["missing_content_points"])),
        "repeated_word_count": float(len(evidence["repeated_words"])),
        "lowercase_sentence_starts": float(evidence["lowercase_sentence_starts"]),
        "time_spent_min": round(float(signals["time_spent_sec"]) / 60.0, 3),
        "task_type_email": 1.0 if task_type == "email" else 0.0,
        "task_type_article": 1.0 if task_type == "article" else 0.0,
    }
