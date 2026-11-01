"""Command line interface for training provenance."""

from __future__ import annotations

import argparse

from training_provenance.endtoend import reproduce
from training_provenance.evaluation import report
from training_provenance.hashing import short
from training_provenance.pipeline import build_pipeline
from training_provenance.reproduce import verify_lineage


def _cmd_build(args: argparse.Namespace) -> None:
    built = build_pipeline(seed=args.seed, l2=args.l2)
    print("Tracked pipeline:")
    print(f"  {report(built).format()}")
    print("Lineage of the evaluation metrics (roots first):")
    for run in built.ledger.lineage(built.metrics_id)["runs"]:
        inputs = ", ".join(short(identifier) for identifier in run["inputs"])
        outputs = ", ".join(short(identifier) for identifier in run["outputs"])
        print(f"  {run['operation']:<12} [{inputs}] -> [{outputs}]  run {short(run['id'])}")


def _cmd_verify(args: argparse.Namespace) -> None:
    built = build_pipeline(seed=args.seed, l2=args.l2)
    verification = verify_lineage(built.store, built.ledger, built.metrics_id)
    print(f"Reproducible: {verification.reproduced} ({verification.reproduced_fraction:.0%})")
    for run in verification.runs:
        state = "ok" if run.reproduced else "MISMATCH"
        print(f"  {run.operation:<12} {state}")


def _cmd_tamper(args: argparse.Namespace) -> None:
    built = build_pipeline(seed=args.seed, l2=args.l2)
    lineage = built.ledger.lineage(built.metrics_id)
    target = lineage["runs"][0]["outputs"][0]
    print(f"Corrupting standardized dataset artifact {short(target)} ...")
    built.store.corrupt(target, {"features": [[0.0]], "labels": [0.0]})
    verification = verify_lineage(built.store, built.ledger, built.metrics_id)
    print(f"Reproducible after tamper: {verification.reproduced}")
    print(f"Integrity failures detected: {len(verification.integrity_failures)}")
    for run in verification.runs:
        state = "ok" if run.reproduced else "MISMATCH"
        print(f"  {run.operation:<12} {state}")


def _cmd_serve(args: argparse.Namespace) -> None:
    from training_provenance.service import serve

    serve(host=args.host, port=args.port)


def _cmd_reproduce(args: argparse.Namespace) -> None:
    report_ = reproduce(seed=args.seed, l2=args.l2)
    print("End-to-end reproduce (build, then rebuild from scratch):")
    print(f"  {report_.format()}")
    for name, ok in sorted(report_.matches.items()):
        print(f"  {name:<10} {'identical' if ok else 'DRIFTED'}")
    print(f"  {'code':<10} {'matches source' if report_.code_matches else 'DRIFTED'}")


def _cmd_recover(args: argparse.Namespace) -> None:
    import tempfile
    from pathlib import Path

    from training_provenance.recovery import (
        CrashError,
        inspect_journal,
        pipeline_plan,
        resume_plan,
        run_plan,
    )

    plan = pipeline_plan(seed=args.seed, l2=args.l2)
    with tempfile.TemporaryDirectory() as directory:
        journal = Path(directory) / "run.journal"
        try:
            run_plan(plan, journal_path=journal, crash_after=1)
        except CrashError as crash:
            print(f"Interrupted: {crash}")
        status = inspect_journal(journal, plan)
        print(f"Journal on disk: {status.format()}")
        resumed = resume_plan(plan, journal)
        print(f"Resumed to completion: {resumed.completed}/{len(plan.steps)} steps")
        clean = run_plan(plan)
        identical = resumed.resolve("metrics") == clean.resolve("metrics")
        print(f"Resumed metrics identical to uninterrupted run: {identical}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="training-provenance", description=__doc__)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--l2", type=float, default=1.0)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("build", help="run the tracked pipeline and print the lineage")
    sub.add_parser("verify", help="verify the pipeline reproduces bit for bit")
    sub.add_parser("tamper", help="corrupt an artifact and show tamper detection")
    sub.add_parser("reproduce", help="rebuild from scratch and compare every content hash")
    sub.add_parser("recover", help="interrupt a run, then resume it from its journal")

    serve = sub.add_parser("serve", help="start the HTTP service")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)

    handlers = {
        "build": _cmd_build,
        "verify": _cmd_verify,
        "tamper": _cmd_tamper,
        "reproduce": _cmd_reproduce,
        "recover": _cmd_recover,
        "serve": _cmd_serve,
    }
    args = parser.parse_args(argv)
    handlers[args.command](args)


if __name__ == "__main__":
    main()
