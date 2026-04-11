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
