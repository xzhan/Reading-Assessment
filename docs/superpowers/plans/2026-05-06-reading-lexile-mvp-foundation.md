# Reading Lexile MVP Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first working backend and static mockup for a 20-30 minute Grade 6-8 Lexile-like reading assessment.

**Architecture:** Add a focused `backend/pet_reading_api` package beside the existing writing package. Keep online assessment deterministic: seed passages/items, select the next passage at passage boundaries, store responses, calculate a range report, and expose `/api/v1/reading` routes through the existing standard-library HTTP server. Create a static HTML mockup in `docs/mockups` that shows the student flow and final report without requiring a frontend build.

**Tech Stack:** Python standard library, SQLite, `unittest`, existing `ThreadingHTTPServer`, static HTML/CSS/JS for mockup.

---

## File Structure

Create:

- `backend/pet_reading_api/__init__.py`: package marker and public module boundary.
- `backend/pet_reading_api/seed_data.py`: small approved demo passage bank used for tests and local runs.
- `backend/pet_reading_api/estimator.py`: deterministic Lexile-like range, practice range, confidence, validity flags, and domain scores.
- `backend/pet_reading_api/adaptive.py`: starting anchor and next-anchor decision logic.
- `backend/pet_reading_api/storage.py`: SQLite schema and persistence methods for reading content, assessments, responses, and estimates.
- `backend/pet_reading_api/service.py`: orchestration for create assessment, get next passage, submit responses, complete, and report.
- `tests/test_reading_estimator.py`: estimator unit coverage.
- `tests/test_reading_adaptive.py`: adaptive engine unit coverage.
- `tests/test_reading_api.py`: HTTP smoke flow for the reading assessment.
- `docs/mockups/reading-lexile-assessment-flow.html`: clickable static mockup for start, assessment, and report states.

Modify:

- `backend/pet_writing_api/server.py`: instantiate `ReadingService` and route `/api/v1/reading/*` paths before writing routes.
- `README.md`: add reading assessment MVP run and test notes.

Do not modify:

- existing writing scoring behavior
- existing writing database tables except where the shared server needs to initialize both services

---

## Task 1: Estimator

**Files:**

- Create: `backend/pet_reading_api/__init__.py`
- Create: `backend/pet_reading_api/estimator.py`
- Test: `tests/test_reading_estimator.py`

- [ ] **Step 1: Create the failing estimator tests**

Create `tests/test_reading_estimator.py`:

```python
"""Tests for Lexile-like reading estimate calculation."""

from __future__ import annotations

import unittest

from backend.pet_reading_api.estimator import estimate_reading_level


class ReadingEstimatorTest(unittest.TestCase):
    def test_estimates_stable_mid_range_reader(self) -> None:
        responses = [
            {"estimated_item_lexile": 675, "skill": "detail", "correct": True, "time_seconds": 35},
            {"estimated_item_lexile": 700, "skill": "main_idea", "correct": True, "time_seconds": 42},
            {"estimated_item_lexile": 775, "skill": "inference", "correct": True, "time_seconds": 55},
            {"estimated_item_lexile": 825, "skill": "vocabulary_context", "correct": True, "time_seconds": 47},
            {"estimated_item_lexile": 850, "skill": "structure_author_purpose", "correct": False, "time_seconds": 60},
            {"estimated_item_lexile": 925, "skill": "inference", "correct": False, "time_seconds": 70},
            {"estimated_item_lexile": 950, "skill": "vocabulary_context", "correct": False, "time_seconds": 65},
            {"estimated_item_lexile": 975, "skill": "detail", "correct": False, "time_seconds": 52},
        ]

        estimate = estimate_reading_level(
            responses=responses,
            passages_completed=4,
            duration_seconds=1420,
        )

        self.assertEqual(estimate["estimated_lower_lexile"], 725)
        self.assertEqual(estimate["estimated_upper_lexile"], 950)
        self.assertEqual(estimate["practice_lower_lexile"], 655)
        self.assertEqual(estimate["practice_upper_lexile"], 890)
        self.assertEqual(estimate["confidence_label"], "Medium")
        self.assertEqual(estimate["cefr_estimate"], "A2+")
        self.assertIn("detail", estimate["domain_scores"])
        self.assertGreaterEqual(estimate["domain_scores"]["detail"], 50)

    def test_flags_fast_low_effort_pattern(self) -> None:
        responses = [
            {"estimated_item_lexile": 650, "skill": "detail", "correct": False, "time_seconds": 3},
            {"estimated_item_lexile": 675, "skill": "main_idea", "correct": False, "time_seconds": 4},
            {"estimated_item_lexile": 700, "skill": "inference", "correct": True, "time_seconds": 3},
            {"estimated_item_lexile": 725, "skill": "vocabulary_context", "correct": False, "time_seconds": 4},
        ]

        estimate = estimate_reading_level(
            responses=responses,
            passages_completed=2,
            duration_seconds=480,
        )

        self.assertEqual(estimate["confidence_label"], "Low")
        self.assertIn("TOO_FEW_PASSAGES", estimate["validity_flags"])
        self.assertIn("TOO_FAST_OVERALL", estimate["validity_flags"])
        self.assertIn("MANY_RUSHED_ITEMS", estimate["validity_flags"])

    def test_marks_above_target_range(self) -> None:
        responses = [
            {"estimated_item_lexile": 950, "skill": "detail", "correct": True, "time_seconds": 45},
            {"estimated_item_lexile": 1000, "skill": "main_idea", "correct": True, "time_seconds": 48},
            {"estimated_item_lexile": 1025, "skill": "inference", "correct": True, "time_seconds": 60},
            {"estimated_item_lexile": 1075, "skill": "vocabulary_context", "correct": True, "time_seconds": 53},
            {"estimated_item_lexile": 1100, "skill": "structure_author_purpose", "correct": True, "time_seconds": 58},
        ]

        estimate = estimate_reading_level(
            responses=responses,
            passages_completed=4,
            duration_seconds=1500,
        )

        self.assertEqual(estimate["range_status"], "above_target_range")
        self.assertIn("ABOVE_TARGET_RANGE", estimate["validity_flags"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the estimator tests and verify they fail**

Run:

```bash
python3 -m unittest tests/test_reading_estimator.py
```

Expected: fail with `ModuleNotFoundError: No module named 'backend.pet_reading_api'`.

- [ ] **Step 3: Add the reading package marker**

Create `backend/pet_reading_api/__init__.py`:

```python
"""PET Reading assessment backend package."""
```

- [ ] **Step 4: Implement `estimator.py`**

Create `backend/pet_reading_api/estimator.py`:

```python
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


def estimate_reading_level(
    *,
    responses: list[dict[str, Any]],
    passages_completed: int,
    duration_seconds: int,
) -> dict[str, Any]:
    flags = _validity_flags(responses, passages_completed, duration_seconds)
    buckets = _bucket_accuracy(responses)
    lower, upper, status = _estimate_range(buckets)
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
    if passages_completed < 3:
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


def _estimate_range(buckets: list[dict[str, Any]]) -> tuple[int, int, str]:
    if not buckets:
        return 500, 650, "below_target_range"

    readable = [
        bucket
        for bucket in buckets
        if bucket["status"] in {"mastered", "readable"}
    ]
    difficult = [
        bucket
        for bucket in buckets
        if bucket["status"] in {"challenge", "too_difficult"}
    ]

    if readable and readable[-1]["bucket_start"] >= 1000 and not difficult:
        return 1000, 1100, "above_target_range"
    if difficult and difficult[0]["bucket_start"] <= 500 and not readable:
        return 500, 650, "below_target_range"

    stable_level = readable[-1]["bucket_start"] if readable else buckets[0]["bucket_start"]
    challenge_level = difficult[0]["bucket_start"] if difficult else min(1100, stable_level + 200)
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
    if passages_completed >= 4 and len(buckets) >= 3:
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
```

- [ ] **Step 5: Run estimator tests and commit**

Run:

```bash
python3 -m unittest tests/test_reading_estimator.py
```

Expected: `OK`.

Commit:

```bash
git add backend/pet_reading_api/__init__.py backend/pet_reading_api/estimator.py tests/test_reading_estimator.py
git commit -m "feat: add reading lexile estimator"
```

---

## Task 2: Adaptive Engine and Seed Content

**Files:**

- Create: `backend/pet_reading_api/adaptive.py`
- Create: `backend/pet_reading_api/seed_data.py`
- Test: `tests/test_reading_adaptive.py`

- [ ] **Step 1: Write adaptive tests**

Create `tests/test_reading_adaptive.py`:

```python
"""Tests for passage-level adaptive reading decisions."""

