import json

from mnemograph.engine import Mnemograph
from mnemograph.llm.mock import MockLLMClient


def test_working_memory_mirror_outputs_are_written(tmp_path):
    engine = Mnemograph(tmp_path, llm_client=MockLLMClient(
        responses={
            "extract": {
                "entities": [{"entity_id": "Plan:Enterprise", "entity_type": "plan", "canonical_name": "Enterprise", "namespace": "company"}],
                "claims": [{
                    "claim_id": "claim-1",
                    "subject": "Plan:Enterprise",
                    "predicate": "price_usd_monthly",
                    "object": "500",
                    "object_type": "literal",
                    "claim_text": "Enterprise plan costs $500/month.",
                    "domain": "pricing",
                    "extraction_run_id": "run-1",
                }],
                "evidence_spans": [],
            }
        }
    ))

    engine.ingest_text("Enterprise plan costs $500/month.", source="user")
    engine.query("What does Enterprise cost?")

    active_context = tmp_path / "memory" / "working" / "active_context.json"
    session_history = tmp_path / "memory" / "working" / "session_history.json"

    assert active_context.exists()
    assert session_history.exists()
    assert json.loads(active_context.read_text())["claims"]


def test_knowledge_and_source_mirrors_are_written_on_ingest(tmp_path):
    engine = Mnemograph(tmp_path, llm_client=MockLLMClient(
        responses={
            "extract": {
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
            }
        }
    ))

    ingest_result = engine.ingest("https://acme.com/pricing", "Pro costs $49/month.", source_type="url")

    pricing_file = tmp_path / "memory" / "knowledge" / "pricing.json"
    source_file = tmp_path / "memory" / "sources" / f"{ingest_result.source_id}.json"

    assert pricing_file.exists()
    assert source_file.exists()
    assert json.loads(pricing_file.read_text())["claims"][0]["claim_text"] == "Pro costs $49/month."
    source_payload = json.loads(source_file.read_text())
    assert source_payload["locator"] == "https://acme.com/pricing"
    assert source_payload["derived_claim_ids"] == ingest_result.claim_ids
