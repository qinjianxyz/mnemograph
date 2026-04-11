"""Context assembly for active working memory."""


def assemble_context(
    question: str,
    claims: list[dict],
    evidence_spans: list[dict],
    conflicts: list[dict],
    open_questions: list[dict],
    token_budget: int = 2000,
) -> dict:
    """Assemble a context snapshot with summary-first ordering."""
    sorted_claims = sorted(
        claims,
        key=lambda claim: (
            0 if claim.get("record_type") == "summary" else 1,
            claim.get("claim_id", ""),
        ),
    )
    assembled_claims: list[dict] = []
    running_token_estimate = 0
    for claim in sorted_claims:
        claim_token_estimate = max(1, len(claim.get("claim_text", "")) // 4)
        if running_token_estimate + claim_token_estimate > token_budget:
            break
        assembled_claims.append(claim)
        running_token_estimate += claim_token_estimate

    return {
        "question": question,
        "claims": assembled_claims,
        "evidence_spans": evidence_spans,
        "conflicts": conflicts,
        "open_questions": open_questions,
        "assembled_claim_ids": [claim.get("claim_id") for claim in assembled_claims],
        "assembled_evidence_ids": [span.get("evidence_id") for span in evidence_spans],
        "token_estimate": running_token_estimate,
    }
