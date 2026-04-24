# PET Writing P0 Review and Pre-Score Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add explicit review gating and a deterministic pre-score endpoint so PET Writing can decide when human review is required before showing a final report and can preview a score before submission.

**Architecture:** Extend the existing scoring pipeline with a `review_payload` stage that is computed from structured signals and model confidence after score prediction. Persist that review metadata with the scored submission, expose it in existing report/status APIs, and add a new stateless `/api/v1/writing/prescore` route that reuses feature extraction and score generation without creating an attempt or running the LLM feedback path.

**Tech Stack:** Python 3 stdlib HTTP server, SQLite, existing `WritingEvaluationPipeline`, existing `unittest` test suite

---

## Scope

This plan intentionally covers only the first P0 slice:

- `needs_review`
- `review_reason_codes`
- stateless `pre-score`

This plan does **not** include:

- `writing_baseline_profiles`
- calibration changes
- LightGBM / XGBoost upgrades
- transformer scoring

## File Structure

### Existing files to modify

- Modify: `/Users/xzhan/vibcoding/EnglishTest/backend/pet_writing_api/pipeline.py`
  Add deterministic review-decision logic and a preview-safe evaluation path.
- Modify: `/Users/xzhan/vibcoding/EnglishTest/backend/pet_writing_api/service.py`
  Persist review metadata, surface it through APIs, and add the `prescore` service method.
- Modify: `/Users/xzhan/vibcoding/EnglishTest/backend/pet_writing_api/storage.py`
  Add review columns and lightweight schema-upgrade logic for existing SQLite databases.
- Modify: `/Users/xzhan/vibcoding/EnglishTest/backend/pet_writing_api/server.py`
  Add the `/api/v1/writing/prescore` route.
- Modify: `/Users/xzhan/vibcoding/EnglishTest/README.md`
  Document the new review semantics and pre-score endpoint.
- Modify: `/Users/xzhan/vibcoding/EnglishTest/docs/PET-Writing-API-Data-Design-v0.1.md`
  Add the new endpoint and response shape.
- Modify: `/Users/xzhan/vibcoding/EnglishTest/docs/PET-Writing-Scorer-IO-Contract-v0.1.md`
  Add the review payload and pre-score contract.

### New files to create

- Create: `/Users/xzhan/vibcoding/EnglishTest/tests/test_review_decision.py`
  Unit tests for deterministic review-decision rules in the pipeline.
- Create: `/Users/xzhan/vibcoding/EnglishTest/tests/test_writing_prescore_api.py`
  End-to-end API tests for the new stateless pre-score route.

---

### Task 1: Add Deterministic Review Decisions To The Scoring Pipeline

**Files:**
- Create: `/Users/xzhan/vibcoding/EnglishTest/tests/test_review_decision.py`
- Modify: `/Users/xzhan/vibcoding/EnglishTest/backend/pet_writing_api/pipeline.py`

- [ ] **Step 1: Write the failing pipeline tests**

```python
import unittest

from backend.pet_writing_api.pipeline import WritingEvaluationPipeline


PROMPT = {
    "id": "pet_email_test",
    "task_type": "email",
    "title": "Write an email to your friend",
    "instructions": "Tell your friend about a club you joined, why you like it, and invite them.",
    "target_word_count_min": 100,
    "target_word_count_max": 140,
    "metadata": {
        "content_points": [
            ["club"],
            ["why", "like"],
            ["invite", "join"],
        ]
    },
}


class ReviewDecisionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.pipeline = WritingEvaluationPipeline(mode="off")

    def test_short_off_topic_draft_requires_review(self) -> None:
        result = self.pipeline.evaluate(
            prompt=PROMPT,
            text="Hello. School is good. I like lunch.",
            time_spent_sec=180,
        )

        review = result["review_payload"]
        self.assertTrue(review["needs_review"])
        self.assertIn("below_target_word_count", review["review_reason_codes"])
        self.assertIn("low_task_coverage", review["review_reason_codes"])

    def test_complete_draft_stays_out_of_review(self) -> None:
        text = (
            "Dear Sam,\\n"
            "I joined the music club at school because I enjoy singing and meeting new friends. "
            "We practise every Tuesday, and I like it because the teacher is kind. "
            "Please come and join us next week because I think you will enjoy the club too."
        )
        result = self.pipeline.evaluate(
            prompt=PROMPT,
            text=text,
            time_spent_sec=900,
        )

        review = result["review_payload"]
        self.assertFalse(review["needs_review"])
        self.assertEqual(review["review_reason_codes"], [])
```

