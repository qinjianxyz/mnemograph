"""Grafeo projection helpers."""

from collections.abc import Callable
from dataclasses import dataclass

from mnemograph.adapters.qdrant import ProjectionError


def project_claim_to_graph_record(claim: dict) -> dict:
    """Convert one canonical claim into a graph-friendly record."""
    object_id = claim.get("object_entity_id") or claim["object_value"]
    object_kind = "entity" if claim["object_type"] == "entity" else "literal"
    return {
        "claim_node": {
            "id": claim["claim_id"],
            "kind": "claim",
            "text": claim["claim_text"],
            "domain": claim["domain"],
            "confidence": float(claim.get("confidence", 0.0)),
            "status": claim.get("status", "active"),
            "source_id": claim.get("source_id"),
            "extraction_run_id": claim.get("extraction_run_id"),
        },
        "subject_node": {
            "id": claim["subject_entity_id"],
            "kind": "entity",
        },
        "object_node": {
            "id": object_id,
            "kind": object_kind,
            "value": claim["object_value"],
        },
        "edge": {
            "claim_id": claim["claim_id"],
            "subject_id": claim["subject_entity_id"],
            "object_id": object_id,
            "predicate": claim["predicate_id"],
            "object_type": claim["object_type"],
            "domain": claim["domain"],
            "confidence": float(claim.get("confidence", 0.0)),
            "valid_time_start": claim.get("valid_time_start"),
            "valid_time_end": claim.get("valid_time_end"),
        },
    }


@dataclass(frozen=True)
class GrafeoProjectionAdapter:
    """Retry-safe adapter boundary for graph projection."""

    sender: Callable[..., None]
    retries: int = 0

    def project_claims(self, claims: list[dict]) -> list[dict]:
        batch = [project_claim_to_graph_record(claim) for claim in claims]
        if not batch:
            return []

        last_error: Exception | None = None
        for _ in range(self.retries + 1):
            try:
                self.sender(batch)
                return batch
            except Exception as exc:  # pragma: no cover - same retry path as qdrant
                last_error = exc
        raise ProjectionError(f"grafeo projection failed: {last_error}") from last_error
