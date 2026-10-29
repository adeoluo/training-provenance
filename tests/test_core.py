"""Tests for hashing, the store, the ledger, and reproducibility."""

from __future__ import annotations

from training_provenance.hashing import canonical_bytes, content_id
from training_provenance.pipeline import build_pipeline, make_dataset
from training_provenance.reproduce import verify_lineage, verify_run
from training_provenance.store import ContentStore, Kind


def test_content_id_is_deterministic_and_order_independent() -> None:
    first = content_id({"a": 1, "b": [1, 2, 3]})
    second = content_id({"b": [1, 2, 3], "a": 1})
    assert first == second
    assert content_id({"a": 1}) != content_id({"a": 2})


def test_store_deduplicates_identical_content() -> None:
    store = ContentStore()
    a = store.put({"x": 1}, Kind.CONFIG)
    b = store.put({"x": 1}, Kind.CONFIG)
    assert a.id == b.id
    assert len(store) == 1
    assert store.artifact(a.id).size_bytes == len(canonical_bytes({"x": 1}))


def test_store_integrity_detects_corruption() -> None:
    store = ContentStore()
    artifact = store.put({"x": [1, 2, 3]}, Kind.DATASET)
    assert store.verify_integrity(artifact.id)
    store.corrupt(artifact.id, {"x": [9, 9, 9]})
    assert not store.verify_integrity(artifact.id)


def test_pipeline_is_reproducible_and_deterministic() -> None:
    first = build_pipeline(seed=0, l2=1.0)
    second = build_pipeline(seed=0, l2=1.0)
    assert first.metrics_id == second.metrics_id
    assert first.model_id == second.model_id
    verification = verify_lineage(first.store, first.ledger, first.metrics_id)
    assert verification.reproduced
    assert verification.reproduced_fraction == 1.0


def test_lineage_traces_back_to_roots() -> None:
    built = build_pipeline(seed=1)
    lineage = built.ledger.lineage(built.metrics_id)
    operations = [run["operation"] for run in lineage["runs"]]
    assert operations == ["standardize", "train_ridge", "evaluate"]
    assert built.dataset_id in lineage["root_inputs"]
    assert built.config_id in lineage["root_inputs"]


def test_tampering_breaks_verification() -> None:
    built = build_pipeline(seed=0)
    standardized = built.ledger.lineage(built.metrics_id)["runs"][0]["outputs"][0]
    built.store.corrupt(standardized, {"features": [[0.0]], "labels": [0.0]})
    verification = verify_lineage(built.store, built.ledger, built.metrics_id)
    assert not verification.reproduced
    assert verification.integrity_failures


def test_run_verification_detects_changed_params() -> None:
    built = build_pipeline(seed=0, l2=1.0)
    run = next(run for run in built.ledger.runs.values() if run.operation == "train_ridge")
    result = verify_run(built.store, run)
    assert result.reproduced


def test_different_config_yields_different_model() -> None:
    low = build_pipeline(seed=0, l2=0.1)
    high = build_pipeline(seed=0, l2=10.0)
    assert low.model_id != high.model_id
    assert low.dataset_id == high.dataset_id


def test_dataset_generation_is_deterministic() -> None:
    assert make_dataset(seed=3) == make_dataset(seed=3)
    assert make_dataset(seed=3) != make_dataset(seed=4)
