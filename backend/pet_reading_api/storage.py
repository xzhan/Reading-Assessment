"""SQLite persistence for PET Reading assessment."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .seed_data import READING_PASSAGES


SCHEMA_SQL = """
create table if not exists reading_passages (
  id text primary key,
  passage_code text not null unique,
  title text not null,
  body_text text not null,
  band_label text not null,
  anchor_lexile integer not null,
  cefr_level text not null,
  genre text not null,
  word_count integer not null,
  topic text not null,
  metadata_json text not null,
  active integer not null default 1,
  created_at text not null,
  updated_at text not null
);

create table if not exists reading_items (
  id text primary key,
  passage_id text not null,
  item_order integer not null,
  skill text not null,
  difficulty_label text not null,
  difficulty_offset integer not null,
  estimated_item_lexile integer not null,
  question_text text not null,
  choices_json text not null,
  correct_choice text not null,
  rationales_json text not null,
  active integer not null default 1,
  created_at text not null,
  updated_at text not null
);

create table if not exists reading_assessments (
  id text primary key,
  student_id text not null,
  grade_level integer,
  status text not null,
  target_range text not null,
  started_at text not null,
  completed_at text,
  duration_sec integer not null default 0,
  current_anchor_lexile integer not null,
  passages_completed integer not null default 0,
  created_at text not null,
  updated_at text not null
);

create table if not exists reading_assessment_passages (
  id text primary key,
  assessment_id text not null,
  passage_id text not null,
  sequence_number integer not null,
  anchor_lexile integer not null,
  started_at text not null,
  completed_at text,
  time_spent_sec integer not null default 0,
  accuracy real,
  created_at text not null,
  updated_at text not null,
  unique (assessment_id, passage_id)
);

create table if not exists reading_responses (
  id text primary key,
  assessment_id text not null,
  passage_id text not null,
  item_id text not null,
  selected_choice text not null,
  is_correct integer not null,
  time_spent_sec integer not null default 0,
  created_at text not null
);

create table if not exists reading_estimates (
  id text primary key,
  assessment_id text not null unique,
  estimated_lower_lexile integer not null,
  estimated_upper_lexile integer not null,
  practice_lower_lexile integer not null,
  practice_upper_lexile integer not null,
  cefr_estimate text not null,
  confidence_label text not null,
  validity_flags_json text not null,
  domain_scores_json text not null,
  report_payload_json text not null,
  created_at text not null
);

create index if not exists idx_reading_passages_anchor
  on reading_passages (anchor_lexile, active);
create index if not exists idx_reading_items_passage_order
  on reading_items (passage_id, item_order);
create index if not exists idx_reading_responses_assessment
  on reading_responses (assessment_id);
"""


class ReadingStorage:
    """Thin SQLite wrapper for reading assessment state."""

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
            for passage in READING_PASSAGES:
                conn.execute(
                    """
                    insert or ignore into reading_passages (
                      id, passage_code, title, body_text, band_label, anchor_lexile,
                      cefr_level, genre, word_count, topic, metadata_json, active,
                      created_at, updated_at
                    ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        passage["id"],
                        passage["passage_code"],
                        passage["title"],
                        passage["body_text"],
                        passage["band_label"],
                        passage["anchor_lexile"],
                        passage["cefr_level"],
                        passage["genre"],
                        passage["word_count"],
                        passage["topic"],
                        self.dumps(passage.get("metadata", {"source": "seed"})),
                        1,
                        now,
                        now,
                    ),
                )
                for item in passage["items"]:
                    conn.execute(
                        """
                        insert or ignore into reading_items (
                          id, passage_id, item_order, skill, difficulty_label,
                          difficulty_offset, estimated_item_lexile, question_text,
                          choices_json, correct_choice, rationales_json, active,
                          created_at, updated_at
                        ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            item["id"],
                            passage["id"],
                            item["item_order"],
                            item["skill"],
                            item["difficulty_label"],
                            item["difficulty_offset"],
                            item["estimated_item_lexile"],
                            item["question_text"],
                            self.dumps(item["choices"]),
                            item["correct_choice"],
                            self.dumps(item["rationales"]),
                            1,
                            now,
                            now,
                        ),
                    )
            conn.commit()

    @staticmethod
    def dumps(value: Any) -> str:
        return json.dumps(value, ensure_ascii=True, sort_keys=True)

    @staticmethod
    def loads(value: str | None, default: Any) -> Any:
        if not value:
            return default
        return json.loads(value)
