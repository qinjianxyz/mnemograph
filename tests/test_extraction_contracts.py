import pytest

from mnemograph.prompts.contracts import validate_extraction_payload


def test_validate_extraction_payload_requires_mandatory_spo_fields():
    with pytest.raises(ValueError, match="subject"):
        validate_extraction_payload(
            {
                "entities": [],
                "claims": [
                    {
                        "predicate": "has_pricing_plan",
                        "object": "Plan:Pro",
                        "object_type": "entity",
                        "claim_text": "Acme offers Pro.",
                        "domain": "pricing",
                        "extraction_run_id": "run-1",
                    }
                ],
                "evidence_spans": [],
            }
        )


def test_validate_extraction_payload_supports_provisional_predicates():
    payload = validate_extraction_payload(
        {
            "entities": [],
            "claims": [
                {
                    "subject": "Company:Acme",
                    "predicate": "has_pricing_plan",
                    "object": "Plan:Pro",
                    "object_type": "entity",
                    "claim_text": "Acme offers Pro.",
                    "domain": "pricing",
                    "provisional_predicate": True,
                    "extraction_run_id": "run-1",
                }
            ],
            "evidence_spans": [],
        }
    )

    assert payload["claims"][0]["provisional_predicate"] is True


def test_validate_extraction_payload_requires_evidence_span_schema():
    with pytest.raises(ValueError, match="quote_text"):
        validate_extraction_payload(
            {
                "entities": [],
                "claims": [
                    {
                        "subject": "Company:Acme",
                        "predicate": "has_pricing_plan",
                        "object": "Plan:Pro",
                        "object_type": "entity",
                        "claim_text": "Acme offers Pro.",
                        "domain": "pricing",
                        "extraction_run_id": "run-1",
                    }
                ],
                "evidence_spans": [
                    {
                        "claim_id": "claim-1",
                        "claim_text": "bad evidence",
                        "source_id": "source-1",
                        "chunk_id": "chunk-1",
                        "extraction_run_id": "run-1",
                    }
                ],
            }
        )


def test_validate_extraction_payload_requires_extraction_run_reference_fields():
    with pytest.raises(ValueError, match="extraction_run_id"):
        validate_extraction_payload(
            {
                "entities": [],
                "claims": [
                    {
                        "subject": "Company:Acme",
                        "predicate": "has_pricing_plan",
                        "object": "Plan:Pro",
                        "object_type": "entity",
                        "claim_text": "Acme offers Pro.",
                        "domain": "pricing",
                    }
                ],
                "evidence_spans": [],
            }
        )


def test_validate_extraction_payload_normalizes_common_local_model_variants():
    payload = validate_extraction_payload(
        {
            "entities": [
                {"name": "Pro", "type": "Plan"},
                {"name": "Stripe", "type": "Company"},
                {"name": "Billing", "type": "Product"},
            ],
            "claims": [
                {
                    "claim_id": "claim_001",
                    "subject": "Pro",
                    "predicate": "price_usd_monthly",
                    "object": "49",
                    "object_type": "literal",
                    "claim_text": "Pro costs $49/month.",
                    "domain": "pricing",
                    "extraction_run_id": "run_001",
                },
                {
                    "claim_id": "claim_002",
                    "subject": "Stripe",
                    "predicate": "has_product",
                    "object": "Billing",
                    "object_type": "entity",
                    "claim_text": "Stripe offers Billing.",
                    "domain": "product",
                    "extraction_run_id": "run_001",
                },
            ],
            "evidence_spans": [
                {"claim_id": "claim_001", "text": "Pro costs $49/month."},
                {"claim_id": "claim_002", "text": "Stripe offers Billing."},
            ],
            "open_questions": [{"text": "What else does Stripe offer?"}],
        }
    )

    assert payload["entities"][0]["entity_id"] == "Plan:Pro"
    assert payload["entities"][1]["entity_id"] == "Company:Stripe"
    assert payload["claims"][0]["subject"] == "Plan:Pro"
    assert payload["claims"][1]["subject"] == "Company:Stripe"
    assert payload["claims"][1]["object"] == "Product:Billing"
    assert payload["evidence_spans"][0]["quote_text"] == "Pro costs $49/month."
    assert payload["evidence_spans"][0]["source_id"] == "chunk-local-source"
    assert payload["open_questions"][0]["question"] == "What else does Stripe offer?"


def test_validate_extraction_payload_normalizes_string_evidence_entries():
    payload = validate_extraction_payload(
        {
            "entities": [{"entity_id": "Company:Stripe", "entity_type": "company", "canonical_name": "Stripe", "namespace": "company"}],
            "claims": [
                {
                    "claim_id": "claim-1",
                    "subject": "Company:Stripe",
                    "predicate": "company_summary",
                    "object": "payments company",
                    "object_type": "literal",
                    "claim_text": "Stripe is a payments company.",
                    "domain": "company",
                    "extraction_run_id": "run-1",
                }
            ],
            "evidence_spans": ["Stripe is a payments company."],
        }
    )

    assert payload["evidence_spans"][0]["claim_id"] == "claim-1"
    assert payload["evidence_spans"][0]["quote_text"] == "Stripe is a payments company."


