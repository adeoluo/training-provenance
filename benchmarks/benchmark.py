"""A deterministic micro-benchmark for the provenance system.

Measures pipeline build and verification time across dataset sizes, confirms that
rebuilding is bit-for-bit identical, and reports the content store size (showing
deduplication). Deterministic and offline; run with:

    uv run python benchmarks/benchmark.py
"""

from __future__ import annotations

import time

from training_provenance.pipeline import build_pipeline, make_dataset
from training_provenance.provenance import Ledger
from training_provenance.reproduce import execute, verify_lineage
from training_provenance.store import ContentStore, Kind


def _tracked_run(rows: int) -> tuple[ContentStore, Ledger, str]:
    store = ContentStore()
    ledger = Ledger()
    dataset = store.put(make_dataset(rows=rows, seed=0), Kind.DATASET)
    config = store.put({"l2": 1.0}, Kind.CONFIG)
    (standardized,) = execute(store, ledger, "standardize", [dataset.id], [Kind.DATASET])
    (model,) = execute(store, ledger, "train_ridge", [standardized, config.id], [Kind.CHECKPOINT])
    (metrics,) = execute(store, ledger, "evaluate", [model, standardized], [Kind.METRICS])
    return store, ledger, metrics


def main() -> None:
    print("rows   build ms   verify ms   artifacts   reproduced   metrics r2")
    for rows in (100, 400, 1600):
        start = time.perf_counter()
        store, ledger, metrics = _tracked_run(rows)
        build_ms = (time.perf_counter() - start) * 1000

        start = time.perf_counter()
        verification = verify_lineage(store, ledger, metrics)
        verify_ms = (time.perf_counter() - start) * 1000

        r2 = store.get(metrics)["r2"]
        print(
            f"{rows:<6} {build_ms:>8.1f}   {verify_ms:>9.1f}   {len(store):>9}   "
            f"{verification.reproduced!s:>10}   {r2:>10.4f}"
        )

    first = build_pipeline(seed=0)
    second = build_pipeline(seed=0)
    print(f"deterministic rebuild: metrics id match = {first.metrics_id == second.metrics_id}")
    before = len(first.store)
    first.store.put({"l2": 1.0}, Kind.CONFIG)
    print(f"deduplication: re-storing an existing config kept the store at {before} artifacts")


if __name__ == "__main__":
    main()