from __future__ import annotations

import unittest

from backend.pet_reading_api.adaptive import next_anchor_lexile, starting_anchor_for_grade
from backend.pet_reading_api.seed_data import READING_PASSAGES


class ReadingAdaptiveTest(unittest.TestCase):
    def test_starting_anchor_uses_grade(self) -> None:
        self.assertEqual(starting_anchor_for_grade(6), 700)
        self.assertEqual(starting_anchor_for_grade(7), 800)
        self.assertEqual(starting_anchor_for_grade(8), 900)
        self.assertEqual(starting_anchor_for_grade(None), 800)

    def test_next_anchor_moves_by_accuracy(self) -> None:
        self.assertEqual(next_anchor_lexile(current_anchor=800, accuracy=1.0), 925)
        self.assertEqual(next_anchor_lexile(current_anchor=800, accuracy=0.8), 850)
        self.assertEqual(next_anchor_lexile(current_anchor=800, accuracy=0.6), 725)
        self.assertEqual(next_anchor_lexile(current_anchor=800, accuracy=0.2), 650)

    def test_next_anchor_clamps_to_mvp_range(self) -> None:
        self.assertEqual(next_anchor_lexile(current_anchor=1050, accuracy=1.0), 1100)
        self.assertEqual(next_anchor_lexile(current_anchor=525, accuracy=0.2), 500)

    def test_seed_data_has_required_skills_per_passage(self) -> None:
        required = {
            "main_idea",
            "detail",
            "inference",
            "vocabulary_context",
            "structure_author_purpose",
        }
        for passage in READING_PASSAGES:
            skills = {item["skill"] for item in passage["items"]}
            self.assertEqual(skills, required)
            self.assertEqual(len(passage["items"]), 5)
```

- [ ] **Step 2: Run adaptive tests and verify they fail**

Run:

```bash
python3 -m unittest tests/test_reading_adaptive.py
```

Expected: fail with `ModuleNotFoundError` for `backend.pet_reading_api.adaptive`.

- [ ] **Step 3: Implement `adaptive.py`**

Create `backend/pet_reading_api/adaptive.py`:

```python
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
```

- [ ] **Step 4: Add seed data**

Create `backend/pet_reading_api/seed_data.py` with four demo passages, one per MVP band:

```python
"""Seed reading passages for local tests and the MVP demo."""

from __future__ import annotations


