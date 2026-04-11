from mnemograph.prompts.extract import build_extraction_prompt


def test_extraction_prompt_declares_schema_domains_and_spo_examples():
    prompt = build_extraction_prompt("Vercel offers Functions and Edge Config.")

    assert '"entities"' in prompt
    assert '"claims"' in prompt
    assert '"evidence_spans"' in prompt
    assert '"open_questions"' in prompt
    assert '"subject"' in prompt
    assert '"predicate"' in prompt
    assert '"object"' in prompt
    assert '"object_type"' in prompt
    assert "Company:Vercel" in prompt
    assert "has_product" in prompt
    assert "price_usd_monthly" in prompt
    for domain in ("product", "pricing", "team", "technology", "company", "security"):
        assert domain in prompt
    assert "Vercel offers Functions and Edge Config." in prompt


def test_compact_extraction_prompt_keeps_schema_but_is_shorter():
    from mnemograph.prompts.extract import build_extraction_prompt

    full_prompt = build_extraction_prompt("Vercel offers Functions and Edge Config.")
    compact_prompt = build_extraction_prompt(
        "Vercel offers Functions and Edge Config.",
        compact=True,
    )

    assert len(compact_prompt) < len(full_prompt)
    for required in ('"entities"', '"claims"', '"evidence_spans"', '"subject"', '"predicate"', '"object"'):
        assert required in compact_prompt
    assert "product" in compact_prompt
    assert "pricing" in compact_prompt


def test_compact_extraction_prompt_caps_output_volume_for_local_models():
    compact_prompt = build_extraction_prompt(
        "Railway helps teams ship software.",
        compact=True,
    )

    assert "at most 6 entities" in compact_prompt
    assert "at most 8 claims" in compact_prompt
    assert "prioritize the most durable facts" in compact_prompt


def test_conversation_extraction_prompt_supports_general_personal_memory_domains():
    prompt = build_extraction_prompt(
        "user: I bought a necklace for my sister's birthday.\nassistant: Noted.",
        profile="conversation",
    )

    for domain in ("personal", "preference", "event", "contact", "task"):
        assert domain in prompt
    for predicate in ("bought_item", "attended_event", "has_phone_number", "prefers", "recommended_item"):
        assert predicate in prompt
    assert "User:Primary" in prompt
    assert "Item:Necklace" in prompt


def test_conversation_extraction_prompt_includes_ranked_recommendation_example():
    prompt = build_extraction_prompt(
        "assistant: 1. Role A 2. Role B 3. Role C",
        profile="conversation",
    )

    assert "recommended_item_at_position" in prompt
    assert "7th recommended work-from-home job" in prompt
    assert "remote travel agent" in prompt


def test_compact_conversation_extraction_prompt_keeps_ranked_recommendation_guidance():
    prompt = build_extraction_prompt(
        "assistant: 1. Role A 2. Role B 3. Role C",
        compact=True,
        profile="conversation",
    )

    assert "recommended_item_at_position" in prompt
    assert "remote travel agent" in prompt
