# ADR-0002: Content addressing over assigned identifiers

- **Status:** Accepted
- **Date:** 2026-01-01

## Context
A provenance system has to name artifacts: datasets, configurations, checkpoints, and evaluation
results. The naive approach assigns an identifier from a counter or a random UUID when an
artifact is created. That is simple but weak: the same content can appear under many names,
there is no way to tell whether two artifacts are identical without comparing them, and a stored
artifact can be swapped for a different one without its name changing.

## Decision
Identify every artifact by the **sha256 hash of its canonical serialization**. Canonicalization
serializes a value to JSON with sorted keys and no insignificant whitespace, so the hash is
stable across processes and machines. A run is also content-addressed: its identity is the hash
of its operation, ordered inputs, parameters, and code version.

## Consequences
- **Deduplication is automatic.** Identical content hashes to the same identifier, so the store
  keeps one copy and re-storing is a no-op.
- **Tampering is evident.** Recomputing an artifact's hash and comparing it to its identifier
  detects any change to the stored bytes.
- **Identity is reproducible.** Rebuilding a pipeline from the same inputs reproduces the same
  identifiers for every artifact, which is what makes verification meaningful.
- The cost is that every value must be canonically serializable and that identifiers are long
  hashes rather than friendly names; a short form is provided for display.
