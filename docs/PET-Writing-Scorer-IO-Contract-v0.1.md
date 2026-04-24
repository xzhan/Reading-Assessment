# PET Writing Scorer Input / Output Contract v0.1

## 1. Goal

This document defines one shared field contract for the PET Writing scorer so that:

- product can collect the right data
- backend can expose stable APIs
- ML training can consume consistent samples
- LLM feedback stays grounded in scorer evidence
- reviewers can calibrate or override low-confidence cases

The goal is to avoid having one schema for the app, another for training, and a third one for reporting.

## 2. Recommended Structure

There are three reasonable ways to organize scorer fields:

### Option A. One flat master table

- easiest to scan at first
- hard to maintain
- mixes raw input, labels, model outputs, and feedback together

### Option B. Lifecycle-based contract

- split fields by stage: prompt, submission, derived features, labels, scores, feedback, audit
- easiest for product, backend, and ML to share
- works well with the current repo structure

### Option C. Separate train-only and inference-only schemas

- clean for research work
- creates duplication and mapping work
- easy to drift over time

### Recommendation

Use **Option B**, with one canonical scorer contract broken into layers:

1. `prompt metadata`
2. `submission raw input`
3. `derived feature package`
4. `human label package`
5. `model score output`
6. `student feedback output`
7. `review and audit output`

That is the contract used in this document.

## 3. Field Status Legend

- `Current`: already present in the repo or active response payload
- `Recommended`: not required for MVP runtime, but strongly recommended for training quality
- `Future`: useful later, but can wait

## 4. Master Matrix

| Layer | Purpose | Main Producer | Main Consumer | Current Persistence |
| --- | --- | --- | --- | --- |
| `prompt` | define task requirements and scoring context | content ops | scorer, trainer, report | `writing_prompts` |
| `student_context` | learner metadata and segmentation | product/backend | analytics, training slices | `students` |
| `attempt` | session-level state | backend | history, rewrite flow | `writing_attempts` |
| `draft` | mutable writing workspace | client/backend | autosave UI | `writing_drafts` |
| `submission` | immutable essay for scoring | backend | scorer, report, review | `writing_submissions` |
| `derived_features` | structured model signals | feature engine | scorer, LLM grounding | `writing_scores.feature_signals_json` plus `scoring_evidence_json` |
| `human_labels` | gold labels for training and QA | teachers/reviewers | trainer, calibration | `human_reviews` and JSONL training files |
| `score_output` | official ML score result | scorer pipeline | report UI, analytics | `writing_scores` |
| `feedback_output` | student-facing explanation | local rules + LLM | report UI | `writing_feedback` and `writing_sentence_feedback` |
| `audit_output` | model trace and failure diagnosis | pipeline | ops, QA, ML | `model_runs` |

## 5. Prompt Metadata Fields

These fields define what the student was asked to do. They are required for correct `Task Achievement` scoring.

| Field | Type | Status | Required For | Source | Notes |
| --- | --- | --- | --- | --- | --- |
| `prompt_id` | `string` | Current | scoring, training, reporting | backend/content ops | stable unique id such as `wp_pet_email_001` |
| `prompt_code` | `string` | Current | admin ops | content ops | human-readable prompt code |
| `task_type` | `enum` | Current | scoring, training | content ops | currently `email` or `article` |
| `title` | `string` | Current | scoring, reporting | content ops | short prompt title |
| `instructions` | `string` | Current | scoring, training, reporting | content ops | full writing instruction text |
| `target_word_count_min` | `integer` | Current | scoring | content ops | used for coverage and length adequacy |
| `target_word_count_max` | `integer` | Current | scoring | content ops | used for coverage and length adequacy |
| `recommended_time_sec` | `integer` | Current | reporting, analytics | content ops | expected completion time |
| `rubric_version` | `string` | Current | scoring, training | ML/content ops | lets you compare scores across rubric changes |
| `content_points` | `array<string or array<string>>` | Current | scoring, training | content ops | stored inside `metadata_json`; current feature engine uses grouped keywords |
| `target_level` | `string` | Recommended | training, analytics | content ops | for example `B1` |
| `exam` | `string` | Recommended | analytics | content ops | recommended constant `PET` |
| `language` | `string` | Future | analytics | content ops | useful if later supporting multilingual UI |
| `prompt_tags` | `array<string>` | Future | analytics, training slices | content ops | example: `invitation`, `school_life` |

