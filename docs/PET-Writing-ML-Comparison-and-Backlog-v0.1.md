# PET Writing ML Comparison and Technical Backlog v0.1

## 1. Purpose

This document does two jobs:

1. compare the ML and scoring design in `NoteRx` with the current PET Writing scorer direction
2. turn the useful overlap into a concrete technical backlog for the PET Writing system

The goal is to borrow the right engineering ideas without importing the wrong problem definition.

## 2. Executive Summary

`NoteRx` and `PET Writing` share an important architectural philosophy:

- extract structured signals first
- produce stable machine scores first
- let generative models explain and extend the result later

But the actual ML problem is different:

- `NoteRx` predicts **content performance potential**
- `PET Writing` must predict **rubric-aligned exam writing quality**

So the parts worth borrowing are mainly:

- the separation of `offline research artifacts` from `online runtime scoring`
- the use of `deterministic pre-score` before deeper generative analysis
- the idea of `baseline comparison`
- the emphasis on `stable score first, LLM second`

The parts that should **not** be copied directly are:

- multi-agent debate as the main scoring path
- hard-coded scoring parameters duplicated in runtime
- business engagement metrics replacing rubric labels

## 3. System Comparison

### 3.1 Problem Definition

| Dimension | NoteRx | PET Writing |
| --- | --- | --- |
| Product goal | diagnose how a Xiaohongshu note may perform | diagnose whether a student can pass PET Writing and how to improve |
| Target variable | engagement / viral potential proxy | rubric-aligned writing score |
| Score meaning | business performance likelihood | exam quality against rubric |
| Main user action after score | optimize title/content for reach | rewrite essay for better PET performance |

### 3.2 Data and Labels

| Dimension | NoteRx | PET Writing |
| --- | --- | --- |
| Main raw data | real social posts + comments + screenshots/videos | prompt + student essay + timing + rubric labels |
| Ground truth style | observational outcome labels such as engagement and viral rate | human rubric scores on 4 dimensions |
| Label quality risk | content performance is noisy and platform-dependent | teacher consistency and rubric agreement are the main risks |
| Best label source | historical platform data | double-rated teacher scoring with adjudication |

### 3.3 Feature Extraction

| Dimension | NoteRx | PET Writing |
| --- | --- | --- |
| Text features | title length, numbers, hooks, emotion words, readability, info density | word count, paragraph count, task coverage, grammar error rate, lexical diversity, sentence variety |
| Visual features | saturation, text ratio, face presence, image/video analysis | not needed in Writing MVP |
| Prompt/task metadata | content category | prompt id, task type, content points, target word count |
| Engine style | rules + content heuristics | rules + rubric-oriented linguistic features |

### 3.4 Model Form

| Dimension | NoteRx | PET Writing |
| --- | --- | --- |
| Current runtime scorer | deterministic weighted scoring model | heuristic rubric scorer or trainable dimension artifact |
| Trainable ML form | regression-derived weights, then hand-shaped runtime scoring | supervised per-dimension scorer trained from labeled essays |
| Target heads | business dimensions such as title/content/visual/growth | `task_achievement`, `organization_coherence`, `grammar_control`, `lexical_range_accuracy` |
| Confidence | implicit or downstream | explicit confidence at overall and dimension level |

### 3.5 LLM Role

| Dimension | NoteRx | PET Writing |
| --- | --- | --- |
| LLM role | multi-agent diagnosis, debate, optimization content generation | grounded explanation, sentence suggestions, rewrite task, optional bounded refinement |
| Can LLM decide official score? | partially involved in explanation stack, but stable scores are separated | should not be the sole judge |
| Best use | rich interpretation for creative content | teaching feedback and rewrite guidance |

## 4. NoteRx ML Details

### 4.1 What NoteRx Actually Uses

`NoteRx` is not a classic end-to-end supervised scoring model. It is closer to a `research-derived deterministic scoring engine`.

Its ML and data stack includes:

- `descriptive statistics`
- `Spearman correlation`
- `linear regression`
- `K-Means clustering`
- `PCA visualization`
- `Kruskal-Wallis tests`
- rule-based feature extraction
- deterministic score functions based on learned ranges and weights

This can be seen in:

- research analysis pipeline: `scripts/research/03_traditional_analysis.py`
- scoring parameter builder: `scripts/research/08_build_scoring_model.py`
- validation script: `scripts/research/10_validate_model.py`
- runtime pre-score: `backend/app/agents/research_data.py`

### 4.2 NoteRx Runtime Scoring Pattern

Runtime scoring in NoteRx works like this:

1. extract structured features from title/content/image/video
2. compare them against category baseline stats
3. compute a deterministic `Model A` pre-score
4. blend that score into stable dimensions
5. let agents and judge produce richer diagnosis and optimization