- [ ] **Step 2: Run the new tests and verify they fail**

Run:

```bash
python3 -m unittest /Users/xzhan/vibcoding/EnglishTest/tests/test_review_decision.py -v
```

Expected: FAIL with `KeyError: 'review_payload'` or assertion failures because the pipeline does not return any explicit review metadata yet.

- [ ] **Step 3: Add review-decision logic to the pipeline**

Add a helper in `/Users/xzhan/vibcoding/EnglishTest/backend/pet_writing_api/pipeline.py` and return its output from `evaluate()`.

```python
    def _build_review_payload(
        self,
        *,
        prompt: dict[str, Any],
        analysis: dict[str, Any],
        score_payload: dict[str, Any],
    ) -> dict[str, Any]:
        signals = analysis["signals"]
        evidence = analysis["evidence"]
        scores = score_payload["scores"]
        reasons: list[str] = []

        if signals["word_count"] < prompt["target_word_count_min"]:
            reasons.append("below_target_word_count")
        elif signals["word_count"] > prompt["target_word_count_max"]:
            reasons.append("above_target_word_count")

        if signals["task_coverage"] < 0.67:
            reasons.append("low_task_coverage")
        if signals["off_topic_risk"] >= 0.45:
            reasons.append("off_topic_risk")
        if scores["confidence"] < 0.72:
            reasons.append("low_overall_confidence")
        if min(scores["dimension_confidence"].values()) < 0.68:
            reasons.append("low_dimension_confidence")
        if evidence["lowercase_sentence_starts"] >= 2:
            reasons.append("surface_quality_risk")

        unique_reasons = list(dict.fromkeys(reasons))
        return {
            "needs_review": bool(unique_reasons),
            "review_status": "required" if unique_reasons else "not_required",
            "review_reason_codes": unique_reasons,
        }
```

Return it from `evaluate()`:

```python
        review_payload = self._build_review_payload(
            prompt=prompt,
            analysis=analysis,
            score_payload=score_payload,
        )

        return {
            "score_payload": score_payload,
            "review_payload": review_payload,
            "feedback_payload": feedback_payload,
            "model_runs": model_runs,
        }
```

- [ ] **Step 4: Run the pipeline tests again**

Run:

```bash
python3 -m unittest /Users/xzhan/vibcoding/EnglishTest/tests/test_review_decision.py -v
```

Expected: PASS with both review-decision test cases green.

- [ ] **Step 5: Create a local checkpoint**

Run:

```bash
git rev-parse --is-inside-work-tree
```

Expected: This workspace currently returns a non-zero exit because it is not a git repo. Record progress in this plan checklist. If the project is later placed under git, use:

```bash
git add /Users/xzhan/vibcoding/EnglishTest/backend/pet_writing_api/pipeline.py /Users/xzhan/vibcoding/EnglishTest/tests/test_review_decision.py
git commit -m "feat: add deterministic review decision payload"
```

---

### Task 2: Persist Review Metadata And Surface It In Existing APIs

**Files:**
- Modify: `/Users/xzhan/vibcoding/EnglishTest/backend/pet_writing_api/storage.py`
- Modify: `/Users/xzhan/vibcoding/EnglishTest/backend/pet_writing_api/service.py`
- Modify: `/Users/xzhan/vibcoding/EnglishTest/tests/test_writing_api.py`

