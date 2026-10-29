"""A production-style stress benchmark for the provenance service.

Builds the pipeline once, then drives the lineage and verify handlers under
sustained, concurrent load and reports throughput with p50, p95, and p99 latency.
Deterministic and offline; run with:

    uv run python benchmarks/stress.py
"""

from __future__ import annotations

import random
import statistics
import time
from concurrent.futures import ThreadPoolExecutor

from training_provenance.service import ProvenanceService, handle


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(fraction * len(ordered)))]


def main() -> None:
    service = ProvenanceService.trained(seed=0)
    artifact = service.built.metrics_id
    rng = random.Random(0)
    requests = []
    for _ in range(5000):
        if rng.random() < 0.5:
            requests.append(("POST", "/lineage", {"artifact": artifact}))
        else:
            requests.append(("GET", "/report", {}))

    def one(request: tuple[str, str, dict[str, object]]) -> float:
        method, path, body = request
        start = time.perf_counter()
        handle(method, path, body, service)
        return (time.perf_counter() - start) * 1000

    print(f"Requests: {len(requests)}")
    for workers in (1, 4, 8):
        start = time.perf_counter()
        with ThreadPoolExecutor(max_workers=workers) as pool:
            latencies = list(pool.map(one, requests))
        wall = time.perf_counter() - start
        print(
            f"workers={workers:<2}  "
            f"throughput={len(requests) / wall:>8.0f} req/s  "
            f"p50={statistics.median(latencies):>6.3f} ms  "
            f"p95={_percentile(latencies, 0.95):>6.3f} ms  "
            f"p99={_percentile(latencies, 0.99):>6.3f} ms"
        )


if __name__ == "__main__":
    main()
