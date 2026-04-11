from mnemograph.context.assemble import assemble_context
from mnemograph.context.render import render_provenance_chain


def test_summary_first_assembly():
    snapshot = assemble_context(
        question="What does Acme sell?",
        claims=[
            {"claim_id": "summary-1", "record_type": "summary", "status": "active", "claim_text": "Acme sells Pro and Team."},
            {"claim_id": "atomic-1", "record_type": "atomic", "status": "active", "claim_text": "Acme sells Pro."},
        ],
        evidence_spans=[],
        conflicts=[],
        open_questions=[],
    )

    assert [claim["claim_id"] for claim in snapshot["claims"]] == ["summary-1", "atomic-1"]


def test_conflict_visibility_is_preserved_in_context():
    snapshot = assemble_context(
        question="What does Pro cost?",
        claims=[],
        evidence_spans=[],
        conflicts=[{"conflict_id": "conflict-1", "conflict_type": "value_conflict"}],
        open_questions=[],
    )

    assert snapshot["conflicts"][0]["conflict_id"] == "conflict-1"


def test_token_budget_limits_claims_by_estimated_tokens():
    snapshot = assemble_context(
        question="What does Acme sell?",
        claims=[
            {"claim_id": "claim-1", "record_type": "summary", "claim_text": "Alpha " * 30},
            {"claim_id": "claim-2", "record_type": "atomic", "claim_text": "Beta " * 30},
        ],
        evidence_spans=[],
        conflicts=[],
        open_questions=[],
        token_budget=50,
    )

    assert [claim["claim_id"] for claim in snapshot["claims"]] == ["claim-1"]
    assert snapshot["assembled_claim_ids"] == ["claim-1"]
    assert snapshot["token_estimate"] <= 50


def test_token_budget_excludes_first_claim_if_it_does_not_fit():
    snapshot = assemble_context(
        question="What does Acme sell?",
        claims=[
            {"claim_id": "claim-1", "record_type": "summary", "claim_text": "Alpha " * 60},
        ],
        evidence_spans=[],
        conflicts=[],
        open_questions=[],
        token_budget=10,
    )

    assert snapshot["claims"] == []
    assert snapshot["assembled_claim_ids"] == []
    assert snapshot["token_estimate"] == 0


def test_provenance_chain_renders_on_demand():
    text = render_provenance_chain(
        claim={"claim_id": "claim-1", "claim_text": "Pro costs $49/month.", "confidence": 0.87, "domain": "pricing"},
        evidence_span={"evidence_id": "evidence-1", "quote_text": "Pro costs $49/month."},
        source={"source_id": "source-1", "locator": "https://acme.com/pricing", "ingested_at": "2026-04-10T00:00:00+00:00"},
    )

    assert "Claim: Pro costs $49/month." in text
    assert "Source: https://acme.com/pricing (ingested 2026-04-10)" in text
    assert "Evidence: \"Pro costs $49/month.\"" in text
    assert "[confidence: 0.87, domain: pricing]" in text
