from pathlib import Path

import yaml


def test_golden_eval_case_loads_and_scores_expected_fields(tmp_path):
    from mnemograph.evals.harness import evaluate_scenario, load_eval_case
    from mnemograph.llm.mock import MockLLMClient

    case_path = Path(tmp_path) / "case.yaml"
    case_path.write_text(
        yaml.safe_dump(
            {
                "id": "pricing_conflict",
                "company_url": "https://example.com",
                "steps": [
                    {
                        "action": "ingest_text",
                        "content": "Pro costs $49/month.",
                        "source": "website",
                    },
                    {
                        "action": "query",
                        "question": "What does Pro cost?",
                        "expect_retrieval_mode": "STRUCTURED_LOOKUP",
                        "expect_answer_contains": "$49",
                    },
                ],
            }
        )
    )

    case = load_eval_case(case_path)
    result = evaluate_scenario(
        case,
        tmp_path / "memory",
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

    assert result["case_id"] == "pricing_conflict"
    assert result["score"]["passed"] == 2
    assert result["score"]["failed"] == 0
    assert result["metrics"]["latency_ms"] >= 0
    assert result["metrics"]["cost_usd"] >= 0


def test_naive_rag_baseline_runs_against_case():
    from mnemograph.evals.baselines import run_naive_rag_baseline

    case = {
        "id": "baseline_case",
        "steps": [
            {"action": "ingest_text", "content": "Stripe offers Billing.", "source": "website"},
            {"action": "query", "question": "What does Stripe offer?"},
        ],
    }

    result = run_naive_rag_baseline(case)

    assert result["baseline"] == "naive_rag"
    assert result["metrics"]["latency_ms"] >= 0
    assert result["metrics"]["cost_usd"] == 0.0
    assert result["outputs"][0]["answer"]


def test_structured_memory_baseline_runs_against_case(tmp_path):
    from mnemograph.evals.baselines import run_structured_memory_baseline
    from mnemograph.llm.mock import MockLLMClient

    case = {
        "id": "structured_case",
        "steps": [
            {"action": "ingest_text", "content": "Stripe offers Billing.", "source": "website"},
            {
                "action": "query",
                "question": "What does Stripe offer?",
                "expect_retrieval_mode": "STRUCTURED_LOOKUP",
            },
        ],
    }

    result = run_structured_memory_baseline(
        case,
        tmp_path / "memory",
        llm_client=MockLLMClient(
            responses={
                "extract": {
                    "entities": [
                        {"entity_id": "Company:Stripe", "entity_type": "company", "canonical_name": "Stripe", "namespace": "company"},
                        {"entity_id": "Product:Billing", "entity_type": "product", "canonical_name": "Billing", "namespace": "company"},
                    ],
                    "claims": [{
                        "claim_id": "claim-1",
                        "subject": "Company:Stripe",
                        "predicate": "has_product",
                        "object": "Product:Billing",
                        "object_type": "entity",
                        "claim_text": "Stripe offers Billing.",
                        "domain": "product",
                        "extraction_run_id": "run-1",
                    }],
                    "evidence_spans": [],
                    "open_questions": [],
                }
            }
        ),
    )

    assert result["baseline"] == "structured_memory"
    assert result["metrics"]["latency_ms"] >= 0
    assert result["metrics"]["cost_usd"] >= 0
    assert result["outputs"][0]["retrieval_mode"] == "STRUCTURED_LOOKUP"


def test_eval_harness_scores_provenance_and_confidence_expectations(tmp_path):
    from mnemograph.evals.harness import evaluate_scenario
    from mnemograph.llm.mock import MockLLMClient

    case = {
        "id": "provenance_low_confidence_case",
        "steps": [
            {
                "action": "ingest_url",
                "locator": "https://acme.com/pricing",
                "content": "Pro costs $49/month.",
                "trust_tier": "low",
            },
            {
                "action": "query",
                "question": "What does Pro cost?",
                "expect_answer_contains": "$49",
                "expect_provenance_contains": "https://acme.com/pricing",
                "expect_confidence_at_most": 0.3,
            },
        ],
    }

    result = evaluate_scenario(
        case,
        tmp_path / "memory",
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

    assert result["score"]["passed"] == 3
    assert result["score"]["failed"] == 0


def test_eval_harness_scores_ingest_open_question_changelog_and_conflict_expectations(tmp_path):
    from mnemograph.evals.harness import evaluate_scenario
    from mnemograph.llm.mock import MockLLMClient

    case = {
        "id": "adversarial_ingest_case",
        "steps": [
            {
                "action": "ingest_text",
                "content": "Build faster with Acme Cloud for every team in seconds.",
                "source": "website",
                "expect_claim_count_at_most": 0,
                "expect_open_question_count_at_least": 1,
                "expect_open_question_domain": "company",
            },
            {
                "action": "ingest_text",
                "content": "Pro costs $49/month.",
                "source": "website",
            },
            {
                "action": "ingest_text",
                "content": "A partner sheet says Pro costs $59/month.",
                "source": "website",
                "expect_changelog_contains": "CONFLICT:",
                "expect_conflict_type": "source_quality_conflict",
            },
        ],
    }

    result = evaluate_scenario(
        case,
        tmp_path / "memory",
        llm_client=MockLLMClient(
            responses={
                "extract": [
                    {
                        "entities": [{"entity_id": "Company:Acme_Cloud", "entity_type": "company", "canonical_name": "Acme Cloud", "namespace": "company"}],
                        "claims": [
                            {
                                "claim_id": "claim-0",
                                "subject": "Company:Acme_Cloud",
                                "predicate": "company_summary",
                                "object": "Build faster with Acme Cloud for every team in seconds.",
                                "object_type": "literal",
                                "claim_text": "Build faster with Acme Cloud for every team in seconds.",
                                "domain": "company",
                                "extraction_run_id": "run-0",
                            }
                        ],
                        "evidence_spans": [],
                        "open_questions": [],
                    },
                    {
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
                    },
                    {
                        "entities": [{"entity_id": "Plan:Pro", "entity_type": "plan", "canonical_name": "Pro", "namespace": "company"}],
                        "claims": [{
                            "claim_id": "claim-2",
                            "subject": "Plan:Pro",
                            "predicate": "price_usd_monthly",
                            "object": "59",
                            "object_type": "literal",
                            "claim_text": "A partner sheet says Pro costs $59/month.",
                            "domain": "pricing",
                            "extraction_run_id": "run-2",
                        }],
                        "evidence_spans": [],
                        "open_questions": [],
                    },
                ]
            }
        ),
    )

    assert result["score"]["passed"] == 5
    assert result["score"]["failed"] == 0


def test_eval_harness_supports_structured_ingest_for_semantic_conflict_cases(tmp_path):
    from mnemograph.evals.harness import evaluate_scenario
    from mnemograph.llm.mock import MockLLMClient

    case = {
        "id": "structured_conflict_case",
        "steps": [
            {
                "action": "ingest_candidates",
                "source": "website",
                "raw_text": "Pro costs $49/month.",
                "claims": [
                    {
                        "subject": "Plan:Pro",
                        "predicate": "price_usd_monthly",
                        "object": "49",
                        "object_type": "literal",
                        "claim_text": "Pro costs $49/month.",
                        "domain": "pricing",
                    }
                ],
            },
            {
                "action": "ingest_candidates",
                "source": "website",
                "raw_text": "Partner sheet says Pro costs $59/month.",
                "claims": [
                    {
                        "subject": "Plan:Pro",
                        "predicate": "price_usd_monthly",
                        "object": "59",
                        "object_type": "literal",
                        "claim_text": "Partner sheet says Pro costs $59/month.",
                        "domain": "pricing",
                    }
                ],
                "expect_changelog_contains": "CONFLICT:",
                "expect_conflict_type": "source_quality_conflict",
            },
        ],
    }

    result = evaluate_scenario(
        case,
        tmp_path / "memory",
        llm_client=MockLLMClient(responses={}),
    )

    assert result["score"]["passed"] == 2
    assert result["score"]["failed"] == 0


def test_golden_cases_cover_required_eval_slices():
    golden_dir = Path(__file__).resolve().parents[1] / "evals" / "golden"
    case_names = {path.name for path in golden_dir.glob("*.yaml")}

    assert "company_pricing_conflict.yaml" in case_names
    assert "conversation_distillation.yaml" in case_names
    assert "temporal_supersession.yaml" in case_names
    assert "store_during_conversation.yaml" in case_names
    assert "low_confidence_hedging.yaml" in case_names
    assert "provenance_chain.yaml" in case_names
    assert "messy_marketing_page.yaml" in case_names
    assert "qualified_pricing_scope.yaml" in case_names
    assert "source_disagreement.yaml" in case_names
