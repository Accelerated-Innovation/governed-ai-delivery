"""Feature-scoped validate and the known-failures record from a clean wheel.

Run with the wheel's Python and -I; never import this checkout's CLI. The
features are starters with files removed. Passing runs show GovKit's selection
and record handling, not that any project control ran or that a record was
reviewed.
"""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from cli import known_failures, paths

assert Path(known_failures.__file__).is_relative_to(sys.prefix)

COMMAND = [sys.executable, "-I", "-m", "cli.govkit"]
AGENTS = ("codex", "claude-code", "copilot")


def govkit(*args, expected=0):
    environment = dict(os.environ)
    environment.pop("CI", None)
    result = subprocess.run(
        COMMAND + [str(a) for a in args],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        env=environment,
    )
    assert result.returncode == expected, (args, result.returncode, result.stdout, result.stderr)
    return result.stdout


def bundled_contract():
    schema = paths.GOVERNANCE_DIR / "schemas/known-failures.schema.json"
    example = paths.GOVERNANCE_DIR / "examples/known-failures/known-failures.json"
    assert schema.is_file() and example.is_file()
    kinds = {key[0] for key in known_failures.load(example).entries}
    assert kinds == set(known_failures.CHECKS_BY_SCOPE), kinds


def scoped_run(workspace, agent):
    target = workspace / agent
    target.mkdir()
    govkit(
        "apply",
        "--agent",
        agent,
        "--target",
        target,
        "--level",
        "4",
        "--type",
        "api",
        "--ci",
        "github",
    )
    for name in ("alpha", "beta"):
        govkit("init", name, "--target", target, "--starter", "backend")
    (target / "features/beta/plan.md").unlink()
    validate = ("validate", "--target", target)

    # The record is printed, never written; the caller saves it outside the tree.
    before = sorted(p.as_posix() for p in target.rglob("*"))
    text = govkit(*validate, "--print-known-failures")
    assert sorted(p.as_posix() for p in target.rglob("*")) == before
    missing_plan = {
        "scope": {"kind": "feature", "name": "beta"},
        "check": "completeness",
        "finding": "plan.md",
    }
    assert missing_plan in json.loads(text)["known_failures"]
    record = workspace / f"{agent}-known-failures.json"
    record.write_text(text, encoding="utf-8")
    digest = hashlib.sha256(record.read_bytes()).hexdigest()

    out = govkit(*validate, "--known-failures", record, "--known-failures-digest", digest)
    assert "outside the inspected tree" in out and f"sha256:{digest}" in out
    assert "[completeness/plan.md] plan.md is missing" in out
    assert "2 feature(s) selected: 0 new failure(s)" in out and "0 resolved" in out
    assert "digest" in govkit(
        *validate, "--known-failures", record, "--known-failures-digest", "0" * 64, expected=1
    )

    # Scoped runs: the selected feature alone decides the exit status.
    govkit(*validate, "--feature", "beta", expected=1)
    out = govkit(*validate, "--feature", "beta", "--known-failures", record)
    assert "1 feature(s) selected" in out and "features/alpha/" not in out
    assert "nope" in govkit(*validate, "--feature", "nope", expected=1)

    # A new failure in a feature that already has known failures fails the run,
    # but only for a selection that includes that feature.
    (target / "features/beta/nfrs.md").unlink()
    out = govkit(*validate, "--known-failures", record, expected=1)
    assert "[completeness/nfrs.md] nfrs.md is missing" in out
    govkit(*validate, "--feature", "alpha", "--known-failures", record)

    # A recorded failure that now passes is resolved: lenient, then strict.
    stale = json.loads(text)
    stale["known_failures"] = [missing_plan]
    resolved = workspace / f"{agent}-resolved.json"
    resolved.write_text(json.dumps(stale), encoding="utf-8")
    (target / "features/beta/plan.md").write_text(
        (target / "features/alpha/plan.md").read_text(encoding="utf-8"), encoding="utf-8"
    )
    only = (*validate, "--only", "experiments", "--feature", "beta", "--known-failures", resolved)
    assert "0 resolved" in govkit(*only)
    out = subprocess.run(
        COMMAND + [str(a) for a in (*validate, "--feature", "beta", "--known-failures", resolved)],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
    ).stdout
    assert "1 resolved" in out and "RESOLVED" in out, out
    print(f"  {agent}: scoped and known-failures runs behaved as specified [synthetic-fixture]")


def main():
    bundled_contract()
    with tempfile.TemporaryDirectory() as folder:
        for agent in AGENTS:
            scoped_run(Path(folder), agent)
    print("wheel validate smoke: OK")


if __name__ == "__main__":
    main()
