"""Minimal ingest pipeline for writing extracted memory into canon."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3

from mnemograph.db import bootstrap_db
from mnemograph.ingest.chunk import TextChunk, chunk_text
from mnemograph.ingest.register import compute_content_hash, register_source
from mnemograph.lifecycle.confidence import ConfidenceInputs, compute_confidence
from mnemograph.llm.client import StructuredLLMClient
from mnemograph.prompts.contracts import validate_extraction_payload
from mnemograph.prompts.extract import build_extraction_prompt
from mnemograph.reconcile.conflicts import build_conflict_record
from mnemograph.reconcile.engine import ClaimInput, decide_merge
from mnemograph.reconcile.predicates import resolve_predicate


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _stable_id(*parts: str) -> str:
    joined = "|".join(parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


HIGH_SPECIFICITY_PREDICATES = {
    "price_usd_monthly",
    "has_ceo",
    "has_founder",
    "headquartered_in",
    "founded_date",
}
MEDIUM_SPECIFICITY_PREDICATES = {
    "has_product",
    "has_feature",
    "uses_framework",
}
KNOWN_STRUCTURED_PREDICATES = HIGH_SPECIFICITY_PREDICATES | MEDIUM_SPECIFICITY_PREDICATES
COMMON_VERBS = {
    "is",
    "are",
    "was",
    "were",
    "be",
    "offers",
    "offer",
    "provides",
    "provide",
    "costs",
    "cost",
    "charges",
    "charge",
    "uses",
    "use",
    "leads",
    "lead",
    "founded",
    "headquartered",
    "supports",
    "support",
    "deploys",
    "deploy",
    "powers",
    "power",
    "led",
}
MARKETING_PHRASES = (
    "in seconds",
    "for every team",
    "scales automatically",
    "developer experience",
    "build faster",
    "ship faster",
    "not specified",
    "not available",
    "not mentioned",
)
IMPERATIVE_MARKETING_STARTS = (
    "build ",
    "deploy ",
    "scale ",
    "ship ",
    "make ",
)
PRICING_PLACEHOLDER_PHRASES = (
    "contact sales",
    "talk to sales",
    "on request",
    "request pricing",
    "custom pricing",
)


def _normalize_object_key(object_type: str, object_value: str) -> str:
    normalized_value = object_value.strip().lower()
    return f"{object_type}:{normalized_value}"


def normalized_spo_key(subject: str, predicate: str, object_type: str, object_value: str) -> str:
    """Return the stable SPO hash used for canonical claims."""
    joined = "|".join(
        (
            subject.strip().lower(),
            predicate.strip().lower(),
            _normalize_object_key(object_type, object_value),
        )
    )
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def _infer_entity(entity_id: str) -> dict[str, str]:
    prefix, _, suffix = entity_id.partition(":")
    entity_type = prefix.lower() if prefix else "entity"
    canonical_name = suffix.replace("_", " ") if suffix else entity_id
    return {
        "entity_id": entity_id,
        "entity_type": entity_type,
        "canonical_name": canonical_name,
        "namespace": "default",
        "status": "active",
    }


def _upsert_entity(connection: sqlite3.Connection, entity: dict) -> None:
    connection.execute(
        """
        INSERT OR IGNORE INTO entities (
            entity_id, entity_type, canonical_name, namespace, status, aliases, external_ids, merge_confidence
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            entity["entity_id"],
            entity.get("entity_type", "entity"),
            entity.get("canonical_name", entity["entity_id"]),
            entity.get("namespace", "default"),
            entity.get("status", "active"),
            json.dumps(entity.get("aliases", [])),
            json.dumps(entity.get("external_ids", {})),
            entity.get("merge_confidence"),
        ),
    )


@dataclass(frozen=True)
class IngestResult:
    source_id: str
    extraction_run_id: str
    claim_ids: list[str]
    chunk_ids: list[str]
    open_questions: list[dict] = field(default_factory=list)


def _trust_score(trust_tier: str) -> float:
    return {
        "low": 0.3,
        "secondary": 0.6,
        "primary": 0.8,
        "authoritative": 0.95,
        "user": 0.85,
        "baseline": 0.7,
    }.get(trust_tier, 0.5)


def _source_trust_score(source_type: str, trust_tier: str) -> float:
    source_defaults = {
        "baseline": 0.70,
        "url": 0.75,
        "text": 0.80,
        "document": 0.85,
        "user": 0.90,
    }
    source_score = source_defaults.get(source_type)
    tier_score = _trust_score(trust_tier)
    if source_score is None:
        return tier_score
    return min(source_score, tier_score)


