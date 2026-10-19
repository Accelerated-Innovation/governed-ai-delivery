"""Consumer quality gates check architecture experiment records (ADR 0020).

The GitHub and Azure `quality-gate.yml` templates must run
`govkit validate --only experiments` only when a non-starter feature declares
an `experiments.yaml` or a `preflight_outcome` block, and must stay non-strict
so experimentation pull requests are not blocked by outstanding work.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
GITHUB = REPO_ROOT / "ci" / "github" / "quality-gate.yml"
AZURE = REPO_ROOT / "ci" / "azure" / "quality-gate.yml"
COMMAND = "govkit validate --target . --only experiments"


def _github_steps() -> list[dict]:
    return yaml.safe_load(GITHUB.read_text(encoding="utf-8"))["jobs"]["architecture-experiments"][
        "steps"
    ]


def _azure_steps() -> list[dict]:
    stages = yaml.safe_load(AZURE.read_text(encoding="utf-8"))["stages"]
    [stage] = [s for s in stages if s["stage"] == "ArchitectureExperiments"]
    [job] = stage["jobs"]
    return job["steps"]


def _named(steps, key, name):
    [step] = [s for s in steps if s.get(key) == name]
    return step


def test_github_job_detects_installs_and_validates_non_strict():
    steps = _github_steps()
    detect = _named(steps, "name", "Detect experiment records and preflight outcomes")
    install = _named(steps, "name", "Install GovKit")
    check = _named(steps, "name", "Check architecture experiment evidence")
    assert install["if"] == check["if"] == "steps.detect.outputs.found == 'yes'"
    assert detect["id"] == "detect"
    assert "govkit~=" in install["run"]
    assert check["run"].strip() == COMMAND
    assert not any("--strict" in step.get("run", "") for step in steps)


def test_azure_stage_detects_installs_and_validates_non_strict():
    steps = _azure_steps()
    install = _named(steps, "displayName", "Install GovKit")
    check = _named(steps, "displayName", "Check architecture experiment evidence")
    condition = "eq(variables['EXPERIMENTS_FOUND'], 'yes')"
    assert install["condition"] == check["condition"] == condition
    assert "govkit~=" in install["script"]
    assert check["script"].strip() == COMMAND
    assert not any("--strict" in step.get("script", "") for step in steps)


def test_both_providers_pin_the_same_govkit_version():
    github = _named(_github_steps(), "name", "Install GovKit")["run"]
    azure = _named(_azure_steps(), "displayName", "Install GovKit")["script"]
    pin = [line for line in github.splitlines() if "govkit~=" in line]
    assert pin and pin == [line for line in azure.splitlines() if "govkit~=" in line]


def _layout(root: Path, files: dict[str, str]) -> None:
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


BLOCK = "```yaml\npreflight_outcome:\n  status: blocked\n  reason: x\n```\n"
LAYOUTS = {
    "no-features": ({}, "no"),
    "plain-feature": ({"features/a/architecture_preflight.md": "# Preflight\n"}, "no"),
    "record": ({"features/a/experiments.yaml": "kind: experiment-set\n"}, "yes"),
    "outcome-block": ({"features/a/architecture_preflight.md": BLOCK}, "yes"),
    "starter-only": (
        {
            "features/starter_backend/experiments.yaml": "x\n",
            "features/starter_backend/architecture_preflight.md": BLOCK,
        },
        "no",
    ),
}


@pytest.mark.skipif(shutil.which("bash") is None or os.name == "nt", reason="needs bash")
@pytest.mark.parametrize("layout", sorted(LAYOUTS))
def test_github_detection_script(tmp_path, layout):
    files, expected = LAYOUTS[layout]
    _layout(tmp_path, files)
    output = tmp_path / "github_output"
    script = _named(_github_steps(), "name", "Detect experiment records and preflight outcomes")
    subprocess.run(
        ["bash", "-c", script["run"]],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        env={"PATH": os.environ["PATH"], "GITHUB_OUTPUT": str(output)},
    )
    assert output.read_text(encoding="utf-8").strip() == f"found={expected}"


@pytest.mark.skipif(shutil.which("bash") is None or os.name == "nt", reason="needs bash")
@pytest.mark.parametrize("layout", sorted(LAYOUTS))
def test_azure_detection_script(tmp_path, layout):
    files, expected = LAYOUTS[layout]
    _layout(tmp_path, files)
    script = _named(
        _azure_steps(), "displayName", "Detect experiment records and preflight outcomes"
    )
    result = subprocess.run(
        ["bash", "-c", script["script"]],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
        env={"PATH": os.environ["PATH"]},
    )
    assert f"##vso[task.setvariable variable=EXPERIMENTS_FOUND]{expected}" in result.stdout
