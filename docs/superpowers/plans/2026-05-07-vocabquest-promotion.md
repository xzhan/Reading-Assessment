# VocabQuest Promotion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Promote the near-ready reviewed VocabQuest candidates into the app's formal reading bank by deterministically replacing one duplicate-skill item with the missing required-skill item.

**Architecture:** Add a focused promoter module that converts reviewed candidates into seed-compatible passage dictionaries. Generate `backend/pet_reading_api/vocabquest_promoted.py`, then append those promoted records to `READING_PASSAGES` in `seed_data.py` so the existing SQLite initialization and reading app path continue unchanged.

**Tech Stack:** Python standard library, JSONL, existing unittest suite, existing SQLite seed path.

---

### Task 1: Promoter Unit Tests

**Files:**
- Modify: `tests/test_reading_review_bank.py`
- Test: `tests/test_reading_review_bank.py`

- [ ] **Step 1: Add failing tests for promotion eligibility**

Add tests that load `data/reading_review/vocabquest_reviewed_candidates.jsonl`, call `promote_vocab_quest_candidates`, and assert:

```python
promoted, skipped = promote_vocab_quest_candidates(candidates)
self.assertEqual(len(promoted), 7)
self.assertGreaterEqual(len(skipped), 31)
for passage in promoted:
    self.assertEqual(
        {item["skill"] for item in passage["items"]},
        set(REQUIRED_SKILLS),
    )
    self.assertEqual(len(passage["items"]), 5)
    self.assertTrue(passage["id"].startswith("rp_vq_"))
    for item in passage["items"]:
        self.assertEqual(set(item["choices"]), {"A", "B", "C", "D"})
        self.assertIn(item["correct_choice"], item["choices"])
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
python3 -m unittest tests.test_reading_review_bank
```

Expected: failure because `promote_vocab_quest_candidates` does not exist yet.

### Task 2: Promotion Logic

**Files:**
- Modify: `backend/pet_reading_api/review_bank.py`
- Test: `tests/test_reading_review_bank.py`

- [ ] **Step 1: Implement public promotion function**

Add:

```python
def promote_vocab_quest_candidates(candidates: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    promoted = []
    skipped = []
    for candidate in candidates:
        promoted_passage, reason = _promote_vocab_quest_candidate(candidate)
        if promoted_passage:
            promoted.append(promoted_passage)
        else:
            skipped.append({"passage_id": candidate.get("passage_id", ""), "reason": reason})
    return promoted, skipped
```

- [ ] **Step 2: Implement candidate promotion rules**

Rules:

```python
if candidate.get("review_status") != "reviewed_candidate": skip
if len(items) != 5: skip
if any(item has invalid choices/correct_choice): skip
if len(missing_required_skills) != 1: skip
if missing skill not in {"structure_author_purpose", "main_idea"}: skip
```

Keep one item per already-covered skill, replace one duplicate-skill item with a generated missing-skill item, and return a seed-compatible passage dict.

- [ ] **Step 3: Generate repair items**

For missing `structure_author_purpose`, generate:

```python
{
    "skill": "structure_author_purpose",
    "question_text": "Why does the writer include several specific details in the passage?",
    "choices": {
        "A": "To show how the main idea develops through events or examples",
        "B": "To list unrelated facts without a purpose",
        "C": "To explain a grammar rule",
        "D": "To introduce a different passage",
    },
    "correct_choice": "A",
}
```

For missing `main_idea`, generate:

```python
{
    "skill": "main_idea",
    "question_text": "What is the passage mainly about?",
    "choices": {
        "A": f"The central situation in {title}",
        "B": "A list of unrelated facts",
        "C": "A grammar lesson about one word",
        "D": "A completely different event",
    },
    "correct_choice": "A",
}
```

- [ ] **Step 4: Run focused tests**

Run:

```bash
python3 -m unittest tests.test_reading_review_bank
```

Expected: pass.

### Task 3: Generator Script And Seed Integration

**Files:**
- Create: `scripts/promote_vocab_quest_reading_bank.py`
- Create: `backend/pet_reading_api/vocabquest_promoted.py`
- Modify: `backend/pet_reading_api/seed_data.py`
- Test: `tests/test_reading_adaptive.py`, `tests/test_reading_api.py`

- [ ] **Step 1: Add generator script**

Create a script that reads `data/reading_review/vocabquest_reviewed_candidates.jsonl`, calls `promote_vocab_quest_candidates`, and writes:

```python
"""Generated promoted VocabQuest reading passages."""

from __future__ import annotations

VOCABQUEST_PROMOTED_PASSAGES = [...]
```

Use `pprint.pformat(..., sort_dicts=False, width=120)`.

- [ ] **Step 2: Generate promoted module**

Run:

```bash
python3 scripts/promote_vocab_quest_reading_bank.py
```

Expected output includes `Promoted 7 candidates` and path `backend/pet_reading_api/vocabquest_promoted.py`.

- [ ] **Step 3: Append promoted passages to seed data**

Modify `seed_data.py`:

```python
from .vocabquest_promoted import VOCABQUEST_PROMOTED_PASSAGES

READING_PASSAGES = [
    ...
] + VOCABQUEST_PROMOTED_PASSAGES
```

- [ ] **Step 4: Verify runtime selection can see promoted passages**

Add or update a test asserting at least one `rp_vq_` passage exists in `READING_PASSAGES` and all its items cover `REQUIRED_SKILLS`.

Run:

```bash
python3 -m unittest tests.test_reading_adaptive tests.test_reading_api
```

Expected: pass.

### Task 4: Final Verification

**Files:**
- Verify all touched files

- [ ] **Step 1: Run focused tests**

```bash
python3 -m unittest tests.test_reading_review_bank tests.test_reading_adaptive tests.test_reading_api
```

Expected: all pass.

- [ ] **Step 2: Run full test suite**

```bash
python3 -m unittest discover -s tests
```

Expected: all pass.

- [ ] **Step 3: Check whitespace**

```bash
git diff --check
```

Expected: no output.
