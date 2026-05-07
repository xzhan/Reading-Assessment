# VocabQuest Promotion Design

## Goal

Promote the reasonable subset of reviewed VocabQuest reading candidates into the app's formal reading bank, without polluting the diagnostic bank with incomplete or structurally broken records.

The first promotion target is the near-ready subset from `data/reading_review/vocabquest_reviewed_candidates.jsonl`: candidates with five items, complete answer keys, and exactly one missing required diagnostic skill. The current import data has no candidate that already covers all five required skills, but several candidates only lack `structure_author_purpose` or `main_idea`.

## Required Skills

Promoted passages must end with one active item for each skill:

- `main_idea`
- `detail`
- `inference`
- `vocabulary_context`
- `structure_author_purpose`

## Promotion Rules

The promotion script will read reviewed candidates and emit seed-compatible records. It will promote a candidate only when:

- `review_status` is `reviewed_candidate`
- there are exactly five source items
- every source item has four choices and a valid `correct_choice`
- the source covers exactly four of the five required skills
- the missing skill is repairable with a deterministic generated item

The first repair pass supports:

- missing `structure_author_purpose`: add a purpose/structure question about why the writer includes events, examples, or details
- missing `main_idea`: add a main-idea question using the passage title and distractors

For candidates with duplicate skills, the promoter will keep the strongest item per duplicate group and replace one duplicate item with the generated missing-skill item. Candidates with 4 or 6 items, missing answer keys, or more than one missing skill stay in review-bank only.

## App Integration

Promoted records are written to a generated module, `backend/pet_reading_api/vocabquest_promoted.py`, as `VOCABQUEST_PROMOTED_PASSAGES`. `seed_data.py` imports and appends those records to the existing `READING_PASSAGES` list. The current SQLite initialization path remains unchanged, so the app continues to use the same `reading_passages` and `reading_items` tables.

Generated IDs will use the source candidate ID, for example:

- passage id: `rp_vq_<source>`
- passage code: `VQ_<SOURCE>`
- item id: `ri_vq_<source>_<skill>`

Metadata will mark the source as `vocab_quest_promoted` so later audits can separate generated/promoted content from hand-authored seed passages.

## Safety

Practice-bank data remains unchanged. The full 38-candidate JSONL stays available for vocabulary practice and future review.

The promotion script should print:

- promoted count
- skipped count
- skip reasons
- generated output path

Tests will verify that promoted records are seed-compatible, have one item per required skill, have valid answer keys, and are visible through the normal reading assessment selection path.