def _extraction_certainty(predicate_id: str) -> float:
    if predicate_id in HIGH_SPECIFICITY_PREDICATES:
        return 0.90
    if predicate_id in MEDIUM_SPECIFICITY_PREDICATES:
        return 0.80
    return 0.60


def _recency_score(source_timestamp: str, reference_timestamp: str) -> float:
    parsed_source = datetime.fromisoformat(source_timestamp)
    parsed_reference = datetime.fromisoformat(reference_timestamp)
    age_seconds = max(0.0, (parsed_reference - parsed_source).total_seconds())
    age_days = age_seconds / 86400.0
    decay = math.pow(0.5, age_days / 30.0)
    return max(0.5, min(1.0, 0.5 + 0.5 * decay))


def _evidence_strength_by_claim(payload: dict) -> dict[str, float]:
    strengths: dict[str, float] = {}
    for evidence in payload.get("evidence_spans", []):
        claim_id = evidence.get("claim_id")
        if not claim_id:
            continue
        strengths[claim_id] = max(
            strengths.get(claim_id, 0.0),
            float(evidence.get("evidence_strength", 0.7)),
        )
    return strengths


def _looks_like_fragment(text: str) -> bool:
    tokens = re.findall(r"[A-Za-z']+", text)
    if not tokens:
        return True
    lowered_tokens = {token.lower() for token in tokens}
    has_verb = any(token in COMMON_VERBS for token in lowered_tokens)
    if has_verb:
        return False
    return len(tokens) <= 4


def _is_low_signal_claim(claim: dict) -> bool:
    claim_text = " ".join(claim.get("claim_text", "").split())
    predicate = claim.get("predicate", "")
    object_value = str(claim.get("object", "")).strip().lower()
    if not claim.get("subject", "").strip():
        return True
    lowered = claim_text.lower()
    if (
        predicate == "price_usd_monthly"
        and any(phrase in lowered for phrase in PRICING_PLACEHOLDER_PHRASES)
        and not re.search(r"\d", lowered)
    ):
        return True
    if predicate == "price_usd_monthly" and object_value in {"unknown", "contact_sales", "talk_to_sales", "custom", "on_request"}:
        return True
    if any(phrase in lowered for phrase in ("not specified", "not available", "not mentioned", "unknown")):
        return True
    if len(claim_text) > 120 and predicate not in KNOWN_STRUCTURED_PREDICATES:
        return True
    if predicate not in KNOWN_STRUCTURED_PREDICATES and any(phrase in lowered for phrase in MARKETING_PHRASES):
        return True
    if predicate not in HIGH_SPECIFICITY_PREDICATES and lowered.startswith(IMPERATIVE_MARKETING_STARTS):
        return True
    return _looks_like_fragment(claim_text)


def _filter_extracted_claims(payload: dict) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    retained_claims: list[dict] = []
    rejected_open_questions: list[dict] = list(payload.get("open_questions", []))
    rejected_claim_ids: set[str] = set()

    for claim in payload.get("claims", []):
        if _is_low_signal_claim(claim):
            rejected_claim_ids.add(claim.get("claim_id", ""))
            rejected_open_questions.append(
                {
                    "question": f"What is {claim.get('claim_text', '').strip()}?",
                    "domain": claim.get("domain", "unknown"),
                    "reason": "extracted text appears to be a tagline, not a structured fact",
                }
            )
            continue
        retained_claims.append(claim)

    retained_claim_id_set = {claim.get("claim_id", "") for claim in retained_claims}
    retained_evidence = [
        evidence
        for evidence in payload.get("evidence_spans", [])
        if evidence.get("claim_id", "") in retained_claim_id_set
    ]
    referenced_entity_ids = {
        claim["subject"]
        for claim in retained_claims
        if claim.get("subject")
    }
    referenced_entity_ids.update(
        claim["object"]
        for claim in retained_claims
        if claim.get("object_type") == "entity" and claim.get("object")
    )
    retained_entities = [
        entity
        for entity in payload.get("entities", [])
        if entity.get("entity_id") in referenced_entity_ids
    ]
    return retained_entities, retained_claims, retained_evidence, rejected_open_questions


def _claim_confidence(
    claim: dict,
    source_type: str,
    trust_tier: str,
    source_timestamp: str,
    reference_timestamp: str,
    evidence_strength: float,
    contradiction: float = 1.0,
    unresolved_value_conflict: bool = False,
) -> float:
    source_trust = _source_trust_score(source_type, trust_tier)
    return compute_confidence(
        ConfidenceInputs(
            trust=source_trust,
            evidence=evidence_strength,
            extraction=_extraction_certainty(claim["predicate"]),
            recency=_recency_score(source_timestamp, reference_timestamp),
            contradiction=contradiction,
            confirmation=1.0 if source_type == "user" else 0.5,
            unresolved_value_conflict=unresolved_value_conflict,
            single_low_trust_source=source_trust < 0.5,
        )
    )


