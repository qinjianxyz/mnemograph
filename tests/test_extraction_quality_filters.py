import sqlite3

from mnemograph.ingest.pipeline import ingest_text_source
from mnemograph.llm.mock import MockLLMClient


def test_contact_sales_pricing_copy_becomes_open_question_not_claim(tmp_path):
    db_path = tmp_path / "memory.db"
    client = MockLLMClient(
        responses={
            "extract": {
                "entities": [
                    {
                        "entity_id": "Plan:Enterprise",
                        "entity_type": "plan",
                        "canonical_name": "Enterprise",
                        "namespace": "company",
                    }
                ],
                "claims": [
                    {
                        "claim_id": "claim-1",
                        "subject": "Plan:Enterprise",
                        "predicate": "price_usd_monthly",
                        "object": "contact_sales",
                        "object_type": "literal",
                        "claim_text": "Contact sales for enterprise pricing.",
                        "domain": "pricing",
                        "extraction_run_id": "run-1",
                    }
                ],
                "evidence_spans": [],
                "open_questions": [],
            }
        }
    )

    result = ingest_text_source(
        db_path=db_path,
        locator="https://acme.com/pricing",
        content="Contact sales for enterprise pricing.",
        llm_client=client,
        source_type="url",
        trust_tier="primary",
    )

    conn = sqlite3.connect(db_path)
    active_claim_count = conn.execute("SELECT COUNT(*) FROM claims WHERE status = 'active'").fetchone()[0]

    assert result.claim_ids == []
    assert active_claim_count == 0
    assert any("enterprise pricing" in question["question"].lower() for question in result.open_questions)


def test_talk_to_sales_pricing_copy_is_also_filtered(tmp_path):
    db_path = tmp_path / "memory.db"
    client = MockLLMClient(
        responses={
            "extract": {
                "entities": [
                    {
                        "entity_id": "Plan:Enterprise",
                        "entity_type": "plan",
                        "canonical_name": "Enterprise",
                        "namespace": "company",
                    }
                ],
                "claims": [
                    {
                        "claim_id": "claim-1",
                        "subject": "Plan:Enterprise",
                        "predicate": "price_usd_monthly",
                        "object": "talk_to_sales",
                        "object_type": "literal",
                        "claim_text": "Talk to sales for enterprise pricing.",
                        "domain": "pricing",
                        "extraction_run_id": "run-1",
                    }
                ],
                "evidence_spans": [],
                "open_questions": [],
            }
        }
    )

    result = ingest_text_source(
        db_path=db_path,
        locator="https://acme.com/pricing",
        content="Talk to sales for enterprise pricing.",
        llm_client=client,
        source_type="url",
        trust_tier="primary",
    )

    conn = sqlite3.connect(db_path)
    active_claim_count = conn.execute("SELECT COUNT(*) FROM claims WHERE status = 'active'").fetchone()[0]

    assert result.claim_ids == []
    assert active_claim_count == 0
    assert any("enterprise pricing" in question["question"].lower() for question in result.open_questions)
