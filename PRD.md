# Mnemograph PRD

## 1. Executive Summary

Mnemograph is a local-first, provenance-first memory engine for AI agents. It
is designed to support persistent memory across sessions, high-quality
incremental updates, contradiction-aware reconciliation, temporal reasoning,
human review, and benchmarkable retrieval behavior.

The first concrete demonstration target is a company or entity intelligence
workflow that satisfies the Hobbes memory interview requirements:

- short-term working memory
- long-term knowledge memory
- source provenance memory
- URL and file/text ingestion
- incremental updates with contradiction handling
- retrieval-aware chat
- store-during-conversation

The broader product direction is a public OSS memory engine that can support
many domains beyond company intelligence.

## 2. Problem

Most agent memory systems fall into one of four traps:

1. They store raw text and call it memory.
2. They do semantic search but handle updates and contradictions poorly.
3. They maintain structured memory but make human inspection difficult.
4. They claim strong memory quality without a serious eval contract.

In practice, users need all of the following at once:

- durable memory across sessions
- high-signal extraction instead of raw dumps
- correct handling of changing facts over time
- provenance back to source evidence
- selective retrieval instead of prompt stuffing
- explicit confidence and uncertainty
- human-reviewable state
- reproducible benchmarks and tests

## 3. Goals

### Product goals

- Build a memory engine that agents can use to ingest, update, retrieve, and
  cite knowledge over time.
- Keep canonical memory state local, structured, and inspectable.
- Support both semantic retrieval and relational/temporal reasoning.
- Make memory quality measurable through public and custom benchmarks.

### System goals

- Separate working, durable, and source memory cleanly.
- Treat claims, evidence, conflicts, and supersession as first-class records.
- Normalize every durable claim into an explicit subject-predicate-object form.
- Support hybrid retrieval with optional vector and graph backends.
- Support a public OSS architecture with minimal default infrastructure.

### Demo goals

- Ingest a company URL or pasted document.
- Extract structured facts into long-term memory.
- Track source provenance and unresolved questions.
- Add a second source with overlapping or conflicting information.
- Produce a visible diff or changelog.
- Answer questions through selective retrieval and context assembly.
- Learn a new fact during chat and recall it later.

## 4. Non-Goals

- Build a general-purpose workflow orchestration platform.
- Depend on cloud-only managed services for core functionality.
- Make vector or graph infrastructure mandatory for the default install.
- Claim SOTA performance before the benchmark suite exists.

## 5. Users

### Primary users

- AI engineers building memory-enabled agents
- researchers benchmarking memory quality
- teams wanting inspectable agent memory
- operators who need to review or edit durable memory

### Secondary users

- product builders needing company or entity intelligence
- OSS contributors extending adapters, schemas, and evals

## 6. Design Principles

1. `Local-first canon`
   - the system should function without mandatory external infrastructure

2. `Hybrid inspectability`
   - durable memory must be queryable by software and readable by humans

3. `Provenance first`
   - every durable memory item must link back to source evidence

4. `Update-aware memory`
   - memory must handle change, not just accumulation

5. `Memory types matter`
   - factual, episodic, procedural, preference, and temporal memory should not
     all be treated identically

6. `Benchmark-first claims`
   - architecture claims must be tied to measurement plans

## 7. Evaluation Criteria Mapping

This project explicitly targets the Hobbes evaluation criteria.

### Memory architecture

- Working memory is ephemeral and session-scoped.
- Durable memory is persistent and structured.
- Source memory preserves provenance and replayability.

### Extraction quality

- Extraction outputs typed claims, not raw chunks alone.
- Extraction outputs normalized subject-predicate-object claims, not text-only
  memories.
- Evidence spans and source references are retained.
- Open questions are captured when information is absent or low confidence.

### Conflict resolution

- New evidence is reconciled with existing claims using explicit actions:
  `ADD`, `UPDATE`, `SUPERSEDE`, `CONTRADICT`, `DELETE`, `NONE`.
- Contradictions are tracked as records, not silently overwritten.

### Confidence tracking

- Each claim has a compositional confidence score with inspectable sub-signals.
- Answers surface low-confidence and unknown states explicitly.

### Retrieval strategy

- The system decides whether retrieval is necessary.
- Retrieval is scoped by domain, memory type, and budget.
- Graph and vector retrieval are optional but measured.

### Context assembly

