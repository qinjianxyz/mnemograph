"""Primary Python API surface for Mnemograph."""

from dataclasses import dataclass
import math
from pathlib import Path
import re
import sqlite3

from mnemograph.context.assemble import assemble_context
from mnemograph.context.render import render_provenance_chain
from mnemograph.ingest.crawl import crawl_priority_pages
from mnemograph.ingest.pipeline import IngestResult, ingest_text_source
from mnemograph.llm.client import StructuredLLMClient
from mnemograph.mirror.write import write_durable_mirrors, write_working_mirrors
from mnemograph.retrieval.classify import RetrievalDecision, classify_query
from mnemograph.retrieval.plan import apply_fallback


@dataclass(frozen=True)
class QueryResult:
    answer: str
    claims: list[dict]
    confidence: float
    provenance: str | None
    retrieval: RetrievalDecision


class Mnemograph:
    """Library-first entrypoint for Mnemograph memory operations."""

    def __init__(self, base_dir: str | Path, llm_client: StructuredLLMClient):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.base_dir / "mnemograph.db"
        self.llm_client = llm_client
        self.session_history: list[dict] = []
        self.last_active_context: dict = {"claims": [], "evidence_spans": [], "conflicts": [], "open_questions": []}
        self.last_crawl_report: dict = {"pages_attempted": 0, "pages_succeeded": 0, "pages_failed": []}

    @staticmethod
    def _infer_entity_payload(entity_id: str) -> dict[str, str]:
        prefix, _, suffix = entity_id.partition(":")
        entity_type = prefix.lower() if prefix else "entity"
        canonical_name = suffix.replace("_", " ") if suffix else entity_id
        return {
            "entity_id": entity_id,
            "entity_type": entity_type,
            "canonical_name": canonical_name,
            "namespace": "company",
        }

    def ingest_candidates(
        self,
        claims: list[dict],
        raw_text: str,
        source: str = "user",
        trust_tier: str | None = None,
        store_text: str | None = None,
    ) -> IngestResult:
        """Ingest pre-normalized claims without another extraction model call."""
        entities: dict[str, dict[str, str]] = {}
        normalized_claims: list[dict] = []
        evidence_spans: list[dict] = []
        for index, claim in enumerate(claims, start=1):
            claim_id = claim.get("claim_id", f"claim-{index}")
            normalized_claim = {
                "claim_id": claim_id,
                "subject": claim["subject"],
                "predicate": claim["predicate"],
                "object": claim["object"],
                "object_type": claim["object_type"],
                "claim_text": claim["claim_text"],
                "domain": claim.get("domain", "unknown"),
                "extraction_run_id": "structured-local",
                "valid_time_start": claim.get("valid_time_start"),
                "valid_time_end": claim.get("valid_time_end"),
                "memory_type": claim.get("memory_type", "semantic"),
            }
            normalized_claims.append(normalized_claim)
            entities[claim["subject"]] = self._infer_entity_payload(claim["subject"])
            if claim["object_type"] == "entity":
                entities[claim["object"]] = self._infer_entity_payload(claim["object"])
            evidence_spans.append(
                {
                    "claim_id": normalized_claim["claim_id"],
                    "quote_text": raw_text,
                    "source_id": "source-local",
                    "chunk_id": "chunk-local",
                    "evidence_strength": 1.0,
                    "extraction_run_id": "structured-local",
                }
            )

        payload = {
            "entities": list(entities.values()),
            "claims": normalized_claims,
            "evidence_spans": evidence_spans,
            "open_questions": [],
        }
        resolved_trust_tier = trust_tier or ("user" if source == "user" else "baseline" if source == "baseline" else "primary")
        resolved_source_type = source if source in {"baseline", "document", "user"} else "text"
        locator = {
            "baseline": "baseline:seed",
            "user": "user:conversation",
            "document": "document:uploaded",
        }.get(source, f"{source}:note")
        result = ingest_text_source(
            db_path=self.db_path,
            locator=locator,
            content=store_text or raw_text,
            llm_client=self.llm_client,
            source_type=resolved_source_type,
            trust_tier=resolved_trust_tier,
            model_name="precomputed-structured",
            prompt_version="seeded",
            precomputed_payload=payload,
        )
        write_durable_mirrors(self.base_dir, self.db_path)
        return result

    def ingest(
        self,
        locator: str,
        content: str,
        source_type: str = "url",
        trust_tier: str = "primary",
    ) -> IngestResult:
        """Ingest a source with explicit content."""
        result = ingest_text_source(
            db_path=self.db_path,
            locator=locator,
            content=content,
            llm_client=self.llm_client,
            source_type=source_type,
            trust_tier=trust_tier,
        )
        write_durable_mirrors(self.base_dir, self.db_path)
        return result

    def ingest_text(self, text: str, source: str = "user", trust_tier: str | None = None) -> IngestResult:
        """Ingest raw text as a source."""
        resolved_trust_tier = trust_tier or ("user" if source == "user" else "baseline" if source == "baseline" else "primary")
        resolved_source_type = source if source in {"baseline", "document", "user"} else "text"
        locator = {
            "baseline": "baseline:seed",
            "user": "user:conversation",
            "document": "document:uploaded",
        }.get(source, f"{source}:note")
        result = ingest_text_source(
            db_path=self.db_path,
            locator=locator,
            content=text,
            llm_client=self.llm_client,
            source_type=resolved_source_type,
            trust_tier=resolved_trust_tier,
        )
        write_durable_mirrors(self.base_dir, self.db_path)
        return result

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        tokens: list[str] = []
        for token in re.findall(r"[a-z0-9]+", text.lower()):
            normalized = re.sub(r"^(\d+)(st|nd|rd|th)$", r"\1", token)
            if normalized in {"what", "does", "the", "and", "for", "with"}:
                continue
            if len(normalized) > 2 or normalized.isdigit():
                tokens.append(normalized)
        return tokens

    def _load_active_claims(self) -> list[dict]:
        if not self.db_path.exists():
            return []
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT
                    claims.claim_id,
                    claims.subject_entity_id,
                    claims.predicate_id,
                    claims.object_type,
                    claims.object_entity_id,
                    claims.object_value,
                    claims.claim_text,
                    claims.domain,
                    claims.status,
                    claims.confidence,
                    subject_entity.canonical_name AS subject_name,
                    object_entity.canonical_name AS object_name
                FROM claims
                LEFT JOIN entities AS subject_entity
                  ON subject_entity.entity_id = claims.subject_entity_id
                LEFT JOIN entities AS object_entity
                  ON object_entity.entity_id = claims.object_entity_id
                WHERE claims.status = 'active'
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def _load_evidence_rows(self, claim_ids: list[str]) -> list[dict]:
        if not claim_ids or not self.db_path.exists():
            return []
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT
                    evidence_spans.evidence_id,
                    evidence_spans.claim_id,
                    evidence_spans.quote_text,
                    evidence_spans.source_id,
                    evidence_spans.chunk_id,
                    evidence_spans.evidence_strength,
                    sources.locator,
                    sources.ingested_at
                FROM evidence_spans
                JOIN sources ON sources.source_id = evidence_spans.source_id
                WHERE evidence_spans.claim_id IN ({placeholders})
                ORDER BY evidence_spans.evidence_strength DESC, evidence_spans.evidence_id ASC
                """.format(placeholders=",".join("?" for _ in claim_ids)),
                claim_ids,
            ).fetchall()
        return [dict(row) for row in rows]

    def _load_conflicts_for_claims(self, claim_ids: list[str]) -> list[dict]:
        if not claim_ids or not self.db_path.exists():
            return []
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT conflict_id, conflict_type, left_claim_id, right_claim_id, status, resolution_policy
                FROM conflicts
                WHERE left_claim_id IN ({placeholders})
                   OR right_claim_id IN ({placeholders})
                ORDER BY created_at DESC
                """.format(placeholders=",".join("?" for _ in claim_ids)),
                claim_ids + claim_ids,
            ).fetchall()
        return [dict(row) for row in rows]

    def _load_claim_by_id(self, claim_id: str) -> dict | None:
        if not self.db_path.exists():
            return None
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT claim_id, subject_entity_id, predicate_id, object_value, claim_text, confidence
                FROM claims
                WHERE claim_id = ?
                """,
                (claim_id,),
            ).fetchone()
        return dict(row) if row else None

    def ingest_url(
        self,
        url: str,
        fetcher=None,
        max_pages: int = 4,
    ) -> IngestResult:
        """Fetch a seed URL plus priority subpages and ingest each as its own source."""
        pages, failures = crawl_priority_pages(
            url,
            fetcher=fetcher,
            max_pages=max_pages,
            return_failures=True,
        )
        self.last_crawl_report = {
            "pages_attempted": len(pages) + len(failures),
            "pages_succeeded": len(pages),
            "pages_failed": failures,
        }
        if not pages:
            raise ValueError(f"no crawlable pages were retrieved from {url}")

        page_results: list[IngestResult] = []
        parent_source_id: str | None = None
        for index, page in enumerate(pages):
            result = ingest_text_source(
                db_path=self.db_path,
                locator=page["url"],
                content=page["text"],
                llm_client=self.llm_client,
                source_type="url",
                trust_tier="primary",
                parent_source_id=parent_source_id,
            )
            if index == 0:
                parent_source_id = result.source_id
            page_results.append(result)

        write_durable_mirrors(self.base_dir, self.db_path)
        return IngestResult(
            source_id=page_results[0].source_id,
            extraction_run_id=page_results[0].extraction_run_id,
            claim_ids=[claim_id for result in page_results for claim_id in result.claim_ids],
            chunk_ids=[chunk_id for result in page_results for chunk_id in result.chunk_ids],
            open_questions=[question for result in page_results for question in result.open_questions],
        )

    def _structured_lookup(self, decision: RetrievalDecision) -> list[dict]:
        claims = self._load_active_claims()
        target_domains = {domain.lower() for domain in decision.target_domains}
        target_entities = [entity.lower() for entity in decision.target_entities]
        filtered: list[dict] = []

        for claim in claims:
            if target_domains and claim.get("domain", "").lower() not in target_domains:
                continue
            if target_entities:
                haystack = " ".join(
                    str(claim.get(field, "")).lower()
                    for field in (
                        "subject_entity_id",
                        "subject_name",
                        "object_entity_id",
                        "object_name",
                        "claim_text",
                    )
                )
                if not any(entity in haystack for entity in target_entities):
                    continue
            filtered.append(claim)

        return sorted(
            filtered,
            key=lambda claim: (-float(claim.get("confidence", 0.0)), claim["claim_id"]),
        )

    def _semantic_search(self, question: str) -> list[dict]:
        claims = self._load_active_claims()
        query_tokens = self._tokenize(question)
        if not query_tokens:
            return []
        lowered_question = question.lower()

        token_sets: dict[str, set[str]] = {}
        for claim in claims:
            document_text = " ".join(
                str(claim.get(field, ""))
                for field in (
                    "subject_entity_id",
                    "subject_name",
                    "predicate_id",
                    "object_value",
                    "object_name",
                    "claim_text",
                    "domain",
                )
            )
            token_sets[claim["claim_id"]] = set(self._tokenize(document_text))

        document_count = max(len(token_sets), 1)
        scored: list[tuple[float, dict]] = []
        for claim in claims:
            overlap = [token for token in query_tokens if token in token_sets[claim["claim_id"]]]
            if not overlap:
                continue

            score = 0.0
            for token in overlap:
                document_frequency = sum(1 for tokens in token_sets.values() if token in tokens)
                idf = math.log((1 + document_count) / (1 + document_frequency)) + 1.0
                score += idf
            if "what does" in lowered_question and claim.get("domain") == "company":
                score += 2.0
            if "who" in lowered_question and claim.get("domain") == "team":
                score += 1.5
            score *= 0.5 + float(claim.get("confidence", 0.0))
            scored.append((score, claim))

        return [
            claim
            for _, claim in sorted(
                scored,
                key=lambda item: (-item[0], -float(item[1].get("confidence", 0.0)), item[1]["claim_id"]),
            )
        ]

    def _source_snippet_search(self, question: str, limit: int = 5) -> list[dict]:
        if not self.db_path.exists():
            return []
        query_tokens = self._tokenize(question)
        if not query_tokens:
            return []
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT
                    source_chunks.chunk_id,
                    source_chunks.text,
                    sources.source_id,
                    sources.locator,
                    sources.ingested_at
                FROM source_chunks
                JOIN sources ON sources.source_id = source_chunks.source_id
                ORDER BY sources.ingested_at ASC, source_chunks.chunk_index ASC
                """
            ).fetchall()

        document_count = max(len(rows), 1)
        token_sets: dict[str, set[str]] = {
            row["chunk_id"]: set(self._tokenize(str(row["text"])))
            for row in rows
        }
        scored: list[tuple[float, dict]] = []
        for row in rows:
            overlap = [token for token in query_tokens if token in token_sets[row["chunk_id"]]]
            if not overlap:
                continue
            score = 0.0
            for token in overlap:
                document_frequency = sum(1 for tokens in token_sets.values() if token in tokens)
                idf = math.log((1 + document_count) / (1 + document_frequency)) + 1.0
                score += idf
            scored.append((score, dict(row)))
        return [
            row
            for _, row in sorted(scored, key=lambda item: (-item[0], item[1]["chunk_id"]))[:limit]
        ]

    def _build_answer_prompt(
        self,
        question: str,
        claims: list[dict],
        evidence_spans: list[dict],
        conflicts: list[dict],
        source_snippets: list[dict],
        reference_date: str | None,
    ) -> str:
        claim_lines = [
            f"- [{index}] {claim['claim_text']} (domain={claim.get('domain')}, confidence={claim.get('confidence')})"
            for index, claim in enumerate(claims, start=1)
        ]
        evidence_lines = [
            f"- claim={span['claim_id']} quote={span['quote_text']}"
            for span in evidence_spans
        ]
        conflict_lines = [
            f"- {conflict['conflict_type']} between {conflict['left_claim_id']} and {conflict['right_claim_id']}"
            for conflict in conflicts
        ]
        snippet_lines = [
            f"- [{index}] {snippet['text']} (locator={snippet['locator']})"
            for index, snippet in enumerate(source_snippets, start=1)
        ]
        return "\n".join(
            [
                "Answer the user question using the supplied claims.",
                "Return JSON with keys: answer, confidence, citations.",
                "Use inline citations like [1] when evidence exists.",
                "If the evidence conflicts, say so explicitly.",
                f"Question: {question}",
                *( [f"Reference date: {reference_date}"] if reference_date else [] ),
                "Claims:",
                *claim_lines,
                "Evidence:",
                *(evidence_lines or ["- none"]),
                "Source snippets:",
                *(snippet_lines or ["- none"]),
                "Conflicts:",
                *(conflict_lines or ["- none"]),
            ]
        )

    def _fallback_answer(
        self,
        claims: list[dict],
        conflicts: list[dict],
    ) -> tuple[str, float, list[str]]:
        if not claims:
            return ("I don't know based on the current memory.", 0.0, [])

        top_claim = claims[0]
        cited_claim_ids = [top_claim["claim_id"]]
        confidence = float(top_claim.get("confidence", 0.5))
        if conflicts:
            conflict_claim = claims[1] if len(claims) > 1 else top_claim
            answer = (
                "I have conflicting information: "
                f"{top_claim['claim_text']} [1] "
                f"and {conflict_claim['claim_text']} [2]"
            )
            cited_claim_ids = [claim["claim_id"] for claim in claims[:2]]
            return (answer, min(confidence, 0.5), cited_claim_ids)
        if confidence >= 0.8:
            return (f"{top_claim['claim_text']} [1]", confidence, cited_claim_ids)
        if confidence >= 0.5:
            return (f"Based on current memory, {top_claim['claim_text']} [1]", confidence, cited_claim_ids)
        return (f"I'm not fully confident, but {top_claim['claim_text']} [1]", confidence, cited_claim_ids)

    def _synthesize_answer(
        self,
        question: str,
        claims: list[dict],
        evidence_spans: list[dict],
        conflicts: list[dict],
        source_snippets: list[dict],
        reference_date: str | None,
    ) -> tuple[str, float, list[str]]:
        if not claims:
            return ("I don't know based on the current memory.", 0.0, [])
        try:
            payload = self.llm_client.generate_structured(
                operation="answer",
                prompt=self._build_answer_prompt(
                    question,
                    claims,
                    evidence_spans,
                    conflicts,
                    source_snippets,
                    reference_date,
                ),
                required_keys=("answer", "confidence", "citations"),
            )
            citations = payload.get("citations", [])
            return (
                payload["answer"],
                float(payload["confidence"]),
                citations,
            )
        except (KeyError, NotImplementedError, ValueError):
            return self._fallback_answer(claims, conflicts)

    def _build_snippet_answer_prompt(self, question: str, snippets: list[dict]) -> str:
        snippet_lines = [
            f"- [{index}] {snippet['text']} (locator={snippet['locator']})"
            for index, snippet in enumerate(snippets, start=1)
        ]
        return self._build_snippet_answer_prompt_with_reference(question, snippets, None)

    def _build_snippet_answer_prompt_with_reference(
        self,
        question: str,
        snippets: list[dict],
        reference_date: str | None,
    ) -> str:
        snippet_lines = [
            f"- [{index}] {snippet['text']} (locator={snippet['locator']})"
            for index, snippet in enumerate(snippets, start=1)
        ]
        return "\n".join(
            [
                "Answer the user question using the supplied source snippets.",
                "Return JSON with keys: answer, confidence, citations.",
                f"Question: {question}",
                *( [f"Reference date: {reference_date}"] if reference_date else [] ),
                "Source snippets:",
                *snippet_lines,
            ]
        )

    def _synthesize_from_snippets(
        self,
        question: str,
        snippets: list[dict],
        reference_date: str | None = None,
    ) -> tuple[str, float]:
        if not snippets:
            return ("I don't know based on the current memory.", 0.0)
        try:
            payload = self.llm_client.generate_structured(
                operation="answer",
                prompt=self._build_snippet_answer_prompt_with_reference(question, snippets, reference_date),
                required_keys=("answer", "confidence", "citations"),
            )
            return payload["answer"], float(payload["confidence"])
        except (KeyError, NotImplementedError, ValueError):
            return snippets[0]["text"], 0.35

    def _render_snippet_provenance(self, snippets: list[dict]) -> str | None:
        if not snippets:
            return None
        top = snippets[0]
        return "\n".join(
            [
                f'Source: {top["locator"]}',
                f'Evidence: "{top["text"]}"',
            ]
        )

    @staticmethod
    def _merge_provenance(*parts: str | None) -> str | None:
        rendered = [part for part in parts if part]
        return "\n\n".join(rendered) if rendered else None

    def _apply_confidence_style(
        self,
        answer: str,
        confidence: float,
        conflicts: list[dict],
    ) -> str:
        """Apply graduated disclosure so answer wording matches confidence."""
        lowered = answer.lower()
        if conflicts:
            return answer
        if confidence < 0.5 and "not fully confident" not in lowered:
            return f"I'm not fully confident, but {answer[0].lower() + answer[1:]}" if answer else answer
        if 0.5 <= confidence < 0.8 and "based on current memory" not in lowered:
            return f"Based on current memory, {answer[0].lower() + answer[1:]}" if answer else answer
        return answer

    def _render_provenance(
        self,
        claims: list[dict],
        evidence_spans: list[dict],
        cited_claim_ids: list[str],
    ) -> str | None:
        if not claims or not evidence_spans:
            return None
        claim_lookup = {claim["claim_id"]: claim for claim in claims}
        target_claim_ids = [claim_id for claim_id in cited_claim_ids if claim_id in claim_lookup]
        if not target_claim_ids:
            target_claim_ids = [claims[0]["claim_id"]]
        rendered: list[str] = []
        for claim_id in target_claim_ids:
            claim = claim_lookup.get(claim_id)
            evidence = next((span for span in evidence_spans if span["claim_id"] == claim_id), None)
            if not claim or not evidence:
                continue
            rendered.append(
                render_provenance_chain(
                    claim=claim,
                    evidence_span={
                        "evidence_id": evidence["evidence_id"],
                        "quote_text": evidence["quote_text"],
                    },
                    source={
                        "source_id": evidence["source_id"],
                        "locator": evidence["locator"],
                        "ingested_at": evidence["ingested_at"],
                    },
                )
            )
        return "\n\n".join(rendered) if rendered else None

    def render_changelog(self, extraction_run_id: str) -> str:
        """Render a human-readable change summary for one ingest run."""
        if not self.db_path.exists():
            return "No changelog available."
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT
                    memory_changes.change_type,
                    memory_changes.reason_code,
                    subject_claim.claim_text AS subject_claim_text,
                    related_claim.claim_text AS related_claim_text
                FROM memory_changes
                JOIN claims AS subject_claim
                  ON subject_claim.claim_id = memory_changes.subject_claim_id
                LEFT JOIN claims AS related_claim
                  ON related_claim.claim_id = memory_changes.related_claim_id
                WHERE subject_claim.extraction_run_id = ?
                ORDER BY memory_changes.created_at ASC
                """,
                (extraction_run_id,),
            ).fetchall()

        if not rows:
            return "No changes recorded for this ingest."

        lines: list[str] = []
        for row in rows:
            change_type = row["change_type"]
            if change_type == "SUPERSEDED":
                lines.append(
                    f"SUPERSEDED: {row['related_claim_text']} -> {row['subject_claim_text']}"
                )
            elif change_type == "CONFLICT":
                lines.append(
                    f"CONFLICT: {row['reason_code']} between {row['related_claim_text']} and {row['subject_claim_text']}"
                )
            else:
                lines.append(f"ADDED: {row['subject_claim_text']}")
        return "\n".join(lines)

    def _record_history(self, speaker: str, content: str) -> None:
        self.session_history.append({"speaker": speaker, "content": content})

    def query(self, question: str, reference_date: str | None = None) -> QueryResult:
        """Query the memory store and write working-memory mirrors."""
        recent_turns = [turn["content"] for turn in self.session_history[-3:]]
        decision = classify_query(question, recent_turns=recent_turns)
        claims: list[dict] = []
        evidence_spans: list[dict] = []
        conflicts: list[dict] = []
        source_snippets: list[dict] = []

        if decision.mode == "WORKING_MEMORY_ONLY" and self.last_active_context["claims"]:
            claims = self.last_active_context["claims"]
            evidence_spans = self.last_active_context.get("evidence_spans", [])
            conflicts = self.last_active_context.get("conflicts", [])
        elif decision.mode == "GRAPH_TRAVERSAL" and self.last_active_context["claims"]:
            claims = self.last_active_context["claims"]
            evidence_spans = self.last_active_context.get("evidence_spans", [])
            conflicts = self.last_active_context.get("conflicts", [])
        elif decision.mode == "STRUCTURED_LOOKUP":
            claims = self._structured_lookup(decision)
            if not claims:
                decision = apply_fallback(decision, structured_hits=0, semantic_hits=1)
                claims = self._semantic_search(question)
            if not claims:
                source_snippets = self._source_snippet_search(question)
                if not source_snippets:
                    decision = apply_fallback(decision, semantic_hits=0)
        elif decision.mode == "GRAPH_TRAVERSAL":
            decision = apply_fallback(decision, graph_resolved=False, semantic_hits=0)
            claims = self._semantic_search(question)
            if not claims:
                source_snippets = self._source_snippet_search(question)
        elif decision.mode == "SEMANTIC_SEARCH":
            claims = self._semantic_search(question)
            if not claims:
                source_snippets = self._source_snippet_search(question)
                if not source_snippets:
                    decision = apply_fallback(decision, semantic_hits=0)
        else:
            claims = []

        if claims and not evidence_spans:
            evidence_spans = self._load_evidence_rows([claim["claim_id"] for claim in claims])
        if claims and not conflicts:
            conflicts = self._load_conflicts_for_claims([claim["claim_id"] for claim in claims])
        if claims and not source_snippets and decision.mode in {"STRUCTURED_LOOKUP", "SEMANTIC_SEARCH"}:
            source_snippets = self._source_snippet_search(question, limit=3)

        active_context = assemble_context(
            question=question,
            claims=claims,
            evidence_spans=evidence_spans,
            conflicts=conflicts,
            open_questions=[],
        )
        self.last_active_context = active_context

        if decision.mode == "GRAPH_TRAVERSAL" and claims and evidence_spans:
            cited_claim_ids = [claim["claim_id"] for claim in claims]
            answer = self._render_provenance(claims, evidence_spans, cited_claim_ids) or "I don't know based on the current memory."
            confidence = 1.0 if answer != "I don't know based on the current memory." else 0.0
            provenance = answer if confidence > 0 else None
        elif claims:
            answer, confidence, cited_claim_ids = self._synthesize_answer(
                question,
                claims,
                evidence_spans,
                conflicts,
                source_snippets,
                reference_date,
            )
            answer = self._apply_confidence_style(answer, confidence, conflicts)
            provenance = self._merge_provenance(
                self._render_provenance(claims, evidence_spans, cited_claim_ids),
                self._render_snippet_provenance(source_snippets),
            )
        elif source_snippets:
            answer, confidence = self._synthesize_from_snippets(question, source_snippets, reference_date)
            provenance = self._render_snippet_provenance(source_snippets)
        elif decision.mode == "NO_RETRIEVAL":
            answer = "I can restate or reformat the current conversation."
            confidence = 1.0
            provenance = None
        else:
            answer = "I don't know based on the current memory."
            confidence = 0.0
            provenance = None

        self._record_history("user", question)
        self._record_history("assistant", answer)
        write_working_mirrors(self.base_dir, active_context, self.session_history)
        return QueryResult(
            answer=answer,
            claims=claims,
            confidence=confidence,
            provenance=provenance,
            retrieval=decision,
        )
