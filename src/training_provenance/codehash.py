"""Content fingerprints of the training code itself.

The code that produced an artifact is as much a part of its provenance as the data
and the configuration: the same dataset and configuration run through different code
produce a different model. Because transforms are Python-defined functions registered
by name, the source text of each one can be read with :func:`inspect.getsource` and
hashed into a content identifier, exactly like any other artifact.

Binding that fingerprint to a run's identity (as its ``code_version``) means a change
to the training code yields different run identifiers, so the ledger records *which
code* produced every artifact. Verification re-reads the current source and recomputes
the fingerprint, which detects code drift just as byte-level integrity checks detect
data tampering.
"""

from __future__ import annotations

import inspect

from training_provenance.hashing import content_id
from training_provenance.transforms import get_transform

PIPELINE_OPERATIONS: tuple[str, ...] = ("standardize", "train_ridge", "evaluate")


def _normalize(source: str) -> str:
    """Normalize source text so the fingerprint ignores insignificant whitespace."""

    lines = [line.rstrip() for line in source.expandtabs(4).splitlines()]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)


def code_sources(operations: tuple[str, ...] = PIPELINE_OPERATIONS) -> dict[str, str]:
    """Return the normalized source text of each named transform."""

    return {
        operation: _normalize(inspect.getsource(get_transform(operation)))
        for operation in operations
    }


def code_fingerprint(operations: tuple[str, ...] = PIPELINE_OPERATIONS) -> str:
    """Return a single content identifier over the sources of ``operations``."""

    return content_id(code_sources(operations))