- Active context contains only the most relevant memory records and evidence.
- The assembly process is logged and auditable.

### Store-during-conversation

- User-provided corrections and updates become candidate durable memory writes.
- Store operations go through reconciliation, not direct blind writes.

### Code quality

- Core logic is deterministic where possible.
- Critical paths are tested with golden cases and eval suites.

### AI tool usage

- Decision-making, tradeoffs, and prompt-assisted design remain public.

## 8. Product Scope

### v1 scope

- canonical local memory store
- file mirrors for review
- URL ingestion
- file/text ingestion
- claim extraction and evidence linkage
- incremental reconciliation
- contradiction and supersession tracking
- Python API surface
- thin CLI wrapper over the Python API
- working-memory session files
- optional Qdrant adapter
- optional Grafeo adapter
- unit, integration, and end-to-end tests
- benchmark harness skeleton and initial scenario set

### later scope

- web UI for review and editing
- connector ecosystem
- online sync modes
- multi-tenant service deployment

## 9. System Overview

Mnemograph has five major subsystems:

1. `Canonical memory engine`
2. `Ingestion and extraction pipeline`
3. `Reconciliation and conflict engine`
4. `Retrieval and context assembly engine`
5. `Evaluation and benchmarking harness`

## 10. Canonical Memory Model

### 10.1 Top-level memory layers

#### Working memory

Ephemeral session state.

Examples:

- active retrieved context
- bounded chat history
- current task state
- retrieval decisions
- transient hypotheses

#### Durable memory

Persistent structured memory.

Examples:

- accepted claims
- user profiles
- preferences
- procedural notes
- entity summaries
- supersession relationships

#### Source memory

Raw ingestion and provenance records.

Examples:

- source URL metadata
- file metadata
- normalized source chunks
- extraction runs
- content hashes

### 10.2 Canonical record types

The canonical store should support at least these record classes:

- `source`
- `source_chunk`
- `claim`
- `evidence_span`
- `entity`
- `conflict`
- `retrieval_run`
- `context_snapshot`
- `conversation_turn`
- `memory_change`

### 10.3 Memory type taxonomy

Each memory record may belong to one or more memory types:

- `semantic`
  - stable factual or descriptive knowledge
- `episodic`
  - what happened in a session or interaction
- `procedural`
  - how-to knowledge, workflows, playbooks
- `preference`
  - stable user or operator preferences
- `temporal`
  - facts whose truth depends on time

### 10.4 Claim structure

Every durable claim should capture:

- canonical id
- entity or namespace
- domain
- claim text
- subject
- predicate
- object
- object kind
  - entity, literal, enum, range, unknown
- object entity id when object kind is `entity`
- normalized SPO key
- confidence score
- support count
- status
  - active, superseded, contradicted, deleted, pending_review
- valid time window
- system time window
- source ids
- evidence span ids
- derived-from extraction run
- change history ids

SPO normalization is mandatory for durable claims. If extraction cannot produce a
valid subject, predicate, and object, the candidate should remain in a
non-durable extraction queue instead of entering canon as a first-class claim.

### 10.5 Claim normalization rules and predicate registry

The system should normalize claims into a canonical graph-friendly structure:

- `subject`
  - stable entity id or namespace-scoped subject key
- `predicate`
  - canonical predicate from a semi-closed domain registry
- `object`
  - entity id, literal value, enum value, range, or explicit unknown marker

If the object is an entity, canon must store both:

- `object_entity_id`
- `object_value`
  - a human-readable label or normalized display form

Examples:

- `Company:Acme` `has_pricing_plan` `Plan:Pro`
- `Plan:Pro` `price_usd_monthly` `49`
- `Company:Acme` `has_ceo` `Person:Jane_Doe`
- `Company:Acme` `pricing_page_status` `unknown`

This is the minimum structure required for:

- deterministic deduplication
- predicate-aware reconciliation
- graph projection
- entity-centric retrieval
- compositional aggregation and consolidation

Predicate normalization should use a semi-closed emergent registry:

- each domain starts with an initially sparse predicate registry
- extraction maps to known predicates when possible
- novel predicates may be proposed when no existing predicate fits
- novel predicates enter canon as provisional predicates and also enter a
  normalization queue instead of silently becoming permanent canonical
  predicates
- periodic normalization clusters similar predicates and merges them onto a
  canonical predicate

This is intended to avoid both failure modes:

