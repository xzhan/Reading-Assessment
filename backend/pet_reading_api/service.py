"""Business logic for PET Reading assessment."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from backend.pet_writing_api.service import ServiceError

from .adaptive import next_anchor_lexile, starting_anchor_for_grade
from .estimator import estimate_reading_level
from .storage import ReadingStorage


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def make_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class ReadingService:
    """Core orchestration for reading assessment and reporting."""

    def __init__(self, storage: ReadingStorage):
        self.storage = storage
        self.storage.initialize(utc_now())

    def create_assessment(self, *, student_id: str, grade_level: int | None) -> dict[str, Any]:
        now = utc_now()
        assessment_id = make_id("rass")
        anchor = starting_anchor_for_grade(grade_level)
        with self.storage.connect() as conn:
            conn.execute(
                """
                insert into reading_assessments (
                  id, student_id, grade_level, status, target_range, started_at,
                  completed_at, duration_sec, current_anchor_lexile,
                  passages_completed, created_at, updated_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    assessment_id,
                    student_id,
                    grade_level,
                    "in_progress",
                    "grades_6_8",
                    now,
                    None,
                    0,
                    anchor,
                    0,
                    now,
                    now,
                ),
            )
            conn.commit()
        return {
            "assessment_id": assessment_id,
            "status": "in_progress",
            "current_anchor_lexile": anchor,
            "created_at": now,
        }

    def get_next_passage(self, assessment_id: str) -> dict[str, Any]:
        now = utc_now()
        with self.storage.connect() as conn:
            assessment = self._fetch_assessment(conn, assessment_id)
            pending = conn.execute(
                """
                select rp.*
                from reading_assessment_passages rap
                join reading_passages rp on rp.id = rap.passage_id
                where rap.assessment_id = ? and rap.completed_at is null
                order by rap.sequence_number desc
                limit 1
                """,
                (assessment_id,),
            ).fetchone()
            passage = pending or self._select_new_passage(conn, assessment)
            if not pending:
                sequence_number = int(assessment["passages_completed"]) + 1
                conn.execute(
                    """
                    insert into reading_assessment_passages (
                      id, assessment_id, passage_id, sequence_number, anchor_lexile,
                      started_at, completed_at, time_spent_sec, accuracy,
                      created_at, updated_at
                    ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        make_id("rap"),
                        assessment_id,
                        passage["id"],
                        sequence_number,
                        passage["anchor_lexile"],
                        now,
                        None,
                        0,
                        None,
                        now,
                        now,
                    ),
                )
                conn.commit()
            items = conn.execute(
                """
                select * from reading_items
                where passage_id = ? and active = 1
                order by item_order
                """,
                (passage["id"],),
            ).fetchall()
        return self._passage_payload(passage, items)

    def submit_responses(
        self,
        *,
        assessment_id: str,
        passage_id: str,
        time_spent_sec: int,
        responses: list[dict[str, Any]],
    ) -> dict[str, Any]:
        now = utc_now()
        with self.storage.connect() as conn:
            assessment = self._fetch_assessment(conn, assessment_id)
            item_rows = {
                row["id"]: row
                for row in conn.execute(
                    "select * from reading_items where passage_id = ?",
                    (passage_id,),
                ).fetchall()
            }
            if len(responses) != len(item_rows):
                raise ServiceError("INCOMPLETE_READING_RESPONSES", "Submit one response for every item.", status=400)
            correct_count = 0
            for response in responses:
                item = item_rows.get(response["item_id"])
                if not item:
                    raise ServiceError("READING_ITEM_NOT_FOUND", "Reading item not found for this passage.", status=404)
                selected = str(response["selected_choice"])
                is_correct = selected == item["correct_choice"]
                correct_count += 1 if is_correct else 0
                conn.execute(
                    """
                    insert into reading_responses (
                      id, assessment_id, passage_id, item_id, selected_choice,
                      is_correct, time_spent_sec, created_at
                    ) values (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        make_id("rrsp"),
                        assessment_id,
                        passage_id,
                        item["id"],
                        selected,
                        1 if is_correct else 0,
                        int(response.get("time_spent_sec", 0)),
                        now,
                    ),
                )
            accuracy = correct_count / len(item_rows) if item_rows else 0.0
            completed = int(assessment["passages_completed"]) + 1
            next_anchor = next_anchor_lexile(
                current_anchor=int(assessment["current_anchor_lexile"]),
                accuracy=accuracy,
            )
            conn.execute(
                """
                update reading_assessment_passages
                set completed_at = ?, time_spent_sec = ?, accuracy = ?, updated_at = ?
                where assessment_id = ? and passage_id = ?
                """,
                (now, time_spent_sec, accuracy, now, assessment_id, passage_id),
            )
            conn.execute(
                """
                update reading_assessments
                set current_anchor_lexile = ?, passages_completed = ?, duration_sec = duration_sec + ?, updated_at = ?
                where id = ?
                """,
                (next_anchor, completed, time_spent_sec, now, assessment_id),
            )
            conn.commit()
        return {
            "status": "ready_to_complete" if completed >= 3 else "continue",
            "passage_accuracy": round(accuracy, 3),
            "next_anchor_lexile": next_anchor,
            "passages_completed": completed,
        }

    def complete_assessment(self, assessment_id: str) -> dict[str, Any]:
        now = utc_now()
        with self.storage.connect() as conn:
            assessment = self._fetch_assessment(conn, assessment_id)
            rows = conn.execute(
                """
                select ri.estimated_item_lexile, ri.skill, rr.is_correct, rr.time_spent_sec
                from reading_responses rr
                join reading_items ri on ri.id = rr.item_id
                where rr.assessment_id = ?
                """,
                (assessment_id,),
            ).fetchall()
            response_payload = [
                {
                    "estimated_item_lexile": row["estimated_item_lexile"],
                    "skill": row["skill"],
                    "correct": bool(row["is_correct"]),
                    "time_seconds": row["time_spent_sec"],
                }
                for row in rows
            ]
            estimate = estimate_reading_level(
                responses=response_payload,
                passages_completed=int(assessment["passages_completed"]),
                duration_seconds=int(assessment["duration_sec"]),
            )
            report = self._report_payload(assessment, estimate)
            conn.execute(
                """
                insert into reading_estimates (
                  id, assessment_id, estimated_lower_lexile, estimated_upper_lexile,
                  practice_lower_lexile, practice_upper_lexile, cefr_estimate,
                  confidence_label, validity_flags_json, domain_scores_json,
                  report_payload_json, created_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(assessment_id) do update set
                  estimated_lower_lexile = excluded.estimated_lower_lexile,
                  estimated_upper_lexile = excluded.estimated_upper_lexile,
                  practice_lower_lexile = excluded.practice_lower_lexile,
                  practice_upper_lexile = excluded.practice_upper_lexile,
                  cefr_estimate = excluded.cefr_estimate,
                  confidence_label = excluded.confidence_label,
                  validity_flags_json = excluded.validity_flags_json,
                  domain_scores_json = excluded.domain_scores_json,
                  report_payload_json = excluded.report_payload_json
                """,
                (
                    make_id("rest"),
                    assessment_id,
                    estimate["estimated_lower_lexile"],
                    estimate["estimated_upper_lexile"],
                    estimate["practice_lower_lexile"],
                    estimate["practice_upper_lexile"],
                    estimate["cefr_estimate"],
                    estimate["confidence_label"],
                    self.storage.dumps(estimate["validity_flags"]),
                    self.storage.dumps(estimate["domain_scores"]),
                    self.storage.dumps(report),
                    now,
                ),
            )
            conn.execute(
                """
                update reading_assessments
                set status = ?, completed_at = ?, updated_at = ?
                where id = ?
                """,
                ("completed", now, now, assessment_id),
            )
            conn.commit()
        return report

    def get_report(self, assessment_id: str) -> dict[str, Any]:
        with self.storage.connect() as conn:
            row = conn.execute(
                "select report_payload_json from reading_estimates where assessment_id = ?",
                (assessment_id,),
            ).fetchone()
        if not row:
            raise ServiceError("READING_REPORT_NOT_READY", "Reading report is not ready.", status=404)
        return self.storage.loads(row["report_payload_json"], {})

    def _select_new_passage(self, conn: Any, assessment: Any) -> Any:
        used_rows = conn.execute(
            "select passage_id from reading_assessment_passages where assessment_id = ?",
            (assessment["id"],),
        ).fetchall()
        used_ids = [row["passage_id"] for row in used_rows]
        params: list[Any] = []
        query = "select * from reading_passages where active = 1"
        if used_ids:
            query += " and id not in (%s)" % ",".join("?" for _ in used_ids)
            params.extend(used_ids)
        query += " order by abs(anchor_lexile - ?), anchor_lexile limit 1"
        params.append(assessment["current_anchor_lexile"])
        passage = conn.execute(query, params).fetchone()
        if not passage:
            raise ServiceError("NO_READING_PASSAGE", "No eligible reading passage found.", status=404)
        return passage

    def _fetch_assessment(self, conn: Any, assessment_id: str) -> Any:
        row = conn.execute("select * from reading_assessments where id = ?", (assessment_id,)).fetchone()
        if not row:
            raise ServiceError("READING_ASSESSMENT_NOT_FOUND", "Reading assessment not found.", status=404)
        return row

    def _passage_payload(self, passage: Any, items: list[Any]) -> dict[str, Any]:
        return {
            "passage": {
                "passage_id": passage["id"],
                "title": passage["title"],
                "body_text": passage["body_text"],
                "genre": passage["genre"],
                "anchor_lexile": passage["anchor_lexile"],
            },
            "items": [
                {
                    "item_id": item["id"],
                    "skill": item["skill"],
                    "question_text": item["question_text"],
                    "choices": self.storage.loads(item["choices_json"], {}),
                }
                for item in items
            ],
        }

    def _report_payload(self, assessment: Any, estimate: dict[str, Any]) -> dict[str, Any]:
        assessment_id = assessment["id"]
        duration_sec = int(assessment["duration_sec"])
        domain_scores = estimate["domain_scores"]
        return {
            "assessment_id": assessment_id,
            "student_id": assessment["student_id"],
            "grade_level": assessment["grade_level"],
            "estimated_range": f"{estimate['estimated_lower_lexile']}L-{estimate['estimated_upper_lexile']}L",
            "practice_range": f"{estimate['practice_lower_lexile']}L-{estimate['practice_upper_lexile']}L",
            "cefr_estimate": estimate["cefr_estimate"],
            "confidence": estimate["confidence_label"],
            "range_status": estimate["range_status"],
            "test_duration": {
                "seconds": duration_sec,
                "display": _duration_display(duration_sec),
            },
            "scaled_score_like": {
                "value": f"{_midpoint(estimate['estimated_lower_lexile'], estimate['estimated_upper_lexile'])}L",
                "status": "internal_estimate",
            },
            "instructional_reading_level_like": {
                "value": _grade_level_projection(
                    _midpoint(estimate["practice_lower_lexile"], estimate["practice_upper_lexile"])
                ),
                "status": "rough_internal_projection",
            },
            "grade_equivalent_like": {
                "value": _grade_level_projection(
                    _midpoint(estimate["estimated_lower_lexile"], estimate["estimated_upper_lexile"])
                ),
                "status": "rough_internal_projection",
            },
            "zpd_like": {
                "lexile_range": f"{estimate['practice_lower_lexile']}L-{estimate['practice_upper_lexile']}L",
                "grade_range": (
                    f"{_grade_level_projection(estimate['practice_lower_lexile'])}-"
                    f"{_grade_level_projection(estimate['practice_upper_lexile'])}"
                ),
                "status": "practice_range_projection",
            },
            "summary": estimate["summary"],
            "domain_scores": domain_scores,
            "official_domain_groups": _official_domain_groups(domain_scores),
            "star_report_alignment": _star_report_alignment(estimate),
            "validity_flags": estimate["validity_flags"],
            "recommendations": estimate["recommendations"],
        }