READING_PASSAGES = [
    {
        "id": "rp_b1_garden_notice",
        "passage_code": "B1_GARDEN_NOTICE",
        "title": "A New Garden at School",
        "body_text": (
            "Our school has a small new garden behind the library. Last month, the science teacher asked students "
            "to help plant vegetables and flowers there. At first, only ten students joined the garden club, but now "
            "more than thirty students come every Friday afternoon. Some students water the plants, some clean the paths, "
            "and others write short notes about how the plants change. The club will sell some vegetables at the school fair "
            "next month. The money will help buy more seeds and simple tools. Many students say the garden makes the school "
            "feel quieter and friendlier."
        ),
        "band_label": "Band 1",
        "anchor_lexile": 600,
        "cefr_level": "A2-",
        "genre": "functional",
        "word_count": 130,
        "topic": "school garden",
        "items": [
            {
                "id": "ri_b1_garden_main",
                "item_order": 1,
                "skill": "main_idea",
                "difficulty_label": "medium",
                "difficulty_offset": 0,
                "estimated_item_lexile": 600,
                "question_text": "What is the passage mainly about?",
                "choices": {"A": "A teacher who leaves school", "B": "A new school club and its garden", "C": "A library that sells books", "D": "A fair for parents only"},
                "correct_choice": "B",
                "rationales": {"A": "No teacher leaves school.", "B": "The passage explains the garden club and its work.", "C": "The library is only a location clue.", "D": "The fair is a future event, not the main idea."},
            },
            {
                "id": "ri_b1_garden_detail",
                "item_order": 2,
                "skill": "detail",
                "difficulty_label": "easy",
                "difficulty_offset": -75,
                "estimated_item_lexile": 525,
                "question_text": "When do students come to the garden club?",
                "choices": {"A": "Every Friday afternoon", "B": "Every Monday morning", "C": "Only during summer", "D": "Before the library opens"},
                "correct_choice": "A",
                "rationales": {"A": "The passage states they come every Friday afternoon.", "B": "Monday is not mentioned.", "C": "Summer is not mentioned.", "D": "The library is not part of the schedule."},
            },
            {
                "id": "ri_b1_garden_inference",
                "item_order": 3,
                "skill": "inference",
                "difficulty_label": "hard",
                "difficulty_offset": 75,
                "estimated_item_lexile": 675,
                "question_text": "Why will the club sell vegetables at the fair?",
                "choices": {"A": "To pay for a school trip", "B": "To buy more seeds and tools", "C": "To close the garden", "D": "To help the library move"},
                "correct_choice": "B",
                "rationales": {"A": "No trip is mentioned.", "B": "The passage says the money will buy seeds and tools.", "C": "The garden is growing, not closing.", "D": "The library does not move."},
            },
            {
                "id": "ri_b1_garden_vocab",
                "item_order": 4,
                "skill": "vocabulary_context",
                "difficulty_label": "medium",
                "difficulty_offset": 0,
                "estimated_item_lexile": 600,
                "question_text": "In the passage, what does tools mean?",
                "choices": {"A": "Things used to do a job", "B": "Stories about plants", "C": "Places to study", "D": "People in a club"},
                "correct_choice": "A",
                "rationales": {"A": "Seeds and garden work show tools are useful objects.", "B": "Stories do not fit the context.", "C": "Places do not fit the sentence.", "D": "People are students, not tools."},
            },
            {
                "id": "ri_b1_garden_structure",
                "item_order": 5,
                "skill": "structure_author_purpose",
                "difficulty_label": "medium",
                "difficulty_offset": 0,
                "estimated_item_lexile": 600,
                "question_text": "Why does the writer include different jobs students do?",
                "choices": {"A": "To show how the club works", "B": "To compare two schools", "C": "To explain a library rule", "D": "To describe a difficult exam"},
                "correct_choice": "A",
                "rationales": {"A": "The jobs explain club activities.", "B": "Only one school is discussed.", "C": "No library rule appears.", "D": "No exam is described."},
            },
        ],
    },
    {
        "id": "rp_b2_lost_camera",
        "passage_code": "B2_LOST_CAMERA",
        "title": "The Lost Camera",
        "body_text": (
            "Mina borrowed her uncle's camera for a class project about daily life in the city. She took photos of a busy market, "
            "a quiet tea shop, and people waiting for buses in the rain. When she returned to school, she could not find the camera "
            "in her bag. Mina felt terrible because the camera was expensive and the photos were important for her project. She went "
            "back to the market and asked three shopkeepers for help. One fruit seller remembered seeing a small black camera near his stall. "
            "He had given it to the market office. Mina was relieved. She learned to check her bag carefully before leaving a place."
        ),
        "band_label": "Band 2",
        "anchor_lexile": 750,
        "cefr_level": "A2",
        "genre": "narrative",
        "word_count": 125,
        "topic": "class project",
        "items": [
            {"id": "ri_b2_camera_main", "item_order": 1, "skill": "main_idea", "difficulty_label": "medium", "difficulty_offset": 0, "estimated_item_lexile": 750, "question_text": "What is the passage mainly about?", "choices": {"A": "A student solving a problem after losing a camera", "B": "A shopkeeper learning to take photos", "C": "A teacher buying a new camera", "D": "A market closing because of rain"}, "correct_choice": "A", "rationales": {"A": "Mina loses and then finds the camera.", "B": "The shopkeeper helps but does not learn photography.", "C": "No teacher buys a camera.", "D": "The market stays open."}},
            {"id": "ri_b2_camera_detail", "item_order": 2, "skill": "detail", "difficulty_label": "easy", "difficulty_offset": -75, "estimated_item_lexile": 675, "question_text": "Where did the fruit seller send the camera?", "choices": {"A": "To Mina's uncle", "B": "To the market office", "C": "To the school library", "D": "To a bus driver"}, "correct_choice": "B", "rationales": {"A": "Her uncle is not at the market.", "B": "The passage states this directly.", "C": "The library is not mentioned.", "D": "Bus drivers are only in Mina's photos."}},
            {"id": "ri_b2_camera_inference", "item_order": 3, "skill": "inference", "difficulty_label": "hard", "difficulty_offset": 75, "estimated_item_lexile": 825, "question_text": "Why did Mina feel terrible?", "choices": {"A": "She disliked her class project.", "B": "She thought she had lost something valuable.", "C": "She missed the bus home.", "D": "She forgot to take any photos."}, "correct_choice": "B", "rationales": {"A": "The project is important to her.", "B": "The camera was expensive and the photos mattered.", "C": "She photographed people waiting for buses, but did not miss one.", "D": "She had taken several photos."}},
            {"id": "ri_b2_camera_vocab", "item_order": 4, "skill": "vocabulary_context", "difficulty_label": "medium", "difficulty_offset": 0, "estimated_item_lexile": 750, "question_text": "What does relieved mean in the passage?", "choices": {"A": "No longer worried", "B": "Very confused", "C": "Still angry", "D": "Too tired to walk"}, "correct_choice": "A", "rationales": {"A": "She finds the camera, so her worry ends.", "B": "She understands what happened.", "C": "She is not described as angry.", "D": "Tiredness is not the point."}},
            {"id": "ri_b2_camera_structure", "item_order": 5, "skill": "structure_author_purpose", "difficulty_label": "medium", "difficulty_offset": 0, "estimated_item_lexile": 750, "question_text": "Why does the writer list Mina's photos at the beginning?", "choices": {"A": "To show why the camera mattered", "B": "To explain how cameras are made", "C": "To describe every shop in the market", "D": "To prove rain is dangerous"}, "correct_choice": "A", "rationales": {"A": "The photos are for her class project.", "B": "No camera-making process appears.", "C": "Only some places are named.", "D": "Rain is background detail."}},
        ],
    },
    {
        "id": "rp_b3_robot_club",
        "passage_code": "B3_ROBOT_CLUB",
        "title": "A Robot That Carries Books",
        "body_text": (
            "The students in Class Seven wanted to build a robot for the school technology fair, but they did not want to make another toy car. "
            "Their teacher suggested watching younger students in the library. After two afternoons, the class noticed that many children carried "
            "heavy books from one table to another while looking for information. The team designed a small robot with a flat top and slow wheels. "
            "It followed a black line on the floor and stopped when someone pressed a red button. The robot was not fast, but that was part of the plan. "
            "In a crowded library, a quick robot would be unsafe. At the fair, the judges praised the team because they had solved a real school problem."
        ),
        "band_label": "Band 3",
        "anchor_lexile": 875,
        "cefr_level": "A2+/B1-",
        "genre": "informational",
        "word_count": 130,
        "topic": "school technology",
        "items": [
            {"id": "ri_b3_robot_main", "item_order": 1, "skill": "main_idea", "difficulty_label": "medium", "difficulty_offset": 0, "estimated_item_lexile": 875, "question_text": "What is the passage mainly about?", "choices": {"A": "Students designing a useful robot for school", "B": "A library replacing all its books", "C": "Judges teaching students to drive cars", "D": "A toy car race at a technology fair"}, "correct_choice": "A", "rationales": {"A": "The team builds a book-carrying robot.", "B": "The library keeps its books.", "C": "Judges evaluate the project.", "D": "They avoid making another toy car."}},
            {"id": "ri_b3_robot_detail", "item_order": 2, "skill": "detail", "difficulty_label": "easy", "difficulty_offset": -75, "estimated_item_lexile": 800, "question_text": "What did the robot follow on the floor?", "choices": {"A": "A black line", "B": "A blue light", "C": "A library card", "D": "A teacher's voice"}, "correct_choice": "A", "rationales": {"A": "The passage states it followed a black line.", "B": "No blue light is mentioned.", "C": "Cards are not part of the robot.", "D": "Voice control is not described."}},
            {"id": "ri_b3_robot_inference", "item_order": 3, "skill": "inference", "difficulty_label": "hard", "difficulty_offset": 75, "estimated_item_lexile": 950, "question_text": "Why was being slow a good feature for the robot?", "choices": {"A": "It made the robot cheaper to paint.", "B": "It made the robot safer in a busy place.", "C": "It helped the robot win races.", "D": "It allowed the robot to read books."}, "correct_choice": "B", "rationales": {"A": "Painting is not discussed.", "B": "A quick robot would be unsafe in a crowded library.", "C": "The robot is not for racing.", "D": "It carries books but does not read."}},
            {"id": "ri_b3_robot_vocab", "item_order": 4, "skill": "vocabulary_context", "difficulty_label": "medium", "difficulty_offset": 0, "estimated_item_lexile": 875, "question_text": "What does praised mean in the passage?", "choices": {"A": "Spoke well of", "B": "Disagreed with", "C": "Copied from", "D": "Waited for"}, "correct_choice": "A", "rationales": {"A": "The judges liked the useful solution.", "B": "They did not disagree.", "C": "No copying is described.", "D": "Waiting is not the meaning."}},
            {"id": "ri_b3_robot_structure", "item_order": 5, "skill": "structure_author_purpose", "difficulty_label": "medium", "difficulty_offset": 0, "estimated_item_lexile": 875, "question_text": "Why does the writer describe the students watching younger children?", "choices": {"A": "To show how they found a real problem", "B": "To explain why libraries are noisy", "C": "To introduce a new reading contest", "D": "To show that the fair was cancelled"}, "correct_choice": "A", "rationales": {"A": "Observation led to the robot idea.", "B": "Noise is not the issue.", "C": "There is no reading contest.", "D": "The fair takes place."}},
        ],
    },
    {
        "id": "rp_b4_sleep_article",
        "passage_code": "B4_SLEEP_ARTICLE",
        "title": "Why One School Started Later",
        "body_text": (
            "For many years, Green Hill School began lessons at 7:30 each morning. Teachers believed the early start gave students more time for clubs "
            "and homework in the afternoon. However, a survey showed that many older students were sleeping less than seven hours on school nights. "
            "Some arrived late, and others said they could not concentrate during the first two lessons. The school tested a later start time for one term. "
            "Lessons began at 8:20, while clubs moved slightly later in the day. The change did not solve every problem, but attendance improved and fewer "
            "students reported feeling sleepy before lunch. The head teacher said the result was not a simple victory for sleeping longer. It showed that "
            "school schedules should be checked when students' habits and health change."
        ),
        "band_label": "Band 4",
        "anchor_lexile": 1025,
        "cefr_level": "B1",
        "genre": "opinion",
        "word_count": 139,
        "topic": "school schedule",
        "items": [
            {"id": "ri_b4_sleep_main", "item_order": 1, "skill": "main_idea", "difficulty_label": "medium", "difficulty_offset": 0, "estimated_item_lexile": 1025, "question_text": "What is the main idea of the article?", "choices": {"A": "A school tested a later start time after noticing student tiredness", "B": "Students at one school stopped doing homework", "C": "A head teacher cancelled all afternoon clubs", "D": "Teachers wanted every lesson to be shorter"}, "correct_choice": "A", "rationales": {"A": "The article explains the reason and result of the later start.", "B": "Homework is not stopped.", "C": "Clubs moved later, not cancelled.", "D": "Lesson length is not discussed."}},
            {"id": "ri_b4_sleep_detail", "item_order": 2, "skill": "detail", "difficulty_label": "easy", "difficulty_offset": -75, "estimated_item_lexile": 950, "question_text": "What problem did the survey find?", "choices": {"A": "Many older students slept less than seven hours", "B": "Most students disliked all clubs", "C": "Teachers arrived after lunch", "D": "The school had no homework"}, "correct_choice": "A", "rationales": {"A": "The survey showed this directly.", "B": "Club dislike is not stated.", "C": "Teacher arrival is not mentioned.", "D": "Homework still exists."}},
            {"id": "ri_b4_sleep_inference", "item_order": 3, "skill": "inference", "difficulty_label": "hard", "difficulty_offset": 75, "estimated_item_lexile": 1100, "question_text": "What does the head teacher probably believe?", "choices": {"A": "Schedules should respond to evidence about students", "B": "Students should choose every lesson time", "C": "Clubs are more important than health", "D": "Starting earlier always improves learning"}, "correct_choice": "A", "rationales": {"A": "The final sentence says schedules should be checked as habits and health change.", "B": "Students do not choose every time.", "C": "Health is central to the decision.", "D": "The school moved away from an early start."}},
            {"id": "ri_b4_sleep_vocab", "item_order": 4, "skill": "vocabulary_context", "difficulty_label": "medium", "difficulty_offset": 0, "estimated_item_lexile": 1025, "question_text": "In the article, what does concentrate mean?", "choices": {"A": "Pay attention", "B": "Leave quickly", "C": "Feel hungry", "D": "Write more slowly"}, "correct_choice": "A", "rationales": {"A": "Sleepy students struggled during lessons.", "B": "Leaving is not implied.", "C": "Hunger is not discussed.", "D": "Writing speed is not the issue."}},
            {"id": "ri_b4_sleep_structure", "item_order": 5, "skill": "structure_author_purpose", "difficulty_label": "medium", "difficulty_offset": 0, "estimated_item_lexile": 1025, "question_text": "Why does the writer mention both benefits and limits of the change?", "choices": {"A": "To give a balanced explanation", "B": "To make the school sound careless", "C": "To show that surveys are useless", "D": "To argue clubs should disappear"}, "correct_choice": "A", "rationales": {"A": "The article says the change helped but did not solve everything.", "B": "The school is shown as testing evidence.", "C": "The survey helps identify the issue.", "D": "Clubs are moved, not removed."}},
        ],
    },
]
```

- [ ] **Step 5: Run adaptive tests and commit**

Run:

```bash
python3 -m unittest tests/test_reading_adaptive.py
```

Expected: `OK`.

Commit:

```bash
git add backend/pet_reading_api/adaptive.py backend/pet_reading_api/seed_data.py tests/test_reading_adaptive.py
git commit -m "feat: add reading adaptive seed data"
```

---

## Task 3: Reading Storage and Service

**Files:**

- Create: `backend/pet_reading_api/storage.py`
- Create: `backend/pet_reading_api/service.py`
- Test: `tests/test_reading_api.py`

- [ ] **Step 1: Write HTTP flow test for reading assessment**

Create `tests/test_reading_api.py`:

```python
"""Smoke tests for the reading Lexile-like assessment API."""

