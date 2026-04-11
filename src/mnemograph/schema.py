"""SQLite schema for the Mnemograph canonical store."""


def schema_statements() -> tuple[str, ...]:
    """Return the ordered DDL statements for the initial schema."""
    return (
        """
        CREATE TABLE IF NOT EXISTS sources (
            source_id TEXT PRIMARY KEY,
            source_type TEXT NOT NULL,
            locator TEXT NOT NULL,
            normalized_locator TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            ingested_at TEXT NOT NULL,
            fetched_at TEXT,
            trust_tier TEXT NOT NULL,
            render_mode TEXT,
            status_code INTEGER,
            parent_source_id TEXT,
            FOREIGN KEY(parent_source_id) REFERENCES sources(source_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS source_chunks (
            chunk_id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            text TEXT NOT NULL,
            text_hash TEXT NOT NULL,
            start_offset INTEGER,
            end_offset INTEGER,
            embedding_profile TEXT,
            projection_status TEXT,
            FOREIGN KEY(source_id) REFERENCES sources(source_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS entities (
            entity_id TEXT PRIMARY KEY,
            entity_type TEXT NOT NULL,
            canonical_name TEXT NOT NULL,
            namespace TEXT NOT NULL,
            status TEXT NOT NULL,
            aliases TEXT,
            external_ids TEXT,
            merge_confidence REAL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS predicates (
            predicate_id TEXT PRIMARY KEY,
            domain TEXT NOT NULL,
            canonical_name TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            alias_list TEXT,
            merged_into_predicate_id TEXT,
            normalization_notes TEXT,
            FOREIGN KEY(merged_into_predicate_id) REFERENCES predicates(predicate_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS extraction_runs (
            extraction_run_id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL,
            run_kind TEXT NOT NULL,
            model_name TEXT NOT NULL,
            prompt_version TEXT NOT NULL,
            status TEXT NOT NULL,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            chunk_batch TEXT NOT NULL,
            cost_estimate_usd REAL,
            error_summary TEXT,
            FOREIGN KEY(source_id) REFERENCES sources(source_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS claims (
            claim_id TEXT PRIMARY KEY,
            subject_entity_id TEXT NOT NULL,
            predicate_id TEXT NOT NULL,
            object_type TEXT NOT NULL,
            object_entity_id TEXT,
            object_value TEXT NOT NULL,
            normalized_spo_key TEXT NOT NULL,
            claim_text TEXT NOT NULL,
            domain TEXT NOT NULL,
            memory_type TEXT NOT NULL,
            status TEXT NOT NULL,
            valid_time_start TEXT,
            valid_time_end TEXT,
            system_time_start TEXT NOT NULL,
            system_time_end TEXT,
            confidence REAL NOT NULL,
            support_count INTEGER NOT NULL DEFAULT 0,
            user_confirmed INTEGER NOT NULL DEFAULT 0,
            provisional_predicate INTEGER NOT NULL DEFAULT 0,
            extraction_run_id TEXT NOT NULL,
            FOREIGN KEY(subject_entity_id) REFERENCES entities(entity_id),
            FOREIGN KEY(predicate_id) REFERENCES predicates(predicate_id),
            FOREIGN KEY(object_entity_id) REFERENCES entities(entity_id),
            FOREIGN KEY(extraction_run_id) REFERENCES extraction_runs(extraction_run_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS evidence_spans (
            evidence_id TEXT PRIMARY KEY,
            claim_id TEXT NOT NULL,
            extraction_run_id TEXT NOT NULL,
            source_id TEXT NOT NULL,
            chunk_id TEXT NOT NULL,
            quote_text TEXT NOT NULL,
            start_offset INTEGER,
            end_offset INTEGER,
            evidence_strength REAL NOT NULL,
            FOREIGN KEY(claim_id) REFERENCES claims(claim_id),
            FOREIGN KEY(extraction_run_id) REFERENCES extraction_runs(extraction_run_id),
            FOREIGN KEY(source_id) REFERENCES sources(source_id),
            FOREIGN KEY(chunk_id) REFERENCES source_chunks(chunk_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS conflicts (
            conflict_id TEXT PRIMARY KEY,
            conflict_type TEXT NOT NULL,
            left_claim_id TEXT NOT NULL,
            right_claim_id TEXT NOT NULL,
            status TEXT NOT NULL,
            resolution_policy TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(left_claim_id) REFERENCES claims(claim_id),
            FOREIGN KEY(right_claim_id) REFERENCES claims(claim_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS memory_changes (
            change_id TEXT PRIMARY KEY,
            change_type TEXT NOT NULL,
            subject_claim_id TEXT NOT NULL,
            related_claim_id TEXT,
            trigger_source_id TEXT,
            created_at TEXT NOT NULL,
            reason_code TEXT NOT NULL,
            FOREIGN KEY(subject_claim_id) REFERENCES claims(claim_id),
            FOREIGN KEY(related_claim_id) REFERENCES claims(claim_id),
            FOREIGN KEY(trigger_source_id) REFERENCES sources(source_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS retrieval_runs (
            retrieval_run_id TEXT PRIMARY KEY,
            query_text TEXT NOT NULL,
            retrieval_mode TEXT NOT NULL,
            working_memory_used INTEGER NOT NULL DEFAULT 0,
            entity_targets TEXT,
            domain_targets TEXT,
            used_vector INTEGER NOT NULL DEFAULT 0,
            used_graph INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS context_snapshots (
            snapshot_id TEXT PRIMARY KEY,
            retrieval_run_id TEXT NOT NULL,
            assembled_claim_ids TEXT NOT NULL,
            assembled_evidence_ids TEXT NOT NULL,
            token_estimate INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(retrieval_run_id) REFERENCES retrieval_runs(retrieval_run_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS conversation_turns (
            turn_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            speaker TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            distilled INTEGER NOT NULL DEFAULT 0
        )
        """,
    )
