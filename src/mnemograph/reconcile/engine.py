"""Deterministic-first reconciliation engine."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ClaimInput:
    claim_id: str
    subject: str
    predicate: str
    object_value: str
    object_type: str = "literal"
    valid_time_start: str | None = None
    source_trust: float = 0.5
    source_timestamp: str | None = None
    entity_resolution_score: float = 1.0


@dataclass(frozen=True)
class MergeDecision:
    action: str
    conflict_type: str | None
    insert_candidate: bool
    supersede_existing: bool
    requires_review: bool


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


def _same_fact_slot(existing: ClaimInput, candidate: ClaimInput) -> bool:
    return existing.subject == candidate.subject and existing.predicate == candidate.predicate


def decide_merge(existing: ClaimInput, candidate: ClaimInput) -> MergeDecision:
    """Return the deterministic merge decision for an incoming claim."""
    if candidate.entity_resolution_score < 0.9 and existing.subject != candidate.subject:
        return MergeDecision(
            action="NONE",
            conflict_type="entity_resolution_conflict",
            insert_candidate=False,
            supersede_existing=False,
            requires_review=True,
        )

    if not _same_fact_slot(existing, candidate):
        return MergeDecision(
            action="ADD",
            conflict_type=None,
            insert_candidate=True,
            supersede_existing=False,
            requires_review=False,
        )

    if existing.object_value == candidate.object_value:
        return MergeDecision(
            action="NONE",
            conflict_type=None,
            insert_candidate=False,
            supersede_existing=False,
            requires_review=False,
        )

    existing_valid = _parse_timestamp(existing.valid_time_start)
    candidate_valid = _parse_timestamp(candidate.valid_time_start)
    if existing_valid and candidate_valid and candidate_valid > existing_valid:
        return MergeDecision(
            action="SUPERSEDE",
            conflict_type="temporal_conflict",
            insert_candidate=True,
            supersede_existing=True,
            requires_review=False,
        )

    existing_seen = _parse_timestamp(existing.source_timestamp)
    candidate_seen = _parse_timestamp(candidate.source_timestamp)
    if (
        candidate.source_trust > existing.source_trust
        and candidate_seen
        and existing_seen
        and candidate_seen > existing_seen
    ):
        return MergeDecision(
            action="SUPERSEDE",
            conflict_type="value_conflict",
            insert_candidate=True,
            supersede_existing=True,
            requires_review=False,
        )

    if abs(candidate.source_trust - existing.source_trust) <= 0.1:
        return MergeDecision(
            action="CONTRADICT",
            conflict_type="source_quality_conflict",
            insert_candidate=True,
            supersede_existing=False,
            requires_review=False,
        )

    return MergeDecision(
        action="CONTRADICT",
        conflict_type="value_conflict",
        insert_candidate=True,
        supersede_existing=False,
        requires_review=False,
    )
