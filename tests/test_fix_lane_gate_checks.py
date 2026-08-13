"""Behavior tests for the fix-lane gate's embedded checker.

This gate exists because `govkit validate` structurally cannot do its job:
validate is a working-tree tool, so it can prove a fix record is internally
consistent but not that its declarations match what the PR actually changed.
Only the diff can, and only CI has it.

Following `tests/test_dbt_gate_checks.py` and `tests/test_eval_gate_checks.py`:
extract the heredoc, execute it against fixtures, and pin the two platform
embeddings identical so they cannot drift.

The gate is deliberately self-contained — it never invokes govkit. Delegating
would make a blocking gate depend on an unpinned PyPI release, and
`run_validation` short-circuits to exit 0 when the marker is missing or stale,
so a gate calling it could be disabled from inside the PR under review.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
GATE_PATHS = {
    "github": REPO_ROOT / "ci" / "github" / "fix-lane-gate.yml",
    "azure": REPO_ROOT / "ci" / "azure" / "fix-lane-gate.yml",
}

CONFIGURED = "src/"


def _extract_checker(gate_path: Path) -> str:
    raw = gate_path.read_text(encoding="utf-8")
    marker = "python - <<'EOF'\n"
    start = raw.index(marker) + len(marker)
    body = []
    for line in raw[start:].splitlines():
        if line.strip() == "EOF":
            break
        body.append(line)
    return textwrap.dedent("\n".join(body)) + "\n"


def _run(
    tmp_path: Path,
    changed: list[str],
    source_paths: str = CONFIGURED,
    records: dict[str, dict] | None = None,
) -> subprocess.CompletedProcess:
    for rel, data in (records or {}).items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    script = tmp_path / "_gate.py"
    script.write_text(_extract_checker(GATE_PATHS["github"]), encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(script)],
        cwd=tmp_path,
        input="\n".join(changed),
        capture_output=True,
        text=True,
        env={"SOURCE_PATHS": source_paths, "PATH": "", "SYSTEMROOT": ""},
    )


def _record(paths: list[str]) -> dict:
    return {"version": 1, "id": "alpha", "surface": {"paths": paths}}


def test_checker_extraction_is_not_empty():
    """Non-vacuous guard: a changed heredoc marker would make every test below
    run an empty script and trivially pass."""
    body = _extract_checker(GATE_PATHS["github"])
    assert "SOURCE_PATHS" in body and "surface" in body, body[:300]


class TestInactiveUntilConfigured:
    def test_unconfigured_sentinel_passes(self, tmp_path):
        """A fresh install must stay green — the opt-in posture."""
        result = _run(tmp_path, ["src/app.py"], source_paths="YOUR_SOURCE_PATHS")
        assert result.returncode == 0, result.stdout
        assert "inactive" in result.stdout

    def test_empty_source_paths_passes(self, tmp_path):
        result = _run(tmp_path, ["src/app.py"], source_paths="")
        assert result.returncode == 0, result.stdout


class TestEscapeHatch:
    def test_source_change_with_no_governing_artifact_fails(self, tmp_path):
        """The whole point: this is what passed every other gate untouched."""
        result = _run(tmp_path, ["src/app.py"])
        assert result.returncode == 1, result.stdout
        assert "no governing artifact" in result.stdout

    def test_docs_only_change_is_not_this_gate_s_business(self, tmp_path):
        result = _run(tmp_path, ["README.md", "docs/backend/architecture/X.md"])
        assert result.returncode == 0, result.stdout

    def test_feature_change_satisfies_the_gate(self, tmp_path):
        """The feature lane is still a governing artifact."""
        result = _run(
            tmp_path, ["src/app.py", "features/billing/plan.md", "src/test_app.py"]
        )
        assert result.returncode == 0, result.stdout


class TestCorrespondence:
    def test_declared_surface_matching_the_diff_passes(self, tmp_path):
        result = _run(
            tmp_path,
            ["src/app.py", "src/test_app.py", "fixes/alpha/fix.yaml"],
            records={"fixes/alpha/fix.yaml": _record(["src/app.py"])},
        )
        assert result.returncode == 0, result.stdout

    def test_source_changed_but_not_declared_fails(self, tmp_path):
        """validate cannot catch this — surface.paths and risk are both declared,
        so they agree with each other while disagreeing with reality."""
        result = _run(
            tmp_path,
            ["src/app.py", "src/sneaky.py", "src/test_app.py", "fixes/alpha/fix.yaml"],
            records={"fixes/alpha/fix.yaml": _record(["src/app.py"])},
        )
        assert result.returncode == 1, result.stdout
        assert "sneaky.py" in result.stdout

    def test_fix_record_without_a_test_in_the_diff_fails(self, tmp_path):
        """Condition 2 is only provable against the diff."""
        result = _run(
            tmp_path,
            ["src/app.py", "fixes/alpha/fix.yaml"],
            records={"fixes/alpha/fix.yaml": _record(["src/app.py"])},
        )
        assert result.returncode == 1, result.stdout
        assert "no test" in result.stdout

    def test_unreadable_record_is_reported_not_crashed(self, tmp_path):
        path = tmp_path / "fixes" / "alpha" / "fix.yaml"
        path.parent.mkdir(parents=True)
        path.write_text("key: [unclosed\n", encoding="utf-8")
        result = _run(
            tmp_path, ["src/app.py", "src/test_app.py", "fixes/alpha/fix.yaml"]
        )
        assert result.returncode == 1, result.stdout
        assert "could not be read" in result.stdout

    def test_multiple_source_roots_are_honoured(self, tmp_path):
        result = _run(
            tmp_path,
            ["lib/util.py", "lib/test_util.py", "fixes/alpha/fix.yaml"],
            source_paths="src/,lib/",
            records={"fixes/alpha/fix.yaml": _record(["lib/util.py"])},
        )
        assert result.returncode == 0, result.stdout


def test_platform_embeddings_are_identical():
    github = _extract_checker(GATE_PATHS["github"])
    azure = _extract_checker(GATE_PATHS["azure"])
    assert github == azure, "github and azure fix-lane checkers have drifted"


@pytest.mark.parametrize("platform", sorted(GATE_PATHS))
def test_gate_does_not_invoke_govkit(platform):
    """Self-contained by design: a blocking gate must not depend on an unpinned
    PyPI release, and run_validation exits 0 on a missing marker — so a gate
    delegating to it could be switched off from inside the PR it is reviewing."""
    text = GATE_PATHS[platform].read_text(encoding="utf-8")
    # Mentions in comments and remediation output are fine and wanted — what
    # must not appear is an executed command.
    invocations = [
        ln for ln in text.splitlines()
        if ln.strip().startswith(("run: govkit", "- script: govkit", "govkit "))
    ]
    assert not invocations, invocations