def _write_source_chunks(
    connection: sqlite3.Connection,
    source_id: str,
    chunks: list[TextChunk],
) -> list[str]:
    chunk_ids: list[str] = []
    for chunk in chunks:
        chunk_id = _stable_id(source_id, str(chunk.chunk_index), compute_content_hash(chunk.text))
        chunk_ids.append(chunk_id)
        connection.execute(
            """
            INSERT OR IGNORE INTO source_chunks (
                chunk_id, source_id, chunk_index, text, text_hash, start_offset, end_offset, embedding_profile, projection_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                chunk_id,
                source_id,
                chunk.chunk_index,
                chunk.text,
                compute_content_hash(chunk.text),
                None,
                None,
                None,
                "pending",
            ),
        )
    return chunk_ids


def _insert_memory_change(
    connection: sqlite3.Connection,
    change_type: str,
    subject_claim_id: str,
    related_claim_id: str | None,
    trigger_source_id: str,
    created_at: str,
    reason_code: str,
) -> None:
    change_id = _stable_id(
        "memory_change",
        change_type,
        subject_claim_id,
        related_claim_id or "",
        trigger_source_id,
        reason_code,
    )
    connection.execute(
        """
        INSERT OR IGNORE INTO memory_changes (
            change_id, change_type, subject_claim_id, related_claim_id,
            trigger_source_id, created_at, reason_code
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            change_id,
            change_type,
            subject_claim_id,
            related_claim_id,
            trigger_source_id,
            created_at,
            reason_code,
        ),
    )


