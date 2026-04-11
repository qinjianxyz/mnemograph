"""Qdrant projection helpers."""

from collections.abc import Callable
from dataclasses import dataclass


class ProjectionError(RuntimeError):
    """Raised when a derived projection fails."""


def project_claim_to_point(claim: dict, vector: list[float]) -> dict:
    """Convert one canonical claim into a Qdrant-compatible point payload."""
    return {
        "id": claim["claim_id"],
        "vector": vector,
        "payload": {
            "claim_id": claim["claim_id"],
            "subject_entity_id": claim["subject_entity_id"],
            "predicate_id": claim["predicate_id"],
            "object_type": claim["object_type"],
            "object_entity_id": claim.get("object_entity_id"),
            "object_value": claim["object_value"],
            "claim_text": claim["claim_text"],
            "domain": claim["domain"],
            "confidence": float(claim.get("confidence", 0.0)),
            "status": claim.get("status", "active"),
            "source_id": claim.get("source_id"),
            "extraction_run_id": claim.get("extraction_run_id"),
            "valid_time_start": claim.get("valid_time_start"),
            "valid_time_end": claim.get("valid_time_end"),
        },
    }


@dataclass(frozen=True)
class QdrantProjectionAdapter:
    """Retry-safe adapter boundary for vector projection."""

    sender: Callable[..., None]
    retries: int = 0

    def project_claims(self, claims: list[dict], vector_lookup: dict[str, list[float]]) -> list[dict]:
        batch = [
            project_claim_to_point(claim, vector_lookup[claim["claim_id"]])
            for claim in claims
            if claim["claim_id"] in vector_lookup
        ]
        if not batch:
            return []

        last_error: Exception | None = None
        for _ in range(self.retries + 1):
            try:
                self.sender(batch)
                return batch
            except Exception as exc:  # pragma: no cover - exercised via adapter failure test
                last_error = exc
        raise ProjectionError(f"qdrant projection failed: {last_error}") from last_error
