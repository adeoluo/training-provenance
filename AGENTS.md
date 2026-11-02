# AGENTS.md

Working notes for coding agents and contributors in **Training Provenance**. The [README](README.md)
explains what the project does and why; this file explains how to change it safely.

## Project

Content-addressed provenance tracking for machine learning pipelines: a deduplicating artifact store, a content-addressed lineage DAG, and bit-for-bit reproducibility and integrity verification.

## Layout

- `benchmarks/`: benchmark scripts and recorded results
- `docker-compose.yml`: local container setup
- `docs/`: documentation, architecture diagram source and render, design records
- `src/`: library and service source
- `tests/`: test suite

Key modules:

- `src/training_provenance/__init__.py`: Training Provenance - content-addressed lineage and reproducibility tracking.
- `src/training_provenance/cli.py`: Command line interface for training provenance.
- `src/training_provenance/codehash.py`: Content fingerprints of the training code itself.
- `src/training_provenance/endtoend.py`: An end-to-end, reproduce-and-verify driver for the tracked pipeline.
- `src/training_provenance/evaluation.py`: Summary reporting over a tracked pipeline.
- `src/training_provenance/hashing.py`: Deterministic content addressing.
- `src/training_provenance/observability.py`: In-process request metrics for the HTTP service (Prometheus text exposition).
- `src/training_provenance/pipeline.py`: A tracked end-to-end machine learning pipeline for demonstration.
- `src/training_provenance/provenance.py`: The provenance ledger: runs and the lineage DAG.
- `src/training_provenance/recovery.py`: Durable, journaled execution with crash recovery.
- `src/training_provenance/reproduce.py`: Execution and reproducibility verification.
- `src/training_provenance/service.py`: A standard-library HTTP service exposing the provenance ledger.
- `src/training_provenance/store.py`: A content-addressed artifact store.
- `src/training_provenance/transforms.py`: A registry of deterministic transforms and a small tracked ML pipeline.

## Commands

| Command | Purpose |
|---|---|
| `make help` | Show this help |
| `make setup` | Install dependencies and pre-commit hooks |
| `make format` | Format automatically |
| `make lint` | Lint (no fixes) |
| `make type` | Type-check |
| `make test` | Run tests |
| `make coverage` | Tests with coverage gate |
| `make evaluation` | Reproduce the results table |
| `make run` | Run the application entrypoint |
| `make diagram` | Render architecture diagram to SVG |
| `make docker-build` | Build the image |
| `make docker-up` | Run via docker compose |
| `make clean` | Remove caches and artifacts |
| `make all` | Full local gate (mirror of continuous integration) |
| `make changelog` | Regenerate CHANGELOG.md from Conventional Commits (git-cliff) |
| `make cut-release` | Cut a release locally: version bump, changelog, tag, GitHub release (RELEASE_VERSION=vX.Y.Z optional) |

Run the full local gate (`make all`) before committing; CI runs the same checks.

## Conventions

- Commits follow Conventional Commits (`feat:`, `fix:`, `perf:`, `refactor:`, `docs:`, `test:`, `ci:`, `chore:`).
  The changelog and the next version number are derived from them.
- Every number quoted in the README is produced by a command in this repository. When behavior
  changes, rerun that command and update the number in the same commit.
- When a component is added, removed or renamed, update `docs/architecture/architecture.mmd`
  and re-render `architecture.svg` so the diagram matches the code.
- README sections keep their fixed order. Prose avoids em and en dashes and promotional wording.
- Tests accompany behavior changes; a bug fix comes with a test that fails without it.
- Releases are cut by the maintainer with `make cut-release`, never from CI.

## Python notes

- Python is managed with `uv`; run commands through `uv run` so the locked environment is used.
- Lint and format with `ruff`; type-check with `mypy`; tests use `pytest`.
- Public functions carry type hints and a docstring that states the contract, not the steps.
