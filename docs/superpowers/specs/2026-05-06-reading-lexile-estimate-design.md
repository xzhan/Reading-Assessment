# Reading Lexile-Like Estimate Design

**Date:** 2026-05-06  
**Status:** Draft  
**Scope:** Grade 6-8 adaptive reading assessment that estimates an internal Lexile-like range

## 1. Goal

Build a 20-30 minute adaptive reading assessment for Chinese Grade 6-8 students.

The assessment should estimate:

- `Estimated Lexile-like Range`, for example `720L-860L`
- `Practice Reading Range`, for example `650L-800L`
- `CEFR Estimate`, for example `A2+`
- domain scores for reading skills
- confidence level and validity notes
- concrete reading and training recommendations

The first version is for internal teaching and placement. It should not claim to produce an official Lexile score.

## 2. Product Positioning

This product answers one practical question:

> What English reading material is this Grade 6-8 student ready to read now?

The system should help teachers and parents choose appropriately difficult texts, not produce a high-stakes official score.

The result should be honest about uncertainty. The first version should output a range, not a fake precise single number.

## 3. Non-Goals

This version does not include:

- official Lexile or Renaissance Star Reading certification
- public claims that the score is an official Lexile measure
- coverage below `500L` or above `1100L`
- a full advanced version for `1000L-1300L`
- item response theory or Rasch modeling at launch
- automated acceptance of AI-generated passages without human review
- a large public student rollout before calibration data exists

## 4. Target Student Range

The first version targets:

- Chinese Grade 6-8 students
- CEFR range: `A2` to `B1`
- internal reading difficulty range: `500L-1100L`

If a student is clearly outside this range, the report should say:

- `Below Target Range`
- or `Above Target Range`

It should not force an unreliable score.

## 5. Assessment Flow

The first version should use passage-level adaptation.

The student reads one passage, answers all items for that passage, then the system decides the next passage difficulty.

### 5.1 Duration

Target duration:

- normal: `20-30` minutes
- minimum valid result: at least `3` completed passages
- normal completion: `4` completed passages
- maximum completion: `5` completed passages

### 5.2 Passage Count and Item Count

Each assessment should normally include:

- `3-5` passages
- `4-6` items per passage
- `18-24` total items

The recommended MVP shape is:

- `5` items per passage
- `4` passages for a normal valid result
- optional `5th` passage when the estimate is unstable

### 5.3 Starting Difficulty

Start from grade when available:

- Grade 6: `650L-750L`
- Grade 7: `750L-850L`
- Grade 8: `850L-950L`

If grade is missing, start from `750L-850L`.

### 5.4 Adaptation Rules

After each passage:

- `85%+` correct and normal time: raise next anchor by `100L-150L`
- `65%-84%` correct: hold or raise by `50L`
- `45%-64%` correct: lower by `50L-100L`
- below `45%` correct: lower by `100L-150L`

Time should not directly lower the reading estimate. It should affect confidence and fluency notes.

### 5.5 Stop Conditions

Stop when one of these is true:

- the student completes `4` passages and the estimate is stable
- the student completes `5` passages
- test duration reaches `30` minutes
- the student is clearly below the target range
- the student is clearly above the target range

## 6. Passage Bank Design

The passage bank should be organized by difficulty band, genre, topic, and internal anchor difficulty.

### 6.1 Difficulty Bands

| Band | Internal Range | Typical Student | Passage Length |
|---|---:|---|---:|
| Band 1 | `500L-650L` | A2- or weaker Grade 6 students | `180-260` words |
| Band 2 | `650L-800L` | A2 and Grade 6-7 core range | `240-330` words |
| Band 3 | `800L-950L` | A2+ to B1- | `300-420` words |
| Band 4 | `950L-1100L` | B1 and stronger students | `380-520` words |

Each passage should have an internal `anchor_lexile`. This is not an official Lexile measure. It is the initial difficulty point used by the adaptive and estimation logic.

Example passage metadata:

```json
{
  "estimated_lexile_band": "800L-950L",
  "anchor_lexile": 875,
  "cefr": "A2+/B1-",
  "word_count": 360,
  "topic": "school technology",
  "genre": "informational"
}
```

### 6.2 Genre Balance

The bank should not overuse one text type. Reading ability differs across text types.

Use these genres:

- `narrative`: story, diary, personal experience
- `informational`: science, history, explanation, article
- `functional`: email, notice, web page, activity information
- `opinion`: review, advice text, simple argument