- fully closed ontology bootstrapping failure
- fully open ontology synonym sprawl that breaks reconciliation

The predicate registry should be treated as a living artifact that evolves with
the knowledge base.

### 10.6 Provenance chain

Every answerable durable claim must support this chain:

- response
- claim
- evidence span
- source chunk
- source record
- original locator and timestamp

This chain must be queryable by APIs and renderable in human-facing output.

## 11. Storage Architecture

### 11.1 Canonical storage

`SQLite` is the canonical source of truth for v1.

Reasons:

- local-first
- easy install
- transactional updates
- easy snapshotting
- stable Rust and Python support
- straightforward schema control

### 11.2 File mirrors

Durable memory is mirrored into human-readable files.

Primary purposes:

- operator review
- git diffs
- debugging
- OSS transparency
- rebuilding graph/vector projections

Initial mirror layout for the Hobbes demo:

- `memory/working/`
- `memory/knowledge/`
- `memory/sources/`

### 11.3 Vector adapter

`Qdrant` is the primary optional vector adapter candidate.

Role:

- semantic recall over source chunks and memory records
- hybrid search with metadata filters
- score-based truncation and retrieval diversity in v1

### 11.3a Embedding profiles

Mnemograph should support named retrieval profiles rather than leaving the
embedding choice undefined.

Default v1 profiles:

- `quality_profile`
  - embeddings: `text-embedding-3-large`
  - intended use: hosted, highest out-of-box retrieval quality
- `local_profile`
  - embeddings: `bge-m3`
  - intended use: OSS-friendly local deployment with strong multilingual and
    hybrid retrieval characteristics

Selection criteria:

- retrieval quality on memory benchmarks
- hybrid dense+sparse compatibility
- multilingual support
- cost per million chunks
- local deployability
- latency under realistic ingestion and query loads

### 11.4 Graph adapter

`Grafeo` is the primary optional graph adapter candidate.

Role:

- entity relationships
- provenance edges
- contradiction edges
- supersession edges
- temporal and dependency traversals

Important boundary:

- Grafeo is not the canonical memory authority in v1
- Grafeo is an asynchronous graph projection over canonical memory state

### 11.5 Projection strategy

All adapters are projections over canon:

- canon write succeeds first
- mirror files update second
- vector and graph projections update asynchronously with retries
- projection lag is measured and visible

## 12. Ingestion Pipeline

### 12.1 Supported source types

- URL
- pasted text
- local file
- chat-provided fact

### 12.1a Crawling policy

URL ingestion quality depends on disciplined crawling.

Default crawl policy:

- same-domain only unless explicitly expanded
- maximum depth: `2`
- maximum pages: `40`
- prioritize likely high-signal pages:
  - homepage
  - pricing
  - product
  - docs
  - about
  - faq
  - security
- obey `robots.txt` by default
- apply per-domain rate limiting
  - default `1 request / second`
- deduplicate by normalized URL and content hash
- remove boilerplate, nav chrome, footers, cookie banners, and repeated page
  furniture where possible

Rendering strategy:

- static fetch first
- escalate to JS rendering only when the static page is content-poor or clearly
  client-rendered

Crawler outputs must preserve:

- source URL
- fetch timestamp
- response status
- normalized content hash
- parent URL / discovery path
- render mode

### 12.2 Ingestion stages

1. `source registration`
   - normalize source metadata
   - compute source id and content hash
   - store provenance record

2. `content acquisition`
   - crawl URL or load file/text
   - preserve raw and normalized representations

3. `chunking`
   - split content into chunks suitable for extraction and retrieval
   - preserve chunk ordering and offsets

4. `pass 1: entity recognition and resolution`
   - identify entities, aliases, and namespaces
   - resolve known entities when possible
   - create unresolved-entity candidates when not possible

5. `pass 2: claim extraction`
   - extract atomic claims per entity
   - require subject-predicate-object normalization for durable candidates
   - attach evidence spans and domains

6. `pass 3: relationship extraction`
   - detect entity-to-entity and claim-to-claim relationships
   - identify potential supersession and contradiction candidates

7. `pass 4: confidence calibration and gap detection`
   - classify claims as stated, weakly inferred, or uncertain
   - generate open questions and explicit unknowns
   - assign extraction-confidence inputs for later composition

8. `reconciliation planning`
   - compare candidates with existing canon
   - determine merge actions

9. `canonical commit`
   - write sources, claims, changes, and conflicts transactionally

