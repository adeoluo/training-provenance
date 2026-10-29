"""Deterministic content addressing.

Every artifact in a tracked pipeline is identified by the hash of its canonical
bytes, so identical content always yields the same identifier and any change,
however small, yields a different one. Canonicalization serializes a value to JSON
with sorted keys and no insignificant whitespace, which makes the hash stable
across processes and machines. This is the foundation of the lineage graph:
identifiers are derived from content, not assigned by a counter.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

_PREFIX = "sha256:"


def canonical_bytes(value: Any) -> bytes:
    """Serialize a JSON-compatible value to deterministic, canonical bytes."""

    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("utf-8")


def content_id(value: Any) -> str:
    """Return the content identifier (a sha256 over the canonical bytes)."""

    digest = hashlib.sha256(canonical_bytes(value)).hexdigest()
    return f"{_PREFIX}{digest}"


def short(identifier: str) -> str:
    """A short, human-readable form of a content identifier for display."""

    body = identifier[len(_PREFIX) :] if identifier.startswith(_PREFIX) else identifier
    return body[:12]