## 6. Student Context Fields

These should not drive the official score directly, but they are useful for segmentation, analytics, and fairness checks.

| Field | Type | Status | Required For | Source | Notes |
| --- | --- | --- | --- | --- | --- |
| `student_id` | `string` | Current | product flow, reporting | backend | internal student id |
| `external_ref` | `string` | Current | integrations | SIS/product | external platform id if needed |
| `display_name` | `string` | Current | reporting | product | student display name |
| `grade_level` | `string` | Current | analytics, training slices | product | example `G7` |
| `target_exam` | `string` | Current | analytics | product | currently defaults to `PET` |
| `locale` | `string` | Current | product ops | product | example `en-US` |
| `native_language` | `string` | Recommended | fairness analysis | product | should not be used for official score prediction |
| `learning_stage` | `string` | Recommended | analytics | product | example `foundation`, `exam-ready` |

## 7. Attempt, Draft, and Submission Fields

These fields separate a mutable writing session from the immutable essay that gets scored.

### 7.1 Attempt Fields

| Field | Type | Status | Required For | Source | Notes |
| --- | --- | --- | --- | --- | --- |
| `attempt_id` | `string` | Current | product flow, reporting | backend | one writing session |
| `student_id` | `string` | Current | reporting | backend | links to student |
| `prompt_id` | `string` | Current | scoring | backend | links to prompt |
| `status` | `enum` | Current | product flow | backend | example: started, submitted, feedback_generated |
| `current_draft_number` | `integer` | Current | rewrite flow | backend | mutable current draft counter |
| `latest_submission_id` | `string|null` | Current | rewrite flow, history | backend | latest scored submission |
| `review_status` | `enum` | Current | QA | scorer/reviewer | current runtime values are `not_required`, `required`, `reviewed`; `in_review` can be added later |
| `started_at` | `datetime` | Current | analytics | backend | session start |
| `completed_at` | `datetime|null` | Current | analytics | backend | session completion |

### 7.2 Draft Fields

| Field | Type | Status | Required For | Source | Notes |
| --- | --- | --- | --- | --- | --- |
| `draft_id` | `string` | Current | autosave | backend | mutable workspace snapshot |
| `attempt_id` | `string` | Current | autosave | backend | parent attempt |
| `draft_number` | `integer` | Current | rewrite flow | backend | draft index |
| `text_content` | `string` | Current | autosave | client | current essay text |
| `word_count` | `integer` | Current | UI hints | backend/client | autosave word count |
| `time_spent_sec` | `integer` | Current | analytics | client/backend | elapsed time so far |
| `saved_at` | `datetime` | Current | autosave | backend | last autosave time |

### 7.3 Submission Fields

| Field | Type | Status | Required For | Source | Notes |
| --- | --- | --- | --- | --- | --- |
| `submission_id` | `string` | Current | scoring, reporting | backend | immutable scored essay id |
| `attempt_id` | `string` | Current | reporting | backend | parent attempt |
| `draft_number` | `integer` | Current | rewrite flow | backend | usually `1` or `2` in MVP |
| `status` | `enum` | Current | scoring flow | backend | current processing state |
| `submitted_text` | `string` | Current | scoring, training | client/backend | exact essay text used for scoring |
| `word_count` | `integer` | Current | scoring, reporting | backend | immutable word count at submit time |
| `paragraph_count` | `integer` | Current | scoring, reporting | backend | immutable paragraph count |
| `time_spent_sec` | `integer` | Current | scoring, analytics | client/backend | final elapsed time |
| `pipeline_stage` | `string` | Current | ops | scorer | current backend stage |
| `submitted_at` | `datetime` | Current | reporting | backend | submit time |
| `processed_at` | `datetime|null` | Current | ops | scorer | completed processing time |
| `client_word_count` | `integer` | Recommended | QA | client | useful for client/server diff checks |
| `input_method` | `enum` | Future | analytics | product | typed, pasted, OCR, speech-to-text |