from __future__ import annotations

import json
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path

from backend.pet_writing_api.server import create_server


class ReadingApiFlowTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "test.db")
        self.server = create_server("127.0.0.1", 0, self.db_path)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp_dir.cleanup()

    def request(self, method: str, path: str, payload: dict | None = None) -> tuple[int, dict]:
        data = None
        headers = {"Content-Type": "application/json"}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url=f"{self.base_url}{path}",
            method=method,
            data=data,
            headers=headers,
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))

    def test_full_reading_flow(self) -> None:
        status, created = self.request(
            "POST",
            "/api/v1/reading/assessments",
            {"student_id": "stu_reader", "grade_level": 7},
        )
        self.assertEqual(status, 201)
        assessment_id = created["assessment_id"]
        self.assertEqual(created["current_anchor_lexile"], 800)

        for _ in range(3):
            status, next_payload = self.request("GET", f"/api/v1/reading/assessments/{assessment_id}/next")
            self.assertEqual(status, 200)
            self.assertIn("passage", next_payload)
            self.assertEqual(len(next_payload["items"]), 5)
            self.assertNotIn("correct_choice", next_payload["items"][0])

            responses = [
                {
                    "item_id": item["item_id"],
                    "selected_choice": "A",
                    "time_spent_sec": 30,
                }
                for item in next_payload["items"]
            ]
            status, result = self.request(
                "POST",
                f"/api/v1/reading/assessments/{assessment_id}/responses",
                {
                    "passage_id": next_payload["passage"]["passage_id"],
                    "time_spent_sec": 360,
                    "responses": responses,
                },
            )
            self.assertEqual(status, 200)
            self.assertIn(result["status"], {"continue", "ready_to_complete"})
            self.assertGreaterEqual(result["passages_completed"], 1)

        status, completed = self.request("POST", f"/api/v1/reading/assessments/{assessment_id}/complete")
        self.assertEqual(status, 200)
        self.assertIn("estimated_range", completed)
        self.assertIn("practice_range", completed)
        self.assertIn("domain_scores", completed)

        status, report = self.request("GET", f"/api/v1/reading/assessments/{assessment_id}/report")
        self.assertEqual(status, 200)
        self.assertEqual(report["assessment_id"], assessment_id)
        self.assertIn("summary", report)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run reading API test and verify it fails**

Run:

```bash
python3 -m unittest tests/test_reading_api.py
```

Expected: fail with `HTTP Error 404: Not Found` for `/api/v1/reading/assessments`.

- [ ] **Step 3: Implement `storage.py`**

Create `backend/pet_reading_api/storage.py`:

