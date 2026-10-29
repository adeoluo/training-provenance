"""A tracked end-to-end machine learning pipeline for demonstration.

The pipeline generates a dataset, standardizes it, fits a ridge-regression model,
and evaluates it, recording every step in the ledger and every artifact in the
content store. The result is a lineage graph whose root is the raw dataset and the
training configuration, and whose leaf is the evaluation metrics, each reachable by
provenance traversal and each independently reproducible.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from training_provenance.provenance import Ledger
from training_provenance.reproduce import execute
from training_provenance.store import ContentStore, Kind


def make_dataset(rows: int = 200, columns: int = 4, *, seed: int = 0) -> dict[str, list[Any]]:
    """Generate a deterministic linear-regression dataset."""

    rng = random.Random(seed)
    weights = [rng.uniform(-2.0, 2.0) for _ in range(columns)]
    bias = rng.uniform(-1.0, 1.0)
    features: list[list[float]] = []
    labels: list[float] = []
    for _ in range(rows):
        row = [round(rng.uniform(-3.0, 3.0), 6) for _ in range(columns)]
        noise = rng.gauss(0.0, 0.1)
        label = bias + sum(w * x for w, x in zip(weights, row, strict=True)) + noise
        features.append(row)
        labels.append(round(label, 6))
    return {"features": features, "labels": labels}


@dataclass(frozen=True)
class BuiltPipeline:
    """The store, ledger, and the key artifact identifiers of a tracked run."""

    store: ContentStore
    ledger: Ledger
    dataset_id: str
    config_id: str
    model_id: str
    metrics_id: str


def build_pipeline(*, seed: int = 0, l2: float = 1.0, code_version: str = "1.0.0") -> BuiltPipeline:
    """Run and track the standardize, train, and evaluate pipeline."""

    store = ContentStore()
    ledger = Ledger()

    dataset = store.put(
        make_dataset(seed=seed), Kind.DATASET, {"source": "synthetic", "seed": seed}
    )
    config = store.put({"l2": l2}, Kind.CONFIG, {"model": "ridge"})

    (standardized_id,) = execute(
        store, ledger, "standardize", [dataset.id], [Kind.DATASET], code_version=code_version
    )
    (model_id,) = execute(
        store,
        ledger,
        "train_ridge",
        [standardized_id, config.id],
        [Kind.CHECKPOINT],
        code_version=code_version,
    )
    (metrics_id,) = execute(
        store,
        ledger,
        "evaluate",
        [model_id, standardized_id],
        [Kind.METRICS],
        code_version=code_version,
    )
    return BuiltPipeline(
        store=store,
        ledger=ledger,
        dataset_id=dataset.id,
        config_id=config.id,
        model_id=model_id,
        metrics_id=metrics_id,
    )
