"""Passage-level adaptive decisions for reading assessment."""

from __future__ import annotations


MIN_ANCHOR = 500
MAX_ANCHOR = 1100


def starting_anchor_for_grade(grade_level: int | None) -> int:
    if grade_level == 6:
        return 700
    if grade_level == 8:
        return 900
    return 800


def next_anchor_lexile(*, current_anchor: int, accuracy: float) -> int:
    if accuracy >= 0.85:
        delta = 125
    elif accuracy >= 0.65:
        delta = 50
    elif accuracy >= 0.45:
        delta = -75
    else:
        delta = -150
    return max(MIN_ANCHOR, min(MAX_ANCHOR, current_anchor + delta))
