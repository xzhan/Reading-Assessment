"""Trainable scorer artifact and pure-Python baseline trainer."""

from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .features import FEATURE_NAMES


DIMENSIONS = [
    "task_achievement",
    "organization_coherence",
    "grammar_control",
    "lexical_range_accuracy",
]


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def readiness_label(overall_score: float) -> str:
    if overall_score >= 15:
        return "on_track"
    if overall_score >= 11:
        return "borderline"
    return "below_target"


def mae(predictions: list[float], labels: list[float]) -> float:
    if not predictions:
        return 0.0
    return sum(abs(p - y) for p, y in zip(predictions, labels)) / len(predictions)


def rmse(predictions: list[float], labels: list[float]) -> float:
    if not predictions:
        return 0.0
    return math.sqrt(sum((p - y) ** 2 for p, y in zip(predictions, labels)) / len(predictions))


def within_one(predictions: list[float], labels: list[float]) -> float:
    if not predictions:
        return 0.0
    return sum(1 for p, y in zip(predictions, labels) if abs(p - y) <= 1.0) / len(predictions)


@dataclass
class DimensionArtifact:
    intercept: float
    weights: dict[str, float]
    feature_means: dict[str, float]
    feature_stds: dict[str, float]
    train_mae: float
    train_rmse: float
    val_mae: float
    val_rmse: float
    val_within_one: float

    def predict(self, feature_vector: dict[str, float]) -> float:
        total = self.intercept
        for name, weight in self.weights.items():
            std = self.feature_stds.get(name, 1.0) or 1.0
            normalized = (feature_vector.get(name, 0.0) - self.feature_means.get(name, 0.0)) / std
            total += weight * normalized
        return round(clamp(total, 0.0, 5.0), 2)


