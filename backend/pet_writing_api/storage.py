"""SQLite persistence for the PET Writing MVP backend."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .seed_data import PET_WRITING_PROMPTS


SCHEMA_SQL = """
create table if not exists students (
  id text primary key,
  external_ref text,
  display_name text not null,
  grade_level text,
  target_exam text not null default 'PET',
  locale text not null default 'en-US',
  created_at text not null,
  updated_at text not null
);

create table if not exists writing_prompts (
  id text primary key,
  prompt_code text not null unique,
  task_type text not null,
  title text not null,
  instructions text not null,
  target_word_count_min integer not null,
  target_word_count_max integer not null,
  recommended_time_sec integer not null,
  rubric_version text not null,
  active integer not null default 1,
  metadata_json text not null,
  created_at text not null,
  updated_at text not null
);

create table if not exists writing_attempts (
  id text primary key,
  student_id text not null,
  prompt_id text not null,
  status text not null,
  current_draft_number integer not null default 1,
  latest_submission_id text,
  review_status text not null default 'not_required',
  started_at text not null,
  completed_at text,
  created_at text not null,
  updated_at text not null
);

create table if not exists writing_drafts (
  id text primary key,
  attempt_id text not null,
  draft_number integer not null,
  text_content text not null,
  word_count integer not null,
  time_spent_sec integer not null default 0,
  saved_at text not null,
  created_at text not null,
  updated_at text not null,
  unique (attempt_id, draft_number)
);

create table if not exists writing_submissions (
  id text primary key,
  attempt_id text not null,
  draft_number integer not null,
  status text not null,
  submitted_text text not null,
  word_count integer not null,
  paragraph_count integer not null,
  time_spent_sec integer not null default 0,
  pipeline_stage text not null,
  submitted_at text not null,
  processed_at text,
  created_at text not null,
  updated_at text not null,
  unique (attempt_id, draft_number)
);

create table if not exists writing_scores (
  id text primary key,
  submission_id text not null unique,
  overall_score real not null,
  overall_max_score real not null,
  readiness_label text not null,
  overall_confidence real not null,
  task_achievement_score real not null,
  organization_coherence_score real not null,
  grammar_control_score real not null,
  lexical_range_accuracy_score real not null,
  task_achievement_confidence real not null,
  organization_coherence_confidence real not null,
  grammar_control_confidence real not null,
  lexical_range_accuracy_confidence real not null,
  needs_review integer not null default 0,
  review_reason_codes_json text not null,
  feature_signals_json text not null,
  scoring_evidence_json text not null,
  scored_at text not null,
  created_at text not null
);

create table if not exists writing_feedback (
  id text primary key,
  submission_id text not null unique,
  strengths_json text not null,
  priority_issues_json text not null,
  rewrite_task_json text not null,
  report_payload_json text not null,
  feedback_version text not null,
  generated_at text not null,
  created_at text not null
);

create table if not exists writing_sentence_feedback (
  id text primary key,
  submission_id text not null,
  sort_order integer not null,
  issue_type text not null,
  original_text text not null,
  suggested_text text not null,
  reason text not null,
  evidence_json text not null,
  created_at text not null
);

create table if not exists writing_comparisons (
  id text primary key,
  attempt_id text not null,
  base_submission_id text not null,
  compare_submission_id text not null,
  score_delta_json text not null,
  improved_points_json text not null,
  remaining_points_json text not null,
  comparison_payload_json text not null,
  generated_at text not null,
  created_at text not null
);

create table if not exists human_reviews (
  id text primary key,
  submission_id text not null,
  reviewer_id text not null,
  review_type text not null,
  overall_score real,
  dimension_scores_json text not null,
  comment text,
  created_at text not null
);

create table if not exists model_runs (
  id text primary key,
  submission_id text not null,
  stage text not null,
  provider text not null,
  model_name text not null,
  model_version text,
  input_payload_json text not null,
  output_payload_json text not null,
  latency_ms integer,
  status text not null,
  error_message text,
  created_at text not null
);

create index if not exists idx_writing_attempts_student_created_at
  on writing_attempts (student_id, created_at desc);
create index if not exists idx_writing_attempts_status
  on writing_attempts (status);
create index if not exists idx_writing_submissions_status_submitted_at
  on writing_submissions (status, submitted_at desc);
create index if not exists idx_writing_submissions_attempt_draft
  on writing_submissions (attempt_id, draft_number);
create index if not exists idx_writing_sentence_feedback_submission_sort
  on writing_sentence_feedback (submission_id, sort_order);
create index if not exists idx_human_reviews_submission
  on human_reviews (submission_id);
create index if not exists idx_model_runs_submission_stage_created_at
  on model_runs (submission_id, stage, created_at desc);
"""


class Storage:
    """Thin SQLite wrapper."""

    def __init__(self, db_path: str):
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize(self, now: str) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA_SQL)
            self._upgrade_schema(conn)
            for prompt in PET_WRITING_PROMPTS:
                conn.execute(
                    """
                    insert or ignore into writing_prompts (
                      id, prompt_code, task_type, title, instructions,
                      target_word_count_min, target_word_count_max,
                      recommended_time_sec, rubric_version, active,
                      metadata_json, created_at, updated_at
                    ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        prompt["id"],
                        prompt["prompt_code"],
                        prompt["task_type"],
                        prompt["title"],
                        prompt["instructions"],
                        prompt["target_word_count_min"],
                        prompt["target_word_count_max"],
                        prompt["recommended_time_sec"],
                        prompt["rubric_version"],
                        1,
                        self.dumps(prompt["metadata"]),
                        now,
                        now,
                    ),
                )
            conn.commit()

    def _upgrade_schema(self, conn: sqlite3.Connection) -> None:
        score_columns = {row["name"] for row in conn.execute("pragma table_info(writing_scores)")}
        if "needs_review" not in score_columns:
            conn.execute("alter table writing_scores add column needs_review integer not null default 0")
        if "review_reason_codes_json" not in score_columns:
            conn.execute("alter table writing_scores add column review_reason_codes_json text not null default '[]'")

    @staticmethod
    def dumps(value: Any) -> str:
        return json.dumps(value, ensure_ascii=True, sort_keys=True)

    @staticmethod
    def loads(value: str | None, default: Any) -> Any:
        if not value:
            return default
        return json.loads(value)
