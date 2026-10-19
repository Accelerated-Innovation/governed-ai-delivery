"""Tests for cli/experiment_store.py — bounded, read-only feature reads.

Fixtures are synthetic records on a temporary tree; they test GovKit's
tooling, not any application runtime.
"""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime
from pathlib import Path

import pytest
import yaml

from cli import experiment_store, paths
from cli.experiment_store import assess_feature
from cli.experiments import criteria_digest, inputs_digest, result_digest
from cli.schema_validation import content_digest

EXAMPLES = paths.GOVERNANCE_DIR / "examples" / "experiments"
NOW = datetime.fromisoformat("2026-11-10T00:00:00+00:00")


def write(root: Path, relative: str, content: str | bytes) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, str):
        content = content.encode("utf-8")
    path.write_bytes(content)


def preflight(status: str, **fields) -> str:
    block = yaml.safe_dump(
        {"preflight_outcome": {"status": status, "reason": "Recorded", **fields}},
        sort_keys=False,
    )
    return f"# Architecture Preflight\n\n## 9. Preflight Conclusion\n\n```yaml\n{block}```\n"


def passed_record(root: Path, feature: str = "discovery") -> dict:
    write(root, f"features/{feature}/acceptance.feature", "Feature: discovery\n")
    write(root, "build/ac1.json", '{"violations": 0}\n')
    acceptance = (root / f"features/{feature}/acceptance.feature").read_bytes()
    criteria = [{"id": "AC-1", "statement": "Revoked release never activates", "threshold": "0"}]
    depends_on = []
    result = {
        "observed_at": "2026-11-01T10:00:00Z",
        "evidence_class": "synthetic-fixture",
        "criteria_digest": criteria_digest(criteria),
        "inputs_digest": inputs_digest(depends_on),
        "criteria": [
            {
                "id": "AC-1",
                "outcome": "pass",
                "evidence": [
                    {
                        "path": "build/ac1.json",
                        "digest": content_digest((root / "build/ac1.json").read_bytes()),
                        "producer": "test-run",
                    }
                ],
            }
        ],
        "summary": "Synthetic run.",
        "limitations": [],
    }
    document = {
        "schema_version": 1,
        "kind": "experiment-set",
        "feature": feature,
        "experiments": [
            {
                "id": "EXP-001",
                "title": "Selection boundary",
                "uncertainty": "Does admission precede ranking?",
                "hypothesis": "Yes, with a null option.",
                "decisions_affected": [{"kind": "adr", "reference": "adr/0001.md"}],
                "requirements": [
                    {
                        "path": f"features/{feature}/acceptance.feature",
                        "digest": content_digest(acceptance),
                    }
                ],
                "scope": {"paths": ["src"], "permitted_effects": "none", "excluded": []},
                "conditions": [],
                "oracle": "deterministic-test",
                "required_evidence_class": "synthetic-fixture",
                "acceptance_criteria": criteria,
                "limits": {"budget": "1 day", "stop_when": ["counterexample"]},
                "depends_on": depends_on,
                "status": "passed",
                "result": result,
                "decision": {
                    "outcome": "adopt",
                    "reference": "adr/0001.md",
                    "recorded_at": "2026-11-01T12:00:00Z",
                },
            }
        ],
    }
    write(root, f"features/{feature}/experiments.yaml", yaml.safe_dump(document, sort_keys=False))
    return document


def snapshot(root: Path) -> dict:
    return {
        str(p.relative_to(root)): (p.read_bytes(), p.stat().st_mtime_ns)
        for p in sorted(root.rglob("*"))
        if p.is_file() and not p.is_symlink()
    }


def codes(result, severity=None):
    return sorted(
        f.code for f in result.assessment.findings if severity is None or f.severity == severity
    )


class TestAbsence:
    def test_feature_without_preflight_or_record_returns_none(self, tmp_path):
        (tmp_path / "features" / "discovery").mkdir(parents=True)
        assert assess_feature(tmp_path, tmp_path / "features" / "discovery") is None

    def test_preflight_without_block_returns_none(self, tmp_path):
        write(tmp_path, "features/discovery/architecture_preflight.md", "# Preflight\nAll good.\n")
        assert assess_feature(tmp_path, tmp_path / "features" / "discovery") is None


