# Mnemograph Public Benchmark Integration Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run Mnemograph against LongMemEval first and MemoryAgentBench second using thin adapters around the real product path, then use the failures to drive product improvements instead of benchmark-specific hacks.

**Architecture:** Add a small `benchmarks/` layer that normalizes public benchmark inputs, replays them through the existing ingest/query engine, emits official-format prediction files, and stores reproducible artifacts. Keep benchmark-specific logic at the adapter boundary; improve extraction, retrieval, and answer grounding only when the observed failures reflect real product weaknesses.

**Tech Stack:** Python, SQLite, pytest, YAML/JSON fixtures, local Ollama-compatible LLM path, benchmark CLI runners

---

## Chunk 1: Benchmark Scaffolding

### Task 1: Create shared benchmark models and result writers

**Files:**
- Create: `projects/oss/mnemograph/src/mnemograph/benchmarks/__init__.py`
- Create: `projects/oss/mnemograph/src/mnemograph/benchmarks/common.py`
- Create: `projects/oss/mnemograph/tests/test_benchmark_common.py`

- [ ] **Step 1: Write the failing tests**

Add tests for:
- benchmark run config parsing
- result directory layout creation
- trace-record serialization
- summary metric aggregation

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest projects/oss/mnemograph/tests/test_benchmark_common.py -v`
Expected: FAIL because the benchmark package does not exist

- [ ] **Step 3: Write minimal implementation**

Create shared dataclasses/helpers for:
- benchmark run config
- benchmark trace rows
- benchmark summary rows
- result directory creation under `benchmarks/results/<benchmark>/<timestamp>/`

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest projects/oss/mnemograph/tests/test_benchmark_common.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add projects/oss/mnemograph/src/mnemograph/benchmarks projects/oss/mnemograph/tests/test_benchmark_common.py
git commit -m "feat(mnemograph): add shared benchmark scaffolding"
```

### Task 2: Expose a benchmark CLI surface

**Files:**
- Modify: `projects/oss/mnemograph/src/mnemograph/cli.py`
- Modify: `projects/oss/mnemograph/pyproject.toml`
- Create: `projects/oss/mnemograph/src/mnemograph/benchmarks/cli.py`
- Create: `projects/oss/mnemograph/tests/test_benchmark_cli.py`

- [ ] **Step 1: Write the failing tests**

Add CLI tests that expect:
- `mnemograph benchmark --help`
- `mnemograph-benchmark --help`
- benchmark selection flags for `longmemeval` and `memoryagentbench`

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest projects/oss/mnemograph/tests/test_benchmark_cli.py -v`
Expected: FAIL because the benchmark CLI entrypoints do not exist

- [ ] **Step 3: Write minimal implementation**

Add:
- top-level `benchmark` subcommand to `mnemograph`
- dedicated `mnemograph-benchmark` script entrypoint
- argument parsing for:
  - benchmark name
  - dataset path
  - result base dir
  - model/base-url
  - case limit
  - replay mode

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest projects/oss/mnemograph/tests/test_benchmark_cli.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add projects/oss/mnemograph/src/mnemograph/cli.py projects/oss/mnemograph/src/mnemograph/benchmarks/cli.py projects/oss/mnemograph/pyproject.toml projects/oss/mnemograph/tests/test_benchmark_cli.py
git commit -m "feat(mnemograph): add benchmark CLI entrypoints"
```

## Chunk 2: LongMemEval Adapter

### Task 3: Add LongMemEval dataset normalization and smoke fixtures

**Files:**
- Create: `projects/oss/mnemograph/src/mnemograph/benchmarks/longmemeval.py`
- Create: `projects/oss/mnemograph/tests/fixtures/benchmarks/longmemeval_smoke.json`
- Create: `projects/oss/mnemograph/tests/test_longmemeval_adapter.py`

- [ ] **Step 1: Write the failing tests**

