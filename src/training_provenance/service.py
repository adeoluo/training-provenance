"""A dependency-free HTTP service exposing the provenance ledger.

The service builds the tracked pipeline once at startup and then answers read-only
provenance queries: the summary report, the lineage of an artifact, an artifact
record, and a reproducibility verification. A pure handler is separated from the
socket binding so it can be tested without a network.

Endpoints
---------
``GET  /health``    liveness and store size.
``GET  /ready``     readiness once the pipeline is built.
``GET  /metrics``   per-route request, error, and latency metrics (Prometheus text).
``GET  /report``    artifact and run counts, reproducibility, and the model metrics.
``GET  /verify``    re-execute the lineage and report reproducibility.
``POST /lineage``   body ``{"artifact": str}``; the provenance of an artifact.
"""

from __future__ import annotations

import json
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from training_provenance.evaluation import report
from training_provenance.observability import ServiceMetrics
from training_provenance.pipeline import BuiltPipeline, build_pipeline
from training_provenance.reproduce import verify_lineage

JsonObject = dict[str, Any]


@dataclass(frozen=True)
class ProvenanceService:
    """Holds the built pipeline and answers provenance queries."""

    built: BuiltPipeline
    metrics: ServiceMetrics = field(default_factory=ServiceMetrics)

    @classmethod
    def trained(cls, *, seed: int = 0, l2: float = 1.0) -> ProvenanceService:
        return cls(built=build_pipeline(seed=seed, l2=l2))

    def report(self) -> JsonObject:
        summary = report(self.built)
        return {
            "artifacts": summary.artifacts,
            "runs": summary.runs,
            "reproduced": summary.reproduced,
            "reproduced_fraction": round(summary.reproduced_fraction, 6),
            "integrity_failures": summary.integrity_failures,
            "metrics": summary.metrics,
        }

    def verify(self) -> JsonObject:
        verification = verify_lineage(self.built.store, self.built.ledger, self.built.metrics_id)
        return {
            "reproduced": verification.reproduced,
            "reproduced_fraction": round(verification.reproduced_fraction, 6),
            "runs": [
                {"operation": run.operation, "reproduced": run.reproduced}
                for run in verification.runs
            ],
            "integrity_failures": verification.integrity_failures,
        }

    def lineage(self, artifact_id: str) -> JsonObject:
        return self.built.ledger.lineage(artifact_id)


def _route(
    method: str, path: str, body: Mapping[str, Any], service: ProvenanceService
) -> tuple[int, JsonObject]:
    if method == "GET" and path == "/health":
        return 200, {"status": "ok", "artifacts": len(service.built.store)}
    if method == "GET" and path == "/report":
        return 200, service.report()
    if method == "GET" and path == "/verify":
        return 200, service.verify()
    if method == "POST" and path == "/lineage":
        artifact = body.get("artifact")
        if not isinstance(artifact, str) or not artifact:
            return 400, {"error": "'artifact' must be a non-empty string"}
        if not service.built.store.contains(artifact):
            return 404, {"error": "unknown artifact"}
        return 200, service.lineage(artifact)
    return 404, {"error": f"no route for {method} {path}"}


def handle(
    method: str, path: str, body: Mapping[str, Any], service: ProvenanceService
) -> tuple[int, JsonObject]:
    """Route a request, recording per-route metrics, and return status and payload."""

    if method == "GET" and path == "/ready":
        return 200, {"status": "ready", "artifacts": len(service.built.store)}
    start = time.perf_counter()
    status, payload = _route(method, path, body, service)
    service.metrics.observe(
        f"{method} {path}", (time.perf_counter() - start) * 1000.0, error=status >= 400
    )
    return status, payload


class _Handler(BaseHTTPRequestHandler):  # pragma: no cover - exercised over sockets
    service: ProvenanceService

    def _respond(self, status: int, payload: JsonObject) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self) -> None:
        if self.path == "/metrics":
            body = self.service.metrics.render_prometheus().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        status, payload = handle("GET", self.path, {}, self.service)
        self._respond(status, payload)

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            self._respond(400, {"error": "request body is not valid JSON"})
            return
        status, payload = handle("POST", self.path, body, self.service)
        self._respond(status, payload)

    def log_message(self, *_: Any) -> None:
        return


def serve(host: str = "127.0.0.1", port: int = 8000) -> None:  # pragma: no cover
    """Start the HTTP service (blocking)."""

    handler = type("_BoundHandler", (_Handler,), {"service": ProvenanceService.trained()})
    server = ThreadingHTTPServer((host, port), handler)
    print(f"training-provenance service listening on http://{host}:{port}")
    server.serve_forever()
