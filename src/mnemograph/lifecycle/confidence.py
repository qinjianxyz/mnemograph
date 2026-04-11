"""Confidence scoring helpers."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ConfidenceInputs:
    trust: float
    evidence: float
    extraction: float
    recency: float
    contradiction: float
    confirmation: float
    unresolved_value_conflict: bool = False
    single_low_trust_source: bool = False


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def compute_confidence(
    inputs: ConfidenceInputs,
    floor: float = 0.05,
    component_floor: float = 0.10,
) -> float:
    """Compute the weighted clamped confidence score."""
    components = {
        "trust": _clamp(inputs.trust),
        "evidence": _clamp(inputs.evidence),
        "extraction": _clamp(inputs.extraction),
        "recency": _clamp(inputs.recency),
        "contradiction": _clamp(inputs.contradiction),
        "confirmation": _clamp(inputs.confirmation),
    }
    weights = {
        "trust": 0.25,
        "evidence": 0.20,
        "extraction": 0.20,
        "recency": 0.15,
        "contradiction": 0.10,
        "confirmation": 0.10,
    }

    score = 1.0
    for key, weight in weights.items():
        score *= max(components[key], component_floor) ** weight
    score = max(floor, score)

    if inputs.unresolved_value_conflict:
        score = min(score, 0.60)
    if inputs.single_low_trust_source:
        score = min(score, 0.30)

    return round(score, 6)


def confidence_band(score: float) -> str:
    """Map a scalar confidence score to a presentation band."""
    if score >= 0.8:
        return "high"
    if score >= 0.5:
        return "medium"
    return "low"
