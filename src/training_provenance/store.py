"""A content-addressed artifact store.

Artifacts are datasets, configurations, checkpoints, and evaluation results. The
store keeps each distinct value exactly once, keyed by its content identifier, so
storing the same content twice is a no-op and deduplication is automatic. An
artifact record carries its identifier, a kind, its size in canonical bytes, and
free-form metadata that does not affect the identity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from training_provenance.hashing import canonical_bytes, content_id


class Kind(StrEnum):
    """The kind of a tracked artifact."""

    DATASET = "dataset"
    CONFIG = "config"
    CHECKPOINT = "checkpoint"
    METRICS = "metrics"


@dataclass(frozen=True)
class Artifact:
    """A content-addressed record describing a stored value."""

    id: str
    kind: Kind
    size_bytes: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ContentStore:
    """A deduplicating, content-addressed store of artifact values and records."""

    _values: dict[str, Any] = field(default_factory=dict)
    _artifacts: dict[str, Artifact] = field(default_factory=dict)

    def put(self, value: Any, kind: Kind, metadata: dict[str, Any] | None = None) -> Artifact:
        identifier = content_id(value)
        if identifier not in self._values:
            self._values[identifier] = value
            self._artifacts[identifier] = Artifact(
                id=identifier,
                kind=kind,
                size_bytes=len(canonical_bytes(value)),
                metadata=metadata or {},
            )
        return self._artifacts[identifier]

    def get(self, identifier: str) -> Any:
        if identifier not in self._values:
            raise KeyError(f"unknown artifact {identifier}")
        return self._values[identifier]

    def artifact(self, identifier: str) -> Artifact:
        if identifier not in self._artifacts:
            raise KeyError(f"unknown artifact {identifier}")
        return self._artifacts[identifier]

    def contains(self, identifier: str) -> bool:
        return identifier in self._values

    def verify_integrity(self, identifier: str) -> bool:
        """Recompute the stored value's content identifier and compare it to its key."""

        return self.contains(identifier) and content_id(self._values[identifier]) == identifier

    def corrupt(self, identifier: str, value: Any) -> None:
        """Replace a stored value without changing its key, to simulate tampering.

        This exists so integrity verification can be demonstrated: after a corrupt
        call the stored bytes no longer hash to their identifier, which
        ``verify_integrity`` detects.
        """

        if identifier not in self._values:
            raise KeyError(f"unknown artifact {identifier}")
        self._values[identifier] = value

    def __len__(self) -> int:
        return len(self._values)
