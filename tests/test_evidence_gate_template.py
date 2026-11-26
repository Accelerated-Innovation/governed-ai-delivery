"""The evidence gate templates judge the features a change touches (L08a).

The step's own script is taken from each template and run in a real repository,
with the provider's variables set as the provider sets them.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from cli import evidence_record, paths
from tests.test_evidence_changed import FIRST, git, project  # noqa: F401
from tests.test_evidence_report import PASSING, _junit

STEP = "Report the features this change touches"
RECORD = "govkit evidence --record --target ."
pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="the templates run bash")


def _steps(provider):
    document = yaml.safe_load(
        (paths.REPO_ROOT / "ci" / provider / "evidence-gate.yml").read_text(encoding="utf-8")
    )
    if provider == "github":
        return document["jobs"]["evidence-check"]["steps"]
    return document["stages"][0]["jobs"][0]["steps"]


def _named(provider, name):
    key = "name" if provider == "github" else "displayName"
    return next(step for step in _steps(provider) if step.get(key) == name)


def _script(step):
    return step.get("run") or step.get("bash") or step.get("script")


@pytest.mark.parametrize("provider", ["github", "azure"])
def test_the_steps_run_in_order_after_the_tests_even_when_an_earlier_one_failed(provider):
    steps = _steps(provider)
    scripts = [_script(step) or "" for step in steps]
    tests = next(i for i, text in enumerate(scripts) if "Not configured" in text)
    record = next(i for i, text in enumerate(scripts) if text.strip() == RECORD)
    changed = next(i for i, text in enumerate(scripts) if "--changed-since" in text)
    assert tests < record < changed
    condition = "if" if provider == "github" else "condition"
    assert steps[record][condition] and steps[changed][condition]
    checkout = steps[0]
    depth = checkout["with"]["fetch-depth"] if provider == "github" else checkout["fetchDepth"]
    assert depth == 0


def _run(provider, target, tmp_path, **variables):
    bin_directory = Path(sys.executable).parent
    environment = {
        **os.environ,
        "PATH": f"{bin_directory}{os.pathsep}{os.environ['PATH']}",
        "RUNNER_TEMP": str(tmp_path),
        "AGENT_TEMPDIRECTORY": str(tmp_path),
        "GITHUB_STEP_SUMMARY": str(tmp_path / "summary.md"),
        **variables,
    }
    return subprocess.run(
        ["bash", "-e", "-o", "pipefail", "-c", _script(_named(provider, STEP))],
        cwd=target,
        env=environment,
        capture_output=True,
        text=True,
    )


@pytest.fixture
def changed(project, tmp_path_factory):  # noqa: F811
    """The project with one touched feature, on a branch, and a scratch directory."""
    target, base = project
    git(target, "branch", "-M", "main")
    git(target, "update-ref", "refs/remotes/origin/main", base)
    (target / "features" / FIRST / "plan.md").write_text("# Plan\n", encoding="utf-8")
    return target, base, tmp_path_factory.mktemp("runner")


def _variables(provider, base):
    return {"BASE": base} if provider == "github" else {"TARGET_BRANCH": "main"}


@pytest.mark.parametrize("provider", ["github", "azure"])
def test_a_passing_feature_passes_the_step_and_reaches_the_summary(provider, changed):
    target, base, scratch = changed
    _junit(target, PASSING)
    evidence_record.write_record(target)
    result = _run(provider, target, scratch, **_variables(provider, base))
    assert result.returncode == 0, result.stdout + result.stderr
    assert "All 1 changed feature(s) passed." in result.stdout
    if provider == "github":
        summary = (scratch / "summary.md").read_text(encoding="utf-8")
    else:
        assert "##vso[task.uploadsummary]" in result.stdout
        summary = (scratch / "evidence-features.md").read_text(encoding="utf-8")
    assert FIRST in summary and "\x1b" not in summary and summary.startswith("```")


@pytest.mark.parametrize("provider", ["github", "azure"])
def test_a_feature_that_is_not_a_pass_fails_the_step(provider, changed):
    target, base, scratch = changed
    result = _run(provider, target, scratch, **_variables(provider, base))
    assert result.returncode == 1, result.stdout + result.stderr
    assert "1 of 1 changed feature(s) did not pass." in result.stdout


@pytest.mark.parametrize(
    "provider, variables",
    [
        ("github", {"BASE": "0" * 40}),
        ("github", {"BASE": ""}),
        ("azure", {"TARGET_BRANCH": "$(System.PullRequest.TargetBranchName)"}),
        ("azure", {"TARGET_BRANCH": ""}),
    ],
)
def test_without_a_usable_base_the_previous_commit_is_compared(provider, variables, changed):
    target, _, scratch = changed
    git(target, "add", ".")
    git(target, "commit", "-qm", "the plan")
    result = _run(provider, target, scratch, **variables)
    assert "comparing with the previous commit" in result.stdout
    assert result.returncode == 1 and f"feature {FIRST}" in result.stdout