This is an important pattern for us because it keeps the product responsive and the score explainable.

### 4.3 What NoteRx Is Best At

- turning offline research into online scoring parameters
- baseline comparison against category norms
- separating stable score from generative explanation
- using a quick pre-score to improve product responsiveness

### 4.4 What NoteRx Is Not Solving

- rubric-based educational scoring
- multi-rater agreement
- confidence-triggered review workflow
- per-dimension supervised essay scoring
- calibration against human exam raters

## 5. PET Writing ML Details

### 5.1 Current PET Writing State

The current PET Writing stack already has the right skeleton:

- feature extraction in `backend/pet_writing_api/features.py`
- hybrid runtime pipeline in `backend/pet_writing_api/pipeline.py`
- trainable scorer artifact in `backend/pet_writing_api/trainable_scorer.py`
- report persistence and model run audit in `backend/pet_writing_api/service.py`

### 5.2 Current Feature Set

The current feature set includes:

- `word_count`
- `paragraph_count`
- `task_coverage`
- `grammar_error_rate`
- `lexical_diversity`
- `sentence_variety`
- `off_topic_risk`
- `connectors`
- `connector_density`
- `avg_sentence_length`
- `long_sentence_ratio`
- `within_target_word_count`
- `content_hits`
- `missing_content_count`
- `repeated_word_count`
- `lowercase_sentence_starts`
- `time_spent_min`
- `task_type_email`
- `task_type_article`

### 5.3 Current Model Form

The current trainable scorer is:

- a per-dimension supervised baseline
- implemented as pure-Python ridge-style regression
- exported as a JSON artifact with weights, normalization stats, and validation summary

This is a stronger educational scoring foundation than NoteRx already, because it is rubric-first.

### 5.4 Current Evaluation Style

The current scorer already tracks:

- `MAE`
- `RMSE`
- `within_one`

The next evaluation upgrades should be:

- `Quadratic Weighted Kappa`
- prompt-split validation
- double-rater agreement comparison
- review-flag precision/recall

## 6. Direct ML Detail Comparison

### 6.1 Algorithms

| Area | NoteRx | PET Writing Current | PET Writing Recommended Next |
| --- | --- | --- | --- |
| exploratory statistics | Spearman, descriptive stats, Kruskal-Wallis, PCA | minimal so far | add dataset audit + prompt-split analysis |
| baseline model | deterministic range scoring using regression-derived weights | heuristic rubric scorer | keep as fallback only |
| supervised learner | not the main runtime core | ridge-style per-dimension regression | LightGBM / XGBoost / CatBoost |
| deep text model | not central | not yet | DeBERTa or RoBERTa multi-task scorer |
| clustering | K-Means | none | optional for dataset profiling only |
| calibration | mostly implicit | confidence heuristic from validation MAE | explicit calibration layer |

### 6.2 Inputs

| Area | NoteRx | PET Writing |
| --- | --- | --- |
| raw text input | title + content | prompt + essay |
| metadata input | category, tags, image count, media data | prompt type, content points, target word count, time spent |
| derived features | title hooks, readability, tag strategy, cover features | task coverage, grammar signals, lexical diversity, organization signals |
| labels | engagement outcome proxy | human rubric scores |

### 6.3 Outputs

| Area | NoteRx | PET Writing |
| --- | --- | --- |
| primary score | total performance score | total PET writing score |
| dimension scores | content / visual / growth / user reaction | 4 rubric dimensions |
| confidence | weakly surfaced | explicit overall and dimension confidence |
| review flag | not central | should become a first-class output |
| generated output | optimized content, comments, debate summary | strengths, priority issues, sentence suggestions, rewrite task |

### 6.4 Engineering Boundary

| Question | NoteRx | PET Writing Recommendation |
| --- | --- | --- |
| should LLM own the final score? | no, stable score is separated | definitely no |
| should runtime scoring be deterministic if the input is identical? | yes, explicitly emphasized | yes, for official score path |
| should research artifacts be versioned? | yes, but runtime duplication exists | yes, and runtime should load a single artifact source |
| should there be a pre-score path? | yes | yes |

## 7. What We Can Reuse Conceptually

### 7.1 Baseline Profile Layer

Borrow the NoteRx idea of `category baseline stats`, but adapt it to writing:

- average word count by prompt type
- high-score connector density range
- typical high-score paragraph count
- common missing content points by prompt
- average task coverage by readiness band

Recommended name:

- `writing_baseline_profiles`

### 7.2 Instant Pre-Score

Borrow the NoteRx idea of a very fast `pre-score` endpoint:

- use deterministic rules or current artifact
- return draft-level preview score in under one second
- use it for draft comparison and UI responsiveness

### 7.3 Offline Research / Online Runtime Separation

Borrow the NoteRx split between:

