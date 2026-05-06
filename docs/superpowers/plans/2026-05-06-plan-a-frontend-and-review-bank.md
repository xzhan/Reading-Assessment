# Plan A Frontend and Review Bank Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Serve a real reading assessment frontend from the Python backend and generate reviewable candidate reading-bank records for human approval.

**Architecture:** Keep one local backend process. Add a static reading app route at `/app/reading` and keep all frontend API calls same-origin. Add a candidate-bank schema/validator and a deterministic generator that writes JSONL/CSV under `data/reading_review/` without importing candidates into the live assessment bank.

**Tech Stack:** Python standard library HTTP server, SQLite, HTML/CSS/vanilla JavaScript, unittest.

---

### Task 1: Serve The Real Reading App

**Files:**
- Create: `backend/pet_reading_api/static/reading_app.html`
- Modify: `backend/pet_writing_api/server.py`
- Test: `tests/test_reading_app.py`

- [ ] **Step 1: Write failing route test**

Create `tests/test_reading_app.py` with a `GET /app/reading` smoke test. It should assert status `200`, content type `text/html`, and HTML containing `data-reading-app`.

- [ ] **Step 2: Verify red**

Run:

```bash
python3 -m unittest tests.test_reading_app
```

Expected: fail with `404` because the app route is not implemented.

- [ ] **Step 3: Add route and HTML**

Create `backend/pet_reading_api/static/reading_app.html`. Update `backend/pet_writing_api/server.py` to serve it for `GET /app/reading`.

- [ ] **Step 4: Verify green**

Run:

```bash
python3 -m unittest tests.test_reading_app
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add backend/pet_reading_api/static/reading_app.html backend/pet_writing_api/server.py tests/test_reading_app.py
git commit -m "feat: serve reading assessment app"
```

### Task 2: Wire Frontend To Reading APIs

**Files:**
- Modify: `backend/pet_reading_api/static/reading_app.html`
- Test: `tests/test_reading_app.py`

- [ ] **Step 1: Extend test for required API calls**

Update the app test to assert the HTML contains calls to `/api/v1/reading/assessments`, `/next`, `/responses`, `/complete`, and `/materials`.

- [ ] **Step 2: Verify red**

Run:

```bash
python3 -m unittest tests.test_reading_app
```

Expected: fail until the frontend JS includes all required API calls.

- [ ] **Step 3: Implement app flow in vanilla JS**

Add Start, Reading, Report, and Materials sections. JS should create an assessment, load the next passage, submit responses, complete after at least three passages, and render the report and materials.

- [ ] **Step 4: Verify green**

Run:

```bash
python3 -m unittest tests.test_reading_app
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add backend/pet_reading_api/static/reading_app.html tests/test_reading_app.py
git commit -m "feat: wire reading app to api"
```

### Task 3: Candidate Reading Bank Schema And Generator

**Files:**
- Create: `backend/pet_reading_api/review_bank.py`
- Create: `scripts/generate_reading_bank.py`
- Create: `tests/test_reading_review_bank.py`

- [ ] **Step 1: Write failing schema/generator test**

Create a test that calls a deterministic generator function, validates at least one candidate, and asserts five items with required skills and `review_status == "candidate"`.

- [ ] **Step 2: Verify red**

Run:

```bash
python3 -m unittest tests.test_reading_review_bank
```

Expected: fail because `backend.pet_reading_api.review_bank` does not exist.

- [ ] **Step 3: Implement validator and deterministic candidates**

Implement `validate_candidate`, `sample_candidates`, and CLI writing `candidates.jsonl` and `candidates.csv`.

- [ ] **Step 4: Verify green**

Run:

```bash
python3 -m unittest tests.test_reading_review_bank
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add backend/pet_reading_api/review_bank.py scripts/generate_reading_bank.py tests/test_reading_review_bank.py
git commit -m "feat: generate candidate reading bank"
```

### Task 4: Documentation And Full Verification

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Document app and candidate generation**

Add run commands for backend app URL and candidate generation.

- [ ] **Step 2: Run full verification**

Run:

```bash
python3 -m unittest discover -s tests
git diff --check
```

Expected: all tests pass and diff check exits `0`.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: document reading app and candidate bank"
```

## Self-Review

- Spec coverage: covers real frontend/API and candidate bank generation; real material catalog remains next phase.
- Placeholder scan: no TBD/TODO placeholders in implementation steps.
- Type consistency: route, file names, and API paths match the existing backend.
