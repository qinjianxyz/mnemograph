# Mnemograph Adversarial Rigor Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Strengthen Mnemograph where the research feedback is directionally correct: messy-source extraction quality and adversarial proof discipline.

**Architecture:** Expand the eval harness first so the harder failure modes become executable acceptance criteria, then harden extraction, retrieval reporting, and baseline reporting only enough to make those new adversarial cases pass. Keep the canonical SQLite-first architecture intact; optimize the path from noisy source material to trustworthy claims rather than adding new storage layers.

**Tech Stack:** Python, SQLite, pytest, YAML golden cases, local Ollama-compatible LLM path

---

## Chunk 1: Adversarial Evaluation Surface

### Task 1: Add harder golden cases and richer eval assertions

**Files:**
- Modify: `projects/oss/mnemograph/src/mnemograph/evals/harness.py`
- Create: `projects/oss/mnemograph/evals/golden/messy_marketing_page.yaml`
- Create: `projects/oss/mnemograph/evals/golden/qualified_pricing_scope.yaml`
- Create: `projects/oss/mnemograph/evals/golden/source_disagreement.yaml`
- Create: `projects/oss/mnemograph/tests/test_eval_harness.py`

- [ ] **Step 1: Write the failing tests**

Add tests that require the harness to score:
- open-question expectations
- minimum/maximum active claim counts
- conflict-type expectations
- changelog contains expectations

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_eval_harness.py -v`
Expected: FAIL because the new assertion types are unsupported

- [ ] **Step 3: Write minimal implementation**

Extend the harness to score the new assertions and add three new golden scenarios that stress:
- marketing-noise filtering
- scoped pricing extraction
- comparable-source disagreement handling

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_eval_harness.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/mnemograph/evals/harness.py evals/golden tests/test_eval_harness.py
git commit -m "test(mnemograph): add adversarial golden cases and richer eval assertions"
```

### Task 2: Make eval output more explicit about proof level

**Files:**
- Modify: `projects/oss/mnemograph/src/mnemograph/evals/cli.py`
- Modify: `projects/oss/mnemograph/README.md`
- Create: `projects/oss/mnemograph/tests/test_eval_cli.py`

- [ ] **Step 1: Write the failing test**

Add a CLI test that expects the summary output to include:
- self-reported local run context
- case count
- assertion count
- latency
- cost

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_eval_cli.py -v`
Expected: FAIL because the current summary is too thin

- [ ] **Step 3: Write minimal implementation**

Update the eval CLI output and README benchmark section so proof artifacts are presented as reproducible local runs rather than external validation.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_eval_cli.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/mnemograph/evals/cli.py README.md tests/test_eval_cli.py
git commit -m "docs(mnemograph): clarify local proof reporting in eval output"
```

## Chunk 2: Extraction Hardening

### Task 3: Filter marketing noise and low-specificity pseudo-facts more aggressively

**Files:**
- Modify: `projects/oss/mnemograph/src/mnemograph/ingest/pipeline.py`
- Create: `projects/oss/mnemograph/tests/test_extraction_quality_filters.py`

- [ ] **Step 1: Write the failing tests**

Add tests for:
- slogan-like marketing claims becoming open questions instead of durable claims
- “not specified” / “contact sales” text not becoming canonical pricing facts
- duplicate near-synonym claims collapsing instead of inflating the canon

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_extraction_quality_filters.py -v`
Expected: FAIL because the current filters are not strict enough

- [ ] **Step 3: Write minimal implementation**

Tighten the low-signal filters and duplicate text-overlap checks while preserving structured claims with concrete predicates and subjects.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_extraction_quality_filters.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/mnemograph/ingest/pipeline.py tests/test_extraction_quality_filters.py
git commit -m "fix(mnemograph): harden extraction filters against marketing noise"
```

### Task 4: Preserve pricing qualifiers and source disagreement rather than flattening them

**Files:**
- Modify: `projects/oss/mnemograph/src/mnemograph/prompts/contracts.py`
- Modify: `projects/oss/mnemograph/src/mnemograph/ingest/pipeline.py`
- Modify: `projects/oss/mnemograph/src/mnemograph/reconcile/conflicts.py`
- Create: `projects/oss/mnemograph/tests/test_qualified_claims.py`

- [ ] **Step 1: Write the failing tests**

Add tests that require:
- annual-billing qualifiers to survive normalization
- “contact sales” to become open questions or low-confidence notes instead of hard prices
- comparable-source value disagreement to emit `source_quality_conflict`

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_qualified_claims.py -v`
Expected: FAIL because qualifiers/conflict typing are not strong enough

- [ ] **Step 3: Write minimal implementation**

Add a lightweight qualifier channel that preserves pricing scope in claim metadata and improves conflict classification when comparable sources disagree.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_qualified_claims.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/mnemograph/prompts/contracts.py src/mnemograph/ingest/pipeline.py src/mnemograph/reconcile/conflicts.py tests/test_qualified_claims.py
git commit -m "feat(mnemograph): preserve pricing qualifiers and source disagreement"
```

## Chunk 3: End-to-End Verification

### Task 5: Prove the harder path end to end

**Files:**
- Modify: `projects/oss/mnemograph/demo-output.txt`
- Modify: `projects/oss/mnemograph/evals/results/latest.txt`
- Modify: `projects/oss/mnemograph/tests/integration/test_demo_flow.py`

- [ ] **Step 1: Write the failing integration assertions**

Extend the demo integration test so it expects:
- filtered open questions from noisy crawl text
- visible conflict typing or supersession when disagreement is introduced
- no pseudo-facts from “pricing not specified” style input

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_demo_flow.py -v`
Expected: FAIL because the current demo assertions are too weak

- [ ] **Step 3: Write minimal implementation**

Adjust the demo/eval execution path only as needed to surface the stronger proof points.

- [ ] **Step 4: Run targeted verification**

Run:
- `pytest tests/integration/test_demo_flow.py -v`
- `pytest tests -q`
- `mnemograph-eval evals/golden/ --base-dir /tmp/mnemograph-adversarial-eval`

Expected:
- targeted test PASS
- full suite PASS
- expanded golden suite PASS

- [ ] **Step 5: Refresh proof artifacts**

Run:
- `mnemograph-eval evals/golden/ --base-dir /tmp/mnemograph-adversarial-eval 2>&1 | tee evals/results/latest.txt`
- `python scripts/demo_hobbes.py --base-dir /tmp/mnemograph-adversarial-demo --base-url http://localhost:11434/v1 --model qwen3.5:latest --max-pages 1 --company-url https://vercel.com 2>&1 | tee demo-output.txt`

Expected: updated proof files reflect the stronger extraction and eval behavior

- [ ] **Step 6: Commit**

```bash
git add tests/integration/test_demo_flow.py evals/results/latest.txt demo-output.txt
git commit -m "test(mnemograph): refresh demo and eval proof artifacts"
```
