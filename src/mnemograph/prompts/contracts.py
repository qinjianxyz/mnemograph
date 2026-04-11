"""Validation contracts for structured extraction payloads."""


CLAIM_REQUIRED_FIELDS = (
    "subject",
    "predicate",
    "object",
    "object_type",
    "claim_text",
    "domain",
    "extraction_run_id",
)

EVIDENCE_REQUIRED_FIELDS = (
    "claim_id",
    "quote_text",
    "source_id",
    "chunk_id",
    "extraction_run_id",
)


def _canonical_entity_id(entity_type: str, name: str) -> str:
    normalized_type = entity_type.strip().title() or "Entity"
    normalized_name = name.strip().replace(" ", "_")
    return f"{normalized_type}:{normalized_name}"


def _default_claim_domain(predicate: str) -> str:
    predicate_domains = {
        "bought_item": "personal",
        "attended_event": "event",
        "had_issue": "task",
        "has_phone_number": "contact",
        "owns_device": "personal",
        "prefers": "preference",
        "recommended_item": "task",
        "recommended_item_at_position": "task",
        "scheduled_for_date": "event",
        "works_as": "personal",
    }
    return predicate_domains.get(predicate, "unknown")


def _uses_primary_user_subject(predicate: str) -> bool:
    return predicate in {
        "bought_item",
        "attended_event",
        "had_issue",
        "owns_device",
        "prefers",
        "recommended_item",
        "recommended_item_at_position",
        "scheduled_for_date",
        "works_as",
    }


def _default_claim_text(subject: str, predicate: str, object_value: str) -> str:
    subject_name = subject.split(":", 1)[-1].replace("_", " ") if subject else "Unknown"
    if predicate == "bought_item":
        return f"{subject_name} bought {object_value}."
    if predicate == "recommended_item_at_position":
        return f"{subject_name} was recommended {object_value} at a ranked position."
    if predicate == "prefers":
        return f"{subject_name} prefers {object_value}."
    if predicate == "scheduled_for_date":
        return f"{subject_name} is scheduled for {object_value}."
    if predicate == "has_phone_number":
        return f"{subject_name} has phone number {object_value}."
    return f"{subject_name} {predicate.replace('_', ' ')} {object_value}."


def _infer_default_subject(payload: dict) -> str | None:
    entities = payload.get("entities", [])
    for entity in entities:
        entity_id = entity.get("entity_id", "")
        if entity_id.startswith("User:"):
            return entity_id
    return None


def _normalize_entities(payload: dict) -> tuple[dict, dict[str, str]]:
    name_to_entity_id: dict[str, str] = {}
    normalized_entities: list[dict] = []
    for entity in payload.get("entities", []):
        if "entity_id" in entity:
            normalized = dict(entity)
            canonical_name = normalized.get("canonical_name") or normalized["entity_id"].split(":", 1)[-1].replace("_", " ")
            normalized.setdefault("canonical_name", canonical_name)
            normalized.setdefault("entity_type", normalized["entity_id"].split(":", 1)[0].lower())
            normalized.setdefault("namespace", "company")
        else:
            typed_identifier = entity.get("type")
            if isinstance(typed_identifier, str) and ":" in typed_identifier and not any(
                entity.get(field) for field in ("name", "id", "canonical_name")
            ):
                entity_type, canonical_name = typed_identifier.split(":", 1)
                normalized = {
                    "entity_id": typed_identifier,
                    "entity_type": entity_type.lower(),
                    "canonical_name": canonical_name.replace("_", " "),
                    "namespace": entity.get("namespace", entity_type.lower()),
                }
                name_to_entity_id[normalized["canonical_name"]] = normalized["entity_id"]
                name_to_entity_id[normalized["canonical_name"].replace("_", " ")] = normalized["entity_id"]
                name_to_entity_id[normalized["entity_id"]] = normalized["entity_id"]
                normalized_entities.append(normalized)
                continue
            name = entity.get("canonical_name") or entity.get("name") or entity.get("id") or entity.get("value")
            entity_type = entity.get("entity_type") or entity.get("type")
            if not name or not entity_type:
                normalized_entities.append(dict(entity))
                continue
            entity_id = entity.get("canonical") or entity.get("entity_id") or _canonical_entity_id(entity_type, name)
            normalized = {
                "entity_id": entity_id,
                "entity_type": str(entity_type).lower(),
                "canonical_name": entity.get("canonical_name") or str(entity_id).split(":", 1)[-1].replace("_", " "),
                "namespace": entity.get("namespace", "company"),
            }
        name_to_entity_id[normalized["canonical_name"]] = normalized["entity_id"]
        name_to_entity_id[normalized["canonical_name"].replace("_", " ")] = normalized["entity_id"]
        name_to_entity_id[normalized["entity_id"]] = normalized["entity_id"]
        normalized_entities.append(normalized)
    payload["entities"] = normalized_entities
    return payload, name_to_entity_id


