# Mnemograph Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a production-grade first implementation of Mnemograph that satisfies the Hobbes memory requirements while preserving the broader public OSS architecture.

**Architecture:** Python-first v1 with a SQLite canonical store, file mirrors, optional Qdrant and Grafeo projections, and benchmark-first validation. Implement the system in thin vertical slices so each slice can be tested end-to-end before adding the next subsystem.

**Tech Stack:** Python, SQLite, Pydantic or equivalent typed schemas, pytest, optional Qdrant, optional Grafeo, GPT-5.4 structured outputs

**Test Policy:** Deterministic tests run in CI with fixtures and mocks. LLM-dependent behaviors use mocked outputs in CI and real-model runs in the eval harness, not the default unit-test path.

---

## Chunk 1: Foundation

### Task 0.5: Package bootstrap and editable install

**Files:**
- Create: `projects/oss/mnemograph/pyproject.toml`
- Create: `projects/oss/mnemograph/tests/test_package_bootstrap.py`

- [ ] **Step 1: Write the failing test**

Write a test that imports `mnemograph` from the editable package install and
verifies the CLI entrypoint resolves.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest projects/oss/mnemograph/tests/test_package_bootstrap.py -v`
Expected: FAIL because package metadata and entrypoints do not exist

- [ ] **Step 3: Write minimal implementation**

Create `pyproject.toml`, define the package metadata, configure the `src/`
layout, and add a `[project.scripts]` entry for the CLI.

- [ ] **Step 4: Install package in editable mode**

Run: `pip install -e projects/oss/mnemograph`
Expected: editable install succeeds and exposes the package to pytest

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest projects/oss/mnemograph/tests/test_package_bootstrap.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add projects/oss/mnemograph/pyproject.toml projects/oss/mnemograph/tests/test_package_bootstrap.py
git commit -m "feat(mnemograph): bootstrap package metadata and editable install"
```

### Task 1: Project scaffold and canonical file map

**Files:**
- Create: `projects/oss/mnemograph/src/mnemograph/__init__.py`
- Create: `projects/oss/mnemograph/src/mnemograph/config.py`
- Create: `projects/oss/mnemograph/src/mnemograph/paths.py`
- Create: `projects/oss/mnemograph/tests/test_paths.py`

- [ ] **Step 1: Write the failing test**

```python
from mnemograph.paths import mirror_paths


def test_mirror_paths_match_hobbes_layout():
    paths = mirror_paths("memory")
    assert paths["working"].endswith("memory/working")
    assert paths["knowledge"].endswith("memory/knowledge")
    assert paths["sources"].endswith("memory/sources")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest projects/oss/mnemograph/tests/test_paths.py -v`
Expected: FAIL because `mnemograph.paths` does not exist

- [ ] **Step 3: Write minimal implementation**

Implement path helpers and config loading for the project root, canonical db,
and mirror directories.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest projects/oss/mnemograph/tests/test_paths.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add projects/oss/mnemograph/src/mnemograph projects/oss/mnemograph/tests/test_paths.py
git commit -m "feat(mnemograph): scaffold core package and mirror path helpers"
```

### Task 2: Canonical schema and SQLite bootstrap

**Files:**
- Create: `projects/oss/mnemograph/src/mnemograph/schema.py`
- Create: `projects/oss/mnemograph/src/mnemograph/db.py`
- Create: `projects/oss/mnemograph/tests/test_schema_bootstrap.py`

- [ ] **Step 1: Write the failing test**

```python
import sqlite3

from mnemograph.db import bootstrap_db


def test_bootstrap_creates_core_tables(tmp_path):
    db_path = tmp_path / "memory.db"
    bootstrap_db(db_path)
    assert db_path.exists()
    conn = sqlite3.connect(db_path)
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    assert "claims" in tables
    assert "extraction_runs" in tables
    assert "context_snapshots" in tables
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest projects/oss/mnemograph/tests/test_schema_bootstrap.py -v`
Expected: FAIL because bootstrap does not exist

- [ ] **Step 3: Write minimal implementation**

Create the initial SQLite schema for sources, chunks, predicates, claims,
evidence, extraction runs, conflicts, retrieval runs, context snapshots, and
conversation turns.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest projects/oss/mnemograph/tests/test_schema_bootstrap.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add projects/oss/mnemograph/src/mnemograph/schema.py projects/oss/mnemograph/src/mnemograph/db.py projects/oss/mnemograph/tests/test_schema_bootstrap.py
git commit -m "feat(mnemograph): add canonical sqlite bootstrap"
```

