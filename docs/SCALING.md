# Scaling - Training Provenance

This note describes how the system behaves as pipelines and load grow, and the tradeoffs on the
path to a production provenance store.

## Where the time goes
- **Hashing** is linear in artifact size: canonical serialization plus one sha256 pass.
- **Building** a tracked pipeline costs the transforms themselves plus one hash per artifact.
- **Verification** re-executes every run in a target's lineage and re-hashes every artifact, so
  it costs roughly as much as building the pipeline once.

## Request-time scaling
The service is stateless and the pipeline is immutable after startup. A stress benchmark
(`uv run python benchmarks/stress.py`) drives the lineage and report handlers under concurrency.
Lineage queries are graph traversals and are fast; the report and verify endpoints re-execute the
pipeline on each call, which a production deployment would cache so that reads are constant time.
Horizontal scaling is adding replicas behind a load balancer.

## Data scaling
The in-memory, JSON-serialized store suits tractable pipelines. For real training artifacts the
store should be backed by a blob store keyed by the same content hashes, so that deduplication and
integrity carry over while large bytes live outside the process. The lineage ledger stays small
because it records identifiers and metadata, not payloads.

## Tradeoffs on the path to production
- **In-memory versus blob-backed store.** Memory keeps the demonstration self-contained; a blob
  backend is required for large checkpoints and is a natural extension because identifiers are
  already content hashes.
- **Full versus partial verification.** Re-executing an entire lineage is thorough but costs a
  full rebuild. Merkle-style proofs would allow verifying a subtree without the whole store.
- **Determinism versus flexibility.** Verification by re-execution requires deterministic
  transforms. Capturing and pinning sources of nondeterminism (seeds, reduction order) is the
  price of making a step verifiable.

## Limits
The store and ledger are single-process and in memory, ideal for study and modest pipelines but
not for a shared, durable artifact registry. Scaling there is a storage and systems problem; the
content-addressing and lineage model carry over unchanged.