```python
"""SQLite persistence for PET Reading assessment."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .seed_data import READING_PASSAGES


SCHEMA_SQL = """
create table if not exists reading_passages (
  id text primary key,
  passage_code text not null unique,
  title text not null,
  body_text text not null,
  band_label text not null,
  anchor_lexile integer not null,
  cefr_level text not null,
  genre text not null,
  word_count integer not null,
  topic text not null,
  metadata_json text not null,
  active integer not null default 1,
  created_at text not null,
  updated_at text not null
);

create table if not exists reading_items (
  id text primary key,
  passage_id text not null,
  item_order integer not null,
  skill text not null,
  difficulty_label text not null,
  difficulty_offset integer not null,
  estimated_item_lexile integer not null,
  question_text text not null,
  choices_json text not null,
  correct_choice text not null,
  rationales_json text not null,
  active integer not null default 1,
  created_at text not null,
  updated_at text not null
);

create table if not exists reading_assessments (
  id text primary key,
  student_id text not null,
  grade_level integer,
  status text not null,
  target_range text not null,
  started_at text not null,
  completed_at text,
  duration_sec integer not null default 0,
  current_anchor_lexile integer not null,
  passages_completed integer not null default 0,
  created_at text not null,
  updated_at text not null
);

create table if not exists reading_assessment_passages (
  id text primary key,
  assessment_id text not null,
  passage_id text not null,
  sequence_number integer not null,
  anchor_lexile integer not null,
  started_at text not null,
  completed_at text,
  time_spent_sec integer not null default 0,
  accuracy real,
  created_at text not null,
  updated_at text not null,
  unique (assessment_id, passage_id)
);

create table if not exists reading_responses (
  id text primary key,
  assessment_id text not null,
  passage_id text not null,
  item_id text not null,
  selected_choice text not null,
  is_correct integer not null,
  time_spent_sec integer not null default 0,
  created_at text not null
);

create table if not exists reading_estimates (
  id text primary key,
  assessment_id text not null unique,
  estimated_lower_lexile integer not null,
  estimated_upper_lexile integer not null,
  practice_lower_lexile integer not null,
  practice_upper_lexile integer not null,
  cefr_estimate text not null,
  confidence_label text not null,
  validity_flags_json text not null,
  domain_scores_json text not null,
  report_payload_json text not null,
  created_at text not null
);

create index if not exists idx_reading_passages_anchor
  on reading_passages (anchor_lexile, active);
create index if not exists idx_reading_items_passage_order
  on reading_items (passage_id, item_order);
create index if not exists idx_reading_responses_assessment
  on reading_responses (assessment_id);
"""


class ReadingStorage:
    def __init__(self, db_path: str):
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize(self, now: str) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA_SQL)
            for passage in READING_PASSAGES:
                conn.execute(
                    """
                    insert or ignore into reading_passages (
                      id, passage_code, title, body_text, band_label, anchor_lexile,
                      cefr_level, genre, word_count, topic, metadata_json, active,
                      created_at, updated_at
                    ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        passage["id"],
                        passage["passage_code"],
                        passage["title"],
                        passage["body_text"],
                        passage["band_label"],
                        passage["anchor_lexile"],
                        passage["cefr_level"],
                        passage["genre"],
                        passage["word_count"],
                        passage["topic"],
                        self.dumps({"source": "seed"}),
                        1,
                        now,
                        now,
                    ),
                )
                for item in passage["items"]:
                    conn.execute(
                        """
                        insert or ignore into reading_items (
                          id, passage_id, item_order, skill, difficulty_label,
                          difficulty_offset, estimated_item_lexile, question_text,
                          choices_json, correct_choice, rationales_json, active,
                          created_at, updated_at
                        ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            item["id"],
                            passage["id"],
                            item["item_order"],
                            item["skill"],
                            item["difficulty_label"],
                            item["difficulty_offset"],
                            item["estimated_item_lexile"],
                            item["question_text"],
                            self.dumps(item["choices"]),
                            item["correct_choice"],
                            self.dumps(item["rationales"]),
                            1,
                            now,
                            now,
                        ),
                    )
            conn.commit()

    @staticmethod
    def dumps(value: Any) -> str:
        return json.dumps(value, ensure_ascii=True, sort_keys=True)

    @staticmethod
    def loads(value: str | None, default: Any) -> Any:
        if not value:
            return default
        return json.loads(value)
```

- [ ] **Step 4: Implement `service.py`**

Create `backend/pet_reading_api/service.py`:

