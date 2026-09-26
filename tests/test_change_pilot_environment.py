"""Pilots isolate setup writers and exercise distinct local and CI environments."""

import json
import os
import subprocess

import pytest

from tests import (
    wheel_maintenance_assessment_smoke,
    wheel_observation_smoke,
    wheel_pipeline_smoke,
    wheel_provider_evidence_smoke,
)
from tests.wheel_change_smoke import run_pilot


def test_local_pilot_clears_inherited_ci_while_ci_pilot_sets_it(tmp_path, monkeypatch):
    monkeypatch.setenv("CI", "true")
    real_run = subprocess.run
    environments = []

    def observed_run(argv, **kwargs):
        if argv[1:5] == ["-I", "-m", "cli.govkit", "conform"]:
            environments.append(kwargs["env"].get("CI"))
        return real_run(argv, **kwargs)

    # Observe the process boundary; every real CLI and project check still runs.
    monkeypatch.setattr(subprocess, "run", observed_run)
    run_pilot(tmp_path, "enhancement")

    assert environments == [None, "true", None], "Local pass/fail runs must not inherit CI"


@pytest.mark.parametrize("pilot", ["change", "pipeline", "evidence", "observation", "maintenance"])
def test_pilot_fixture_does_not_launch_automatic_git_maintenance(tmp_path, monkeypatch, pilot):
    trace = tmp_path / "git-trace.json"
    config = tmp_path / "gitconfig"
    # Force maintenance on, but keep this pre-fix control synchronous and isolated.
    config.write_text("[maintenance]\n\tauto = true\n\tautoDetach = false\n")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(config))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_TRACE2_EVENT", str(trace))
    workspace = tmp_path / "pilot"
    workspace.mkdir()
    pilots = {
        "change": lambda: run_pilot(workspace, "defect"),
        "pipeline": lambda: wheel_pipeline_smoke.run_pilot(workspace, "codex"),
        "evidence": lambda: wheel_provider_evidence_smoke.run_pilot(
            workspace / "evidence", "codex", "github"
        ),
        "observation": lambda: wheel_observation_smoke.run_pilot(workspace, "codex", "github"),
        "maintenance": lambda: wheel_maintenance_assessment_smoke.run_pilot(workspace, "codex"),
    }

    pilots[pilot]()

    events = [json.loads(line) for line in trace.read_text().splitlines()]
    assert any(e["event"] == "start" for e in events), "The real Git process must be traced"
    automatic = [
        e["argv"]
        for e in events
        if e["event"] == "child_start"
        and "maintenance" in e.get("argv", [])
        and "--auto" in e["argv"]
    ]
    assert not automatic, f"Fixture setup launched automatic maintenance: {automatic}"


@pytest.mark.parametrize("relative", [".git/objects/maintenance.lock", ".git/index"])
def test_change_pilot_still_detects_git_file_or_mtime_mutation(tmp_path, monkeypatch, relative):
    real_run = subprocess.run
    changed = False

    def mutate_after_first_inspection(argv, **kwargs):
        nonlocal changed
        outcome = real_run(argv, **kwargs)
        if not changed and argv[1:5] == ["-I", "-m", "cli.govkit", "conform"]:
            path = tmp_path / "consumer" / relative
            if path.exists():
                stat = path.stat()
                os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000_000))
            else:
                path.write_text("controlled concurrent writer\n")
            changed = True
        return outcome

    monkeypatch.setattr(subprocess, "run", mutate_after_first_inspection)

    with pytest.raises(AssertionError, match="Inspection changed files or mtimes") as error:
        run_pilot(tmp_path, "enhancement")

    assert changed
    assert relative in str(error.value)