For reporting, group genres into:

- `Literature`: narrative and personal experience texts
- `Informational Text`: informational, functional, and opinion texts

## 7. Item Bank Design

Each passage should have `5` multiple-choice items.

### 7.1 Required Skill Coverage

Each passage should include:

1. `main_idea`
2. `detail`
3. `inference`
4. `vocabulary_context`
5. `structure_author_purpose`

This allows the final report to show domain scores, not only a total reading estimate.

### 7.2 Item Difficulty

Each item should have its own difficulty. Passage difficulty alone is not enough.

Recommended offsets:

- `easy`: `-75L`
- `medium`: `0L`
- `hard`: `+75L`
- `very_hard`: `+125L`

Formula:

```text
estimated_item_lexile = passage_anchor_lexile + difficulty_offset
```

Example:

- passage anchor: `850L`
- easy detail item: `775L`
- medium main idea item: `850L`
- hard inference item: `925L`

### 7.3 Item Metadata

Each item should store:

```json
{
  "skill": "inference",
  "difficulty_label": "hard",
  "difficulty_offset": 75,
  "estimated_item_lexile": 925,
  "question_text": "...",
  "choices": {
    "A": "...",
    "B": "...",
    "C": "...",
    "D": "..."
  },
  "correct_choice": "C",
  "evidence": "Paragraph 3 supports this answer.",
  "rationales": {
    "A": "True detail but not the reason.",
    "B": "Opposite of the passage.",
    "C": "Correct because it follows from paragraph 3.",
    "D": "Too broad."
  }
}
```

### 7.4 Distractor Quality

Good distractors should be plausible and explainable.

Acceptable distractor patterns:

- true detail but wrong answer to this question
- partially correct but incomplete
- common misunderstanding of time, cause, or speaker
- reasonable real-world assumption that is not supported by the text
- overextended inference

Invalid distractor patterns:

- obviously silly option
- option that can be eliminated without reading
- two choices that are both defensibly correct
- answer length that makes the correct option obvious
- distractors that test grammar instead of reading

## 8. MVP Bank Size

Recommended MVP production target:

- `60` generated candidate passages
- `300` generated candidate items
- `40` approved launch passages
- `200` approved launch items

Per band:

- generate `15` candidate passages
- approve at least `10` launch passages
- keep weaker candidates for revision or retirement

This gives the adaptive test enough variety while keeping human review realistic.

## 9. AI-Assisted Content Generation

AI should produce first drafts. The system and teachers decide what enters the assessment bank.

The generation pipeline should be:

1. select target parameters
2. generate passage draft
3. run automatic passage validation
4. generate items from approved passage draft
5. run automatic item validation
6. send to human review
7. approve, revise, or retire

### 9.1 Target Parameters

Each generation job should start with explicit target parameters:

```json
{
  "target_band": "800L-950L",
  "anchor_lexile": 875,
  "cefr": "A2+/B1-",
  "genre": "informational",
  "topic": "school technology",
  "word_count": 360,
  "skills_required": [
    "main_idea",
    "detail",
    "inference",
    "vocabulary_context",
    "structure_author_purpose"
  ]
}
```

### 9.2 Passage Generation Prompt Shape

Passage generation should ask for original assessment text only.

It should not ask for items in the same call.

Prompt shape:

```text
You are creating original English reading assessment passages for Chinese Grade 6-8 students.

Target:
- Estimated reading band: 800L-950L
- CEFR: A2+/B1-
- Genre: informational
- Topic: school technology
- Word count: 330-390 words
- Audience: Chinese middle school students
- Purpose: reading assessment, not reading practice

Requirements:
- Write an original passage. Do not adapt copyrighted text.
- Use natural, age-appropriate English.
- Avoid politics, violence, romance, religion, adult topics, and culturally obscure references.
- Keep paragraphs clear.
- Include enough information to support main idea, detail, inference, vocabulary-in-context, and author-purpose questions.
- Do not include questions yet.

Return JSON only:
{
  "title": "...",
  "body_text": "...",
  "estimated_band": "800L-950L",
  "cefr": "A2+/B1-",
  "genre": "informational",
  "topic": "school technology",
  "word_count": 0,
  "difficulty_notes": ["..."]
}
```

### 9.3 Item Generation Prompt Shape

Item generation should use a validated passage as input.

Prompt shape:

```text
Create 5 multiple-choice reading assessment items for this passage.

Rules:
- Exactly 4 choices per question.
- Exactly 1 correct answer.
- Distractors must be plausible.
- Every answer must be supported by the passage.
- Do not ask grammar questions.
- Do not ask questions answerable without reading the passage.
- Include evidence from the passage.
- Include rationale for every option.

Required skills:
1. main_idea
2. detail
3. inference
4. vocabulary_context
5. structure_author_purpose

Difficulty offsets:
- easy: -75L
- medium: 0L
- hard: +75L

Passage anchor lexile: 875

Return JSON only:
{
  "items": [
    {
      "skill": "main_idea",
      "difficulty_label": "medium",
      "difficulty_offset": 0,
      "estimated_item_lexile": 875,
      "question_text": "...",
      "choices": {"A": "...", "B": "...", "C": "...", "D": "..."},
      "correct_choice": "B",
      "evidence": "...",
      "rationales": {"A": "...", "B": "...", "C": "...", "D": "..."}
    }
  ]
}
```

### 9.4 Automatic Validation

Passage validation should check:

- JSON shape is valid
- word count is within range
- genre is one of the allowed genres
- topic is age appropriate
- no prohibited sensitive content
- paragraph count is reasonable
- sentence length and lexical difficulty roughly match the band
- passage is original according to available duplicate checks

Item validation should check:

- exactly `5` items
- required skills are all present
- exactly `4` choices per item
- correct choice exists
- each item has evidence
- each option has a rationale
- item difficulty fields are valid
- estimated item difficulty matches passage anchor plus offset
- no item can be answered without the passage
- no answer is exposed by option length or wording pattern

Automatic validation can reject drafts or send them to `needs_revision`.

### 9.5 Human Review

Teachers should approve assessment content before launch.

Human review should answer:

1. Is the passage difficulty appropriate for the band?
2. Is the passage suitable for Chinese Grade 6-8 students?
3. Does each item have exactly one correct answer?
4. Are distractors plausible?
5. Does every inference item have textual support?

Content states:

- `draft_generated`
- `auto_validated`
- `needs_revision`
- `approved`
- `retired`

## 10. Estimate Algorithm

The first estimator should be transparent and deterministic.

Name:

```text
Lexile-like Reading Estimate v0.1
```

### 10.1 Inputs

The estimator should use:

- `estimated_item_lexile`
- `correct`
- `skill`
- `time_seconds`
- `passage_anchor_lexile`
- passages completed
- total duration

### 10.2 Validity Checks

Before estimating, flag:

- total time below `10` minutes
- many items answered in less than `5` seconds
- fewer than `3` completed passages
- simple items missed while harder items are repeatedly correct
- very high accuracy on all top-band items
- very low accuracy on all bottom-band items

Validity flags should affect confidence and report wording.

### 10.3 Difficulty Buckets

Group item results by `100L` buckets:

- `500L-599L`
- `600L-699L`
- `700L-799L`
- `800L-899L`
- `900L-999L`
- `1000L-1099L`

Bucket interpretation:

- `85%+`: mastered
- `70%-84%`: readable independently
- `50%-69%`: challenge zone
- below `50%`: too difficult

### 10.4 Range Estimate

First version rule:

```text
lower_bound = highest stable mastered/readable level - 50L
upper_bound = first clear challenge or too-difficult level + 50L
```

If performance is stable, produce a narrower range.

If performance is noisy, produce a wider range and lower confidence.

### 10.5 Practice Range

Practice range should be lower than or equal to the estimated range.

Recommended rule:

```text
practice_lower = estimated_lower - 70L
practice_upper = estimated_upper - 60L
```

Clamp to the product range unless the student is outside the target range.

### 10.6 Time Handling

Time should affect:

- `Reading Fluency` note
- confidence
- validity flags

Time should not directly lower the core comprehension estimate.

Examples:

- correct and slow: comprehension is adequate, fluency needs practice
- wrong and slow: text was likely too hard
- correct and extremely fast: possible guessing, lower confidence
- wrong and extremely fast: possible rushing

## 11. Domain Scores

The report should include domain scores:

- `main_idea`
- `detail`
- `inference`
- `vocabulary_context`
- `structure_author_purpose`

First version scoring should use difficulty-weighted accuracy.

Difficulty weights:

- `500L-650L`: `1.0`
- `650L-800L`: `1.2`
- `800L-950L`: `1.4`
- `950L-1100L`: `1.6`

