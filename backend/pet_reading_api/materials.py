"""Parent-facing reading material recommendations."""

from __future__ import annotations

from typing import Any


READING_MATERIALS: list[dict[str, Any]] = [
    {
        "id": "mat_school_garden_520",
        "title": "A School Garden After the Rain",
        "format": "short_article",
        "lexile": 520,
        "genre": "informational",
        "topic": "school_life",
        "length": "short",
    },
    {
        "id": "mat_library_robot_600",
        "title": "The Library Robot",
        "format": "short_story",
        "lexile": 600,
        "genre": "fiction",
        "topic": "technology",
        "length": "short",
    },
    {
        "id": "mat_lost_map_680",
        "title": "The Lost Map at the Station",
        "format": "graded_reader_chapter",
        "lexile": 680,
        "genre": "fiction",
        "topic": "mystery",
        "length": "medium",
    },
    {
        "id": "mat_city_bees_740",
        "title": "Why Cities Need Bees",
        "format": "magazine_article",
        "lexile": 740,
        "genre": "informational",
        "topic": "science",
        "length": "medium",
    },
    {
        "id": "mat_volunteer_farm_800",
        "title": "A Summer on a French Farm",
        "format": "personal_narrative",
        "lexile": 800,
        "genre": "literary_nonfiction",
        "topic": "travel",
        "length": "medium",
    },
    {
        "id": "mat_mountain_weather_860",
        "title": "Reading Weather on the Mountain",
        "format": "science_article",
        "lexile": 860,
        "genre": "informational",
        "topic": "nature",
        "length": "medium",
    },
    {
        "id": "mat_sleep_research_930",
        "title": "Why One School Started Later",
        "format": "argument_article",
        "lexile": 930,
        "genre": "informational",
        "topic": "health",
        "length": "medium",
    },
    {
        "id": "mat_debate_plastic_1020",
        "title": "The Debate About Plastic Waste",
        "format": "long_article",
        "lexile": 1020,
        "genre": "informational",
        "topic": "environment",
        "length": "long",
    },
]


def build_parent_material_recommendations(
    *,
    assessment_id: str,
    practice_lower_lexile: int,
    practice_upper_lexile: int,
    grade_level: int | None,
) -> dict[str, Any]:
    """Build deterministic material buckets for parent book selection."""

    challenge_upper = min(1100, practice_upper_lexile + 100)
    buckets = {
        "confidence_or_warmup": _bucket(
            fit_label="confidence_or_warmup",
            label="Confidence or warm-up",
            range_text=f"below {practice_lower_lexile}L",
            lower=0,
            upper=practice_lower_lexile - 1,
            parent_action="Use for relaxed reading, review, or rebuilding confidence.",
            why="This is easier than the growth zone, so the child should read with less strain.",
        ),
        "best_fit_daily_reading": _bucket(
            fit_label="best_fit_daily_reading",
            label="Best fit daily reading",
            range_text=f"{practice_lower_lexile}L-{practice_upper_lexile}L",
            lower=practice_lower_lexile,
            upper=practice_upper_lexile,
            parent_action="Choose most routine independent reading from this range.",
            why="This matches the child's ZPD-like practice range for steady growth.",
        ),
        "supported_challenge": _bucket(
            fit_label="supported_challenge",
            label="Supported challenge",
            range_text=f"{practice_upper_lexile}L-{challenge_upper}L",
            lower=practice_upper_lexile,
            upper=challenge_upper,
            parent_action="Use when an adult can discuss vocabulary, plot, or key ideas.",
            why="This is slightly above the daily range and can stretch the child with support.",
        ),
        "frustration_risk": _bucket(
            fit_label="frustration_risk",
            label="Frustration risk",
            range_text=f"above {challenge_upper}L",
            lower=challenge_upper + 1,
            upper=1500,
            parent_action="Avoid for routine reading unless motivation and support are both high.",
            why="This is likely beyond the child's current comfortable practice range.",
        ),
    }
    return {
        "assessment_id": assessment_id,
        "goal": "parent_material_selection",
        "grade_level": grade_level,
        "selection_basis": {
            "zpd_like_range": f"{practice_lower_lexile}L-{practice_upper_lexile}L",
            "source": "internal_reading_estimate",
        },
        "buckets": buckets,
    }


def _bucket(
    *,
    fit_label: str,
    label: str,
    range_text: str,
    lower: int,
    upper: int,
    parent_action: str,
    why: str,
) -> dict[str, Any]:
    return {
        "label": label,
        "range": range_text,
        "parent_action": parent_action,
        "materials": [
            _material_payload(material, fit_label=fit_label, parent_action=parent_action, why=why)
            for material in _select_materials(lower, upper)
        ],
    }


def _select_materials(lower: int, upper: int, *, limit: int = 3) -> list[dict[str, Any]]:
    matches = [material for material in READING_MATERIALS if lower <= int(material["lexile"]) <= upper]
    if matches:
        return sorted(matches, key=lambda material: int(material["lexile"]))[:limit]
    midpoint = max(0, round((lower + upper) / 2))
    return sorted(READING_MATERIALS, key=lambda material: abs(int(material["lexile"]) - midpoint))[:1]


def _material_payload(
    material: dict[str, Any],
    *,
    fit_label: str,
    parent_action: str,
    why: str,
) -> dict[str, Any]:
    return {
        "id": material["id"],
        "title": material["title"],
        "format": material["format"],
        "lexile": f"{material['lexile']}L",
        "genre": material["genre"],
        "topic": material["topic"],
        "length": material["length"],
        "fit_label": fit_label,
        "why_this_fits": why,
        "parent_action": parent_action,
    }
