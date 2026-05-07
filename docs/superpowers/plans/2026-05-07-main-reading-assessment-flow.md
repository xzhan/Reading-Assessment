# Main Reading Assessment Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Change the main reading assessment from 3 passages / 15 questions to 6 passages / 30 questions.

**Architecture:** The backend remains the source of truth for assessment length. `ReadingService.submit_responses` controls when the assessment is ready to complete, while the estimator and report fidelity logic define when a result has enough evidence to be considered valid.

**Tech Stack:** Python `unittest`, SQLite-backed reading API, static HTML reading app.

---

### Task 1: Lock Main Assessment Length

**Files:**
- Modify: `tests/test_reading_api.py`
- Modify: `backend/pet_reading_api/service.py`

- [ ] **Step 1: Write the failing API test**

In `tests/test_reading_api.py`, update `test_full_reading_flow` so it submits 6 passages. Assert the first 5 submissions return `continue`, and the 6th returns `ready_to_complete`.

- [ ] **Step 2: Verify RED**

Run:

```bash
python3 -m unittest tests.test_reading_api.ReadingApiTest.test_full_reading_flow
```

Expected: fail because the current service returns `ready_to_complete` after 3 passages.

- [ ] **Step 3: Implement the threshold**

In `backend/pet_reading_api/service.py`, introduce `ASSESSMENT_TARGET_PASSAGES = 6` and use it in `submit_responses`.

- [ ] **Step 4: Verify GREEN**

Run:

```bash
python3 -m unittest tests.test_reading_api.ReadingApiTest.test_full_reading_flow
```

Expected: pass.

### Task 2: Align Report Fidelity With 30 Questions

**Files:**
- Modify: `tests/test_reading_api.py`
- Modify: `tests/test_reading_estimator.py`
- Modify: `backend/pet_reading_api/service.py`
- Modify: `backend/pet_reading_api/estimator.py`

- [ ] **Step 1: Write/update report tests**

Update report assertions to expect `testing_scope.passages_completed == 6` for a valid main assessment, and update estimator tests so 6 passages is the valid evidence target.

- [ ] **Step 2: Verify RED**

Run:

```bash
python3 -m unittest tests.test_reading_api tests.test_reading_estimator
```

Expected: fail until estimator and fidelity thresholds are updated.

- [ ] **Step 3: Implement fidelity threshold**

Set estimator too-few-passage logic to 6 passages and update `_test_fidelity_payload` copy to say fewer than 6 passages.

- [ ] **Step 4: Verify GREEN**

Run:

```bash
python3 -m unittest tests.test_reading_api tests.test_reading_estimator
```

Expected: pass.

### Task 3: Full Verification And Browser Smoke

**Files:**
- No production files beyond Tasks 1-2.

- [ ] **Step 1: Run full tests**

Run:

```bash
python3 -m unittest discover -s tests
git diff --check
```

Expected: all tests pass and no whitespace errors.

- [ ] **Step 2: Restart local app**

Run:

```bash
python3 backend/app.py --host 127.0.0.1 --port 8123 --db-path /tmp/english_test_reading_manual_test.db
```

- [ ] **Step 3: Browser smoke test**

Open `http://127.0.0.1:8123/app/reading`, start an assessment, submit 6 passages, and verify the report shows `6 passages, 30 items`.
