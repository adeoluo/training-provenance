# Operations Guide - Training Provenance

The service is a single stateless process that builds the tracked pipeline once at startup and
then answers read-only provenance queries. It has zero runtime dependencies and binds only the
Python standard library HTTP server.

## Service contract

| Method | Path | Request | Response |
|---|---|---|---|
| GET | `/health` | none | `{"status": "ok", "artifacts": int}` |
| GET | `/ready` | none | `{"status": "ready", "artifacts": int}` once built |
| GET | `/metrics` | none | Prometheus text: per-route requests, errors, latency histogram |
| GET | `/report` | none | artifact and run counts, reproducibility, and the model metrics |
| GET | `/verify` | none | per-run reproducibility and integrity failures |
| POST | `/lineage` | `{"artifact": str}` | the full provenance of an artifact |

## Startup
The pipeline is built once when the process starts and takes a few milliseconds. Until it
completes the process is not listening, so a readiness probe against `/ready` fails closed.

## Constraints and limits
- `/lineage` requires a non-empty string `artifact` identifier; unknown identifiers return 404.
- Request bodies that are not valid JSON return a 400 without touching the ledger.
- The service is read-only: it never mutates the tracked pipeline in response to a request.

## Observability
- `/metrics` exposes `service_requests_total`, `service_errors_total`,
  `service_request_duration_ms_sum`, and a latency histogram, all labeled by route.
- Scrape `/metrics` with Prometheus and alert on error rate and p99 latency per route. The
  `/report` and `/verify` endpoints re-verify the lineage on each call; a production deployment
  would cache the verification and expose the cached result.

## Health and readiness
- **Liveness:** `/health` returns as soon as the process is up.
- **Readiness:** `/ready` returns ready only after the pipeline is built.

## Failure modes and responses
- **Malformed or unknown artifact:** 400 or 404, counted in metrics.
- **Unknown route:** 404, counted in metrics.
- **Process restart:** safe at any time; the pipeline is deterministic, so restarts reproduce
  identical artifacts, identifiers, and lineage.

## Deployment
Run the container from the provided `Dockerfile` behind a reverse proxy that terminates TLS and
enforces connection and rate limits. The process is stateless, so scaling out is a matter of
running more replicas behind a load balancer (see [SCALING.md](SCALING.md)).