```python
"""Business logic for PET Reading assessment."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from backend.pet_writing_api.service import ServiceError

from .adaptive import next_anchor_lexile, starting_anchor_for_grade
from .estimator import estimate_reading_level
from .storage import ReadingStorage


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def make_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class ReadingService:
    def __init__(self, storage: ReadingStorage):
        self.storage = storage
        self.storage.initialize(utc_now())

    def create_assessment(self, *, student_id: str, grade_level: int | None) -> dict[str, Any]:
        now = utc_now()
        assessment_id = make_id("rass")
        anchor = starting_anchor_for_grade(grade_level)
        with self.storage.connect() as conn:
            conn.execute(
                """
                insert into reading_assessments (
                  id, student_id, grade_level, status, target_range, started_at,
                  completed_at, duration_sec, current_anchor_lexile,
                  passages_completed, created_at, updated_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    assessment_id,
                    student_id,
                    grade_level,
                    "in_progress",
                    "grades_6_8",
                    now,
                    None,
                    0,
                    anchor,
                    0,
                    now,
                    now,
                ),
            )
            conn.commit()
        return {
            "assessment_id": assessment_id,
            "status": "in_progress",
            "current_anchor_lexile": anchor,
            "created_at": now,
        }

    def get_next_passage(self, assessment_id: str) -> dict[str, Any]:
        now = utc_now()
        with self.storage.connect() as conn:
            assessment = self._fetch_assessment(conn, assessment_id)
            used_ids = {
                row["passage_id"]
                for row in conn.execute(
                    "select passage_id from reading_assessment_passages where assessment_id = ?",
                    (assessment_id,),
                ).fetchall()
            }
            passage = conn.execute(
                """
                select * from reading_passages
                where active = 1
                  and id not in (%s)
                order by abs(anchor_lexile - ?), anchor_lexile
                limit 1
                """ % ",".join("?" for _ in used_ids) if used_ids else
                """
                select * from reading_passages
                where active = 1
                order by abs(anchor_lexile - ?), anchor_lexile
                limit 1
                """,
                (*used_ids, assessment["current_anchor_lexile"]) if used_ids else (assessment["current_anchor_lexile"],),
            ).fetchone()
            if not passage:
                raise ServiceError("NO_READING_PASSAGE", "No eligible reading passage found.", status=404)
            existing = conn.execute(
                """
                select id from reading_assessment_passages
                where assessment_id = ? and passage_id = ?
                """,
                (assessment_id, passage["id"]),
            ).fetchone()
            if not existing:
                sequence_number = int(assessment["passages_completed"]) + 1
                conn.execute(
                    """
                    insert into reading_assessment_passages (
                      id, assessment_id, passage_id, sequence_number, anchor_lexile,
                      started_at, completed_at, time_spent_sec, accuracy,
                      created_at, updated_at
                    ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        make_id("rap"),
                        assessment_id,
                        passage["id"],
                        sequence_number,
                        passage["anchor_lexile"],
                        now,
                        None,
                        0,
                        None,
                        now,
                        now,
                    ),
                )
                conn.commit()
            items = conn.execute(
                """
                select * from reading_items
                where passage_id = ? and active = 1
                order by item_order
                """,
                (passage["id"],),
            ).fetchall()
        return {
            "passage": {
                "passage_id": passage["id"],
                "title": passage["title"],
                "body_text": passage["body_text"],
                "genre": passage["genre"],
                "anchor_lexile": passage["anchor_lexile"],
            },
            "items": [
                {
                    "item_id": item["id"],
                    "skill": item["skill"],
                    "question_text": item["question_text"],
                    "choices": self.storage.loads(item["choices_json"], {}),
                }
                for item in items
            ],
        }

    def submit_responses(
        self,
        *,
        assessment_id: str,
        passage_id: str,
        time_spent_sec: int,
        responses: list[dict[str, Any]],
    ) -> dict[str, Any]:
        now = utc_now()
        with self.storage.connect() as conn:
            assessment = self._fetch_assessment(conn, assessment_id)
            item_rows = {
                row["id"]: row
                for row in conn.execute(
                    "select * from reading_items where passage_id = ?",
                    (passage_id,),
                ).fetchall()
            }
            if len(responses) != len(item_rows):
                raise ServiceError("INCOMPLETE_READING_RESPONSES", "Submit one response for every item.", status=400)
            correct_count = 0
            for response in responses:
                item = item_rows.get(response["item_id"])
                if not item:
                    raise ServiceError("READING_ITEM_NOT_FOUND", "Reading item not found for this passage.", status=404)
                selected = str(response["selected_choice"])
                is_correct = selected == item["correct_choice"]
                correct_count += 1 if is_correct else 0
                conn.execute(
                    """
                    insert into reading_responses (
                      id, assessment_id, passage_id, item_id, selected_choice,
                      is_correct, time_spent_sec, created_at
                    ) values (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        make_id("rrsp"),
                        assessment_id,
                        passage_id,
                        item["id"],
                        selected,
                        1 if is_correct else 0,
                        int(response.get("time_spent_sec", 0)),
                        now,
                    ),
                )
            accuracy = correct_count / len(item_rows) if item_rows else 0.0
            completed = int(assessment["passages_completed"]) + 1
            next_anchor = next_anchor_lexile(
                current_anchor=int(assessment["current_anchor_lexile"]),
                accuracy=accuracy,
            )
            conn.execute(
                """
                update reading_assessment_passages
                set completed_at = ?, time_spent_sec = ?, accuracy = ?, updated_at = ?
                where assessment_id = ? and passage_id = ?
                """,
                (now, time_spent_sec, accuracy, now, assessment_id, passage_id),
            )
            conn.execute(
                """
                update reading_assessments
                set current_anchor_lexile = ?, passages_completed = ?, duration_sec = duration_sec + ?, updated_at = ?
                where id = ?
                """,
                (next_anchor, completed, time_spent_sec, now, assessment_id),
            )
            conn.commit()
        return {
            "status": "ready_to_complete" if completed >= 3 else "continue",
            "passage_accuracy": round(accuracy, 3),
            "next_anchor_lexile": next_anchor,
            "passages_completed": completed,
        }

    def complete_assessment(self, assessment_id: str) -> dict[str, Any]:
        now = utc_now()
        with self.storage.connect() as conn:
            assessment = self._fetch_assessment(conn, assessment_id)
            responses = conn.execute(
                """
                select ri.estimated_item_lexile, ri.skill, rr.is_correct, rr.time_spent_sec
                from reading_responses rr
                join reading_items ri on ri.id = rr.item_id
                where rr.assessment_id = ?
                """,
                (assessment_id,),
            ).fetchall()
            response_payload = [
                {
                    "estimated_item_lexile": row["estimated_item_lexile"],
                    "skill": row["skill"],
                    "correct": bool(row["is_correct"]),
                    "time_seconds": row["time_spent_sec"],
                }
                for row in responses
            ]
            estimate = estimate_reading_level(
                responses=response_payload,
                passages_completed=int(assessment["passages_completed"]),
                duration_seconds=int(assessment["duration_sec"]),
            )
            report = self._report_payload(assessment_id, estimate)
            conn.execute(
                """
                insert into reading_estimates (
                  id, assessment_id, estimated_lower_lexile, estimated_upper_lexile,
                  practice_lower_lexile, practice_upper_lexile, cefr_estimate,
                  confidence_label, validity_flags_json, domain_scores_json,
                  report_payload_json, created_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(assessment_id) do update set
                  estimated_lower_lexile = excluded.estimated_lower_lexile,
                  estimated_upper_lexile = excluded.estimated_upper_lexile,
                  practice_lower_lexile = excluded.practice_lower_lexile,
                  practice_upper_lexile = excluded.practice_upper_lexile,
                  cefr_estimate = excluded.cefr_estimate,
                  confidence_label = excluded.confidence_label,
                  validity_flags_json = excluded.validity_flags_json,
                  domain_scores_json = excluded.domain_scores_json,
                  report_payload_json = excluded.report_payload_json
                """,
                (
                    make_id("rest"),
                    assessment_id,
                    estimate["estimated_lower_lexile"],
                    estimate["estimated_upper_lexile"],
                    estimate["practice_lower_lexile"],
                    estimate["practice_upper_lexile"],
                    estimate["cefr_estimate"],
                    estimate["confidence_label"],
                    self.storage.dumps(estimate["validity_flags"]),
                    self.storage.dumps(estimate["domain_scores"]),
                    self.storage.dumps(report),
                    now,
                ),
            )
            conn.execute(
                """
                update reading_assessments
                set status = ?, completed_at = ?, updated_at = ?
                where id = ?
                """,
                ("completed", now, now, assessment_id),
            )
            conn.commit()
        return report

    def get_report(self, assessment_id: str) -> dict[str, Any]:
        with self.storage.connect() as conn:
            row = conn.execute(
                "select report_payload_json from reading_estimates where assessment_id = ?",
                (assessment_id,),
            ).fetchone()
        if not row:
            raise ServiceError("READING_REPORT_NOT_READY", "Reading report is not ready.", status=404)
        return self.storage.loads(row["report_payload_json"], {})

    def _fetch_assessment(self, conn: Any, assessment_id: str) -> Any:
        row = conn.execute("select * from reading_assessments where id = ?", (assessment_id,)).fetchone()
        if not row:
            raise ServiceError("READING_ASSESSMENT_NOT_FOUND", "Reading assessment not found.", status=404)
        return row

    def _report_payload(self, assessment_id: str, estimate: dict[str, Any]) -> dict[str, Any]:
        return {
            "assessment_id": assessment_id,
            "estimated_range": f"{estimate['estimated_lower_lexile']}L-{estimate['estimated_upper_lexile']}L",
            "practice_range": f"{estimate['practice_lower_lexile']}L-{estimate['practice_upper_lexile']}L",
            "cefr_estimate": estimate["cefr_estimate"],
            "confidence": estimate["confidence_label"],
            "range_status": estimate["range_status"],
            "summary": estimate["summary"],
            "domain_scores": estimate["domain_scores"],
            "validity_flags": estimate["validity_flags"],
            "recommendations": estimate["recommendations"],
        }
```

- [ ] **Step 5: Run reading API test and keep the expected route failure**

Run:

```bash
python3 -m unittest tests/test_reading_api.py
```

Expected: still fails with `HTTP Error 404: Not Found` because server routes are not wired.

Commit only if no unrelated files are changed:

```bash
git add backend/pet_reading_api/storage.py backend/pet_reading_api/service.py tests/test_reading_api.py
git commit -m "feat: add reading assessment service"
```

---

## Task 4: Server Route Integration

**Files:**

- Modify: `backend/pet_writing_api/server.py`
- Test: `tests/test_reading_api.py`
- Regression Test: `tests/test_writing_api.py`

- [ ] **Step 1: Modify server imports and service creation**

In `backend/pet_writing_api/server.py`, add imports:

```python
from backend.pet_reading_api.service import ReadingService
from backend.pet_reading_api.storage import ReadingStorage
```

Change:

```python
def make_handler(service: WritingService) -> type[BaseHTTPRequestHandler]:
```

to:

```python
def make_handler(service: WritingService, reading_service: ReadingService) -> type[BaseHTTPRequestHandler]:
```

Change `create_server` from:

```python
def create_server(host: str, port: int, db_path: str) -> ThreadingHTTPServer:
    service = WritingService(Storage(db_path))
    server = ThreadingHTTPServer((host, port), make_handler(service))
    return server
```

to:

```python
def create_server(host: str, port: int, db_path: str) -> ThreadingHTTPServer:
    service = WritingService(Storage(db_path))
    reading_service = ReadingService(ReadingStorage(db_path))
    server = ThreadingHTTPServer((host, port), make_handler(service, reading_service))
    return server
```

- [ ] **Step 2: Add reading routes before writing routes**

Inside `_dispatch`, after the health route and before writing routes, add:

```python
                if method == "POST" and path == "/api/v1/reading/assessments":
                    body = read_json_body(self)
                    json_response(
                        self,
                        201,
                        reading_service.create_assessment(
                            student_id=body["student_id"],
                            grade_level=body.get("grade_level"),
                        ),
                    )
                    return
                if method == "GET" and path.startswith("/api/v1/reading/assessments/") and path.endswith("/next"):
                    assessment_id = path.split("/")[-2]
                    json_response(self, 200, reading_service.get_next_passage(assessment_id))
                    return
                if method == "POST" and path.startswith("/api/v1/reading/assessments/") and path.endswith("/responses"):
                    assessment_id = path.split("/")[-2]
                    body = read_json_body(self)
                    json_response(
                        self,
                        200,
                        reading_service.submit_responses(
                            assessment_id=assessment_id,
                            passage_id=body["passage_id"],
                            time_spent_sec=int(body.get("time_spent_sec", 0)),
                            responses=body["responses"],
                        ),
                    )
                    return
                if method == "POST" and path.startswith("/api/v1/reading/assessments/") and path.endswith("/complete"):
                    assessment_id = path.split("/")[-2]
                    json_response(self, 200, reading_service.complete_assessment(assessment_id))
                    return
                if method == "GET" and path.startswith("/api/v1/reading/assessments/") and path.endswith("/report"):
                    assessment_id = path.split("/")[-2]
                    json_response(self, 200, reading_service.get_report(assessment_id))
                    return
```

- [ ] **Step 3: Run reading and writing API tests**

Run:

```bash
python3 -m unittest tests/test_reading_api.py tests/test_writing_api.py
```

Expected: both test files pass with `OK`.

- [ ] **Step 4: Commit server integration**

Commit:

```bash
git add backend/pet_writing_api/server.py tests/test_reading_api.py
git commit -m "feat: expose reading assessment api"
```

---

## Task 5: Static UI Mockup

**Files:**

- Create: `docs/mockups/reading-lexile-assessment-flow.html`

- [ ] **Step 1: Create the static HTML mockup**