## 8. Canonical Online Scorer Input

This is the normalized payload the online scorer should conceptually receive after lookup and preprocessing.

```json
{
  "prompt": {
    "prompt_id": "wp_pet_email_001",
    "task_type": "email",
    "title": "Invite a friend to your club",
    "instructions": "Write an email to your friend...",
    "target_word_count_min": 100,
    "target_word_count_max": 140,
    "recommended_time_sec": 1200,
    "rubric_version": "pet-writing-v1",
    "content_points": ["which club", "why you like it", "invite your friend"]
  },
  "submission": {
    "submission_id": "sub_001",
    "attempt_id": "att_001",
    "student_id": "stu_001",
    "draft_number": 1,
    "submitted_text": "Dear Sam, ...",
    "time_spent_sec": 980,
    "word_count_client": 126
  }
}
```

## 9. Derived Feature Package

These fields are not human labels. They are machine-derived evidence used by the scorer and by grounded feedback.

### 9.1 Current Feature Signals

These are already produced in `/Users/xzhan/vibcoding/EnglishTest/backend/pet_writing_api/features.py`.

| Field | Type | Status | Used By | Meaning |
| --- | --- | --- | --- | --- |
| `word_count` | `integer` | Current | score, report | tokenized word count |
| `paragraph_count` | `integer` | Current | score, report | number of non-empty paragraphs |
| `task_coverage` | `float` | Current | score, feedback | ratio of content point groups matched |
| `grammar_error_rate` | `float` | Current | score, feedback | simple pattern-based sentence issue rate |
| `lexical_diversity` | `float` | Current | score | ratio of unique words to total words |
| `sentence_variety` | `float` | Current | score | variation in sentence lengths |
| `off_topic_risk` | `float` | Current | score, review | inverse proxy from low coverage |
| `connectors` | `integer` | Current | score | number of discourse markers detected |
| `connector_density` | `float` | Current | score | connectors per sentence |
| `avg_sentence_length` | `float` | Current | score | average words per sentence |
| `long_sentence_ratio` | `float` | Current | score | proportion of long sentences |
| `time_spent_sec` | `integer` | Current | analytics | elapsed time |

### 9.2 Current Evidence Fields

| Field | Type | Status | Used By | Meaning |
| --- | --- | --- | --- | --- |
| `sentence_count` | `integer` | Current | feedback, review | number of detected sentences |
| `within_target_word_count` | `boolean` | Current | score, feedback | whether length falls in target band |
| `content_hits` | `integer` | Current | score, feedback | matched content group count |
| `content_groups` | `array` | Current | review | prompt-side grouped targets |
| `missing_content_points` | `array<string>` | Current | feedback, review | uncovered required points |
| `repeated_words` | `array<string>` | Current | score, feedback | repeated words above threshold |
| `lowercase_sentence_starts` | `integer` | Current | score, feedback | count of lowercase sentence openings |

### 9.3 Current Feature Vector Fields

These are the actual structured inputs used by the trainable baseline scorer artifact.

| Field | Type | Status | Used By | Notes |
| --- | --- | --- | --- | --- |
| `word_count` | `float` | Current | trainable scorer | numeric |
| `paragraph_count` | `float` | Current | trainable scorer | numeric |
| `task_coverage` | `float` | Current | trainable scorer | numeric |
| `grammar_error_rate` | `float` | Current | trainable scorer | numeric |
| `lexical_diversity` | `float` | Current | trainable scorer | numeric |
| `sentence_variety` | `float` | Current | trainable scorer | numeric |
| `off_topic_risk` | `float` | Current | trainable scorer | numeric |
| `connectors` | `float` | Current | trainable scorer | numeric |
| `connector_density` | `float` | Current | trainable scorer | numeric |
| `avg_sentence_length` | `float` | Current | trainable scorer | numeric |
| `long_sentence_ratio` | `float` | Current | trainable scorer | numeric |
| `within_target_word_count` | `float` | Current | trainable scorer | `1.0` or `0.0` |
| `content_hits` | `float` | Current | trainable scorer | numeric |
| `missing_content_count` | `float` | Current | trainable scorer | derived count |
| `repeated_word_count` | `float` | Current | trainable scorer | derived count |
| `lowercase_sentence_starts` | `float` | Current | trainable scorer | numeric |
| `time_spent_min` | `float` | Current | trainable scorer | derived from seconds |
| `task_type_email` | `float` | Current | trainable scorer | one-hot feature |
| `task_type_article` | `float` | Current | trainable scorer | one-hot feature |

