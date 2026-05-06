# PET-Writing-System

This workspace currently contains two active PET-oriented tracks:

- a reading worksheet generation pipeline
- a Writing MVP backend skeleton for scoring, feedback, and rewrite flow

## PET Writing MVP Backend

The Writing backend is a lightweight Python service built with the standard library, so it does not require installing FastAPI or other web frameworks before you can run it.

### What it supports today

- seeded PET Writing prompts for `email` and `article`
- creating writing attempts
- autosaving drafts
- submitting draft 1 and draft 2
- heuristic scoring across `4` dimensions
- deterministic review gating with `needs_review` and `review_reason_codes`
- internal review workflow for `review_required -> reviewed`
- grounded feedback and sentence-level suggestions
- rewrite task generation
- draft comparison
- student history lookup
- stateless `pre-score` preview before submission
- internal human review write endpoint
- optional OpenAI-compatible `LLM refinement` and `LLM feedback` stages

### Main entry point

`/Users/xzhan/vibcoding/EnglishTest/backend/app.py`

### Run the backend

```bash
python3 /Users/xzhan/vibcoding/EnglishTest/backend/app.py --host 127.0.0.1 --port 8000
```

### Enable hybrid LLM scoring and feedback

By default, the backend runs in local fallback mode and uses only the built-in scoring pipeline.

To enable LLM-backed stages, set:

```bash
export OPENAI_API_KEY="YOUR_KEY"
export OPENAI_MODEL="YOUR_MODEL"
export OPENAI_BASE_URL="https://api.openai.com/v1"
export PET_WRITING_LLM_MODE="feedback"
```

Supported `PET_WRITING_LLM_MODE` values:

- `off`: local scoring and local feedback only
- `feedback`: local scoring plus LLM-grounded feedback
- `hybrid`: local scoring plus LLM score refinement and LLM feedback

### Train a baseline scorer artifact

The repo now includes a pure-Python baseline trainer that learns `4` writing dimensions from labeled JSONL essays and saves a JSON model artifact.

Training entry point:

`/Users/xzhan/vibcoding/EnglishTest/scripts/train_writing_scorer.py`

Starter data assets:

- template: `/Users/xzhan/vibcoding/EnglishTest/data/pet_writing/templates/pet_writing_labeled_template.jsonl`
- sample dataset: `/Users/xzhan/vibcoding/EnglishTest/data/pet_writing/samples/pet_writing_labeled_sample.jsonl`
- labeling guide: `/Users/xzhan/vibcoding/EnglishTest/docs/PET-Writing-Labeling-Guide-v0.1.md`

Example:

```bash
python3 /Users/xzhan/vibcoding/EnglishTest/scripts/train_writing_scorer.py \
  --input-jsonl /Users/xzhan/vibcoding/EnglishTest/data/pet_writing/samples/pet_writing_labeled_sample.jsonl \
  --output-model /Users/xzhan/vibcoding/EnglishTest/output/writing_scorer_model.json
```

After training, point the backend to the artifact:

```bash
export PET_WRITING_MODEL_PATH="/Users/xzhan/vibcoding/EnglishTest/output/writing_scorer_model.json"
python3 /Users/xzhan/vibcoding/EnglishTest/backend/app.py --host 127.0.0.1 --port 8000
```

If `PET_WRITING_MODEL_PATH` is not set, the backend falls back to the built-in heuristic scorer.

### Quick smoke test

```bash
python3 -m unittest \
  /Users/xzhan/vibcoding/EnglishTest/tests/test_review_decision.py \
  /Users/xzhan/vibcoding/EnglishTest/tests/test_writing_api.py \
  /Users/xzhan/vibcoding/EnglishTest/tests/test_writing_prescore_api.py \
  /Users/xzhan/vibcoding/EnglishTest/tests/test_writing_pipeline.py
```

### Review gating and pre-score

- `POST /api/v1/writing/prescore` returns a stateless preview score and review decision.
- Final scored submissions now include:
  - `review.needs_review`
  - `review.review_status`
  - `review.review_reason_codes`
- The pre-score route intentionally skips persistence and should stay deterministic and low-latency.

### Example endpoints

