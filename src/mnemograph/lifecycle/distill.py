"""Conversation distillation helpers."""

from dataclasses import dataclass
import re


PLAN_PRICE_PATTERNS = (
    re.compile(r"(?P<plan>[A-Za-z]+)\s+plan\s+is\s+\$(?P<price>\d+)(?:/mo|/month| per month)", re.IGNORECASE),
    re.compile(r"(?P<plan>[A-Za-z]+)\s+costs\s+\$(?P<price>\d+)(?:/mo|/month| per month)", re.IGNORECASE),
    re.compile(r"(?P<plan>[A-Za-z]+)\s+is\s+\$(?P<price>\d+)(?:/mo|/month| per month)", re.IGNORECASE),
)
LEADERSHIP_PATTERNS = (
    re.compile(r"(?P<person>[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+leads\s+(?P<company>[A-Z][a-zA-Z]+)", re.IGNORECASE),
    re.compile(r"(?P<person>[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+is the\s+(?P<role>ceo|founder)\s+of\s+(?P<company>[A-Z][a-zA-Z]+)", re.IGNORECASE),
)


@dataclass(frozen=True)
class ConversationTurn:
    speaker: str
    content: str


def should_distill(
    turn_count: int,
    explicit_request: bool = False,
    session_end: bool = False,
    threshold: int = 15,
) -> bool:
    """Return whether episodic turns should be distilled."""
    return session_end or explicit_request or turn_count >= threshold


def distill_conversation(turns: list[ConversationTurn]) -> list[dict]:
    """Extract durable fact candidates from conversation turns."""
    candidates: list[dict] = []
    for turn in turns:
        matched = False
        for pattern in PLAN_PRICE_PATTERNS:
            match = pattern.search(turn.content)
            if not match:
                continue
            plan = match.group("plan").capitalize()
            price = match.group("price")
            candidates.append(
                {
                    "subject": f"Plan:{plan}",
                    "predicate": "price_usd_monthly",
                    "object": price,
                    "object_type": "literal",
                    "claim_text": f"{plan} plan costs ${price}/month.",
                    "domain": "pricing",
                    "memory_type": "semantic",
                }
            )
            matched = True
            break
        if matched:
            continue

        for pattern in LEADERSHIP_PATTERNS:
            match = pattern.search(turn.content)
            if not match:
                continue
            person = match.group("person").strip()
            company = match.group("company").strip()
            candidates.append(
                {
                    "subject": f"Company:{company}",
                    "predicate": "has_ceo",
                    "object": f"Person:{person.replace(' ', '_')}",
                    "object_type": "entity",
                    "claim_text": f"{company} is led by {person}.",
                    "domain": "team",
                    "memory_type": "semantic",
                }
            )
            matched = True
            break
        if matched:
            continue

        lowered = turn.content.lower().strip()
        if lowered.startswith(("actually", "correction:", "update:")):
            candidates.append(
                {
                    "needs_llm_extraction": True,
                    "raw_text": turn.content,
                }
            )
    return candidates
