"""Durable, journaled execution with crash recovery.

A long pipeline can be interrupted -- a machine dies, a job is pre-empted -- part way
through. This module runs a declarative :class:`Plan` one step at a time and, after every
completed step, writes a *journal*: a content-addressed snapshot of the store, the ledger,
and the name-to-identifier bindings produced so far. If the run is interrupted, the journal
on disk is a consistent prefix of the work. Resuming loads that prefix, verifies that every
recorded run still reproduces and every stored artifact still hashes to its identifier
(so a damaged journal is rejected rather than silently continued), and then executes only
the remaining steps.

Because execution is deterministic and artifacts are content-addressed, a resumed run yields
byte-for-byte the same identifiers as an uninterrupted one.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from training_provenance.codehash import PIPELINE_OPERATIONS, code_sources
from training_provenance.hashing import content_id
from training_provenance.pipeline import make_dataset
from training_provenance.provenance import Ledger
from training_provenance.reproduce import execute, verify_lineage
from training_provenance.store import ContentStore, Kind


class CrashError(RuntimeError):
    """Raised by the runner to simulate an interrupted run after some steps complete."""


class LedgerCorruptionError(RuntimeError):
    """Raised when a journal fails integrity verification and must not be resumed."""


class PlanMismatchError(RuntimeError):
    """Raised when a journal was written for a different plan than the one resuming it."""


@dataclass(frozen=True)
class Root:
    """A root input artifact placed in the store before any step runs."""

    name: str
    value: Any
    kind: Kind
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Step:
    """One operation consuming named inputs and producing named outputs."""

    operation: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    output_kinds: tuple[Kind, ...]


@dataclass(frozen=True)
class Plan:
    """A root set and an ordered list of steps, executed under one code version."""

    roots: tuple[Root, ...]
    steps: tuple[Step, ...]
    code_version: str

    def fingerprint(self) -> str:
        return content_id(
            {
                "code_version": self.code_version,
                "roots": [
                    {"name": r.name, "kind": r.kind.value, "content": content_id(r.value)}
                    for r in self.roots
                ],
                "steps": [
                    {
                        "operation": s.operation,
                        "inputs": list(s.inputs),
                        "outputs": list(s.outputs),
                        "kinds": [k.value for k in s.output_kinds],
                    }
                    for s in self.steps
                ],
            }
        )


@dataclass
class RunState:
    """The mutable state of a (possibly partial) journaled run."""

    store: ContentStore
    ledger: Ledger
    names: dict[str, str]
    completed: int

    def resolve(self, name: str) -> str:
        return self.names[name]


@dataclass(frozen=True)
class JournalStatus:
    """A report on a journal found on disk relative to a plan."""

    completed: int
    total: int
    plan_matches: bool

    @property
    def complete(self) -> bool:
        return self.plan_matches and self.completed >= self.total

    @property
    def interrupted(self) -> bool:
        return self.plan_matches and 0 <= self.completed < self.total

    def format(self) -> str:
        if not self.plan_matches:
            return "journal was written for a different plan"
        state = "complete" if self.complete else "interrupted"
        return f"{state}: {self.completed}/{self.total} steps recorded"


def pipeline_plan(*, seed: int = 0, l2: float = 1.0) -> Plan:
    """The real standardize -> train_ridge -> evaluate pipeline as a durable plan."""

    code = code_sources()
    roots = (
        Root(
            "dataset", make_dataset(seed=seed), Kind.DATASET, {"source": "synthetic", "seed": seed}
        ),
        Root("config", {"l2": l2}, Kind.CONFIG, {"model": "ridge"}),
        Root("code", code, Kind.CODE, {"operations": list(PIPELINE_OPERATIONS)}),
    )
    steps = (
        Step("standardize", ("dataset",), ("standardized",), (Kind.DATASET,)),
        Step("train_ridge", ("standardized", "config"), ("model",), (Kind.CHECKPOINT,)),
        Step("evaluate", ("model", "standardized"), ("metrics",), (Kind.METRICS,)),
    )
    return Plan(roots=roots, steps=steps, code_version=content_id(code))


def _fresh_state(plan: Plan) -> RunState:
    store = ContentStore()
    names: dict[str, str] = {}
    for root in plan.roots:
        names[root.name] = store.put(root.value, root.kind, root.metadata).id
    return RunState(store=store, ledger=Ledger(), names=names, completed=0)


def _run_step(state: RunState, step: Step, plan: Plan) -> None:
    input_ids = [state.resolve(name) for name in step.inputs]
    output_ids = execute(
        state.store,
        state.ledger,
        step.operation,
        input_ids,
        list(step.output_kinds),
        code_version=plan.code_version,
    )
    for name, identifier in zip(step.outputs, output_ids, strict=True):
        state.names[name] = identifier
    state.completed += 1


def _persist(journal_path: Path, state: RunState, plan: Plan) -> None:
    journal_path.write_text(
        json.dumps(
            {
                "plan_fingerprint": plan.fingerprint(),
                "completed": state.completed,
                "total": len(plan.steps),
                "names": state.names,
                "store": state.store.snapshot(),
                "ledger": state.ledger.snapshot(),
            }
        ),
        encoding="utf-8",
    )


def _load_state(journal: dict[str, Any]) -> RunState:
    return RunState(
        store=ContentStore.restore(journal["store"]),
        ledger=Ledger.restore(journal["ledger"]),
        names=dict(journal["names"]),
        completed=int(journal["completed"]),
    )


def inspect_journal(journal_path: Path, plan: Plan) -> JournalStatus:
    """Report whether a journal on disk is complete, interrupted, or for another plan."""

    journal = json.loads(journal_path.read_text(encoding="utf-8"))
    return JournalStatus(
        completed=int(journal["completed"]),
        total=len(plan.steps),
        plan_matches=journal.get("plan_fingerprint") == plan.fingerprint(),
    )


def verify_state(state: RunState) -> None:
    """Re-verify every recorded run and every stored artifact; raise on any damage."""

    for run in state.ledger.runs.values():
        verification = verify_lineage(state.store, state.ledger, run.output_ids[0])
        if not verification.reproduced:
            raise LedgerCorruptionError(f"journal integrity check failed at run {run.operation!r}")


def run_plan(
    plan: Plan, *, journal_path: Path | None = None, crash_after: int | None = None
) -> RunState:
    """Execute ``plan`` from the start, journaling after each step.

    If ``crash_after`` is set, execute that many steps (journaling each) and then raise
    :class:`CrashError`, leaving a consistent partial journal behind.
    """

    state = _fresh_state(plan)
    for index, step in enumerate(plan.steps):
        _run_step(state, step, plan)
        if journal_path is not None:
            _persist(journal_path, state, plan)
        if crash_after is not None and index + 1 >= crash_after:
            raise CrashError(f"interrupted after {state.completed} of {len(plan.steps)} steps")
    return state


def resume_plan(plan: Plan, journal_path: Path) -> RunState:
    """Resume an interrupted run from its journal, after verifying the recorded prefix."""

    journal = json.loads(journal_path.read_text(encoding="utf-8"))
    if journal.get("plan_fingerprint") != plan.fingerprint():
        raise PlanMismatchError("journal was written for a different plan")
    state = _load_state(journal)
    verify_state(state)
    for step in plan.steps[state.completed :]:
        _run_step(state, step, plan)
        _persist(journal_path, state, plan)
    return state
