"""Candidate reading-bank generation and validation for human review."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


REQUIRED_SKILLS = (
    "main_idea",
    "detail",
    "inference",
    "vocabulary_context",
    "structure_author_purpose",
)


def sample_candidates(count: int = 4) -> list[dict[str, Any]]:
    """Return deterministic candidate passages for review workflow testing."""

    templates = [
        {
            "passage_id": "cand_b2_city_bees",
            "title": "Why Cities Need Bees",
            "anchor_lexile": 740,
            "target_band": "650L-800L",
            "cefr_level": "A2",
            "genre": "informational",
            "topic": "science",
            "body_text": (
                "Many people imagine bees living only in quiet fields, but some bees do very well in cities. "
                "They visit flowers in parks, gardens, and even on balconies. A city can give bees food from early "
                "spring until late autumn because people plant many different kinds of flowers. Some schools now keep "
                "small bee hotels so students can watch how insects help plants grow. The projects also teach children "
                "that a city is not separate from nature. If people avoid harmful sprays and leave some wild plants, "
                "city bees can continue their important work."
            ),
        },
        {
            "passage_id": "cand_b3_weather_mountain",
            "title": "Reading Weather on the Mountain",
            "anchor_lexile": 860,
            "target_band": "800L-950L",
            "cefr_level": "A2+",
            "genre": "informational",
            "topic": "nature",
            "body_text": (
                "Before a mountain walk, Maya's group studied a simple weather report. The guide explained that a sunny "
                "morning did not guarantee a safe afternoon. On high ground, wind can push clouds over the path quickly, "
                "and temperature can fall within minutes. The students packed light raincoats, water, and a paper map. "
                "Halfway up, the sky turned grey, but the group was prepared. They returned by a lower path and reached "
                "the village before heavy rain began. Maya learned that planning is not a sign of fear; it is a way to "
                "enjoy nature responsibly."
            ),
        },
        {
            "passage_id": "cand_b1_library_robot",
            "title": "The Library Robot",
            "anchor_lexile": 610,
            "target_band": "500L-650L",
            "cefr_level": "A2-",
            "genre": "narrative",
            "topic": "technology",
            "body_text": (
                "Class Seven built a small robot for the school library. It had a flat top for books and slow wheels that "
                "followed a black line on the floor. At first, some students wanted the robot to move quickly, but their "
                "teacher asked them to watch the younger children in the library. The team noticed that the room was often "
                "busy and crowded. A slow robot would be safer and easier to stop. At the technology fair, the judges liked "
                "the robot because it solved a real problem in a careful way."
            ),
        },
        {
            "passage_id": "cand_b4_later_school",
            "title": "Why One School Started Later",
            "anchor_lexile": 980,
            "target_band": "950L-1100L",
            "cefr_level": "B1",
            "genre": "opinion",
            "topic": "health",
            "body_text": (
                "A secondary school changed its timetable after teachers studied research about teenage sleep. Lessons "
                "began thirty minutes later, and clubs moved to the afternoon. Some parents worried that the new plan would "
                "make family mornings more difficult, but the school tested it for one term before making a final decision. "
                "Attendance improved slightly, and students reported feeling more awake in the first lesson. The head "
                "teacher said the change was not a perfect answer for every family, but it showed that school routines "
                "should be checked when students' needs change."
            ),
        },
    ]
    return [_candidate_from_template(template) for template in templates[: max(0, count)]]


def validate_candidate(candidate: dict[str, Any]) -> list[str]:
    """Return validation errors for a candidate record."""

    errors: list[str] = []
    for field in (
        "passage_id",
        "title",
        "body_text",
        "target_band",
        "anchor_lexile",
        "genre",
        "topic",
        "review_status",
        "items",
    ):
        if field not in candidate:
            errors.append(f"missing field: {field}")
    if errors:
        return errors
    if candidate["review_status"] != "candidate":
        errors.append("review_status must be candidate")
    if len(candidate["body_text"].split()) < 80:
        errors.append("body_text must contain at least 80 words")
    items = candidate["items"]
    if len(items) != 5:
        errors.append("candidate must include exactly 5 items")
    skills = {item.get("skill") for item in items}
    if skills != set(REQUIRED_SKILLS):
        errors.append("items must cover the required skills exactly once")
    for index, item in enumerate(items, start=1):
        item_id = item.get("item_id", f"item {index}")
        choices = item.get("choices", {})
        correct_choice = item.get("correct_choice")
        if set(choices) != {"A", "B", "C", "D"}:
            errors.append(f"{item_id}: choices must be A-D")
        if correct_choice not in choices:
            errors.append(f"{item_id}: correct_choice must be one of A-D")
        rationales = item.get("rationales", {})
        if correct_choice not in rationales or not rationales.get(correct_choice):
            errors.append(f"{item_id}: correct rationale is required")
    return errors


def write_review_files(candidates: list[dict[str, Any]], output_dir: Path) -> dict[str, Path]:
    """Write candidate review files and return their paths."""

    output_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = output_dir / "candidates.jsonl"
    csv_path = output_dir / "candidates.csv"
    with jsonl_path.open("w", encoding="utf-8") as jsonl_file:
        for candidate in candidates:
            jsonl_file.write(json.dumps(candidate, ensure_ascii=False, sort_keys=True) + "\n")
    with csv_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            lineterminator="\n",
            fieldnames=[
                "passage_id",
                "title",
                "anchor_lexile",
                "review_status",
                "target_band",
                "cefr_level",
                "genre",
                "topic",
                "word_count",
                "item_count",
            ],
        )
        writer.writeheader()
        for candidate in candidates:
            writer.writerow(
                {
                    "passage_id": candidate["passage_id"],
                    "title": candidate["title"],
                    "anchor_lexile": candidate["anchor_lexile"],
                    "review_status": candidate["review_status"],
                    "target_band": candidate["target_band"],
                    "cefr_level": candidate["cefr_level"],
                    "genre": candidate["genre"],
                    "topic": candidate["topic"],
                    "word_count": candidate["word_count"],
                    "item_count": len(candidate["items"]),
                }
            )
    return {"jsonl": jsonl_path, "csv": csv_path}


def _candidate_from_template(template: dict[str, Any]) -> dict[str, Any]:
    passage_id = template["passage_id"]
    anchor = int(template["anchor_lexile"])
    return {
        **template,
        "word_count": len(template["body_text"].split()),
        "review_status": "candidate",
        "reviewer": "",
        "review_notes": "",
        "items": [
            _item(
                passage_id=passage_id,
                order=1,
                skill="main_idea",
                question="What is the passage mainly about?",
                correct="B",
                choices={
                    "A": "A problem that cannot be solved",
                    "B": f"The main ideas in {template['title'].lower()}",
                    "C": "A story about buying expensive equipment",
                    "D": "A list of unrelated facts",
                },
                anchor=anchor,
            ),
            _item(
                passage_id=passage_id,
                order=2,
                skill="detail",
                question="Which detail is stated in the passage?",
                correct="A",
                choices={
                    "A": "People make a careful plan before acting",
                    "B": "The project happens only during winter",
                    "C": "Everyone disagrees with the final choice",
                    "D": "The passage says the plan failed completely",
                },
                anchor=anchor - 75,
            ),
            _item(
                passage_id=passage_id,
                order=3,
                skill="inference",
                question="What can the reader infer from the passage?",
                correct="C",
                choices={
                    "A": "The people ignored all advice",
                    "B": "The situation was impossible to improve",
                    "C": "Careful choices can make an activity more successful",
                    "D": "The writer thinks learning is unnecessary",
                },
                anchor=anchor + 75,
            ),
            _item(
                passage_id=passage_id,
                order=4,
                skill="vocabulary_context",
                question="In the passage, what does important mean?",
                correct="A",
                choices={
                    "A": "Having value or meaning",
                    "B": "Very small",
                    "C": "Quickly forgotten",
                    "D": "Impossible to see",
                },
                anchor=anchor,
            ),
            _item(
                passage_id=passage_id,
                order=5,
                skill="structure_author_purpose",
                question="Why does the writer include specific examples?",
                correct="D",
                choices={
                    "A": "To make the passage harder to follow",
                    "B": "To avoid explaining the topic",
                    "C": "To introduce an unrelated character",
                    "D": "To show how the main idea works in real life",
                },
                anchor=anchor,
            ),
        ],
    }


def _item(
    *,
    passage_id: str,
    order: int,
    skill: str,
    question: str,
    correct: str,
    choices: dict[str, str],
    anchor: int,
) -> dict[str, Any]:
    return {
        "item_id": f"{passage_id}_{skill}",
        "item_order": order,
        "skill": skill,
        "difficulty_label": "medium",
        "difficulty_offset": 0,
        "estimated_item_lexile": anchor,
        "question_text": question,
        "choices": choices,
        "correct_choice": correct,
        "rationales": {key: ("Supported by the passage." if key == correct else "This choice is not supported by the passage.") for key in choices},
    }
