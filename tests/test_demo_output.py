from mnemograph.demo import default_questions_for_company, render_demo_report, write_demo_report


def test_default_demo_questions_follow_company_name():
    questions = default_questions_for_company("Railway")

    assert questions[0] == "What products does Railway offer?"
    assert questions[1] == "Who leads Railway?"
    assert questions[2] == "What does Pro cost?"


def test_render_demo_report_produces_narrated_walkthrough():
    report = render_demo_report(
        {
            "baseline": {
                "stats": {
                    "claim_count": 4,
                    "domain_breakdown": {"company": 1, "pricing": 1, "product": 1, "team": 1},
                    "sample_claims": [
                        {"confidence": 0.82, "claim_text": "Stripe Pro plan costs $20/month.", "domain": "pricing"},
                        {"confidence": 0.78, "claim_text": "Stripe offers Payments.", "domain": "product"},
                    ],
                    "open_question_count": 1,
                }
            },
            "crawl": {"pages_attempted": 3, "pages_succeeded": 3, "pages_failed": []},
            "first_ingest": {"open_questions": []},
            "stats": {
                "entity_count": 12,
                "claim_count": 28,
                "domain_breakdown": {"product": 10, "pricing": 5, "team": 4},
                "sample_claims": [
                    {"confidence": 0.9, "claim_text": "Stripe offers Stripe Payments.", "domain": "product"},
                    {"confidence": 0.85, "claim_text": "Pro costs $25/month.", "domain": "pricing"},
                ],
            },
            "qa_results": [
                {
                    "question": "What products does Stripe offer?",
                    "retrieval_mode": "SEMANTIC_SEARCH",
                    "claim_count": 8,
                    "answer": "Stripe offers Payments and Billing. [1][2]",
                }
            ],
            "second_ingest_text": "Pro costs $59/month.",
            "changelog": "SUPERSEDED: Pro costs $25/month. -> Pro costs $59/month.",
            "stored_candidate": {"subject": "Plan:Enterprise", "predicate": "price_usd_monthly", "object": "500"},
            "recall_result": {
                "answer": "Enterprise plan costs $500/month [1]",
                "provenance": 'Claim: Enterprise plan costs $500/month. [confidence: 0.91, domain: pricing]\nEvidence: "enterprise plan is $500/mo"\nSource: user:conversation (ingested 2026-04-10)',
            },
            "memory_state": {
                "files": [
                    "memory/working/active_context.json",
                    "memory/working/session_history.json",
                    "memory/knowledge/pricing.json",
                    "memory/sources/source_001.json",
                ],
                "tree": ["memory/sources"],
                "knowledge_summaries": ["memory/knowledge/pricing.json (5 claims)"],
            },
        }
    )

    assert "=== Phase 1: Ingesting" in report
    assert "=== Phase 2: Asking questions ===" in report
    assert "=== Phase 3: Contradictory source ===" in report
    assert "=== Phase 4: Conversation ===" in report
    assert "=== Phase 5: Final memory state ===" in report
    assert "=== Phase 0: Synthetic baseline ===" in report
    assert "Retrieval: SEMANTIC_SEARCH" in report
    assert "Confidence:" in report
    assert "SUPERSEDED:" in report
    assert "Source: user:conversation (ingested 2026-04-10)" in report
    assert report.count("memory/knowledge/pricing.json") == 1


def test_write_demo_report_persists_report_in_base_dir(tmp_path):
    report_path = write_demo_report(tmp_path, "demo report")

    assert report_path == tmp_path / "demo-output.txt"
    assert report_path.read_text() == "demo report\n"
