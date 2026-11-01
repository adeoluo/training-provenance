"""An end-to-end, reproduce-and-verify driver for the tracked pipeline.

This ties the pieces together into the workflow a provenance system exists to support:
run a real (if small) training pipeline that records every artifact -- dataset,
configuration, code fingerprint, model, and metrics -- then *reproduce* it from scratch
and confirm that every recorded content hash is identical, and that the current source
still matches the code fingerprint bound to the run. A single mismatch anywhere means the
result is not reproducible, and the field that drifted is named.
"""

from __future__ import annotations

from dataclasses import dataclass

from training_provenance.codehash import code_fingerprint
from training_provenance.pipeline import BuiltPipeline, build_pipeline
from training_provenance.reproduce import verify_lineage


@dataclass(frozen=True)
class ReproductionReport:
    """The outcome of rebuilding a tracked pipeline and comparing it to the original."""

    matches: dict[str, bool]
    lineage_reproduced: bool
    code_matches: bool
    metrics: dict[str, float]

    @property
    def reproduced(self) -> bool:
        """True only when every artifact hash, the lineage, and the code all match."""

        return all(self.matches.values()) and self.lineage_reproduced and self.code_matches

    @property
    def mismatches(self) -> list[str]:
        return sorted(name for name, ok in self.matches.items() if not ok)

    def format(self) -> str:
        status = "reproduced" if self.reproduced else "NOT reproduced"
        detail = "all artifact hashes identical" if self.reproduced else f"drift: {self.mismatches}"
        return f"end-to-end {status}  ({detail})  metrics {self.metrics}"


def verify_code(built: BuiltPipeline) -> bool:
    """Recompute the source fingerprint and confirm it matches what the ledger recorded.

    The code artifact's identity is the fingerprint, and every run was recorded under
    that same fingerprint as its ``code_version``; both must still match the current
    source, or the code has drifted from what produced the artifacts.
    """

    current = code_fingerprint()
    if current != built.code_id:
        return False
    return all(run.code_version == current for run in built.ledger.runs.values())


def reproduce(*, seed: int = 0, l2: float = 1.0) -> ReproductionReport:
    """Build the pipeline twice and confirm every recorded content hash is identical."""

    original = build_pipeline(seed=seed, l2=l2)
    rebuilt = build_pipeline(seed=seed, l2=l2)
    matches = {
        "dataset": original.dataset_id == rebuilt.dataset_id,
        "config": original.config_id == rebuilt.config_id,
        "code": original.code_id == rebuilt.code_id,
        "model": original.model_id == rebuilt.model_id,
        "metrics": original.metrics_id == rebuilt.metrics_id,
    }
    lineage = verify_lineage(rebuilt.store, rebuilt.ledger, rebuilt.metrics_id)
    return ReproductionReport(
        matches=matches,
        lineage_reproduced=lineage.reproduced,
        code_matches=verify_code(rebuilt),
        metrics=rebuilt.store.get(rebuilt.metrics_id),
    )