10. `projection updates`
   - update file mirrors
   - update vector index
   - update graph projection

### 12.2a Multi-pass execution strategy

The four extraction passes are logical phases, not a requirement for four
separate LLM calls per chunk.

Default v1 execution:

- page-level or document-level prepass for entity inventory
- batch multiple chunks into a single extraction call where token budgets allow
- combine passes `1 + 2` by default
  - entity recognition and claim extraction in one structured output
- combine passes `3 + 4` by default
  - relationship extraction and confidence calibration in one structured output
- run only the expensive relationship phase on chunks that produced durable
  claims or entity interactions

Cost-constrained mode:

- allow a degraded single-pass extractor
- still require structured output and evidence spans
- mark extraction quality profile as reduced for evaluation purposes

### 12.3 Extraction quality requirements

Extraction must prefer:

- atomic claims over vague summaries
- explicit entities over anonymous references
- predicate normalization over free-form fact strings
- evidence-backed claims over unsupported abstractions
- domain labels over generic buckets
- explicit unknowns over fabricated certainty

### 12.4 Open questions

When the system cannot determine a fact, it should write an explicit open
question record such as:

- pricing unknown
- no evidence for customer count
- gated documentation
- contradictory employment of a role

### 12.5 Prompt architecture

Prompt quality is a first-class implementation surface.

All prompt-driven components should use structured outputs with explicit schemas.

Required prompt classes:

- `entity+claim extraction`
  - input: chunk batch + known entities + predicate registry snapshot
  - output: entities, aliases, claims, evidence spans, provisional predicates
- `relationship+calibration`
  - input: extracted claims + entity inventory + source metadata
  - output: relationships, contradiction candidates, extraction-confidence
    components, open questions
- `reconciliation ambiguity resolver`
  - input: candidate claims + ambiguous canonical match sets
  - output: match recommendation, rationale class, affected claim ids
- `retrieval classifier`
  - input: user query + working memory summary
  - output: retrieval mode, entities, domains, temporal/provenance flags
- `consolidation`
  - input: entity/domain claim bundles
  - output: summary claims + provenance backrefs

Prompt rules:

- outputs must validate against JSON schema or typed tool schemas
- hidden reasoning should not be stored as chain-of-thought artifacts
- use few-shot examples for high-risk tasks:
  - predicate normalization
  - conflict classification
  - temporal interpretation
  - open-question generation
- include a repair step only when schema validation fails

## 13. Incremental Merge and Conflict Resolution

This is one of the core differentiators.

### 13.1 Merge actions

Candidate updates can take one of these actions:

- `ADD`
- `UPDATE`
- `SUPERSEDE`
- `CONTRADICT`
- `DELETE`
- `NONE`

### 13.2 Reconciliation policy

The reconciliation engine should be deterministic by default.

Default deterministic path:

- exact or normalized SPO match
- valid-time overlap or temporal ordering
- typed conflict policy
- source trust comparison
- evidence count comparison

LLM-assisted reconciliation is fallback-only for ambiguous cases such as:

- entity identity
- predicate compatibility when normalized predicates are still provisional
- semantic similarity between near-match candidates
- ambiguous entity resolution

This keeps the common path fast, auditable, and testable while preserving an
escape hatch for the hard cases.

### 13.3 Conflict classes

Conflicts should be typed, not generic:

- `value_conflict`
- `temporal_conflict`
- `entity_resolution_conflict`
- `source_quality_conflict`
- `insufficient_evidence_conflict`

Default resolution posture:

- `temporal_conflict`
  - auto-supersede when claims refer to different valid times and the temporal
    ordering is supported
- `value_conflict`
  - auto-supersede only when the newer source is strictly higher trust
  - otherwise keep both and flag the conflict
- `entity_resolution_conflict`
  - auto-merge only above very high confidence
  - otherwise queue for human review
- `source_quality_conflict`
  - always flag
  - answer honestly with both sources if queried
- `insufficient_evidence_conflict`
  - keep the better-evidenced claim active
  - do not spend human review budget unless the claim is high-impact

### 13.4 Temporal semantics

Mnemograph should distinguish:

- `system time`
  - when the memory system learned something
- `valid time`
  - when the underlying fact was true

This is essential for:

- pricing changes
- leadership changes
- current projects vs past projects
- “tomorrow” or time-bound user facts

### 13.5 Confidence model

