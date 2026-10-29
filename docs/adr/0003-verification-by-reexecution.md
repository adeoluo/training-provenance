# ADR-0003: Reproducibility verification by re-execution

- **Status:** Accepted
- **Date:** 2026-01-01

## Context
Recording lineage is necessary but not sufficient. A provenance claim is only credible if it can
be checked: given the recorded inputs, do they actually produce the recorded outputs, and are the
stored artifacts intact? There are two ways to gain confidence. One is to trust metadata and
signatures. The other is to re-run the computation and compare.

## Decision
Verify reproducibility by **re-execution**. Each transform is a deterministic function registered
by name. To verify a run, its recorded inputs are fetched from the store, the transform is
re-executed, and the recomputed output identifiers are compared to the recorded ones. To verify a
whole pipeline, the lineage of a target artifact is walked, every run is re-executed, and every
stored artifact is checked to still hash to its identifier.

## Consequences
- Reproducibility is **checked, not asserted**, and a failure is **localized**: the specific run
  whose outputs no longer match is identified, and the specific corrupted artifact is named.
- The approach depends on **determinism**. Transforms must be deterministic for re-execution to
  reproduce identical bytes; nondeterministic steps must have their randomness pinned or captured
  first, which is recorded as a limitation and a roadmap item.
- Verification cost is the cost of re-running the pipeline. For large pipelines this motivates
  partial, Merkle-style verification, which is a roadmap item.