Formula:

```text
skill_score = weighted_correct_points / weighted_possible_points * 100
```

Scores should be rounded to whole numbers for reports.

## 12. Confidence Rules

Confidence should be one of:

- `High`
- `Medium`
- `Low`

### 12.1 High Confidence

Use when:

- `4-5` passages completed
- at least `3` difficulty bands covered
- accuracy decreases reasonably as difficulty rises
- no major timing or response pattern flags

### 12.2 Medium Confidence

Use when:

- `3-4` passages completed
- `2-3` difficulty bands covered
- performance is mostly reasonable but somewhat uneven

### 12.3 Low Confidence

Use when:

- too few passages were completed
- timing is abnormal
- response pattern is inconsistent
- student is clearly outside the target range

## 13. Report Design

The report should be useful for instruction.

Recommended report payload:

```json
{
  "estimated_range": "720L-860L",
  "practice_range": "650L-800L",
  "cefr_estimate": "A2+",
  "confidence": "Medium",
  "summary": "The student can understand most A2+ texts independently. B1-level passages are possible with support.",
  "domain_scores": {
    "main_idea": 82,
    "detail": 88,
    "inference": 61,
    "vocabulary_context": 70,
    "structure_author_purpose": 66
  },
  "strengths": [
    "Locates details accurately.",
    "Understands main ideas in school and daily-life texts."
  ],
  "needs_practice": [
    "Inference questions.",
    "Vocabulary meaning from context.",
    "Longer informational passages."
  ],
  "recommendations": [
    "Read 650L-800L texts independently.",
    "Use 800L-900L texts with teacher support."
  ],
  "validity_flags": []
}
```

### 13.1 Above Target Range

If a student performs strongly on `950L-1100L` items:

```text
Above Target Range
The student performed strongly on 950L-1100L items.
Recommendation: Take the advanced version covering 1000L-1300L.
```

### 13.2 Below Target Range

If a student struggles with `500L-650L` items:

```text
Below Target Range
The student struggled with 500L-650L items.
Recommendation: Use the foundation version covering 300L-650L.
```

## 14. Data Model

The reading module should follow the existing writing backend pattern while keeping content, responses, estimate, and report separate.

### 14.1 `reading_passages`

```text
id
passage_code
title
body_text
band_label
anchor_lexile
cefr_level
genre
word_count
topic
metadata_json
active
created_at
updated_at
```

### 14.2 `reading_items`

```text
id
passage_id
item_order
skill
difficulty_label
difficulty_offset
estimated_item_lexile
question_text
choices_json
correct_choice
rationales_json
active
created_at
updated_at
```

### 14.3 `reading_assessments`

```text
id
student_id
grade_level
status
target_range
started_at
completed_at
duration_sec
current_anchor_lexile
passages_completed
created_at
updated_at
```

### 14.4 `reading_assessment_passages`

```text
id
assessment_id
passage_id
sequence_number
anchor_lexile
started_at
completed_at
time_spent_sec
accuracy
created_at
updated_at
```

### 14.5 `reading_responses`

```text
id
assessment_id
passage_id
item_id
selected_choice
is_correct
time_spent_sec
created_at
```

### 14.6 `reading_estimates`

```text
id
assessment_id
estimated_lower_lexile
estimated_upper_lexile
practice_lower_lexile
practice_upper_lexile
cefr_estimate
confidence_label
validity_flags_json
domain_scores_json
report_payload_json
created_at
```

## 15. API Design

Routes should live under `/api/v1/reading`.

### 15.1 Create Assessment

```http
POST /api/v1/reading/assessments
```

Request:

```json
{
  "student_id": "stu_001",
  "grade_level": 7
}
```

Response:

```json
{
  "assessment_id": "rass_abc123",
  "status": "in_progress",
  "current_anchor_lexile": 800
}
```

### 15.2 Get Next Passage

```http
GET /api/v1/reading/assessments/{assessment_id}/next
```

Response should include passage text and item choices. It must not include correct answers.

### 15.3 Submit Passage Responses

```http
POST /api/v1/reading/assessments/{assessment_id}/responses
```

Request:

```json
{
  "passage_id": "rp_001",
  "time_spent_sec": 420,
  "responses": [
    {
      "item_id": "ri_001",
      "selected_choice": "B",
      "time_spent_sec": 45
    }
  ]
}
```

