from pathlib import Path
from collections.abc import Callable
from typing import get_type_hints

import pytest


def test_qdrant_projection_payload_shape():
    from mnemograph.adapters.qdrant import project_claim_to_point

    claim = {
        "claim_id": "claim-1",
        "subject_entity_id": "Company:Stripe",
        "predicate_id": "has_product",
        "object_type": "entity",
        "object_entity_id": "Product:Billing",
        "object_value": "Product:Billing",
        "claim_text": "Stripe offers Billing.",
        "domain": "product",
        "confidence": 0.91,
        "status": "active",
        "source_id": "source-1",
        "extraction_run_id": "run-1",
        "valid_time_start": "2026-04-10T00:00:00Z",
        "valid_time_end": None,
    }

    point = project_claim_to_point(claim, vector=[0.1, 0.2, 0.3])

    assert point["id"] == "claim-1"
    assert point["vector"] == [0.1, 0.2, 0.3]
    assert point["payload"]["subject_entity_id"] == "Company:Stripe"
    assert point["payload"]["predicate_id"] == "has_product"
    assert point["payload"]["object_entity_id"] == "Product:Billing"
    assert point["payload"]["domain"] == "product"
    assert point["payload"]["confidence"] == 0.91


def test_grafeo_projection_payload_shape():
    from mnemograph.adapters.grafeo import project_claim_to_graph_record

    claim = {
        "claim_id": "claim-1",
        "subject_entity_id": "Company:Stripe",
        "predicate_id": "has_product",
        "object_type": "entity",
        "object_entity_id": "Product:Billing",
        "object_value": "Product:Billing",
        "claim_text": "Stripe offers Billing.",
        "domain": "product",
        "confidence": 0.91,
        "status": "active",
        "source_id": "source-1",
        "extraction_run_id": "run-1",
        "valid_time_start": "2026-04-10T00:00:00Z",
        "valid_time_end": None,
    }

    graph_record = project_claim_to_graph_record(claim)

    assert graph_record["claim_node"]["id"] == "claim-1"
    assert graph_record["subject_node"]["id"] == "Company:Stripe"
    assert graph_record["object_node"]["id"] == "Product:Billing"
    assert graph_record["edge"]["predicate"] == "has_product"
    assert graph_record["edge"]["confidence"] == 0.91


def test_adapter_failure_leaves_canon_intact(tmp_path):
    from mnemograph.adapters.qdrant import ProjectionError, QdrantProjectionAdapter
    from mnemograph.db import bootstrap_db

    db_path = Path(tmp_path) / "memory.db"
    bootstrap_db(db_path)

    attempts: list[dict] = []

    def failing_sender(batch):
        attempts.extend(batch)
        raise RuntimeError("boom")

    adapter = QdrantProjectionAdapter(sender=failing_sender)
    claim = {
        "claim_id": "claim-1",
        "subject_entity_id": "Company:Stripe",
        "predicate_id": "has_product",
        "object_type": "entity",
        "object_entity_id": "Product:Billing",
        "object_value": "Product:Billing",
        "claim_text": "Stripe offers Billing.",
        "domain": "product",
        "confidence": 0.91,
        "status": "active",
        "source_id": "source-1",
        "extraction_run_id": "run-1",
    }

    with pytest.raises(ProjectionError):
        adapter.project_claims([claim], vector_lookup={"claim-1": [0.1, 0.2]})

    assert len(attempts) == 1
    assert db_path.exists()


def test_projection_adapters_expose_strict_sender_annotations():
    from mnemograph.adapters.grafeo import GrafeoProjectionAdapter
    from mnemograph.adapters.qdrant import QdrantProjectionAdapter

    qdrant_hint = get_type_hints(QdrantProjectionAdapter)["sender"]
    grafeo_hint = get_type_hints(GrafeoProjectionAdapter)["sender"]

    assert qdrant_hint == Callable[..., None]
    assert grafeo_hint == Callable[..., None]
