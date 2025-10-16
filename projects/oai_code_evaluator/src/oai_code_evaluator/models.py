from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ModelResponse:
    id: str
    text: str
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AttemptRatings:
    instructions: float
    accuracy: float
    optimality: float
    presentation: float
    freshness: float  # "Actualización"
    justification: str = ""


@dataclass
class AttemptSubmission:
    prompt: str
    category: str
    subcategory: str
    difficulty: str
    responses: List[ModelResponse]
    ranking: List[str]  # ordered list of response IDs (best -> worst)
    ranking_rationale: str
    rewrite_preferred: str  # rewrite the attempter produced for the preferred answer
    ratings: AttemptRatings
    evidence: Optional[str] = None  # e.g., code execution output


@dataclass
class EvaluationInput:
    submission: AttemptSubmission
    # Potentially future fields: guidelines version, rubric mapping, etc.


@dataclass
class DimensionCorrection:
    original: float
    updated: float
    rationale: str


@dataclass
class EvaluationResult:
    corrected_ratings: Dict[str, DimensionCorrection]
    corrected_ranking: List[str]
    ranking_feedback: str
    rewrite_final: str
    prompt_feedback: str
    global_summary: str
    meta: Dict[str, Any] = field(default_factory=dict)
    fired_rules: List[Dict[str, Any]] = field(default_factory=list)
    # Nuevos campos para pipeline extendido
    score: float | None = None
    flags: Dict[str, bool] = field(default_factory=dict)
    label: str | None = None
