import sqlite3

from mnemograph.db import bootstrap_db
from mnemograph.reconcile.predicates import merge_predicate_into_canonical, resolve_predicate


def test_resolve_predicate_reuses_existing_canonical_predicate(tmp_path):
    db_path = tmp_path / "memory.db"
    bootstrap_db(db_path)

    with sqlite3.connect(db_path) as conn:
        first = resolve_predicate(conn, domain="pricing", proposed_name="has_pricing_plan")
        second = resolve_predicate(conn, domain="pricing", proposed_name="has_pricing_plan")
        count = conn.execute("SELECT COUNT(*) FROM predicates").fetchone()[0]

    assert first["predicate_id"] == second["predicate_id"]
    assert first["status"] == "canonical"
    assert count == 1


def test_resolve_predicate_creates_provisional_predicate_for_novel_name(tmp_path):
    db_path = tmp_path / "memory.db"
    bootstrap_db(db_path)

    with sqlite3.connect(db_path) as conn:
        record = resolve_predicate(
            conn,
            domain="pricing",
            proposed_name="plan_cost",
            provisional=True,
        )

    assert record["predicate_id"] == "plan_cost"
    assert record["status"] == "provisional"


def test_resolve_predicate_reuses_global_predicate_id_across_domains(tmp_path):
    db_path = tmp_path / "memory.db"
    bootstrap_db(db_path)

    with sqlite3.connect(db_path) as conn:
        first = resolve_predicate(conn, domain="product", proposed_name="supports")
        second = resolve_predicate(conn, domain="security", proposed_name="supports")
        count = conn.execute("SELECT COUNT(*) FROM predicates").fetchone()[0]

    assert first["predicate_id"] == second["predicate_id"]
    assert count == 1


def test_merge_predicate_into_canonical_merges_alias_history(tmp_path):
    db_path = tmp_path / "memory.db"
    bootstrap_db(db_path)

    with sqlite3.connect(db_path) as conn:
        canonical = resolve_predicate(conn, domain="pricing", proposed_name="price_usd_monthly")
        provisional = resolve_predicate(
            conn,
            domain="pricing",
            proposed_name="plan_cost",
            provisional=True,
        )
        merge_predicate_into_canonical(conn, provisional["predicate_id"], canonical["predicate_id"])
        merged = conn.execute(
            "SELECT status, merged_into_predicate_id FROM predicates WHERE predicate_id = ?",
            (provisional["predicate_id"],),
        ).fetchone()
        aliases = conn.execute(
            "SELECT alias_list FROM predicates WHERE predicate_id = ?",
            (canonical["predicate_id"],),
        ).fetchone()[0]

    assert merged == ("merged", canonical["predicate_id"])
    assert "plan_cost" in aliases