- [ ] **Step 1: Extend the API smoke test to assert review fields**

Update `/Users/xzhan/vibcoding/EnglishTest/tests/test_writing_api.py` with assertions after fetching the report:

```python
        status, report = self.request("GET", f"/api/v1/writing/submissions/{submission_id}/report")
        self.assertEqual(status, 200)
        self.assertIn("scores", report)
        self.assertIn("feedback", report)
        self.assertIn("review", report)
        self.assertFalse(report["review"]["needs_review"])
        self.assertEqual(report["review"]["review_reason_codes"], [])

        status, attempt_state = self.request("GET", f"/api/v1/writing/attempts/{attempt_id}")
        self.assertEqual(status, 200)
        self.assertEqual(attempt_state["review_status"], "not_required")
```

- [ ] **Step 2: Run the smoke test and verify it fails**

Run:

```bash
python3 -m unittest /Users/xzhan/vibcoding/EnglishTest/tests/test_writing_api.py -v
```

Expected: FAIL because the report payload does not include `review` yet.

- [ ] **Step 3: Add review columns and schema-upgrade logic**

Modify `/Users/xzhan/vibcoding/EnglishTest/backend/pet_writing_api/storage.py` in two places.

First, add review columns to `writing_scores`:

```sql
  needs_review integer not null default 0,
  review_reason_codes_json text not null,
```

Insert them near the confidence columns in `SCHEMA_SQL`.

Second, add an upgrade helper so older local SQLite files do not break:

```python
    def initialize(self, now: str) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA_SQL)
            self._upgrade_schema(conn)
            ...

    def _upgrade_schema(self, conn: sqlite3.Connection) -> None:
        score_columns = {row["name"] for row in conn.execute("pragma table_info(writing_scores)")}
        if "needs_review" not in score_columns:
            conn.execute("alter table writing_scores add column needs_review integer not null default 0")
        if "review_reason_codes_json" not in score_columns:
            conn.execute("alter table writing_scores add column review_reason_codes_json text not null default '[]'")
```

- [ ] **Step 4: Persist and expose review metadata in the service layer**

Modify `/Users/xzhan/vibcoding/EnglishTest/backend/pet_writing_api/service.py`.

Store the review data when scoring finishes:

```python
            evaluation = self.pipeline.evaluate(
                prompt=prompt,
                text=text,
                time_spent_sec=time_spent_sec,
                word_count_client=word_count_client,
            )
            score_payload = evaluation["score_payload"]
            review_payload = evaluation["review_payload"]
            feedback_payload = evaluation["feedback_payload"]
```

Update attempt state using the review decision:

```python
            next_attempt_status = "feedback_ready" if draft_number == 1 else "completed"
            conn.execute(
                """
                update writing_attempts
                set status = ?, current_draft_number = ?, latest_submission_id = ?,
                    review_status = ?, updated_at = ?, completed_at = ?
                where id = ?
                """,
                (
                    next_attempt_status,
                    draft_number,
                    submission_id,
                    review_payload["review_status"],
                    processed_at,
                    processed_at if draft_number > 1 else None,
                    attempt_id,
                ),
            )
```

Persist review metadata inside `_store_score()`:

```python
    def _store_score(
        self,
        conn: sqlite3.Connection,
        submission_id: str,
        score_payload: dict[str, Any],
        review_payload: dict[str, Any],
        now: str,
    ) -> None:
        ...
        conn.execute(
            """
            insert into writing_scores (
              id, submission_id, overall_score, overall_max_score, readiness_label,
              overall_confidence, task_achievement_score, organization_coherence_score,
              grammar_control_score, lexical_range_accuracy_score,
              task_achievement_confidence, organization_coherence_confidence,
              grammar_control_confidence, lexical_range_accuracy_confidence,
              needs_review, review_reason_codes_json,
              feature_signals_json, scoring_evidence_json, scored_at, created_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ...,
                1 if review_payload["needs_review"] else 0,
                self.storage.dumps(review_payload["review_reason_codes"]),
                ...,
            ),
        )
```