Create `docs/mockups/reading-lexile-assessment-flow.html`:

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Reading Level Assessment Mockup</title>
  <style>
    :root {
      --bg: #f7f5ef;
      --surface: #fffdf7;
      --ink: #1d2528;
      --muted: #64706f;
      --line: #d9d5c8;
      --green: #247257;
      --green-soft: #e2f0ea;
      --blue: #2f6f94;
      --blue-soft: #e4eff6;
      --gold: #a66d16;
      --gold-soft: #f8ecd4;
      --red: #b84e42;
      --red-soft: #f8e4df;
      --shadow: 0 18px 40px rgba(29, 37, 40, 0.12);
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    button { font: inherit; }

    .shell {
      width: min(1200px, calc(100% - 32px));
      margin: 0 auto;
      padding: 20px 0 36px;
    }

    .topbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 12px 0 20px;
    }

    .brand {
      display: flex;
      gap: 12px;
      align-items: center;
    }

    .logo {
      width: 40px;
      height: 40px;
      border-radius: 8px;
      display: grid;
      place-items: center;
      background: var(--ink);
      color: var(--surface);
      font-weight: 800;
    }

    .brand strong { display: block; font-size: 15px; }
    .brand span { display: block; color: var(--muted); font-size: 13px; margin-top: 2px; }

    .steps {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;
      width: min(620px, 100%);
    }

    .step {
      border: 1px solid var(--line);
      background: rgba(255, 253, 247, 0.78);
      border-radius: 8px;
      padding: 10px 12px;
      color: var(--muted);
      text-align: left;
      cursor: pointer;
    }

    .step small { display: block; font-size: 11px; text-transform: uppercase; }
    .step span { display: block; font-weight: 750; font-size: 14px; margin-top: 2px; }
    .step.active { background: var(--ink); color: var(--surface); border-color: var(--ink); box-shadow: var(--shadow); }

    .panel {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
      padding: 24px;
    }

    .view { display: none; }
    .view.active { display: block; }

    .hero {
      display: grid;
      grid-template-columns: minmax(0, 1fr) 340px;
      gap: 22px;
      align-items: start;
    }

    h1, h2, h3 { margin: 0; letter-spacing: 0; }
    h1 { font-size: clamp(32px, 4vw, 56px); line-height: 1; max-width: 780px; }
    h2 { font-size: 28px; margin-bottom: 10px; }
    h3 { font-size: 16px; margin-bottom: 8px; }

    p { color: var(--muted); line-height: 1.58; margin: 10px 0 0; }

    .actions { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 22px; }
    .btn {
      border: 1px solid var(--ink);
      background: var(--ink);
      color: var(--surface);
      border-radius: 8px;
      min-height: 42px;
      padding: 0 16px;
      font-weight: 750;
      cursor: pointer;
    }
    .btn.secondary { background: transparent; color: var(--ink); }

    .stats {
      display: grid;
      gap: 10px;
    }

    .stat, .question, .card {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: rgba(255, 253, 247, 0.8);
      padding: 14px;
    }

    .stat strong { display: block; font-size: 24px; }
    .stat span { display: block; color: var(--muted); font-size: 13px; margin-top: 2px; }

    .assessment {
      display: grid;
      grid-template-columns: minmax(0, 1.15fr) minmax(320px, 0.85fr);
      gap: 18px;
      align-items: start;
    }

    .passage {
      font-size: 17px;
      line-height: 1.72;
      color: #263033;
    }

    .meta {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin: 0 0 14px;
    }

    .pill {
      display: inline-flex;
      align-items: center;
      min-height: 26px;
      padding: 0 10px;
      border-radius: 999px;
      background: var(--blue-soft);
      color: #214d68;
      font-size: 12px;
      font-weight: 750;
    }

    .timer {
      color: var(--gold);
      background: var(--gold-soft);
    }

    .question { margin-bottom: 10px; }
    .question strong { display: block; margin-bottom: 10px; }

    .choice {
      display: block;
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      text-align: left;
      padding: 10px 12px;
      margin-top: 8px;
      cursor: pointer;
    }
    .choice.active { border-color: var(--green); background: var(--green-soft); color: #174d3b; }

    .report-grid {
      display: grid;
      grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
      gap: 18px;
      align-items: start;
    }

    .score-band {
      height: 30px;
      border-radius: 6px;
      overflow: hidden;
      display: grid;
      grid-template-columns: 22% 28% 28% 22%;
      margin: 18px 0 8px;
    }
    .score-band div:nth-child(1) { background: var(--red); }
    .score-band div:nth-child(2) { background: #f1c44d; }
    .score-band div:nth-child(3) { background: var(--blue); }
    .score-band div:nth-child(4) { background: var(--green); }

    .big-score {
      font-size: 44px;
      line-height: 1;
      font-weight: 850;
      margin-top: 12px;
    }

    .domains {
      display: grid;
      gap: 10px;
    }

    .domain-row {
      display: grid;
      grid-template-columns: 180px 1fr 44px;
      gap: 10px;
      align-items: center;
      font-size: 14px;
    }

    .bar {
      height: 10px;
      border-radius: 999px;
      background: #e8e4d8;
      overflow: hidden;
    }
    .bar i { display: block; height: 100%; background: var(--green); }

    @media (max-width: 860px) {
      .topbar, .hero, .assessment, .report-grid { grid-template-columns: 1fr; display: grid; }
      .topbar { align-items: stretch; }
      .steps { width: 100%; }
      .domain-row { grid-template-columns: 1fr; gap: 6px; }
    }
  </style>
</head>
<body>
  <main class="shell">
    <header class="topbar">
      <div class="brand">
        <div class="logo">R</div>
        <div>
          <strong>Reading Level Check</strong>
          <span>Grade 6-8 Lexile-like estimate</span>
        </div>
      </div>
      <nav class="steps" aria-label="Mockup views">
        <button class="step active" data-view="start"><small>Step 1</small><span>Start</span></button>
        <button class="step" data-view="test"><small>Step 2</small><span>Reading</span></button>
        <button class="step" data-view="report"><small>Step 3</small><span>Report</span></button>
      </nav>
    </header>

    <section class="panel view active" id="start">
      <div class="hero">
        <div>
          <h1>Find the right English reading level in 20-30 minutes.</h1>
          <p>This internal assessment estimates a reading range, not an official Lexile score. The result helps teachers choose independent reading materials and supported challenge texts.</p>
          <div class="actions">
            <button class="btn" data-view-target="test">Start assessment</button>
            <button class="btn secondary" data-view-target="report">Preview report</button>
          </div>
        </div>
        <aside class="stats">
          <div class="stat"><strong>3-5</strong><span>Adaptive passages</span></div>
          <div class="stat"><strong>18-24</strong><span>Reading items</span></div>
          <div class="stat"><strong>500L-1100L</strong><span>MVP target range</span></div>
        </aside>
      </div>
    </section>

    <section class="panel view" id="test">
      <div class="assessment">
        <article>
          <div class="meta">
            <span class="pill">Passage 2 of 4</span>
            <span class="pill">Anchor 875L</span>
            <span class="pill timer">08:42 elapsed</span>
          </div>
          <h2>A Robot That Carries Books</h2>
          <p class="passage">The students in Class Seven wanted to build a robot for the school technology fair, but they did not want to make another toy car. Their teacher suggested watching younger students in the library. After two afternoons, the class noticed that many children carried heavy books from one table to another while looking for information. The team designed a small robot with a flat top and slow wheels. It followed a black line on the floor and stopped when someone pressed a red button.</p>
          <p class="passage">The robot was not fast, but that was part of the plan. In a crowded library, a quick robot would be unsafe. At the fair, the judges praised the team because they had solved a real school problem.</p>
        </article>
        <aside>
          <div class="question">
            <strong>Why was being slow a good feature for the robot?</strong>
            <button class="choice">A. It made the robot cheaper to paint.</button>
            <button class="choice active">B. It made the robot safer in a busy place.</button>
            <button class="choice">C. It helped the robot win races.</button>
            <button class="choice">D. It allowed the robot to read books.</button>
          </div>
          <div class="question">
            <strong>What does praised mean in the passage?</strong>
            <button class="choice">A. Spoke well of</button>
            <button class="choice">B. Disagreed with</button>
            <button class="choice">C. Copied from</button>
            <button class="choice">D. Waited for</button>
          </div>
          <div class="actions">
            <button class="btn" data-view-target="report">Submit passage</button>
          </div>
        </aside>
      </div>
    </section>

    <section class="panel view" id="report">
      <div class="report-grid">
        <section class="card">
          <h2>Reading Report</h2>
          <p>Estimated Lexile-like Range</p>
          <div class="big-score">720L-860L</div>
          <div class="score-band"><div></div><div></div><div></div><div></div></div>
          <p><strong>Practice Range:</strong> 650L-800L</p>
          <p><strong>CEFR:</strong> A2+</p>
          <p><strong>Confidence:</strong> Medium</p>
        </section>
        <section class="card">
          <h2>Skill Profile</h2>
          <div class="domains">
            <div class="domain-row"><span>Main idea</span><div class="bar"><i style="width:82%"></i></div><strong>82</strong></div>
            <div class="domain-row"><span>Detail</span><div class="bar"><i style="width:88%"></i></div><strong>88</strong></div>
            <div class="domain-row"><span>Inference</span><div class="bar"><i style="width:61%"></i></div><strong>61</strong></div>
            <div class="domain-row"><span>Vocabulary context</span><div class="bar"><i style="width:70%"></i></div><strong>70</strong></div>
            <div class="domain-row"><span>Structure / purpose</span><div class="bar"><i style="width:66%"></i></div><strong>66</strong></div>
          </div>
          <p><strong>Next step:</strong> Read 650L-800L texts independently. Use 800L-900L texts with teacher support.</p>
        </section>
      </div>
    </section>
  </main>
  <script>
    const buttons = document.querySelectorAll("[data-view], [data-view-target]");
    function showView(id) {
      document.querySelectorAll(".view").forEach((view) => view.classList.toggle("active", view.id === id));
      document.querySelectorAll(".step").forEach((step) => step.classList.toggle("active", step.dataset.view === id));
    }
    buttons.forEach((button) => {
      button.addEventListener("click", () => showView(button.dataset.view || button.dataset.viewTarget));
    });
  </script>
</body>
</html>
```

- [ ] **Step 2: Open the mockup locally**

Run:

```bash
open docs/mockups/reading-lexile-assessment-flow.html
```

Expected: browser opens the mockup with Start, Reading, and Report tabs.

- [ ] **Step 3: Commit mockup**

Commit:

```bash
git add docs/mockups/reading-lexile-assessment-flow.html
git commit -m "docs: add reading assessment mockup"
```

---

## Task 6: README Notes and Full Verification

**Files:**

- Modify: `README.md`

- [ ] **Step 1: Add README section**

Append to `README.md` under the PET Reading section:

```markdown

## Reading Level Assessment MVP

The backend also supports a first Lexile-like reading assessment flow for Grade 6-8 students.

This is an internal teaching estimate, not an official Lexile or Renaissance Star Reading score.

### Reading assessment endpoints

- `POST /api/v1/reading/assessments`
- `GET /api/v1/reading/assessments/{assessment_id}/next`
- `POST /api/v1/reading/assessments/{assessment_id}/responses`
- `POST /api/v1/reading/assessments/{assessment_id}/complete`
- `GET /api/v1/reading/assessments/{assessment_id}/report`

### Run reading tests

```bash
python3 -m unittest \
  /Users/xzhan/vibcoding/EnglishTest/tests/test_reading_estimator.py \
  /Users/xzhan/vibcoding/EnglishTest/tests/test_reading_adaptive.py \
  /Users/xzhan/vibcoding/EnglishTest/tests/test_reading_api.py
```

### UI mockup

Open:

`/Users/xzhan/vibcoding/EnglishTest/docs/mockups/reading-lexile-assessment-flow.html`
```

- [ ] **Step 2: Run reading tests**

Run:

```bash
python3 -m unittest \
  tests/test_reading_estimator.py \
  tests/test_reading_adaptive.py \
  tests/test_reading_api.py
```

Expected: all tests pass with `OK`.

- [ ] **Step 3: Run writing regression tests**

Run:

```bash
python3 -m unittest \
  tests/test_writing_api.py \
  tests/test_writing_prescore_api.py \
  tests/test_review_workflow_api.py
```

Expected: all tests pass with `OK`.

- [ ] **Step 4: Commit docs and final verification**

Commit:

```bash
git add README.md
git commit -m "docs: document reading assessment mvp"
```

Run:

```bash
git status --short
```

Expected: no output.

---

## Data Request for User

The MVP can start with seed demo passages, but real sample material will improve the level bands.

Preferred sample format:

```json
{
  "title": "A sample title",
  "body_text": "Full passage text...",
  "target_band": "650L-800L",
  "estimated_anchor_lexile": 750,
  "cefr": "A2",
  "grade_range": "6-7",
  "genre": "informational",
  "source": "original_or_owned",
  "items": [
    {
      "skill": "main_idea",
      "question_text": "Question text...",
      "choices": {"A": "...", "B": "...", "C": "...", "D": "..."},
      "correct_choice": "B",
      "evidence": "Sentence or paragraph evidence.",
      "rationales": {"A": "...", "B": "...", "C": "...", "D": "..."}
    }
  ]
}
```

Minimum useful batch:

- `8-12` passages
- at least `2` passages per band
- each passage with `5` items
- only original, owned, or clearly licensed text

Best first batch:

- `20` passages
- `5` per band
- mixed genres: narrative, informational, functional, opinion

---

## Self-Review

Spec coverage:

- Adaptive 20-30 minute flow: Tasks 2-4.
- Lexile-like estimator: Task 1.
- Seed content and item metadata: Task 2.
- API and persistence: Tasks 3-4.
- UI mockup: Task 5.
- Documentation and verification: Task 6.

Deferred to a second plan:

- AI-assisted content generation pipeline.
- Automatic item validation tooling.
- Human review UI for content approval.
- Star Reading calibration import.

These are deliberately excluded from this first implementation because the backend assessment loop should work before the content factory is automated.

