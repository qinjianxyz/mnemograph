import json

from mnemograph import cli


def test_demo_subcommand_invokes_demo_runner(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cli, "build_default_client", lambda model, base_url: object())
    monkeypatch.setattr(
        cli,
        "run_demo",
        lambda base_dir, llm_client, company_url, max_pages=3: {
            "company_url": company_url,
            "crawl": {"pages_succeeded": 1, "pages_failed": []},
            "stats": {"entity_count": 1, "claim_count": 1, "domain_breakdown": {"company": 1}, "sample_claims": []},
            "qa_results": [],
            "second_ingest_text": "noop",
            "changelog": "ADDED: noop",
            "stored_candidate": {"subject": "Plan:Enterprise", "predicate": "price_usd_monthly", "object": "500"},
            "recall_result": {"answer": "ok", "provenance": None},
            "memory_state": {"files": [], "tree": []},
        },
    )

    exit_code = cli.main(
        [
            "demo",
            "--base-dir",
            str(tmp_path),
            "--company-url",
            "https://acme.com",
        ]
    )

    assert exit_code == 0
    assert "https://acme.com" in capsys.readouterr().out
