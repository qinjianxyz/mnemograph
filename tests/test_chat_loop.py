import sqlite3

from mnemograph.chat.loop import ChatSession
from mnemograph.engine import Mnemograph
from mnemograph.llm.mock import MockLLMClient


def test_bounded_session_history_and_store_during_conversation(tmp_path):
    engine = Mnemograph(tmp_path, llm_client=MockLLMClient(responses={}))
    session = ChatSession(engine, history_limit=3)

    session.handle_turn("hello")
    session.handle_turn("thanks")
    session.handle_turn("Actually their enterprise plan is $500/mo.")
    answer = session.handle_turn("What does Enterprise cost?")

    assert len(session.session_history) == 3
    assert "500" in answer.answer

    with sqlite3.connect(engine.db_path) as conn:
        stored_text = " ".join(row[0] for row in conn.execute("SELECT text FROM source_chunks"))

    assert "Enterprise plan costs $500/month." in stored_text
    assert "Actually their enterprise plan is $500/mo." not in stored_text
