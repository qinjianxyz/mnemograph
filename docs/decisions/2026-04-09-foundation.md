# Decision Log: Foundation Choices

Date: 2026-04-09

## Status

Accepted for the current PRD draft.

## Decision 1: Public OSS project, not Enterprise OS-specific product

Mnemograph should be useful to the outside world. The first demo adapter may be
company or entity intelligence, but the engine itself should remain general.

## Decision 2: Hybrid canon

Canonical memory state lives in a structured local store and is mirrored into
human-reviewable files.

Rationale:

- structured updates need transactions and schema control
- human review needs readable artifacts
- git diffs are useful but should not be the only storage mechanism

## Decision 2b: Semi-closed emergent predicate registry

Durable claims use mandatory SPO normalization, but the predicate vocabulary is
not fully fixed upfront.

Rationale:

- fully closed ontologies suffer from cold-start failure
- fully open predicates create synonym sprawl and break reconciliation
- a normalization queue plus periodic clustering gives us stronger merge quality
  without freezing the ontology too early

## Decision 3: Modular retrieval plane

Vector and graph systems are adapters, not mandatory dependencies for the
default install.

Rationale:

- preserves local-first adoption
- keeps optional accelerators optional
- allows benchmark ablations

## Decision 4: Grafeo is first-class, but not sole canon

Grafeo should be adopted as a serious graph projection target because
provenance, contradiction edges, and temporal reasoning are core memory
problems.

Grafeo should not become the only memory authority in v1.

Rationale:

- young ecosystem and sparse public documentation
- attractive fit for relational memory reasoning
- lower risk when used as projection over canonical state

## Decision 5: Python-first v1 with targeted Rust usage

Use Python for the v1 engine because the memory, embeddings, crawler, LLM, and
evaluation ecosystems are Python-native and the quality bottleneck is iteration
speed, not hot-path latency.

Use Rust selectively where it compounds:

- Grafeo itself
- future projection workers
- future embeddable / WASM-friendly components
- profiled hot paths if later justified

## Decision 6: Benchmark-first claims

The system should not claim to be SOTA based on architecture alone.

Required evidence includes:

- public benchmark runs
- custom evals for provenance and contradiction handling
- ablation comparisons
- external baseline comparisons
- cost reporting alongside quality metrics

## Decision 7: Retrieval policy defaults

Default to structured lookup when an entity is detectable. Use semantic search
for exploratory questions. Use graph traversal for relationships and provenance.
Use multi-path retrieval for temporal comparison and compound reasoning.

V1 should implement this policy with an LLM classifier that emits structured
retrieval decisions for evaluation.

## Decision 8: Conflict posture

Be bold on temporal conflicts, conservative on entity resolution, and honest on
value/source-quality conflicts.

This preserves correctness while minimizing unnecessary human review.

The default reconciliation path should remain deterministic:

- normalized SPO matching
- valid-time comparison
- typed conflict policy application

LLM assistance is fallback-only for ambiguous predicate similarity and entity
resolution cases.

## Decision 9: Trust UX

Surface uncertainty proactively, but keep the full provenance chain on demand
instead of overwhelming the default answer path.

## Decision 10: Retrieval and ingestion defaults

Use an LLM retrieval classifier in v1, but bias it toward structured lookup when
an entity is detectable.

Use multi-pass extraction as a logical architecture, while combining compatible
passes and batching chunks in execution so ingest cost does not explode.

Support named embedding profiles instead of a single vague model choice:

- quality-oriented hosted profile
- OSS-friendly local profile

## Decision 11: Python API before CLI

The primary implementation surface should be a Python API class. The CLI exists
for demos and manual inspection, but it should stay a thin wrapper over the
same engine methods used by tests and downstream integrators.

## Design influences

- Letta: inspectable memory surfaces
- Mem0: explicit memory reconciliation actions
- Graphiti / Zep: temporal graph reasoning
- Supermemory: chunk-aware ingestion, relational versioning, benchmark rigor
- LangGraph: clean long-term memory abstractions
- public review feedback: mandatory SPO, compositional confidence, consolidation,
  distillation, decay, explicit retrieval decision policy
