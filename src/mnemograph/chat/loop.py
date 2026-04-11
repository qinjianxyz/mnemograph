"""Thin chat session wrapper over the engine API."""

from mnemograph.engine import Mnemograph, QueryResult
from mnemograph.lifecycle.distill import ConversationTurn, distill_conversation
from mnemograph.mirror.write import write_working_mirrors
from mnemograph.retrieval.classify import RetrievalDecision


class ChatSession:
    """Maintain bounded session history while delegating storage/query to the engine."""

    def __init__(self, engine: Mnemograph, history_limit: int = 10):
        self.engine = engine
        self.history_limit = history_limit
        self.session_history: list[dict] = []

    def _trim_history(self) -> None:
        if len(self.session_history) > self.history_limit:
            self.session_history = self.session_history[-self.history_limit :]

    def handle_turn(self, user_input: str) -> QueryResult:
        """Handle one conversational turn."""
        distilled = distill_conversation([ConversationTurn(speaker="user", content=user_input)])
        self.session_history.append({"speaker": "user", "content": user_input})

        if distilled:
            if any(candidate.get("needs_llm_extraction") for candidate in distilled):
                self.engine.ingest_text(user_input, source="user")
            else:
                self.engine.ingest_candidates(
                    distilled,
                    raw_text=user_input,
                    store_text="\n".join(candidate["claim_text"] for candidate in distilled),
                    source="user",
                )
            result = QueryResult(
                answer="Stored the new information in memory.",
                claims=[],
                confidence=1.0,
                provenance=None,
                retrieval=RetrievalDecision("NO_RETRIEVAL", [], [], False, False, 1.0),
            )
        else:
            self.engine.session_history = list(self.session_history)
            result = self.engine.query(user_input)

        self.session_history.append({"speaker": "assistant", "content": result.answer})
        self._trim_history()
        self.engine.session_history = list(self.session_history)
        write_working_mirrors(self.engine.base_dir, self.engine.last_active_context, self.session_history)
        return result
