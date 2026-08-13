"""Behavior tests for the eval-gate embedded prediction checker.

The gate globs `features/*/plan.md` with no `starter_*` exclusion, while
`cli/features.py::list_user_features` filters starters and
`ci/*/data-common-gate.yml` skips them explicitly in shell. The manifest ships
`features/starter_backend/` — whose `plan.md` carries an all-`null` prediction
block *by design* — alongside this gate, so a team following the gate's own
header instruction ("copy this file to .github/workflows/") gets a red gate on
day one, for a file govkit itself wrote.

Following `tests/test_dbt_gate_checks.py`: extract the heredoc, execute it against
fixtures, and pin the two platform embeddings identical so they cannot drift.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
GATE_PATHS = {
    "github": REPO_ROOT / "ci" / "github" / "eval-gate.yml",
    "azure": REPO_ROOT / "ci" / "azure" / "eval-gate.yml",
}

GOOD_PREDICTION = """```yaml
evaluation_prediction:
  first:
    fast:           { score: 5, evidence: "no io" }
    isolated:       { score: 4, evidence: "no shared state" }
    repeatable:     { score: 4, evidence: "deterministic" }
    self_verifying: { score: 5, evidence: "explicit asserts" }
    timely:         { score: 4, evidence: "tests first" }
    average: 4.4
  virtues:
    working:   { score: 5, evidence: "green" }
    unique:    { score: 4, evidence: "one owner" }
    simple:    { score: 4, evidence: "few paths" }
    clear:     { score: 4, evidence: "named well" }
    easy:      { score: 4, evidence: "small delta" }
    developed: { score: 4, evidence: "typed" }
    brief:     { score: 4, evidence: "terse" }
    average: 4.14
  thresholds_met: true
```
"""

LOW_PREDICTION = GOOD_PREDICTION.replace("{ score: 5, evidence: \"no io\" }", "{ score: 1, evidence: \"slow\" }").replace(
    "average: 4.4", "average: 3.0"
)


def _extract_first_heredoc(gate_path: Path) -> str:
    """Pull the first python heredoc body out of the gate, de-indented."""
    raw = gate_path.read_text(encoding="utf-8")
    marker = "python - <<'EOF'\n"
    start = raw.index(marker) + len(marker)
    body = []
    for line in raw[start:].splitlines():
        if line.strip() == "EOF":
            break
        body.append(line)
    return textwrap.dedent("\n".join(body)) + "\n"


def _run_gate(tmp_path: Path, features: dict[str, str]) -> subprocess.CompletedProcess:
    for name, plan in features.items():
        d = tmp_path / "features" / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "plan.md").write_text(f"# Plan\n\n{plan}", encoding="utf-8")
    script = tmp_path / "_gate.py"
    script.write_text(_extract_first_heredoc(GATE_PATHS["github"]), encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(script)], cwd=tmp_path, capture_output=True, text=True
    )


def test_heredoc_extraction_is_not_empty():
    """Non-vacuous guard: if the marker changes, every test below would run an
    empty script and trivially pass."""
    body = _extract_first_heredoc(GATE_PATHS["github"])
    assert "evaluation_prediction" in body and "glob" in body, body[:400]


def test_complete_prediction_passes(tmp_path: Path):
    result = _run_gate(tmp_path, {"real_feature": GOOD_PREDICTION})
    assert result.returncode == 0, result.stdout + result.stderr


def test_below_threshold_prediction_fails(tmp_path: Path):
    result = _run_gate(tmp_path, {"real_feature": LOW_PREDICTION})
    assert result.returncode == 1, result.stdout + result.stderr


def test_shipped_starter_does_not_fail_the_gate(tmp_path: Path):
    """`features/starter_backend/plan.md` ships an all-null prediction block on
    purpose. The gate must skip starters the way `list_user_features` does."""
    starter_plan = (REPO_ROOT / "features" / "starter_backend" / "plan.md").read_text(
        encoding="utf-8"
    )
    (tmp_path / "features" / "starter_backend").mkdir(parents=True)
    (tmp_path / "features" / "starter_backend" / "plan.md").write_text(
        starter_plan, encoding="utf-8"
    )
    script = tmp_path / "_gate.py"
    script.write_text(_extract_first_heredoc(GATE_PATHS["github"]), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(script)], cwd=tmp_path, capture_output=True, text=True
    )
    assert result.returncode == 0, (
        "eval-gate fails on govkit's own shipped starter:\n" + result.stdout + result.stderr
    )


def test_starter_skipped_but_real_feature_still_checked(tmp_path: Path):
    """The exclusion must not become a blanket escape — a real feature alongside
    a starter is still evaluated."""
    starter_plan = (REPO_ROOT / "features" / "starter_backend" / "plan.md").read_text(
        encoding="utf-8"
    )
    (tmp_path / "features" / "starter_backend").mkdir(parents=True)
    (tmp_path / "features" / "starter_backend" / "plan.md").write_text(
        starter_plan, encoding="utf-8"
    )
    result = _run_gate(tmp_path, {"real_feature": LOW_PREDICTION})
    assert result.returncode == 1, result.stdout + result.stderr
    assert "real_feature" in result.stdout, result.stdout


def test_platform_embeddings_are_identical():
    github = _extract_first_heredoc(GATE_PATHS["github"])
    azure = _extract_first_heredoc(GATE_PATHS["azure"])
    assert github == azure, (
        "github and azure eval-gate checkers have drifted; they must stay identical"
    )