def _duration_display(seconds: int) -> str:
    minutes, remainder = divmod(seconds, 60)
    return f"{minutes} min {remainder} sec"


def _midpoint(lower: int, upper: int) -> int:
    return round((lower + upper) / 2)


def _grade_level_projection(lexile: int) -> float:
    # Internal rough mapping for report readability, not a normed GE/IRL value.
    projected = 1.0 + (lexile / 140)
    return round(max(1.0, min(12.9, projected)), 1)


def _official_domain_groups(domain_scores: dict[str, int]) -> dict[str, dict[str, int]]:
    return {
        "literature": {
            "comprehension_of_elements_and_ideas": domain_scores["main_idea"],
            "structure_genre_and_authors_craft": domain_scores["structure_author_purpose"],
            "extending_meaning_and_deepening_understanding": domain_scores["inference"],
        },
        "informational_text": {
            "comprehension_of_information_and_ideas": domain_scores["detail"],
            "organization_purpose_and_language_use": domain_scores["structure_author_purpose"],
            "analysis_evaluation_and_extending_meaning": domain_scores["inference"],
        },
        "vocabulary": {
            "vocabulary_development": domain_scores["vocabulary_context"],
        },
    }


def _star_report_alignment(estimate: dict[str, Any]) -> dict[str, Any]:
    midpoint = _midpoint(estimate["estimated_lower_lexile"], estimate["estimated_upper_lexile"])
    return {
        "scaled_score_like": {
            "status": "internal_estimate",
            "value": f"{midpoint}L",
            "note": "Comparable display slot to Star SS, but not an official Renaissance score.",
        },
        "percentile_rank": {
            "status": "not_available",
            "reason": "Requires a norm group and percentile calibration dataset.",
        },
        "grade_equivalent_like": {
            "status": "rough_internal_projection",
            "value": _grade_level_projection(midpoint),
            "reason": "Useful for teacher orientation, not a normed GE score.",
        },
        "instructional_reading_level_like": {
            "status": "rough_internal_projection",
            "value": _grade_level_projection(
                _midpoint(estimate["practice_lower_lexile"], estimate["practice_upper_lexile"])
            ),
            "reason": "Derived from practice range, not official IRL.",
        },
        "zpd_like": {
            "status": "practice_range_projection",
            "lexile_range": f"{estimate['practice_lower_lexile']}L-{estimate['practice_upper_lexile']}L",
        },
    }