Response:

```json
{
  "status": "continue",
  "passage_accuracy": 0.8,
  "next_anchor_lexile": 850,
  "passages_completed": 2
}
```

### 15.4 Complete Assessment

```http
POST /api/v1/reading/assessments/{assessment_id}/complete
```

Response:

```json
{
  "estimated_range": "720L-860L",
  "practice_range": "650L-800L",
  "cefr_estimate": "A2+",
  "confidence": "Medium",
  "domain_scores": {
    "main_idea": 82,
    "detail": 88,
    "inference": 61,
    "vocabulary_context": 70,
    "structure_author_purpose": 66
  }
}
```

### 15.5 Get Report

```http
GET /api/v1/reading/assessments/{assessment_id}/report
```

Returns the persisted `report_payload_json`.

## 16. Service Boundaries

Recommended module layout:

```text
backend/pet_reading_api/__init__.py
backend/pet_reading_api/seed_data.py
backend/pet_reading_api/storage.py
backend/pet_reading_api/service.py
backend/pet_reading_api/adaptive.py
backend/pet_reading_api/estimator.py
backend/pet_reading_api/content_generation.py
backend/pet_reading_api/validators.py
```

Responsibilities:

- `adaptive.py`: select next passage anchor and choose eligible passage
- `estimator.py`: estimate range, confidence, domain scores, and validity flags
- `content_generation.py`: generate passage and item drafts through an LLM
- `validators.py`: validate generated content before human review
- `service.py`: orchestrate assessment API behavior
- `storage.py`: manage SQLite schema and persistence

Keep these flows separate:

- offline content generation
- human content review
- online student assessment
- deterministic estimate calculation
- report assembly

## 17. Calibration Plan

The first version starts with internal anchors. The reliable score comes from calibration.

Calibration data sources:

- student responses in this system
- teacher review of item quality
- optional Star Reading official results for the same students

Calibration table shape:

```text
Our v0.1 estimate     Star Reading median
650L-800L             720L
750L-900L             830L
850L-1000L            940L
950L-1100L            1030L
```

Use calibration to adjust:

- passage `anchor_lexile`
- item `estimated_item_lexile`
- final range mapping
- confidence rules

## 18. Success Metrics

Assessment quality:

- at least `80%` of completed tests finish in `20-30` minutes
- at least `90%` of valid tests complete `3+` passages
- fewer than `10%` of tests are invalid due to timing or response pattern
- teachers agree with the reported range in at least `70%` of early cases

Content quality:

- every launch passage has human approval
- every item has one correct answer and evidence
- every band has at least `10` approved passages
- every skill has enough items across all bands

Calibration quality:

- collect Star Reading comparison data where possible
- review error patterns monthly
- revise anchors for passages with abnormal performance

## 19. Risks

### 19.1 AI Content Quality

AI-generated passages may look fluent but contain weak assessment logic.

Mitigation:

- split passage generation and item generation
- run automatic validation
- require human approval before launch

### 19.2 False Precision

Users may treat the estimate as official or exact.

Mitigation:

- label the result as `Lexile-like`
- output ranges instead of exact numbers
- show confidence and validity notes

### 19.3 Weak Calibration

Initial anchors may be biased.

Mitigation:

- store item-level response data
- compare to official Star Reading results when available
- revise anchors as data accumulates

### 19.4 Test Fatigue

Long passages or too many items may exceed 30 minutes.

Mitigation:

- use passage-level stop conditions
- cap at `5` passages
- track duration and fluency separately

## 20. Open Decisions

The following decisions should be made before implementation:

1. Whether to seed the first passage bank directly in SQLite or from JSON fixtures.
2. Whether content review happens in an internal admin UI or via spreadsheet-style review first.
3. Whether the first launch includes only generated content or mixes generated content with manually written anchor passages.
4. Whether the student-facing report should show both English and Chinese explanations.

## 21. Recommended MVP

Build the first version in this order:

1. Define JSON schema for passages and items.
2. Generate `60` candidate passages and `300` candidate items.
3. Build automatic validators.
4. Human-review and approve `40` passages.
5. Implement assessment tables and reading service.
6. Implement passage-level adaptive selection.
7. Implement deterministic `Lexile-like Reading Estimate v0.1`.
8. Generate the student report payload.
9. Run an internal pilot with Grade 6-8 students.
10. Calibrate anchors using student response data and any available official Star Reading results.

