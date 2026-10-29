# Case Study - Auditing a model back to its inputs

This walk-through follows a model from its evaluation metrics back to the exact dataset and
configuration that produced it, and then shows what happens when an artifact is tampered with.

## The question
An audit asks a simple question of a trained model: what produced this, and does it reproduce?
Without provenance the answer is a guess. With content-addressed lineage it is a traversal.

## Building the tracked pipeline
The pipeline standardizes a dataset, fits a ridge-regression model, and evaluates it. Each step is
a deterministic transform whose inputs and outputs are content-addressed. Running it records three
runs in the ledger and five artifacts in the store: the raw dataset, the training configuration,
the standardized dataset, the model checkpoint, and the metrics.

## Tracing provenance
Given the metrics identifier, the lineage traversal walks backward through `evaluate`,
`train_ridge`, and `standardize` to the two root inputs: the raw dataset and the configuration.
The audit now has the exact content hashes of everything that produced the model, and because
those hashes are derived from the content, they cannot be pointing at the wrong thing.

## Verifying reproducibility
Verification re-executes each run on its recorded inputs and compares the recomputed output
identifiers to the recorded ones, and re-hashes every artifact. The pipeline reproduces bit for
bit: three of three runs match and every artifact passes its integrity check. Rebuilding the whole
pipeline from scratch yields the same metrics identifier, confirming determinism.

## Detecting tampering
Now corrupt the standardized dataset, replacing its bytes while keeping its identifier. The stored
value no longer hashes to its key. Verification immediately reports a failure: `reproduced` is
false, one integrity failure is listed, and the `standardize` run is marked as a mismatch. The
fault is localized to the exact step, not merely detected.

## The lesson
Provenance is only worth as much as it can be checked. Content addressing makes identity
reproducible and tampering evident, and verification by re-execution turns a provenance record
from a claim into a test. That is the difference between saying a model is reproducible and being
able to prove it.