### 9.4 Recommended Additional Features

These are the best next fields to add if you want the ML scorer to improve.

| Field | Type | Status | Used By | Why It Matters |
| --- | --- | --- | --- | --- |
| `spelling_error_rate` | `float` | Recommended | grammar, lexical scoring | current pipeline lacks spelling-specific signal |
| `verb_tense_error_count` | `integer` | Recommended | grammar scoring | common PET weakness |
| `article_error_count` | `integer` | Recommended | grammar scoring | common PET weakness |
| `prompt_relevance_score` | `float` | Recommended | task achievement | stronger than keyword coverage only |
| `paragraph_balance_score` | `float` | Recommended | organization | better structure signal |
| `opening_strength_score` | `float` | Recommended | organization | useful for email/article openings |
| `closing_strength_score` | `float` | Recommended | task achievement, organization | useful for purpose completion |
| `type_token_ratio` | `float` | Future | lexical scoring | common lexical richness feature |
| `mtld` | `float` | Future | lexical scoring | more stable than plain TTR |
| `grammar_tool_error_breakdown` | `object` | Future | training, review | error categories for richer modeling |

## 10. Human Label Package

These are the gold labels. This is the most important section for training.

### 10.1 Minimum Gold Labels

| Field | Type | Status | Required For | Source | Notes |
| --- | --- | --- | --- | --- | --- |
| `labels.task_achievement` | `integer or float` | Current | training | teacher | rubric-aligned score from `0-5` |
| `labels.organization_coherence` | `integer or float` | Current | training | teacher | rubric-aligned score from `0-5` |
| `labels.grammar_control` | `integer or float` | Current | training | teacher | rubric-aligned score from `0-5` |
| `labels.lexical_range_accuracy` | `integer or float` | Current | training | teacher | rubric-aligned score from `0-5` |

### 10.2 Strongly Recommended Label Metadata

| Field | Type | Status | Required For | Source | Notes |
| --- | --- | --- | --- | --- | --- |
| `rater_id` | `string` | Current | training QA | teacher | already supported in labeling template `meta.rater_id` |
| `review_type` | `enum` | Current | QA | reviewer | example `calibration`, `appeal`, `qa` |
| `overall_score_human` | `float` | Recommended | QA, reporting | teacher | should equal or derive from the four dimensions |
| `label_comment` | `string` | Current | QA | reviewer | short rationale |
| `issue_tags` | `array<string>` | Recommended | training analysis | teacher | example `missing_content_point`, `tense_errors` |
| `second_rater_id` | `string` | Recommended | agreement checks | teacher | for double scoring |
| `second_rater_scores` | `object` | Recommended | agreement checks | teacher | second rubric set |
| `adjudicated_scores` | `object` | Recommended | gold dataset | lead reviewer | final agreed rubric score |
| `label_status` | `enum` | Recommended | dataset QA | reviewer | draft, approved, adjudicated |

### 10.3 Training JSONL Row

This is the recommended normalized row for model training.

```json
{
  "sample_id": "essay_001",
  "prompt_id": "wp_pet_email_001",
  "task_type": "email",
  "text": "Dear Sam, I joined the music club because...",
  "time_spent_sec": 960,
  "labels": {
    "task_achievement": 4,
    "organization_coherence": 4,
    "grammar_control": 4,
    "lexical_range_accuracy": 3
  },
  "meta": {
    "rater_id": "teacher_01",
    "grade_level": "G7",
    "notes": ["clear task coverage", "simple but correct language"],
    "issue_tags": ["limited_lexical_range"]
  },
  "external": {
    "external_scores": {
      "site_a_overall": 3.5
    }
  }
}
```

