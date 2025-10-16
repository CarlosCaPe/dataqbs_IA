"""Simplified rubric heuristics.
In a real setting these would be loaded from authoritative docs or versioned guidelines.
"""
from __future__ import annotations

from typing import Dict, Tuple

# Expected ranges or soft thresholds for each dimension (0-5 scale for example)
RANGE = (0.0, 5.0)

DIMENSIONS = [
    "instructions",
    "accuracy",
    "optimality",
    "presentation",
    "freshness",
]

# Basic heuristics: name -> (ideal_mean, tolerance)
HEURISTICS: Dict[str, Tuple[float, float]] = {
    "instructions": (4.0, 1.5),
    "accuracy": (4.2, 1.2),
    "optimality": (3.8, 1.4),
    "presentation": (4.0, 1.2),
    "freshness": (3.5, 1.5),
}


def clamp(value: float) -> float:
    lo, hi = RANGE
    return max(lo, min(hi, value))


def suggest_adjustment(value: float, dim: str) -> float:
    ideal, tol = HEURISTICS.get(dim, (3.5, 1.5))
    # If within tolerance: keep, else pull 40% toward ideal
    if abs(value - ideal) <= tol:
        return value
    return clamp(value + 0.4 * (ideal - value))