Confidence should not be a single opaque number.

The score should be derived from:

- source trust
- evidence count
- extraction certainty
- recency / freshness
- contradiction penalty
- user confirmation

The final output can still expose a single summarized confidence score, but the
subcomponents should remain inspectable.

Recommended v1 formula:

```text
clamped_component = max(component, component_floor)

confidence =
max(
  floor,
  clamped_trust^0.25 *
  clamped_evidence^0.20 *
  clamped_extraction^0.20 *
  clamped_recency^0.15 *
  clamped_contradiction^0.10 *
  clamped_confirmation^0.10
)
```

Where:

- each component is normalized to `[0, 1]`
- `floor` defaults to `0.05`
- each component has its own floor to avoid zero-product collapse
  - default `component_floor = 0.10`
- `contradiction` is a retained-confidence factor, not a raw penalty
- `confirmation` rises with explicit user or high-trust corroboration

The system should also support hard caps:

- unresolved active value conflict caps confidence at `0.60`
- single low-trust source caps confidence at `0.45`
- explicit user correction can raise confirmation but should not erase a
  contradiction flag on its own

### 13.6 Changelog requirements

Every durable write should produce machine-readable change records:

- what changed
- why it changed
- which sources triggered the change
- whether prior claims were superseded or contradicted

### 13.7 Memory consolidation and compaction

Durable memory cannot remain an append-only log.

The system needs a periodic consolidation process that:

- groups active claims by entity, domain, and predicate neighborhood
- merges redundant or mutually supporting claims
- creates consolidated summaries or rollups
- preserves provenance links back to underlying atomic claims
- marks consolidated claims as preferred retrieval surfaces without deleting the
  atomic source claims

Default trigger:

- when an entity accumulates more than `10` active atomic claims in the same
  domain, the domain becomes eligible for consolidation

Default policy:

- an LLM synthesizes an entity or domain summary from the contributing atomic
  claims
- the summary becomes the primary default retrieval surface
- atomic claims remain stored for provenance and auditability
- atomic claims are deprioritized in default retrieval once represented by a
  fresh summary
- summaries must record `last_consolidated_at` and reconsolidate when new
  claims arrive

Summary bypass triggers:

- if summary-based answer confidence falls below `0.70`, fall through to
  atomic claims
- if the user asks for a specific predicate or value that a summary abstracts
  over, include the relevant atomic claims even when a summary exists
- if unresolved conflicts are attached to the summarized area, surface the
  atomic claims that carry the disagreement

Consolidation outputs should include:

- `entity_summary`
- `domain_summary`
- `predicate_rollup`

Each consolidated record should preserve:

- contributing claim ids
- source support counts
- freshness window
- unresolved conflicts that prevented stronger consolidation

### 13.8 Memory decay and retention

Low-value memory should decay instead of accumulating forever.

Decay should be configurable by:

- memory type
- confidence
- retrieval frequency
- age
- conflict state

Recommended v1 policy:

- low-confidence temporal claims decay fastest
- unretrieved uncertain claims decay faster than frequently retrieved claims
- preferences decay slowly
- high-confidence consolidated semantic claims decay slowest

Concrete default:

- decay applies only when a claim is low-confidence, not user-confirmed, and not
  recently retrieved
- baseline weekly decay factor is `confidence = confidence * 0.95`
- claims below `0.10` confidence move to archived status rather than deletion

Never decay by default:

- user-confirmed claims
- high-evidence claims with support count above `3`
- historical temporal claims whose valid time has ended but which remain
  factually correct for that window

Decay actions can include:

- lower retrieval priority
- demotion from preferred to archival surfaces
- review-required status
- archival from active retrieval to cold storage

## 14. Retrieval Strategy

### 14.1 Retrieval decision

Not every question requires a durable-memory lookup.

The system should explicitly classify each query into one of these modes:

- `NO_RETRIEVAL`
  - direct response with no memory access
  - intended for meta-instructions, formatting requests, and purely local
    conversational turns
- `WORKING_MEMORY_ONLY`
  - use session-local cached active context and recent turns
  - do not access durable canon or external adapters
- `STRUCTURED_LOOKUP`
  - query canon by entity, predicate, domain, or namespace
- `SEMANTIC_SEARCH`
  - retrieve from vector memory or source chunks
- `GRAPH_TRAVERSAL`
  - retrieve via relationships, provenance, or temporal edges
