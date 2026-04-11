# Mnemograph Benchmark Methodology

Date: 2026-04-09

## Objective

Define a benchmark methodology that can honestly evaluate whether Mnemograph
improves agent memory quality instead of merely adding more components.

## Benchmarking principles

1. Evaluate behaviors, not architecture claims.
2. Measure each major subsystem with ablations.
3. Separate retrieval quality from update quality.
4. Include provenance and trust UX, not just answer accuracy.
5. Keep public datasets and custom evals side by side.
6. Compare against external baselines, not just internal ablations.

## Evaluation criteria mapping

### Memory architecture

Measure:

- clean working vs durable vs source separation
- mirror integrity
- projection lag

Signals:

- state leakage rate from working to durable
- missing provenance record rate
- projection rebuild success rate

### Extraction quality

Measure:

- entity extraction precision / recall
- SPO extraction precision / recall
- evidence span correctness
- open-question quality

### Conflict resolution

Measure:

- merge action accuracy
- conflict classification accuracy
- supersession correctness
- false merge rate

### Confidence tracking

Measure:

- calibration error
- confidence-stratified answer accuracy
- conflict-aware hedging correctness

### Retrieval strategy

Measure:

- retrieval mode classification accuracy
- precision@k by retrieval mode
- structured lookup hit rate
- semantic fallback rate

### Context assembly

Measure:

- token count
- evidence coverage
- stale-claim injection rate
- unresolved-conflict visibility rate

### Store-during-conversation

Measure:

- distillation precision / recall
- later recall success
- incorrect durable write rate

## Benchmark suites

### Public benchmarks

- `LongMemEval / LongMemEval-S`
  - long-horizon updates and memory retention
- `LoCoMo`
  - long conversation memory and reasoning
- `ConvoMem`
  - personalization and preference memory
- `MemoryBench`
  - cross-system comparison and reproducibility

### Custom Mnemograph suites

- `provenance_suite`
  - can every surfaced answer trace back to evidence and source?
- `conflict_suite`
  - can the system classify and handle typed conflicts correctly?
- `temporal_suite`
  - can the system reason over valid time vs system time?
- `entity_intelligence_suite`
  - can the system answer entity-level business questions with selective
    retrieval?
- `conversation_distillation_suite`
  - can the system extract durable facts from episodic conversations without
    over-writing noise?
- `trust_ux_suite`
  - does answer presentation match confidence and conflict state?

## External baselines

Every serious benchmark report should compare Mnemograph to at least two
baselines, not only its own ablations.

### Baseline A: naive RAG

- chunk -> embed -> retrieve -> answer
- no reconciliation
- no SPO normalization
- no typed conflicts
- no temporal validity windows

This is the minimum baseline because it approximates what most production RAG
systems actually do.

### Baseline B: structured-memory without temporal graph semantics

- structured extraction
- add/update/delete memory maintenance
- no mandatory SPO canon
- no typed conflict classes
- no bitemporal claim handling

This is the minimum competitive baseline for comparison against systems in the
Mem0 class.

## Ablation matrix

Required ablations:

- `canon_only`
- `canon_plus_vector`
- `canon_plus_graph`
- `canon_plus_vector_plus_graph`
- `no_reconciliation`
- `no_consolidation`
- `no_distillation`
- `no_temporal_grounding`
- `no_decay`

## Task matrix

| Task family | Example | Primary subsystem |
| --- | --- | --- |
| extraction | "Extract pricing facts from docs" | ingestion/extraction |
| update | "Second source changes a plan price" | reconciliation |
| conflict | "Two sources disagree on CEO" | conflict engine |
| temporal | "What was pricing last year?" | temporal reasoning |
| retrieval | "What does Acme charge for Pro?" | retrieval planner |
| provenance | "How do you know this?" | context assembly / UX |
| distillation | "User said enterprise is $500/mo" | chat + distillation |
| consolidation | "Summarize all product facts for Acme" | lifecycle |

## Metrics

### Core metrics

- answer accuracy
- exact-match claim accuracy
- claim precision / recall / F1
- conflict classification precision / recall / F1
- temporal reasoning accuracy
- provenance completeness rate
- retrieval decision accuracy
- retrieval precision@k
- context token budget
- latency p50 / p95
- cost per ingestion
- cost per query

### Calibration metrics

- Brier score
- expected calibration error
- answer accuracy by confidence band
- false-certainty rate

### Lifecycle metrics

- consolidation freshness
- duplicate active claim rate
- stale active claim rate
- archived-yet-needed retrieval miss rate

## Test execution modes

The implementation must separate deterministic correctness tests from
LLM-dependent evaluation runs.

### Deterministic tests

- run in CI on every change
- use fixtures and mocks only
- cover chunking, schema validation, confidence math, decay, mirror generation,
  deterministic reconciliation paths, and projection safety

### LLM-dependent tests

- use mocked structured outputs in CI to verify prompt contracts and plumbing
- use real model calls in a separate eval job or manual benchmark run
- cover extraction quality, retrieval classification quality, consolidation
  synthesis quality, and store-during-conversation behavior

This avoids flaky CI while still catching prompt regressions and real-model
quality drift.

## Acceptance gates

These are initial engineering gates, not final public claims.

- structured lookup should achieve `precision@5 >= 0.85` on entity-targeted
  questions and outperform semantic-only retrieval on the same slice by at
  least `0.15`
- graph-enabled runs should improve answer accuracy on relationship and
  provenance queries by at least `0.10` over the best non-graph baseline
- temporal grounding should improve time-sensitive question accuracy by at
  least `0.10` while reducing static-fact accuracy by no more than `0.02`
- confidence bands should monotonically correlate with answer accuracy and keep
  `false-certainty rate < 0.05`
- provenance completeness should be `>= 0.98` on benchmarked answers
- `cost per ingestion` and `cost per query` must be reported for every ablation
  and baseline condition

## Evaluation harness design

Each eval case should include:

- source fixtures
- expected entities
- expected claims
- expected merge actions
- expected conflicts
- expected retrieval mode
- expected answer shape
- expected provenance chain

Harness outputs should include:

- raw model output
- validated structured artifacts
- retrieval logs
- context snapshots
- answer text
- scoring report
- estimated token usage and cost summary

## Reporting

Every benchmark report should publish:

- model and prompt version
- embedding profile
- graph/vector adapters enabled
- external baseline condition
- ablation condition
- metric summary
- cost summary
- representative failures
- unresolved caveats

## Failure analysis loop

When a benchmark fails:

1. classify failure source
   - crawl
   - extraction
   - normalization
   - reconciliation
   - retrieval mode
   - ranking
   - context assembly
   - answer rendering
2. write a regression case
3. patch the subsystem
4. rerun the relevant slice before rerunning the full benchmark
