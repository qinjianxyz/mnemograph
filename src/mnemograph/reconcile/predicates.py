"""Predicate registry lifecycle helpers."""

from datetime import UTC, datetime
import json
import sqlite3


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def resolve_predicate(
    connection: sqlite3.Connection,
    domain: str,
    proposed_name: str,
    provisional: bool = False,
) -> dict[str, str]:
    """Resolve or create a predicate in the semi-closed registry."""
    existing = connection.execute(
        """
        SELECT predicate_id, canonical_name, status
        FROM predicates
        WHERE predicate_id = ?
        """,
        (proposed_name,),
    ).fetchone()
    if existing:
        return {
            "predicate_id": existing[0],
            "canonical_name": existing[1],
            "status": existing[2],
        }

    now = _utc_now()
    status = "provisional" if provisional else "canonical"
    connection.execute(
        """
        INSERT INTO predicates (
            predicate_id, domain, canonical_name, status, created_at, updated_at,
            alias_list, merged_into_predicate_id, normalization_notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            proposed_name,
            domain,
            proposed_name,
            status,
            now,
            now,
            json.dumps([]),
            None,
            None,
        ),
    )
    return {
        "predicate_id": proposed_name,
        "canonical_name": proposed_name,
        "status": status,
    }


def merge_predicate_into_canonical(
    connection: sqlite3.Connection,
    provisional_predicate_id: str,
    canonical_predicate_id: str,
) -> None:
    """Merge a provisional predicate into a canonical predicate."""
    alias_row = connection.execute(
        "SELECT alias_list FROM predicates WHERE predicate_id = ?",
        (canonical_predicate_id,),
    ).fetchone()
    aliases = json.loads(alias_row[0] or "[]") if alias_row else []
    if provisional_predicate_id not in aliases:
        aliases.append(provisional_predicate_id)

    now = _utc_now()
    connection.execute(
        """
        UPDATE predicates
        SET alias_list = ?, updated_at = ?
        WHERE predicate_id = ?
        """,
        (json.dumps(aliases), now, canonical_predicate_id),
    )
    connection.execute(
        """
        UPDATE predicates
        SET status = ?, merged_into_predicate_id = ?, updated_at = ?
        WHERE predicate_id = ?
        """,
        ("merged", canonical_predicate_id, now, provisional_predicate_id),
    )
    connection.commit()
