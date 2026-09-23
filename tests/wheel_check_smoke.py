"""Exercise the check protocol with runtime-only wheel dependencies and -I."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from cli import check_runner, paths
from cli.check_models import State
from cli.check_runner import load_report
from cli.profiles import load_profile

assert Path(check_runner.__file__).is_relative_to(sys.prefix)
examples = sorted((paths.GOVERNANCE_DIR / "examples/check-results").glob("*.json"))
assert len(examples) == 3
assert {load_report(p).state for p in examples} == {State.PASS, State.FAIL, State.UNKNOWN}
command = [sys.executable, "-I", "-m", "cli.govkit"]


def snapshot(target):
    return {
        p.relative_to(target): (p.read_bytes(), p.stat().st_mtime_ns)
        for p in target.rglob("*")
        if p.is_file()
    }


with tempfile.TemporaryDirectory() as directory:
    target = Path(directory)
    profile = load_profile(paths.GOVERNANCE_DIR / "examples/packs/llm-without-gherkin.yaml")
    (target / ".govkit").mkdir()
    (target / ".govkit/profile.yaml").write_text(json.dumps(profile.document))
    subprocess.run(
        command + ["pack", "apply", "--target", str(target), "--json"],
        check=True,
        capture_output=True,
        text=True,
    )
    options = ["conform", "--target", str(target), "--json"]
    before = snapshot(target)
    skipped = subprocess.run(command + options, capture_output=True, text=True)
    assert skipped.returncode == 1
    raw = json.loads(skipped.stdout)
    assert next(r for r in raw["results"] if r["id"] == "llm-exact-match")["state"] == "skipped"
    assert snapshot(target) == before
    arguments = target / "arguments.json"
    arguments.write_text('{"llm-exact-match":["--results","results.json"]}')
    options += ["--execute-pack-check", "llm-exact-match", "--pack-arguments", str(arguments)]
    results = target / "results.json"
    for actual, expected_exit in [("hello", 0), ("wrong", 1)]:
        results.write_text(
            json.dumps({"cases": [{"id": "hello", "expected": "hello", "actual": actual}]})
        )
        before = snapshot(target)
        local = subprocess.run(command + options, capture_output=True, text=True)
        ci = subprocess.run(
            command + options, capture_output=True, text=True, env={**os.environ, "CI": "true"}
        )
        assert local.returncode == ci.returncode == expected_exit
        assert local.stdout == ci.stdout
        raw = json.loads(local.stdout)
        control = next(r for r in raw["results"] if r["id"] == "llm-exact-match")
        assert control["state"] == ("pass" if expected_exit == 0 else "fail")
        assert control["execution"] == "executed"
        assert control["evidence"][0]["origin"] == "tool-execution"
        assert snapshot(target) == before
        record = target / "check-results.json"
        record.write_text(local.stdout)
        assert load_report(record).exit_code == expected_exit
    assert not (target / ".govkit/marker.json").exists()
    assert not (target / "features").exists()
print(
    "Check wheel smoke passed: bundled reports; skipped/pass/fail controls; explicit local/CI parity"
)