Expose it in `get_report()`:

```python
            "review": {
                "needs_review": bool(score["needs_review"]),
                "review_status": "required" if score["needs_review"] else "not_required",
                "review_reason_codes": self.storage.loads(score["review_reason_codes_json"], []),
            },
```

Also add `review_status` to `get_submission()` and `get_history()`.

- [ ] **Step 5: Run the smoke test again**

Run:

```bash
python3 -m unittest /Users/xzhan/vibcoding/EnglishTest/tests/test_writing_api.py -v
```

Expected: PASS with the report now exposing review metadata and the attempt returning `review_status`.

- [ ] **Step 6: Create a local checkpoint**

Run:

```bash
git rev-parse --is-inside-work-tree
```

Expected: still non-zero in this workspace. If git exists later, checkpoint with:

```bash
git add /Users/xzhan/vibcoding/EnglishTest/backend/pet_writing_api/storage.py /Users/xzhan/vibcoding/EnglishTest/backend/pet_writing_api/service.py /Users/xzhan/vibcoding/EnglishTest/tests/test_writing_api.py
git commit -m "feat: persist review metadata in writing reports"
```

---

### Task 3: Add A Stateless Pre-Score API

**Files:**
- Create: `/Users/xzhan/vibcoding/EnglishTest/tests/test_writing_prescore_api.py`
- Modify: `/Users/xzhan/vibcoding/EnglishTest/backend/pet_writing_api/pipeline.py`
- Modify: `/Users/xzhan/vibcoding/EnglishTest/backend/pet_writing_api/service.py`
- Modify: `/Users/xzhan/vibcoding/EnglishTest/backend/pet_writing_api/server.py`

- [ ] **Step 1: Write the failing API test for pre-score**

Create `/Users/xzhan/vibcoding/EnglishTest/tests/test_writing_prescore_api.py`:

```python
import json
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path

from backend.pet_writing_api.server import create_server


class WritingPreScoreApiTest(unittest.TestCase):
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
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(
            url=f"{self.base_url}{path}",
            method=method,
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))

    def test_prescore_is_stateless_and_returns_review(self) -> None:
        status, prompts = self.request("GET", "/api/v1/writing/prompts")
        self.assertEqual(status, 200)
        prompt_id = prompts["items"][0]["prompt_id"]

        status, payload = self.request(
            "POST",
            "/api/v1/writing/prescore",
            {
                "prompt_id": prompt_id,
                "text": "Hello. I like school.",
                "time_spent_sec": 120,
                "word_count_client": 4,
            },
        )
        self.assertEqual(status, 200)
        self.assertNotIn("submission_id", payload)
        self.assertIn("scores", payload)
        self.assertIn("review", payload)
        self.assertTrue(payload["review"]["needs_review"])
        self.assertIn("signals", payload)
```

- [ ] **Step 2: Run the new API test and verify it fails**

Run:

```bash
python3 -m unittest /Users/xzhan/vibcoding/EnglishTest/tests/test_writing_prescore_api.py -v
```

Expected: FAIL with `NOT_FOUND` because `/api/v1/writing/prescore` does not exist yet.

- [ ] **Step 3: Add a preview-safe scoring path**

Add a method to `/Users/xzhan/vibcoding/EnglishTest/backend/pet_writing_api/pipeline.py` that skips the LLM path and reuses the same deterministic scoring + review rules:

```python
    def prescore(
        self,
        *,
        prompt: dict[str, Any],
        text: str,
        time_spent_sec: int,
        word_count_client: int | None = None,
    ) -> dict[str, Any]:
        analysis = extract_features(prompt, text, time_spent_sec)
        score_payload, score_model_name = self._baseline_scores(prompt, analysis)
        review_payload = self._build_review_payload(
            prompt=prompt,
            analysis=analysis,
            score_payload=score_payload,
        )
        feedback_payload = self._local_feedback(prompt, text, analysis, score_payload, {})

        return {
            "score_payload": score_payload,
            "review_payload": review_payload,
            "feedback_payload": feedback_payload,
            "model_runs": [
                self._internal_run(
                    stage="prescore",
                    model_name=score_model_name,
                    input_payload={
                        "prompt_id": prompt["id"],
                        "word_count_client": word_count_client,
                    },
                    output_payload={
                        "scores": score_payload["scores"],
                        "review": review_payload,
                    },
                )
            ],
        }
```

- [ ] **Step 4: Wire the service and route**

In `/Users/xzhan/vibcoding/EnglishTest/backend/pet_writing_api/service.py`, add:

```python
    def prescore(
        self,
        prompt_id: str,
        text: str,
        time_spent_sec: int,
        word_count_client: int | None = None,
    ) -> dict[str, Any]:
        prompt = self.get_prompt(prompt_id)
        evaluation = self.pipeline.prescore(
            prompt=prompt,
            text=text,
            time_spent_sec=time_spent_sec,
            word_count_client=word_count_client,
        )
        return {
            "prompt": {
                "prompt_id": prompt["prompt_id"],
                "task_type": prompt["task_type"],
                "title": prompt["title"],
            },
            "text_stats": {
                "word_count": self._word_count(text),
                "paragraph_count": self._paragraph_count(text),
                "time_spent_sec": time_spent_sec,
            },
            "scores": evaluation["score_payload"]["scores"],
            "review": evaluation["review_payload"],
            "signals": evaluation["score_payload"]["signals"],
            "feedback_preview": {
                "priority_issues": evaluation["feedback_payload"]["priority_issues"],
                "rewrite_task": evaluation["feedback_payload"]["rewrite_task"],
            },
            "persisted": False,
        }
```

In `/Users/xzhan/vibcoding/EnglishTest/backend/pet_writing_api/server.py`, add:

```python
                if method == "POST" and path == "/api/v1/writing/prescore":
                    body = read_json_body(self)
                    json_response(
                        self,
                        200,
                        service.prescore(
                            prompt_id=body["prompt_id"],
                            text=body["text"],
                            time_spent_sec=int(body.get("time_spent_sec", 0)),
                            word_count_client=body.get("word_count_client"),
                        ),
                    )
                    return
```

- [ ] **Step 5: Run the new pre-score test**

Run:

```bash
python3 -m unittest /Users/xzhan/vibcoding/EnglishTest/tests/test_writing_prescore_api.py -v
```

Expected: PASS with a stateless payload that includes `scores`, `review`, and `signals`.

- [ ] **Step 6: Run the related regression tests together**

Run:

```bash
python3 -m unittest \
  /Users/xzhan/vibcoding/EnglishTest/tests/test_review_decision.py \
  /Users/xzhan/vibcoding/EnglishTest/tests/test_writing_api.py \
  /Users/xzhan/vibcoding/EnglishTest/tests/test_writing_prescore_api.py -v
```

Expected: PASS across all three files.

- [ ] **Step 7: Create a local checkpoint**

Run:

```bash
git rev-parse --is-inside-work-tree
```

Expected: non-zero here until the workspace is under git. If git exists later, checkpoint with:

```bash
git add /Users/xzhan/vibcoding/EnglishTest/backend/pet_writing_api/pipeline.py /Users/xzhan/vibcoding/EnglishTest/backend/pet_writing_api/service.py /Users/xzhan/vibcoding/EnglishTest/backend/pet_writing_api/server.py /Users/xzhan/vibcoding/EnglishTest/tests/test_writing_prescore_api.py
git commit -m "feat: add stateless writing prescore endpoint"
```

---

### Task 4: Update Docs And Run Final Verification