- `GET /api/v1/health`
- `GET /api/v1/writing/prompts`
- `POST /api/v1/writing/prescore`
- `POST /api/v1/writing/attempts`
- `PUT /api/v1/writing/attempts/{attempt_id}/draft`
- `POST /api/v1/writing/attempts/{attempt_id}/submissions`
- `GET /api/v1/writing/submissions/{submission_id}/report`
- `POST /api/v1/writing/attempts/{attempt_id}/rewrite`
- `GET /api/v1/writing/attempts/{attempt_id}/comparison`
- `GET /api/v1/internal/writing/reviews/queue`
- `POST /api/v1/internal/writing/reviews`

### Key docs

- `/Users/xzhan/vibcoding/EnglishTest/docs/PET-Writing-PRD-v0.1.md`
- `/Users/xzhan/vibcoding/EnglishTest/docs/PET-Writing-API-Data-Design-v0.1.md`
- `/Users/xzhan/vibcoding/EnglishTest/docs/PET-Writing-Scorer-Tech-Design-v0.1.md`
- `/Users/xzhan/vibcoding/EnglishTest/docs/PET-Writing-Labeling-Guide-v0.1.md`

## PET Reading Pipeline

This workspace also contains a script that turns the PET vocabulary PDF into PET-level reading worksheets.

## What it does

- Extracts 66 vocabulary pages from `/Users/aistudio/PET/PET全.pdf`
- Selects focus words from each page
- Calls an OpenAI-compatible chat model once per source page
- Validates passage length, question count, answer format, and vocabulary coverage
- Caches every generated page as JSON so you can resume failed runs
- Renders a final PDF with one reading worksheet per page, including answers

## Main script

`/Users/xzhan/vibcoding/EnglishTest/scripts/pet_reading_pipeline.py`

## Extract vocabulary only

```bash
python3 /Users/xzhan/vibcoding/EnglishTest/scripts/pet_reading_pipeline.py extract \
  --source-pdf /Users/aistudio/PET/PET全.pdf \
  --output-json /Users/xzhan/vibcoding/EnglishTest/output/pet_vocab.json
```

## Build the full reading PDF

Set your API key and model first, or pass them directly:

```bash
export OPENAI_API_KEY="YOUR_KEY"
export OPENAI_MODEL="YOUR_MODEL"
python3 /Users/xzhan/vibcoding/EnglishTest/scripts/pet_reading_pipeline.py build \
  --source-pdf /Users/aistudio/PET/PET全.pdf \
  --output-dir /Users/xzhan/vibcoding/EnglishTest/output
```

## Useful options

- `--base-url`: use any OpenAI-compatible endpoint
- `--batch-id 04220958`: controls the suffix in titles such as `Reading Quest: PET全_Page_1_04220958`
- `--start-page 1 --end-page 10`: generate only part of the book
- `--force`: regenerate pages even if cached JSON already exists
- `--render-only`: skip model calls and render from cached JSON

## Output files

- `output/pet_vocab_<batch>.json`
- `output/pet_readings_<batch>.json`
- `output/pet_readings_<batch>.pdf`
- `output/raw_<batch>/page_001.json` ... `page_066.json`

## Reading Level Assessment MVP

The backend also supports a first Lexile-like reading assessment flow for Grade 6-8 students.

This is an internal teaching estimate, not an official Lexile or Renaissance Star Reading score.

### Report term coverage

The reading report intentionally mirrors the main Star Reading report slots while labeling each non-official value.

- `benchmark`: internal District Benchmark-like band with Urgent Intervention, Intervention, On Watch, and At/Above Benchmark labels.
- `scaled_score_like`: internal Lexile-like midpoint for the SS display slot.
- `percentile_rank`: marked `not_available` until a norm group and percentile calibration dataset exist.
- `grade_equivalent_like`: rough internal GE-style projection.
- `instructional_reading_level_like`: rough internal IRL-style projection from the practice range.
- `official_domain_groups`: Literature, Informational Text, and Vocabulary groupings mapped from MVP skill domains.
- `reading_recommendation`: parent-facing material selection guidance, including independent reading range, supported-challenge range, easier confidence reading, and frustration-risk range.
- `test_duration` and `test_fidelity`: elapsed time, passages completed, items answered, and validity cautions.
- `report_metadata`: report type, target range, scale, benchmark type, and official-status disclaimer.
- `zpd_like`: internal practice range used as a ZPD-like recommendation. It represents the growth practice zone: too low is not challenging, too high can be frustrating without support.
- `testing_scope`: target grades, difficulty range, passages completed, items answered, measured skills, and official terms that require external norm data.
- `report_term_coverage`: machine-readable coverage map for every official-style report term above.

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
