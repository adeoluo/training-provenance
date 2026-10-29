"""Tests for the HTTP service handler (exercised without a socket)."""

from __future__ import annotations

from training_provenance.service import ProvenanceService, handle


def _service() -> ProvenanceService:
    return ProvenanceService.trained(seed=0, l2=1.0)


def test_health_and_ready() -> None:
    service = _service()
    status, payload = handle("GET", "/health", {}, service)
    assert status == 200
    assert payload["artifacts"] == len(service.built.store)
    status, payload = handle("GET", "/ready", {}, service)
    assert status == 200
    assert payload["status"] == "ready"


def test_report_endpoint() -> None:
    service = _service()
    status, payload = handle("GET", "/report", {}, service)
    assert status == 200
    assert payload["reproduced"] is True
    assert payload["runs"] == 3
    assert "r2" in payload["metrics"]


def test_verify_endpoint() -> None:
    service = _service()
    status, payload = handle("GET", "/verify", {}, service)
    assert status == 200
    assert payload["reproduced"] is True
    assert len(payload["runs"]) == 3


def test_lineage_endpoint() -> None:
    service = _service()
    status, payload = handle("POST", "/lineage", {"artifact": service.built.metrics_id}, service)
    assert status == 200
    assert payload["target"] == service.built.metrics_id
    assert [run["operation"] for run in payload["runs"]] == [
        "standardize",
        "train_ridge",
        "evaluate",
    ]


def test_lineage_rejects_bad_and_unknown_artifacts() -> None:
    service = _service()
    status, _ = handle("POST", "/lineage", {"artifact": ""}, service)
    assert status == 400
    status, _ = handle("POST", "/lineage", {"artifact": "sha256:deadbeef"}, service)
    assert status == 404


def test_unknown_route_and_metrics() -> None:
    service = _service()
    status, _ = handle("GET", "/nope", {}, service)
    assert status == 404
    handle("GET", "/report", {}, service)
    rendered = service.metrics.render_prometheus()
    assert "service_requests_total" in rendered
    assert service.metrics.total_errors >= 1
