"""Training Provenance - content-addressed lineage and reproducibility tracking."""

from training_provenance.codehash import code_fingerprint, code_sources
from training_provenance.endtoend import ReproductionReport, reproduce, verify_code
from training_provenance.evaluation import ProvenanceReport, report
from training_provenance.hashing import content_id, short
from training_provenance.pipeline import BuiltPipeline, build_pipeline, make_dataset
from training_provenance.provenance import Ledger, Run, run_id
from training_provenance.recovery import (
    CrashError,
    JournalStatus,
    LedgerCorruptionError,
    Plan,
    PlanMismatchError,
    Root,
    RunState,
    Step,
    inspect_journal,
    pipeline_plan,
    resume_plan,
    run_plan,
    verify_state,
)
from training_provenance.reproduce import (
    LineageVerification,
    RunVerification,
    execute,
    verify_lineage,
    verify_run,
)
from training_provenance.store import Artifact, ContentStore, Kind

__version__ = "0.1.1"

__all__ = [
    "Artifact",
    "BuiltPipeline",
    "ContentStore",
    "CrashError",
    "JournalStatus",
    "Kind",
    "Ledger",
    "LedgerCorruptionError",
    "LineageVerification",
    "Plan",
    "PlanMismatchError",
    "ProvenanceReport",
    "ReproductionReport",
    "Root",
    "Run",
    "RunState",
    "RunVerification",
    "Step",
    "build_pipeline",
    "code_fingerprint",
    "code_sources",
    "content_id",
    "execute",
    "inspect_journal",
    "make_dataset",
    "pipeline_plan",
    "report",
    "reproduce",
    "resume_plan",
    "run_id",
    "run_plan",
    "short",
    "verify_code",
    "verify_lineage",
    "verify_run",
    "verify_state",
]
