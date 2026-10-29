# Evaluation Report - Training Provenance

> Reproduce with `python -m training_provenance build`, `verify`, and `tamper`, and
> `uv run python benchmarks/benchmark.py`. Everything here is deterministic.

## Setup
- **Pipeline:** a raw dataset and a training configuration feed three deterministic runs,
  `standardize` then `train_ridge` then `evaluate`, producing a standardized dataset, a model
  checkpoint, and evaluation metrics.
- **Tracking:** every artifact is content-addressed and stored once; every run is recorded in the
  lineage ledger with its inputs, parameters, code version, and outputs.

## Reproducibility and integrity

| Property | Result |
|---|---|
| runs reproduced on re-execution | 3 of 3 |
| artifact integrity | all pass |
| deterministic rebuild (same metrics identifier) | yes |
| deduplication (re-storing content is a no-op) | yes, store stays at 5 artifacts |
| tamper detection | corrupting an artifact fails verification and names the run |
| model fit (held-in R squared) | 0.999 |

## Scaling

| dataset rows | build (ms) | verify (ms) | artifacts |
|---:|---:|---:|---:|
| 100 | 1.4 | 0.9 | 5 |
| 400 | 5.2 | 3.4 | 5 |
| 1600 | 20.4 | 13.5 | 5 |

Build and verification time grow linearly with dataset size, while the artifact count stays fixed
because content addressing deduplicates and the pipeline shape is constant.

## Tamper detection in detail
Corrupting the standardized-dataset artifact (replacing its bytes without changing its
identifier) makes the stored value no longer hash to its key. Whole-lineage verification then
reports `reproduced = False`, lists one integrity failure, and marks the `standardize` run as a
mismatch, localizing the fault to the exact step.

## Throughput
The read-only service answers lineage and report queries at over 1,000 requests per second with
low-single-digit millisecond latency; the report endpoint re-verifies the lineage on each call,
which a production deployment would cache.