## Chunk 2: Ingestion and Extraction

### Task 3: Source registration and chunking

**Files:**
- Create: `projects/oss/mnemograph/src/mnemograph/ingest/register.py`
- Create: `projects/oss/mnemograph/src/mnemograph/ingest/chunk.py`
- Create: `projects/oss/mnemograph/tests/test_source_registration.py`
- Create: `projects/oss/mnemograph/tests/test_chunking.py`

- [ ] **Step 1: Write the failing tests**

Write tests for:
- normalized URL registration
- content hash stability
- chunk boundary preservation

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest projects/oss/mnemograph/tests/test_source_registration.py projects/oss/mnemograph/tests/test_chunking.py -v`
Expected: FAIL because the ingest modules do not exist

- [ ] **Step 3: Write minimal implementation**

Implement source registration, hash computation, and semantic-boundary chunking.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest projects/oss/mnemograph/tests/test_source_registration.py projects/oss/mnemograph/tests/test_chunking.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add projects/oss/mnemograph/src/mnemograph/ingest projects/oss/mnemograph/tests/test_source_registration.py projects/oss/mnemograph/tests/test_chunking.py
git commit -m "feat(mnemograph): add source registration and chunking"
```

### Task 4: Crawl policy and acquisition

**Files:**
- Create: `projects/oss/mnemograph/src/mnemograph/ingest/crawl.py`
- Create: `projects/oss/mnemograph/tests/test_crawl_policy.py`

- [ ] **Step 1: Write the failing test**

Write tests for:
- same-domain restriction
- page depth limit
- page count limit
- robots-aware behavior

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest projects/oss/mnemograph/tests/test_crawl_policy.py -v`
Expected: FAIL because crawl policy implementation does not exist

- [ ] **Step 3: Write minimal implementation**

Implement crawl planning, URL filtering, and fetch-mode selection.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest projects/oss/mnemograph/tests/test_crawl_policy.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add projects/oss/mnemograph/src/mnemograph/ingest/crawl.py projects/oss/mnemograph/tests/test_crawl_policy.py
git commit -m "feat(mnemograph): add crawl policy and acquisition planner"
```

### Task 4.5: LLM client abstraction and test backends

**Files:**
- Create: `projects/oss/mnemograph/src/mnemograph/llm/client.py`
- Create: `projects/oss/mnemograph/src/mnemograph/llm/mock.py`
- Create: `projects/oss/mnemograph/tests/test_llm_client.py`

- [ ] **Step 1: Write the failing test**

Write tests that validate:
- mock backend returns schema-valid structured output
- OpenAI-compatible backend reads config without live network calls
- extraction and retrieval callers can depend on the same interface

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest projects/oss/mnemograph/tests/test_llm_client.py -v`
Expected: FAIL because the LLM client abstraction does not exist

- [ ] **Step 3: Write minimal implementation**

Implement a small LLM client interface with:
- mock backend for unit tests
- OpenAI-compatible backend for integration tests and real runs
- config-driven model selection and API key loading

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest projects/oss/mnemograph/tests/test_llm_client.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add projects/oss/mnemograph/src/mnemograph/llm projects/oss/mnemograph/tests/test_llm_client.py
git commit -m "feat(mnemograph): add llm client abstraction and mock backend"
```

### Task 5: Structured extraction contracts

**Files:**
- Create: `projects/oss/mnemograph/src/mnemograph/prompts/extract.py`
- Create: `projects/oss/mnemograph/src/mnemograph/prompts/contracts.py`
- Create: `projects/oss/mnemograph/tests/test_extraction_contracts.py`

- [ ] **Step 1: Write the failing test**

