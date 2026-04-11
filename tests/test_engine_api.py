from mnemograph.engine import Mnemograph
from mnemograph.llm.mock import MockLLMClient
from mnemograph.retrieval.classify import RetrievalDecision


def test_engine_ingest_text_and_query(tmp_path):
    engine = Mnemograph(tmp_path, llm_client=MockLLMClient(
        responses={
            "extract": {
                "entities": [{"entity_id": "Plan:Enterprise", "entity_type": "plan", "canonical_name": "Enterprise", "namespace": "company"}],
                "claims": [{
                    "claim_id": "claim-1",
                    "subject": "Plan:Enterprise",
                    "predicate": "price_usd_monthly",
                    "object": "500",
                    "object_type": "literal",
                    "claim_text": "Enterprise plan costs $500/month.",
                    "domain": "pricing",
                    "extraction_run_id": "run-1",
                }],
                "evidence_spans": [],
            }
        }
    ))

    ingest_result = engine.ingest_text("Enterprise plan costs $500/month.", source="user")
    query_result = engine.query("What does Enterprise cost?")

    assert ingest_result.claim_ids
    assert "500" in query_result.answer
    assert query_result.claims


def test_engine_structured_lookup_supports_product_and_team_domains(tmp_path):
    engine = Mnemograph(
        tmp_path,
        llm_client=MockLLMClient(
            responses={
                "extract": {
                    "entities": [
                        {
                            "entity_id": "Company:Stripe",
                            "entity_type": "company",
                            "canonical_name": "Stripe",
                            "namespace": "company",
                        },
                        {
                            "entity_id": "Product:Billing",
                            "entity_type": "product",
                            "canonical_name": "Billing",
                            "namespace": "company",
                        },
                    ],
                    "claims": [
                        {
                            "claim_id": "claim-1",
                            "subject": "Company:Stripe",
                            "predicate": "has_product",
                            "object": "Product:Billing",
                            "object_type": "entity",
                            "claim_text": "Stripe offers Billing.",
                            "domain": "product",
                            "extraction_run_id": "run-1",
                        },
                        {
                            "claim_id": "claim-2",
                            "subject": "Company:Stripe",
                            "predicate": "has_ceo",
                            "object": "Patrick Collison",
                            "object_type": "literal",
                            "claim_text": "Stripe is led by Patrick Collison.",
                            "domain": "team",
                            "extraction_run_id": "run-1",
                        },
                    ],
                    "evidence_spans": [],
                    "open_questions": [],
                }
            }
        ),
    )

    engine.ingest_text("Stripe offers Billing and is led by Patrick Collison.", source="website")

    product_result = engine.query("What products does stripe offer?")
    team_result = engine.query("Who leads Stripe?")

    assert product_result.retrieval.mode == "STRUCTURED_LOOKUP"
    assert product_result.claims[0]["predicate_id"] == "has_product"
    assert team_result.retrieval.mode == "STRUCTURED_LOOKUP"
    assert team_result.claims[0]["predicate_id"] == "has_ceo"


def test_engine_semantic_search_ranks_more_relevant_claims_first(tmp_path):
    engine = Mnemograph(
        tmp_path,
        llm_client=MockLLMClient(
            responses={
                "extract": {
                    "entities": [
                        {
                            "entity_id": "Company:Vercel",
                            "entity_type": "company",
                            "canonical_name": "Vercel",
                            "namespace": "company",
                        }
                    ],
                    "claims": [
                        {
                            "claim_id": "claim-1",
                            "subject": "Company:Vercel",
                            "predicate": "company_summary",
                            "object": "frontend cloud platform",
                            "object_type": "literal",
                            "claim_text": "Vercel is a frontend cloud platform for web applications.",
                            "domain": "company",
                            "extraction_run_id": "run-1",
                        },
                        {
                            "claim_id": "claim-2",
                            "subject": "Plan:Pro",
                            "predicate": "price_usd_monthly",
                            "object": "20",
                            "object_type": "literal",
                            "claim_text": "Vercel Pro costs $20/month.",
                            "domain": "pricing",
                            "extraction_run_id": "run-1",
                        },
                    ],
                    "evidence_spans": [],
                    "open_questions": [],
                }
            }
        ),
    )

    engine.ingest_text("Vercel is a frontend cloud platform. Pro costs $20/month.", source="website")
    result = engine.query("What does Vercel do?")

    assert result.retrieval.mode == "SEMANTIC_SEARCH"
    assert result.claims[0]["predicate_id"] == "company_summary"


