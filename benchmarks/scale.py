"""A large-workload scale benchmark for the provenance pipeline.

Builds the tracked standardize -> train_ridge -> evaluate pipeline over
progressively larger synthetic datasets and reports, per workload, the wall-clock
build time, throughput in dataset rows ingested per second, the peak traced memory,
the fraction of the lineage that verifies (content-addressed reproducibility), and
the model's held-in R squared. It complements ``benchmark.py`` (three fixed sizes)
by showing how content hashing, ingestion, and lineage verification scale as the
dataset grows.

Timing and memory are captured in separate phases on purpose: ``tracemalloc``
instruments every allocation and perturbs the wall-clock, while the peak footprint
is governed by the resident dataset and its content-addressed artifacts, so a
single traced pass measures it faithfully. Deterministic and offline; run with:

    uv run python benchmarks/scale.py
"""

from __future__ import annotations

import time
import tracemalloc
from dataclasses import dataclass

from training_provenance.pipeline import make_dataset
from training_provenance.provenance import Ledger
from training_provenance.reproduce import execute, verify_lineage
from training_provenance.store import ContentStore, Kind

WORKLOADS: tuple[int, ...] = (1000, 4000, 16000)
_SEED = 0


def _tracked_run(rows: int) -> tuple[ContentStore, Ledger, str]:
    store = ContentStore()
    ledger = Ledger()
    dataset = store.put(make_dataset(rows=rows, seed=_SEED), Kind.DATASET)
    config = store.put({"l2": 1.0}, Kind.CONFIG)
    (standardized,) = execute(store, ledger, "standardize", [dataset.id], [Kind.DATASET])
    (model,) = execute(store, ledger, "train_ridge", [standardized, config.id], [Kind.CHECKPOINT])
    (metrics,) = execute(store, ledger, "evaluate", [model, standardized], [Kind.METRICS])
    return store, ledger, metrics


@dataclass(frozen=True)
class ScalePoint:
    """One row of the scale table for a single workload size."""

    size: int
    seconds: float
    throughput: float
    peak_mib: float
    verified: float
    r2: float


def measure(rows: int) -> ScalePoint:
    """Build and verify a tracked pipeline over ``rows`` rows and measure the cost."""

    tracemalloc.start()
    tracemalloc.reset_peak()
    _tracked_run(rows)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    start = time.perf_counter()
    store, ledger, metrics = _tracked_run(rows)
    verification = verify_lineage(store, ledger, metrics)
    seconds = time.perf_counter() - start

    return ScalePoint(
        size=rows,
        seconds=seconds,
        throughput=rows / seconds if seconds > 0 else 0.0,
        peak_mib=peak / 1048576,
        verified=verification.reproduced_fraction,
        r2=store.get(metrics)["r2"],
    )


def main() -> None:
    print("Synthetic regression data; a pure-Python, from-scratch provenance system.")
    print("Wall-clock is not competitive with compiled numerical libraries.")
    print("Build and verification run end to end; 'verified' is the reproduced fraction.\n")

    header = f"{'rows':>8}  {'seconds':>8}  {'rows/sec':>10}  {'peak MiB':>9}"
    print(f"{header}  {'verified':>8}  {'r2':>7}")
    for size in WORKLOADS:
        point = measure(size)
        print(
            f"{point.size:>8}  {point.seconds:>8.3f}  {point.throughput:>10.0f}  "
            f"{point.peak_mib:>9.2f}  {point.verified:>8.3f}  {point.r2:>7.4f}"
        )


if __name__ == "__main__":
    main()
