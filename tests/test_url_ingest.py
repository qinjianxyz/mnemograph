import sqlite3

from mnemograph.engine import Mnemograph
from mnemograph.llm.mock import MockLLMClient


def test_ingest_url_fetches_and_cleans_seed_and_priority_subpages(tmp_path):
    visited: list[str] = []
    pages = {
        "https://stripe.com": """
            <html><body>
            <nav>Home Pricing Docs</nav>
            <main>
              <h1>Stripe</h1>
              <p>Stripe provides payments infrastructure for the internet.</p>
              <a href="/pricing">Pricing</a>
              <a href="/about">About</a>
              <a href="https://example.com/offsite">Offsite</a>
            </main>
            <footer>Privacy Terms Cookies</footer>
            </body></html>
        """,
        "https://stripe.com/pricing": """
            <html><body>
            <main>
              <h1>Pricing</h1>
              <p>Standard pricing is 2.9% + 30c per successful card charge.</p>
            </main>
            </body></html>
        """,
        "https://stripe.com/about": """
            <html><body>
            <main>
              <h1>About Stripe</h1>
              <p>Stripe builds programmable financial infrastructure.</p>
            </main>
            </body></html>
        """,
    }

    def fetcher(url: str) -> str:
        visited.append(url)
        return pages[url]

    engine = Mnemograph(
        tmp_path,
        llm_client=MockLLMClient(
        responses={
            "extract": [{
                    "entities": [
                        {
                            "entity_id": "Company:Stripe",
                            "entity_type": "company",
                            "canonical_name": "Stripe",
                            "namespace": "company",
                        }
                    ],
                    "claims": [
                        {
                            "claim_id": "claim-1",
                            "subject": "Company:Stripe",
                            "predicate": "offers_payments_infrastructure",
                            "object": "payments infrastructure for the internet",
                            "object_type": "literal",
                            "claim_text": "Stripe provides payments infrastructure for the internet.",
                            "domain": "company",
                            "extraction_run_id": "run-1",
                        }
                    ],
                    "evidence_spans": [],
                    "open_questions": [],
                }] * 3
            }
        ),
    )

    result = engine.ingest_url("https://stripe.com", fetcher=fetcher, max_pages=3)

    assert result.claim_ids
    assert visited == [
        "https://stripe.com",
        "https://stripe.com/pricing",
        "https://stripe.com/about",
    ]

    with sqlite3.connect(engine.db_path) as conn:
        stored_text = " ".join(row[0] for row in conn.execute("SELECT text FROM source_chunks"))

    lowered = stored_text.lower()
    assert "payments infrastructure for the internet" in lowered
    assert "standard pricing is 2.9% + 30c" in lowered
    assert "programmable financial infrastructure" in lowered
    assert "privacy terms cookies" not in lowered
    assert "offsite" not in lowered

    with sqlite3.connect(engine.db_path) as conn:
        source_rows = conn.execute(
            "SELECT locator, parent_source_id FROM sources ORDER BY locator ASC"
        ).fetchall()

    assert len(source_rows) == 3
    parent_ids = {parent_source_id for _, parent_source_id in source_rows if parent_source_id is not None}
    assert len(parent_ids) == 1
