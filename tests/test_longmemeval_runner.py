import json
from pathlib import Path

from mnemograph.engine import QueryResult
from mnemograph.llm.mock import MockLLMClient
from mnemograph.retrieval.classify import RetrievalDecision


def test_run_longmemeval_case_replays_history_and_writes_artifacts(tmp_path):
    from mnemograph.benchmarks.longmemeval import load_longmemeval_cases, run_longmemeval_cases

    fixture_path = Path(__file__).parent / "fixtures" / "benchmarks" / "longmemeval_smoke.json"
    cases = load_longmemeval_cases(fixture_path)
    llm_client = MockLLMClient(
        responses={
            "extract": [
                {
                    "entities": [],
                    "claims": [],
                    "evidence_spans": [],
                    "open_questions": [],
                },
                {
                    "entities": [{"entity_id": "Plan:Pro", "entity_type": "plan", "canonical_name": "Pro", "namespace": "company"}],
                    "claims": [
                        {
                            "claim_id": "claim-1",
                            "subject": "Plan:Pro",
                            "predicate": "price_usd_monthly",
                            "object": "49",
                            "object_type": "literal",
                            "claim_text": "The Pro plan costs $49/month.",
                            "domain": "pricing",
                            "extraction_run_id": "run-1",
                        }
                    ],
                    "evidence_spans": [],
                    "open_questions": [],
                },
                {
                    "entities": [],
                    "claims": [],
                    "evidence_spans": [],
                    "open_questions": [],
                },
                {
                    "entities": [{"entity_id": "Plan:Pro", "entity_type": "plan", "canonical_name": "Pro", "namespace": "company"}],
                    "claims": [
                        {
                            "claim_id": "claim-2",
                            "subject": "Plan:Pro",
                            "predicate": "price_usd_monthly",
                            "object": "59",
                            "object_type": "literal",
                            "claim_text": "The Pro plan now costs $59/month.",
                            "domain": "pricing",
                            "extraction_run_id": "run-2",
                        }
                    ],
                    "evidence_spans": [],
                    "open_questions": [],
                },
            ],
            "answer": {
                "answer": "The Pro plan now costs $59/month. [1]",
                "confidence": 0.91,
                "citations": [],
            },
        }
    )

    result = run_longmemeval_cases(
        cases=cases,
        working_base_dir=tmp_path / "working",
        result_base_dir=tmp_path / "results",
        llm_client=llm_client,
        replay_mode="full-history",
        run_slug="smoke-run",
    )

    assert result.result_dir == tmp_path / "results" / "longmemeval" / "smoke-run"
    assert result.summary.example_count == 1
    assert result.summary.open_question_total == 0
    assert result.summary.evaluator_failed == 0
    assert result.traces[0].ingest_count == 4
    assert result.traces[0].retrieval_mode == "STRUCTURED_LOOKUP"

    config_path = result.result_dir / "config.json"
    predictions_path = result.result_dir / "predictions.jsonl"
    traces_path = result.result_dir / "traces.jsonl"
    summary_path = result.result_dir / "summary.md"

    assert config_path.exists()
    assert predictions_path.exists()
    assert traces_path.exists()
    assert summary_path.exists()

    predictions = [json.loads(line) for line in predictions_path.read_text(encoding="utf-8").splitlines()]
    traces = [json.loads(line) for line in traces_path.read_text(encoding="utf-8").splitlines()]

    assert predictions == [
        {
            "question_id": "q-001",
            "hypothesis": "The Pro plan now costs $59/month. [1]",
        }
    ]
    assert traces[0]["example_id"] == "q-001"
    assert traces[0]["ingest_count"] == 4
    assert "examples: 1" in summary_path.read_text(encoding="utf-8")


