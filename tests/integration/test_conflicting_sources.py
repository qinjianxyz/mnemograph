import sqlite3

from mnemograph.ingest.pipeline import ingest_text_source
from mnemograph.llm.mock import MockLLMClient


def test_conflicting_sources_preserve_history_and_record_conflict(tmp_path):
    db_path = tmp_path / "memory.db"

    first_client = MockLLMClient(
        responses={
            "extract": {
                "entities": [
                    {
                        "entity_id": "Plan:Pro",
                        "entity_type": "plan",
                        "canonical_name": "Pro",
                        "namespace": "company",
                    }
                ],
                "claims": [
                    {
                        "claim_id": "claim-1",
                        "subject": "Plan:Pro",
                        "predicate": "price_usd_monthly",
                        "object": "49",
                        "object_type": "literal",
                        "claim_text": "Pro costs $49 per month.",
                        "domain": "pricing",
                        "extraction_run_id": "run-local-1",
                    }
                ],
                "evidence_spans": [],
            }
        }
    )
    second_client = MockLLMClient(
        responses={
            "extract": {
                "entities": [
                    {
                        "entity_id": "Plan:Pro",
                        "entity_type": "plan",
                        "canonical_name": "Pro",
                        "namespace": "company",
                    }
                ],
                "claims": [
                    {
                        "claim_id": "claim-2",
                        "subject": "Plan:Pro",
                        "predicate": "price_usd_monthly",
                        "object": "99",
                        "object_type": "literal",
                        "claim_text": "Pro costs $99 per month.",
                        "domain": "pricing",
                        "extraction_run_id": "run-local-2",
                    }
                ],
                "evidence_spans": [],
            }
        }
    )

    ingest_text_source(
        db_path=db_path,
        locator="https://acme.com/pricing",
        content="Pro costs $49 per month.",
        llm_client=first_client,
        source_type="url",
        trust_tier="secondary",
    )
    ingest_text_source(
        db_path=db_path,
        locator="https://acme.com/sales-deck",
        content="Pro costs $99 per month.",
        llm_client=second_client,
        source_type="text",
        trust_tier="authoritative",
    )

    conn = sqlite3.connect(db_path)
    claim_rows = conn.execute(
        "SELECT object_value, status FROM claims ORDER BY system_time_start"
    ).fetchall()
    conflict_count = conn.execute("SELECT COUNT(*) FROM conflicts").fetchone()[0]
    active_values = conn.execute(
        "SELECT object_value FROM claims WHERE status = 'active'"
    ).fetchall()

    assert len(claim_rows) == 2
    assert conflict_count == 1
    assert active_values == [("99",)]