Write tests that validate:
- mandatory SPO fields
- provisional predicate support
- evidence span schema
- extraction run reference fields

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest projects/oss/mnemograph/tests/test_extraction_contracts.py -v`
Expected: FAIL because contracts do not exist

- [ ] **Step 3: Write minimal implementation**

Implement prompt builders and strict structured-output contracts.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest projects/oss/mnemograph/tests/test_extraction_contracts.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add projects/oss/mnemograph/src/mnemograph/prompts projects/oss/mnemograph/tests/test_extraction_contracts.py
git commit -m "feat(mnemograph): add extraction prompt contracts"
```

### Task 5.5: Integration checkpoint for ingest to canon

**Files:**
- Create: `projects/oss/mnemograph/tests/integration/test_ingest_to_canon.py`

- [ ] **Step 1: Write the failing integration test**

Use a fixture source and mock LLM output to verify:
- source registration succeeds
- chunking succeeds
- extraction run is recorded
- at least one validated claim is written to canon

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest projects/oss/mnemograph/tests/integration/test_ingest_to_canon.py -v`
Expected: FAIL because the ingestion slices are not yet composed

- [ ] **Step 3: Compose the existing implementation**

Wire source registration, chunking, extraction contracts, and DB writes into a
minimal ingest path.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest projects/oss/mnemograph/tests/integration/test_ingest_to_canon.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add projects/oss/mnemograph/tests/integration/test_ingest_to_canon.py projects/oss/mnemograph/src/mnemograph
git commit -m "test(mnemograph): add first ingest-to-canon integration checkpoint"
```

## Chunk 3: Reconciliation and Lifecycle

### Task 6: Predicate registry and normalization queue

**Files:**
- Create: `projects/oss/mnemograph/src/mnemograph/reconcile/predicates.py`
- Create: `projects/oss/mnemograph/tests/test_predicate_registry.py`

- [ ] **Step 1: Write the failing test**

Write tests for:
- canonical predicate reuse
- provisional predicate creation
- merge of provisional to canonical

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest projects/oss/mnemograph/tests/test_predicate_registry.py -v`
Expected: FAIL because registry does not exist

- [ ] **Step 3: Write minimal implementation**

Implement the semi-closed predicate registry and normalization queue behavior.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest projects/oss/mnemograph/tests/test_predicate_registry.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add projects/oss/mnemograph/src/mnemograph/reconcile/predicates.py projects/oss/mnemograph/tests/test_predicate_registry.py
git commit -m "feat(mnemograph): add predicate registry lifecycle"
```

### Task 7: Merge action engine and typed conflict policy

**Files:**
- Create: `projects/oss/mnemograph/src/mnemograph/reconcile/engine.py`
- Create: `projects/oss/mnemograph/src/mnemograph/reconcile/conflicts.py`
- Create: `projects/oss/mnemograph/tests/test_merge_actions.py`
- Create: `projects/oss/mnemograph/tests/test_conflict_policy.py`

- [ ] **Step 1: Write the failing tests**

Cover:
- temporal auto-supersede
- strict-higher-trust value supersede
- entity conflict review queue
- source-quality conflict honesty

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest projects/oss/mnemograph/tests/test_merge_actions.py projects/oss/mnemograph/tests/test_conflict_policy.py -v`
Expected: FAIL because reconciliation engine does not exist

- [ ] **Step 3: Write minimal implementation**

Implement merge matching, conflict typing, and default resolution policy with a
deterministic-first path:
- normalized SPO matching
- valid-time comparison
- typed conflict policy application
- LLM fallback only for ambiguous predicate similarity and entity resolution

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest projects/oss/mnemograph/tests/test_merge_actions.py projects/oss/mnemograph/tests/test_conflict_policy.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add projects/oss/mnemograph/src/mnemograph/reconcile projects/oss/mnemograph/tests/test_merge_actions.py projects/oss/mnemograph/tests/test_conflict_policy.py
git commit -m "feat(mnemograph): add reconciliation and conflict engine"
```

### Task 7.5: Integration checkpoint for conflicting sources

**Files:**
- Create: `projects/oss/mnemograph/tests/integration/test_conflicting_sources.py`

- [ ] **Step 1: Write the failing integration test**

