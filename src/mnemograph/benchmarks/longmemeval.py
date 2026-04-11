"""Thin LongMemEval adapter around the real Mnemograph product path."""

from dataclasses import dataclass
import json
from pathlib import Path
import re
import shutil
import subprocess
import time

from mnemograph.benchmarks.common import (
    BenchmarkSummary,
    BenchmarkTraceRow,
    create_result_dir,
    write_json,
    write_jsonl,
)
from mnemograph.engine import Mnemograph
from mnemograph.llm.client import StructuredLLMClient

@dataclass(frozen=True)
class LongMemEvalCase:
    """Official LongMemEval example shape used by the adapter."""

    question_id: str
    question_type: str
    question: str
    answer: str
    question_date: str
    haystack_session_ids: list[str]
    haystack_dates: list[str]
    haystack_sessions: list[list[dict]]
    answer_session_ids: list[str]


def load_longmemeval_cases(path: str | Path) -> list[LongMemEvalCase]:
    """Load LongMemEval examples from the official JSON structure."""
    raw_cases = json.loads(Path(path).read_text(encoding="utf-8"))
    return [
        LongMemEvalCase(
            question_id=raw_case["question_id"],
            question_type=raw_case["question_type"],
            question=raw_case["question"],
            answer=raw_case["answer"],
            question_date=raw_case["question_date"],
            haystack_session_ids=list(raw_case["haystack_session_ids"]),
            haystack_dates=list(raw_case["haystack_dates"]),
            haystack_sessions=list(raw_case["haystack_sessions"]),
            answer_session_ids=list(raw_case.get("answer_session_ids", [])),
        )
        for raw_case in raw_cases
    ]


def build_replay_steps(
    case: LongMemEvalCase,
    replay_mode: str = "full-history",
) -> list[dict]:
    """Convert one LongMemEval case into replayable ingest steps."""
    steps: list[dict] = []
    for session_id, session_date, session in zip(
        case.haystack_session_ids,
        case.haystack_dates,
        case.haystack_sessions,
        strict=False,
    ):
        if replay_mode == "oracle-history" and session_id not in case.answer_session_ids:
            continue
        for turn_index, turn in enumerate(session):
            steps.append(
                {
                    "session_id": session_id,
                    "session_date": session_date,
                    "turn_index": turn_index,
                    "role": turn["role"],
                    "content": f"{turn['role']}: {turn['content']}",
                    "has_answer": bool(turn.get("has_answer")),
                }
            )
    return steps


def format_prediction_record(question_id: str, hypothesis: str) -> dict[str, str]:
    """Return the official LongMemEval prediction record shape."""
    return {
        "question_id": question_id,
        "hypothesis": hypothesis,
    }


def build_evaluator_command(
    evaluator_script_path: str | Path,
    predictions_path: str | Path,
    dataset_path: str | Path,
    judge_model: str = "gpt-4o",
) -> list[str]:
    """Build the official evaluator subprocess command."""
    return [
        "python3",
        str(evaluator_script_path),
        judge_model,
        str(predictions_path),
        str(dataset_path),
    ]


def _normalize_answer(text: str) -> str:
    return " ".join(text.strip().lower().split())


def _normalize_answer_relaxed(text: str) -> str:
    collapsed = re.sub(r"[^a-z0-9]+", " ", text.lower())
    return " ".join(collapsed.split())


