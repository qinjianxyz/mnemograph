"""Deterministic-first retrieval classification."""

from dataclasses import dataclass, replace
import re


STOP_ENTITIES = {
    "What",
    "Where",
    "When",
    "Why",
    "How",
    "Can",
    "Please",
    "Answer",
    "Actually",
    "Their",
}
DOMAIN_KEYWORDS = {
    "pricing": ("price", "pricing", "charge", "cost", "plan", "tier", "billing"),
    "product": ("product", "products", "feature", "features", "offer", "offers", "sell", "sells"),
    "team": ("ceo", "founder", "founders", "lead", "leads", "leadership", "executive", "executives"),
    "technology": ("api", "sdk", "database", "stack", "infrastructure", "architecture", "framework"),
    "company": ("headquartered", "founded", "customers", "market", "industry"),
    "security": ("security", "soc2", "soc 2", "sso", "scim", "compliance"),
}


@dataclass(frozen=True)
class RetrievalDecision:
    mode: str
    target_entities: list[str]
    target_domains: list[str]
    temporal_intent: bool
    provenance_requirement: bool
    confidence: float
    fallback_reason: str | None = None


def _extract_entities(query: str) -> list[str]:
    candidates = re.findall(r"\b[A-Z][a-zA-Z]+\b", query)
    return [candidate for candidate in candidates if candidate not in STOP_ENTITIES]


def classify_query(query: str, recent_turns: list[str] | None = None) -> RetrievalDecision:
    """Classify a query into a retrieval mode using deterministic heuristics."""
    lowered = query.lower().strip()
    recent_turns = recent_turns or []

    if any(phrase in lowered for phrase in ("bullet", "bullets", "rephrase", "rewrite", "shorter")):
        return RetrievalDecision("NO_RETRIEVAL", [], [], False, False, 0.95)

    if recent_turns and any(phrase in lowered for phrase in ("again", "repeat", "what was")):
        return RetrievalDecision("WORKING_MEMORY_ONLY", [], [], False, False, 0.9)

    if any(phrase in lowered for phrase in ("how do you know", "show sources", "where did you learn", "show evidence")):
        return RetrievalDecision("GRAPH_TRAVERSAL", [], [], False, True, 0.95)

    entities = _extract_entities(query)
    if any(word in lowered for word in ("compare", "last year", "before", "after")):
        domains = [
            domain
            for domain, keywords in DOMAIN_KEYWORDS.items()
            if any(keyword in lowered for keyword in keywords)
        ]
        return RetrievalDecision("MULTI_PATH", entities, domains, True, False, 0.75)

    domains = [
        domain
        for domain, keywords in DOMAIN_KEYWORDS.items()
        if any(keyword in lowered for keyword in keywords)
    ]
    if domains:
        return RetrievalDecision("STRUCTURED_LOOKUP", entities, domains, False, False, 0.85)

    return RetrievalDecision("SEMANTIC_SEARCH", entities, domains, False, False, 0.6)


def with_fallback(decision: RetrievalDecision, mode: str, reason: str) -> RetrievalDecision:
    """Return a copy of a retrieval decision with a fallback mode."""
    return replace(decision, mode=mode, fallback_reason=reason)
