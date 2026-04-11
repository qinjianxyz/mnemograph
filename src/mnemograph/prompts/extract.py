"""Prompt builders for extraction tasks."""


def build_extraction_prompt(
    chunk_text: str,
    compact: bool = False,
    profile: str = "document",
) -> str:
    """Return the structured extraction prompt for one chunk."""
    if profile == "conversation":
        if compact:
            return f"""
Extract durable conversational memory from the text and return valid JSON.

Required top-level keys:
- "entities"
- "claims"
- "evidence_spans"
- "open_questions"

Primary conversational domains:
- personal
- preference
- event
- contact
- task

Useful predicates:
- bought_item
- attended_event
- has_phone_number
- prefers
- recommended_item
- recommended_item_at_position
- scheduled_for_date
- had_issue
- owns_device

Canonical entity examples:
- User:Primary
- Item:Necklace
- Event:Networking_Event
- Contact:Speyer_Tourism_Board

Ranked recommendation example:
- The 7th recommended work-from-home job for seniors was remote travel agent.
- predicate: recommended_item_at_position

Rules:
- Focus on durable user-specific or assistant-provided facts worth recalling later.
- Ignore filler, politeness, and generic advice that is not specific to the user.
- If a detail is too vague to store as a fact, add an open question instead.
- Return at most 6 entities and at most 8 claims.
- Return only valid JSON.

Text:
{chunk_text}
""".strip()

        return f"""
You are extracting durable conversational memory records from a chat turn.

Return valid JSON with exactly these top-level keys:
- "entities": array of entity objects
- "claims": array of claim objects
- "evidence_spans": array of evidence objects
- "open_questions": array of unanswered questions

Each claim must be an atomic SPO memory worth recalling later.

Conversational memory domains:
- personal
- preference
- event
- contact
- task
- item

Conversational predicate examples:
- bought_item
- attended_event
- had_issue
- has_phone_number
- prefers
- recommended_item
- scheduled_for_date
- owns_device
- works_as

Canonical entity examples:
- User:Primary
- Item:Necklace
- Event:Networking_Event
- Contact:Speyer_Tourism_Board
- Device:Dell_XPS_13

Rules:
- Prefer user-specific facts, preferences, plans, contacts, purchases, events, and concrete assistant recommendations.
- Ignore generic advice, chit-chat, filler acknowledgements, and content that would not matter in a later recall query.
- If the text references a list or ranked recommendation, preserve the memorable item and list position when directly stated.
- If a detail is implied but not explicit, emit an open question instead of guessing.
- Return only valid JSON.

Example:
Input:
assistant: 1. Virtual customer service representative 2. Telehealth professional 3. Remote bookkeeper 4. Virtual tutor or teacher 5. Freelance writer or editor 6. Online survey taker 7. Remote travel agent

Output claim idea:
- subject: User:Primary
- predicate: recommended_item_at_position
- object: Item:Remote_Travel_Agent
- object_type: entity
- claim_text: The 7th recommended work-from-home job for seniors was remote travel agent.
- domain: task

Now extract from this conversation chunk:
{chunk_text}
""".strip()

    if compact:
        return f"""
Extract durable memory from the text and return valid JSON.

Required top-level keys:
- "entities"
- "claims"
- "evidence_spans"
- "open_questions"

Each claim must include:
- "claim_id"
- "subject"
- "predicate"
- "object"
- "object_type"
- "claim_text"
- "domain"
- "extraction_run_id"

Use atomic SPO claims.
Canonical entity examples:
- Company:Vercel
- Product:Vercel_Functions
- Person:Jane_Doe
- Plan:Pro

Allowed domains:
- product
- pricing
- team
- technology
- company
- security

Common predicates:
- has_product
- price_usd_monthly
- has_ceo
- has_founder
- headquartered_in
- has_soc2

Rules:
- Only extract facts directly supported by the text.
- If a fact is missing, add an "open_questions" item instead of guessing.
- "object_type" must be one of: entity, literal, enum, range, unknown.
- Keep evidence quotes short and directly grounded in the text.
- prioritize the most durable facts instead of exhaustive coverage.
- Return at most 6 entities and at most 8 claims.
- Ignore repetitive marketing copy, UI labels, navigation items, and one-word feature slogans.
- Prefer one strong claim over many weak paraphrases.

Text:
{chunk_text}
""".strip()

    return f"""
You are extracting durable memory records from a source chunk.

Return valid JSON with exactly these top-level keys:
- "entities": array of entity objects
- "claims": array of claim objects
- "evidence_spans": array of evidence objects
- "open_questions": array of unanswered questions

Use atomic SPO claims. Every claim must include:
- "claim_id"
- "subject"
- "predicate"
- "object"
- "object_type"
- "claim_text"
- "domain"
- "extraction_run_id"

Entity object shape:
{{
  "entity_id": "Company:Vercel",
  "entity_type": "company",
  "canonical_name": "Vercel",
  "namespace": "company"
}}

Claim object shape:
{{
  "claim_id": "claim-1",
  "subject": "Company:Vercel",
  "predicate": "has_product",
  "object": "Vercel Functions",
  "object_type": "entity",
  "claim_text": "Vercel offers Vercel Functions.",
  "domain": "product",
  "valid_time_start": null,
  "valid_time_end": null,
  "extraction_run_id": "chunk-local"
}}

Evidence object shape:
{{
  "claim_id": "claim-1",
  "quote_text": "Vercel Functions lets you run serverless code.",
  "source_id": "chunk-local-source",
  "chunk_id": "chunk-local-id",
  "extraction_run_id": "chunk-local",
  "start_offset": null,
  "end_offset": null,
  "evidence_strength": 0.9
}}

Open question shape:
{{
  "question": "What is the enterprise price?",
  "domain": "pricing",
  "reason": "Pricing page mentions only Pro and Team tiers."
}}

Allowed memory domains:
- product
- pricing
- team
- technology
- company
- security

Example predicates by domain:
- product: has_product, has_feature, serves_use_case
- pricing: has_pricing_tier, price_usd_monthly, has_enterprise_plan
- team: employs_person, has_ceo, has_founder
- technology: uses_database, uses_framework, offers_api
- company: headquartered_in, founded_date, serves_customer_segment
- security: has_soc2, supports_sso, supports_scim

Rules:
- Prefer canonical entities like Company:Vercel or Person:Jane_Doe.
- "object_type" must be one of: entity, literal, enum, range, unknown.
- Claims must be directly supported by the text. Do not hallucinate.
- If the text implies a likely fact but does not clearly state it, emit an open question instead of a claim.
- If no durable claim exists for a domain that would normally matter, add an open question for that gap.
- Keep claims atomic. Split compound statements into multiple claims.

Few-shot example:
Input text:
"Vercel offers Functions and Edge Config. Pricing for Pro starts at $20/month. The company was founded by Guillermo Rauch."

Output JSON:
{{
  "entities": [
    {{"entity_id": "Company:Vercel", "entity_type": "company", "canonical_name": "Vercel", "namespace": "company"}},
    {{"entity_id": "Product:Vercel_Functions", "entity_type": "product", "canonical_name": "Vercel Functions", "namespace": "company"}},
    {{"entity_id": "Product:Edge_Config", "entity_type": "product", "canonical_name": "Edge Config", "namespace": "company"}},
    {{"entity_id": "Plan:Pro", "entity_type": "plan", "canonical_name": "Pro", "namespace": "company"}},
    {{"entity_id": "Person:Guillermo_Rauch", "entity_type": "person", "canonical_name": "Guillermo Rauch", "namespace": "company"}}
  ],
  "claims": [
    {{"claim_id": "claim-1", "subject": "Company:Vercel", "predicate": "has_product", "object": "Product:Vercel_Functions", "object_type": "entity", "claim_text": "Vercel offers Vercel Functions.", "domain": "product", "valid_time_start": null, "valid_time_end": null, "extraction_run_id": "chunk-local"}},
    {{"claim_id": "claim-2", "subject": "Company:Vercel", "predicate": "has_product", "object": "Product:Edge_Config", "object_type": "entity", "claim_text": "Vercel offers Edge Config.", "domain": "product", "valid_time_start": null, "valid_time_end": null, "extraction_run_id": "chunk-local"}},
    {{"claim_id": "claim-3", "subject": "Plan:Pro", "predicate": "price_usd_monthly", "object": "20", "object_type": "literal", "claim_text": "Pro starts at $20/month.", "domain": "pricing", "valid_time_start": null, "valid_time_end": null, "extraction_run_id": "chunk-local"}},
    {{"claim_id": "claim-4", "subject": "Company:Vercel", "predicate": "has_founder", "object": "Person:Guillermo_Rauch", "object_type": "entity", "claim_text": "Vercel was founded by Guillermo Rauch.", "domain": "team", "valid_time_start": null, "valid_time_end": null, "extraction_run_id": "chunk-local"}}
  ],
  "evidence_spans": [
    {{"claim_id": "claim-1", "quote_text": "Vercel offers Functions", "source_id": "chunk-local-source", "chunk_id": "chunk-local-id", "extraction_run_id": "chunk-local", "start_offset": null, "end_offset": null, "evidence_strength": 0.9}}
  ],
  "open_questions": [
    {{"question": "What security certifications does Vercel hold?", "domain": "security", "reason": "No security details were stated in the text."}}
  ]
}}

Now extract from this chunk:
{chunk_text}
""".strip()