Add tests for:
- loading a LongMemEval-style example
- converting benchmark history into replayable ingest steps
- producing official prediction records with `question_id` and `hypothesis`
- supporting `oracle-history` and `full-history` mode selection

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest projects/oss/mnemograph/tests/test_longmemeval_adapter.py -v`
Expected: FAIL because the adapter does not exist

- [ ] **Step 3: Write minimal implementation**

Implement:
- dataset loader
- history normalization
- replay plan generation
- prediction record formatting

Use a small checked-in smoke fixture so the adapter can be tested without the full public dataset.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest projects/oss/mnemograph/tests/test_longmemeval_adapter.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add projects/oss/mnemograph/src/mnemograph/benchmarks/longmemeval.py projects/oss/mnemograph/tests/fixtures/benchmarks/longmemeval_smoke.json projects/oss/mnemograph/tests/test_longmemeval_adapter.py
git commit -m "feat(mnemograph): add LongMemEval adapter smoke coverage"
```

### Task 4: Run LongMemEval through the real engine and persist artifacts

**Files:**
- Modify: `projects/oss/mnemograph/src/mnemograph/benchmarks/longmemeval.py`
- Create: `projects/oss/mnemograph/tests/test_longmemeval_runner.py`
- Create: `projects/oss/mnemograph/benchmarks/results/.gitkeep`

- [ ] **Step 1: Write the failing tests**

Add runner tests that expect:
- one benchmark example creates a fresh `base_dir`
- the runner ingests benchmark history through `Mnemograph`
- the runner queries through `Mnemograph.query(...)`
- artifacts are written:
  - `config.json`
  - `predictions.jsonl`
  - `traces.jsonl`
  - `summary.md`

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest projects/oss/mnemograph/tests/test_longmemeval_runner.py -v`
Expected: FAIL because the runner/artifact path is missing

- [ ] **Step 3: Write minimal implementation**

Implement the LongMemEval runner so it:
- replays benchmark history into a per-example or per-run Mnemograph base dir
- captures per-example traces:
  - ingest count
  - claim count
  - open-question count
  - retrieval mode
  - confidence
  - provenance present/absent
- writes benchmark artifacts under `benchmarks/results/longmemeval/...`

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest projects/oss/mnemograph/tests/test_longmemeval_runner.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add projects/oss/mnemograph/src/mnemograph/benchmarks/longmemeval.py projects/oss/mnemograph/tests/test_longmemeval_runner.py projects/oss/mnemograph/benchmarks/results/.gitkeep
git commit -m "feat(mnemograph): run LongMemEval through the real engine"
```

### Task 5: Add official-evaluator integration and first reproducible LongMemEval run

**Files:**
- Modify: `projects/oss/mnemograph/src/mnemograph/benchmarks/longmemeval.py`
- Modify: `projects/oss/mnemograph/README.md`
- Create: `projects/oss/mnemograph/tests/test_longmemeval_evaluator.py`

- [ ] **Step 1: Write the failing tests**