def test_run_longmemeval_benchmark_returns_cli_summary_shape(tmp_path):
    from mnemograph.benchmarks.longmemeval import run_longmemeval_benchmark

    fixture_path = Path(__file__).parent / "fixtures" / "benchmarks" / "longmemeval_smoke.json"
    llm_client = MockLLMClient(
        responses={
            "extract": [
                {
                    "entities": [],
                    "claims": [],
                    "evidence_spans": [],
                    "open_questions": [],
                },
                {
                    "entities": [{"entity_id": "Plan:Pro", "entity_type": "plan", "canonical_name": "Pro", "namespace": "company"}],
                    "claims": [
                        {
                            "claim_id": "claim-1",
                            "subject": "Plan:Pro",
                            "predicate": "price_usd_monthly",
                            "object": "49",
                            "object_type": "literal",
                            "claim_text": "The Pro plan costs $49/month.",
                            "domain": "pricing",
                            "extraction_run_id": "run-1",
                        }
                    ],
                    "evidence_spans": [],
                    "open_questions": [],
                },
                {
                    "entities": [],
                    "claims": [],
                    "evidence_spans": [],
                    "open_questions": [],
                },
                {
                    "entities": [{"entity_id": "Plan:Pro", "entity_type": "plan", "canonical_name": "Pro", "namespace": "company"}],
                    "claims": [
                        {
                            "claim_id": "claim-2",
                            "subject": "Plan:Pro",
                            "predicate": "price_usd_monthly",
                            "object": "59",
                            "object_type": "literal",
                            "claim_text": "The Pro plan now costs $59/month.",
                            "domain": "pricing",
                            "extraction_run_id": "run-2",
                        }
                    ],
                    "evidence_spans": [],
                    "open_questions": [],
                },
            ],
            "answer": {
                "answer": "$59/month",
                "confidence": 0.91,
                "citations": [],
            },
        }
    )

    result = run_longmemeval_benchmark(
        dataset_path=fixture_path,
        result_base_dir=tmp_path / "results",
        working_base_dir=tmp_path / "working",
        llm_client=llm_client,
        replay_mode="full-history",
        case_limit=1,
        run_slug="smoke-run",
    )

    assert result["benchmark"] == "longmemeval"
    assert result["status"] == "proxy_only"
    assert result["case_count"] == 1
    assert result["proxy_exact_match"] == 1.0
    assert result["proxy_relaxed_exact_match"] == 1.0
    assert result["proxy_contains_match"] == 1.0
    assert result["result_dir"] == str(tmp_path / "results" / "longmemeval" / "smoke-run")


def test_run_longmemeval_cases_passes_question_date_and_session_date_metadata(tmp_path, monkeypatch):
    from mnemograph.benchmarks import longmemeval as longmemeval_module

    fixture_path = Path(__file__).parent / "fixtures" / "benchmarks" / "longmemeval_smoke.json"
    cases = longmemeval_module.load_longmemeval_cases(fixture_path)
    captured_locators: list[str] = []
    captured_reference_dates: list[str | None] = []

    class FakeEngine:
        def __init__(self, base_dir, llm_client):
            self.base_dir = base_dir
            self.llm_client = llm_client

        def ingest(self, locator: str, content: str, source_type: str = "url", trust_tier: str = "primary"):
            captured_locators.append(locator)
            return None

        def query(self, question: str, reference_date: str | None = None):
            captured_reference_dates.append(reference_date)
            return QueryResult(
                answer="stub",
                claims=[],
                confidence=0.4,
                provenance=None,
                retrieval=RetrievalDecision("SEMANTIC_SEARCH", [], [], False, False, 0.6),
            )

    monkeypatch.setattr(longmemeval_module, "Mnemograph", FakeEngine)

    longmemeval_module.run_longmemeval_cases(
        cases=cases,
        working_base_dir=tmp_path / "working",
        result_base_dir=tmp_path / "results",
        llm_client=MockLLMClient(
            responses={
                "extract": {
                    "entities": [],
                    "claims": [],
                    "evidence_spans": [],
                    "open_questions": [],
                },
                "answer": {
                    "answer": "unused",
                    "confidence": 0.1,
                    "citations": [],
                },
            }
        ),
        replay_mode="full-history",
        run_slug="metadata-run",
    )

    assert captured_reference_dates == [cases[0].question_date]
    assert captured_locators
    assert f"@{cases[0].haystack_dates[0]}" in captured_locators[0]
