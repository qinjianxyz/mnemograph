# Mnemograph System Architecture

Date: 2026-04-09

## Objective

Describe the initial system architecture for Mnemograph in enough detail to
guide implementation planning.

## Component model

### 1. Source ingestion layer

Responsibilities:

- fetch or load source content
- normalize metadata
- compute hashes
- split content into chunks
- enforce crawl policy and source deduplication

Inputs:

- URL
- file
- raw text
- chat-derived fact

Outputs:

- `source`
- `source_chunk`

Default crawl policy:

- same-domain by default
- bounded depth and page count
- robots-aware
- static fetch first, JS rendering only when needed
- boilerplate-aware normalization

### 2. Extraction layer

Responsibilities:

- run multi-pass extraction over chunks
- resolve entities and aliases
- derive candidate claims with mandatory SPO normalization
- map predicates to a semi-closed emergent registry
- extract relationships between entities and claims
- attach evidence spans
- classify domains, memory types, and confidence inputs
- generate open questions

Execution note:

- multi-pass refers to logical phases, not necessarily one LLM call per phase
- v1 should batch chunks and combine compatible phases to control latency and
  cost

Outputs:

- `claim`
- `evidence_span`
- `open_question`

Prompt contract:

- structured schema-validated outputs only
- prompt classes for extraction, reconciliation, retrieval classification, and
  consolidation

### 3. Reconciliation layer

Responsibilities:

- compare candidate claims to canon
- decide `ADD`, `UPDATE`, `SUPERSEDE`, `CONTRADICT`, `DELETE`, `NONE`
- calculate confidence deltas
- run consolidation and compaction passes
- run decay and archival policy
- emit changelog records

Outputs:

- `claim`
- `memory_change`
- `conflict`

### 4. Canonical store

Responsibilities:

- transactional truth store
- expose stable query interfaces
- support snapshotting and rebuilds

Initial backend:

- SQLite

### 5. Mirror projection layer

Responsibilities:

- generate human-readable files
- preserve durable provenance
- support review and diffing

Outputs:

- `memory/working/*`
- `memory/knowledge/*`
- `memory/sources/*`

### 6. Retrieval layer

Responsibilities:

- classify query mode
  - `NO_RETRIEVAL`, `WORKING_MEMORY_ONLY`, `STRUCTURED_LOOKUP`,
    `SEMANTIC_SEARCH`, `GRAPH_TRAVERSAL`, `MULTI_PATH`
- distinguish direct-response turns from working-memory turns
- prefer structured lookup when entity detection succeeds
- select retrieval targets
- call vector and graph adapters when beneficial
- apply score-based truncation and fallback policy

### 7. Context assembly layer

Responsibilities:

- build active context snapshots
- honor token budgets
- include provenance and uncertainty

### 8. Chat layer

Responsibilities:

- maintain session history
- answer with cited memory
- capture new knowledge during conversation
- distill episodic session memory into durable semantic memory at checkpoints

### 8.5 Python API layer

Responsibilities:

- expose the primary integration surface for application developers
- wrap ingest, query, provenance, and session operations behind typed methods
- keep the CLI and future UI as thin adapters over the same engine

Representative methods:

- `ingest(locator)`
- `ingest_text(text, source=...)`
- `query(question)`
- `show_provenance(answer_or_claim_id)`

### 8.6 CLI layer

Responsibilities:

- provide demo and operator-facing command entrypoints
- delegate to the Python API instead of owning business logic

### 9. Evaluation layer

Responsibilities:

- run benchmark suites
- run custom scenario tests
- compare ablations

## Projection architecture

The system uses asynchronous projections:

- canon commit
- file mirror projection
- vector projection
- graph projection

Each projection is:

- idempotent
- replayable
- measurable

## Graph strategy

Grafeo projection should encode:

- entities
- claims
- subject-predicate-object structure
- canonical predicate registry mappings
- source nodes
- evidence edges
- contradiction edges
- supersession edges
- temporal validity metadata

## Vector strategy

Qdrant projection should index:

- source chunks
- claim summaries
- atomic claims when needed for fallback retrieval

Payload filters should include:

- entity
- domain
- memory type
- source trust
- confidence bucket
- freshness bucket

Named retrieval profiles:

- `quality_profile`
  - hosted, strongest default embedding quality
- `local_profile`
  - OSS-friendly local embeddings

## Failure model

If graph or vector projection fails:

- canon remains valid
- mirror files remain valid
- projection lag is surfaced
- retries can rebuild derived state

## Implementation note

This architecture is intentionally designed to support the Hobbes interview demo
and a broader public OSS memory engine without needing two separate systems.

The first implementation should build the Python API before the CLI so tests
and downstream integrations use the same stable surface.
