import json


def test_load_longmemeval_cases_reads_official_case_shape(tmp_path):
    from mnemograph.benchmarks.longmemeval import load_longmemeval_cases

    fixture_path = tmp_path / "longmemeval.json"
    fixture_path.write_text(
        json.dumps(
            [
                {
                    "question_id": "q-001",
                    "question_type": "knowledge-update",
                    "question": "What does Pro cost now?",
                    "answer": "$59/month",
                    "question_date": "2026-04-10",
                    "haystack_session_ids": ["session-1", "session-2"],
                    "haystack_dates": ["2026-04-01", "2026-04-09"],
                    "haystack_sessions": [
                        [
                            {"role": "user", "content": "What does Pro cost?"},
                            {"role": "assistant", "content": "The Pro plan costs $49/month."},
                        ],
                        [
                            {"role": "user", "content": "Pricing changed this week."},
                            {"role": "assistant", "content": "The Pro plan now costs $59/month.", "has_answer": True},
                        ],
                    ],
                    "answer_session_ids": ["session-2"],
                }
            ]
        ),
        encoding="utf-8",
    )

    cases = load_longmemeval_cases(fixture_path)

    assert len(cases) == 1
    assert cases[0].question_id == "q-001"
    assert cases[0].question_type == "knowledge-update"
    assert cases[0].answer_session_ids == ["session-2"]


def test_build_longmemeval_replay_steps_supports_full_and_oracle_history():
    from mnemograph.benchmarks.longmemeval import LongMemEvalCase, build_replay_steps

    case = LongMemEvalCase(
        question_id="q-001",
        question_type="knowledge-update",
        question="What does Pro cost now?",
        answer="$59/month",
        question_date="2026-04-10",
        haystack_session_ids=["session-1", "session-2"],
        haystack_dates=["2026-04-01", "2026-04-09"],
        haystack_sessions=[
            [
                {"role": "user", "content": "What does Pro cost?"},
                {"role": "assistant", "content": "The Pro plan costs $49/month."},
            ],
            [
                {"role": "user", "content": "Pricing changed this week."},
                {"role": "assistant", "content": "The Pro plan now costs $59/month.", "has_answer": True},
            ],
        ],
        answer_session_ids=["session-2"],
    )

    full_history = build_replay_steps(case, replay_mode="full-history")
    oracle_history = build_replay_steps(case, replay_mode="oracle-history")

    assert [(step["session_id"], step["turn_index"]) for step in full_history] == [
        ("session-1", 0),
        ("session-1", 1),
        ("session-2", 0),
        ("session-2", 1),
    ]
    assert [(step["session_id"], step["turn_index"]) for step in oracle_history] == [
        ("session-2", 0),
        ("session-2", 1),
    ]
    assert oracle_history[1]["role"] == "assistant"
    assert oracle_history[1]["content"] == "assistant: The Pro plan now costs $59/month."


def test_format_longmemeval_prediction_matches_official_shape():
    from mnemograph.benchmarks.longmemeval import format_prediction_record

    record = format_prediction_record(question_id="q-001", hypothesis="The Pro plan now costs $59/month.")

    assert record == {
        "question_id": "q-001",
        "hypothesis": "The Pro plan now costs $59/month.",
    }
