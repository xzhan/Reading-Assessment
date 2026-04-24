"""Business logic for the PET Writing MVP backend."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

from .pipeline import WritingEvaluationPipeline
from .storage import Storage


class ServiceError(Exception):
    """Application-level error with a stable error code."""

    def __init__(self, code: str, message: str, status: int = 400, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.details = details or {}

    def to_payload(self) -> dict[str, Any]:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            }
        }


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def make_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class WritingService:
    """Core orchestration for prompt selection, scoring, and reporting."""

    def __init__(self, storage: Storage, pipeline: WritingEvaluationPipeline | None = None):
        self.storage = storage
        self.storage.initialize(utc_now())
        self.pipeline = pipeline or WritingEvaluationPipeline()

    def list_prompts(self, task_type: str | None = None, limit: int = 20) -> dict[str, Any]:
        query = """
            select id, task_type, title, instructions,
                   target_word_count_min, target_word_count_max,
                   recommended_time_sec
            from writing_prompts
            where active = 1
        """
        params: list[Any] = []
        if task_type:
            query += " and task_type = ?"
            params.append(task_type)
        query += " order by id limit ?"
        params.append(limit)
        with self.storage.connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return {
            "items": [
                {
                    "prompt_id": row["id"],
                    "task_type": row["task_type"],
                    "title": row["title"],
                    "instructions": row["instructions"],
                    "target_word_count_min": row["target_word_count_min"],
                    "target_word_count_max": row["target_word_count_max"],
                    "recommended_time_sec": row["recommended_time_sec"],
                }
                for row in rows
            ]
        }

    def get_prompt(self, prompt_id: str) -> dict[str, Any]:
        prompt = self._fetch_prompt(prompt_id)
        return self._prompt_record_to_dict(prompt)

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

    def create_attempt(self, student_id: str, prompt_id: str) -> dict[str, Any]:
        now = utc_now()
        attempt_id = make_id("att")
        prompt = self._fetch_prompt(prompt_id)
        with self.storage.connect() as conn:
            self._ensure_student(conn, student_id, now)
            conn.execute(
                """
                insert into writing_attempts (
                  id, student_id, prompt_id, status, current_draft_number,
                  latest_submission_id, review_status, started_at,
                  completed_at, created_at, updated_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    attempt_id,
                    student_id,
                    prompt["id"],
                    "drafting",
                    1,
                    None,
                    "not_required",
                    now,
                    None,
                    now,
                    now,
                ),
            )
            conn.commit()
        return {
            "attempt_id": attempt_id,
            "status": "drafting",
            "prompt_id": prompt["id"],
            "draft_number": 1,
            "created_at": now,
        }

    def list_review_queue(self, limit: int = 20) -> dict[str, Any]:
        with self.storage.connect() as conn:
            rows = conn.execute(
                """
                select wa.id as attempt_id, wa.student_id, wa.review_status, wa.status,
                       ws.id as submission_id, ws.draft_number, ws.submitted_at,
                       wp.id as prompt_id, wp.task_type, wp.title,
                       sc.overall_score, sc.readiness_label, sc.review_reason_codes_json
                from writing_attempts wa
                join writing_submissions ws on ws.id = wa.latest_submission_id
                join writing_prompts wp on wp.id = wa.prompt_id
                join writing_scores sc on sc.submission_id = ws.id
                where wa.review_status = 'required'
                order by ws.submitted_at asc
                limit ?
                """,
                (limit,),
            ).fetchall()
        return {
            "items": [
                {
                    "attempt_id": row["attempt_id"],
                    "submission_id": row["submission_id"],
                    "student_id": row["student_id"],
                    "draft_number": row["draft_number"],
                    "submitted_at": row["submitted_at"],
                    "review_status": row["review_status"],
                    "status": row["status"],
                    "prompt": {
                        "prompt_id": row["prompt_id"],
                        "task_type": row["task_type"],
                        "title": row["title"],
                    },
                    "scores": {
                        "overall": row["overall_score"],
                        "readiness": row["readiness_label"],
                    },
                    "review_reason_codes": self.storage.loads(row["review_reason_codes_json"], []),
                }
                for row in rows
            ],
            "next_cursor": None,
        }

    def get_attempt(self, attempt_id: str) -> dict[str, Any]:
        with self.storage.connect() as conn:
            row = conn.execute(
                """
                select wa.*, wp.title, wp.task_type
                from writing_attempts wa
                join writing_prompts wp on wp.id = wa.prompt_id
                where wa.id = ?
                """,
                (attempt_id,),
            ).fetchone()
            if not row:
                raise ServiceError("ATTEMPT_NOT_FOUND", "Writing attempt not found.", status=404)
            submissions = conn.execute(
                """
                select id, draft_number, status, submitted_at
                from writing_submissions
                where attempt_id = ?
                order by draft_number
                """,
                (attempt_id,),
            ).fetchall()
        return {
            "attempt_id": row["id"],
            "student_id": row["student_id"],
            "prompt_id": row["prompt_id"],
            "prompt_title": row["title"],
            "task_type": row["task_type"],
            "status": row["status"],
            "current_draft_number": row["current_draft_number"],
            "latest_submission_id": row["latest_submission_id"],
            "review_status": row["review_status"],
            "submissions": [
                {
                    "submission_id": item["id"],
                    "draft_number": item["draft_number"],
                    "status": item["status"],
                    "submitted_at": item["submitted_at"],
                }
                for item in submissions
            ],
        }

    def save_draft(self, attempt_id: str, draft_number: int, text: str, time_spent_sec: int) -> dict[str, Any]:
        now = utc_now()
        word_count = self._word_count(text)
        with self.storage.connect() as conn:
            self._fetch_attempt(conn, attempt_id)
            conn.execute(
                """
                insert into writing_drafts (
                  id, attempt_id, draft_number, text_content, word_count,
                  time_spent_sec, saved_at, created_at, updated_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(attempt_id, draft_number) do update set
                  text_content = excluded.text_content,
                  word_count = excluded.word_count,
                  time_spent_sec = excluded.time_spent_sec,
                  saved_at = excluded.saved_at,
                  updated_at = excluded.updated_at
                """,
                (
                    make_id("drf"),
                    attempt_id,
                    draft_number,
                    text,
                    word_count,
                    time_spent_sec,
                    now,
                    now,
                    now,
                ),
            )
            conn.commit()
        return {
            "attempt_id": attempt_id,
            "draft_number": draft_number,
            "saved_at": now,
            "word_count": word_count,
            "status": "draft",
        }

    def submit_draft(
        self,
        attempt_id: str,
        draft_number: int,
        text: str,
        time_spent_sec: int,
        word_count_client: int | None = None,
    ) -> dict[str, Any]:
        now = utc_now()
        submission_id = make_id("sub")
        word_count = self._word_count(text)
        paragraph_count = self._paragraph_count(text)
        with self.storage.connect() as conn:
            attempt = self._fetch_attempt(conn, attempt_id)
            prompt_record = self._fetch_prompt_row(conn, attempt["prompt_id"])
            prompt = self._prompt_record_to_dict(prompt_record)
            if word_count < 30:
                raise ServiceError(
                    "SUBMISSION_TOO_SHORT",
                    "Essay is below the minimum recommended word count.",
                    details={"min_word_count": 30, "current_word_count": word_count},
                )
            conn.execute(
                """
                insert into writing_submissions (
                  id, attempt_id, draft_number, status, submitted_text,
                  word_count, paragraph_count, time_spent_sec, pipeline_stage,
                  submitted_at, processed_at, created_at, updated_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    submission_id,
                    attempt_id,
                    draft_number,
                    "processing",
                    text,
                    word_count,
                    paragraph_count,
                    time_spent_sec,
                    "scoring",
                    now,
                    None,
                    now,
                    now,
                ),
            )
            conn.execute(
                "update writing_attempts set status = ?, updated_at = ? where id = ?",
                ("scoring", now, attempt_id),
            )

            evaluation = self.pipeline.evaluate(
                prompt=prompt,
                text=text,
                time_spent_sec=time_spent_sec,
                word_count_client=word_count_client,
            )
            score_payload = evaluation["score_payload"]
            review_payload = evaluation["review_payload"]
            feedback_payload = evaluation["feedback_payload"]
            for run in evaluation["model_runs"]:
                self._store_model_run(conn, submission_id, run)
            self._store_score(conn, submission_id, score_payload, review_payload, now)
            self._store_feedback(conn, submission_id, feedback_payload, now)
            conn.executemany(
                """
                insert into writing_sentence_feedback (
                  id, submission_id, sort_order, issue_type, original_text,
                  suggested_text, reason, evidence_json, created_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        make_id("sfb"),
                        submission_id,
                        item["sort_order"],
                        item["issue_type"],
                        item["original"],
                        item["suggestion"],
                        item["reason"],
                        self.storage.dumps(item.get("evidence", {})),
                        now,
                    )
                    for item in feedback_payload["sentence_suggestions"]
                ],
            )
            processed_at = utc_now()
            conn.execute(
                """
                update writing_submissions
                set status = ?, pipeline_stage = ?, processed_at = ?, updated_at = ?
                where id = ?
                """,
                ("feedback_generated", "completed", processed_at, processed_at, submission_id),
            )
            next_attempt_status = self._attempt_status_after_scoring(draft_number, review_payload["needs_review"])
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
            comparison_ready = False
            if draft_number >= 2:
                comparison_ready = self._create_comparison(conn, attempt_id, prompt, submission_id, processed_at)
            conn.commit()
        return {
            "submission_id": submission_id,
            "attempt_id": attempt_id,
            "draft_number": draft_number,
            "status": "feedback_generated",
            "queue_status": "completed",
            "comparison_ready": comparison_ready,
            "poll_url": f"/api/v1/writing/submissions/{submission_id}",
        }

    def get_submission(self, submission_id: str) -> dict[str, Any]:
        with self.storage.connect() as conn:
            row = conn.execute(
                """
                select ws.id, ws.attempt_id, ws.draft_number, ws.status, ws.pipeline_stage, wa.review_status
                from writing_submissions ws
                join writing_attempts wa on wa.id = ws.attempt_id
                where ws.id = ?
                """,
                (submission_id,),
            ).fetchone()
            if not row:
                raise ServiceError("SUBMISSION_NOT_FOUND", "Submission not found.", status=404)
        return {
            "submission_id": row["id"],
            "attempt_id": row["attempt_id"],
            "draft_number": row["draft_number"],
            "status": row["status"],
            "pipeline_stage": row["pipeline_stage"],
            "review_status": row["review_status"],
            "report_ready": row["status"] == "feedback_generated",
        }

    def get_report(self, submission_id: str) -> dict[str, Any]:
        with self.storage.connect() as conn:
            submission = conn.execute(
                """
                select ws.id, ws.attempt_id, ws.draft_number, ws.word_count,
                       ws.paragraph_count, ws.time_spent_sec, ws.status,
                       wa.prompt_id, wa.review_status, wp.task_type, wp.title
                from writing_submissions ws
                join writing_attempts wa on wa.id = ws.attempt_id
                join writing_prompts wp on wp.id = wa.prompt_id
                where ws.id = ?
                """,
                (submission_id,),
            ).fetchone()
            if not submission:
                raise ServiceError("SUBMISSION_NOT_FOUND", "Submission not found.", status=404)
            if submission["status"] != "feedback_generated":
                raise ServiceError("REPORT_NOT_READY", "Submission report is not ready yet.", status=409)
            score = conn.execute("select * from writing_scores where submission_id = ?", (submission_id,)).fetchone()
            feedback = conn.execute("select * from writing_feedback where submission_id = ?", (submission_id,)).fetchone()
            sentence_feedback = conn.execute(
                """
                select sort_order, issue_type, original_text, suggested_text, reason, evidence_json
                from writing_sentence_feedback
                where submission_id = ?
                order by sort_order
                """,
                (submission_id,),
            ).fetchall()
            latest_runs = conn.execute(
                """
                select stage, provider, model_name, model_version, status, error_message
                from model_runs
                where submission_id = ?
                order by created_at asc
                """,
                (submission_id,),
            ).fetchall()
        return {
            "submission_id": submission["id"],
            "attempt_id": submission["attempt_id"],
            "draft_number": submission["draft_number"],
            "prompt": {
                "prompt_id": submission["prompt_id"],
                "task_type": submission["task_type"],
                "title": submission["title"],
            },
            "text_stats": {
                "word_count": submission["word_count"],
                "paragraph_count": submission["paragraph_count"],
                "time_spent_sec": submission["time_spent_sec"],
            },
            "scores": {
                "overall": {
                    "score": score["overall_score"],
                    "max_score": score["overall_max_score"],
                    "readiness": score["readiness_label"],
                    "confidence": score["overall_confidence"],
                },
                "dimensions": {
                    "task_achievement": {
                        "score": score["task_achievement_score"],
                        "max_score": 5,
                        "confidence": score["task_achievement_confidence"],
                    },
                    "organization_coherence": {
                        "score": score["organization_coherence_score"],
                        "max_score": 5,
                        "confidence": score["organization_coherence_confidence"],
                    },
                    "grammar_control": {
                        "score": score["grammar_control_score"],
                        "max_score": 5,
                        "confidence": score["grammar_control_confidence"],
                    },
                    "lexical_range_accuracy": {
                        "score": score["lexical_range_accuracy_score"],
                        "max_score": 5,
                        "confidence": score["lexical_range_accuracy_confidence"],
                    },
                },
            },
            "signals": self.storage.loads(score["feature_signals_json"], {}),
            "feedback": {
                "strengths": self.storage.loads(feedback["strengths_json"], []),
                "priority_issues": self.storage.loads(feedback["priority_issues_json"], []),
                "sentence_suggestions": [
                    {
                        "issue_type": row["issue_type"],
                        "original": row["original_text"],
                        "suggestion": row["suggested_text"],
                        "reason": row["reason"],
                        "evidence": self.storage.loads(row["evidence_json"], {}),
                    }
                    for row in sentence_feedback
                ],
                "rewrite_task": self.storage.loads(feedback["rewrite_task_json"], {}),
            },
            "review": {
                "needs_review": bool(score["needs_review"]),
                "review_status": submission["review_status"],
                "review_reason_codes": self.storage.loads(score["review_reason_codes_json"], []),
            },
            "pipeline": [
                {
                    "stage": row["stage"],
                    "provider": row["provider"],
                    "model_name": row["model_name"],
                    "model_version": row["model_version"],
                    "status": row["status"],
                    "error_message": row["error_message"],
                }
                for row in latest_runs
            ],
        }

    def start_rewrite(self, attempt_id: str) -> dict[str, Any]:
        now = utc_now()
        with self.storage.connect() as conn:
            attempt = self._fetch_attempt(conn, attempt_id)
            if attempt["review_status"] == "required":
                raise ServiceError(
                    "REVIEW_REQUIRED",
                    "A human review is required before rewrite can start.",
                    status=409,
                )
            if not attempt["latest_submission_id"]:
                raise ServiceError(
                    "REPORT_NOT_READY",
                    "No scored submission is available for rewrite yet.",
                    status=409,
                )
            feedback = conn.execute(
                "select rewrite_task_json from writing_feedback where submission_id = ?",
                (attempt["latest_submission_id"],),
            ).fetchone()
            if not feedback:
                raise ServiceError("REPORT_NOT_READY", "No rewrite task is available yet.", status=409)
            next_draft = max(2, int(attempt["current_draft_number"]) + 1)
            conn.execute(
                "update writing_attempts set status = ?, current_draft_number = ?, updated_at = ? where id = ?",
                ("rewrite_in_progress", next_draft, now, attempt_id),
            )
            conn.commit()
        return {
            "attempt_id": attempt_id,
            "status": "rewrite_in_progress",
            "next_draft_number": next_draft,
            "rewrite_task": self.storage.loads(feedback["rewrite_task_json"], {}),
        }

    def get_comparison(self, attempt_id: str) -> dict[str, Any]:
        with self.storage.connect() as conn:
            row = conn.execute(
                """
                select *
                from writing_comparisons
                where attempt_id = ?
                order by generated_at desc
                limit 1
                """,
                (attempt_id,),
            ).fetchone()
            if not row:
                raise ServiceError("REPORT_NOT_READY", "Comparison is not ready yet for this attempt.", status=409)
        return {
            "attempt_id": row["attempt_id"],
            "base_submission_id": row["base_submission_id"],
            "compare_submission_id": row["compare_submission_id"],
            "score_delta": self.storage.loads(row["score_delta_json"], {}),
            "summary": {
                "improved": self.storage.loads(row["improved_points_json"], []),
                "still_needs_work": self.storage.loads(row["remaining_points_json"], []),
            },
        }

    def get_history(self, student_id: str, limit: int = 20) -> dict[str, Any]:
        with self.storage.connect() as conn:
            rows = conn.execute(
                """
                select wa.id as attempt_id, wa.status, wa.created_at, wp.title, wp.task_type,
                       wa.review_status, ws.id as submission_id, ws.draft_number, sc.overall_score, sc.readiness_label
                from writing_attempts wa
                join writing_prompts wp on wp.id = wa.prompt_id
                left join writing_submissions ws on ws.id = wa.latest_submission_id
                left join writing_scores sc on sc.submission_id = ws.id
                where wa.student_id = ?
                order by wa.created_at desc
                limit ?
                """,
                (student_id, limit),
            ).fetchall()
        return {
            "items": [
                {
                    "attempt_id": row["attempt_id"],
                    "status": row["status"],
                    "created_at": row["created_at"],
                    "task_type": row["task_type"],
                    "prompt_title": row["title"],
                    "latest_submission_id": row["submission_id"],
                    "latest_draft_number": row["draft_number"],
                    "review_status": row["review_status"],
                    "overall_score": row["overall_score"],
                    "readiness": row["readiness_label"],
                }
                for row in rows
            ],
            "next_cursor": None,
        }

    def add_review(
        self,
        submission_id: str,
        reviewer_id: str,
        scores: dict[str, float],
        comment: str | None = None,
    ) -> dict[str, Any]:
        now = utc_now()
        review_id = make_id("rev")
        with self.storage.connect() as conn:
            submission = conn.execute(
                "select id, attempt_id, draft_number from writing_submissions where id = ?",
                (submission_id,),
            ).fetchone()
            if not submission:
                raise ServiceError("SUBMISSION_NOT_FOUND", "Submission not found.", status=404)
            conn.execute(
                """
                insert into human_reviews (
                  id, submission_id, reviewer_id, review_type, overall_score,
                  dimension_scores_json, comment, created_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    review_id,
                    submission_id,
                    reviewer_id,
                    "calibration",
                    scores.get("overall"),
                    self.storage.dumps(scores),
                    comment,
                    now,
                ),
            )
            self._apply_review_scores(conn, submission_id, scores)
            conn.execute(
                "update writing_attempts set review_status = ?, status = ?, updated_at = ? where id = ?",
                (
                    "reviewed",
                    self._attempt_status_after_review(int(submission["draft_number"])),
                    now,
                    submission["attempt_id"],
                ),
            )
            conn.commit()
        return {"review_id": review_id, "submission_id": submission_id, "status": "reviewed"}

    def _ensure_student(self, conn: sqlite3.Connection, student_id: str, now: str) -> None:
        conn.execute(
            """
            insert or ignore into students (
              id, external_ref, display_name, grade_level, target_exam, locale, created_at, updated_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (student_id, None, student_id, None, "PET", "en-US", now, now),
        )

    def _fetch_prompt(self, prompt_id: str) -> sqlite3.Row:
        with self.storage.connect() as conn:
            return self._fetch_prompt_row(conn, prompt_id)

    def _fetch_prompt_row(self, conn: sqlite3.Connection, prompt_id: str) -> sqlite3.Row:
        row = conn.execute(
            "select * from writing_prompts where id = ? and active = 1",
            (prompt_id,),
        ).fetchone()
        if not row:
            raise ServiceError("PROMPT_NOT_FOUND", "Writing prompt not found.", status=404)
        return row

    def _fetch_attempt(self, conn: sqlite3.Connection, attempt_id: str) -> sqlite3.Row:
        row = conn.execute("select * from writing_attempts where id = ?", (attempt_id,)).fetchone()
        if not row:
            raise ServiceError("ATTEMPT_NOT_FOUND", "Writing attempt not found.", status=404)
        return row

    @staticmethod
    def _attempt_status_after_scoring(draft_number: int, needs_review: bool) -> str:
        if needs_review:
            return "review_required"
        return "feedback_ready" if draft_number == 1 else "completed"

    @staticmethod
    def _attempt_status_after_review(draft_number: int) -> str:
        return "feedback_ready" if draft_number == 1 else "completed"

    @staticmethod
    def _readiness_from_overall(overall_score: float) -> str:
        if overall_score < 11.0:
            return "below_target"
        if overall_score < 15.0:
            return "borderline"
        return "on_track"

    def _apply_review_scores(self, conn: sqlite3.Connection, submission_id: str, scores: dict[str, float]) -> None:
        task = float(scores["task_achievement"])
        organization = float(scores["organization_coherence"])
        grammar = float(scores["grammar_control"])
        lexical = float(scores["lexical_range_accuracy"])
        overall = float(scores.get("overall", round(task + organization + grammar + lexical, 2)))
        readiness = self._readiness_from_overall(overall)
        conn.execute(
            """
            update writing_scores
            set overall_score = ?, readiness_label = ?, overall_confidence = ?,
                task_achievement_score = ?, organization_coherence_score = ?,
                grammar_control_score = ?, lexical_range_accuracy_score = ?,
                task_achievement_confidence = ?, organization_coherence_confidence = ?,
                grammar_control_confidence = ?, lexical_range_accuracy_confidence = ?,
                needs_review = ?, review_reason_codes_json = ?
            where submission_id = ?
            """,
            (
                overall,
                readiness,
                1.0,
                task,
                organization,
                grammar,
                lexical,
                1.0,
                1.0,
                1.0,
                1.0,
                0,
                self.storage.dumps([]),
                submission_id,
            ),
        )

    def _create_comparison(
        self,
        conn: sqlite3.Connection,
        attempt_id: str,
        prompt: dict[str, Any],
        compare_submission_id: str,
        now: str,
    ) -> bool:
        base_submission = conn.execute(
            """
            select id, submitted_text
            from writing_submissions
            where attempt_id = ? and draft_number = 1
            """,
            (attempt_id,),
        ).fetchone()
        compare_submission = conn.execute(
            """
            select id, submitted_text
            from writing_submissions
            where id = ?
            """,
            (compare_submission_id,),
        ).fetchone()
        if not base_submission or not compare_submission or base_submission["id"] == compare_submission_id:
            return False
        base_score = conn.execute("select * from writing_scores where submission_id = ?", (base_submission["id"],)).fetchone()
        new_score = conn.execute("select * from writing_scores where submission_id = ?", (compare_submission_id,)).fetchone()
        if not base_score or not new_score:
            return False
        comparison_result = self.pipeline.summarize_comparison(
            prompt=prompt,
            base_text=base_submission["submitted_text"],
            compare_text=compare_submission["submitted_text"],
            base_scores=self._score_row_to_payload(base_score),
            compare_scores=self._score_row_to_payload(new_score),
        )
        payload = comparison_result["comparison_payload"]
        conn.execute(
            """
            insert into writing_comparisons (
              id, attempt_id, base_submission_id, compare_submission_id,
              score_delta_json, improved_points_json, remaining_points_json,
              comparison_payload_json, generated_at, created_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                make_id("cmp"),
                attempt_id,
                base_submission["id"],
                compare_submission_id,
                self.storage.dumps(payload["score_delta"]),
                self.storage.dumps(payload["improved"]),
                self.storage.dumps(payload["still_needs_work"]),
                self.storage.dumps(payload),
                now,
                now,
            ),
        )
        for run in comparison_result["model_runs"]:
            self._store_model_run(conn, compare_submission_id, run)
        return True

    def _store_score(
        self,
        conn: sqlite3.Connection,
        submission_id: str,
        score_payload: dict[str, Any],
        review_payload: dict[str, Any],
        now: str,
    ) -> None:
        scores = score_payload["scores"]
        dims = scores["dimensions"]
        conf = scores["dimension_confidence"]
        conn.execute(
            """
            insert into writing_scores (
              id, submission_id, overall_score, overall_max_score, readiness_label,
              overall_confidence, task_achievement_score, organization_coherence_score,
              grammar_control_score, lexical_range_accuracy_score,
              task_achievement_confidence, organization_coherence_confidence,
              grammar_control_confidence, lexical_range_accuracy_confidence, needs_review,
              review_reason_codes_json,
              feature_signals_json, scoring_evidence_json, scored_at, created_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                make_id("scr"),
                submission_id,
                scores["overall"],
                20.0,
                scores["readiness"],
                scores["confidence"],
                dims["task_achievement"],
                dims["organization_coherence"],
                dims["grammar_control"],
                dims["lexical_range_accuracy"],
                conf["task_achievement"],
                conf["organization_coherence"],
                conf["grammar_control"],
                conf["lexical_range_accuracy"],
                1 if review_payload["needs_review"] else 0,
                self.storage.dumps(review_payload["review_reason_codes"]),
                self.storage.dumps(score_payload["signals"]),
                self.storage.dumps(score_payload["evidence"]),
                now,
                now,
            ),
        )

    def _store_feedback(self, conn: sqlite3.Connection, submission_id: str, payload: dict[str, Any], now: str) -> None:
        report_payload = {
            "strengths": payload["strengths"],
            "priority_issues": payload["priority_issues"],
            "rewrite_task": payload["rewrite_task"],
        }
        conn.execute(
            """
            insert into writing_feedback (
              id, submission_id, strengths_json, priority_issues_json,
              rewrite_task_json, report_payload_json, feedback_version,
              generated_at, created_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                make_id("fbk"),
                submission_id,
                self.storage.dumps(payload["strengths"]),
                self.storage.dumps(payload["priority_issues"]),
                self.storage.dumps(payload["rewrite_task"]),
                self.storage.dumps(report_payload),
                "feedback-v2",
                now,
                now,
            ),
        )

    def _store_model_run(self, conn: sqlite3.Connection, submission_id: str, run: dict[str, Any]) -> None:
        now = utc_now()
        conn.execute(
            """
            insert into model_runs (
              id, submission_id, stage, provider, model_name, model_version,
              input_payload_json, output_payload_json, latency_ms,
              status, error_message, created_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                make_id("mdl"),
                submission_id,
                run["stage"],
                run["provider"],
                run["model_name"],
                run.get("model_version"),
                self.storage.dumps(run.get("input_payload", {})),
                self.storage.dumps(run.get("output_payload", {})),
                run.get("latency_ms"),
                run.get("status", "completed"),
                run.get("error_message"),
                now,
            ),
        )

    def _prompt_record_to_dict(self, prompt: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": prompt["id"],
            "prompt_id": prompt["id"],
            "task_type": prompt["task_type"],
            "title": prompt["title"],
            "instructions": prompt["instructions"],
            "target_word_count_min": prompt["target_word_count_min"],
            "target_word_count_max": prompt["target_word_count_max"],
            "recommended_time_sec": prompt["recommended_time_sec"],
            "metadata": self.storage.loads(prompt["metadata_json"], {}),
        }

    @staticmethod
    def _word_count(text: str) -> int:
        return len([word for word in text.split() if word.strip()])

    @staticmethod
    def _paragraph_count(text: str) -> int:
        paragraphs = [part.strip() for part in text.splitlines() if part.strip()]
        return max(1, len(paragraphs))

    @staticmethod
    def _score_row_to_payload(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "overall": row["overall_score"],
            "readiness": row["readiness_label"],
            "confidence": row["overall_confidence"],
            "dimensions": {
                "task_achievement": row["task_achievement_score"],
                "organization_coherence": row["organization_coherence_score"],
                "grammar_control": row["grammar_control_score"],
                "lexical_range_accuracy": row["lexical_range_accuracy_score"],
            },
        }