def test_validate_extraction_payload_normalizes_id_type_canonical_entity_shape():
    payload = validate_extraction_payload(
        {
            "entities": [
                {"id": "Railway", "type": "Company", "canonical": "Company:Railway"},
                {"id": "Pro", "type": "Plan", "canonical": "Plan:Pro"},
            ],
            "claims": [
                {
                    "claim_id": "claim-1",
                    "subject": "Railway",
                    "predicate": "has_pricing_tier",
                    "object": "Pro",
                    "object_type": "entity",
                    "claim_text": "Railway offers Pro.",
                    "domain": "pricing",
                    "extraction_run_id": "run-1",
                }
            ],
            "evidence_spans": [{"claim_id": "claim-1", "text": "Railway offers Pro."}],
        }
    )

    assert payload["entities"][0]["entity_id"] == "Company:Railway"
    assert payload["entities"][1]["entity_id"] == "Plan:Pro"
    assert payload["claims"][0]["subject"] == "Company:Railway"
    assert payload["claims"][0]["object"] == "Plan:Pro"


def test_validate_extraction_payload_normalizes_span_evidence_key():
    payload = validate_extraction_payload(
        {
            "entities": [{"name": "Vercel", "type": "Company"}],
            "claims": [
                {
                    "claim_id": "claim-1",
                    "subject": "Vercel",
                    "predicate": "company_summary",
                    "object": "ai cloud platform",
                    "object_type": "literal",
                    "claim_text": "Vercel provides developer tools.",
                    "domain": "company",
                    "extraction_run_id": "run-1",
                }
            ],
            "evidence_spans": [{"claim_id": "claim-1", "span": "Vercel provides developer tools."}],
        }
    )

    assert payload["evidence_spans"][0]["quote_text"] == "Vercel provides developer tools."


def test_validate_extraction_payload_normalizes_string_open_questions():
    payload = validate_extraction_payload(
        {
            "entities": [],
            "claims": [],
            "evidence_spans": [],
            "open_questions": ["What else does Stripe offer?"],
        }
    )

    assert payload["open_questions"][0]["question"] == "What else does Stripe offer?"
    assert payload["open_questions"][0]["domain"] == "unknown"


def test_validate_extraction_payload_normalizes_compact_conversation_claim_shape():
    payload = validate_extraction_payload(
        {
            "entities": [
                {
                    "type": "User:Primary",
                    "claims": [
                        {
                            "predicate": "bought_item",
                            "value": "gift for sister's birthday",
                        }
                    ],
                }
            ],
            "claims": [
                {
                    "predicate": "bought_item",
                    "value": "gift for sister's birthday",
                },
                {
                    "predicate": "bought_item",
                    "value": "gift for mom",
                },
            ],
            "evidence_spans": [
                "gifts for my sister's birthday",
                "my mom",
            ],
            "open_questions": [],
        }
    )

    assert payload["entities"][0]["entity_id"] == "User:Primary"
    assert payload["claims"][0]["subject"] == "User:Primary"
    assert payload["claims"][0]["object"] == "gift for sister's birthday"
    assert payload["claims"][0]["object_type"] == "literal"
    assert payload["claims"][0]["domain"] == "personal"
    assert payload["claims"][0]["extraction_run_id"] == "chunk-local"
    assert payload["claims"][1]["subject"] == "User:Primary"
    assert payload["evidence_spans"][0]["claim_id"] == payload["claims"][0]["claim_id"]


def test_validate_extraction_payload_normalizes_argument_based_conversation_claim_shape():
    payload = validate_extraction_payload(
        {
            "entities": [
                {
                    "type": "Item",
                    "value": "Silver hoop earrings with a small pearl in the center",
                }
            ],
            "claims": [
                {
                    "predicate": "bought_item",
                    "arguments": [
                        "Silver hoop earrings with a small pearl in the center",
                        "her",
                    ],
                }
            ],
            "evidence_spans": [
                "I got her a pair of silver hoop earrings with a small pearl in the center",
            ],
            "open_questions": [],
        }
    )

    assert payload["entities"][0]["entity_id"] == "Item:Silver_hoop_earrings_with_a_small_pearl_in_the_center"
    assert payload["claims"][0]["subject"] == "User:Primary"
    assert payload["claims"][0]["object"] == "Item:Silver_hoop_earrings_with_a_small_pearl_in_the_center"
    assert payload["claims"][0]["object_type"] == "entity"
    assert payload["claims"][0]["domain"] == "personal"
