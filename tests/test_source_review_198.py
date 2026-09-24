"""PR #198 regressions exercise real source controls and committed Git changes."""

import copy
import subprocess
import sys

import pytest
import yaml

from tests import test_source_pipeline_contract as contract
from tests import test_source_self_hosting as hosting
from tests import wheel_source_self_hosting_smoke as smoke
from tests.test_change_conformance import git

source_checkout = hosting.source_checkout


@pytest.fixture
def workflow():
    return yaml.load(
        (hosting.ROOT / ".github/workflows/test.yml").read_text(), Loader=yaml.BaseLoader
    )


@pytest.mark.parametrize(
    "mutation",
    ["python311", "python312", "missing-version", "missing-setup", "wrong-axis", "duplicate"],
)
def test_matrix_control_rejects_setup_that_does_not_bind_each_interpreter(workflow, mutation):
    steps = workflow["jobs"]["fast"]["steps"]
    setup = next(step for step in steps if step.get("uses", "").startswith("actions/setup-python@"))
    if mutation == "missing-setup":
        steps.remove(setup)
    elif mutation == "duplicate":
        extra = copy.deepcopy(setup)
        extra["with"]["python-version"] = "3.12"
        steps.append(extra)
    elif mutation == "missing-version":
        setup["with"].pop("python-version")
    else:
        setup["with"]["python-version"] = {
            "python311": "3.11",
            "python312": "3.12",
            "wrong-axis": "${{ matrix.python }}",
        }[mutation]
    with pytest.raises(AssertionError):
        contract.test_both_supported_python_versions_run_the_fast_tier(workflow)


def test_matrix_control_accepts_the_actual_setup_binding(workflow):
    contract.test_both_supported_python_versions_run_the_fast_tier(workflow)


@pytest.mark.parametrize(
    "mutation", ["shallow", "no-history", "head-base", "no-base", "no-argument"]
)
def test_wheel_control_requires_history_and_explicit_event_comparison_base(workflow, mutation):
    steps = workflow["jobs"]["wheel-smoke"]["steps"]
    checkout = next(step for step in steps if step.get("uses", "").startswith("actions/checkout@"))
    source = next(
        step
        for step in steps
        if step.get("name") == "Source self-hosting works from the wheel with test dependencies"
    )
    if mutation == "shallow":
        checkout.setdefault("with", {})["fetch-depth"] = "1"
    elif mutation == "no-history":
        checkout.pop("with", None)
    elif mutation == "head-base":
        source["env"] = {"GOVKIT_BASE": "${{ github.sha }}"}
    elif mutation == "no-base":
        source.pop("env", None)
    else:
        source["run"] = source["run"].replace(' --base "$GOVKIT_BASE"', "")
    with pytest.raises(AssertionError):
        contract.test_installed_wheel_validation_follows_both_test_tiers(workflow)


def test_smoke_includes_committed_changes_against_the_callers_base(source_checkout):
    target, _, base = source_checkout
    git(target, "add", ".")
    git(target, "commit", "-qm", "Committed source maintenance")
    head = git(target, "rev-parse", "HEAD")
    assert git(target, "status", "--porcelain") == ""
    report = smoke.run(target, base, observed_at=hosting.CLOCK)
    assert report["change"]["base"] == base
    assert report["change"]["revision"] == head != base
    assert {c["path"] for c in report["change"]["changes"]} == {"source-change.txt"}
    assert report["state"] == "unknown"


@pytest.mark.parametrize("base", [None, "", "HEAD", "0" * 40, "f" * 40])
def test_smoke_refuses_missing_symbolic_or_unavailable_base(source_checkout, base):
    target, _, _ = source_checkout
    with pytest.raises(ValueError, match="comparison base"):
        smoke.run(target, base)


def test_smoke_refuses_comparison_with_the_current_revision(source_checkout):
    target, _, head = source_checkout
    with pytest.raises(ValueError, match="comparison base"):
        smoke.run(target, head)


def test_smoke_cli_requires_an_explicit_base(source_checkout):
    target, _, _ = source_checkout
    completed = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            str(hosting.ROOT / "tests/wheel_source_self_hosting_smoke.py"),
            str(target),
        ],
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert completed.returncode == 2
    assert "required: --base" in completed.stderr
