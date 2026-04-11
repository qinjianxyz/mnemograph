from mnemograph.demo import run_demo
from mnemograph.llm.mock import MockLLMClient


def test_run_demo_executes_end_to_end_with_mocked_llm(tmp_path):
    pages = {
        "https://stripe.com": """
            <html><body><main>
            <h1>Stripe</h1>
            <p>Stripe offers Billing.</p>
            <p>Stripe powers internet payments.</p>
            <a href="/pricing">Pricing</a>
            <a href="/about">About</a>
            </main></body></html>
        """,
        "https://stripe.com/pricing": """
            <html><body><main>
            <p>Pro costs $49/month.</p>
            </main></body></html>
        """,
        "https://stripe.com/about": """
            <html><body><main>
            <p>Stripe is led by Patrick Collison.</p>
            </main></body></html>
        """,
    }

    def fetcher(url: str) -> str:
        return pages[url]

    llm_client = MockLLMClient(
        responses={
            "extract": [
                {
                    "entities": [
                        {"entity_id": "Company:Stripe", "entity_type": "company", "canonical_name": "Stripe", "namespace": "company"},
                        {"entity_id": "Product:Billing", "entity_type": "product", "canonical_name": "Billing", "namespace": "company"},
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
                    ],
                    "evidence_spans": [
                        {"claim_id": "claim-1", "quote_text": "Stripe offers Billing.", "source_id": "chunk-local-source", "chunk_id": "chunk-local-id", "extraction_run_id": "run-1"},
                    ],
                    "open_questions": [],
                },
                {
                    "entities": [{"entity_id": "Plan:Pro", "entity_type": "plan", "canonical_name": "Pro", "namespace": "company"}],
                    "claims": [
                        {
                            "claim_id": "claim-2",
                            "subject": "Plan:Pro",
                            "predicate": "price_usd_monthly",
                            "object": "49",
                            "object_type": "literal",
                            "claim_text": "Pro costs $49/month.",
                            "domain": "pricing",
                            "extraction_run_id": "run-1b",
                        }
                    ],
                    "evidence_spans": [
                        {"claim_id": "claim-2", "quote_text": "Pro costs $49/month.", "source_id": "chunk-local-source", "chunk_id": "chunk-local-id", "extraction_run_id": "run-1b"},
                    ],
                    "open_questions": [],
                },
                {
                    "entities": [{"entity_id": "Company:Stripe", "entity_type": "company", "canonical_name": "Stripe", "namespace": "company"}],
                    "claims": [
                        {
                            "claim_id": "claim-3",
                            "subject": "Company:Stripe",
                            "predicate": "has_ceo",
                            "object": "Patrick Collison",
                            "object_type": "literal",
                            "claim_text": "Stripe is led by Patrick Collison.",
                            "domain": "team",
                            "extraction_run_id": "run-1c",
                        }
                    ],
                    "evidence_spans": [
                        {"claim_id": "claim-3", "quote_text": "Stripe is led by Patrick Collison.", "source_id": "chunk-local-source", "chunk_id": "chunk-local-id", "extraction_run_id": "run-1c"},
                    ],
                    "open_questions": [],
                },
            ],
            "answer": [
                {"answer": "Stripe offers Billing. [1]", "confidence": 0.9, "citations": []},
                {"answer": "Stripe is led by Patrick Collison. [1]", "confidence": 0.9, "citations": []},
                {"answer": "Pro costs $49/month. [1]", "confidence": 0.85, "citations": []},
                {"answer": "Enterprise plan costs $500/month. [1]", "confidence": 0.9, "citations": []},
                {"answer": "I learned this from the pricing source. [1]", "confidence": 0.8, "citations": []},
            ],
        }
    )

    result = run_demo(
        base_dir=tmp_path,
        llm_client=llm_client,
        company_url="https://stripe.com",
        fetcher=fetcher,
    )

    assert result["stats"]["claim_count"] >= 3
    assert result["stats"]["domain_breakdown"]["pricing"] >= 1
    assert result["qa_results"][0]["retrieval_mode"] == "STRUCTURED_LOOKUP"
    assert "SUPERSEDED:" in result["changelog"]
    assert "Stripe Pro plan costs $59/month." in result["changelog"]
    assert "500" in result["recall_result"]["answer"]
    assert "memory/knowledge/pricing.json" in result["memory_state"]["files"]
    assert "memory/sources" in result["memory_state"]["tree"]


def test_run_demo_respects_max_pages_limit(tmp_path):
    pages = {
        "https://stripe.com": """
            <html><body><main>
            <h1>Stripe</h1>
            <p>Stripe offers Billing.</p>
            <a href="/pricing">Pricing</a>
            <a href="/about">About</a>
            </main></body></html>
        """,
        "https://stripe.com/pricing": "<html><body><main><p>Pro costs $49/month.</p></main></body></html>",
        "https://stripe.com/about": "<html><body><main><p>Stripe is led by Patrick Collison.</p></main></body></html>",
    }

    def fetcher(url: str) -> str:
        return pages[url]

    llm_client = MockLLMClient(
        responses={
            "extract": [
                {
                    "entities": [
                        {"entity_id": "Company:Stripe", "entity_type": "company", "canonical_name": "Stripe", "namespace": "company"},
                        {"entity_id": "Product:Billing", "entity_type": "product", "canonical_name": "Billing", "namespace": "company"},
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
                    ],
                    "evidence_spans": [],
                    "open_questions": [],
                },
            ],
            "answer": [
                {"answer": "Stripe offers Billing. [1]", "confidence": 0.9, "citations": []},
                {"answer": "I don't know. [1]", "confidence": 0.2, "citations": []},
                {"answer": "I don't know. [1]", "confidence": 0.2, "citations": []},
                {"answer": "Enterprise plan costs $500/month. [1]", "confidence": 0.9, "citations": []},
                {"answer": "I learned this from the user correction. [1]", "confidence": 0.8, "citations": []},
            ],
        }
    )

    result = run_demo(
        base_dir=tmp_path,
        llm_client=llm_client,
        company_url="https://stripe.com",
        fetcher=fetcher,
        max_pages=1,
    )

    assert result["crawl"]["pages_succeeded"] == 1
    assert "SUPERSEDED:" in result["changelog"]