- offline analysis scripts
- runtime scoring services

For PET Writing, this should become:

- `scripts/training/*`
- `scripts/eval/*`
- `output/models/*`
- runtime API loading a single model artifact

### 7.4 Baseline Comparison UI

Borrow the UI concept, not the exact metrics:

- compare a student essay against high-score PET essays
- compare current essay against target band
- compare draft 1 versus draft 2

## 8. What We Should Not Reuse Directly

### 8.1 Multi-Agent Debate As Core Scoring

For educational scoring, multi-agent debate is too noisy for the official scoring path.

Better use cases:

- low-confidence review assist
- teacher QA assistant
- rich coaching mode outside the official score

### 8.2 Hard-Coded Model Parameters In Multiple Places

NoteRx duplicates scoring parameters across research and runtime. For PET Writing, this would create drift.

Recommended rule:

- one trained artifact
- one loader
- one version id
- no duplicated score parameters in prompts or service code

### 8.3 Outcome Metrics As Score Labels

NoteRx can optimize for content performance. PET Writing cannot use external popularity or engagement proxies.

PET Writing must stay anchored to:

- prompt completion
- organization
- grammar
- vocabulary

## 9. Technical Backlog

## 9.1 P0 — Immediate

### P0.1 Add explicit review outputs

- add `needs_review`
- add `review_reason_codes`
- trigger when confidence is low or score pattern looks unusual

Why:

- this is the cleanest boundary between machine score and human override

### P0.2 Add `writing_baseline_profiles`

- store per-task and per-prompt distributions
- expose them in internal analysis first
- later surface selected baseline comparisons in report UI

Why:

- this is the most valuable concept to borrow from NoteRx

### P0.3 Add a fast `pre-score` endpoint

- score current text using the current artifact or deterministic fallback
- do not wait for full feedback generation
- use it for rewrite and before/after comparison

Why:

- improves product responsiveness and supports the rewrite loop

### P0.4 Make artifact loading the single official scorer source

- remove any future temptation to duplicate params in multiple modules
- keep runtime score logic centered on `TrainableScorerArtifact`

Why:

- avoids research/runtime drift

### P0.5 Strengthen validation scripts

- add prompt-level split evaluation
- add per-dimension reports
- save validation summaries alongside the model

Why:

- educational scoring needs stronger evaluation discipline than NoteRx

## 9.2 P1 — Near-Term

### P1.1 Expand grammar-oriented features

- `spelling_error_rate`
- `verb_tense_error_count`
- `article_error_count`
- richer sentence well-formedness signals

Why:

- this is where the current PET scorer is still thin

### P1.2 Add calibration

- score bin remapping
- isotonic-style calibration later when dependencies are available
- calibrated readiness thresholds

Why:

- stable educational scoring needs calibrated outputs, not just raw predictions

### P1.3 Add scorer review dashboard

- low-confidence queue
- scorer artifact version
- human override vs model score delta
- most common review reasons

Why:

- connects training and operations

### P1.4 Add dataset versioning

- dataset id
- label schema version
- prompt set version
- artifact training summary

Why:

- makes experiments repeatable

## 9.3 P2 — Mid-Term

### P2.1 Move from ridge baseline to gradient-boosted tree models

- LightGBM
- XGBoost
- CatBoost

Why:

- likely strongest next step on structured rubric features

### P2.2 Add transformer text scorer

- `prompt + essay` encoder
- shared encoder
- four task heads

Why:

- needed for stronger semantic understanding of task achievement and coherence

### P2.3 Add structured + text fusion

- combine feature model outputs and transformer outputs
- keep confidence and calibration on top

Why:

- likely best production-quality scorer architecture

### P2.4 Add active learning loop

- sample low-confidence essays
- send to teacher review
- feed back into the next training round

Why:

- best way to improve label efficiency

## 9.4 P3 — Later

### P3.1 Multi-agent review assist

- not part of official scoring
- only for difficult essays or teacher support

### P3.2 Prompt drift and rubric drift monitoring

- monitor performance by prompt family
- detect shifts after rubric updates

### P3.3 Teacher-side disagreement modeling

- track rater disagreement
- use it for uncertainty modeling

## 10. Recommended Build Order

If we continue from the current codebase, the most sensible order is:

1. add `needs_review` and `review_reason_codes`
2. add `pre-score`
3. add `writing_baseline_profiles`
4. expand feature set for grammar and task relevance
5. strengthen validation scripts
6. move to boosted trees
7. add calibration
8. add transformer scorer
9. add fusion

## 11. Bottom Line

The best lesson from `NoteRx` is not its multi-agent layer.

The best lesson is this:

`research artifacts should produce a stable, explainable score first; generative AI should explain, compare, and improve that score afterward.`

That lesson transfers extremely well to PET Writing.