- `MULTI_PATH`
  - combine structured, semantic, and graph retrieval

Each retrieval decision must be logged and later evaluable.

Default v1 implementation:

- use the LLM as a lightweight classifier with structured output

Primary implementation surface:

- the default integration target is a Python API, not the CLI
- the CLI should remain a thin wrapper over methods such as:
  - `ingest(...)`
  - `ingest_text(...)`
  - `query(...)`
  - `show_provenance(...)`
- output fields must include:
  - retrieval mode
  - target entities
  - target domains
  - temporal intent
  - provenance requirement

Default bias:

- prefer `STRUCTURED_LOOKUP` when an entity is detectable
- fall back to `SEMANTIC_SEARCH` only when the query is genuinely exploratory or
  under-specified

### 14.2 Retrieval planning

Given a user query, retrieval planning should determine:

- target entities
- target domains
- relevant memory types
- whether temporal reasoning is needed
- whether source evidence needs to be expanded
- context budget

Decision inputs should include:

- recent working-memory sufficiency
- explicit entity mentions
- predicate-like question structure
- temporal intent markers
- relationship intent markers
- ambiguity / under-specification
- need for evidence-backed answers

### 14.3 Retrieval order

Recommended order:

1. working memory
2. canonical durable memory by entity/domain/type
3. vector recall for related claims and chunks
4. graph traversal for related entities, provenance, conflicts, and temporal
   relations
5. context assembly

Fallback policy:

- if structured lookup returns zero relevant claims, automatically fall back to
  semantic search before answering with a knowledge gap
- if graph traversal cannot resolve the requested relationship, fall back to
  the best matching structured or semantic evidence and surface uncertainty
- if all durable retrieval paths return zero relevant evidence, answer
  honestly that the system does not know

### 14.4 Context assembly

The context builder should assemble:

- high-confidence claim summaries
- relevant evidence snippets
- active conflicts or low-confidence warnings
- open questions when material
- provenance chains for all claims included

The builder should avoid:

- dumping entire files
- mixing stale and current claims without labeling
- including irrelevant memory types

### 14.5 Answering behavior

Answers should:

- cite memory records and source records used
- acknowledge uncertainty
- say “I don’t know” when evidence is absent
- highlight contradictory evidence when unresolved

### 14.6 Provenance UX

For every answer, the system should be able to render:

- which claims were used
- which evidence spans supported each claim
- which source chunks those spans came from
- which original source URL or file produced the chunk
- when the source was ingested
- when the fact was valid if temporally grounded

Default trust UX is graduated disclosure:

- confidence `> 0.80`
  - clean answer by default
  - citations available on demand
- confidence `0.50 - 0.80`
  - qualified answer with lightweight uncertainty language
- confidence `< 0.50`
  - hedged answer with the key source surfaced inline
- active unresolved conflict
  - conflicting claims surfaced together
- no evidence
  - explicit gap statement

Default citation mode:

- light inline markers for ordinary use
- expandable provenance chain when the user asks for sources or explanation

## 15. Chat Loop

### 15.1 Required behaviors

- maintain bounded working memory
- decide whether retrieval is needed
- answer with provenance
- accept user corrections and additions
- write durable updates through reconciliation

### 15.2 Session files for the Hobbes demo

- `memory/working/active_context.json`
- `memory/working/session_history.json`

### 15.3 Store-during-conversation flow

1. detect candidate memory from user turn
2. classify memory type and domain
3. reconcile against existing canon
4. write change records and mirror files
5. allow later recall in the same or next session

### 15.4 Episodic to semantic distillation

Conversation memory is initially episodic.

At session checkpoints or session end, the system should run a distillation step
that:

- scans episodic turns and working-memory notes
- extracts candidate durable facts, preferences, and procedural lessons
- routes them through the same reconciliation pipeline as any other source
- preserves links from durable memory back to the originating conversation turn

This prevents raw conversation logs from becoming the durable memory layer while
still allowing useful facts to survive the session boundary.

## 16. Benchmarking and Evaluation

Yes, memory systems can be benchmarked seriously. Mnemograph should make that a
first-class requirement.

### 16.1 Public benchmark targets

- `LongMemEval / LongMemEval-S`
  - multi-session memory
  - knowledge updates
  - temporal reasoning
- `LoCoMo`
  - long conversation reasoning and recall
- `ConvoMem`
  - personalization and preference learning
