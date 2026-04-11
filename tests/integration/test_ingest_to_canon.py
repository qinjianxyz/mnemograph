import sqlite3

from mnemograph.ingest.pipeline import ingest_text_source
from mnemograph.llm.mock import MockLLMClient


def test_ingest_to_canon_records_source_chunks_run_and_claim(tmp_path):
    db_path = tmp_path / "memory.db"
    client = MockLLMClient(
        responses={
            "extract": {
                "entities": [
                    {
                        "entity_id": "Company:Acme",
                        "entity_type": "company",
                        "canonical_name": "Acme",
                        "namespace": "company",
                    },
                    {
                        "entity_id": "Plan:Pro",
                        "entity_type": "plan",
                        "canonical_name": "Pro",
                        "namespace": "company",
                    },
                ],
                "claims": [
                    {
                        "claim_id": "claim-1",
                        "subject": "Company:Acme",
                        "predicate": "has_pricing_plan",
                        "object": "Plan:Pro",
                        "object_type": "entity",
                        "claim_text": "Acme offers a Pro plan.",
                        "domain": "pricing",
                        "extraction_run_id": "run-local",
                    }
                ],
                "evidence_spans": [
                    {
                        "claim_id": "claim-1",
                        "quote_text": "Acme offers a Pro plan.",
                        "source_id": "source-local",
                        "chunk_id": "chunk-local",
                        "extraction_run_id": "run-local",
                    }
                ],
            }
        }
    )

    result = ingest_text_source(
        db_path=db_path,
        locator="https://acme.com/pricing",
        content="Acme offers a Pro plan.",
        llm_client=client,
        source_type="url",
    )

    assert result.source_id
    assert result.extraction_run_id
    assert len(result.claim_ids) == 1

    conn = sqlite3.connect(db_path)
    source_count = conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
    chunk_count = conn.execute("SELECT COUNT(*) FROM source_chunks").fetchone()[0]
    run_count = conn.execute("SELECT COUNT(*) FROM extraction_runs").fetchone()[0]
    claim_count = conn.execute("SELECT COUNT(*) FROM claims").fetchone()[0]

    assert source_count == 1
    assert chunk_count == 1
    assert run_count == 1
    assert claim_count == 1


def test_ingest_duplicate_claim_reuses_existing_claim_for_evidence(tmp_path):
    db_path = tmp_path / "memory.db"
    client = MockLLMClient(
        responses={
            "extract": [
                {
                    "entities": [
                        {
                            "entity_id": "Company:Acme",
                            "entity_type": "company",
                            "canonical_name": "Acme",
                            "namespace": "company",
                        }
                    ],
                    "claims": [
                        {
                            "claim_id": "claim-1",
                            "subject": "Company:Acme",
                            "predicate": "company_summary",
                            "object": "payments company",
                            "object_type": "literal",
                            "claim_text": "Acme is a payments company.",
                            "domain": "company",
                            "extraction_run_id": "run-1",
                        }
                    ],
                    "evidence_spans": [
                        {
                            "claim_id": "claim-1",
                            "quote_text": "Acme is a payments company.",
                            "source_id": "source-1",
                            "chunk_id": "chunk-1",
                            "extraction_run_id": "run-1",
                        }
                    ],
                },
                {
                    "entities": [
                        {
                            "entity_id": "Company:Acme",
                            "entity_type": "company",
                            "canonical_name": "Acme",
                            "namespace": "company",
                        }
                    ],
                    "claims": [
                        {
                            "claim_id": "claim-2",
                            "subject": "Company:Acme",
                            "predicate": "company_summary",
                            "object": "payments company",
                            "object_type": "literal",
                            "claim_text": "Acme is a payments company.",
                            "domain": "company",
                            "extraction_run_id": "run-2",
                        }
                    ],
                    "evidence_spans": [
                        {
                            "claim_id": "claim-2",
                            "quote_text": "Acme is a payments company.",
                            "source_id": "source-2",
                            "chunk_id": "chunk-2",
                            "extraction_run_id": "run-2",
                        }
                    ],
                },
            ]
        }
    )

    first = ingest_text_source(
        db_path=db_path,
        locator="https://acme.com",
        content="Acme is a payments company.",
        llm_client=client,
        source_type="url",
    )
    second = ingest_text_source(
        db_path=db_path,
        locator="https://acme.com/about",
        content="Acme is a payments company.",
        llm_client=client,
        source_type="url",
    )

    conn = sqlite3.connect(db_path)
    claim_count = conn.execute("SELECT COUNT(*) FROM claims").fetchone()[0]
    evidence_count = conn.execute("SELECT COUNT(*) FROM evidence_spans").fetchone()[0]
    support_count = conn.execute("SELECT support_count FROM claims WHERE claim_id = ?", (first.claim_ids[0],)).fetchone()[0]
    distinct_claim_ids = [row[0] for row in conn.execute("SELECT DISTINCT claim_id FROM evidence_spans ORDER BY claim_id").fetchall()]

    assert second.source_id != first.source_id
    assert claim_count == 1
    assert evidence_count == 2
    assert support_count == 2
    assert distinct_claim_ids == [first.claim_ids[0]]