class TestAssessment:
    def test_record_and_reliance_are_read_and_current(self, tmp_path):
        document = passed_record(tmp_path)
        digest = result_digest(document["experiments"][0]["result"])
        write(
            tmp_path,
            "features/discovery/architecture_preflight.md",
            preflight(
                "approved-for-planning",
                relies_on=[{"experiment": "EXP-001", "result_digest": digest}],
            ),
        )
        result = assess_feature(tmp_path, tmp_path / "features" / "discovery", now=NOW)
        assert result.feature_dir == "features/discovery"
        assert result.assessment.findings == ()
        assert [s.effective for s in result.assessment.experiments] == ["passed"]

    def test_changed_requirement_on_disk_breaks_reliance(self, tmp_path):
        document = passed_record(tmp_path)
        digest = result_digest(document["experiments"][0]["result"])
        write(
            tmp_path,
            "features/discovery/architecture_preflight.md",
            preflight(
                "approved-for-planning",
                relies_on=[{"experiment": "EXP-001", "result_digest": digest}],
            ),
        )
        write(tmp_path, "features/discovery/acceptance.feature", "Feature: discovery v2\n")
        result = assess_feature(tmp_path, tmp_path / "features" / "discovery", now=NOW)
        assert codes(result, "error") == ["stale-reliance"]

    def test_record_without_preflight_is_assessed(self, tmp_path):
        passed_record(tmp_path)
        result = assess_feature(tmp_path, tmp_path / "features" / "discovery", now=NOW)
        assert result.assessment.outcome is None
        assert result.assessment.findings == ()

    def test_reads_another_features_record_for_reliance(self, tmp_path):
        document = passed_record(tmp_path, feature="onboarding")
        digest = result_digest(document["experiments"][0]["result"])
        write(
            tmp_path,
            "features/discovery/architecture_preflight.md",
            preflight(
                "approved-for-planning",
                relies_on=[
                    {
                        "experiment": "EXP-001",
                        "record": "features/onboarding/experiments.yaml",
                        "result_digest": digest,
                    }
                ],
            ),
        )
        result = assess_feature(tmp_path, tmp_path / "features" / "discovery", now=NOW)
        assert result.assessment.findings == ()

    def test_missing_relied_upon_record_is_reported(self, tmp_path):
        write(
            tmp_path,
            "features/discovery/architecture_preflight.md",
            preflight(
                "approved-for-planning",
                relies_on=[
                    {
                        "experiment": "EXP-001",
                        "record": "features/elsewhere/experiments.yaml",
                        "result_digest": "0" * 64,
                    }
                ],
            ),
        )
        result = assess_feature(tmp_path, tmp_path / "features" / "discovery", now=NOW)
        assert codes(result) == ["missing-record"]

    def test_reads_nothing_it_writes(self, tmp_path):
        document = passed_record(tmp_path)
        digest = result_digest(document["experiments"][0]["result"])
        write(
            tmp_path,
            "features/discovery/architecture_preflight.md",
            preflight(
                "approved-for-planning",
                relies_on=[{"experiment": "EXP-001", "result_digest": digest}],
            ),
        )
        before = snapshot(tmp_path)
        assess_feature(tmp_path, tmp_path / "features" / "discovery", now=NOW)
        assert snapshot(tmp_path) == before