def _normalize_claims(payload: dict, name_to_entity_id: dict[str, str]) -> dict:
    source_claims = list(payload.get("claims", []))
    if not source_claims:
        for entity in payload.get("entities", []):
            entity_claims = entity.get("claims")
            if not isinstance(entity_claims, list):
                continue
            for claim in entity_claims:
                if not isinstance(claim, dict):
                    continue
                source_claims.append(
                    {
                        **claim,
                        "subject": entity.get("entity_id") or entity.get("canonical_name") or entity.get("type"),
                    }
                )

    default_subject = _infer_default_subject(payload)
    normalized_claims: list[dict] = []
    for index, claim in enumerate(source_claims, start=1):
        normalized = dict(claim)
        infer_run_id = "value" in normalized or any(
            field not in normalized
            for field in ("subject", "object", "object_type", "claim_text", "domain")
        )
        normalized.setdefault("claim_id", f"claim-{index}")
        if "subject" not in normalized:
            predicate = str(normalized.get("predicate", ""))
            if default_subject:
                normalized["subject"] = default_subject
            elif _uses_primary_user_subject(predicate):
                normalized["subject"] = "User:Primary"
        subject = normalized.get("subject")
        if subject in name_to_entity_id:
            normalized["subject"] = name_to_entity_id[subject]
        if "object" not in normalized and "value" in normalized:
            normalized["object"] = normalized["value"]
        if "object" not in normalized and isinstance(normalized.get("arguments"), list) and normalized["arguments"]:
            normalized["object"] = normalized["arguments"][0]
        if "object_type" not in normalized:
            object_value = normalized.get("object")
            if isinstance(object_value, str) and object_value in name_to_entity_id:
                normalized["object_type"] = "entity"
            else:
                normalized["object_type"] = "literal"
        if normalized.get("object_type") == "entity" and normalized.get("object") in name_to_entity_id:
            normalized["object"] = name_to_entity_id[normalized["object"]]
        normalized.setdefault("domain", _default_claim_domain(str(normalized.get("predicate", ""))))
        if infer_run_id:
            normalized.setdefault("extraction_run_id", "chunk-local")
        if "claim_text" not in normalized and normalized.get("subject") and normalized.get("predicate") and normalized.get("object"):
            normalized["claim_text"] = _default_claim_text(
                str(normalized["subject"]),
                str(normalized["predicate"]),
                str(normalized["object"]),
            )
        normalized.setdefault("provisional_predicate", False)
        normalized_claims.append(normalized)
    payload["claims"] = normalized_claims
    return payload


def _normalize_evidence(payload: dict) -> dict:
    normalized_evidence: list[dict] = []
    claim_run_lookup = {
        claim.get("claim_id"): claim.get("extraction_run_id", "chunk-local")
        for claim in payload.get("claims", [])
    }
    claim_ids = [claim.get("claim_id") for claim in payload.get("claims", []) if claim.get("claim_id")]
    for index, evidence in enumerate(payload.get("evidence_spans", [])):
        if isinstance(evidence, dict):
            normalized = dict(evidence)
        else:
            normalized = {
                "claim_id": claim_ids[min(index, len(claim_ids) - 1)] if claim_ids else "claim-local",
                "quote_text": str(evidence),
            }
        if "quote_text" not in normalized and "evidence" in normalized:
            normalized["quote_text"] = normalized.pop("evidence")
        if "quote_text" not in normalized and "text" in normalized:
            normalized["quote_text"] = normalized.pop("text")
        if "quote_text" not in normalized and "span" in normalized:
            normalized["quote_text"] = normalized.pop("span")
        normalized.setdefault("source_id", "chunk-local-source")
        normalized.setdefault("chunk_id", "chunk-local-id")
        normalized.setdefault(
            "extraction_run_id",
            claim_run_lookup.get(normalized.get("claim_id"), "chunk-local"),
        )
        normalized_evidence.append(normalized)
    payload["evidence_spans"] = normalized_evidence
    return payload


def _normalize_open_questions(payload: dict) -> dict:
    normalized_questions: list[dict] = []
    for question in payload.get("open_questions", []):
        if isinstance(question, dict):
            normalized = dict(question)
        else:
            normalized = {"question": str(question)}
        if "question" not in normalized and "text" in normalized:
            normalized["question"] = normalized.pop("text")
        normalized.setdefault("domain", "unknown")
        normalized.setdefault("reason", "not specified")
        normalized_questions.append(normalized)
    payload["open_questions"] = normalized_questions
    return payload


def _require_fields(payload: dict, required_fields: tuple[str, ...]) -> None:
    for field in required_fields:
        if field not in payload:
            raise ValueError(f"missing required field: {field}")


def validate_extraction_payload(payload: dict) -> dict:
    """Validate the minimal structured extraction payload contract."""
    for top_level in ("entities", "claims", "evidence_spans"):
        if top_level not in payload:
            raise ValueError(f"missing required field: {top_level}")

    payload = dict(payload)
    payload, name_to_entity_id = _normalize_entities(payload)
    payload = _normalize_claims(payload, name_to_entity_id)
    payload = _normalize_evidence(payload)
    payload = _normalize_open_questions(payload)

    for claim in payload["claims"]:
        _require_fields(claim, CLAIM_REQUIRED_FIELDS)

    for evidence_span in payload["evidence_spans"]:
        _require_fields(evidence_span, EVIDENCE_REQUIRED_FIELDS)

    return payload
