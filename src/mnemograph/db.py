"""Database bootstrap helpers for Mnemograph."""

from pathlib import Path
import sqlite3

from mnemograph.schema import schema_statements


def bootstrap_db(db_path: str | Path) -> None:
    """Create the initial SQLite schema for the canonical store."""
    target = Path(db_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(target) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        for statement in schema_statements():
            connection.execute(statement)
        connection.commit()
