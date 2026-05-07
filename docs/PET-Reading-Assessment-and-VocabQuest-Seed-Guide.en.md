# PET Reading Assessment and VocabQuest Seed Guide

Date: 2026-05-07

This document explains how the Reading MVP uses VocabQuest-generated reading content, how candidates are reviewed for seed eligibility, and how the main assessment flow uses promoted passages.

## 1. Goal

The Reading MVP does not produce an official Lexile score or an official Renaissance Star Reading score. It produces an internal, explainable reading estimate for teachers and parents.

The report includes:

- Lexile-like reading range
- ZPD-like practice range
- CEFR estimate
- Reading skill profile
- Parent-facing reading material guidance
- Test duration and fidelity notes

The current main assessment flow is:

- 6 reading passages
- 5 multiple-choice items per passage
- 30 total items
- Coverage across 5 reading skills

## 2. Required Skills

Each diagnostic-ready passage must cover the following 5 skills exactly once:

| Skill field | Meaning | Purpose |
| --- | --- | --- |
| `main_idea` | Main idea | Checks whether the student understands the whole passage |
| `detail` | Detail | Checks whether the student can locate and understand stated details |
| `inference` | Inference | Checks whether the student can infer meaning from the text |
| `vocabulary_context` | Vocabulary in context | Checks whether the student can infer word meaning from context |
| `structure_author_purpose` | Structure and author purpose | Checks whether the student understands why the author wrote something |

If a passage does not cover all 5 required skills, it should not be used directly as a diagnostic assessment seed.

## 3. What Is a Reviewed Candidate?

A `reviewed candidate` is a normalized reading record imported from a VocabQuest export and prepared for review or promotion.

Main files:

- `data/reading_review/vocabquest_reviewed_candidates.jsonl`
- `data/reading_review/vocabquest_reviewed_candidates.csv`

Each candidate contains:

- passage id
- title
- body text
- anchor Lexile-like difficulty
- CEFR level
- item list
- skill for each item
- A-D choices
- correct answer
- rationale
- validation flags
- diagnostic-ready status

## 4. Seed Eligibility

A candidate is seed-ready when it satisfies all of these conditions:

- Body text has at least 80 English words
- Exactly 5 items
- Each item has A-D choices
- The correct answer maps to one of the choices
- The correct answer has a rationale
- The 5 items cover the 5 required skills exactly once
- No validation flags are present

When this is true:

```text
diagnostic_ready = true
validation_flags = []
```

Such a candidate can be promoted into app seed data.

## 5. What Is Promotion?

Promotion converts reviewed candidates into seed-compatible reading passages used by the app.

Input:

```text
data/reading_review/vocabquest_reviewed_candidates.jsonl
```

Output:

```text
backend/pet_reading_api/vocabquest_promoted.py
```

Promoted passages are imported by `seed_data.py` into `READING_PASSAGES`, then written into `reading_passages` and `reading_items` when the local database initializes.

## 6. Current Bank Snapshot

After the latest update:

- The review bank contains 39 VocabQuest reviewed candidates
- The promoted seed bank contains 10 VocabQuest readings
- 29 candidates remain skipped for now

New or replaced entries:

| Seed ID | Title | Status |
| --- | --- | --- |
| `rp_vq_253ea7923758` | `Reading Quest [Literature]: PET全_Page_57_03261514` | Replaces the old invalid Page 57 candidate |
| `rp_vq_3fcd767f3e99` | `Reading Quest [Literature]: PET全_Page_59_03261514` | Newly added |

The old Page 57 candidate:

```text
vq_4d34d1625dea
```

was removed from the reviewed JSONL because its diagnostic skill coverage was incomplete. It has been replaced by the corrected Page 57 version.

## 7. Importing a New VocabQuest File

Example input:

```bash
/Users/xzhan/Downloads/reading_quests.json
```

Import it into the review bank:

```bash
python3 scripts/import_vocab_quest_reading_bank.py \
  /Users/xzhan/Downloads/reading_quests.json
```

Check the output:

```text
Imported N reviewed Vocab Quest candidates
Diagnostic-ready candidates: M
Validation flags:
...
```

If the diagnostic-ready count is lower than expected, some candidates need manual repair.

## 8. Generating App Seeds

After importing or repairing candidates, run:

```bash
python3 scripts/promote_vocab_quest_reading_bank.py
```

Example output:

```text
Promoted 10 candidates
Skipped 29 candidates
Output: backend/pet_reading_api/vocabquest_promoted.py
```

`Promoted` is the number of passages available to the app.

`Skipped` is the number of candidates kept out of the seed bank. Common reasons include:

- `item_count_not_5`
- `missing_skill_count_not_1`
- `unsupported_missing_skill_*`

## 9. Minimal Manual Repair Rule

If a passage is mostly usable but misses one requirement, prefer the smallest safe edit:

- Keep valid items
- Change only the incorrect `skill`
- Or replace only the item needed for the missing skill
- Do not rewrite the whole passage
- Do not change passage content unless necessary

Example repair pattern:

```text
Keep q1/q2/q4/q5, change q3 from detail to structure_author_purpose.
```

This keeps the review process fast and reduces the chance of introducing new content errors.

## 10. Main Assessment Flow

When the user clicks `Start assessment`:

1. The system creates a reading assessment.
2. The grade level determines the initial anchor Lexile-like difficulty.
3. The app returns one passage and 5 items at a time.
4. After each submission, the system calculates passage accuracy.
5. Adaptive logic adjusts the next anchor.
6. After 6 passages, the status becomes `ready_to_complete`.
7. The system generates the reading report.

Status rule:

```text
passages 1-5: continue
passage 6: ready_to_complete
```

## 11. Important Report Terms

| Term | Meaning |
| --- | --- |
| Lexile-like | Internal reading difficulty estimate, not official Lexile |
| SS-like | Internal scaled-score display slot, not official Star SS |
| PR | Percentile Rank; currently N/A because there is no norm group |
| GE-like | Internal grade-equivalent style estimate |
| IRL-like | Internal instructional reading level projection |
| ZPD-like | Recommended reading practice range |
| Benchmark-like | Internal benchmark band |
| Test Fidelity | Validity and confidence notes for the assessment |

## 12. Verification Commands

After every import, replacement, or promotion, run at least:

```bash
python3 -m unittest tests.test_reading_review_bank tests.test_reading_api tests.test_reading_adaptive tests.test_reading_estimator
git diff --check
```

Before committing or shipping, run the full suite:

```bash
python3 -m unittest discover -s tests
```

## 13. Running Locally

Start the app:

```bash
python3 backend/app.py --host 127.0.0.1 --port 8123 \
  --db-path /tmp/english_test_reading_manual_test.db
```

Open:

```text
http://127.0.0.1:8123/app/reading
```

If an old process is already using the port, stop it first and restart the app. The database must be reseeded after regenerating promoted passages so the running app can see the latest seed data.