Add tests that expect:
- evaluator subprocess command construction when an official evaluator path is supplied
- graceful fallback when the evaluator is unavailable
- summary output that distinguishes:
  - benchmark raw run
  - evaluator metrics
  - self-reported local status

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest projects/oss/mnemograph/tests/test_longmemeval_evaluator.py -v`
Expected: FAIL because evaluator integration does not exist

- [ ] **Step 3: Write minimal implementation**

Add evaluator wiring and document the first benchmark command in `README.md`.

- [ ] **Step 4: Run targeted verification**

Run:
- `pytest projects/oss/mnemograph/tests/test_longmemeval_evaluator.py -v`
- `pytest projects/oss/mnemograph/tests -q`

Expected:
- evaluator tests PASS
- full suite PASS

- [ ] **Step 5: Run first benchmark slice**

Run a small local LongMemEval slice with the local Ollama path and store the outputs under `benchmarks/results/longmemeval/...`.

Expected: a reproducible first external benchmark artifact set exists, even if the score is weak.

- [ ] **Step 6: Commit**

```bash
git add projects/oss/mnemograph/src/mnemograph/benchmarks/longmemeval.py projects/oss/mnemograph/README.md projects/oss/mnemograph/tests/test_longmemeval_evaluator.py projects/oss/mnemograph/benchmarks/results
git commit -m "test(mnemograph): add first reproducible LongMemEval run"
```

## Chunk 3: Product Improvements Driven by LongMemEval

### Task 6: Add benchmark failure buckets and analysis-ready traces

**Files:**
- Modify: `projects/oss/mnemograph/src/mnemograph/benchmarks/common.py`
- Modify: `projects/oss/mnemograph/src/mnemograph/benchmarks/longmemeval.py`
- Create: `projects/oss/mnemograph/tests/test_benchmark_traces.py`

- [ ] **Step 1: Write the failing tests**

Add tests that require benchmark traces to classify failures as:
- extraction
- canon
- retrieval
- synthesis
- unsupported

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest projects/oss/mnemograph/tests/test_benchmark_traces.py -v`
Expected: FAIL because trace classification is not present

- [ ] **Step 3: Write minimal implementation**

Add trace fields and a simple failure-bucketing policy driven by observable signals rather than benchmark-specific answer heuristics.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest projects/oss/mnemograph/tests/test_benchmark_traces.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add projects/oss/mnemograph/src/mnemograph/benchmarks/common.py projects/oss/mnemograph/src/mnemograph/benchmarks/longmemeval.py projects/oss/mnemograph/tests/test_benchmark_traces.py
git commit -m "feat(mnemograph): classify benchmark failures by subsystem"
```

### Task 7: Fix the highest-value product weaknesses exposed by LongMemEval

**Files:**
- Modify: `projects/oss/mnemograph/src/mnemograph/ingest/pipeline.py`
- Modify: `projects/oss/mnemograph/src/mnemograph/retrieval/classify.py`
- Modify: `projects/oss/mnemograph/src/mnemograph/engine.py`
- Create: `projects/oss/mnemograph/tests/test_longmemeval_regressions.py`

- [ ] **Step 1: Write failing regression tests from the first benchmark run**

Capture the first real failure patterns as deterministic or mocked regressions. Target only real product weaknesses such as:
- missed temporal cues
- missed entity targeting
- bad abstention on unsupported evidence
- weak structured lookup routing

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest projects/oss/mnemograph/tests/test_longmemeval_regressions.py -v`
Expected: FAIL based on the captured benchmark failures

- [ ] **Step 3: Write minimal product improvements**

Improve the real engine behavior. Do not add benchmark-specific branches.

- [ ] **Step 4: Run targeted verification**

Run:
- `pytest projects/oss/mnemograph/tests/test_longmemeval_regressions.py -v`
- `pytest projects/oss/mnemograph/tests -q`

Expected:
- regression tests PASS
- full suite PASS

- [ ] **Step 5: Re-run the same LongMemEval slice**

Store a second result set and compare the delta in `summary.md`.

- [ ] **Step 6: Commit**

```bash
git add projects/oss/mnemograph/src/mnemograph/ingest/pipeline.py projects/oss/mnemograph/src/mnemograph/retrieval/classify.py projects/oss/mnemograph/src/mnemograph/engine.py projects/oss/mnemograph/tests/test_longmemeval_regressions.py projects/oss/mnemograph/benchmarks/results
git commit -m "fix(mnemograph): improve product behavior from LongMemEval failures"
```

## Chunk 4: MemoryAgentBench Integration

### Task 8: Add a scoped MemoryAgentBench adapter with explicit unsupported-task handling

**Files:**
- Create: `projects/oss/mnemograph/src/mnemograph/benchmarks/memoryagentbench.py`
- Create: `projects/oss/mnemograph/tests/fixtures/benchmarks/memoryagentbench_smoke.json`
- Create: `projects/oss/mnemograph/tests/test_memoryagentbench_adapter.py`

