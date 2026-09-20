"""Selective-risk and pairwise consistency utilities."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class RiskCoveragePoint:
    coverage: float
    risk: float
    threshold: float

    def as_dict(self) -> dict[str, float]:
        return {
            "coverage": self.coverage,
            "risk": self.risk,
            "threshold": self.threshold,
        }


def confidence_from_probabilities(probabilities: Mapping[str, float]) -> float:
    if not probabilities:
        raise ValueError("probabilities must not be empty")
    return max(float(value) for value in probabilities.values())


def risk_coverage_curve(
    correct: Sequence[bool],
    confidence: Sequence[float],
) -> list[RiskCoveragePoint]:
    if len(correct) != len(confidence) or not correct:
        raise ValueError("correct and confidence must be non-empty and equally sized")
    ranked = sorted(enumerate(confidence), key=lambda item: (-item[1], item[0]))
    points = [RiskCoveragePoint(coverage=0.0, risk=0.0, threshold=1.0)]
    correct_count = 0
    for rank, (index, score) in enumerate(ranked, start=1):
        correct_count += int(correct[index])
        points.append(
            RiskCoveragePoint(
                coverage=rank / len(correct),
                risk=1.0 - correct_count / rank,
                threshold=float(score),
            )
        )
    return points


def coverage_at_target_error(
    correct: Sequence[bool],
    confidence: Sequence[float],
    target_error: float,
) -> float:
    if not 0 <= target_error <= 1:
        raise ValueError("target_error must be in [0, 1]")
    points = risk_coverage_curve(correct, confidence)
    return max(point.coverage for point in points if point.risk <= target_error)


def swap_consistency(original_labels: Sequence[str], swapped_labels: Sequence[str]) -> float:
    if len(original_labels) != len(swapped_labels) or not original_labels:
        raise ValueError("swap label sequences must be non-empty and equally sized")
    inverse = {"A": "B", "B": "A", "TIE": "TIE"}
    expected = [inverse.get(label, label) for label in original_labels]
    return sum(actual == wanted for actual, wanted in zip(swapped_labels, expected, strict=True)) / len(expected)
