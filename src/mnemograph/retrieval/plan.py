"""Fallback logic for retrieval decisions."""

from mnemograph.retrieval.classify import RetrievalDecision, with_fallback


def apply_fallback(
    decision: RetrievalDecision,
    structured_hits: int = 0,
    semantic_hits: int = 0,
    graph_resolved: bool = True,
) -> RetrievalDecision:
    """Apply retrieval fallback policy to a decision."""
    if decision.mode == "STRUCTURED_LOOKUP" and structured_hits == 0:
        return with_fallback(decision, "SEMANTIC_SEARCH", "structured_lookup_empty")
    if decision.mode == "GRAPH_TRAVERSAL" and not graph_resolved:
        return with_fallback(decision, "SEMANTIC_SEARCH", "graph_unresolved")
    if decision.mode == "SEMANTIC_SEARCH" and semantic_hits == 0:
        return with_fallback(decision, "NO_RETRIEVAL", "semantic_search_empty")
    return decision
