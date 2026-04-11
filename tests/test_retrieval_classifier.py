from mnemograph.retrieval.classify import classify_query
from mnemograph.retrieval.plan import apply_fallback


def test_direct_meta_turn_maps_to_no_retrieval():
    decision = classify_query("Answer in two bullet points.")
    assert decision.mode == "NO_RETRIEVAL"


def test_recent_recall_maps_to_working_memory_only():
    decision = classify_query(
        "What was the pricing again?",
        recent_turns=["Their Pro plan costs $49/month."],
    )
    assert decision.mode == "WORKING_MEMORY_ONLY"


def test_entity_targeted_pricing_query_prefers_structured_lookup():
    decision = classify_query("What does Acme charge for Pro?")
    assert decision.mode == "STRUCTURED_LOOKUP"
    assert "Acme" in decision.target_entities


def test_classify_pricing_query_returns_structured_lookup():
    decision = classify_query("What does Pro cost?")
    assert decision.mode == "STRUCTURED_LOOKUP"
    assert "pricing" in decision.target_domains
    assert "Pro" in decision.target_entities


def test_product_query_prefers_structured_lookup():
    decision = classify_query("What products does stripe offer?")
    assert decision.mode == "STRUCTURED_LOOKUP"
    assert "product" in decision.target_domains


def test_team_query_prefers_structured_lookup():
    decision = classify_query("Who leads Stripe?")
    assert decision.mode == "STRUCTURED_LOOKUP"
    assert "team" in decision.target_domains


def test_provenance_query_prefers_graph_traversal():
    decision = classify_query("Where did you learn this?")
    assert decision.mode == "GRAPH_TRAVERSAL"


def test_zero_hit_structured_lookup_falls_back_to_semantic_search():
    decision = classify_query("What does Acme charge for Pro?")
    fallback = apply_fallback(decision, structured_hits=0, semantic_hits=1)
    assert fallback.mode == "SEMANTIC_SEARCH"
    assert fallback.fallback_reason == "structured_lookup_empty"
