"""Candidate reading-bank generation and validation for human review."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any


REQUIRED_SKILLS = (
    "main_idea",
    "detail",
    "inference",
    "vocabulary_context",
    "structure_author_purpose",
)
VALID_REVIEW_STATUSES = ("candidate", "reviewed_candidate")
SKILL_ALIASES = {
    "conclusion": "main_idea",
    "author_purpose": "structure_author_purpose",
    "structure": "structure_author_purpose",
}
LEVEL_DEFAULTS = {
    "A2": (650, "500L-650L", "A2"),
    "A2+": (750, "650L-800L", "A2+"),
    "B1": (850, "800L-950L", "B1"),
    "B1+": (980, "950L-1100L", "B1+"),
}


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


def validate_candidate(candidate: dict[str, Any], *, strict_skill_coverage: bool = True) -> list[str]:
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
    if candidate["review_status"] not in VALID_REVIEW_STATUSES:
        errors.append("review_status must be candidate or reviewed_candidate")
    if len(candidate["body_text"].split()) < 80:
        errors.append("body_text must contain at least 80 words")
    items = candidate["items"]
    if len(items) != 5:
        errors.append("candidate must include exactly 5 items")
    skills = {item.get("skill") for item in items}
    if strict_skill_coverage and skills != set(REQUIRED_SKILLS):
        errors.append("items must cover the required skills exactly once")
    if not strict_skill_coverage:
        unsupported = sorted(skill for skill in skills if skill not in set(REQUIRED_SKILLS))
        if unsupported:
            errors.append(f"unsupported skills: {', '.join(unsupported)}")
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


def candidates_from_vocab_quest_export(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize a Vocab Quest export into reviewed reading-bank candidates."""

    if payload.get("exportType") != "quests":
        raise ValueError("Vocab Quest exportType must be quests")
    sessions = payload.get("sessions")
    if not isinstance(sessions, list):
        raise ValueError("Vocab Quest payload must contain a sessions list")
    return [_candidate_from_vocab_quest_session(session) for session in sessions]


