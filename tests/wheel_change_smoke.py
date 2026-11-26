"""Eight bundled actual-change pilots, also run from a runtime-only wheel."""

import difflib
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

from cli import change_conformance, paths
from cli.change_conformance import load_change_report
from cli.posture import reference
from cli.posture_change import parse_change_posture
from cli.schema_validation import canonical_json, content_digest

PILOTS = (
    "defect",
    "enhancement",
    "refactor",
    "mcp",
    "llm",
    "feature",
    "architecture",
    "experiment",
)
# The experiment pilot reuses a bundled record observed on 2026-11-01; assess it
# at that scenario's documented time so the result is not in the future.
OBSERVED = {"experiment": "2026-11-10T00:00:00Z"}


def run_pilot(workspace, name, then=None):
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
        env = dict(os.environ)
        env.pop("CI", None)
        if ci:
            env["CI"] = "true"
        result = subprocess.run(
            command + args,
            capture_output=True,
            text=True,
            env=env,
        )
        if expected is not None:
            assert result.returncode == expected, (name, result.stdout, result.stderr)
        return json.loads(result.stdout)

    invoke(["pack", "apply", "--target", str(trusted), "--json"])

    def git(*args):
        # Fixture commits must not leave background writers racing later snapshots.
        return subprocess.run(
            ["git", "-c", "maintenance.auto=false", "-C", str(target), *args],
            check=True,
            capture_output=True,
            text=True,
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
        OBSERVED.get(name, "2026-09-23T12:00:00Z"),
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

    def posture(source, label):
        saved = workspace / (label + "-change.json")
        saved.write_text(json.dumps(source))
        output = workspace / (label + "-posture.json")
        before_export = snapshot()
        exported = invoke(
            [
                "posture",
                "change",
                "--results",
                str(saved),
                "--target",
                str(target),
                "--output",
                str(output),
                "--json",
            ]
        )
        assert parse_change_posture(exported).document == exported == json.loads(output.read_text())
        assert exported["results"]["summary"] == source["checks"]["summary"]
        assert exported["results"]["exit_code"] == source["exit_code"]
        assert exported["workflow"]["selected"] == source["plan"]["workflow"]
        assert [
            (c["ref"], c["state"], c["execution"], c["required"])
            for c in exported["results"]["controls"]
        ] == [
            (reference("control", c["id"]), c["state"], c["execution"], c["required"])
            for c in source["checks"]["results"]
        ]
        human = subprocess.run(
            command + ["posture", "change", "--results", str(saved)], capture_output=True, text=True
        )
        assert human.returncode == 0, human.stderr
        for control in exported["results"]["controls"]:
            assert control["ref"] in human.stdout and control["state"] in human.stdout
            for finding in control["findings"]:
                assert finding["ref"] in human.stdout and finding["action_ref"] in human.stdout
        if label == "initial":
            # Saved results can be internally valid yet contradict their plan.
            # Exercise installed CLI refusal before it creates a public artifact.
            original = load_change_report(saved)
            identifier = source["plan"]["checks"][0]["id"]
            invalid = workspace / "weakened-results.json"
            refused_output = workspace / "refused-posture.json"
            for changes in (
                {"scope": ("unplanned/narrow",)},
                {"source_policy": "substituted-policy.md"},
                {"reason": "substituted obligation"},
            ):
                altered = replace(
                    original,
                    checks=replace(
                        original.checks,
                        results=tuple(
                            replace(c, spec=replace(c.spec, **changes))
                            if c.spec.id == identifier
                            else c
                            for c in original.checks.results
                        ),
                    ),
                )
                invalid.write_text(altered.to_json())
                assert load_change_report(invalid).document == altered.document
                refused = subprocess.run(
                    command
                    + [
                        "posture",
                        "change",
                        "--results",
                        str(invalid),
                        "--target",
                        str(target),
                        "--output",
                        str(refused_output),
                        "--json",
                    ],
                    capture_output=True,
                    text=True,
                )
                assert refused.returncode == 1 and not refused.stdout, (
                    name,
                    changes,
                    refused.stderr,
                )
                assert not refused_output.exists(), (name, changes)
            forged = json.loads(json.dumps(exported))
            forged["results"]["controls"][0]["local_ref"] = "/checks/results/1"
            forged["digest"] = content_digest(
                canonical_json({k: v for k, v in forged.items() if k != "digest"}).encode()
            )
            try:
                parse_change_posture(forged)
            except ValueError:
                pass
            else:
                raise AssertionError((name, "Accepted a pointer to another result"))
        assert output.stat().st_mode & 0o777 == 0o600
        assert str(target) not in output.read_text() and str(trusted) not in output.read_text()
        assert snapshot() == before_export

    expected = 1 if name == "architecture" else 0
    local = invoke(args, expected=expected)
    ci = invoke(args, ci=True, expected=expected)
    assert local == ci, (
        name,
        "Local/CI reports differ",
        "\n".join(
            difflib.unified_diff(
                json.dumps(local, sort_keys=True, indent=2).splitlines(),
                json.dumps(ci, sort_keys=True, indent=2).splitlines(),
                fromfile="local",
                tofile="ci",
            )
        ),
    )
    after = snapshot()
    assert after == before, (
        name,
        "Inspection changed files or mtimes",
        [key for key in sorted(before.keys() | after.keys()) if before.get(key) != after.get(key)],
    )
    assert not (target / ".govkit").exists()  # An isolated, initially ungoverned consumer.
    record = workspace / "result.json"
    record.write_text(json.dumps(local))
    assert load_change_report(record).document == local
    posture(local, "initial")
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
    posture(failed, "failed")
    if then is not None:
        then(write, git, invoke, args, posture)


FEATURE = """Feature: Result

  Background:
    Given the service is running

  @scenario:result-value
  Scenario: The result is the answer
    When the result is requested
    Then it is 42
"""
CRITERIA = "criteria:\n  - name: result-latency\n    threshold: 0.9\n"


def definition_change(write, git, invoke, args, posture):
    """A change may add to a feature's definition; it may not remove or alter it (L06a)."""
    target = Path(args[args.index("--target") + 1])
    acceptance = "features/01_result/acceptance.feature"
    criteria = "features/01_result/eval_criteria.yaml"
    write(target, acceptance, FEATURE)
    write(target, criteria, CRITERIA)
    git("add", ".")
    git("commit", "-qm", "a feature definition")
    args = list(args)
    args[args.index("--base") + 1] = git("rev-parse", "HEAD")

    def check(report):
        return next(r for r in report["checks"]["results"] if r["id"] == "change:definition")

    def codes(report):
        return sorted(f["code"] for f in check(report)["findings"] if f["category"] == "change")

    write(target, "src/service.py", "def result():\n    return 42\n\n# touched\n")
    untouched = invoke(args, expected=None)
    assert all(r["id"] != "change:definition" for r in untouched["checks"]["results"])

    write(target, acceptance, FEATURE + "\n  Scenario: Another\n    Then it is still 42\n")
    write(target, criteria, CRITERIA + "  - name: result-accuracy\n    threshold: 1\n")
    added = invoke(args, expected=None)
    assert check(added)["state"] == "pass", check(added)

    write(target, acceptance, FEATURE.replace("it is 42", "it is a number"))
    write(target, criteria, CRITERIA.replace("0.9", "0.1"))
    weakened = invoke(args, expected=1)
    assert check(weakened)["state"] == "fail", check(weakened)
    assert codes(weakened) == ["criterion-altered", "scenario-altered"], check(weakened)
    posture(weakened, "definition")

    write(target, acceptance, FEATURE.replace("the service is running", "nothing"))
    write(target, criteria, CRITERIA)
    assert codes(invoke(args, expected=1)) == ["shared-steps-changed"]
    (target / acceptance).unlink()
    assert codes(invoke(args, expected=1)) == ["definition-removed"]


def protected_change(write, git, invoke, args, posture):
    """A change may add tests; it may not alter existing tests or protected files (L06b)."""
    target = Path(args[args.index("--target") + 1])
    trusted = Path(args[args.index("--policy-target") + 1])
    test, workflow = "tests/test_result.py", ".github/workflows/ci.yml"
    body = "from src.service import result\n\n\ndef test_result():\n    assert result() == 42\n"
    write(target, test, body)
    write(target, workflow, "on: push\n")
    git("add", ".")
    git("commit", "-qm", "tests and a workflow")
    args = list(args)
    args[args.index("--base") + 1] = git("rev-parse", "HEAD")

    def check(report):
        return next((r for r in report["checks"]["results"] if r["id"] == "change:protected"), None)

    def codes(report):
        return sorted(f["code"] for f in check(report)["findings"] if f["category"] == "change")

    write(target, test, body.replace("== 42", "is not None"))
    assert check(invoke(args, expected=None)) is None, "no declaration, no check"

    config = trusted / "conformance.json"
    policy = json.loads(config.read_text())
    policy["protected"] = {
        "tests": ["tests"],
        "files": [".github/workflows"],
        "escape_markers": ["pytest.mark.skip"],
    }
    config.write_text(json.dumps(policy))
    weakened = invoke(args, expected=1)
    assert check(weakened)["state"] == "fail" and codes(weakened) == ["test-altered"]
    posture(weakened, "protected")

    write(target, test, body + "\n\ndef test_again():\n    assert result() == 42\n")
    write(target, "tests/test_more.py", "def test_more():\n    assert True\n")
    added = invoke(args, expected=None)
    assert check(added)["state"] == "pass", check(added)

    write(target, workflow, "on: workflow_dispatch\n")
    write(
        target,
        "tests/test_more.py",
        "import pytest\n\n\n@pytest.mark.skip\ndef test_more():\n    assert False\n",
    )
    assert codes(invoke(args, expected=1)) == ["escape-marker-added", "protected-file-changed"]
    (target / test).unlink()
    assert "test-removed" in codes(invoke(args, expected=1))


def _junit(outcome=""):
    return (
        '<?xml version="1.0"?><testsuites><testsuite name="pytest" tests="1">'
        '<testcase classname="tests.result" name="test_the_result_is_the_answer" time="0.01">'
        f"{outcome}</testcase></testsuite></testsuites>"
    )


def feature_answer(write, git, invoke, args, posture):
    """One answer for a feature: done, continue or escalate, with stable exit codes (L07a)."""
    target = Path(args[args.index("--target") + 1])
    write(target, "features/01_result/acceptance.feature", FEATURE)
    write(target, ".gitignore", "junit.xml\ngovkit-evidence-record.json\n")
    git("add", ".")
    git("commit", "-qm", "a feature and its ignore rules")
    args = list(args)
    args[args.index("--base") + 1] = git("rev-parse", "HEAD")
    args += ["--feature", "01_result"]
    command = [sys.executable, "-I", "-m", "cli.govkit"]

    def record():
        recorded = [*command, "evidence", "--record", "--target", str(target)]
        subprocess.run(recorded, check=True, capture_output=True)

    def codes(answer):
        return [(reason["state"], reason["code"]) for reason in answer["reasons"]]

    write(target, "src/service.py", "def result():\n    return 42\n\n# touched\n")
    missing = invoke(args, expected=1)
    assert codes(missing) == [("continue", "result-missing")], missing["reasons"]

    write(target, "junit.xml", _junit())
    assert codes(invoke(args, expected=1)) == [("continue", "results-unrecorded")]
    record()
    done = invoke(args, expected=0)
    assert done["state"] == "done" and done["reasons"] == [], done["reasons"]
    assert change_conformance.parse_feature_verdict(done) == done
    assert done["evidence"]["outcome"] == "PASS" and done["change"]["exit_code"] == 0
    posture(done["change"], "feature-answer")
    text = subprocess.run(
        command + [a for a in args if a != "--json"], capture_output=True, text=True
    )
    assert text.returncode == 0 and "Feature 01_result: DONE" in text.stdout, text.stdout

    write(target, "src/service.py", "def result():\n    return 42\n\n# touched again\n")
    assert codes(invoke(args, expected=1)) == [("continue", "results-stale")]

    write(target, "junit.xml", _junit('<failure message="boom">trace</failure>'))
    record()
    failed = invoke(args, expected=1)
    assert failed["state"] == "continue" and codes(failed) == [("continue", "result-failed")]
    assert failed["reasons"][0]["requirements"] == ["01_result#scenario:result-value"]

    write(target, "junit.xml", _junit('<skipped message="no service"/>'))
    record()
    skipped = invoke(args, expected=3)
    assert skipped["state"] == "escalate" and codes(skipped) == [("escalate", "result-skipped")]
    assert change_conformance.parse_feature_verdict(skipped) == skipped

    write(target, "junit.xml", _junit('<failure message="boom">trace</failure>'))
    write(target, "features/01_result/acceptance.feature", FEATURE.replace("it is 42", "it is 7"))
    record()
    weakened = invoke(args, expected=3)
    assert codes(weakened)[0] == ("escalate", "definition-changed"), weakened["reasons"]
    assert ("continue", "result-failed") in codes(weakened)

    unknown = subprocess.run(command + args[:-1] + ["nowhere"], capture_output=True, text=True)
    assert unknown.returncode == 2 and unknown.stdout == "", unknown


if __name__ == "__main__":
    assert Path(change_conformance.__file__).is_relative_to(sys.prefix)
    example = json.loads((paths.GOVERNANCE_DIR / "examples/posture/change.json").read_text())
    assert parse_change_posture(example).document == example
    for name in PILOTS:
        with tempfile.TemporaryDirectory(prefix="govkit-change-pilot-") as directory:
            # The create-only writer rejects symlink parents, including macOS /var.
            run_pilot(Path(directory).resolve(), name)
    with tempfile.TemporaryDirectory(prefix="govkit-change-pilot-") as directory:
        run_pilot(Path(directory).resolve(), "enhancement", definition_change)
    with tempfile.TemporaryDirectory(prefix="govkit-change-pilot-") as directory:
        run_pilot(Path(directory).resolve(), "enhancement", protected_change)
    with tempfile.TemporaryDirectory(prefix="govkit-change-pilot-") as directory:
        run_pilot(Path(directory).resolve(), "enhancement", feature_answer)
    answer = json.loads(
        (paths.GOVERNANCE_DIR / "examples/feature-verdict/feature-verdict.json").read_text()
    )
    assert change_conformance.parse_feature_verdict(answer) == answer
    print(
        "Eight actual-change pilots, the definition check, the protected-file check and the feature answer: real outcomes, private posture, planned metadata preservation, source pointer integrity and protected publication verified."
    )
