from mnemograph.llm.mock import MockLLMClient


def test_eval_cli_runs_cases_and_prints_summary(monkeypatch, tmp_path, capsys):
    from mnemograph.evals import cli as eval_cli

    case_path = tmp_path / "case.yaml"
    case_path.write_text(
        "\n".join(
            [
                "id: pricing_case",
                "steps:",
                "  - action: ingest_text",
                "    source: website",
                "    content: Pro costs $49/month.",
                "  - action: query",
                "    question: What does Pro cost?",
                "    expect_retrieval_mode: STRUCTURED_LOOKUP",
                "    expect_answer_contains: '$49'",
            ]
        )
    )

    monkeypatch.setattr(
        eval_cli,
        "build_default_client",
        lambda model, base_url: MockLLMClient(
            responses={
                "extract": {
                    "entities": [{"entity_id": "Plan:Pro", "entity_type": "plan", "canonical_name": "Pro", "namespace": "company"}],
                    "claims": [{
                        "claim_id": "claim-1",
                        "subject": "Plan:Pro",
                        "predicate": "price_usd_monthly",
                        "object": "49",
                        "object_type": "literal",
                        "claim_text": "Pro costs $49/month.",
                        "domain": "pricing",
                        "extraction_run_id": "run-1",
                    }],
                    "evidence_spans": [],
                    "open_questions": [],
                }
            }
        ),
    )

    exit_code = eval_cli.main(
        [
            str(case_path),
            "--base-dir",
            str(tmp_path / "runs"),
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "Local eval run (self-reported, reproducible)" in output
    assert "pricing_case" in output
    assert "passed=2" in output
    assert "assertions=2" in output
    assert "cost_usd=" in output
    assert "Summary" in output
    assert "cases=1 assertions=2 passed=2 failed=0" in output