## 11. External and Auxiliary Fields

External data can help, but must not replace your gold labels.

| Field | Type | Status | Allowed Use | Notes |
| --- | --- | --- | --- | --- |
| `external_scores` | `object<string, float>` | Recommended | weak supervision, analysis | never treat as gold labels |
| `external_feedback_summary` | `array<string>` | Recommended | feature ideas, analysis | can help derive issue tags |
| `external_band_label` | `string` | Future | comparison only | often not PET-specific |
| `data_source_name` | `string` | Recommended | governance | track where outside data came from |
| `usage_rights` | `string` | Recommended | governance | internal, licensed, public, unknown |

## 12. Score Output Contract

This is the official scorer output. The LLM may explain it, but should not replace it.

There are currently **two score shapes** in the codebase:

- the **internal scorer payload** produced by the evaluation pipeline
- the **public report API wrapper** returned by the service layer

The first matters more for ML integration. The second matters more for frontend consumption.

### 12.1 Internal Scorer Payload Fields

| Field | Type | Status | Produced By | Notes |
| --- | --- | --- | --- | --- |
| `scores.overall` | `float` | Current | scorer | current product scale is `0-20` |
| `scores.readiness` | `enum` | Current | scorer | current labels: `below_target`, `borderline`, `on_track` |
| `scores.confidence` | `float` | Current | scorer | overall confidence |
| `scores.dimensions.task_achievement` | `float` | Current | scorer | official dimension score |
| `scores.dimensions.organization_coherence` | `float` | Current | scorer | official dimension score |
| `scores.dimensions.grammar_control` | `float` | Current | scorer | official dimension score |
| `scores.dimensions.lexical_range_accuracy` | `float` | Current | scorer | official dimension score |
| `scores.dimension_confidence.task_achievement` | `float` | Current | scorer | confidence per dimension |
| `scores.dimension_confidence.organization_coherence` | `float` | Current | scorer | confidence per dimension |
| `scores.dimension_confidence.grammar_control` | `float` | Current | scorer | confidence per dimension |
| `scores.dimension_confidence.lexical_range_accuracy` | `float` | Current | scorer | confidence per dimension |

### 12.2 Current Public Report API Wrapper Fields

These are returned today by `/api/v1/writing/submissions/{submission_id}/report`.

| Field | Type | Status | Produced By | Notes |
| --- | --- | --- | --- | --- |
| `scores.overall.score` | `float` | Current | service layer | overall score for UI |
| `scores.overall.max_score` | `float` | Current | service layer | currently `20` |
| `scores.overall.readiness` | `enum` | Current | service layer | readiness label |
| `scores.overall.confidence` | `float` | Current | service layer | overall confidence |
| `scores.dimensions.task_achievement.score` | `float` | Current | service layer | dimension score |
| `scores.dimensions.task_achievement.max_score` | `float` | Current | service layer | currently `5` |
| `scores.dimensions.task_achievement.confidence` | `float` | Current | service layer | dimension confidence |
| `scores.dimensions.organization_coherence.score` | `float` | Current | service layer | dimension score |
| `scores.dimensions.organization_coherence.max_score` | `float` | Current | service layer | currently `5` |
| `scores.dimensions.organization_coherence.confidence` | `float` | Current | service layer | dimension confidence |
| `scores.dimensions.grammar_control.score` | `float` | Current | service layer | dimension score |
| `scores.dimensions.grammar_control.max_score` | `float` | Current | service layer | currently `5` |
| `scores.dimensions.grammar_control.confidence` | `float` | Current | service layer | dimension confidence |
| `scores.dimensions.lexical_range_accuracy.score` | `float` | Current | service layer | dimension score |
| `scores.dimensions.lexical_range_accuracy.max_score` | `float` | Current | service layer | currently `5` |
| `scores.dimensions.lexical_range_accuracy.confidence` | `float` | Current | service layer | dimension confidence |

