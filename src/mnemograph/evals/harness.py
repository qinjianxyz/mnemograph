"""Golden-scenario evaluation harness."""

from datetime import UTC, datetime
from pathlib import Path
import shutil
import sqlite3
import time

import yaml

from mnemograph.chat.loop import ChatSession
from mnemograph.engine import Mnemograph
from mnemograph.llm.client import StructuredLLMClient


def load_eval_case(path: str | Path) -> dict:
    """Load one golden eval case from YAML."""
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _load_total_cost(db_path: Path) -> float:
    if not db_path.exists():
        return 0.0
    with sqlite3.connect(db_path) as conn:
        value = conn.execute(
            "SELECT COALESCE(SUM(cost_estimate_usd), 0.0) FROM extraction_runs"
        ).fetchone()[0]
    return float(value or 0.0)


def _score_query_step(step: dict, output: dict) -> list[dict]:
    assertions: list[dict] = []
    expected_mode = step.get("expect_retrieval_mode")
    if expected_mode is not None:
        assertions.append(
            {
                "field": "retrieval_mode",
                "expected": expected_mode,
                "actual": output.get("retrieval_mode"),
                "passed": output.get("retrieval_mode") == expected_mode,
            }
        )

    expected_answer_contains = step.get("expect_answer_contains")
    if expected_answer_contains is not None:
        answer = output.get("answer", "")
        assertions.append(
            {
                "field": "answer_contains",
                "expected": expected_answer_contains,
                "actual": answer,
                "passed": expected_answer_contains.lower() in answer.lower(),
            }
        )

    expected_provenance_contains = step.get("expect_provenance_contains")
    if expected_provenance_contains is not None:
        provenance = output.get("provenance") or ""
        assertions.append(
            {
                "field": "provenance_contains",
                "expected": expected_provenance_contains,
                "actual": provenance,
                "passed": expected_provenance_contains.lower() in provenance.lower(),
            }
        )

    expected_confidence_at_most = step.get("expect_confidence_at_most")
    if expected_confidence_at_most is not None:
        confidence = float(output.get("confidence", 0.0))
        assertions.append(
            {
                "field": "confidence_at_most",
                "expected": expected_confidence_at_most,
                "actual": confidence,
                "passed": confidence <= float(expected_confidence_at_most),
            }
        )
    return assertions


def _score_ingest_step(step: dict, output: dict) -> list[dict]:
    assertions: list[dict] = []

    expected_open_question_contains = step.get("expect_open_question_contains")
    if expected_open_question_contains is not None:
        rendered_questions = "\n".join(question.get("question", "") for question in output.get("open_questions", []))
        assertions.append(
            {
                "field": "open_question_contains",
                "expected": expected_open_question_contains,
                "actual": rendered_questions,
                "passed": expected_open_question_contains.lower() in rendered_questions.lower(),
            }
        )

    expected_open_question_count_at_least = step.get("expect_open_question_count_at_least")
    if expected_open_question_count_at_least is not None:
        question_count = len(output.get("open_questions", []))
        assertions.append(
            {
                "field": "open_question_count_at_least",
                "expected": expected_open_question_count_at_least,
                "actual": question_count,
                "passed": question_count >= int(expected_open_question_count_at_least),
            }
        )

    expected_open_question_domain = step.get("expect_open_question_domain")
    if expected_open_question_domain is not None:
        domains = sorted({question.get("domain", "unknown") for question in output.get("open_questions", [])})
        assertions.append(
            {
                "field": "open_question_domain",
                "expected": expected_open_question_domain,
                "actual": domains,
                "passed": expected_open_question_domain in domains,
            }
        )

    expected_claim_count_at_most = step.get("expect_claim_count_at_most")
    if expected_claim_count_at_most is not None:
        claim_count = int(output.get("claim_count", 0))
        assertions.append(
            {
                "field": "claim_count_at_most",
                "expected": expected_claim_count_at_most,
                "actual": claim_count,
                "passed": claim_count <= int(expected_claim_count_at_most),
            }
        )

    expected_changelog_contains = step.get("expect_changelog_contains")
    if expected_changelog_contains is not None:
        changelog = output.get("changelog", "")
        assertions.append(
            {
                "field": "changelog_contains",
                "expected": expected_changelog_contains,
                "actual": changelog,
                "passed": expected_changelog_contains.lower() in changelog.lower(),
            }
        )

    expected_conflict_type = step.get("expect_conflict_type")
    if expected_conflict_type is not None:
        conflict_types = output.get("conflict_types", [])
        assertions.append(
            {
                "field": "conflict_type",
                "expected": expected_conflict_type,
                "actual": conflict_types,
                "passed": expected_conflict_type in conflict_types,
            }
        )

    return assertions


