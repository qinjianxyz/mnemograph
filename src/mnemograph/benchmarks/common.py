"""Shared models and artifact helpers for public benchmark runs."""

from collections import Counter
from dataclasses import asdict, dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class BenchmarkTraceRow:
    """One per-example benchmark trace row."""

    benchmark: str
    example_id: str
    question: str
    ingest_count: int
    claim_count: int
    open_question_count: int
    retrieval_mode: str
    confidence: float
    provenance_present: bool
    answer: str
    evaluator_passed: bool | None
    failure_bucket: str | None

    def to_record(self) -> dict:
        """Return a JSON-serializable record."""
        return asdict(self)


@dataclass(frozen=True)
class BenchmarkSummary:
    """Aggregate metrics for one benchmark run."""

    benchmark: str
    example_count: int
    evaluator_passed: int
    evaluator_failed: int
    open_question_total: int
    provenance_coverage: float
    failure_buckets: dict[str, int]
    latency_ms: float

    @classmethod
    def from_trace_rows(
        cls,
        benchmark: str,
        latency_ms: float,
        traces: list[BenchmarkTraceRow],
    ) -> "BenchmarkSummary":
        """Summarize a benchmark run from per-example traces."""
        example_count = len(traces)
        evaluator_passed = sum(1 for trace in traces if trace.evaluator_passed is True)
        evaluator_failed = sum(1 for trace in traces if trace.evaluator_passed is False)
        open_question_total = sum(trace.open_question_count for trace in traces)
        provenance_hits = sum(1 for trace in traces if trace.provenance_present)
        provenance_coverage = provenance_hits / example_count if example_count else 0.0
        failure_buckets = dict(
            sorted(
                Counter(
                    trace.failure_bucket
                    for trace in traces
                    if trace.failure_bucket is not None
                ).items()
            )
        )
        return cls(
            benchmark=benchmark,
            example_count=example_count,
            evaluator_passed=evaluator_passed,
            evaluator_failed=evaluator_failed,
            open_question_total=open_question_total,
            provenance_coverage=provenance_coverage,
            failure_buckets=failure_buckets,
            latency_ms=latency_ms,
        )


def create_result_dir(
    benchmark_name: str,
    result_base_dir: str | Path,
    run_slug: str,
) -> Path:
    """Create and return a benchmark result directory."""
    result_dir = Path(result_base_dir) / benchmark_name / run_slug
    result_dir.mkdir(parents=True, exist_ok=True)
    return result_dir


def write_json(path: str | Path, payload: dict) -> None:
    """Write one JSON file with stable formatting."""
    Path(path).write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def write_jsonl(path: str | Path, records: list[dict]) -> None:
    """Write newline-delimited JSON records."""
    Path(path).write_text(
        "\n".join(json.dumps(record, sort_keys=True) for record in records) + ("\n" if records else ""),
        encoding="utf-8",
    )
