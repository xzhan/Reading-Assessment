#!/usr/bin/env python3
"""Promote reviewed Vocab Quest candidates into seed-compatible reading passages."""

from __future__ import annotations

import argparse
import json
import pprint
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.pet_reading_api.review_bank import promote_vocab_quest_candidates


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Promote reviewed Vocab Quest candidates for app use.")
    parser.add_argument(
        "--input",
        type=Path,
        default=ROOT / "data" / "reading_review" / "vocabquest_reviewed_candidates.jsonl",
        help="Reviewed Vocab Quest candidate JSONL path.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "backend" / "pet_reading_api" / "vocabquest_promoted.py",
        help="Generated Python module path.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    candidates = [
        json.loads(line)
        for line in args.input.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    promoted, skipped = promote_vocab_quest_candidates(candidates)
    args.output.write_text(_module_text(promoted), encoding="utf-8")

    skip_reasons = Counter(skip["reason"] for skip in skipped)
    print(f"Promoted {len(promoted)} candidates")
    print(f"Skipped {len(skipped)} candidates")
    for reason, count in sorted(skip_reasons.items()):
        print(f"- {reason}: {count}")
    print(f"Output: {args.output}")


def _module_text(promoted: list[dict[str, object]]) -> str:
    payload = pprint.pformat(promoted, sort_dicts=False, width=120)
    return (
        '"""Generated promoted VocabQuest reading passages."""\n\n'
        "from __future__ import annotations\n\n\n"
        f"VOCABQUEST_PROMOTED_PASSAGES = {payload}\n"
    )


if __name__ == "__main__":
    main()
