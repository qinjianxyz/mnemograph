# Mnemograph Ingestion and Extraction Design

Date: 2026-04-09

## Objective

Specify how raw sources become typed, evidence-backed claim candidates with
controlled cost and latency.

## Pipeline overview

1. source registration
2. content acquisition
3. cleanup and boilerplate removal
4. chunking
5. entity and claim extraction
6. relationship and confidence extraction
7. provisional predicate handling
8. candidate commit to reconciliation queue

## Crawl strategy

Default crawl policy:

- same-domain only
- max depth: 2
- max pages: 40
- 1 request/second default
- robots-aware
- static fetch first
- JS rendering only on content-poor pages

Priority pages:

- homepage
- pricing
- product
- docs
- faq
- about
- security

## Content cleanup

Cleanup should remove:

- nav menus
- footers
- cookie banners
- repeated calls to action
- unrelated chrome

The system must preserve:

- headings
- tables
- lists
- inline links
- section order

## Chunking strategy

Default chunking target:

- preserve semantic boundaries first
- target roughly 600-1200 tokens per chunk
- overlap only when section continuity requires it

Chunk metadata:

- source id
- chunk index
- heading path
- offsets
- token estimate

## Logical extraction passes

### Pass A: entity inventory + claim extraction

Combined by default in v1.

Input:

- chunk batch
- known entities
- predicate registry snapshot

Output:

- entity candidates
- alias candidates
- SPO claim candidates
- evidence spans
- provisional predicates

### Pass B: relationship extraction + confidence calibration

Combined by default in v1.

Input:

- claim candidates
- source metadata
- entity inventory

Output:

- relationship candidates
- contradiction candidates
- extraction-confidence components
- open questions

## Cost control

Multi-pass is a logical architecture, not a per-chunk 4x call mandate.

Default cost controls:

- batch chunks when token budgets allow
- skip relationship extraction for chunks with no durable claims
- provide a reduced-cost single-pass mode
- cache extraction results by content hash

## Prompt contracts

All extraction prompts must use structured output.

Each prompt should define:

- input contract
- JSON schema or tool schema
- allowed enums
- failure handling path

No free-form extraction output should flow into canon.

Every extraction execution must create an `extraction_run` record before claim
materialization.

The extraction run must capture:

- source id
- chunk batch
- model name
- prompt version
- run kind
- status
- estimated token usage and cost

Claims and evidence spans created by that execution must point back to the
originating `extraction_run_id` so benchmark traces and provenance audits can
reconstruct exactly how a memory item entered canon.

## Provisional predicates

Novel predicates should be usable immediately but marked provisional.

Lifecycle:

1. extractor proposes provisional predicate
2. claim enters canon with `provisional_predicate = true`
3. normalization job clusters similar predicates
4. canonical merge rewrites claims to the chosen predicate
5. old provisional ids remain as aliases for traceability

This avoids dead-letter claims that are invisible until manual review.

## Output quality rules

Extraction should prefer:

- explicit subject over pronoun
- canonical predicate over free text
- explicit unknown over invention
- evidence-backed claim over summary-only assertion

## Failure handling

If schema validation fails:

- attempt one repair pass
- if still invalid, keep the result in an extraction-failure log
- do not write malformed durable claims
