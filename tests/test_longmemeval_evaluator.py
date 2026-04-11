from pathlib import Path


def test_build_longmemeval_evaluator_command_matches_official_shape(tmp_path):
    from mnemograph.benchmarks.longmemeval import build_evaluator_command

    command = build_evaluator_command(
        evaluator_script_path=tmp_path / "evaluate_qa.py",
        predictions_path=tmp_path / "predictions.jsonl",
        dataset_path=tmp_path / "dataset.json",
        judge_model="gpt-4o",
    )

    assert command == [
        "python3",
        str(tmp_path / "evaluate_qa.py"),
        "gpt-4o",
        str(tmp_path / "predictions.jsonl"),
        str(tmp_path / "dataset.json"),
    ]


def test_evaluate_longmemeval_predictions_falls_back_to_proxy_metrics_when_evaluator_missing(tmp_path):
    from mnemograph.benchmarks.longmemeval import LongMemEvalCase, evaluate_predictions

    cases = [
        LongMemEvalCase(
            question_id="q-001",
            question_type="knowledge-update",
            question="What does Pro cost now?",
            answer="$59/month",
            question_date="2026-04-10",
            haystack_session_ids=[],
            haystack_dates=[],
            haystack_sessions=[],
            answer_session_ids=[],
        )
    ]
    predictions_path = tmp_path / "predictions.jsonl"
    predictions_path.write_text('{"question_id": "q-001", "hypothesis": "$59/month"}\n', encoding="utf-8")

    metrics = evaluate_predictions(
        cases=cases,
        predictions_path=predictions_path,
        dataset_path=tmp_path / "dataset.json",
        evaluator_script_path=None,
    )

    assert metrics["status"] == "proxy_only"
    assert metrics["proxy_exact_match"] == 1.0
    assert metrics["proxy_relaxed_exact_match"] == 1.0
    assert metrics["proxy_contains_match"] == 1.0
    assert metrics["official_evaluator_ran"] is False


def test_evaluate_longmemeval_predictions_reports_relaxed_and_contains_metrics(tmp_path):
    from mnemograph.benchmarks.longmemeval import LongMemEvalCase, evaluate_predictions

    cases = [
        LongMemEvalCase(
            question_id="q-001",
            question_type="single-session-assistant",
            question="What was the 7th job in the list?",
            answer="Transcriptionist.",
            question_date="2026-04-10",
            haystack_session_ids=[],
            haystack_dates=[],
            haystack_sessions=[],
            answer_session_ids=[],
        ),
        LongMemEvalCase(
            question_id="q-002",
            question_type="single-session-user",
            question="What did I buy for my sister's birthday gift?",
            answer="a yellow dress",
            question_date="2026-04-10",
            haystack_session_ids=[],
            haystack_dates=[],
            haystack_sessions=[],
            answer_session_ids=[],
        ),
    ]
    predictions_path = tmp_path / "predictions.jsonl"
    predictions_path.write_text(
        "\n".join(
            [
                '{"question_id": "q-001", "hypothesis": "Transcriptionist"}',
                '{"question_id": "q-002", "hypothesis": "You bought a yellow dress and a pair of matching earrings for your sister\'s birthday."}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    metrics = evaluate_predictions(
        cases=cases,
        predictions_path=predictions_path,
        dataset_path=tmp_path / "dataset.json",
        evaluator_script_path=None,
    )

    assert metrics["proxy_exact_match"] == 0.0
    assert metrics["proxy_relaxed_exact_match"] == 0.5
    assert metrics["proxy_contains_match"] == 1.0
