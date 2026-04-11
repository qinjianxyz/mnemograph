from pathlib import Path


def test_create_result_dir_creates_benchmark_timestamp_tree(tmp_path):
    from mnemograph.benchmarks.common import create_result_dir

    result_dir = create_result_dir(
        benchmark_name="longmemeval",
        result_base_dir=tmp_path,
        run_slug="2026-04-11T12-00-00Z",
    )

    assert result_dir == tmp_path / "longmemeval" / "2026-04-11T12-00-00Z"
    assert result_dir.exists()
    assert result_dir.is_dir()


def test_benchmark_trace_row_serializes_to_dict():
    from mnemograph.benchmarks.common import BenchmarkTraceRow

    row = BenchmarkTraceRow(
        benchmark="longmemeval",
        example_id="q-001",
        question="What changed?",
        ingest_count=3,
        claim_count=9,
        open_question_count=2,
        retrieval_mode="MULTI_PATH",
        confidence=0.72,
        provenance_present=True,
        answer="The plan changed. [1]",
        evaluator_passed=None,
        failure_bucket="retrieval",
    )

    assert row.to_record() == {
        "benchmark": "longmemeval",
        "example_id": "q-001",
        "question": "What changed?",
        "ingest_count": 3,
        "claim_count": 9,
        "open_question_count": 2,
        "retrieval_mode": "MULTI_PATH",
        "confidence": 0.72,
        "provenance_present": True,
        "answer": "The plan changed. [1]",
        "evaluator_passed": None,
        "failure_bucket": "retrieval",
    }


def test_summarize_trace_rows_aggregates_latency_and_failure_counts():
    from mnemograph.benchmarks.common import BenchmarkSummary, BenchmarkTraceRow

    summary = BenchmarkSummary.from_trace_rows(
        benchmark="longmemeval",
        latency_ms=1532.4,
        traces=[
            BenchmarkTraceRow(
                benchmark="longmemeval",
                example_id="q-001",
                question="What does Pro cost?",
                ingest_count=2,
                claim_count=4,
                open_question_count=0,
                retrieval_mode="STRUCTURED_LOOKUP",
                confidence=0.88,
                provenance_present=True,
                answer="Pro costs $49/month. [1]",
                evaluator_passed=True,
                failure_bucket=None,
            ),
            BenchmarkTraceRow(
                benchmark="longmemeval",
                example_id="q-002",
                question="Who leads the company?",
                ingest_count=2,
                claim_count=4,
                open_question_count=1,
                retrieval_mode="SEMANTIC_SEARCH",
                confidence=0.41,
                provenance_present=False,
                answer="I don't know based on the current memory.",
                evaluator_passed=False,
                failure_bucket="extraction",
            ),
        ],
    )

    assert summary.benchmark == "longmemeval"
    assert summary.example_count == 2
    assert summary.evaluator_passed == 1
    assert summary.evaluator_failed == 1
    assert summary.open_question_total == 1
    assert summary.provenance_coverage == 0.5
    assert summary.failure_buckets == {"extraction": 1}
    assert summary.latency_ms == 1532.4