def test_query_returns_synthesized_answer_with_provenance_chain(tmp_path):
    engine = Mnemograph(
        tmp_path,
        llm_client=MockLLMClient(
            responses={
                "extract": {
                    "entities": [{"entity_id": "Plan:Pro", "entity_type": "plan", "canonical_name": "Pro", "namespace": "company"}],
                    "claims": [{
                        "claim_id": "claim-1",
                        "subject": "Plan:Pro",
                        "predicate": "price_usd_monthly",
                        "object": "49",
                        "object_type": "literal",
                        "claim_text": "Pro costs $49/month.",
                        "domain": "pricing",
                        "extraction_run_id": "run-1",
                    }],
                    "evidence_spans": [{
                        "claim_id": "claim-1",
                        "quote_text": "Pro costs $49/month.",
                        "source_id": "chunk-local-source",
                        "chunk_id": "chunk-local-id",
                        "extraction_run_id": "run-1",
                    }],
                    "open_questions": [],
                },
                "answer": {
                    "answer": "The Pro plan costs $49/month. [1]",
                    "confidence": 0.82,
                    "citations": ["claim-1"],
                },
            }
        ),
    )

    engine.ingest("https://acme.com/pricing", "Pro costs $49/month.", source_type="url")
    result = engine.query("What does Pro cost?")

    assert result.answer == "The Pro plan costs $49/month. [1]"
    assert result.provenance is not None
    assert "https://acme.com/pricing" in result.provenance
    assert "Pro costs $49/month." in result.provenance


def test_provenance_query_reuses_last_active_context(tmp_path):
    engine = Mnemograph(
        tmp_path,
        llm_client=MockLLMClient(
            responses={
                "extract": {
                    "entities": [{"entity_id": "Plan:Pro", "entity_type": "plan", "canonical_name": "Pro", "namespace": "company"}],
                    "claims": [{
                        "claim_id": "claim-1",
                        "subject": "Plan:Pro",
                        "predicate": "price_usd_monthly",
                        "object": "49",
                        "object_type": "literal",
                        "claim_text": "Pro costs $49/month.",
                        "domain": "pricing",
                        "extraction_run_id": "run-1",
                    }],
                    "evidence_spans": [{
                        "claim_id": "claim-1",
                        "quote_text": "Pro costs $49/month.",
                        "source_id": "chunk-local-source",
                        "chunk_id": "chunk-local-id",
                        "extraction_run_id": "run-1",
                    }],
                    "open_questions": [],
                }
            }
        ),
    )

    engine.ingest("https://acme.com/pricing", "Pro costs $49/month.", source_type="url")
    first = engine.query("What does Pro cost?")
    provenance = engine.query("How do you know this?")

    assert first.provenance is not None
    assert provenance.retrieval.mode == "GRAPH_TRAVERSAL"
    assert provenance.answer is not None
    assert "https://acme.com/pricing" in provenance.answer
    assert "Pro costs $49/month." in provenance.answer


def test_render_changelog_reports_superseded_claims(tmp_path):
    engine = Mnemograph(
        tmp_path,
        llm_client=MockLLMClient(
            responses={
                "extract": {
                    "entities": [{"entity_id": "Plan:Pro", "entity_type": "plan", "canonical_name": "Pro", "namespace": "company"}],
                    "claims": [{
                        "claim_id": "claim-1",
                        "subject": "Plan:Pro",
                        "predicate": "price_usd_monthly",
                        "object": "49",
                        "object_type": "literal",
                        "claim_text": "Pro costs $49/month.",
                        "domain": "pricing",
                        "extraction_run_id": "run-1",
                    }],
                    "evidence_spans": [],
                    "open_questions": [],
                }
            }
        ),
    )
    engine.ingest("https://acme.com/pricing", "Pro costs $49/month.", source_type="url")

    engine.llm_client = MockLLMClient(
        responses={
            "extract": {
                "entities": [{"entity_id": "Plan:Pro", "entity_type": "plan", "canonical_name": "Pro", "namespace": "company"}],
                "claims": [{
                    "claim_id": "claim-2",
                    "subject": "Plan:Pro",
                    "predicate": "price_usd_monthly",
                    "object": "59",
                    "object_type": "literal",
                    "claim_text": "Pro costs $59/month.",
                    "domain": "pricing",
                    "extraction_run_id": "run-2",
                }],
                "evidence_spans": [],
                "open_questions": [],
            }
        }
    )
    second = engine.ingest_text("Pro costs $59/month.", source="user")
    changelog = engine.render_changelog(second.extraction_run_id)

    assert "SUPERSEDED:" in changelog
    assert "$49" in changelog
    assert "$59" in changelog


