"""Seven bundled actual-change pilots, also run from a runtime-only wheel."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from cli import change_conformance, paths
from cli.change_conformance import load_change_report

PILOTS = ("defect", "enhancement", "refactor", "mcp", "llm", "feature", "architecture")


def run_pilot(workspace, name):
    root = paths.GOVERNANCE_DIR / "examples"
    fixture = json.loads((root / "change-conformance/consumer.json").read_text())
    target, trusted = workspace / "consumer", workspace / "policy"
    target.mkdir()
    trusted.mkdir()

    def write(directory, relative, text):
        path = directory / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    for relative, content in fixture["files"].items():
        write(target, relative, content)
        write(trusted, relative, content)
    for relative, content in fixture["base_files"].items():
        write(target, relative, content)
    write(trusted, ".govkit/profile.yaml", json.dumps(fixture["profile"]))
    write(trusted, "conformance.json", json.dumps(fixture["conformance"]))
    command = [sys.executable, "-I", "-m", "cli.govkit"]

    def invoke(args, *, ci=False, expected=0):
        result = subprocess.run(
            command + args,
            capture_output=True,
            text=True,
            env={**os.environ, **({"CI": "true"} if ci else {})},
        )
        assert result.returncode == expected, (name, result.stdout, result.stderr)
        return json.loads(result.stdout)

    invoke(["pack", "apply", "--target", str(trusted), "--json"])

    def git(*args):
        return subprocess.run(
            ["git", "-C", str(target), *args], check=True, capture_output=True, text=True
        ).stdout.strip()

    git("init", "-q")
    git("config", "user.email", "pilot@example.invalid")
    git("config", "user.name", "Govkit pilot")
    git("add", ".")
    git("commit", "-qm", "pilot baseline")
    base = git("rev-parse", "HEAD")
    for relative, content in fixture["fixed_files"].items():
        write(target, relative, content)
    arguments = workspace / "arguments.json"
    arguments.write_text('{"llm-exact-match":["--results","results.json"]}')
    args = [
        "conform",
        "--request",
        str(root / "workflows/requests" / (name + ".json")),
        "--target",
        str(target),
        "--policy-target",
        str(trusted),
        "--base",
        base,
        "--observed-at",
        "2026-09-23T12:00:00Z",
        "--execute-check",
        "project:tests",
        "--execute-check",
        "llm-exact-match",
        "--pack-arguments",
        str(arguments),
        "--json",
    ]
    if name == "defect":
        args += ["--execute-check", "defect:eligibility"]
    if name == "mcp":
        args += ["--execute-check", "review:mcp", "--execute-check", "review:public-contract"]

    def snapshot():
        return {
            (str(folder), p.relative_to(folder).as_posix()): (p.read_bytes(), p.stat().st_mtime_ns)
            for folder in (target, trusted)
            for p in folder.rglob("*")
            if p.is_file()
        }

    before = snapshot()
    expected = 1 if name == "architecture" else 0
    local = invoke(args, expected=expected)
    ci = invoke(args, ci=True, expected=expected)
    assert local == ci and snapshot() == before
    assert not (target / ".govkit").exists()  # An isolated, initially ungoverned consumer.
    record = workspace / "result.json"
    record.write_text(json.dumps(local))
    assert load_change_report(record).document == local
    checks = {r["id"]: r for r in local["checks"]["results"]}
    assert checks["change:architecture"]["state"] == "pass"
    if name == "architecture":
        assert checks["approval:architecture"]["state"] == "unknown"
        assert all(
            c["state"] == "pass" for key, c in checks.items() if key != "approval:architecture"
        )
    if name == "llm":
        write(target, "results.json", '{"cases":[{"id":"hello","expected":"hi","actual":"wrong"}]}')
        failed_check = "llm-exact-match"
    elif name == "mcp":
        write(target, "src/mcp_tool.py", 'def tool(value):\n    return {"length": -1}\n')
        failed_check = "review:mcp"
    elif name == "architecture":
        write(target, "src/service.py", "import forbidden\ndef result():\n    return 42\n")
        failed_check = "change:architecture"
    else:
        write(target, "src/service.py", "def result():\n    return 0\n")
        failed_check = "defect:eligibility" if name == "defect" else "project:tests"
    failed = invoke(args, expected=1)
    assert (
        next(r for r in failed["checks"]["results"] if r["id"] == failed_check)["state"] == "fail"
    )


if __name__ == "__main__":
    assert Path(change_conformance.__file__).is_relative_to(sys.prefix)
    for name in PILOTS:
        with tempfile.TemporaryDirectory(prefix="govkit-change-pilot-") as directory:
            run_pilot(Path(directory), name)
    print(
        "Seven actual-change pilots: passing measurements, real failures, replay and local/CI parity verified."
    )
