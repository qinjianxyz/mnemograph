"""Conflict record helpers."""

import hashlib

from mnemograph.reconcile.engine import MergeDecision


def build_conflict_record(
    left_claim_id: str,
    right_claim_id: str,
    decision: MergeDecision,
) -> dict[str, str]:
    """Build a conflict record from a merge decision."""
    if not decision.conflict_type:
        raise ValueError("cannot build a conflict record without a conflict type")

    conflict_id = hashlib.sha256(
        f"{left_claim_id}|{right_claim_id}|{decision.conflict_type}".encode("utf-8")
    ).hexdigest()
    return {
        "conflict_id": conflict_id,
        "conflict_type": decision.conflict_type,
        "left_claim_id": left_claim_id,
        "right_claim_id": right_claim_id,
        "status": "pending",
        "resolution_policy": "review" if decision.requires_review else "preserve_both",
    }
