# Mnemograph Public Benchmark Integration Design

Date: 2026-04-11

## Objective

Integrate Mnemograph with public memory benchmarks in a way that measures the
real product, not a benchmark-only fork of the product. The first targets are
LongMemEval and MemoryAgentBench, in that order.

## Problem statement

Mnemograph currently has strong local proof artifacts:

- deterministic tests
- golden eval scenarios
- narrated demo runs

Those artifacts are useful for regression protection, but they are still
self-reported. We need public benchmark runs that answer a harder question:
does the same canon, extraction, reconciliation, retrieval, and answer path
hold up against external tasks without introducing benchmark-specific
shortcuts?

## Design principles

1. Benchmark adapters must wrap the real product path.
2. No benchmark-only engine logic inside canonical memory or retrieval.
3. Use official dataset formats and official evaluators wherever practical.
4. Separate subsystem diagnosis:
   - extraction failures
   - reconciliation/canon failures
   - retrieval failures
   - answer-synthesis failures
5. Treat benchmark outputs as self-reported reproducible artifacts until they
   are independently validated.
6. Optimize product quality under benchmark pressure, not benchmark score in
   isolation.

## Benchmark order

### LongMemEval first

LongMemEval is the better first integration because it supports a thin
prediction workflow:

- load official examples
- run the system under test
- emit predictions in the official format
- run the official evaluator

That makes it easier to get a credible first external result without building a
heavy framework bridge first.

### MemoryAgentBench second

MemoryAgentBench is more agent-framework-heavy and should come after the first
LongMemEval pass. The first supported slice should focus on the competencies
closest to Mnemograph's strengths:

- accurate retrieval
- test-time learning
- conflict-sensitive memory updates

We should not commit to full benchmark coverage until the task interfaces are
mapped cleanly to Mnemograph's product path.

## Architecture

Add a new benchmark layer inside Mnemograph:

```text
benchmarks/
  common.py
  cli.py
  longmemeval.py
  memoryagentbench.py
  results/
```

This layer does only benchmark adaptation:

- dataset loading and normalization
- replay orchestration
- benchmark-native prediction export
- evaluator invocation
- run artifact storage

The benchmark layer must call the existing product surfaces:

- `Mnemograph.ingest_text(...)`
- `Mnemograph.ingest_candidates(...)` only when the benchmark itself provides
  structured gold or oracle-style memory state
- `Mnemograph.query(...)`

It must not add alternative retrieval or answer code paths.

## LongMemEval adapter design

### Inputs

- official dataset file(s)
- benchmark mode:
  - `oracle-history`
  - `full-history`
- model config:
  - local Ollama-compatible endpoint
  - model name
- run config:
  - result directory
  - optional case limit

### Replay modes

#### Oracle-history

Use the benchmark's evidence-bearing history slice when available. This mode is
useful for measuring retrieval, reconciliation, and answer quality without
letting noisy upstream extraction dominate the first run.

#### Full-history

Replay the benchmark's full memory-relevant history through the normal product
path. This is the more realistic mode and should become the primary mode once
the adapter is stable.

### Outputs

Per official example:

- `question_id`
- `hypothesis`

Additional Mnemograph-side artifacts:

- retrieval mode used
- number of claims retrieved
- confidence score
- provenance availability
- crawl/ingest summary where relevant
- error category if the run fails

### Result storage

Store runs under a dedicated benchmark artifact tree such as:

```text
benchmarks/results/longmemeval/<timestamp>/
  config.json
  predictions.jsonl
  traces.jsonl
  evaluator_output.json
  summary.md
```

This preserves reproducibility and makes later optimization passes diagnosable.

## MemoryAgentBench adapter design

### Scope

Start with a scoped adapter that supports only the benchmark slices that can be
mapped cleanly onto Mnemograph today.

### Supported first-pass task families

- retrieval-heavy tasks
- memory update tasks
- contradiction or correction-sensitive tasks

### Deferred scope

Do not promise full agent-loop or tool-use parity with the benchmark's richest
tasks until the task contract is mapped. If a MemoryAgentBench task expects a
broader agent runtime than Mnemograph currently exposes, mark it unsupported
instead of silently approximating it.

## Observability and failure analysis

Every benchmark run should emit enough data to attribute failure by subsystem.

Required per-example trace fields:

- benchmark name
- benchmark example ID
- ingestion mode
- ingest count
- extracted claim count
- open-question count
- retrieval mode
- retrieved claim IDs
- confidence
- provenance present or absent
- final answer
- evaluator result when available
- failure bucket:
  - extraction
  - canon
  - retrieval
  - synthesis
  - unsupported

This is necessary because benchmark scores alone will not tell us whether poor
results are caused by extraction quality, canon semantics, or answer wording.

## Product optimization policy

### Allowed optimizations

- better extraction filtering for messy real-world inputs
- stronger qualifier handling
- better entity targeting
- better retrieval planning
- better confidence-aware answer shaping
- better abstention when evidence is weak

### Disallowed optimizations

- benchmark-specific retrieval branches
- hard-coded answer patterns for known tasks
- bypassing reconciliation to inflate recall
- turning off filtering just to preserve noisy benchmark text
- a separate benchmark-only engine path

## Testing strategy

### Deterministic tests

Add unit tests for:

- dataset normalization
- replay sequencing
- official prediction-file formatting
- result-directory artifact writing
- unsupported-task classification

### Smoke benchmarks

Add tiny smoke slices for:

- one or two LongMemEval examples
- one or two MemoryAgentBench examples

These should prove the adapter wiring before full runs.

### Live benchmark runs

Run full benchmark commands outside normal CI and store the outputs as local
proof artifacts. Treat them as self-reported until independently validated.

## Success criteria

### Milestone A: LongMemEval

- official-format predictions generated from the real Mnemograph engine
- official evaluator runs successfully when available
- result artifacts stored under `benchmarks/results/longmemeval/...`
- at least one product-improving optimization pass performed from observed
  failures

### Milestone B: MemoryAgentBench

- scoped benchmark adapter working on compatible tasks
- result artifacts stored under `benchmarks/results/memoryagentbench/...`
- unsupported tasks surfaced explicitly, not silently approximated
- at least one product-improving optimization pass performed from observed
  failures

## Risks

### Extraction becomes the dominant failure source

This is likely. The benchmark layer should make that visible rather than hiding
it behind overall answer accuracy.

### Benchmark task contracts may not match product boundaries

MemoryAgentBench especially may expect a fuller agent runtime. We should prefer
honest partial support over low-credibility emulation.

### Public scores may initially look weak

That is acceptable. The first goal is a credible baseline run and subsystem
diagnosis, not a flattering number.

## Non-goals

- replacing the existing golden eval harness
- claiming SOTA from self-run benchmark outputs
- building a second memory engine optimized for benchmark tasks
- widening adapter scope beyond LongMemEval and MemoryAgentBench in this slice