Use two fixture sources that disagree on a value and verify:
- both claims are preserved
- a typed conflict record is created
- the active claim follows the configured policy

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest projects/oss/mnemograph/tests/integration/test_conflicting_sources.py -v`
Expected: FAIL because the reconciliation pipeline is not yet composed

- [ ] **Step 3: Compose the existing implementation**

Wire the ingest path and reconciliation engine together for a two-source update
flow.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest projects/oss/mnemograph/tests/integration/test_conflicting_sources.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add projects/oss/mnemograph/tests/integration/test_conflicting_sources.py projects/oss/mnemograph/src/mnemograph
git commit -m "test(mnemograph): add conflicting-source integration checkpoint"
```

### Task 8a: Confidence scoring

**Files:**
- Create: `projects/oss/mnemograph/src/mnemograph/lifecycle/confidence.py`
- Create: `projects/oss/mnemograph/tests/test_confidence.py`

- [ ] **Step 1: Write the failing tests**

Cover:
- component-level clamping in confidence composition
- confidence band monotonicity on controlled fixtures

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest projects/oss/mnemograph/tests/test_confidence.py -v`
Expected: FAIL because the confidence module does not exist

- [ ] **Step 3: Write minimal implementation**

Implement the clamped confidence composition and calibration helpers.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest projects/oss/mnemograph/tests/test_confidence.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add projects/oss/mnemograph/src/mnemograph/lifecycle/confidence.py projects/oss/mnemograph/tests/test_confidence.py
git commit -m "feat(mnemograph): add confidence scoring"
```

### Task 8b: Consolidation and summary maintenance

**Files:**
- Create: `projects/oss/mnemograph/src/mnemograph/lifecycle/consolidate.py`
- Create: `projects/oss/mnemograph/tests/test_consolidation.py`

- [ ] **Step 1: Write the failing test**

Cover:
- consolidation trigger after more than 10 domain-aligned atomic claims
- summary claim creation with provenance links
- atomic claims excluded from default retrieval after consolidation

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest projects/oss/mnemograph/tests/test_consolidation.py -v`
Expected: FAIL because consolidation does not exist

- [ ] **Step 3: Write minimal implementation**

Implement consolidation triggers, summary claim materialization, and
supersession metadata.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest projects/oss/mnemograph/tests/test_consolidation.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add projects/oss/mnemograph/src/mnemograph/lifecycle/consolidate.py projects/oss/mnemograph/tests/test_consolidation.py
git commit -m "feat(mnemograph): add claim consolidation lifecycle"
```

### Task 8c: Episodic-to-semantic distillation

**Files:**
- Create: `projects/oss/mnemograph/src/mnemograph/lifecycle/distill.py`
- Create: `projects/oss/mnemograph/tests/test_distillation.py`

- [ ] **Step 1: Write the failing test**

Cover:
- durable fact extraction from conversation turns
- non-durable chatter ignored
- distillation trigger at 15 turns

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest projects/oss/mnemograph/tests/test_distillation.py -v`
Expected: FAIL because distillation does not exist

- [ ] **Step 3: Write minimal implementation**

Implement episodic-to-semantic candidate extraction and the distillation
trigger policy.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest projects/oss/mnemograph/tests/test_distillation.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add projects/oss/mnemograph/src/mnemograph/lifecycle/distill.py projects/oss/mnemograph/tests/test_distillation.py
git commit -m "feat(mnemograph): add episodic-to-semantic distillation"
```

### Task 8d: Decay and archival policy

**Files:**
- Create: `projects/oss/mnemograph/src/mnemograph/lifecycle/decay.py`
- Create: `projects/oss/mnemograph/tests/test_decay.py`

- [ ] **Step 1: Write the failing test**

Cover:
- low-confidence never-retrieved claims decay over time
- user-confirmed and historical claims do not decay
- archival threshold at `< 0.10` confidence

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest projects/oss/mnemograph/tests/test_decay.py -v`
Expected: FAIL because decay does not exist

- [ ] **Step 3: Write minimal implementation**

Implement the configurable decay schedule and archival status transition.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest projects/oss/mnemograph/tests/test_decay.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add projects/oss/mnemograph/src/mnemograph/lifecycle/decay.py projects/oss/mnemograph/tests/test_decay.py
git commit -m "feat(mnemograph): add decay and archival lifecycle"
```

## Chunk 4: Retrieval, Context, and Chat

### Task 9: Retrieval classifier and planner

