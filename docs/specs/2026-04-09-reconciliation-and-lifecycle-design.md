# Mnemograph Reconciliation and Lifecycle Design

Date: 2026-04-09

## Objective

Specify how candidate claims become durable memory, how conflicts are handled,
and how memory evolves over time.

## Reconciliation inputs

- candidate claims
- candidate evidence spans
- matching canonical claims
- source trust metadata
- temporal metadata
- predicate registry state

## Merge actions

- `ADD`
- `UPDATE`
- `SUPERSEDE`
- `CONTRADICT`
- `DELETE`
- `NONE`

## Match keys

Primary reconciliation key:

- subject
- predicate
- object
- valid-time overlap

Secondary signals:

- source trust
- evidence support
- semantic similarity
- recency

## Deterministic-first reconciliation

The default reconciliation path should not require an LLM.

Deterministic path:

- match on normalized SPO keys
- compare valid-time windows and temporal ordering
- apply typed conflict policies
- choose actions using source trust and evidence support rules

LLM fallback is reserved for ambiguous cases only:

- provisional predicate near-matches
- entity resolution uncertainty
- semantic near-duplicate claims that cannot be resolved by deterministic keys

This keeps the common path fast, reproducible, and testable.

## Conflict policy

### Temporal conflict

- default: auto-supersede when valid times differ and ordering is supported
- preserve both claims

### Value conflict

- default: auto-supersede only if newer source is strictly higher trust
- otherwise retain both and flag

### Entity resolution conflict

- default: auto-merge only above very high confidence
- otherwise queue for review

### Source quality conflict

- default: always flag

### Insufficient evidence conflict

- default: keep the better-evidenced claim active

## Confidence composition

Use component-level clamping to avoid zero-product collapse.

Inputs:

- trust
- evidence
- extraction
- recency
- contradiction
- confirmation

Each component is normalized and clamped before composition.

## Consolidation

Trigger:

- more than 10 active claims in one entity/domain neighborhood

Output:

- entity summary
- domain summary
- predicate rollup

Atomic claims remain in storage but summary claims become the default retrieval
surface.

Bypass rules:

- if a summary-based answer is below `0.70` confidence, retrieve supporting
  atomic claims
- if the query targets a specific predicate or value, prefer the relevant
  atomic claims even when a summary exists
- if unresolved conflicts are attached to the summary region, include the
  conflicting atomic claims

## Distillation

Conversation turns and working-memory notes are episodic by default.

Distillation checkpoints:

- session end
- explicit user request
- long conversation threshold

Default threshold:

- `15` turns

Distilled outputs must go through the same reconciliation pipeline as other
sources.

## Decay and archival

Default weekly decay:

- confidence = confidence * 0.95

Applies only to:

- low-confidence
- non-user-confirmed
- unretrieved claims

Historical temporal claims are archived, not deleted, when no longer active.

## Changelog

Every lifecycle transition writes a change record with:

- change type
- source trigger
- affected claim ids
- reason code
- timestamp