**Files:**
- Modify: `/Users/xzhan/vibcoding/EnglishTest/README.md`
- Modify: `/Users/xzhan/vibcoding/EnglishTest/docs/PET-Writing-API-Data-Design-v0.1.md`
- Modify: `/Users/xzhan/vibcoding/EnglishTest/docs/PET-Writing-Scorer-IO-Contract-v0.1.md`

- [ ] **Step 1: Update the README with the new review/pre-score contract**

Add a short section like this:

```md
## Review gating and pre-score

- `POST /api/v1/writing/prescore` returns a stateless preview score and review decision.
- Final scored submissions now include:
  - `review.needs_review`
  - `review.review_status`
  - `review.review_reason_codes`
- The pre-score route intentionally skips persistence and should stay deterministic and low-latency.
```

- [ ] **Step 2: Update the API design doc**

Add the new endpoint contract to `/Users/xzhan/vibcoding/EnglishTest/docs/PET-Writing-API-Data-Design-v0.1.md`:

```json
POST /api/v1/writing/prescore
{
  "prompt_id": "pet_writing_email_01",
  "text": "Dear Sam, ...",
  "time_spent_sec": 540,
  "word_count_client": 112
}
```

Response excerpt:

```json
{
  "persisted": false,
  "scores": { "...": "..." },
  "review": {
    "needs_review": false,
    "review_status": "not_required",
    "review_reason_codes": []
  },
  "signals": { "...": "..." }
}
```

- [ ] **Step 3: Update the scorer IO contract**

Add the following package to `/Users/xzhan/vibcoding/EnglishTest/docs/PET-Writing-Scorer-IO-Contract-v0.1.md`:

```json
{
  "review_output": {
    "needs_review": false,
    "review_status": "not_required",
    "review_reason_codes": []
  }
}
```

Also note that `pre-score` returns the same score and review schema but is `persisted: false`.

- [ ] **Step 4: Run the full verification suite**

Run:

```bash
python3 -m unittest \
  /Users/xzhan/vibcoding/EnglishTest/tests/test_review_decision.py \
  /Users/xzhan/vibcoding/EnglishTest/tests/test_writing_api.py \
  /Users/xzhan/vibcoding/EnglishTest/tests/test_writing_prescore_api.py \
  /Users/xzhan/vibcoding/EnglishTest/tests/test_writing_pipeline.py \
  /Users/xzhan/vibcoding/EnglishTest/tests/test_trainable_scorer.py -v
```

Then run:

```bash
python3 -m py_compile \
  /Users/xzhan/vibcoding/EnglishTest/backend/app.py \
  /Users/xzhan/vibcoding/EnglishTest/backend/pet_writing_api/*.py
```

Expected: all tests PASS and `py_compile` exits cleanly with no syntax errors.

- [ ] **Step 5: Final checkpoint**

Run:

```bash
git rev-parse --is-inside-work-tree
```

Expected: non-zero in this current workspace. If git exists later, checkpoint with:

```bash
git add /Users/xzhan/vibcoding/EnglishTest/README.md /Users/xzhan/vibcoding/EnglishTest/docs/PET-Writing-API-Data-Design-v0.1.md /Users/xzhan/vibcoding/EnglishTest/docs/PET-Writing-Scorer-IO-Contract-v0.1.md
git commit -m "docs: add review gating and prescore contracts"
```

---

## Self-Review

### Spec coverage

- `needs_review`: covered by Task 1 and Task 2
- `review_reason_codes`: covered by Task 1 and Task 2
- `pre-score`: covered by Task 3
- docs and contracts: covered by Task 4

No required item from this scoped P0 slice is missing.

### Placeholder scan

- No `TODO`
- No `TBD`
- No `"write tests for the above"` without concrete code
- No undefined route names or payload keys outside the tasks

### Type consistency

The plan consistently uses:

- `review_payload`
- `needs_review`
- `review_status`
- `review_reason_codes`
- `prescore`

These names should be kept exact during implementation.
