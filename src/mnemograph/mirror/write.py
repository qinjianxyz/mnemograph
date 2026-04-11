"""Write inspectable memory mirror artifacts."""

import json
from pathlib import Path
import sqlite3

from mnemograph.paths import mirror_paths


def _ensure_mirror_dirs(base_dir: str | Path) -> dict[str, str]:
    paths = mirror_paths(Path(base_dir) / "memory")
    for path in paths.values():
        Path(path).mkdir(parents=True, exist_ok=True)
    return paths


def write_working_mirrors(base_dir: str | Path, active_context: dict, session_history: list[dict]) -> None:
    """Write active context and session history mirrors."""
    paths = _ensure_mirror_dirs(base_dir)

    Path(paths["working"], "active_context.json").write_text(
        json.dumps(active_context, indent=2, sort_keys=True)
    )
    Path(paths["working"], "session_history.json").write_text(
        json.dumps(session_history, indent=2, sort_keys=True)
    )


def write_durable_mirrors(base_dir: str | Path, db_path: str | Path) -> None:
    """Write knowledge and source mirrors from the canonical database."""
    paths = _ensure_mirror_dirs(base_dir)
    target_db = Path(db_path)
    if not target_db.exists():
        return

    with sqlite3.connect(target_db) as conn:
        conn.row_factory = sqlite3.Row

        claim_rows = conn.execute(
            """
            SELECT
                claim_id,
                subject_entity_id,
                predicate_id,
                object_type,
                object_entity_id,
                object_value,
                claim_text,
                domain,
                status,
                confidence,
                extraction_run_id
            FROM claims
            WHERE status IN ('active', 'superseded', 'pending_review')
            ORDER BY domain ASC, claim_id ASC
            """
        ).fetchall()

        claims_by_domain: dict[str, list[dict]] = {}
        for row in claim_rows:
            row_dict = dict(row)
            claims_by_domain.setdefault(row_dict["domain"], []).append(row_dict)

        for domain, claims in claims_by_domain.items():
            Path(paths["knowledge"], f"{domain}.json").write_text(
                json.dumps({"domain": domain, "claims": claims}, indent=2, sort_keys=True)
            )

        source_rows = conn.execute(
            """
            SELECT source_id, source_type, locator, normalized_locator, ingested_at, trust_tier
            FROM sources
            ORDER BY ingested_at ASC, source_id ASC
            """
        ).fetchall()

        for row in source_rows:
            row_dict = dict(row)
            extraction_runs = [
                record[0]
                for record in conn.execute(
                    "SELECT extraction_run_id FROM extraction_runs WHERE source_id = ? ORDER BY completed_at ASC",
                    (row_dict["source_id"],),
                ).fetchall()
            ]
            derived_claim_ids = [
                record[0]
                for record in conn.execute(
                    """
                    SELECT claims.claim_id
                    FROM claims
                    JOIN extraction_runs
                      ON extraction_runs.extraction_run_id = claims.extraction_run_id
                    WHERE extraction_runs.source_id = ?
                    ORDER BY claims.claim_id ASC
                    """,
                    (row_dict["source_id"],),
                ).fetchall()
            ]
            payload = {
                **row_dict,
                "extraction_run_ids": extraction_runs,
                "derived_claim_ids": derived_claim_ids,
            }
            Path(paths["sources"], f"{row_dict['source_id']}.json").write_text(
                json.dumps(payload, indent=2, sort_keys=True)
            )
