from mnemograph.reconcile.engine import ClaimInput, decide_merge


def test_temporal_conflict_auto_supersedes_later_claim():
    existing = ClaimInput(
        claim_id="claim-old",
        subject="Company:Acme",
        predicate="has_ceo",
        object_value="Person:Jane",
        object_type="entity",
        valid_time_start="2024-01-01T00:00:00+00:00",
        source_trust=0.9,
        source_timestamp="2024-01-01T00:00:00+00:00",
    )
    candidate = ClaimInput(
        claim_id="claim-new",
        subject="Company:Acme",
        predicate="has_ceo",
        object_value="Person:John",
        object_type="entity",
        valid_time_start="2025-01-01T00:00:00+00:00",
        source_trust=0.9,
        source_timestamp="2025-01-01T00:00:00+00:00",
    )

    decision = decide_merge(existing, candidate)

    assert decision.action == "SUPERSEDE"
    assert decision.conflict_type == "temporal_conflict"
    assert decision.supersede_existing is True
    assert decision.insert_candidate is True


def test_strictly_higher_trust_value_conflict_supersedes():
    existing = ClaimInput(
        claim_id="claim-old",
        subject="Plan:Pro",
        predicate="price_usd_monthly",
        object_value="49",
        source_trust=0.6,
        source_timestamp="2026-01-01T00:00:00+00:00",
    )
    candidate = ClaimInput(
        claim_id="claim-new",
        subject="Plan:Pro",
        predicate="price_usd_monthly",
        object_value="99",
        source_trust=0.95,
        source_timestamp="2026-02-01T00:00:00+00:00",
    )

    decision = decide_merge(existing, candidate)

    assert decision.action == "SUPERSEDE"
    assert decision.conflict_type == "value_conflict"
    assert decision.supersede_existing is True
