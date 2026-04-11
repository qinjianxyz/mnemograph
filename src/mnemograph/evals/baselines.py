"""Simple baseline runners for benchmark comparisons."""

from collections import Counter
from datetime import UTC, datetime
import math
import time

from mnemograph.evals.harness import evaluate_scenario
from mnemograph.llm.client import StructuredLLMClient


def _tokenize(text: str) -> list[str]:
    return [token for token in "".join(ch.lower() if ch.isalnum() else " " for ch in text).split() if len(token) > 2]


def run_naive_rag_baseline(case: dict) -> dict:
    """Run a bag-of-text baseline without structured memory."""
    started = time.perf_counter()
    corpus: list[str] = []
    outputs: list[dict] = []

    for index, step in enumerate(case.get("steps", []), start=1):
        action = step["action"]
        if action == "ingest_text":
            corpus.append(step["content"])
            continue
        if action != "query":
            continue

        query_tokens = _tokenize(step["question"])
        document_tokens = [Counter(_tokenize(document)) for document in corpus]
        scores: list[tuple[float, str]] = []
        for document, counts in zip(corpus, document_tokens, strict=False):
            score = 0.0
            for token in query_tokens:
                if counts[token]:
                    score += 1.0 + math.log1p(counts[token])
            if score > 0:
                scores.append((score, document))
        best_document = max(scores, default=(0.0, "I don't know based on the current memory."))[1]
        outputs.append(
            {
                "step": index,
                "question": step["question"],
                "answer": best_document,
                "retrieval_mode": "SEMANTIC_ONLY",
            }
        )

    return {
        "baseline": "naive_rag",
        "evaluated_at": datetime.now(UTC).isoformat(),
        "outputs": outputs,
        "metrics": {
            "latency_ms": (time.perf_counter() - started) * 1000,
            "cost_usd": 0.0,
        },
    }


def run_structured_memory_baseline(
    case: dict,
    base_dir,
    llm_client: StructuredLLMClient,
) -> dict:
    """Run the current structured engine as a benchmark baseline."""
    result = evaluate_scenario(case, base_dir=base_dir, llm_client=llm_client)
    return {
        "baseline": "structured_memory",
        "evaluated_at": result["evaluated_at"],
        "outputs": [output for output in result["outputs"] if output["action"] == "query"],
        "metrics": result["metrics"],
        "score": result["score"],
    }
