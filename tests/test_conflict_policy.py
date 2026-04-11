from mnemograph.reconcile.conflicts import build_conflict_record
from mnemograph.reconcile.engine import ClaimInput, decide_merge


def test_entity_resolution_conflict_queues_review():
    existing = ClaimInput(
        claim_id="claim-old",
        subject="Company:Acme",
        predicate="headquartered_in",
        object_value="San Francisco",
        source_trust=0.8,
        source_timestamp="2026-01-01T00:00:00+00:00",
        entity_resolution_score=1.0,
    )
    candidate = ClaimInput(
        claim_id="claim-new",
        subject="Company:Acme Corporation",
        predicate="headquartered_in",
        object_value="San Francisco",
        source_trust=0.8,
        source_timestamp="2026-01-02T00:00:00+00:00",
        entity_resolution_score=0.5,
    )

    decision = decide_merge(existing, candidate)

    assert decision.action == "NONE"
    assert decision.conflict_type == "entity_resolution_conflict"
    assert decision.requires_review is True


def test_source_quality_conflict_surfaces_both_versions():
    existing = ClaimInput(
        claim_id="claim-old",
        subject="Plan:Pro",
        predicate="price_usd_monthly",
        object_value="49",
        source_trust=0.8,
        source_timestamp="2026-01-01T00:00:00+00:00",
    )
    candidate = ClaimInput(
        claim_id="claim-new",
        subject="Plan:Pro",
        predicate="price_usd_monthly",
        object_value="99",
        source_trust=0.78,
        source_timestamp="2026-02-01T00:00:00+00:00",
    )

    decision = decide_merge(existing, candidate)
    conflict = build_conflict_record(existing.claim_id, candidate.claim_id, decision)

    assert decision.action == "CONTRADICT"
    assert decision.conflict_type == "source_quality_conflict"
    assert decision.supersede_existing is False
    assert conflict["status"] == "pending"