- [ ] **Step 1: Write the failing tests**

Add tests for:
- dataset normalization
- supported-task detection
- unsupported-task surfacing
- prediction/trace export

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest projects/oss/mnemograph/tests/test_memoryagentbench_adapter.py -v`
Expected: FAIL because the adapter does not exist

- [ ] **Step 3: Write minimal implementation**

Implement a first-pass adapter that supports only tasks that map cleanly onto Mnemograph's current product boundary. Mark unsupported tasks explicitly in traces and summaries.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest projects/oss/mnemograph/tests/test_memoryagentbench_adapter.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add projects/oss/mnemograph/src/mnemograph/benchmarks/memoryagentbench.py projects/oss/mnemograph/tests/fixtures/benchmarks/memoryagentbench_smoke.json projects/oss/mnemograph/tests/test_memoryagentbench_adapter.py
git commit -m "feat(mnemograph): add scoped MemoryAgentBench adapter"
```

### Task 9: Run a first MemoryAgentBench slice and capture improvement opportunities

**Files:**
- Modify: `projects/oss/mnemograph/README.md`
- Modify: `projects/oss/mnemograph/benchmarks/results`
- Create: `projects/oss/mnemograph/tests/test_memoryagentbench_runner.py`

- [ ] **Step 1: Write the failing tests**

Add runner tests that expect:
- supported MemoryAgentBench tasks run through the product path
- unsupported tasks are counted but not silently skipped
- result artifacts are written under `benchmarks/results/memoryagentbench/...`

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest projects/oss/mnemograph/tests/test_memoryagentbench_runner.py -v`
Expected: FAIL because runner wiring and result summaries are missing

- [ ] **Step 3: Write minimal implementation**

Implement the runner, update docs, and preserve the same artifact format used for LongMemEval where possible.

- [ ] **Step 4: Run targeted verification**

Run:
- `pytest projects/oss/mnemograph/tests/test_memoryagentbench_runner.py -v`
- `pytest projects/oss/mnemograph/tests -q`

Expected:
- runner tests PASS
- full suite PASS

- [ ] **Step 5: Run first MemoryAgentBench slice**

Run a reproducible local slice, save artifacts under `benchmarks/results/memoryagentbench/...`, and record the main failure buckets.

- [ ] **Step 6: Commit**

```bash
git add projects/oss/mnemograph/README.md projects/oss/mnemograph/tests/test_memoryagentbench_runner.py projects/oss/mnemograph/benchmarks/results
git commit -m "test(mnemograph): add first MemoryAgentBench run artifacts"
```

## Chunk 5: Final Verification and Handoff

### Task 10: Verify benchmark integration end to end and refresh public proof

**Files:**
- Modify: `projects/oss/mnemograph/README.md`
- Modify: `projects/oss/mnemograph/benchmarks/results`

- [ ] **Step 1: Run full deterministic verification**

Run: `pytest projects/oss/mnemograph/tests -v`
Expected: PASS

- [ ] **Step 2: Run benchmark CLI smoke checks**

Run:
- `mnemograph benchmark --help`
- `mnemograph-benchmark --help`

Expected: both commands print benchmark usage successfully

- [ ] **Step 3: Re-run the latest LongMemEval slice**

Run the benchmark with the current local Ollama path and save the artifact set.

- [ ] **Step 4: Re-run the latest MemoryAgentBench slice**

Run the supported benchmark slice and save the artifact set.

- [ ] **Step 5: Update documentation**

Document:
- how to run each benchmark
- what is self-reported vs independently validated
- what tasks are unsupported today
- what the current observed failure buckets are

- [ ] **Step 6: Commit**

```bash
git add projects/oss/mnemograph/README.md projects/oss/mnemograph/benchmarks/results
git commit -m "docs(mnemograph): document public benchmark runs and limitations"
```
