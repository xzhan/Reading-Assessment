#!/usr/bin/env python3
"""Generate candidate reading-bank files for human review."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.pet_reading_api.review_bank import sample_candidates, validate_candidate, write_review_files


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate reading-bank candidate files for review.")
    parser.add_argument("--count", type=int, default=4, help="Number of deterministic sample candidates to write.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "data" / "reading_review",
        help="Directory for candidates.jsonl and candidates.csv.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    candidates = sample_candidates(count=args.count)
    errors = {
        candidate["passage_id"]: validate_candidate(candidate)
        for candidate in candidates
        if validate_candidate(candidate)
    }
    if errors:
        raise SystemExit(f"Generated invalid candidates: {errors}")
    paths = write_review_files(candidates, args.output_dir)
    print(f"Wrote {len(candidates)} candidates")
    print(f"JSONL: {paths['jsonl']}")
    print(f"CSV: {paths['csv']}")


if __name__ == "__main__":
    main()
