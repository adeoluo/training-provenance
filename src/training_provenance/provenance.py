"""The provenance ledger: runs and the lineage DAG.

A run records that an operation consumed an ordered list of input artifacts and a
parameter dictionary, under a declared code version, and produced an ordered list
of output artifacts. The run's identity is the content hash of its operation,
inputs, parameters, and code version, so a run is itself content-addressed: the
same operation on the same inputs is the same run. Edges from input artifacts into
a run and from the run out to its outputs form a directed acyclic lineage graph
that can be traversed to recover the full provenance of any artifact.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from training_provenance.hashing import content_id


@dataclass(frozen=True)
class Run:
    """A content-addressed record of one deterministic transformation."""

    id: str
    operation: str
    input_ids: list[str]
    output_ids: list[str]
    params: dict[str, Any]
    code_version: str


def run_id(operation: str, input_ids: list[str], params: dict[str, Any], code_version: str) -> str:
    """Compute the content-addressed identity of a run from its inputs."""

    return content_id(
        {
            "operation": operation,
            "inputs": input_ids,
            "params": params,
            "code_version": code_version,
        }
    )


@dataclass
class Ledger:
    """Records runs and indexes the lineage graph over artifacts and runs."""

    runs: dict[str, Run] = field(default_factory=dict)
    _producer: dict[str, str] = field(default_factory=dict)

    def record(self, run: Run) -> Run:
        self.runs[run.id] = run
        for output_id in run.output_ids:
            self._producer[output_id] = run.id
        return run

    def producing_run(self, artifact_id: str) -> Run | None:
        producer = self._producer.get(artifact_id)
        return self.runs.get(producer) if producer is not None else None

    def ancestor_runs(self, artifact_id: str) -> list[Run]:
        """All runs upstream of an artifact, in topological order (roots first)."""

        ordered: list[Run] = []
        seen: set[str] = set()

        def visit(current_id: str) -> None:
            run = self.producing_run(current_id)
            if run is None or run.id in seen:
                return
            seen.add(run.id)
            for parent in run.input_ids:
                visit(parent)
            ordered.append(run)

        visit(artifact_id)
        return ordered

    def lineage(self, artifact_id: str) -> dict[str, Any]:
        """A serializable description of the full lineage of an artifact."""

        runs = self.ancestor_runs(artifact_id)
        inputs: set[str] = set()
        outputs: set[str] = set()
        for run in runs:
            inputs.update(run.input_ids)
            outputs.update(run.output_ids)
        roots = sorted(inputs - outputs)
        return {
            "target": artifact_id,
            "runs": [
                {
                    "id": run.id,
                    "operation": run.operation,
                    "inputs": run.input_ids,
                    "outputs": run.output_ids,
                    "params": run.params,
                    "code_version": run.code_version,
                }
                for run in runs
            ],
            "root_inputs": roots,
        }