def _insert_claim(
    connection: sqlite3.Connection,
    claim: dict,
    predicate_id: str,
    extraction_run_id: str,
    system_time_start: str,
    claim_id: str,
    status: str,
    confidence: float,
) -> None:
    connection.execute(
        """
        INSERT OR IGNORE INTO claims (
            claim_id, subject_entity_id, predicate_id, object_type, object_entity_id, object_value,
            normalized_spo_key, claim_text, domain, memory_type, status, valid_time_start,
            valid_time_end, system_time_start, system_time_end, confidence, support_count,
            user_confirmed, provisional_predicate, extraction_run_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            claim_id,
            claim["subject"],
            predicate_id,
            claim["object_type"],
            claim["object"] if claim["object_type"] == "entity" else None,
            claim["object"],
            normalized_spo_key(
                claim["subject"],
                predicate_id,
                claim["object_type"],
                claim["object"],
            ),
            claim["claim_text"],
            claim["domain"],
            claim.get("memory_type", "semantic"),
            status,
            claim.get("valid_time_start"),
            claim.get("valid_time_end"),
            system_time_start,
            None,
            confidence,
            1,
            0,
            1 if claim.get("provisional_predicate", False) else 0,
            extraction_run_id,
        ),
    )


def _load_existing_active_claim(
    connection: sqlite3.Connection,
    subject: str,
    predicate_id: str,
) -> ClaimInput | None:
    row = connection.execute(
        """
        SELECT
            claims.claim_id,
            claims.subject_entity_id,
            claims.predicate_id,
            claims.object_value,
            claims.object_type,
            claims.valid_time_start,
            sources.source_type,
            sources.trust_tier,
            extraction_runs.completed_at
        FROM claims
        JOIN extraction_runs ON extraction_runs.extraction_run_id = claims.extraction_run_id
        JOIN sources ON sources.source_id = extraction_runs.source_id
        WHERE claims.subject_entity_id = ? AND claims.predicate_id = ? AND claims.status = 'active'
        ORDER BY claims.system_time_start DESC
        LIMIT 1
        """,
        (subject, predicate_id),
    ).fetchone()
    if not row:
        return None
    return ClaimInput(
        claim_id=row[0],
        subject=row[1],
        predicate=row[2],
        object_value=row[3],
        object_type=row[4],
        valid_time_start=row[5],
        source_trust=_source_trust_score(row[6], row[7]),
        source_timestamp=row[8],
    )


def ingest_text_source(
    db_path: str | Path,
    locator: str,
    content: str,
    llm_client: StructuredLLMClient,
    source_type: str = "text",
    trust_tier: str = "primary",
    model_name: str = "mock-structured",
    prompt_version: str = "v1",
    parent_source_id: str | None = None,
    render_mode: str = "static",
    status_code: int = 200,
    precomputed_payload: dict | None = None,
) -> IngestResult:
    """Ingest one text source into the canonical store."""
    bootstrap_db(db_path)
    source = register_source(source_type=source_type, locator=locator, content=content)
    chunks = chunk_text(content)
    now = _utc_now()
    extraction_run_id = _stable_id(source.source_id, model_name, prompt_version, compute_content_hash(content))

    with sqlite3.connect(db_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            """
            INSERT OR IGNORE INTO sources (
                source_id, source_type, locator, normalized_locator, content_hash, ingested_at, fetched_at,
                trust_tier, render_mode, status_code, parent_source_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source.source_id,
                source.source_type,
                source.locator,
                source.normalized_locator,
                source.content_hash,
                now,
                now,
                trust_tier,
                render_mode,
                status_code,
                parent_source_id,
            ),
        )

        chunk_ids = _write_source_chunks(connection, source.source_id, chunks)
        connection.execute(
            """
            INSERT OR IGNORE INTO extraction_runs (
                extraction_run_id, source_id, run_kind, model_name, prompt_version, status,
                started_at, completed_at, chunk_batch, cost_estimate_usd, error_summary
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                extraction_run_id,
                source.source_id,
                "initial_ingest",
                model_name,
                prompt_version,
                "completed",
                now,
                now,
                json.dumps(chunk_ids),
                0.0,
                None,
            ),
        )

        claim_ids: list[str] = []
        open_questions: list[dict] = []
        claim_id_map: dict[str, str] = {}
        for chunk_index, (chunk_id, chunk) in enumerate(zip(chunk_ids, chunks, strict=False)):
            chunk_claim_ids: list[str] = []
            if precomputed_payload is not None:
                payload = validate_extraction_payload(
                    precomputed_payload
                    if chunk_index == 0
                    else {
                        "entities": [],
                        "claims": [],
                        "evidence_spans": [],
                        "open_questions": [],
                    }
                )
            else:
                payload = validate_extraction_payload(
                    llm_client.generate_structured(
                        operation="extract",
                        prompt=build_extraction_prompt(
                            chunk.text,
                            compact=getattr(llm_client, "prompt_profile", "full") == "compact",
                            profile="conversation" if source_type == "conversation" else "document",
                        ),
                        required_keys=("entities", "claims", "evidence_spans"),
                    )
                )
            evidence_strengths = _evidence_strength_by_claim(payload)
            entities, claims, evidence_spans, chunk_open_questions = _filter_extracted_claims(payload)
            open_questions.extend(chunk_open_questions)

            for entity in entities:
                _upsert_entity(connection, {**_infer_entity(entity["entity_id"]), **entity})

            for claim_index, claim in enumerate(claims):
                _upsert_entity(connection, _infer_entity(claim["subject"]))
                if claim["object_type"] == "entity":
                    _upsert_entity(connection, _infer_entity(claim["object"]))

                predicate_record = resolve_predicate(
                    connection,
                    domain=claim["domain"],
                    proposed_name=claim["predicate"],
                    provisional=claim.get("provisional_predicate", False),
                )
                predicate_id = predicate_record["predicate_id"]

                canonical_claim_id = _stable_id(
                    extraction_run_id,
                    claim.get("claim_id", str(claim_index)),
                    normalized_spo_key(
                        claim["subject"],
                        predicate_id,
                        claim["object_type"],
                        claim["object"],
                    ),
                )
                if "claim_id" in claim:
                    claim_id_map[claim["claim_id"]] = canonical_claim_id
                existing_claim = _load_existing_active_claim(
                    connection,
                    subject=claim["subject"],
                    predicate_id=predicate_id,
                )
                candidate_claim = ClaimInput(
                    claim_id=canonical_claim_id,
                    subject=claim["subject"],
                    predicate=predicate_id,
                    object_value=claim["object"],
                    object_type=claim["object_type"],
                    valid_time_start=claim.get("valid_time_start"),
                    source_trust=_source_trust_score(source_type, trust_tier),
                    source_timestamp=now,
                )

                if existing_claim is None:
                    claim_confidence = _claim_confidence(
                        claim=claim,
                        source_type=source_type,
                        trust_tier=trust_tier,
                        source_timestamp=now,
                        reference_timestamp=now,
                        evidence_strength=evidence_strengths.get(claim.get("claim_id", ""), 0.7),
                    )
                    _insert_claim(
                        connection,
                        claim=claim,
                        predicate_id=predicate_id,
                        extraction_run_id=extraction_run_id,
                        system_time_start=now,
                        claim_id=canonical_claim_id,
                        status=claim.get("status", "active"),
                        confidence=claim_confidence,
                    )
                    _insert_memory_change(
                        connection,
                        change_type="ADDED",
                        subject_claim_id=canonical_claim_id,
                        related_claim_id=None,
                        trigger_source_id=source.source_id,
                        created_at=now,
                        reason_code="new_claim",
                    )
                    claim_ids.append(canonical_claim_id)
                    chunk_claim_ids.append(canonical_claim_id)
                    continue

                decision = decide_merge(existing_claim, candidate_claim)
                if decision.action == "NONE" and not decision.conflict_type:
                    if "claim_id" in claim:
                        claim_id_map[claim["claim_id"]] = existing_claim.claim_id
                    chunk_claim_ids.append(existing_claim.claim_id)
                    connection.execute(
                        "UPDATE claims SET support_count = support_count + 1 WHERE claim_id = ?",
                        (existing_claim.claim_id,),
                    )
                    continue

                inserted_status = "pending_review" if decision.requires_review else "active"
                claim_confidence = _claim_confidence(
                    claim=claim,
                    source_type=source_type,
                    trust_tier=trust_tier,
                    source_timestamp=now,
                    reference_timestamp=now,
                    evidence_strength=evidence_strengths.get(claim.get("claim_id", ""), 0.7),
                    contradiction=0.6 if decision.conflict_type else 1.0,
                    unresolved_value_conflict=decision.conflict_type == "value_conflict" and decision.requires_review,
                )
                _insert_claim(
                    connection,
                    claim=claim,
                    predicate_id=predicate_id,
                    extraction_run_id=extraction_run_id,
                    system_time_start=now,
                    claim_id=canonical_claim_id,
                    status=inserted_status,
                    confidence=claim_confidence,
                )
                claim_ids.append(canonical_claim_id)
                chunk_claim_ids.append(canonical_claim_id)

                if decision.supersede_existing:
                    connection.execute(
                        "UPDATE claims SET status = 'superseded' WHERE claim_id = ?",
                        (existing_claim.claim_id,),
                    )
                    _insert_memory_change(
                        connection,
                        change_type="SUPERSEDED",
                        subject_claim_id=canonical_claim_id,
                        related_claim_id=existing_claim.claim_id,
                        trigger_source_id=source.source_id,
                        created_at=now,
                        reason_code=decision.conflict_type or decision.action.lower(),
                    )
                else:
                    _insert_memory_change(
                        connection,
                        change_type="ADDED" if not decision.conflict_type else "CONFLICT",
                        subject_claim_id=canonical_claim_id,
                        related_claim_id=existing_claim.claim_id if decision.conflict_type else None,
                        trigger_source_id=source.source_id,
                        created_at=now,
                        reason_code=decision.conflict_type or decision.action.lower(),
                    )

                if decision.conflict_type:
                    conflict = build_conflict_record(
                        existing_claim.claim_id,
                        canonical_claim_id,
                        decision,
                    )
                    connection.execute(
                        """
                        INSERT OR IGNORE INTO conflicts (
                            conflict_id, conflict_type, left_claim_id, right_claim_id,
                            status, resolution_policy, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            conflict["conflict_id"],
                            conflict["conflict_type"],
                            conflict["left_claim_id"],
                            conflict["right_claim_id"],
                            conflict["status"],
                            conflict["resolution_policy"],
                            now,
                        ),
                    )

            for evidence_index, evidence in enumerate(evidence_spans):
                referenced_claim_id = claim_id_map.get(evidence["claim_id"])
                if referenced_claim_id is None and chunk_claim_ids:
                    referenced_claim_id = (
                        chunk_claim_ids[evidence_index]
                        if evidence_index < len(chunk_claim_ids)
                        else chunk_claim_ids[0]
                    )
                if referenced_claim_id is None:
                    continue
                evidence_id = _stable_id(
                    extraction_run_id,
                    "evidence",
                    str(evidence_index),
                    referenced_claim_id,
                )
                connection.execute(
                    """
                    INSERT OR IGNORE INTO evidence_spans (
                        evidence_id, claim_id, extraction_run_id, source_id, chunk_id,
                        quote_text, start_offset, end_offset, evidence_strength
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        evidence_id,
                        referenced_claim_id,
                        extraction_run_id,
                        source.source_id,
                        chunk_id,
                        evidence["quote_text"],
                        evidence.get("start_offset"),
                        evidence.get("end_offset"),
                        evidence.get("evidence_strength", 1.0),
                    ),
                )

        connection.commit()

    return IngestResult(
        source_id=source.source_id,
        extraction_run_id=extraction_run_id,
        claim_ids=claim_ids,
        chunk_ids=chunk_ids,
        open_questions=open_questions,
    )
