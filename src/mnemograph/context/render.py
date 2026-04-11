"""Human-facing provenance rendering."""


def render_provenance_chain(claim: dict, evidence_span: dict, source: dict) -> str:
    """Render the claim -> evidence -> source chain."""
    ingested_at = str(source.get("ingested_at", "")).split("T", 1)[0]
    confidence = float(claim.get("confidence", 0.0))
    domain = claim.get("domain", "unknown")
    return "\n".join(
        [
            f"Claim: {claim['claim_text']} [confidence: {confidence:.2f}, domain: {domain}]",
            f'Evidence: "{evidence_span["quote_text"]}"',
            f"Source: {source['locator']} (ingested {ingested_at})",
        ]
    )