- `MemoryBench`
  - provider comparison and reproducibility

### 16.2 Custom benchmark categories

Mnemograph also needs custom evals that public memory benchmarks underweight:

- source provenance completeness
- claim extraction precision
- contradiction detection accuracy
- supersession correctness
- open-question quality
- store-during-conversation correctness
- company/entity intelligence retrieval
- graph vs vector ablation quality

### 16.3 Evaluation metrics

At minimum:

- answer accuracy
- claim precision / recall
- update correctness
- contradiction detection precision / recall
- temporal reasoning accuracy
- provenance completeness rate
- retrieval decision accuracy
- retrieval precision@k
- context token count
- latency p50 / p95
- projection freshness lag

### 16.4 Required ablations

- canon only
- canon + vector
- canon + graph
- canon + vector + graph
- no temporal grounding
- no reconciliation engine
- no file mirrors

### 16.5 Benchmarking principle

Mnemograph should not claim superiority because it has more components. It
should only claim improvement if the measured system beats simpler baselines on
the tasks those components were introduced to solve.

## 17. Testing Strategy

### 17.1 Unit tests

- schema validation
- chunking
- crawl normalization and deduplication
- extraction parsing
- reconciliation decisions
- confidence calculation
- temporal reasoning helpers
- file mirror generation

### 17.2 Integration tests

- source ingest to canon
- canon to mirror projection
- canon to vector projection
- canon to Grafeo projection
- retrieval planner end-to-end on stored data
- crawling policy and page-prioritization behavior
- prompt-output schema validation and repair flow

### 17.3 End-to-end tests

- URL ingest and question answering
- second source introduces conflict
- user correction in conversation
- later recall of stored correction
- low-confidence / unknown answer behavior

### 17.4 Golden cases

The project should maintain stable golden scenarios for:

- same-fact duplicate
- richer update
- contradiction
- temporal supersession
- irrelevant new source
- gated or missing information
- provisional predicate normalization
- crawl boilerplate failure vs clean extraction

## 18. Implementation Architecture

### 18.1 Python-first v1

The v1 implementation should be Python-first.

Reasoning:

- the memory ecosystem is Python-native
- LLM clients, crawling, embeddings, and benchmark harnesses are easiest to
  integrate in Python
- extraction and eval iteration speed matters more than micro-optimizing
  reconciliation latency in v1
- Python minimizes contributor friction for a public OSS project

### 18.2 Rust where it materially helps

Rust remains valuable, but only for narrow roles where it compounds:

- Grafeo itself as a Rust-native graph engine
- optional projection workers for high-throughput indexing
- future embeddable or WASM-friendly local core components
- hot-path scoring or compaction utilities if profiling later justifies them

### 18.3 v1 Python responsibilities

Python should own:

- canonical schema and storage layer
- source ingestion pipelines
- extraction orchestration
- reconciliation engine
- retrieval planner
- Python API surface
- CLI wrapper
- demos
- eval runners and benchmark glue

## 19. Public Artifact Policy

These artifacts should remain public:

- README
- PRD
- architecture specs
- decision logs
- benchmark methodology
- major prompt and evaluation design notes

This improves:

- OSS trust
- reproducibility
- reviewability
- contributor onboarding

## 20. Initial Roadmap

### Phase 0

- finalize PRD
- finalize architecture decisions
- define canonical schema
- define benchmark plan

### Phase 1

- implement canonical store
- implement file mirrors
- implement basic ingestion
- implement reconciliation engine

### Phase 2

- implement retrieval planner
- implement chat loop
- implement Hobbes demo adapter

### Phase 3

- implement Qdrant adapter
- implement Grafeo projection
- add evaluation suite and ablations

### Phase 4

- benchmark against public baselines
- optimize hot paths
- prepare OSS release

## 21. Open Questions

- exact public project name
- exact Grafeo projection schema
- whether to support user-editable memory corrections from day one

## 22. Current Recommendation Summary

- `hybrid canon`: yes
- `modular adapters`: yes
- `SQLite as source of truth`: yes
- `file mirrors`: yes
- `Qdrant adapter`: yes, optional
- `Grafeo adapter`: yes, experimental but first-class
- `Grafeo as sole canon`: no
- `implementation default`: Python-first v1
- `Rust usage`: targeted, not default
- `embedding profiles`: quality + local
- `prompt architecture`: structured-output, schema-validated
- `benchmark-first development`: yes
