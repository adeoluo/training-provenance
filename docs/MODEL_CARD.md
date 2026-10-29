# Model / System Card - Training Provenance

## Overview
- **What it is:** a from-scratch, content-addressed provenance system for machine learning
  pipelines, with a deduplicating store, a lineage DAG, and reproducibility and integrity
  verification. Zero runtime dependencies.
- **Base model(s):** not applicable; the tracked demonstration model is a ridge regression fit by
  closed form.
- **Version and date:** 1.0, 2026-01-01.

## Intended use
- **Primary use cases:** teaching and demonstrating content addressing, lineage tracking, and
  reproducibility verification; a reference implementation for provenance and audit tooling.
- **Primary users:** engineers and researchers building reproducible training pipelines and model
  audits.

## Out-of-scope / prohibited use
- A drop-in replacement for a production artifact store. Artifacts are kept in memory and
  serialized as JSON, which suits tractable pipelines, not terabyte checkpoints.

## Performance
- The tracked pipeline reproduces bit for bit (3 of 3 runs, full integrity), rebuilds
  deterministically to the same identifiers, deduplicates identical content, and detects
  tampering with the specific run pinpointed. See [`EVALUATION_REPORT.md`](EVALUATION_REPORT.md).

## Risks and limitations
- Verification requires deterministic transforms; nondeterminism must be pinned or captured.
- The in-memory JSON store is unsuitable for very large artifacts.
- The demonstration transforms are deliberately small.

## Safety mitigations
- The HTTP service is read-only and validates that a requested artifact identifier is a known,
  non-empty string before returning its lineage.

## Environmental / cost footprint
- Building and verifying the pipeline takes milliseconds of single-core CPU time, so the energy
  footprint is negligible.