**Files:**
- Create: `projects/oss/mnemograph/src/mnemograph/retrieval/classify.py`
- Create: `projects/oss/mnemograph/src/mnemograph/retrieval/plan.py`
- Create: `projects/oss/mnemograph/tests/test_retrieval_classifier.py`

- [ ] **Step 1: Write the failing test**

Write tests covering:
- direct meta-turn -> `NO_RETRIEVAL`
- recent recall -> `WORKING_MEMORY_ONLY`
- entity-targeted pricing query -> `STRUCTURED_LOOKUP`
- provenance query -> `GRAPH_TRAVERSAL`
- zero-hit structured lookup -> semantic fallback

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest projects/oss/mnemograph/tests/test_retrieval_classifier.py -v`
Expected: FAIL because retrieval planner does not exist

- [ ] **Step 3: Write minimal implementation**

Implement LLM classifier contracts and deterministic fallback heuristics.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest projects/oss/mnemograph/tests/test_retrieval_classifier.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add projects/oss/mnemograph/src/mnemograph/retrieval projects/oss/mnemograph/tests/test_retrieval_classifier.py
git commit -m "feat(mnemograph): add retrieval classifier and planner"
```

### Task 10: Context assembly and provenance rendering

**Files:**
- Create: `projects/oss/mnemograph/src/mnemograph/context/assemble.py`
- Create: `projects/oss/mnemograph/src/mnemograph/context/render.py`
- Create: `projects/oss/mnemograph/tests/test_context_assembly.py`

- [ ] **Step 1: Write the failing test**

Cover:
- summary-first assembly
- conflict visibility
- provenance chain rendering on demand

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest projects/oss/mnemograph/tests/test_context_assembly.py -v`
Expected: FAIL because context assembly does not exist

- [ ] **Step 3: Write minimal implementation**

Implement assembled context generation and expandable provenance views.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest projects/oss/mnemograph/tests/test_context_assembly.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add projects/oss/mnemograph/src/mnemograph/context projects/oss/mnemograph/tests/test_context_assembly.py
git commit -m "feat(mnemograph): add context assembly and provenance rendering"
```

### Task 11: Python API surface, CLI wrapper, and Hobbes mirror outputs

**Files:**
- Create: `projects/oss/mnemograph/src/mnemograph/engine.py`
- Create: `projects/oss/mnemograph/src/mnemograph/chat/loop.py`
- Create: `projects/oss/mnemograph/src/mnemograph/mirror/write.py`
- Create: `projects/oss/mnemograph/tests/test_engine_api.py`
- Create: `projects/oss/mnemograph/tests/test_chat_loop.py`
- Create: `projects/oss/mnemograph/tests/test_mirror_outputs.py`

- [ ] **Step 1: Write the failing tests**

Cover:
- `Mnemograph.ingest(...)`
- `Mnemograph.ingest_text(...)`
- `Mnemograph.query(...)`
- bounded session history
- store-during-conversation
- `memory/working/active_context.json`
- `memory/working/session_history.json`

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest projects/oss/mnemograph/tests/test_engine_api.py projects/oss/mnemograph/tests/test_chat_loop.py projects/oss/mnemograph/tests/test_mirror_outputs.py -v`
Expected: FAIL because the engine API, chat wrapper, and mirror modules do not exist

- [ ] **Step 3: Write minimal implementation**

Implement the `Mnemograph` Python API first, then build the CLI chat loop as a
thin wrapper over it. Add session state handling and mirror projection writes.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest projects/oss/mnemograph/tests/test_engine_api.py projects/oss/mnemograph/tests/test_chat_loop.py projects/oss/mnemograph/tests/test_mirror_outputs.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add projects/oss/mnemograph/src/mnemograph/engine.py projects/oss/mnemograph/src/mnemograph/chat projects/oss/mnemograph/src/mnemograph/mirror projects/oss/mnemograph/tests/test_engine_api.py projects/oss/mnemograph/tests/test_chat_loop.py projects/oss/mnemograph/tests/test_mirror_outputs.py
git commit -m "feat(mnemograph): add engine api, cli wrapper, and mirror outputs"
```

## Chunk 5: Adapters and Evals

### Task 12: Optional Qdrant and Grafeo projections