def test_ingest_filters_marketing_copy_and_varies_confidence_by_signal(tmp_path):
    db_path = tmp_path / "memory.db"
    client = MockLLMClient(
        responses={
            "extract": [
                {
                    "entities": [
                        {
                            "entity_id": "Company:Vercel",
                            "entity_type": "company",
                            "canonical_name": "Vercel",
                            "namespace": "company",
                        },
                        {
                            "entity_id": "Product:Functions",
                            "entity_type": "product",
                            "canonical_name": "Functions",
                            "namespace": "company",
                        },
                    ],
                    "claims": [
                        {
                            "claim_id": "claim-1",
                            "subject": "Company:Vercel",
                            "predicate": "offers",
                            "object": "Deploy AI apps in seconds with infrastructure that scales automatically for every team.",
                            "object_type": "literal",
                            "claim_text": "Deploy AI apps in seconds with infrastructure that scales automatically for every team.",
                            "domain": "company",
                            "extraction_run_id": "run-1",
                        },
                        {
                            "claim_id": "claim-2",
                            "subject": "Company:Vercel",
                            "predicate": "has_product",
                            "object": "Product:Functions",
                            "object_type": "entity",
                            "claim_text": "Vercel offers Functions.",
                            "domain": "product",
                            "extraction_run_id": "run-1",
                        },
                        {
                            "claim_id": "claim-3",
                            "subject": "Company:Vercel",
                            "predicate": "price_usd_monthly",
                            "object": "unknown",
                            "object_type": "literal",
                            "claim_text": "Pricing details are not specified in the text.",
                            "domain": "pricing",
                            "extraction_run_id": "run-1",
                        },
                    ],
                    "evidence_spans": [],
                    "open_questions": [],
                },
                {
                    "entities": [
                        {
                            "entity_id": "Plan:Enterprise",
                            "entity_type": "plan",
                            "canonical_name": "Enterprise",
                            "namespace": "company",
                        }
                    ],
                    "claims": [
                        {
                            "claim_id": "claim-3",
                            "subject": "Plan:Enterprise",
                            "predicate": "price_usd_monthly",
                            "object": "500",
                            "object_type": "literal",
                            "claim_text": "Enterprise plan costs $500/month.",
                            "domain": "pricing",
                            "extraction_run_id": "run-2",
                        }
                    ],
                    "evidence_spans": [],
                    "open_questions": [],
                },
            ]
        }
    )

    ingest_text_source(
        db_path=db_path,
        locator="https://vercel.com",
        content="Deploy AI apps in seconds. Vercel offers Functions.",
        llm_client=client,
        source_type="url",
        trust_tier="primary",
    )
    ingest_text_source(
        db_path=db_path,
        locator="user:conversation",
        content="Enterprise plan costs $500/month.",
        llm_client=client,
        source_type="text",
        trust_tier="user",
    )

    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT claim_text, confidence FROM claims WHERE status = 'active' ORDER BY claim_text ASC"
    ).fetchall()

    assert [row[0] for row in rows] == [
        "Enterprise plan costs $500/month.",
        "Vercel offers Functions.",
    ]
    assert rows[0][1] > rows[1][1]