class TrainableScorerArtifact:
    """JSON-serializable scorer artifact."""

    def __init__(self, version: str, dimensions: dict[str, DimensionArtifact], training_summary: dict[str, Any]):
        self.version = version
        self.dimensions = dimensions
        self.training_summary = training_summary

    def predict(self, feature_vector: dict[str, float]) -> dict[str, Any]:
        dimension_scores = {name: artifact.predict(feature_vector) for name, artifact in self.dimensions.items()}
        overall = round(sum(dimension_scores.values()), 2)
        avg_val_mae = sum(artifact.val_mae for artifact in self.dimensions.values()) / max(1, len(self.dimensions))
        confidence = round(clamp(0.92 - (avg_val_mae * 0.12), 0.55, 0.95), 3)
        dimension_confidence = {
            name: round(clamp(0.94 - (artifact.val_mae * 0.15), 0.52, 0.96), 3)
            for name, artifact in self.dimensions.items()
        }
        return {
            "overall": overall,
            "readiness": readiness_label(overall),
            "confidence": confidence,
            "dimensions": dimension_scores,
            "dimension_confidence": dimension_confidence,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "training_summary": self.training_summary,
            "dimensions": {
                name: {
                    "intercept": artifact.intercept,
                    "weights": artifact.weights,
                    "feature_means": artifact.feature_means,
                    "feature_stds": artifact.feature_stds,
                    "train_mae": artifact.train_mae,
                    "train_rmse": artifact.train_rmse,
                    "val_mae": artifact.val_mae,
                    "val_rmse": artifact.val_rmse,
                    "val_within_one": artifact.val_within_one,
                }
                for name, artifact in self.dimensions.items()
            },
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TrainableScorerArtifact":
        dimensions = {
            name: DimensionArtifact(
                intercept=float(item["intercept"]),
                weights={k: float(v) for k, v in item["weights"].items()},
                feature_means={k: float(v) for k, v in item["feature_means"].items()},
                feature_stds={k: float(v) for k, v in item["feature_stds"].items()},
                train_mae=float(item["train_mae"]),
                train_rmse=float(item["train_rmse"]),
                val_mae=float(item["val_mae"]),
                val_rmse=float(item["val_rmse"]),
                val_within_one=float(item["val_within_one"]),
            )
            for name, item in payload["dimensions"].items()
        }
        return cls(
            version=str(payload.get("version", "unknown")),
            dimensions=dimensions,
            training_summary=payload.get("training_summary", {}),
        )

    @classmethod
    def load(cls, path: str | Path) -> "TrainableScorerArtifact":
        with open(path, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
        return cls.from_dict(payload)

    def save(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, ensure_ascii=True, indent=2, sort_keys=True)


def _feature_stats(samples: list[dict[str, float]]) -> tuple[dict[str, float], dict[str, float]]:
    means = {}
    stds = {}
    for name in FEATURE_NAMES:
        values = [sample.get(name, 0.0) for sample in samples]
        mean = sum(values) / max(1, len(values))
        variance = sum((value - mean) ** 2 for value in values) / max(1, len(values))
        std = math.sqrt(variance) or 1.0
        means[name] = mean
        stds[name] = std
    return means, stds


def _normalize(samples: list[dict[str, float]], means: dict[str, float], stds: dict[str, float]) -> list[list[float]]:
    matrix = []
    for sample in samples:
        row = []
        for name in FEATURE_NAMES:
            row.append((sample.get(name, 0.0) - means[name]) / stds[name])
        matrix.append(row)
    return matrix


def _train_ridge(
    features: list[list[float]],
    labels: list[float],
    *,
    learning_rate: float,
    epochs: int,
    l2: float,
) -> tuple[float, list[float]]:
    if not features:
        return 0.0, [0.0 for _ in FEATURE_NAMES]
    intercept = sum(labels) / max(1, len(labels))
    weights = [0.0 for _ in FEATURE_NAMES]
    n_samples = len(features)
    for _ in range(epochs):
        grad_intercept = 0.0
        grad_weights = [0.0 for _ in FEATURE_NAMES]
        for row, target in zip(features, labels):
            prediction = intercept + sum(weight * value for weight, value in zip(weights, row))
            error = prediction - target
            grad_intercept += error
            for index, value in enumerate(row):
                grad_weights[index] += error * value
        intercept -= learning_rate * (grad_intercept / n_samples)
        for index in range(len(weights)):
            grad = (grad_weights[index] / n_samples) + (l2 * weights[index])
            weights[index] -= learning_rate * grad
    return intercept, weights


def _predict_matrix(intercept: float, weights: list[float], features: list[list[float]]) -> list[float]:
    predictions = []
    for row in features:
        predictions.append(intercept + sum(weight * value for weight, value in zip(weights, row)))
    return predictions


def train_artifact(
    dataset: list[dict[str, Any]],
    *,
    learning_rate: float = 0.03,
    epochs: int = 900,
    l2: float = 0.01,
    val_ratio: float = 0.2,
    seed: int = 42,
) -> TrainableScorerArtifact:
    if len(dataset) < 8:
        raise ValueError("Need at least 8 labeled essays to train a baseline scorer.")
    shuffled = list(dataset)
    random.Random(seed).shuffle(shuffled)
    val_size = max(1, int(len(shuffled) * val_ratio))
    train_samples = shuffled[:-val_size] or shuffled
    val_samples = shuffled[-val_size:] if len(shuffled) > 1 else shuffled

    train_vectors = [sample["feature_vector"] for sample in train_samples]
    val_vectors = [sample["feature_vector"] for sample in val_samples]
    means, stds = _feature_stats(train_vectors)
    train_matrix = _normalize(train_vectors, means, stds)
    val_matrix = _normalize(val_vectors, means, stds)

    dimension_artifacts: dict[str, DimensionArtifact] = {}
    metrics: dict[str, Any] = {}
    for dimension in DIMENSIONS:
        train_labels = [float(sample["labels"][dimension]) for sample in train_samples]
        val_labels = [float(sample["labels"][dimension]) for sample in val_samples]
        intercept, weights = _train_ridge(
            train_matrix,
            train_labels,
            learning_rate=learning_rate,
            epochs=epochs,
            l2=l2,
        )
        train_predictions = [clamp(value, 0.0, 5.0) for value in _predict_matrix(intercept, weights, train_matrix)]
        val_predictions = [clamp(value, 0.0, 5.0) for value in _predict_matrix(intercept, weights, val_matrix)]
        artifact = DimensionArtifact(
            intercept=round(intercept, 6),
            weights={name: round(weight, 6) for name, weight in zip(FEATURE_NAMES, weights)},
            feature_means={name: round(value, 6) for name, value in means.items()},
            feature_stds={name: round(value, 6) for name, value in stds.items()},
            train_mae=round(mae(train_predictions, train_labels), 4),
            train_rmse=round(rmse(train_predictions, train_labels), 4),
            val_mae=round(mae(val_predictions, val_labels), 4),
            val_rmse=round(rmse(val_predictions, val_labels), 4),
            val_within_one=round(within_one(val_predictions, val_labels), 4),
        )
        dimension_artifacts[dimension] = artifact
        metrics[dimension] = {
            "train_mae": artifact.train_mae,
            "train_rmse": artifact.train_rmse,
            "val_mae": artifact.val_mae,
            "val_rmse": artifact.val_rmse,
            "val_within_one": artifact.val_within_one,
        }

    training_summary = {
        "feature_names": FEATURE_NAMES,
        "train_count": len(train_samples),
        "val_count": len(val_samples),
        "learning_rate": learning_rate,
        "epochs": epochs,
        "l2": l2,
        "metrics": metrics,
    }
    return TrainableScorerArtifact(
        version="trainable-ridge-v1",
        dimensions=dimension_artifacts,
        training_summary=training_summary,
    )
