#!/usr/bin/env python3
"""Import reviewed Vocab Quest reading exports into review-bank files."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.pet_reading_api.review_bank import candidates_from_vocab_quest_export, write_review_files


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import Vocab Quest reading export files for review.")
    parser.add_argument("input", type=Path, help="Path to a Vocab Quest JSON export.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "data" / "reading_review",
        help="Directory for imported JSONL and CSV review files.",
    )
    parser.add_argument(
        "--basename",
        default="vocabquest_reviewed_candidates",
        help="Output basename, without .jsonl or .csv.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    candidates = candidates_from_vocab_quest_export(payload)
    paths = write_review_files(candidates, args.output_dir, basename=args.basename)

    diagnostic_ready_count = sum(1 for candidate in candidates if candidate.get("diagnostic_ready"))
    flag_counts = Counter(
        flag
        for candidate in candidates
        for flag in candidate.get("validation_flags", [])
    )

    print(f"Imported {len(candidates)} reviewed Vocab Quest candidates")
    print(f"Diagnostic-ready candidates: {diagnostic_ready_count}")
    print(f"JSONL: {paths['jsonl']}")
    print(f"CSV: {paths['csv']}")
    if flag_counts:
        print("Validation flags:")
        for flag, count in sorted(flag_counts.items()):
            print(f"- {flag}: {count}")


if __name__ == "__main__":
    main()
