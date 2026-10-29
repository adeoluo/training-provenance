"""Summary reporting over a tracked pipeline."""

from __future__ import annotations

from dataclasses import dataclass

from training_provenance.pipeline import BuiltPipeline
from training_provenance.reproduce import LineageVerification, verify_lineage
from training_provenance.store import Kind


@dataclass(frozen=True)
class ProvenanceReport:
    """A summary of a tracked pipeline and its reproducibility."""

    artifacts: int
    runs: int
    reproduced: bool
    reproduced_fraction: float
    integrity_failures: int
    metrics: dict[str, float]

    def format(self) -> str:
        status = "reproduced" if self.reproduced else "NOT reproduced"
        return (
            f"artifacts {self.artifacts}  runs {self.runs}  "
            f"{status} ({self.reproduced_fraction:.0%} of runs)  "
            f"integrity failures {self.integrity_failures}  "
            f"metrics {self.metrics}"
        )


def kind_counts(built: BuiltPipeline) -> dict[str, int]:
    counts: dict[str, int] = {kind.value: 0 for kind in Kind}
    for identifier in list_artifacts(built):
        counts[built.store.artifact(identifier).kind.value] += 1
    return counts


def list_artifacts(built: BuiltPipeline) -> list[str]:
    identifiers: set[str] = set()
    for run in built.ledger.runs.values():
        identifiers.update(run.input_ids)
        identifiers.update(run.output_ids)
    identifiers.add(built.dataset_id)
    identifiers.add(built.config_id)
    return sorted(identifiers)


def report(built: BuiltPipeline) -> ProvenanceReport:
    """Verify the pipeline and summarize it."""

    verification: LineageVerification = verify_lineage(built.store, built.ledger, built.metrics_id)
    return ProvenanceReport(
        artifacts=len(built.store),
        runs=len(built.ledger.runs),
        reproduced=verification.reproduced,
        reproduced_fraction=verification.reproduced_fraction,
        integrity_failures=len(verification.integrity_failures),
        metrics=built.store.get(built.metrics_id),
    )
