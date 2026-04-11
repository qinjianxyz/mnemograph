"""Demo helpers for the public Mnemograph walkthrough."""

from pathlib import Path
import shutil
import sqlite3
from urllib.parse import urlsplit

from mnemograph.chat.loop import ChatSession
from mnemograph.engine import Mnemograph
from mnemograph.llm.client import OpenAICompatibleLLMClient, StructuredLLMClient


BASELINE_SEEDS = {
    "vercel": (
        "Vercel Pro plan costs $20/month. "
        "Vercel offers Functions, Edge Config, and AI SDK. "
        "Guillermo Rauch is the CEO of Vercel. "
        "Vercel is headquartered in San Francisco."
    ),
    "stripe": (
        "Stripe Pro plan costs $20/month. "
        "Stripe offers Payments, Billing, and Connect. "
        "Patrick Collison is the CEO of Stripe. "
        "Stripe is headquartered in San Francisco."
    ),
}


def default_questions_for_company(company_name: str) -> tuple[str, str, str]:
    """Return the default narrated demo questions for a company."""
    return (
        f"What products does {company_name} offer?",
        f"Who leads {company_name}?",
        "What does Pro cost?",
    )


def _company_name_from_url(company_url: str) -> str:
    host = urlsplit(company_url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    label = host.split(".", 1)[0]
    return label.replace("-", " ").title() or "the company"


def _baseline_seed_text(company_url: str, company_name: str) -> str:
    host = urlsplit(company_url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    label = host.split(".", 1)[0]
    if label in BASELINE_SEEDS:
        return BASELINE_SEEDS[label]
    return (
        f"{company_name} Pro plan costs $20/month. "
        f"{company_name} offers Core Platform, Enterprise Support, and Public API access. "
        f"{company_name} is headquartered in San Francisco."
    )


def _baseline_seed_claims(company_name: str, company_url: str) -> list[dict]:
    host = urlsplit(company_url).netloc.lower()
    company_entity = f"Company:{company_name.replace(' ', '_')}"
    if "vercel.com" in host:
        return [
            {
                "subject": "Plan:Pro",
                "predicate": "price_usd_monthly",
                "object": "20",
                "object_type": "literal",
                "claim_text": "Vercel Pro plan costs $20/month.",
                "domain": "pricing",
            },
            {
                "subject": company_entity,
                "predicate": "has_product",
                "object": "Product:Functions",
                "object_type": "entity",
                "claim_text": "Vercel offers Functions.",
                "domain": "product",
            },
            {
                "subject": company_entity,
                "predicate": "has_ceo",
                "object": "Person:Guillermo_Rauch",
                "object_type": "entity",
                "claim_text": "Guillermo Rauch is the CEO of Vercel.",
                "domain": "team",
            },
            {
                "subject": company_entity,
                "predicate": "headquartered_in",
                "object": "San Francisco",
                "object_type": "literal",
                "claim_text": "Vercel is headquartered in San Francisco.",
                "domain": "company",
            },
        ]
    if "stripe.com" in host:
        return [
            {
                "subject": "Plan:Pro",
                "predicate": "price_usd_monthly",
                "object": "20",
                "object_type": "literal",
                "claim_text": "Stripe Pro plan costs $20/month.",
                "domain": "pricing",
            },
            {
                "subject": company_entity,
                "predicate": "has_product",
                "object": "Product:Billing",
                "object_type": "entity",
                "claim_text": "Stripe offers Billing.",
                "domain": "product",
            },
            {
                "subject": company_entity,
                "predicate": "has_ceo",
                "object": "Person:Patrick_Collison",
                "object_type": "entity",
                "claim_text": "Patrick Collison is the CEO of Stripe.",
                "domain": "team",
            },
            {
                "subject": company_entity,
                "predicate": "headquartered_in",
                "object": "San Francisco",
                "object_type": "literal",
                "claim_text": "Stripe is headquartered in San Francisco.",
                "domain": "company",
            },
        ]
    return [
        {
            "subject": "Plan:Pro",
            "predicate": "price_usd_monthly",
            "object": "20",
            "object_type": "literal",
            "claim_text": f"{company_name} Pro plan costs $20/month.",
            "domain": "pricing",
        },
        {
            "subject": company_entity,
            "predicate": "has_product",
            "object": "Product:Core_Platform",
            "object_type": "entity",
            "claim_text": f"{company_name} offers Core Platform.",
            "domain": "product",
        },
        {
            "subject": company_entity,
            "predicate": "headquartered_in",
            "object": "San Francisco",
            "object_type": "literal",
            "claim_text": f"{company_name} is headquartered in San Francisco.",
            "domain": "company",
        },
    ]


def _collect_stats(db_path: Path) -> dict:
    with sqlite3.connect(db_path) as conn:
        entity_count = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
        claim_count = conn.execute("SELECT COUNT(*) FROM claims").fetchone()[0]
        domain_rows = conn.execute(
            "SELECT domain, COUNT(*) FROM claims GROUP BY domain ORDER BY domain ASC"
        ).fetchall()
        sample_claims = conn.execute(
            """
            SELECT claim_text, domain, confidence
            FROM claims
            ORDER BY confidence DESC, claim_id ASC
            LIMIT 5
            """
        ).fetchall()

    return {
        "entity_count": entity_count,
        "claim_count": claim_count,
        "domain_breakdown": {domain: count for domain, count in domain_rows},
        "sample_claims": [
            {"claim_text": claim_text, "domain": domain, "confidence": confidence}
            for claim_text, domain, confidence in sample_claims
        ],
    }


def _collect_run_stats(db_path: Path, extraction_run_id: str) -> dict:
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT claim_text, domain, confidence
            FROM claims
            WHERE extraction_run_id = ?
            ORDER BY confidence DESC, claim_id ASC
            """,
            (extraction_run_id,),
        ).fetchall()
    sample_claims = [
        {"claim_text": claim_text, "domain": domain, "confidence": confidence}
        for claim_text, domain, confidence in rows[:5]
    ]
    domain_breakdown: dict[str, int] = {}
    for _, domain, _ in rows:
        domain_breakdown[domain] = domain_breakdown.get(domain, 0) + 1
    return {
        "claim_count": len(rows),
        "domain_breakdown": domain_breakdown,
        "sample_claims": sample_claims,
        "open_question_count": 0,
    }


def _snapshot_memory_state(base_dir: Path) -> dict:
    memory_root = base_dir / "memory"
    files = sorted(
        str(path.relative_to(base_dir))
        for path in memory_root.rglob("*")
        if path.is_file()
    )
    tree = sorted(
        str(path.relative_to(base_dir))
        for path in memory_root.rglob("*")
    )
    return {"files": files, "tree": tree, "root": str(memory_root.relative_to(base_dir))}


def _knowledge_file_summaries(base_dir: Path, domain_breakdown: dict[str, int]) -> list[str]:
    lines: list[str] = []
    for domain, count in sorted(domain_breakdown.items()):
        candidate = base_dir / "memory" / "knowledge" / f"{domain}.json"
        if candidate.exists():
            lines.append(f"memory/knowledge/{domain}.json ({count} claims)")
    return lines


def run_demo(
    base_dir: str | Path,
    llm_client: StructuredLLMClient,
    company_url: str = "https://stripe.com",
    fetcher=None,
    max_pages: int = 3,
) -> dict:
    """Run the scripted Hobbes-style demo and return structured results."""
    base_path = Path(base_dir)
    if base_path.exists():
        shutil.rmtree(base_path)
    engine = Mnemograph(base_path, llm_client=llm_client)
    company_name = _company_name_from_url(company_url)
    baseline_text = _baseline_seed_text(company_url, company_name)

    baseline_ingest = engine.ingest_candidates(
        _baseline_seed_claims(company_name, company_url),
        raw_text=baseline_text,
        source="baseline",
    )
    baseline_stats = _collect_run_stats(engine.db_path, baseline_ingest.extraction_run_id)
    baseline_stats["open_question_count"] = len(baseline_ingest.open_questions)
    first_ingest = engine.ingest_url(company_url, fetcher=fetcher, max_pages=max_pages)
    stats = _collect_stats(engine.db_path)

    qa_results = []
    for question in default_questions_for_company(company_name):
        result = engine.query(question)
        qa_results.append(
            {
                "question": question,
                "retrieval_mode": result.retrieval.mode,
                "claim_count": len(result.claims),
                "answer": result.answer,
                "confidence": result.confidence,
                "provenance": result.provenance,
            }
        )

    second_ingest_text = f"{company_name} Pro plan costs $59/month."
    second_ingest = engine.ingest_candidates(
        [
            {
                "subject": "Plan:Pro",
                "predicate": "price_usd_monthly",
                "object": "59",
                "object_type": "literal",
                "claim_text": second_ingest_text,
                "domain": "pricing",
            }
        ],
        raw_text=second_ingest_text,
        source="user",
    )
    changelog = engine.render_changelog(second_ingest.extraction_run_id)

    session = ChatSession(engine, history_limit=6)
    correction_text = "Actually their enterprise plan is $500/mo."
    session.handle_turn(correction_text)
    recall_result = session.handle_turn("What does Enterprise cost?")
    provenance_result = engine.query("How do you know this?")

    return {
        "company_url": company_url,
        "crawl": engine.last_crawl_report,
        "baseline": {
            "text": baseline_text,
            "source_id": baseline_ingest.source_id,
            "extraction_run_id": baseline_ingest.extraction_run_id,
            "claim_ids": baseline_ingest.claim_ids,
            "stats": baseline_stats,
        },
        "first_ingest": {
            "source_id": first_ingest.source_id,
            "extraction_run_id": first_ingest.extraction_run_id,
            "claim_ids": first_ingest.claim_ids,
            "open_questions": first_ingest.open_questions,
        },
        "stats": stats,
        "qa_results": qa_results,
        "second_ingest_text": second_ingest_text,
        "second_ingest": {
            "source_id": second_ingest.source_id,
            "extraction_run_id": second_ingest.extraction_run_id,
            "claim_ids": second_ingest.claim_ids,
        },
        "changelog": changelog,
        "stored_candidate": {
            "subject": "Plan:Enterprise",
            "predicate": "price_usd_monthly",
            "object": "500",
        },
        "correction_text": correction_text,
        "recall_result": {
            "answer": recall_result.answer,
            "confidence": recall_result.confidence,
            "retrieval_mode": recall_result.retrieval.mode,
            "provenance": recall_result.provenance,
        },
        "provenance_result": {
            "answer": provenance_result.answer,
            "retrieval_mode": provenance_result.retrieval.mode,
            "provenance": provenance_result.provenance,
        },
        "memory_state": {
            **_snapshot_memory_state(base_path),
            "knowledge_summaries": _knowledge_file_summaries(base_path, stats["domain_breakdown"]),
        },
    }


def render_demo_report(result: dict) -> str:
    """Render the structured demo result as a narrated walkthrough."""
    company_url = result.get("company_url", "company site")
    baseline = result.get(
        "baseline",
        {
            "stats": {
                "claim_count": 0,
                "domain_breakdown": {},
                "sample_claims": [],
                "open_question_count": 0,
            }
        },
    )
    first_ingest = result.get("first_ingest", {"open_questions": []})
    lines = [
        "========================================",
        " Mnemograph Demo - Company Intelligence",
        "========================================",
        "",
        "=== Phase 0: Synthetic baseline ===",
        f"Seeded {baseline['stats']['claim_count']} structured claims before crawling.",
        "Baseline domains: "
        + ", ".join(
            f"{domain}={count}"
            for domain, count in baseline["stats"]["domain_breakdown"].items()
        ),
        "Baseline sample claims:",
    ]
    for sample in baseline["stats"]["sample_claims"]:
        lines.append(f"  [{sample['confidence']:.2f}] {sample['claim_text']} ({sample['domain']})")
    if baseline["stats"].get("open_question_count"):
        lines.append(
            f"Filtered into open questions: {baseline['stats']['open_question_count']}"
        )

    lines.extend(
        [
            "",
        f"=== Phase 1: Ingesting {company_url} ===",
        (
            f"Crawled {result['crawl']['pages_succeeded']} pages"
            f" ({len(result['crawl']['pages_failed'])} failed)."
        ),
        (
            f"Extracted {result['stats']['entity_count']} entities, "
            f"{result['stats']['claim_count']} claims across {len(result['stats']['domain_breakdown'])} domains"
        ),
        "Domain breakdown: "
        + ", ".join(f"{domain}={count}" for domain, count in result["stats"]["domain_breakdown"].items()),
        "Sample claims:",
        ]
    )
    for sample in result["stats"]["sample_claims"]:
        lines.append(f"  [{sample['confidence']:.2f}] {sample['claim_text']} ({sample['domain']})")
    if first_ingest.get("open_questions"):
        lines.append(f"Filtered into open questions: {len(first_ingest['open_questions'])}")

    lines.append("")
    lines.append("=== Phase 2: Asking questions ===")
    for qa in result["qa_results"]:
        lines.append(f"Q: {qa['question']}")
        lines.append(f"Retrieval: {qa['retrieval_mode']} -> {qa['claim_count']} claims")
        lines.append(f"A: {qa['answer']}")
        lines.append(f"Confidence: {qa.get('confidence', 0.0):.2f}")
        if qa.get("provenance"):
            lines.append(f"Provenance: {qa['provenance']}")
        lines.append("")

    lines.extend(
        [
            "=== Phase 3: Contradictory source ===",
            f'Ingesting: "{result["second_ingest_text"]}"',
            "Changelog:",
            *[f"  {line}" for line in result["changelog"].splitlines()],
            "",
            "=== Phase 4: Conversation ===",
            f'User: {result.get("correction_text", "Actually their enterprise plan is $500/mo.")}',
            (
                "-> Stored as: "
                f'{result["stored_candidate"]["subject"]} '
                f'{result["stored_candidate"]["predicate"]} '
                f'{result["stored_candidate"]["object"]}'
            ),
            "User: What does Enterprise cost?",
            f'A: {result["recall_result"]["answer"]}',
            f'Confidence: {result["recall_result"].get("confidence", 0.0):.2f}',
        ]
    )
    if result["recall_result"].get("provenance"):
        lines.append(f'Provenance: {result["recall_result"]["provenance"]}')

    knowledge_summary_paths = {
        summary.split(" (", 1)[0] for summary in result["memory_state"].get("knowledge_summaries", [])
    }
    lines.extend(["", "=== Phase 5: Final memory state ==="])
    lines.extend(result["memory_state"].get("knowledge_summaries", []))
    lines.extend(
        [
            *[
                f"{path}"
                for path in result["memory_state"]["files"]
                if path not in knowledge_summary_paths
            ],
            "",
            "========================================",
            f" Demo complete. Inspect {result['memory_state'].get('root', 'memory/')}",
            "========================================",
        ]
    )
    return "\n".join(lines)


def write_demo_report(base_dir: str | Path, report: str) -> Path:
    """Persist the narrated demo report to the demo base directory."""
    base_path = Path(base_dir)
    base_path.mkdir(parents=True, exist_ok=True)
    report_path = base_path / "demo-output.txt"
    report_path.write_text(report.rstrip() + "\n")
    return report_path


def build_default_client(
    model: str = "qwen3.5:latest",
    base_url: str = "http://localhost:11434/v1",
) -> OpenAICompatibleLLMClient:
    """Create the default live client for the public demo script."""
    return OpenAICompatibleLLMClient(model=model, api_base=base_url)
