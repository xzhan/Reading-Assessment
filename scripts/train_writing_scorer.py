#!/usr/bin/env python3
"""Train a baseline PET Writing scorer artifact from labeled JSONL essays."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.pet_writing_api.features import extract_features
from backend.pet_writing_api.seed_data import PET_WRITING_PROMPTS
from backend.pet_writing_api.trainable_scorer import DIMENSIONS, train_artifact


def build_prompt_lookup() -> dict[str, dict[str, Any]]:
    lookup = {}
    for item in PET_WRITING_PROMPTS:
        lookup[item["id"]] = {
            "id": item["id"],
            "task_type": item["task_type"],
            "title": item["title"],
            "instructions": item["instructions"],
            "target_word_count_min": item["target_word_count_min"],
            "target_word_count_max": item["target_word_count_max"],
            "metadata": item["metadata"],
        }
    return lookup


def normalize_prompt(raw: dict[str, Any], prompt_lookup: dict[str, dict[str, Any]]) -> dict[str, Any]:
    prompt_id = raw.get("prompt_id")
    if prompt_id and prompt_id in prompt_lookup:
        prompt = dict(prompt_lookup[prompt_id])
    else:
        prompt = {
            "id": prompt_id or raw.get("sample_id", "custom_prompt"),
            "task_type": raw.get("task_type", "email"),
            "title": raw.get("prompt_title", "Custom PET Writing Prompt"),
            "instructions": raw.get("prompt_instructions", ""),
            "target_word_count_min": int(raw.get("target_word_count_min", 100)),
            "target_word_count_max": int(raw.get("target_word_count_max", 140)),
            "metadata": raw.get("prompt_metadata", {}),
        }
    return prompt


def load_dataset(path: Path) -> list[dict[str, Any]]:
    prompt_lookup = build_prompt_lookup()
    dataset = []
    with path.open("r", encoding="utf-8") as fh:
        for line_number, line in enumerate(fh, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            item = json.loads(stripped)
            labels = item.get("labels") or {}
            missing_dimensions = [name for name in DIMENSIONS if name not in labels]
            if missing_dimensions:
                raise ValueError(f"Line {line_number} is missing labels for: {', '.join(missing_dimensions)}")
            prompt = normalize_prompt(item, prompt_lookup)
            text = item["text"]
            analysis = extract_features(prompt, text, int(item.get("time_spent_sec", 0)))
            dataset.append(
                {
                    "sample_id": item.get("sample_id", f"line_{line_number}"),
                    "prompt": prompt,
                    "text": text,
                    "labels": {name: float(labels[name]) for name in DIMENSIONS},
                    "feature_vector": analysis["feature_vector"],
                    "signals": analysis["signals"],
                }
            )
    return dataset


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train a baseline PET Writing scorer artifact.")
    parser.add_argument("--input-jsonl", required=True, help="Path to labeled writing JSONL.")
    parser.add_argument("--output-model", required=True, help="Path to save trained scorer artifact JSON.")
    parser.add_argument("--learning-rate", type=float, default=0.03, help="Learning rate for ridge regression.")
    parser.add_argument("--epochs", type=int, default=900, help="Number of training epochs.")
    parser.add_argument("--l2", type=float, default=0.01, help="L2 regularization weight.")
    parser.add_argument("--val-ratio", type=float, default=0.2, help="Validation split ratio.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for train/validation split.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    input_path = Path(args.input_jsonl)
    output_path = Path(args.output_model)
    dataset = load_dataset(input_path)
    artifact = train_artifact(
        dataset,
        learning_rate=args.learning_rate,
        epochs=args.epochs,
        l2=args.l2,
        val_ratio=args.val_ratio,
        seed=args.seed,
    )
    artifact.save(output_path)
    print(f"Saved scorer artifact to {output_path}")
    summary = artifact.training_summary
    print(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
