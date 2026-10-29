"""Execution and reproducibility verification.

Executing an operation runs its transform on the input artifact values, stores the
outputs in the content store, and records a run in the ledger. Because transforms
are deterministic and artifacts are content-addressed, a run can later be verified
by re-executing it on its recorded inputs and checking that the recomputed output
identifiers match the recorded ones. Verifying a whole pipeline walks the lineage
of a target artifact and verifies every run, plus the byte-level integrity of every
stored artifact, which is what catches silent corruption or tampering.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from training_provenance.hashing import content_id
from training_provenance.provenance import Ledger, Run, run_id
from training_provenance.store import ContentStore, Kind
from training_provenance.transforms import get_transform


def execute(
    store: ContentStore,
    ledger: Ledger,
    operation: str,
    input_ids: list[str],
    output_kinds: list[Kind],
    params: dict[str, Any] | None = None,
    code_version: str = "1.0.0",
) -> list[str]:
    """Run an operation, store its outputs, record the run, and return output ids."""

    params = params or {}
    values = [store.get(identifier) for identifier in input_ids]
    outputs = get_transform(operation)(values, params)
    if len(outputs) != len(output_kinds):
        raise ValueError("operation produced an unexpected number of outputs")
    output_ids = [
        store.put(value, kind).id for value, kind in zip(outputs, output_kinds, strict=True)
    ]
    ledger.record(
        Run(
            id=run_id(operation, input_ids, params, code_version),
            operation=operation,
            input_ids=input_ids,
            output_ids=output_ids,
            params=params,
            code_version=code_version,
        )
    )
    return output_ids


@dataclass(frozen=True)
class RunVerification:
    """The result of re-executing a single run."""

    run_id: str
    operation: str
    reproduced: bool
    expected: list[str]
    recomputed: list[str]


def verify_run(store: ContentStore, run: Run) -> RunVerification:
    """Re-execute a run on its recorded inputs and compare the output identifiers."""

    try:
        values = [store.get(identifier) for identifier in run.input_ids]
        outputs = get_transform(run.operation)(values, run.params)
        recomputed = [content_id(value) for value in outputs]
    except (KeyError, ValueError):
        recomputed = []
    return RunVerification(
        run_id=run.id,
        operation=run.operation,
        reproduced=recomputed == run.output_ids,
        expected=list(run.output_ids),
        recomputed=recomputed,
    )


@dataclass(frozen=True)
class LineageVerification:
    """The result of verifying every run and artifact in a lineage."""

    target: str
    runs: list[RunVerification]
    integrity_failures: list[str]

    @property
    def reproduced(self) -> bool:
        return all(run.reproduced for run in self.runs) and not self.integrity_failures

    @property
    def reproduced_fraction(self) -> float:
        if not self.runs:
            return 1.0
        return sum(1 for run in self.runs if run.reproduced) / len(self.runs)


def verify_lineage(store: ContentStore, ledger: Ledger, target_id: str) -> LineageVerification:
    """Verify the reproducibility of every run and the integrity of every artifact."""

    runs = ledger.ancestor_runs(target_id)
    run_results = [verify_run(store, run) for run in runs]
    artifact_ids: set[str] = {target_id}
    for run in runs:
        artifact_ids.update(run.input_ids)
        artifact_ids.update(run.output_ids)
    integrity_failures = sorted(
        identifier
        for identifier in artifact_ids
        if store.contains(identifier) and not store.verify_integrity(identifier)
    )
    return LineageVerification(
        target=target_id, runs=run_results, integrity_failures=integrity_failures
    )