def _load_conflict_types_for_run(db_path: Path, extraction_run_id: str) -> list[str]:
    if not db_path.exists():
        return []
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT conflicts.conflict_type
            FROM conflicts
            JOIN claims
              ON claims.claim_id = conflicts.right_claim_id
            WHERE claims.extraction_run_id = ?
            ORDER BY conflicts.conflict_type ASC
            """,
            (extraction_run_id,),
        ).fetchall()
    return [str(row[0]) for row in rows]


def evaluate_scenario(case: dict, base_dir: str | Path, llm_client: StructuredLLMClient) -> dict:
    """Run one scenario against the real engine and score step expectations."""
    base_path = Path(base_dir)
    if base_path.exists():
        shutil.rmtree(base_path)
    engine = Mnemograph(base_path, llm_client=llm_client)
    chat = ChatSession(engine)
    started = time.perf_counter()
    outputs: list[dict] = []
    assertions: list[dict] = []

    for index, step in enumerate(case.get("steps", []), start=1):
        action = step["action"]
        if action == "ingest_text":
            result = engine.ingest_text(
                step["content"],
                source=step.get("source", "website"),
                trust_tier=step.get("trust_tier"),
            )
            output = {
                "step": index,
                "action": action,
                "source_id": result.source_id,
                "claim_count": len(result.claim_ids),
                "open_questions": result.open_questions,
                "changelog": engine.render_changelog(result.extraction_run_id),
                "conflict_types": _load_conflict_types_for_run(engine.db_path, result.extraction_run_id),
            }
            outputs.append(output)
            assertions.extend(_score_ingest_step(step, output))
        elif action == "ingest_url":
            result = engine.ingest(
                step["locator"],
                step["content"],
                source_type="url",
                trust_tier=step.get("trust_tier", "primary"),
            )
            output = {
                "step": index,
                "action": action,
                "source_id": result.source_id,
                "locator": step["locator"],
                "claim_count": len(result.claim_ids),
                "open_questions": result.open_questions,
                "changelog": engine.render_changelog(result.extraction_run_id),
                "conflict_types": _load_conflict_types_for_run(engine.db_path, result.extraction_run_id),
            }
            outputs.append(output)
            assertions.extend(_score_ingest_step(step, output))
        elif action == "ingest_candidates":
            result = engine.ingest_candidates(
                step["claims"],
                raw_text=step.get("raw_text", ""),
                source=step.get("source", "user"),
                trust_tier=step.get("trust_tier"),
                store_text=step.get("store_text"),
            )
            output = {
                "step": index,
                "action": action,
                "source_id": result.source_id,
                "claim_count": len(result.claim_ids),
                "open_questions": result.open_questions,
                "changelog": engine.render_changelog(result.extraction_run_id),
                "conflict_types": _load_conflict_types_for_run(engine.db_path, result.extraction_run_id),
            }
            outputs.append(output)
            assertions.extend(_score_ingest_step(step, output))
        elif action == "query":
            result = engine.query(step["question"])
            output = {
                "step": index,
                "action": action,
                "question": step["question"],
                "answer": result.answer,
                "retrieval_mode": result.retrieval.mode,
                "claim_count": len(result.claims),
                "confidence": result.confidence,
                "provenance": result.provenance,
            }
            outputs.append(output)
            assertions.extend(_score_query_step(step, output))
        elif action == "chat_turn":
            result = chat.handle_turn(step["content"])
            outputs.append(
                {
                    "step": index,
                    "action": action,
                    "content": step["content"],
                    "answer": result.answer,
                    "retrieval_mode": result.retrieval.mode,
                }
            )
        else:
            raise ValueError(f"unsupported eval action: {action}")

    latency_ms = (time.perf_counter() - started) * 1000
    passed = sum(1 for assertion in assertions if assertion["passed"])
    failed = sum(1 for assertion in assertions if not assertion["passed"])

    return {
        "case_id": case["id"],
        "evaluated_at": datetime.now(UTC).isoformat(),
        "outputs": outputs,
        "assertions": assertions,
        "score": {
            "passed": passed,
            "failed": failed,
            "pass_rate": 1.0 if not assertions else passed / len(assertions),
        },
        "metrics": {
            "latency_ms": latency_ms,
            "cost_usd": _load_total_cost(engine.db_path),
        },
    }


def expand_case_paths(patterns: list[str]) -> list[Path]:
    """Expand files, directories, and glob patterns into YAML case paths."""
    paths: list[Path] = []
    for pattern in patterns:
        candidate = Path(pattern)
        if candidate.is_dir():
            paths.extend(sorted(candidate.glob("*.yaml")))
            continue
        if any(char in pattern for char in "*?[]"):
            paths.extend(sorted(Path().glob(pattern)))
            continue
        paths.append(candidate)

    deduped: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        deduped.append(resolved)
    return deduped