### 12.3 Review and Calibration Fields

| Field | Type | Status | Produced By | Notes |
| --- | --- | --- | --- | --- |
| `review.needs_review` | `boolean` | Current | scorer policy | now explicit in report and pre-score payloads |
| `review.review_status` | `string` | Current | scorer policy | current runtime values: `not_required`, `required`, `reviewed` |
| `review.review_reason_codes` | `array<string>` | Current | scorer policy | examples: `low_task_coverage`, `below_target_word_count`, `low_overall_confidence` |
| `calibrated` | `boolean` | Future | scorer | whether score went through calibration layer |
| `calibration_version` | `string` | Future | scorer | track calibration artifact version |

### 12.4 Recommended Official Response Shape

```json
{
  "submission_id": "sub_001",
  "attempt_id": "att_001",
  "draft_number": 1,
  "scores": {
    "overall": 14.0,
    "readiness": "borderline",
    "confidence": 0.81,
    "dimensions": {
      "task_achievement": 4.0,
      "organization_coherence": 3.0,
      "grammar_control": 3.0,
      "lexical_range_accuracy": 4.0
    },
    "dimension_confidence": {
      "task_achievement": 0.86,
      "organization_coherence": 0.79,
      "grammar_control": 0.77,
      "lexical_range_accuracy": 0.75
    }
  },
  "signals": {
    "word_count": 128,
    "paragraph_count": 3,
    "task_coverage": 0.84,
    "grammar_error_rate": 0.09
  },
  "evidence": {
    "within_target_word_count": true,
    "missing_content_points": [],
    "repeated_words": ["club"]
  },
  "review": {
    "needs_review": false,
    "review_status": "not_required",
    "review_reason_codes": []
  }
}
```

### 12.5 Stateless Pre-score Shape

`POST /api/v1/writing/prescore` returns the same score and review schema, but it is explicitly non-persistent.

```json
{
  "prompt": {
    "prompt_id": "wp_pet_email_001",
    "task_type": "email",
    "title": "Write an email to your English friend"
  },
  "scores": {
    "overall": 14.0,
    "readiness": "borderline",
    "confidence": 0.81
  },
  "review": {
    "needs_review": false,
    "review_status": "not_required",
    "review_reason_codes": []
  },
  "signals": {
    "word_count": 128,
    "task_coverage": 0.84
  },
  "persisted": false
}
```

## 13. Feedback Output Contract

These fields are student-facing. They should always be grounded in `signals`, `evidence`, and the essay text.

### 13.1 Current Feedback Fields

| Field | Type | Status | Produced By | Notes |
| --- | --- | --- | --- | --- |
| `feedback.strengths` | `array<string>` | Current | local rules or LLM | short positives tied to evidence |
| `feedback.priority_issues` | `array<string>` | Current | local rules or LLM | top `2-3` issues only |
| `feedback.sentence_suggestions` | `array<object>` | Current | local rules or LLM | sentence-level rewrite suggestions |
| `feedback.rewrite_task` | `object or string` | Current | local rules or LLM | next action for draft 2 |

### 13.2 Sentence Suggestion Fields

| Field | Type | Status | Produced By | Notes |
| --- | --- | --- | --- | --- |
| `issue_type` | `string` | Current | local rules or LLM | grammar, cohesion, task, lexical |
| `original` | `string` | Current | local rules or LLM | must quote real student text |
| `suggestion` | `string` | Current | local rules or LLM | improved version |
| `reason` | `string` | Current | local rules or LLM | short, student-friendly |
| `evidence` | `object` | Current | local rules or LLM | pattern, feature, or grounded note |

### 13.3 Recommended Rewrite Task Shape