def evaluate_predictions(
    cases: list[LongMemEvalCase],
    predictions_path: str | Path,
    dataset_path: str | Path,
    evaluator_script_path: str | Path | None,
    judge_model: str = "gpt-4o",
) -> dict:
    """Evaluate predictions with the official evaluator when available, else a proxy metric."""
    predictions = [
        json.loads(line)
        for line in Path(predictions_path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    case_by_id = {case.question_id: case for case in cases}
    exact_matches = 0
    relaxed_matches = 0
    contains_matches = 0
    for prediction in predictions:
        case = case_by_id.get(prediction["question_id"])
        if not case:
            continue
        normalized_prediction = _normalize_answer(prediction["hypothesis"])
        normalized_gold = _normalize_answer(case.answer)
        relaxed_prediction = _normalize_answer_relaxed(prediction["hypothesis"])
        relaxed_gold = _normalize_answer_relaxed(case.answer)
        if normalized_prediction == normalized_gold:
            exact_matches += 1
        if relaxed_prediction == relaxed_gold:
            relaxed_matches += 1
        if relaxed_gold and (relaxed_gold in relaxed_prediction or relaxed_prediction in relaxed_gold):
            contains_matches += 1
    proxy_exact_match = exact_matches / len(predictions) if predictions else 0.0
    proxy_relaxed_exact_match = relaxed_matches / len(predictions) if predictions else 0.0
    proxy_contains_match = contains_matches / len(predictions) if predictions else 0.0

    if evaluator_script_path is None:
        return {
            "status": "proxy_only",
            "official_evaluator_ran": False,
            "proxy_exact_match": proxy_exact_match,
            "proxy_relaxed_exact_match": proxy_relaxed_exact_match,
            "proxy_contains_match": proxy_contains_match,
        }

    command = build_evaluator_command(
        evaluator_script_path=evaluator_script_path,
        predictions_path=predictions_path,
        dataset_path=dataset_path,
        judge_model=judge_model,
    )
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "status": "official" if completed.returncode == 0 else "official_failed",
        "official_evaluator_ran": True,
        "proxy_exact_match": proxy_exact_match,
        "proxy_relaxed_exact_match": proxy_relaxed_exact_match,
        "proxy_contains_match": proxy_contains_match,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "command": command,
    }


@dataclass(frozen=True)
class LongMemEvalRunResult:
    """Artifacts and summaries from one LongMemEval adapter run."""

    result_dir: Path
    predictions: list[dict[str, str]]
    traces: list[BenchmarkTraceRow]
    summary: BenchmarkSummary


def _write_summary_markdown(path: Path, summary: BenchmarkSummary) -> None:
    lines = [
        "# LongMemEval Run Summary",
        "",
        f"- benchmark: {summary.benchmark}",
        f"- examples: {summary.example_count}",
        f"- evaluator_passed: {summary.evaluator_passed}",
        f"- evaluator_failed: {summary.evaluator_failed}",
        f"- open_questions: {summary.open_question_total}",
        f"- provenance_coverage: {summary.provenance_coverage:.2f}",
        f"- latency_ms: {summary.latency_ms:.1f}",
    ]
    if summary.failure_buckets:
        lines.append(f"- failure_buckets: {summary.failure_buckets}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_longmemeval_cases(
    cases: list[LongMemEvalCase],
    working_base_dir: str | Path,
    result_base_dir: str | Path,
    llm_client: StructuredLLMClient,
    replay_mode: str = "full-history",
    run_slug: str = "latest",
) -> LongMemEvalRunResult:
    """Run LongMemEval cases through the real Mnemograph engine."""
    started = time.perf_counter()
    result_dir = create_result_dir("longmemeval", result_base_dir, run_slug)
    predictions: list[dict[str, str]] = []
    traces: list[BenchmarkTraceRow] = []
    working_root = Path(working_base_dir)
    working_root.mkdir(parents=True, exist_ok=True)

    for case in cases:
        case_base_dir = working_root / case.question_id
        if case_base_dir.exists():
            shutil.rmtree(case_base_dir)
        engine = Mnemograph(case_base_dir, llm_client=llm_client)
        replay_steps = build_replay_steps(case, replay_mode=replay_mode)
        for step in replay_steps:
            engine.ingest(
                locator=f"longmemeval:{case.question_id}:{step['session_id']}:{step['turn_index']}@{step['session_date']}",
                content=step["content"],
                source_type="conversation",
                trust_tier="primary",
            )
        query_result = engine.query(case.question, reference_date=case.question_date)
        predictions.append(
            format_prediction_record(
                question_id=case.question_id,
                hypothesis=query_result.answer,
            )
        )
        traces.append(
            BenchmarkTraceRow(
                benchmark="longmemeval",
                example_id=case.question_id,
                question=case.question,
                ingest_count=len(replay_steps),
                claim_count=len(query_result.claims),
                open_question_count=0,
                retrieval_mode=query_result.retrieval.mode,
                confidence=query_result.confidence,
                provenance_present=bool(query_result.provenance),
                answer=query_result.answer,
                evaluator_passed=None,
                failure_bucket=None,
            )
        )

    summary = BenchmarkSummary.from_trace_rows(
        benchmark="longmemeval",
        latency_ms=(time.perf_counter() - started) * 1000,
        traces=traces,
    )
    write_json(
        result_dir / "config.json",
        {
            "benchmark": "longmemeval",
            "replay_mode": replay_mode,
            "case_count": len(cases),
            "working_base_dir": str(working_root),
        },
    )
    write_jsonl(result_dir / "predictions.jsonl", predictions)
    write_jsonl(result_dir / "traces.jsonl", [trace.to_record() for trace in traces])
    _write_summary_markdown(result_dir / "summary.md", summary)
    return LongMemEvalRunResult(
        result_dir=result_dir,
        predictions=predictions,
        traces=traces,
        summary=summary,
    )


def run_longmemeval_benchmark(
    dataset_path: str | Path | None,
    result_base_dir: str | Path,
    working_base_dir: str | Path,
    llm_client: StructuredLLMClient,
    replay_mode: str = "full-history",
    case_limit: int | None = None,
    run_slug: str = "latest",
) -> dict:
    """Load a dataset file and execute a LongMemEval benchmark run."""
    if dataset_path is None:
        raise ValueError("dataset_path is required for LongMemEval runs")
    cases = load_longmemeval_cases(dataset_path)
    if case_limit is not None:
        cases = cases[:case_limit]
    run_result = run_longmemeval_cases(
        cases=cases,
        working_base_dir=working_base_dir,
        result_base_dir=result_base_dir,
        llm_client=llm_client,
        replay_mode=replay_mode,
        run_slug=run_slug,
    )
    evaluation = evaluate_predictions(
        cases=cases,
        predictions_path=run_result.result_dir / "predictions.jsonl",
        dataset_path=dataset_path,
        evaluator_script_path=None,
    )
    return {
        "benchmark": "longmemeval",
        "status": evaluation["status"],
        "case_count": len(cases),
        "proxy_exact_match": evaluation["proxy_exact_match"],
        "proxy_relaxed_exact_match": evaluation["proxy_relaxed_exact_match"],
        "proxy_contains_match": evaluation["proxy_contains_match"],
        "result_dir": str(run_result.result_dir),
        "latency_ms": run_result.summary.latency_ms,
        "official_evaluator_ran": evaluation["official_evaluator_ran"],
    }
