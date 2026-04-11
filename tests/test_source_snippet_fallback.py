from mnemograph.engine import Mnemograph
from mnemograph.llm.mock import MockLLMClient


def test_query_falls_back_to_source_snippets_when_no_claims_exist(tmp_path):
    llm_client = MockLLMClient(
        responses={
            "extract": {
                "entities": [],
                "claims": [],
                "evidence_spans": [],
                "open_questions": [],
            },
            "answer": {
                "answer": "The 7th job in the list was remote travel agent. [1]",
                "confidence": 0.58,
                "citations": ["snippet-1"],
            },
        }
    )
    engine = Mnemograph(tmp_path, llm_client=llm_client)
    engine.ingest(
        locator="longmemeval:1903aded:session-0:1",
        content=(
            "assistant: 1. Virtual customer service representative "
            "2. Telehealth professional 3. Remote bookkeeper "
            "4. Virtual tutor or teacher 5. Freelance writer or editor "
            "6. Online survey taker 7. Remote travel agent"
        ),
        source_type="conversation",
        trust_tier="primary",
    )

    result = engine.query("What was the 7th job in the list?")

    assert result.answer == "The 7th job in the list was remote travel agent. [1]"
    assert result.confidence == 0.58
    assert result.provenance is not None
    assert "remote travel agent" in result.provenance.lower()
    assert "longmemeval:1903aded:session-0:1" in result.provenance
