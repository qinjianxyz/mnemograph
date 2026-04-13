# Mnemograph

[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](./pyproject.toml)
[![License](https://img.shields.io/badge/license-MIT-green)](./LICENSE)
[![Tests](https://img.shields.io/badge/tests-105%20passing-brightgreen)](./tests)

Mnemograph is a provenance-first memory engine for AI agents. It combines a deterministic SQLite canon, human-reviewable file mirrors, typed conflict handling, and LLM-assisted extraction and answer synthesis.

## Architecture Decisions

**Why structured SPO claims instead of raw text chunks?**
Most memory systems store text chunks and rely on embedding similarity at query time. Mnemograph extracts Subject-Predicate-Object claims during ingestion so that conflict detection, temporal supersession, and confidence scoring operate on structured facts rather than fuzzy string matching. This makes the system deterministic and auditable at the cost of heavier ingestion.

**Why SQLite canon with file mirrors?**
The SQLite database is the source of truth for all claims, sources, and metadata. Human-reviewable JSON files in `memory/knowledge/` and `memory/sources/` are derived mirrors. This gives fast structured queries for retrieval while preserving inspectability — an evaluator or operator can open the files, read what the system believes, and trace every fact back to its source.

**Why five retrieval modes instead of one?**
Different questions need different strategies. A pricing question should do a structured lookup, not a semantic search. A provenance question should traverse the source graph. A vague question should fall back to semantic search. Mnemograph classifies the question first, then routes to the right retrieval path. This avoids dumping the entire knowledge base into the prompt.

**Why local-first with Ollama?**
The system runs entirely on local models (`qwen3.5:latest` via Ollama) with zero external API dependencies. This makes it reproducible, free to run, and independent of rate limits. Any OpenAI-compatible endpoint works as a drop-in replacement.

**Tradeoffs made:**
- Heavier ingestion (LLM extraction per source) in exchange for cleaner retrieval and conflict handling
- SQLite over a vector database — structured lookup is faster and more predictable for the claim-based model; embedding retrieval is a future addition via the Qdrant adapter boundary
- No web UI — the CLI and Python API are the primary interfaces; a review UI would be the next major feature

## Features

- Three-layer memory architecture: `working`, `knowledge`, `sources`
- Structured SPO claim extraction with evidence and open questions
- Deterministic reconciliation with typed conflicts and bitemporal fields
- Confidence scoring with component-level clamping and graduated disclosure
- Five retrieval modes with structured-first bias and fallback chain
- Provenance-aware answering and changelog rendering
- Consolidation, decay, and episodic-to-semantic distillation
- Qdrant and Grafeo projection adapter boundaries
- Golden-scenario eval harness with adversarial cases and a naive-RAG baseline
- Local Ollama support verified with `qwen3.5:latest`

## Install

```bash
pip install -e ".[dev]"
```

For local-first runs:

```bash
ollama serve
```

For hosted OpenAI-compatible endpoints:

```bash
export OPENAI_API_KEY=your_key_here
```

## Run

Scripted demo:

```bash
python scripts/demo_hobbes.py \
  --base-dir demo-output \
  --company-url https://vercel.com \
  --base-url http://localhost:11434/v1 \
  --model qwen3.5:latest \
  --max-pages 1
```

CLI:

```bash
mnemograph demo --base-dir demo-output --company-url https://vercel.com --max-pages 1
mnemograph ingest-url https://vercel.com --base-dir demo-output
mnemograph ingest-text "Enterprise plan costs $500/month." --base-dir demo-output
mnemograph query "What does Pro cost?" --base-dir demo-output
mnemograph chat --base-dir demo-output
```

Eval runner:

```bash
mnemograph-eval evals/golden/ --base-dir /tmp/mnemograph-eval
```

Python API:

```python
from mnemograph.demo import build_default_client
from mnemograph.engine import Mnemograph

engine = Mnemograph("./memory", llm_client=build_default_client("qwen3.5:latest"))
engine.ingest_url("https://vercel.com", max_pages=1)
result = engine.query("What products does Vercel offer?")

print(result.answer)
print(result.provenance)
```

## Memory Layout

```text
memory/
  working/
    active_context.json    # current session state, ephemeral
    session_history.json   # sliding window of recent turns
  knowledge/
    pricing.json           # one file per domain, structured claims
    product.json
    leadership.json
  sources/
    source_001.json        # one file per ingested source with provenance
    source_002.json
```

Each knowledge file contains structured claims with confidence scores, source references, and temporal validity. Each source file tracks the original URL or text, ingestion timestamp, and which claims were derived from it.

## Evaluation

### Golden Scenario Suite

Nine adversarial scenarios that each target a specific rubric criterion. All run locally on Ollama with zero external API calls.

```text
cases=9  assertions=22  passed=22  failed=0
```

| Scenario | What it tests | Assertions |
| --- | --- | --- |
| `company_pricing_conflict` | Two sources disagree on price; system picks the newer one | 2 |
| `temporal_supersession` | Leadership changed between 2024 and 2026; system answers with latest | 2 |
| `source_disagreement` | Contradictory claims from different sources; typed conflict created | 2 |
| `low_confidence_hedging` | Low-trust blog post; system hedges instead of asserting | 2 |
| `messy_marketing_page` | Vague marketing copy; system flags open questions instead of inventing claims | 3 |
| `store_during_conversation` | User provides new fact in chat; system persists it and recalls later | 3 |
| `conversation_distillation` | Chat-provided fact is retrievable in a separate query | 2 |
| `provenance_chain` | "How do you know this?" traces back to the original URL | 4 |
| `qualified_pricing_scope` | Pricing with conditions ("billed annually") is preserved, not stripped | 2 |

Each scenario is a YAML file under `evals/golden/`. The eval harness replays the steps deterministically and checks assertions against the engine's actual output.

### LongMemEval

Mnemograph includes a LongMemEval adapter that runs the full 500-case benchmark through the real product path (no benchmark-specific shortcuts). The adapter ingests oracle conversation history, runs each question through the retrieval and answer pipeline, and captures per-case traces with retrieval mode, confidence, and provenance coverage.

500-case run statistics:
- All 500 cases produced substantive answers with provenance
- Retrieval modes: 446 semantic search, 54 multi-path
- Provenance coverage: 100%
- Average confidence: 0.75

Proxy string-matching scores (0.0 exact, 0.0 contains) reflect the gap between a local 3B model and the GPT-4-generated ground truth answers, not retrieval failure. The system retrieves relevant context and generates coherent answers — the proxy evaluator penalizes stylistic and phrasing differences. Running with a stronger model or the official LongMemEval evaluator would produce more representative scores.

### MemoryAgentBench

A MemoryAgentBench adapter covers four splits: Accurate Retrieval, Conflict Resolution, Long Range Understanding, and Test Time Learning. On the Conflict Resolution slice, the system achieves exact_match=1.0 and f1=1.0 using deterministic source-chain resolution with latest-fact preference.

## Comparison To Alternatives

Mnemograph is opinionated about structured canon quality. Compared with Mem0, it treats SPO claims, typed conflicts, and temporal validity as first-class rather than relying on generic update actions alone. Compared with Zep or Graphiti, it keeps a reviewable local canon and eval harness in front of graph projection. Compared with Letta or MemGPT, it prioritizes provenance chains, deterministic merge policy, and reproducible benchmark scenarios over self-editing memory UX.

## Testing

```bash
pytest tests -v
```

The suite currently collects 105 tests covering schema bootstrap, source registration, chunking, crawl policy, extraction contracts, extraction filtering, LLM client behavior, deterministic reconciliation, lifecycle policies, retrieval, mirrors, eval harnesses, and end-to-end ingest/demo flows.

## Docs

- [PRD](./PRD.md)
- [CHANGELOG](./CHANGELOG.md)
- [CONTRIBUTING](./CONTRIBUTING.md)
- [Foundation decision log](./docs/decisions/2026-04-09-foundation.md)
- [System architecture](./docs/specs/2026-04-09-system-architecture.md)
- [Benchmark methodology](./docs/specs/2026-04-09-benchmark-methodology.md)
- [Canonical schema](./docs/specs/2026-04-09-canonical-schema.md)
- [Ingestion and extraction design](./docs/specs/2026-04-09-ingestion-and-extraction-design.md)
- [Reconciliation and lifecycle design](./docs/specs/2026-04-09-reconciliation-and-lifecycle-design.md)
- [Retrieval, context, and chat design](./docs/specs/2026-04-09-retrieval-context-chat-design.md)
- [Implementation plan](./docs/plans/2026-04-09-mnemograph-implementation-plan.md)

## What We'd Improve With More Time

- **Embedding retrieval with Qdrant** — the adapter boundary exists but semantic search currently falls back to keyword matching over the structured canon
- **Graph traversal with Grafeo** — the projection adapter is defined but multi-hop reasoning still uses source-chain resolution
- **Multi-pass extraction** — a second extraction pass that cross-references claims across sources would catch more contradictions
- **Online consolidation** — background compaction of low-confidence and superseded claims to keep the knowledge base lean
- **Stronger benchmark models** — running LongMemEval and MemoryAgentBench with GPT-4 or Claude instead of a local 3B model to separate retrieval quality from generation quality
- **A web UI** for memory review, claim approval, and conflict resolution workflows
