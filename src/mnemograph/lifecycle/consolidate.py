"""Claim consolidation helpers."""

from datetime import UTC, datetime
import hashlib


def should_consolidate(claims: list[dict], threshold: int = 10) -> bool:
    """Return whether a claim neighborhood is eligible for consolidation."""
    active_atomic = [
        claim
        for claim in claims
        if claim.get("status") == "active" and claim.get("record_type", "atomic") == "atomic"
    ]
    return len(active_atomic) > threshold


def build_summary_claim(subject_entity_id: str, domain: str, claims: list[dict]) -> dict:
    """Create a summary claim that points back to the atomic claims."""
    contributing_ids = [claim["claim_id"] for claim in claims]
    digest = hashlib.sha256("|".join(contributing_ids).encode("utf-8")).hexdigest()[:12]
    return {
        "claim_id": f"summary:{subject_entity_id}:{domain}:{digest}",
        "subject_entity_id": subject_entity_id,
        "domain": domain,
        "record_type": "summary",
        "status": "active",
        "preferred_for_retrieval": True,
        "contributing_claim_ids": contributing_ids,
        "claim_text": f"Summary for {subject_entity_id} in {domain}",
        "last_consolidated_at": datetime.now(UTC).isoformat(),
    }


def preferred_retrieval_claims(claims: list[dict]) -> list[dict]:
    """Return the preferred retrieval surface after consolidation."""
    summaries = [claim for claim in claims if claim.get("record_type") == "summary"]
    if summaries:
        return summaries
    return [
        claim
        for claim in claims
        if claim.get("status") == "active" and claim.get("record_type", "atomic") == "atomic"
    ]
