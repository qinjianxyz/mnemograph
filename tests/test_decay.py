from datetime import UTC, datetime, timedelta

from mnemograph.lifecycle.decay import DecayCandidate, apply_decay


def test_low_confidence_never_retrieved_claims_decay_over_time():
    now = datetime.now(UTC)
    candidate = DecayCandidate(
        claim_id="claim-1",
        confidence=0.2,
        created_at=now - timedelta(days=14),
        last_retrieved_at=None,
        user_confirmed=False,
        support_count=1,
        status="active",
    )

    decayed = apply_decay(candidate, as_of=now)

    assert decayed.confidence < candidate.confidence
    assert decayed.status == "active"


def test_user_confirmed_and_historical_claims_do_not_decay():
    now = datetime.now(UTC)
    confirmed = DecayCandidate(
        claim_id="claim-2",
        confidence=0.2,
        created_at=now - timedelta(days=14),
        last_retrieved_at=None,
        user_confirmed=True,
        support_count=1,
        status="active",
    )
    historical = DecayCandidate(
        claim_id="claim-3",
        confidence=0.2,
        created_at=now - timedelta(days=14),
        last_retrieved_at=None,
        user_confirmed=False,
        support_count=1,
        status="active",
        valid_time_end=now - timedelta(days=1),
        historical_temporal=True,
    )

    assert apply_decay(confirmed, as_of=now) == confirmed
    assert apply_decay(historical, as_of=now) == historical


def test_archival_threshold_triggers_below_point_one_confidence():
    now = datetime.now(UTC)
    candidate = DecayCandidate(
        claim_id="claim-4",
        confidence=0.09,
        created_at=now - timedelta(days=8),
        last_retrieved_at=None,
        user_confirmed=False,
        support_count=1,
        status="active",
    )

    decayed = apply_decay(candidate, as_of=now)

    assert decayed.status == "archived"
    assert decayed.confidence < 0.10
