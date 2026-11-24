"""`govkit evidence --feature` and its JSON report from a clean wheel.

Run with the wheel's Python and -I; never import this checkout's CLI. The
project is the bundled example, so a passing run shows that GovKit binds
scenarios to results and prints a valid report. It does not show that any
project's tests ran.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from cli import evidence_report, paths
from cli.schema_validation import validate_document

assert Path(evidence_report.__file__).is_relative_to(sys.prefix)

COMMAND = [sys.executable, "-I", "-m", "cli.govkit"]
EXAMPLE = paths.GOVERNANCE_DIR / "examples" / "evidence-report"


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


def example_project(target: Path, feature: str) -> None:
    directory = target / "features" / feature
    directory.mkdir(parents=True)
    shutil.copy(EXAMPLE / "acceptance.feature", directory)
    shutil.copy(EXAMPLE / "junit.xml", target)


def bundled_contract() -> dict:
    assert (paths.GOVERNANCE_DIR / "schemas/evidence-report.schema.json").is_file()
    example = json.loads((EXAMPLE / "evidence-report.json").read_text(encoding="utf-8"))
    validate_document(example, evidence_report.SCHEMA)
    return example


def level_free_run(workspace: Path, example: dict) -> None:
    """No marker and no level: a project needs only the feature and the results."""
    target = workspace / "level-free"
    feature = example["feature"]["name"]
    example_project(target, feature)
    before = sorted(p.as_posix() for p in target.rglob("*"))
    report = json.loads(
        govkit("evidence", "--target", target, "--feature", feature, "--json", expected=1)
    )
    assert report == example, report
    assert sorted(p.as_posix() for p in target.rglob("*")) == before, "the report wrote a file"
    text = govkit("evidence", "--target", target, "--feature", feature, expected=1)
    assert "FAIL" in text and "missing" in text, text

    # Fix what the report names, and the same command says the feature is done.
    junit = target / "junit.xml"
    fixed = junit.read_text(encoding="utf-8")
    fixed = fixed.replace('<skipped message="directory service unavailable"/>', "")
    fixed = fixed.replace('<failure message="p95 was 240 ms">assert 240 &lt;= 200</failure>', "")
    fixed = fixed.replace(
        'name="test_amount_parses"', 'name="test_a_rejected_invoice_returns_to_its_author"'
    )
    fixed = fixed.replace('failures="1"', 'failures="0"').replace('skipped="1"', 'skipped="0"')
    junit.write_text(fixed, encoding="utf-8")
    done = json.loads(govkit("evidence", "--target", target, "--feature", feature, "--json"))
    validate_document(done, evidence_report.SCHEMA)
    assert done["outcome"] == "PASS", done["detail"]
    assert [r["revision_digest"] for r in done["results"]] == [
        r["revision_digest"] for r in example["results"]
    ]

    govkit("evidence", "--target", target, "--feature", "nope", expected=2)
    govkit("evidence", "--target", target, "--json", expected=2)
    print("  level-free: report, schema, fix-and-rerun and usage errors [bundled-example]")


def legacy_run(workspace: Path, example: dict) -> None:
    """A legacy level 4 install gives the same report; the marker is not used."""
    target = workspace / "legacy"
    target.mkdir()
    govkit(
        "apply", "--agent", "claude-code", "--target", target,
        "--level", "4", "--type", "api", "--ci", "github",
    )  # fmt: skip
    feature = example["feature"]["name"]
    example_project(target, feature)
    report = json.loads(
        govkit("evidence", "--target", target, "--feature", feature, "--json", expected=1)
    )
    assert report == example, report
    print("  legacy level 4: the same report [bundled-example]")


def main():
    example = bundled_contract()
    with tempfile.TemporaryDirectory() as folder:
        level_free_run(Path(folder), example)
        legacy_run(Path(folder), example)
    print("wheel evidence smoke: OK")


if __name__ == "__main__":
    main()
