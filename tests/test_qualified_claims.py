import sqlite3

from mnemograph.engine import Mnemograph
from mnemograph.llm.mock import MockLLMClient


def test_comparable_sources_surface_source_quality_conflict_without_superseding(tmp_path):
    engine = Mnemograph(tmp_path, llm_client=MockLLMClient(
        responses={
            "extract": [
                {
                    "entities": [{"entity_id": "Plan:Pro", "entity_type": "plan", "canonical_name": "Pro", "namespace": "company"}],
                    "claims": [{
                        "claim_id": "claim-1",
                        "subject": "Plan:Pro",
                        "predicate": "price_usd_monthly",
                        "object": "49",
                        "object_type": "literal",
                        "claim_text": "Pro costs $49/month.",
                        "domain": "pricing",
                        "extraction_run_id": "run-1",
                    }],
                    "evidence_spans": [],
                    "open_questions": [],
                },
                {
                    "entities": [{"entity_id": "Plan:Pro", "entity_type": "plan", "canonical_name": "Pro", "namespace": "company"}],
                    "claims": [{
                        "claim_id": "claim-2",
                        "subject": "Plan:Pro",
                        "predicate": "price_usd_monthly",
                        "object": "59",
                        "object_type": "literal",
                        "claim_text": "Partner sheet says Pro costs $59/month.",
                        "domain": "pricing",
                        "extraction_run_id": "run-2",
                    }],
                    "evidence_spans": [],
                    "open_questions": [],
                },
            ]
        }
    ))

    first = engine.ingest_text("Pro costs $49/month.", source="website")
    second = engine.ingest_text("Partner sheet says Pro costs $59/month.", source="website")

    with sqlite3.connect(engine.db_path) as conn:
        conflict_types = [row[0] for row in conn.execute("SELECT conflict_type FROM conflicts").fetchall()]
        active_claims = [row[0] for row in conn.execute("SELECT claim_text FROM claims WHERE status = 'active' ORDER BY claim_text").fetchall()]

    changelog = engine.render_changelog(second.extraction_run_id)

    assert conflict_types == ["source_quality_conflict"]
    assert active_claims == [
        "Partner sheet says Pro costs $59/month.",
        "Pro costs $49/month.",
    ]
    assert "CONFLICT: source_quality_conflict" in changelog
    assert "SUPERSEDED:" not in changelog