**Files:**
- Create: `projects/oss/mnemograph/src/mnemograph/adapters/qdrant.py`
- Create: `projects/oss/mnemograph/src/mnemograph/adapters/grafeo.py`
- Create: `projects/oss/mnemograph/tests/test_adapter_projections.py`

- [ ] **Step 1: Write the failing test**

Write tests for:
- canonical claim projection payload shape
- adapter failure leaves canon intact

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest projects/oss/mnemograph/tests/test_adapter_projections.py -v`
Expected: FAIL because adapters do not exist

- [ ] **Step 3: Write minimal implementation**

Implement projection contracts and retry-safe adapter boundaries.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest projects/oss/mnemograph/tests/test_adapter_projections.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add projects/oss/mnemograph/src/mnemograph/adapters projects/oss/mnemograph/tests/test_adapter_projections.py
git commit -m "feat(mnemograph): add qdrant and grafeo projection adapters"
```

### Task 13: Benchmark harness and first golden scenarios

**Files:**
- Create: `projects/oss/mnemograph/src/mnemograph/evals/harness.py`
- Create: `projects/oss/mnemograph/src/mnemograph/evals/baselines.py`
- Create: `projects/oss/mnemograph/evals/golden/company_pricing_conflict.yaml`
- Create: `projects/oss/mnemograph/evals/golden/conversation_distillation.yaml`
- Create: `projects/oss/mnemograph/tests/test_eval_harness.py`

- [ ] **Step 1: Write the failing tests**

Write tests that:
- load a golden eval case and score expected fields
- run the naive RAG baseline
- run the structured-memory baseline
- emit latency and cost fields in the report

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest projects/oss/mnemograph/tests/test_eval_harness.py -v`
Expected: FAIL because the harness does not exist

- [ ] **Step 3: Write minimal implementation**

Implement eval loading, scenario execution glue, baseline runners, and report
output with cost and latency summaries.

- [ ] **Step 3.5: Separate CI-safe tests from live-model eval runs**

Keep fixture-based and mocked eval-harness tests in the normal test suite.
Reserve real-model benchmark executions for a separate eval command or job so
CI stays deterministic.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest projects/oss/mnemograph/tests/test_eval_harness.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add projects/oss/mnemograph/src/mnemograph/evals projects/oss/mnemograph/evals projects/oss/mnemograph/tests/test_eval_harness.py
git commit -m "feat(mnemograph): add eval harness and golden scenarios"
```

## Chunk 6: End-to-End Demo and Verification

### Task 14: Demo script

**Files:**
- Create: `projects/oss/mnemograph/scripts/demo_hobbes.py`
- Create: `projects/oss/mnemograph/tests/test_demo_script.py`

- [ ] **Step 1: Write the failing test**

Write a smoke test that the demo script runs through:
- initial URL ingest
- second-source conflict
- chat correction
- later recall

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest projects/oss/mnemograph/tests/test_demo_script.py -v`
Expected: FAIL because the demo script does not exist

- [ ] **Step 3: Write minimal implementation**

Implement a reproducible demo flow using a fixed company fixture or a controlled
real-company path.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest projects/oss/mnemograph/tests/test_demo_script.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add projects/oss/mnemograph/scripts/demo_hobbes.py projects/oss/mnemograph/tests/test_demo_script.py
git commit -m "feat(mnemograph): add end-to-end demo script"
```

### Task 15: Full project verification

**Files:**
- Modify: `projects/oss/mnemograph/README.md`

- [ ] **Step 1: Run targeted project test suite**

Run: `pytest projects/oss/mnemograph/tests -q`
Expected: PASS

- [ ] **Step 2: Run demo smoke flow**

Run: `python projects/oss/mnemograph/scripts/demo_hobbes.py`
Expected: completes and writes Hobbes-compatible mirrors

- [ ] **Step 3: Review docs against implementation**

Check:
- README setup instructions
- PRD alignment
- benchmark methodology coverage

- [ ] **Step 4: Commit**

```bash
git add projects/oss/mnemograph
git commit -m "feat(mnemograph): complete first end-to-end implementation slice"
```

Plan complete and saved to `projects/oss/mnemograph/docs/plans/2026-04-09-mnemograph-implementation-plan.md`. Ready to execute?
