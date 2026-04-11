# Mnemograph Canonical Schema

Date: 2026-04-09

## Objective

Define the canonical local schema for Mnemograph so ingestion, reconciliation,
retrieval, projections, and evals all operate on the same memory model.

## Storage surfaces

- canonical store: SQLite
- mirror surfaces: Markdown and JSON
- derived projections: Qdrant and Grafeo

## Core entities

### `sources`

Represents a source document, URL, file, or conversation-derived input.

Required fields:

- `source_id`
- `source_type`
- `locator`
- `normalized_locator`
- `content_hash`
- `ingested_at`
- `fetched_at`
- `trust_tier`
- `render_mode`
- `status_code`
- `parent_source_id`

### `source_chunks`

Required fields:

- `chunk_id`
- `source_id`
- `chunk_index`
- `text`
- `text_hash`
- `start_offset`
- `end_offset`
- `embedding_profile`
- `projection_status`

### `entities`

Required fields:

- `entity_id`
- `entity_type`
- `canonical_name`
- `namespace`
- `status`

Optional fields:

- aliases
  - stored as JSON array
- external ids
  - stored as JSON object or JSON array, depending on source shape
- merge confidence

### `predicates`

Represents the semi-closed emergent predicate registry.

Required fields:

- `predicate_id`
- `domain`
- `canonical_name`
- `status`
  - canonical, provisional, deprecated, merged
- `created_at`
- `updated_at`

Optional fields:

- alias list
- merged_into_predicate_id
- normalization_notes

### `claims`

Atomic durable claims.

Required fields:

- `claim_id`
- `subject_entity_id`
- `predicate_id`
- `object_type`
- `object_entity_id`
- `object_value`
- `normalized_spo_key`
- `claim_text`
- `domain`
- `memory_type`
- `status`
- `valid_time_start`
- `valid_time_end`
- `system_time_start`
- `system_time_end`
- `confidence`
- `support_count`
- `user_confirmed`
- `provisional_predicate`
- `extraction_run_id`

Nullability rules:

- `object_entity_id` is a nullable foreign key to `entities.entity_id` unless
  `object_type = entity`, in which case it is required
- `object_value` stores the normalized literal payload or a human-readable
  label for entity objects

### `evidence_spans`

Required fields:

- `evidence_id`
- `claim_id`
- `extraction_run_id`
- `source_id`
- `chunk_id`
- `quote_text`
- `start_offset`
- `end_offset`
- `evidence_strength`

### `extraction_runs`

Represents one structured extraction execution over one source or a batch of
source chunks.

Required fields:

- `extraction_run_id`
- `source_id`
- `run_kind`
  - initial_ingest, reingest, conversation_distill, repair, backfill
- `model_name`
- `prompt_version`
- `status`
- `started_at`
- `chunk_batch`
  - stored as JSON array of chunk ids

Optional fields:

- `completed_at`
- `cost_estimate_usd`
- `error_summary`

### `conflicts`

Required fields:

- `conflict_id`
- `conflict_type`
- `left_claim_id`
- `right_claim_id`
- `status`
- `resolution_policy`
- `created_at`

### `memory_changes`

Required fields:

- `change_id`
- `change_type`
  - add, update, supersede, contradict, delete, archive, consolidate
- `subject_claim_id`
- `related_claim_id`
- `trigger_source_id`
- `created_at`
- `reason_code`

### `retrieval_runs`

Required fields:

- `retrieval_run_id`
- `query_text`
- `retrieval_mode`
- `working_memory_used`
- `entity_targets`
- `domain_targets`
- `used_vector`
- `used_graph`
- `created_at`

### `context_snapshots`

Required fields:

- `snapshot_id`
- `retrieval_run_id`
- `assembled_claim_ids`
- `assembled_evidence_ids`
- `token_estimate`
- `created_at`

### `conversation_turns`

Required fields:

- `turn_id`
- `session_id`
- `speaker`
- `content`
- `created_at`
- `distilled`

## Key relationships

- source -> chunks
- source -> extraction run
- source/chunk -> evidence span
- extraction run -> claim
- extraction run -> evidence span
- evidence span -> claim
- claim.subject_entity_id -> entity
- claim.object_entity_id -> entity when `object_type = entity`
- entity + predicate + object -> claim
- claim -> conflict
- claim -> memory change
- retrieval run -> context snapshot
- conversation turn -> distilled claims

## Unique constraints

- `sources.normalized_locator + content_hash`
- `predicates.domain + canonical_name`
- `claims.normalized_spo_key + valid_time_start + system_time_start`
- `source_chunks.source_id + chunk_index`

## Index strategy

### High-priority indexes

- `claims(subject_entity_id, predicate_id, status)`
- `claims(object_entity_id, predicate_id, status)`
- `claims(domain, memory_type, status)`
- `claims(valid_time_start, valid_time_end)`
- `claims(system_time_start, system_time_end)`
- `predicates(domain, status)`
- `evidence_spans(claim_id)`
- `extraction_runs(source_id, started_at)`
- `retrieval_runs(retrieval_mode, created_at)`

## Normalization rules

### `claims.normalized_spo_key`

The normalized SPO key is the deterministic deduplication key for a claim
before time windows are considered.

Algorithm:

1. `subject_key = lower(trim(subject_entity_id))`
2. `predicate_key = lower(trim(predicate_id))`
3. derive `object_key`:
   - if `object_type = entity`, require `object_entity_id` and use
     `entity:` + `lower(trim(object_entity_id))`
   - if `object_type = literal`, use `literal:` + normalized literal value
   - if `object_type = enum`, use `enum:` + lower(trim(object_value))
   - if `object_type = range`, use `range:` + canonical serialized range
   - if `object_type = unknown`, use `unknown`
4. concatenate `subject_key | predicate_key | object_key`
5. hash with a stable digest for storage

Literal normalization rules:

- trim whitespace
- lowercase unless case is semantically meaningful
- normalize currency symbols to ISO currency code where possible
- normalize numeric formatting
- normalize dates to ISO 8601 where possible

This prevents deduplication from depending on raw surface strings when two
extractions refer to the same fact.

## JSON column contract

SQLite list-like and nested fields must be stored as JSON, never as
comma-separated strings.

Required JSON-backed columns:

- `entities.aliases`
- `entities.external_ids`
- `predicates.alias_list`
- `extraction_runs.chunk_batch`
- `retrieval_runs.entity_targets`
- `retrieval_runs.domain_targets`
- `context_snapshots.assembled_claim_ids`
- `context_snapshots.assembled_evidence_ids`

## Mirror contract

The Hobbes mirror view should expose:

- `memory/sources/source_*.json`
- `memory/knowledge/<entity-or-domain>.json`
- `memory/working/active_context.json`
- `memory/working/session_history.json`

Mirror files are projections. They must include canonical ids so they are
traceable back to SQLite.

## Projection contract

### Qdrant

Qdrant points should reference:

- `claim_id`
- `chunk_id`
- `entity_id`
- `domain`
- `memory_type`
- `confidence_bucket`

### Grafeo

Grafeo projection should map:

- entity nodes
- predicate nodes
- claim nodes
- source nodes
- evidence edges
- supersession edges
- contradiction edges
- provenance edges

## Schema evolution

Rules:

- additive changes preferred
- destructive changes require migration docs
- predicate merges should preserve old ids and alias history
- archived claims are never physically deleted by default
- JSON-bearing columns must remain valid JSON across schema revisions
