"""Decay and archival helpers."""

from dataclasses import dataclass, replace
from datetime import UTC, datetime
import math


@dataclass(frozen=True)
class DecayCandidate:
    claim_id: str
    confidence: float
    created_at: datetime
    last_retrieved_at: datetime | None
    user_confirmed: bool
    support_count: int
    status: str
    valid_time_end: datetime | None = None
    historical_temporal: bool = False


def apply_decay(
    candidate: DecayCandidate,
    as_of: datetime,
    weekly_factor: float = 0.95,
    archive_threshold: float = 0.10,
) -> DecayCandidate:
    """Apply decay to a claim candidate when policy allows it."""
    if candidate.user_confirmed or candidate.support_count > 3 or candidate.historical_temporal:
        return candidate

    anchor = candidate.last_retrieved_at or candidate.created_at
    if anchor.tzinfo is None:
        anchor = anchor.replace(tzinfo=UTC)
    if as_of.tzinfo is None:
        as_of = as_of.replace(tzinfo=UTC)

    days_elapsed = max(0.0, (as_of - anchor).total_seconds() / 86400)
    weeks_elapsed = days_elapsed / 7.0
    if weeks_elapsed <= 0:
        return candidate

    decayed_confidence = candidate.confidence * math.pow(weekly_factor, weeks_elapsed)
    status = "archived" if decayed_confidence < archive_threshold else candidate.status
    return replace(candidate, confidence=decayed_confidence, status=status)
