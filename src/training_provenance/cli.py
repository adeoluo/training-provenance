"""Command line interface for training provenance."""

from __future__ import annotations

import argparse

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


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="training-provenance", description=__doc__)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--l2", type=float, default=1.0)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("build", help="run the tracked pipeline and print the lineage")
    sub.add_parser("verify", help="verify the pipeline reproduces bit for bit")
    sub.add_parser("tamper", help="corrupt an artifact and show tamper detection")

    serve = sub.add_parser("serve", help="start the HTTP service")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)

    handlers = {
        "build": _cmd_build,
        "verify": _cmd_verify,
        "tamper": _cmd_tamper,
        "serve": _cmd_serve,
    }
    args = parser.parse_args(argv)
    handlers[args.command](args)


if __name__ == "__main__":
    main()
