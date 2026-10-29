"""Tests for the command line interface and the report helpers."""

from __future__ import annotations

import pytest

from training_provenance.cli import main
from training_provenance.evaluation import kind_counts, list_artifacts, report
from training_provenance.pipeline import build_pipeline


def test_cli_build_verify_and_tamper(capsys: pytest.CaptureFixture[str]) -> None:
    main(["build"])
    build_output = capsys.readouterr().out
    assert "standardize" in build_output
    assert "train_ridge" in build_output

    main(["verify"])
    verify_output = capsys.readouterr().out
    assert "Reproducible: True" in verify_output

    main(["tamper"])
    tamper_output = capsys.readouterr().out
    assert "Reproducible after tamper: False" in tamper_output
    assert "Integrity failures detected: 1" in tamper_output


def test_report_and_kind_counts() -> None:
    built = build_pipeline(seed=0)
    summary = report(built)
    assert summary.reproduced
    assert summary.runs == 3
    assert "reproduced" in summary.format()

    counts = kind_counts(built)
    assert counts["dataset"] >= 1
    assert counts["checkpoint"] >= 1
    assert counts["metrics"] >= 1
    assert len(list_artifacts(built)) == len(built.store)