class TestUnsafeAndInvalidInput:
    def test_invalid_record_is_a_finding(self, tmp_path):
        write(tmp_path, "features/discovery/experiments.yaml", "kind: a\nkind: b\n")
        result = assess_feature(tmp_path, tmp_path / "features" / "discovery")
        assert codes(result) == ["invalid-record"]

    def test_invalid_outcome_is_a_finding(self, tmp_path):
        write(
            tmp_path,
            "features/discovery/architecture_preflight.md",
            "```yaml\npreflight_outcome:\n  status: aligned\n  reason: x\n```\n",
        )
        result = assess_feature(tmp_path, tmp_path / "features" / "discovery")
        assert codes(result) == ["invalid-outcome"]

    def test_unsafe_reliance_path_is_an_invalid_outcome(self, tmp_path):
        write(
            tmp_path,
            "features/discovery/architecture_preflight.md",
            preflight(
                "approved-for-planning",
                relies_on=[
                    {
                        "experiment": "EXP-001",
                        "record": "../outside.yaml",
                        "result_digest": "0" * 64,
                    }
                ],
            ),
        )
        result = assess_feature(tmp_path, tmp_path / "features" / "discovery")
        assert codes(result) == ["invalid-outcome"]

    def test_oversized_record_is_refused(self, tmp_path, monkeypatch):
        monkeypatch.setattr(experiment_store, "MAX_DOCUMENT_BYTES", 64)
        write(tmp_path, "features/discovery/experiments.yaml", "#" * 65)
        result = assess_feature(tmp_path, tmp_path / "features" / "discovery")
        assert codes(result) == ["invalid-record"]
        assert "byte limit" in result.assessment.findings[0].message

    def test_oversized_evidence_is_unverifiable(self, tmp_path, monkeypatch):
        passed_record(tmp_path)
        monkeypatch.setattr(experiment_store, "MAX_HASHED_BYTES", 4)
        result = assess_feature(tmp_path, tmp_path / "features" / "discovery", now=NOW)
        assert "unverifiable-evidence" in codes(result, "unknown")

    @pytest.mark.skipif(os.name == "nt", reason="symlink creation needs privileges on Windows")
    def test_symlinked_evidence_is_unverifiable(self, tmp_path):
        passed_record(tmp_path)
        target = tmp_path / "build" / "real.json"
        target.write_bytes((tmp_path / "build/ac1.json").read_bytes())
        (tmp_path / "build/ac1.json").unlink()
        (tmp_path / "build/ac1.json").symlink_to(target)
        result = assess_feature(tmp_path, tmp_path / "features" / "discovery", now=NOW)
        assert codes(result) == ["unverifiable-evidence"]

    @pytest.mark.skipif(os.name == "nt", reason="symlink creation needs privileges on Windows")
    def test_symlinked_record_is_refused(self, tmp_path):
        passed_record(tmp_path, feature="onboarding")
        (tmp_path / "features" / "discovery").mkdir(parents=True)
        (tmp_path / "features/discovery/experiments.yaml").symlink_to(
            tmp_path / "features/onboarding/experiments.yaml"
        )
        result = assess_feature(tmp_path, tmp_path / "features" / "discovery")
        assert codes(result) == ["invalid-record"]


EXAMPLE_SCENARIOS = sorted(p.name for p in EXAMPLES.iterdir() if p.is_dir())


def test_bundled_example_scenarios_are_present():
    assert EXAMPLE_SCENARIOS == [
        "boundary",
        "relied",
        "required",
        "revised",
        "stale",
        "synthetic",
    ]


@pytest.mark.parametrize("scenario", EXAMPLE_SCENARIOS)
def test_bundled_example_scenarios_assess_as_documented(tmp_path, scenario):
    source = EXAMPLES / scenario
    expected = json.loads((source / "expected.json").read_text(encoding="utf-8"))
    shutil.copytree(source, tmp_path / scenario)
    root = tmp_path / scenario
    result = assess_feature(
        root, root / "features" / "discovery", now=datetime.fromisoformat(expected["now"])
    )
    assert result is not None
    found = {severity: codes(result, severity) for severity in ("error", "outstanding", "unknown")}
    assert found == expected["findings"]
    assert {s.id: s.effective for s in result.assessment.experiments} == expected["states"]
    assert result.assessment.ready_for_completion is expected["ready"]
    for example in sorted((source / "features" / "discovery").glob("experiments.yaml")):
        assert yaml.safe_load(example.read_text(encoding="utf-8"))["feature"] == "discovery"
