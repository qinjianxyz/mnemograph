from mnemograph.lifecycle.consolidate import (
    build_summary_claim,
    preferred_retrieval_claims,
    should_consolidate,
)


def _atomic_claim(claim_id: str, predicate_id: str = "has_feature") -> dict:
    return {
        "claim_id": claim_id,
        "subject_entity_id": "Company:Acme",
        "domain": "product",
        "predicate_id": predicate_id,
        "status": "active",
        "record_type": "atomic",
        "claim_text": f"Claim {claim_id}",
    }


def test_consolidation_trigger_after_more_than_ten_domain_aligned_claims():
    claims = [_atomic_claim(f"claim-{index}") for index in range(11)]
    assert should_consolidate(claims) is True
    assert should_consolidate(claims[:10]) is False


def test_summary_claim_creation_preserves_provenance_links():
    claims = [_atomic_claim(f"claim-{index}") for index in range(11)]
    summary = build_summary_claim("Company:Acme", "product", claims)

    assert summary["record_type"] == "summary"
    assert summary["subject_entity_id"] == "Company:Acme"
    assert summary["domain"] == "product"
    assert len(summary["contributing_claim_ids"]) == 11
    assert summary["preferred_for_retrieval"] is True


def test_atomic_claims_are_excluded_from_default_retrieval_once_summarized():
    claims = [_atomic_claim(f"claim-{index}") for index in range(11)]
    summary = build_summary_claim("Company:Acme", "product", claims)

    preferred = preferred_retrieval_claims(claims + [summary])

    assert [record["record_type"] for record in preferred] == ["summary"]