| Field | Type | Status | Produced By | Notes |
| --- | --- | --- | --- | --- |
| `goal` | `string` | Recommended | local rules or LLM | one-sentence rewrite goal |
| `target_word_count` | `string` | Recommended | local rules or LLM | for example `120-140 words` |
| `must_fix` | `array<string>` | Recommended | local rules or LLM | top two required fixes |
| `stretch_goal` | `string` | Recommended | local rules or LLM | one optional improvement |

## 14. Audit and Model Run Fields

These fields make the system debuggable and keep score explanations honest.

| Field | Type | Status | Produced By | Notes |
| --- | --- | --- | --- | --- |
| `model_run_id` | `string` | Current | pipeline | internal run id |
| `submission_id` | `string` | Current | pipeline | parent submission |
| `stage` | `enum` | Current | pipeline | examples: `extract_features`, `predict_scores`, `llm_score_refinement`, `llm_feedback_generation` |
| `provider` | `string` | Current | pipeline | `internal`, `openai-compatible` |
| `model_name` | `string` | Current | pipeline | heuristic scorer name, artifact version, or LLM name |
| `model_version` | `string|null` | Current | pipeline | optional concrete model version |
| `input_payload_json` | `json` | Current | pipeline | request payload used by that stage |
| `output_payload_json` | `json` | Current | pipeline | raw output from that stage |
| `latency_ms` | `integer|null` | Current | pipeline | stage latency |
| `status` | `enum` | Current | pipeline | completed or failed |
| `error_message` | `string|null` | Current | pipeline | failure detail |
| `created_at` | `datetime` | Current | pipeline | audit timestamp |

## 15. Human Review Output

These fields let a teacher calibrate, confirm, or override the score.

| Field | Type | Status | Produced By | Notes |
| --- | --- | --- | --- | --- |
| `review_id` | `string` | Current | reviewer API | unique review event id |
| `submission_id` | `string` | Current | reviewer API | reviewed submission |
| `reviewer_id` | `string` | Current | reviewer API | teacher or lead reviewer |
| `review_type` | `enum` | Current | reviewer API | calibration, qa, appeal |
| `overall_score` | `float|null` | Current | reviewer API | optional explicit overall |
| `dimension_scores_json` | `json` | Current | reviewer API | reviewed dimension set |
| `comment` | `string|null` | Current | reviewer API | rationale note |
| `created_at` | `datetime` | Current | reviewer API | review timestamp |
| `final_resolution` | `enum` | Recommended | review workflow | confirmed, adjusted, escalated |

## 16. Recommended Boundaries

To keep the system clean, each layer should own only a narrow responsibility:

- `prompt` owns task definition
- `submission` owns the immutable essay and timing facts
- `derived_features` owns machine-observed signals only
- `human_labels` owns training truth
- `score_output` owns the official model decision
- `feedback_output` owns student-facing explanation
- `audit_output` owns traceability

Do not mix these responsibilities together.

## 17. What Should Not Be Used As Gold Labels

The following fields may be useful, but should not define the official training target:

- third-party essay site scores
- LLM free-form judgments without rubric trace
- teacher comments without dimension scores
- overall score only, without four dimension labels

## 18. Minimum Dataset Versions

If you want stable progress, keep three dataset shapes separate:

### 18.1 Online Scoring Dataset

- prompt metadata
- submission text
- time spent
- derived features

### 18.2 Gold Training Dataset

- online scoring dataset
- four human dimension labels
- rater metadata
- issue tags if available

### 18.3 Reporting Dataset

- online scoring dataset
- official scores
- confidence
- priority issues
- sentence suggestions
- rewrite task

## 19. Immediate Next Fields To Add

If we continue from the current codebase, these are the most valuable additions:

1. `needs_review`
2. `review_reason_codes`
3. `overall_score_human`
4. `issue_tags`
5. `prompt_relevance_score`
6. `spelling_error_rate`
7. `verb_tense_error_count`
8. `article_error_count`

## 20. Practical Recommendation

For the next phase of this project, use this document as the single source of truth for:

- labeling templates
- training JSONL generation
- scorer request normalization
- report response design
- future migration to stronger ML models

The key principle is simple:

`raw input`, `gold labels`, `model output`, and `LLM feedback` must stay separate.