def test_query_applies_low_confidence_hedging_to_llm_answer(tmp_path):
    engine = Mnemograph(
        tmp_path,
        llm_client=MockLLMClient(
            responses={
                "extract": {
                    "entities": [{"entity_id": "Plan:Pro", "entity_type": "plan", "canonical_name": "Pro", "namespace": "company"}],
                    "claims": [{
                        "claim_id": "claim-1",
                        "subject": "Plan:Pro",
                        "predicate": "price_usd_monthly",
                        "object": "49",
                        "object_type": "literal",
                        "claim_text": "Pro costs $49/month.",
                        "domain": "pricing",
                        "confidence": 0.3,
                        "extraction_run_id": "run-1",
                    }],
                    "evidence_spans": [{
                        "claim_id": "claim-1",
                        "quote_text": "Pro costs $49/month.",
                        "source_id": "chunk-local-source",
                        "chunk_id": "chunk-local-id",
                        "extraction_run_id": "run-1",
                    }],
                    "open_questions": [],
                },
                "answer": {
                    "answer": "Pro costs $49/month.",
                    "confidence": 0.3,
                    "citations": ["claim-1"],
                },
            }
        ),
    )

    engine.ingest("https://acme.com/pricing-rumor", "Pro costs $49/month.", source_type="url", trust_tier="low")
    result = engine.query("What does Pro cost?")

    assert "not fully confident" in result.answer.lower()


def test_query_includes_source_snippets_and_reference_date_in_answer_prompt(tmp_path):
    class RecordingLLMClient:
        def __init__(self):
            self.answer_prompts: list[str] = []

        def generate_structured(self, operation: str, prompt: str, required_keys: tuple[str, ...]) -> dict:
            if operation == "extract":
                return {
                    "entities": [{"entity_id": "User:Primary", "entity_type": "user", "canonical_name": "Primary", "namespace": "conversation"}],
                    "claims": [{
                        "claim_id": "claim-1",
                        "subject": "User:Primary",
                        "predicate": "bought_item",
                        "object": "gift for sister's birthday",
                        "object_type": "literal",
                        "claim_text": "Primary bought gift for sister's birthday.",
                        "domain": "personal",
                        "extraction_run_id": "run-1",
                    }],
                    "evidence_spans": [{
                        "claim_id": "claim-1",
                        "quote_text": "gifts for my sister's birthday",
                        "source_id": "chunk-local-source",
                        "chunk_id": "chunk-local-id",
                        "extraction_run_id": "run-1",
                    }],
                    "open_questions": [],
                }
            self.answer_prompts.append(prompt)
            return {
                "answer": "You bought a yellow dress. [1]",
                "confidence": 0.83,
                "citations": ["claim-1"],
            }

    llm_client = RecordingLLMClient()
    engine = Mnemograph(tmp_path, llm_client=llm_client)
    engine.ingest(
        locator="longmemeval:q-001:session-0:4@2022/03/09 (Wed) 04:12",
        content="user: For my sister's birthday, I got her a yellow dress and a pair of earrings to match.",
        source_type="conversation",
        trust_tier="primary",
    )

    result = engine.query(
        "What did I buy for my sister's birthday gift?",
        reference_date="2022/04/04 (Mon) 01:38",
    )

    assert result.answer == "You bought a yellow dress. [1]"
    assert llm_client.answer_prompts
    assert "Source snippets:" in llm_client.answer_prompts[0]
    assert "yellow dress" in llm_client.answer_prompts[0]
    assert "Reference date: 2022/04/04 (Mon) 01:38" in llm_client.answer_prompts[0]
