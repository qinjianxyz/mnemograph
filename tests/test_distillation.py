from mnemograph.lifecycle.distill import ConversationTurn, distill_conversation, should_distill


def test_distill_conversation_extracts_durable_fact_candidates():
    turns = [
        ConversationTurn(speaker="user", content="Actually their enterprise plan is $500/mo."),
        ConversationTurn(speaker="assistant", content="Understood."),
    ]

    candidates = distill_conversation(turns)

    assert len(candidates) == 1
    assert candidates[0]["subject"] == "Plan:Enterprise"
    assert candidates[0]["predicate"] == "price_usd_monthly"
    assert candidates[0]["object"] == "500"
    assert candidates[0]["domain"] == "pricing"


def test_distill_conversation_handles_costs_variants():
    turns = [ConversationTurn(speaker="user", content="Enterprise costs $500/month.")]

    candidates = distill_conversation(turns)

    assert len(candidates) == 1
    assert candidates[0]["subject"] == "Plan:Enterprise"
    assert candidates[0]["object"] == "500"


def test_distill_conversation_handles_leadership_patterns():
    turns = [ConversationTurn(speaker="user", content="Patrick leads Stripe.")]

    candidates = distill_conversation(turns)

    assert len(candidates) == 1
    assert candidates[0]["predicate"] == "has_ceo"
    assert candidates[0]["subject"] == "Company:Stripe"
    assert candidates[0]["object"] == "Person:Patrick"
    assert candidates[0]["domain"] == "team"


def test_distill_conversation_flags_corrections_for_llm_fallback():
    turns = [ConversationTurn(speaker="user", content="Actually enterprise pricing starts at $500/month for annual contracts.")]

    candidates = distill_conversation(turns)

    assert len(candidates) == 1
    assert candidates[0]["needs_llm_extraction"] is True
    assert candidates[0]["raw_text"] == turns[0].content


def test_distill_conversation_ignores_non_durable_chatter():
    turns = [
        ConversationTurn(speaker="user", content="Thanks, that was helpful."),
        ConversationTurn(speaker="assistant", content="Happy to help."),
    ]

    assert distill_conversation(turns) == []


def test_distillation_trigger_defaults_to_fifteen_turns():
    assert should_distill(turn_count=14) is False
    assert should_distill(turn_count=15) is True