def promote_vocab_quest_candidates(
    candidates: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Promote reviewed Vocab Quest candidates into seed-compatible passages."""

    promoted: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for candidate in candidates:
        passage, reason = _promote_vocab_quest_candidate(candidate)
        if passage:
            promoted.append(passage)
        else:
            skipped.append({"passage_id": candidate.get("passage_id", ""), "reason": reason})
    return promoted, skipped


def write_review_files(candidates: list[dict[str, Any]], output_dir: Path, *, basename: str = "candidates") -> dict[str, Path]:
    """Write candidate review files and return their paths."""

    output_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = output_dir / f"{basename}.jsonl"
    csv_path = output_dir / f"{basename}.csv"
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
                "diagnostic_ready",
                "validation_flags",
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
                    "diagnostic_ready": candidate.get("diagnostic_ready", ""),
                    "validation_flags": ";".join(candidate.get("validation_flags", [])),
                }
            )
    return {"jsonl": jsonl_path, "csv": csv_path}


def _promote_vocab_quest_candidate(candidate: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
    if candidate.get("review_status") != "reviewed_candidate":
        return None, "not_reviewed_candidate"
    items = candidate.get("items", [])
    if len(items) != 5:
        return None, "item_count_not_5"
    invalid_reason = _invalid_promotion_item_reason(items)
    if invalid_reason:
        return None, invalid_reason

    first_by_skill: dict[str, dict[str, Any]] = {}
    for item in items:
        skill = item.get("skill")
        if skill in REQUIRED_SKILLS and skill not in first_by_skill:
            first_by_skill[skill] = item
    missing = [skill for skill in REQUIRED_SKILLS if skill not in first_by_skill]
    generated_missing_skill = ""
    if not missing:
        repaired_items = first_by_skill
    elif len(missing) == 1:
        missing_skill = missing[0]
        if missing_skill not in {"main_idea", "structure_author_purpose"}:
            return None, f"unsupported_missing_skill_{missing_skill}"
        generated_missing_skill = missing_skill
        repaired_items = {
            **first_by_skill,
            missing_skill: _generated_repair_item(candidate, missing_skill),
        }
    else:
        return None, "missing_skill_count_not_1"
    passage_id = str(candidate["passage_id"])
    suffix = passage_id.removeprefix("vq_")
    promoted_items = [
        _seed_item_from_candidate_item(
            passage_id=f"rp_vq_{suffix}",
            item=repaired_items[skill],
            skill=skill,
            order=order,
            anchor=int(candidate["anchor_lexile"]),
        )
        for order, skill in enumerate(REQUIRED_SKILLS, start=1)
    ]
    return (
        {
            "id": f"rp_vq_{suffix}",
            "passage_code": f"VQ_{suffix.upper()}",
            "title": candidate["title"],
            "body_text": candidate["body_text"],
            "band_label": "VocabQuest",
            "anchor_lexile": int(candidate["anchor_lexile"]),
            "cefr_level": candidate["cefr_level"],
            "genre": candidate["genre"],
            "word_count": int(candidate["word_count"]),
            "topic": candidate["topic"],
            "metadata": {
                "source": "vocab_quest_promoted",
                "source_candidate_id": passage_id,
                "source_session_id": candidate.get("source_session_id", ""),
                "generated_missing_skill": generated_missing_skill,
            },
            "items": promoted_items,
        },
        "",
    )


def _invalid_promotion_item_reason(items: list[dict[str, Any]]) -> str:
    for index, item in enumerate(items, start=1):
        choices = item.get("choices", {})
        correct_choice = item.get("correct_choice")
        if set(choices) != {"A", "B", "C", "D"}:
            return f"item_{index}_choices_not_a_d"
        if correct_choice not in choices:
            return f"item_{index}_correct_choice_invalid"
        rationales = item.get("rationales", {})
        if not rationales.get(correct_choice):
            return f"item_{index}_correct_rationale_missing"
    return ""


def _generated_repair_item(candidate: dict[str, Any], skill: str) -> dict[str, Any]:
    if skill == "main_idea":
        return {
            "item_id": f"{candidate['passage_id']}_generated_main_idea",
            "skill": "main_idea",
            "difficulty_label": "medium",
            "difficulty_offset": 0,
            "estimated_item_lexile": int(candidate["anchor_lexile"]),
            "question_text": "What is the passage mainly about?",
            "choices": {
                "A": f"The central situation in {candidate['title']}",
                "B": "A list of unrelated facts",
                "C": "A grammar lesson about one word",
                "D": "A completely different event",
            },
            "correct_choice": "A",
            "rationales": {
                "A": "This choice best summarizes the whole passage.",
                "B": "The details in the passage are connected, not unrelated.",
                "C": "The passage is a reading text, not a grammar lesson.",
                "D": "This choice does not match the passage.",
            },
        }
    return {
        "item_id": f"{candidate['passage_id']}_generated_structure_author_purpose",
        "skill": "structure_author_purpose",
        "difficulty_label": "medium",
        "difficulty_offset": 0,
        "estimated_item_lexile": int(candidate["anchor_lexile"]),
        "question_text": "Why does the writer include several specific details in the passage?",
        "choices": {
            "A": "To show how the main idea develops through events or examples",
            "B": "To list unrelated facts without a purpose",
            "C": "To explain a grammar rule",
            "D": "To introduce a different passage",
        },
        "correct_choice": "A",
        "rationales": {
            "A": "The details help connect the passage events and ideas.",
            "B": "The details support the passage rather than being unrelated.",
            "C": "The passage does not focus on a grammar rule.",
            "D": "The details belong to this passage.",
        },
    }


def _seed_item_from_candidate_item(
    *,
    passage_id: str,
    item: dict[str, Any],
    skill: str,
    order: int,
    anchor: int,
) -> dict[str, Any]:
    return {
        "id": f"ri_{passage_id.removeprefix('rp_')}_{skill}",
        "item_order": order,
        "skill": skill,
        "difficulty_label": item.get("difficulty_label", "medium"),
        "difficulty_offset": int(item.get("difficulty_offset", 0)),
        "estimated_item_lexile": int(item.get("estimated_item_lexile", anchor)),
        "question_text": item["question_text"],
        "choices": item["choices"],
        "correct_choice": item["correct_choice"],
        "rationales": item["rationales"],
    }


def _candidate_from_vocab_quest_session(session: dict[str, Any]) -> dict[str, Any]:
    source_id = str(session.get("id") or session.get("title") or "untitled")
    title = str(session.get("title") or "Untitled Reading Quest").strip()
    body_text = _normalize_whitespace(str(session.get("passage") or ""))
    level = str(session.get("targetLevel") or "B1").strip().upper()
    anchor, target_band, cefr_level = LEVEL_DEFAULTS.get(level, LEVEL_DEFAULTS["B1"])
    reading_type = _reading_type(session)
    passage_id = f"vq_{_stable_code(source_id)}"
    items, item_flags = _vocab_quest_items(
        passage_id=passage_id,
        questions=session.get("questions") or [],
        anchor=anchor,
    )
    candidate: dict[str, Any] = {
        "passage_id": passage_id,
        "title": title,
        "anchor_lexile": anchor,
        "target_band": target_band,
        "cefr_level": cefr_level,
        "genre": _genre_from_reading_type(reading_type, title),
        "topic": reading_type,
        "body_text": body_text,
        "word_count": len(body_text.split()),
        "review_status": "reviewed_candidate",
        "reviewer": "source_reviewed",
        "review_notes": "Imported from reviewed Vocab Quest export; diagnostic readiness is computed separately.",
        "source": "vocab_quest",
        "source_session_id": source_id,
        "source_title": title,
        "source_category": session.get("category", ""),
        "original_vocab": session.get("originalVocab") or [],
        "items": items,
    }
    candidate["validation_flags"] = _vocab_quest_validation_flags(candidate, item_flags)
    candidate["diagnostic_ready"] = not candidate["validation_flags"]
    return candidate


def _vocab_quest_items(
    *,
    passage_id: str,
    questions: list[dict[str, Any]],
    anchor: int,
) -> tuple[list[dict[str, Any]], list[str]]:
    items: list[dict[str, Any]] = []
    flags: list[str] = []
    for order, question in enumerate(questions, start=1):
        options = [str(option) for option in question.get("options", [])]
        choices = {letter: option for letter, option in zip(("A", "B", "C", "D"), options)}
        correct_choice = _correct_choice_from_answer(options, str(question.get("correctAnswer") or ""))
        if not correct_choice:
            flags.append(f"item_{order}_correct_answer_not_found")
        skill, skill_flag = _normalize_skill(question)
        if skill_flag:
            flags.append(f"item_{order}_{skill_flag}")
        item_id = _normalize_whitespace(str(question.get("id") or f"q{order}"))
        items.append(
            {
                "item_id": f"{passage_id}_{_stable_code(item_id)}",
                "item_order": order,
                "skill": skill,
                "difficulty_label": "medium",
                "difficulty_offset": 0,
                "estimated_item_lexile": anchor,
                "question_text": _normalize_whitespace(str(question.get("question") or "")),
                "choices": choices,
                "correct_choice": correct_choice,
                "rationales": {
                    letter: (
                        _normalize_whitespace(str(question.get("explanation") or "Supported by the passage."))
                        if letter == correct_choice
                        else "This choice is not the reviewed answer."
                    )
                    for letter in choices
                },
                "target_word": str(question.get("word") or "").strip(),
                "source_question_id": item_id,
                "source_question_type": str(question.get("type") or ""),
            }
        )
    return items, flags


def _vocab_quest_validation_flags(candidate: dict[str, Any], item_flags: list[str]) -> list[str]:
    flags = list(dict.fromkeys(item_flags))
    structural_errors = validate_candidate(candidate, strict_skill_coverage=False)
    flags.extend(f"structural_{_flag(error)}" for error in structural_errors)
    skills = [item.get("skill") for item in candidate.get("items", [])]
    if len(skills) != 5:
        flags.append("diagnostic_item_count_not_5")
    if set(skills) != set(REQUIRED_SKILLS):
        flags.append("diagnostic_skill_coverage_incomplete")
    return list(dict.fromkeys(flags))


def _reading_type(session: dict[str, Any]) -> str:
    explicit = str(session.get("readingType") or "").strip()
    if explicit:
        return explicit
    title = str(session.get("title") or "")
    match = re.search(r"\[(?P<kind>[^\]]+)\]", title)
    return match.group("kind").strip().lower() if match else "reading"


def _genre_from_reading_type(reading_type: str, title: str) -> str:
    normalized = reading_type.strip().lower()
    if normalized == "informational":
        return "informational"
    if normalized == "literature" or "[literature]" in title.lower():
        return "literature"
    if normalized.startswith("pet_part") or normalized == "vocabulary" or "[vocabulary]" in title.lower():
        return "vocabulary"
    return normalized or "reading"


def _normalize_skill(question: dict[str, Any]) -> tuple[str, str | None]:
    raw_skill = str(question.get("skill") or "").strip()
    if raw_skill:
        skill = SKILL_ALIASES.get(raw_skill, raw_skill)
        if skill in REQUIRED_SKILLS:
            return skill, None if skill == raw_skill else f"skill_mapped_from_{_flag(raw_skill)}"
        return "detail", f"skill_mapped_from_unsupported_{_flag(raw_skill)}"
    question_text = str(question.get("question") or "").lower()
    if "main" in question_text or "overall" in question_text or "primary goal" in question_text:
        return "main_idea", "skill_inferred"
    if "infer" in question_text or "imply" in question_text or "suggest" in question_text or "feel" in question_text:
        return "inference", "skill_inferred"
    if "what does" in question_text or "meaning" in question_text or "mean in" in question_text:
        return "vocabulary_context", "skill_inferred"
    if "author" in question_text or "purpose" in question_text:
        return "structure_author_purpose", "skill_inferred"
    return "detail", "skill_inferred"


def _correct_choice_from_answer(options: list[str], answer: str) -> str:
    normalized_answer = _normalize_answer(answer)
    for index, option in enumerate(options[:4]):
        if _normalize_answer(option) == normalized_answer:
            return ("A", "B", "C", "D")[index]
    return ""


def _normalize_answer(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold().rstrip(".")


def _stable_code(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "", value)
    return (cleaned or "untitled").lower()[:12]


def _flag(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


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
