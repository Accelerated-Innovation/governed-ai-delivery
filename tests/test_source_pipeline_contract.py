"""Executable, deliberately limited contract for this source repo's Tests workflow.

These checks inspect declarations; they do not authenticate hosted execution,
branch protection, reusable consumer entry points or arbitrary shell semantics.
"""

from pathlib import Path

import pytest
import yaml


@pytest.fixture
def workflow():
    # BaseLoader preserves GitHub's `on` key and Python version strings.
    path = Path(__file__).resolve().parents[1] / ".github/workflows/test.yml"
    return yaml.load(path.read_text(), Loader=yaml.BaseLoader)


@pytest.mark.parametrize("event", ["pull_request", "push"])
def test_every_path_on_main_reaches_the_source_workflow(workflow, event):
    assert workflow["on"][event] == {"branches": ["main"]}, (
        "Source validation must not exclude paths or narrow default event activity"
    )


@pytest.mark.parametrize("job", ["fast", "e2e", "wheel-smoke"])
def test_required_source_jobs_do_not_skip_or_ignore_failures(workflow, job):
    definition = workflow["jobs"][job]
    assert "if" not in definition, f"{job} must run for every workflow invocation"
    assert definition.get("continue-on-error", "false") == "false"
    for step in definition["steps"]:
        assert "if" not in step, f"{job} must not conditionally omit validation steps"
        assert step.get("continue-on-error", "false") == "false"


def test_both_supported_python_versions_run_the_fast_tier(workflow):
    fast = workflow["jobs"]["fast"]
    assert fast["strategy"]["matrix"] == {"python-version": ["3.11", "3.12"]}
    setup = [
        step for step in fast["steps"] if step.get("uses", "").startswith("actions/setup-python@")
    ]
    assert len(setup) == 1, "One setup-python step must select each matrix interpreter"
    assert setup[0].get("with", {}).get("python-version") == "${{ matrix.python-version }}"
    steps = {step.get("name"): step for step in fast["steps"]}
    assert steps["Run pytest (fast tier)"]["run"].strip() == 'pytest -m "not e2e"'


def test_e2e_tier_preserves_pytest_failure_through_tee(workflow):
    steps = {step.get("name"): step for step in workflow["jobs"]["e2e"]["steps"]}
    assert steps["Run pytest (e2e tier)"]["run"].splitlines() == [
        "set -euo pipefail",
        "pytest -m e2e --no-header -q -rs | tee /tmp/e2e.txt",
    ]


def test_installed_wheel_validation_follows_both_test_tiers(workflow):
    wheel = workflow["jobs"]["wheel-smoke"]
    assert set(wheel["needs"]) == {"fast", "e2e"}
    checkouts = [
        step for step in wheel["steps"] if step.get("uses", "").startswith("actions/checkout@")
    ]
    assert len(checkouts) == 1
    assert checkouts[0].get("with", {}).get("fetch-depth") == "0", (
        "The caller's comparison commit must be available to conformance"
    )
    steps = {step.get("name"): step for step in wheel["steps"]}
    assert steps["Build wheel"]["run"].strip() == "python -m build --wheel"
    assert "Install wheel into a clean venv" in steps
    assert "Actual-change conformance works from the wheel" in steps
    assert "Source self-hosting works from the wheel with test dependencies" in steps
    source = steps["Source self-hosting works from the wheel with test dependencies"]
    assert source.get("env", {}).get("GOVKIT_BASE") == (
        "${{ github.event_name == 'pull_request' && github.event.pull_request.base.sha || github.event.before }}"
    )
    assert ' --base "$GOVKIT_BASE"' in source["run"]
