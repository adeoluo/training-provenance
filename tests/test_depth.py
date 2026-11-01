"""Depth tests: code-hash provenance, end-to-end reproduction, crash recovery, tamper matrix.

These exercise the flagship guarantees of the system:

- the training *code* is fingerprinted and bound to every run, and drift is detected;
- an end-to-end run reproduces bit for bit from scratch;
- an interrupted run resumes from its journal to an identical result, and a damaged journal
  is rejected rather than silently continued;
- every field of every artifact in a lineage, mutated in turn, is caught by verification,
  while a clean lineage verifies.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from training_provenance.codehash import code_fingerprint, code_sources
from training_provenance.endtoend import reproduce, verify_code
from training_provenance.pipeline import build_pipeline
from training_provenance.provenance import Ledger
from training_provenance.recovery import (
    CrashError,
    LedgerCorruptionError,
    PlanMismatchError,
    inspect_journal,
    pipeline_plan,
    resume_plan,
    run_plan,
)
from training_provenance.reproduce import verify_lineage
from training_provenance.store import ContentStore, Kind


# --------------------------------------------------------------------------- #
# Code-hash provenance
# --------------------------------------------------------------------------- #
def test_code_fingerprint_is_deterministic_and_covers_pipeline() -> None:
    assert code_fingerprint() == code_fingerprint()
    sources = code_sources()
    assert set(sources) == {"standardize", "train_ridge", "evaluate"}


def test_build_pipeline_binds_code_fingerprint_to_every_run() -> None:
    built = build_pipeline(seed=0)
    assert built.code_id == code_fingerprint()
    assert built.store.artifact(built.code_id).kind is Kind.CODE
    assert {run.code_version for run in built.ledger.runs.values()} == {built.code_id}


def test_verify_code_detects_drift() -> None:
    built = build_pipeline(seed=0)
    assert verify_code(built)
    # A run recorded under a different code version is code drift.
    drifted = build_pipeline(seed=0, code_version="sha256:not-the-real-source")
    assert not verify_code(drifted)


# --------------------------------------------------------------------------- #
# End-to-end reproduction
# --------------------------------------------------------------------------- #
def test_end_to_end_reproduces_every_hash() -> None:
    report = reproduce(seed=0, l2=1.0)
    assert report.reproduced
    assert report.mismatches == []
    assert set(report.matches) == {"dataset", "config", "code", "model", "metrics"}
    assert all(report.matches.values())
    assert report.code_matches
    assert "r2" in report.metrics
    assert "reproduced" in report.format()


def test_end_to_end_distinguishes_configurations() -> None:
    low = reproduce(seed=0, l2=0.1)
    high = reproduce(seed=0, l2=10.0)
    assert low.reproduced and high.reproduced
    assert low.metrics != high.metrics


# --------------------------------------------------------------------------- #
# Store / ledger durable snapshot round-trip
# --------------------------------------------------------------------------- #
def test_store_snapshot_round_trip() -> None:
    built = build_pipeline(seed=1)
    restored = ContentStore.restore(built.store.snapshot())
    assert restored.ids() == built.store.ids()
    for identifier in built.store.ids():
        assert restored.verify_integrity(identifier)
        assert restored.get(identifier) == built.store.get(identifier)


def test_ledger_snapshot_round_trip() -> None:
    built = build_pipeline(seed=1)
    restored = Ledger.restore(built.ledger.snapshot())
    assert set(restored.runs) == set(built.ledger.runs)
    original = built.ledger.lineage(built.metrics_id)
    assert restored.lineage(built.metrics_id) == original


# --------------------------------------------------------------------------- #
# Crash recovery
# --------------------------------------------------------------------------- #
def test_interrupted_run_resumes_to_identical_result(tmp_path: Path) -> None:
    plan = pipeline_plan(seed=0)
    journal = tmp_path / "run.journal"

    with pytest.raises(CrashError):
        run_plan(plan, journal_path=journal, crash_after=1)

    status = inspect_journal(journal, plan)
    assert status.interrupted
    assert not status.complete
    assert status.completed == 1
    assert "interrupted" in status.format()

    resumed = resume_plan(plan, journal)
    assert resumed.completed == len(plan.steps)

    clean = run_plan(plan)
    # The resumed run is byte-for-byte identical to the uninterrupted one.
    assert resumed.names == clean.names
    final = resumed.resolve("metrics")
    verification = verify_lineage(resumed.store, resumed.ledger, final)
    assert verification.reproduced


def test_resume_after_each_possible_crash_point(tmp_path: Path) -> None:
    plan = pipeline_plan(seed=2)
    clean = run_plan(plan)
    for crash_after in range(1, len(plan.steps) + 1):
        journal = tmp_path / f"crash-{crash_after}.journal"
        with pytest.raises(CrashError):
            run_plan(plan, journal_path=journal, crash_after=crash_after)
        resumed = resume_plan(plan, journal)
        assert resumed.names == clean.names
        assert verify_lineage(resumed.store, resumed.ledger, resumed.resolve("metrics")).reproduced


def test_completed_journal_is_reported_complete(tmp_path: Path) -> None:
    plan = pipeline_plan(seed=0)
    journal = tmp_path / "run.journal"
    run_plan(plan, journal_path=journal)
    status = inspect_journal(journal, plan)
    assert status.complete
    assert not status.interrupted


def test_resume_rejects_corrupted_journal(tmp_path: Path) -> None:
    plan = pipeline_plan(seed=0)
    journal = tmp_path / "run.journal"
    with pytest.raises(CrashError):
        run_plan(plan, journal_path=journal, crash_after=2)

    # Tamper with a stored value inside the journal without changing its key.
    import json

    data = json.loads(journal.read_text(encoding="utf-8"))
    tampered = False
    for entry in data["store"]["artifacts"]:
        if entry["kind"] == Kind.DATASET.value:
            entry["value"] = {"features": [[0.0]], "labels": [0.0]}
            tampered = True
    assert tampered
    journal.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(LedgerCorruptionError):
        resume_plan(plan, journal)


def test_resume_rejects_plan_mismatch(tmp_path: Path) -> None:
    journal = tmp_path / "run.journal"
    with pytest.raises(CrashError):
        run_plan(pipeline_plan(seed=0), journal_path=journal, crash_after=1)
    # A journal from seed=0 must not be resumed against a different plan.
    with pytest.raises(PlanMismatchError):
        resume_plan(pipeline_plan(seed=99), journal)
    assert not inspect_journal(journal, pipeline_plan(seed=99)).plan_matches


# --------------------------------------------------------------------------- #
# Exhaustive tamper matrix
# --------------------------------------------------------------------------- #
def _perturb(value: Any) -> Any:
    """Return a changed copy of a single JSON-compatible value."""

    if isinstance(value, bool):
        return not value
    if isinstance(value, int | float):
        return value + 1
    if isinstance(value, str):
        return value + "~"
    if isinstance(value, list):
        return [_perturb(value[0]), *value[1:]] if value else [0]
    if isinstance(value, dict):
        if value:
            key = next(iter(value))
            return {**value, key: _perturb(value[key])}
        return {"tampered": 0}
    return "tampered"


def _field_mutations(value: Any) -> list[tuple[str, Any]]:
    """Every single-field mutation of a value, labelled by the field changed."""

    mutations: list[tuple[str, Any]] = []
    if isinstance(value, dict):
        for key in value:
            mutations.append((key, {**value, key: _perturb(value[key])}))
    elif isinstance(value, list) and value:
        mutations.append(("element", [_perturb(value[0]), *value[1:]]))
        mutations.append(("length", value[:-1]))
    else:
        mutations.append(("whole", _perturb(value)))
    return mutations


def _lineage_artifacts(built: Any) -> list[str]:
    ids: set[str] = {built.metrics_id}
    for run in built.ledger.runs.values():
        ids.update(run.input_ids)
        ids.update(run.output_ids)
    return sorted(ids)


def test_clean_lineage_verifies() -> None:
    built = build_pipeline(seed=0)
    assert verify_lineage(built.store, built.ledger, built.metrics_id).reproduced


def test_tamper_matrix_detects_every_field_mutation() -> None:
    built = build_pipeline(seed=0)
    checked = 0
    for identifier in _lineage_artifacts(built):
        original = built.store.get(identifier)
        for label, mutated in _field_mutations(original):
            assert mutated != original, f"{identifier} {label} produced no change"
            built.store.corrupt(identifier, mutated)
            verification = verify_lineage(built.store, built.ledger, built.metrics_id)
            assert not verification.reproduced, f"undetected tamper: {identifier} field {label}"
            # Detection is either a byte-level integrity failure or a run that no
            # longer reproduces (a downstream recomputation diverges).
            assert verification.integrity_failures or any(
                not run.reproduced for run in verification.runs
            )
            built.store.corrupt(identifier, original)  # restore for the next mutation
            checked += 1
        # Restoring leaves the whole lineage verifying again.
        assert verify_lineage(built.store, built.ledger, built.metrics_id).reproduced
    assert checked >= 8  # at least two fields across the five lineage artifacts


# --------------------------------------------------------------------------- #
# CLI surface for the new commands
# --------------------------------------------------------------------------- #
def test_cli_reproduce_and_recover(capsys: pytest.CaptureFixture[str]) -> None:
    from training_provenance.cli import main

    main(["reproduce"])
    out = capsys.readouterr().out
    assert "reproduced" in out
    assert "identical" in out

    main(["recover"])
    out = capsys.readouterr().out
    assert "Interrupted" in out
    assert "Resumed metrics identical to uninterrupted run: True" in out
