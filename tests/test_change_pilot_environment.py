"""The source/wheel pilot must exercise distinct local and CI environments."""

import subprocess

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
