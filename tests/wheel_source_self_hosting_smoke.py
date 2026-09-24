"""Inspect the actual source checkout with an installed wheel and test dependencies.

This is a local model demonstration using candidate policy, not protected PR
admission. Its expected canonical outcome is unknown, never a conformance pass.
"""

import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from cli import change_conformance
from cli.change_scope import capture_change
from cli.posture import reference
from cli.posture_change import parse_change_posture


def invoke(*args):
    return subprocess.run(
        [sys.executable, "-I", "-B", "-m", "cli.govkit", *map(str, args)],
        capture_output=True,
        text=True,
        timeout=300,
    )


def run(root):
    assert Path(change_conformance.__file__).is_relative_to(sys.prefix)
    base = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    before = capture_change(root, base)
    assert before.complete, before.problems
    assert not (root / ".govkit/marker.json").exists()
    for action in (("profile", "preview"), ("pack", "verify"), ("pipeline", "catalog")):
        result = invoke(*action, "--target", root, "--json")
        assert result.returncode == 0, (action, result.stdout, result.stderr)
        if action[0] == "pipeline":
            catalog = json.loads(result.stdout)
            assert catalog["ready"] and catalog["pins"]["packs"] == []
            assert catalog["execution"] == "not-run" and catalog["enforcement"] == "unknown"
    with tempfile.TemporaryDirectory(prefix="govkit-source-wheel-") as directory:
        evidence = Path(directory).resolve()
        policy = evidence / "policy"
        # Explicit bootstrap fixture. A separate copy alone conveys no authority.
        shutil.copytree(root / ".govkit", policy / ".govkit")
        result = invoke(
            "conform",
            "--target",
            root,
            "--policy-target",
            policy,
            "--request",
            policy / ".govkit/requests/source-maintenance.json",
            "--base",
            base,
            "--observed-at",
            datetime.now(timezone.utc).isoformat(),
            "--execute-check",
            "project:tests",
            "--execute-check",
            "project:pipeline-contract",
            "--json",
        )
        assert result.stdout, result.stderr
        record = evidence / "change.json"
        record.write_text(result.stdout)
        report = change_conformance.load_change_report(record).document
        checks = {c["id"]: c for c in report["checks"]["results"]}
        for identifier in ("project:tests", "project:pipeline-contract", "change:stable-inputs"):
            assert checks[identifier]["state"] == "pass", checks[identifier]
            assert checks[identifier]["execution"] == "executed"
        unknowns = {c["id"] for c in checks.values() if c["state"] == "unknown"}
        assert unknowns == {"provider:protected-caller", "change:architecture"}, checks
        assert report["state"] == "unknown" and result.returncode != 0
        assert report["plan"]["decisions"] == []
        exported = invoke("posture", "change", "--results", record, "--json")
        assert exported.returncode == 0, exported.stderr
        posture = parse_change_posture(json.loads(exported.stdout)).document
        assert posture["coverage"]["provider_enforcement"] == "not-supplied"
        assert posture["results"]["state"] == "unknown"
        controls = {c["ref"]: c for c in posture["results"]["controls"]}
        for identifier in unknowns:
            assert controls[reference("control", identifier)]["state"] == "unknown"
        human = invoke("posture", "change", "--results", record)
        assert human.returncode == 0 and "unknown" in human.stdout, human.stderr
    assert capture_change(root, base).digest == before.digest
    print(
        "Installed-wheel source self-hosting verified: model and empty lock resolved, "
        "both selected commands executed, inputs stable, canonical posture replayed. "
        "Conformance remains unknown: architecture and protected-caller evidence unmeasured. "
        "Candidate-policy smoke only; not protected admission."
    )


if __name__ == "__main__":
    run(Path(sys.argv[1]).resolve())
