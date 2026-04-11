# Mnemograph Retrieval, Context Assembly, and Chat Design

Date: 2026-04-09

## Objective

Specify how the system decides what to retrieve, what to assemble into context,
and how chat interactions update memory.

## Retrieval mode taxonomy

- `NO_RETRIEVAL`
  - direct local response, no memory access
- `WORKING_MEMORY_ONLY`
  - use session-local active context only
- `STRUCTURED_LOOKUP`
  - entity/predicate/domain lookup against canon
- `SEMANTIC_SEARCH`
  - vector recall over chunks and claims
- `GRAPH_TRAVERSAL`
  - relationship, provenance, or temporal traversal
- `MULTI_PATH`
  - combined retrieval for harder questions

## Default classifier policy

Use the LLM as a structured retrieval classifier in v1.

Bias:

- if an entity is detectable, prefer structured lookup
- if the query asks "how do you know" or requests relationships, prefer graph
- if the query is exploratory, use semantic search
- if the query mixes value, time, and relationships, use multi-path

## Structured classifier output

Required fields:

- retrieval mode
- target entities
- target domains
- temporal intent
- provenance requirement
- confidence in classification

## Retrieval order

1. working memory
2. structured canonical lookup
3. vector recall
4. graph traversal
5. context assembly

Reranking is intentionally deferred from v1. The default v1 path uses
score-based truncation and mode-aware ordering so the first implementation
stays debuggable. Cross-encoder or LLM reranking can be added only after
profiling shows a clear quality gap.

## Retrieval fallback policy

- if `STRUCTURED_LOOKUP` returns zero results, automatically fall back to
  `SEMANTIC_SEARCH`
- if `SEMANTIC_SEARCH` also returns zero relevant results, return an honest
  no-information answer
- if `GRAPH_TRAVERSAL` cannot resolve an entity edge, fall back to the best
  matching structured or semantic result and surface uncertainty
- every fallback must be recorded in the retrieval run for later evaluation

## Context assembly rules

Assemble:

- high-confidence summary claims first
- atomic claims when needed for nuance
- evidence spans for supporting claims
- active conflicts and open questions

Summary bypass triggers:

- if summary-based answer confidence is below `0.70`, expand to the relevant
  atomic claims
- if the query targets a specific predicate, value, or time slice that the
  summary abstracts over, expand to the matching atomic claims
- if unresolved conflicts exist in the summarized region, include the
  conflicting atomic claims by default

Avoid:

- stale claims without labels
- duplicate facts represented at multiple levels
- raw source dumps unless explicitly requested

## Token discipline

Context builder should optimize for:

- summary-first context
- atomic-on-demand expansion
- evidence snippets over large chunks
- conflict visibility without unnecessary duplication

## Trust UX

Default graduated disclosure:

- high confidence: clean answer
- medium confidence: qualified answer
- low confidence: hedged answer with source surfaced
- active conflict: both versions surfaced
- no evidence: explicit gap

Full provenance is available on demand through:

- “show sources”
- “how do you know this?”
- “show evidence”

## Store during conversation

1. detect candidate durable fact
2. classify memory type
3. reconcile against canon
4. update mirrors and projections
5. allow later recall

## Primary integration surface

The primary consumer interface should be a Python API, not the CLI.

The default engine surface should expose operations equivalent to:

- `ingest(locator)`
- `ingest_text(text, source=...)`
- `query(question)`
- `show_provenance(answer_or_claim_id)`

The CLI is a thin wrapper over this API for demos and manual inspection.

Distillation triggers:

- session end
- explicit user request
- long conversation threshold reached

Default long conversation threshold:

- distill after `15` turns unless the session is already in a batched
  distillation flow

## Session artifacts

Hobbes-compatible mirror outputs:

- `memory/working/active_context.json`
- `memory/working/session_history.json`
