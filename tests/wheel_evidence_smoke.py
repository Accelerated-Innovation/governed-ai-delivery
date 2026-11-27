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


def git(target: Path, *args) -> None:
    environment = dict(
        os.environ,
        GIT_AUTHOR_NAME="smoke", GIT_AUTHOR_EMAIL="smoke@example.invalid",
        GIT_COMMITTER_NAME="smoke", GIT_COMMITTER_EMAIL="smoke@example.invalid",
    )  # fmt: skip
    subprocess.run(
        ["git", "-C", str(target), *args], check=True, capture_output=True, env=environment
    )


def without_provenance(report: dict) -> dict:
    """The commit, tree digest and time are this run's own; the rest is the example's."""
    return {key: value for key, value in report.items() if key != "provenance"}


def example_project(target: Path, feature: str) -> None:
    """A committed project, then the results of a test run and its record."""
    directory = target / "features" / feature
    directory.mkdir(parents=True, exist_ok=True)
    shutil.copy(EXAMPLE / "acceptance.feature", directory)
    shutil.copy(EXAMPLE / "eval_criteria.yaml", directory)
    git(target, "init", "-q", "-b", "main")
    git(target, "add", "-A")
    git(target, "commit", "-q", "-m", "project")
    shutil.copy(EXAMPLE / "evaluation-run.json", target / "govkit-eval-results.json")
    # Stored under a name evidence discovery does not match; see the guide.
    shutil.copy(EXAMPLE / "test-run.xml", target / "junit.xml")
    govkit("evidence", "--target", target, "--record")


def bundled_contract() -> dict:
    assert (paths.GOVERNANCE_DIR / "schemas/evidence-report.schema.json").is_file()
    assert (paths.GOVERNANCE_DIR / "schemas/evaluation-results.schema.json").is_file()
    validate_document(
        json.loads((EXAMPLE / "evaluation-run.json").read_text(encoding="utf-8")),
        "evaluation-results",
    )
    example = json.loads((EXAMPLE / "evidence-report.json").read_text(encoding="utf-8"))
    validate_document(example, evidence_report.SCHEMA)
    assert (paths.GOVERNANCE_DIR / "schemas/evidence-record.schema.json").is_file()
    validate_document(
        json.loads((EXAMPLE / "record.json").read_text(encoding="utf-8")), "evidence-record"
    )
    run = paths.GOVERNANCE_DIR / "examples" / "verification-run"
    assert (run / "acceptance.baseline.feature").is_file()
    validate_document(
        json.loads((run / "verification-run.json").read_text(encoding="utf-8")),
        "verification-run",
    )
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
    assert without_provenance(report) == without_provenance(example), report
    assert report["provenance"]["state"] == "current", report["provenance"]
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

    # Rewritten results are stale until they are recorded again.
    stale = json.loads(
        govkit("evidence", "--target", target, "--feature", feature, "--json", expected=1)
    )
    assert stale["provenance"]["state"] == "stale", stale["provenance"]
    assert stale["outcome"] == "INCONCLUSIVE", stale["detail"]
    govkit("evidence", "--target", target, "--record")
    still_owed = json.loads(
        govkit("evidence", "--target", target, "--feature", feature, "--json", expected=1)
    )
    assert still_owed["outcome"] == "FAIL", still_owed["detail"]
    assert still_owed["summary"]["owed"] == 1

    # The scenarios pass now. The criteria need results too, including the one
    # that needs a person, which GovKit reports as owed and never starts.
    measured = {
        "routing-explanation-faithfulness": (0.91, "ratio", "faithfulness"),
        "routing-p95-latency": (0.18, "seconds", "p95_latency"),
        "refusal-safety": (0.995, None, None),
        "explanation-tone-review": (0.9, None, None),
    }
    results = []
    for name, (value, unit, metric) in measured.items():
        entry = {"requirement_id": f"{feature}#evaluation:{name}", "value": value}
        if unit:
            entry.update(unit=unit, metric=metric)
        results.append(entry)
    document = {"schema_version": 1, "kind": "govkit.evaluation-results", "results": results}
    validate_document(document, "evaluation-results")
    (target / "govkit-eval-results.json").write_text(json.dumps(document), encoding="utf-8")
    govkit("evidence", "--target", target, "--record")
    done = json.loads(govkit("evidence", "--target", target, "--feature", feature, "--json"))
    validate_document(done, evidence_report.SCHEMA)
    assert done["outcome"] == "PASS", done["detail"]

    # An edit after the record: the same results no longer count.
    source = target / "features" / feature / "acceptance.feature"
    original = source.read_text(encoding="utf-8")
    source.write_text(original + "\n# edited after the tests ran\n", encoding="utf-8")
    edited = json.loads(
        govkit("evidence", "--target", target, "--feature", feature, "--json", expected=1)
    )
    assert edited["provenance"]["state"] == "stale", edited["provenance"]
    source.write_text(original, encoding="utf-8")
    govkit("evidence", "--target", target, "--feature", feature)

    # A new commit: stale again until the tests are run and recorded.
    (target / "notes.txt").write_text("a change\n", encoding="utf-8")
    git(target, "add", "-A", "--", "notes.txt")
    git(target, "commit", "-q", "-m", "change")
    committed = json.loads(
        govkit("evidence", "--target", target, "--feature", feature, "--json", expected=1)
    )
    assert committed["provenance"]["state"] == "stale", committed["provenance"]
    govkit("evidence", "--target", target, "--record")
    govkit("evidence", "--target", target, "--feature", feature)
    govkit("evidence", "--target", target, "--record", "--feature", feature, expected=2)
    assert [r["revision_digest"] for r in done["results"]] == [
        r["revision_digest"] for r in example["results"]
    ]

    govkit("evidence", "--target", target, "--feature", "nope", expected=2)
    govkit("evidence", "--target", target, "--json", expected=2)
    print(
        "  level-free: report, record, staleness, fix-and-rerun and usage errors [bundled-example]"
    )


def stated_location_run(workspace: Path, example: dict) -> None:
    """Results under a name the default search does not match, as Maven writes them."""
    target = workspace / "stated-location"
    feature = example["feature"]["name"]
    example_project(target, feature)
    reports = target / "target" / "surefire-reports"
    reports.mkdir(parents=True)
    (target / "junit.xml").rename(reports / "TEST-com.example.RoutingTest.xml")
    (target / "govkit-evidence-record.json").unlink()
    by_name = json.loads(
        govkit("evidence", "--target", target, "--feature", feature, "--json", expected=1)
    )
    assert [s["tool"] for s in by_name["sources"]] == ["evaluation-results"], by_name["sources"]

    pattern = "target/surefire-reports/TEST-*.xml"
    govkit("evidence", "--target", target, "--record", "--junit", "target/*.xml", expected=1)
    govkit("evidence", "--target", target, "--record", "--junit", "features/**/*", expected=1)
    govkit("evidence", "--target", target, "--record", "--junit", "../*.xml", expected=1)
    assert not (target / "govkit-evidence-record.json").exists(), "a refused record was written"
    govkit("evidence", "--target", target, "--junit", pattern, expected=2)
    govkit("evidence", "--target", target, "--record", "--junit", pattern)
    record = json.loads((target / "govkit-evidence-record.json").read_text(encoding="utf-8"))
    validate_document(record, "evidence-record")
    assert record["junit_patterns"] == [pattern], record
    report = json.loads(
        govkit("evidence", "--target", target, "--feature", feature, "--json", expected=1)
    )
    assert report["provenance"]["state"] == "current", report["provenance"]
    # The same verdicts as the example; only the file each test came from differs.
    assert report["outcome"] == example["outcome"] and report["summary"] == example["summary"]
    assert [(r["requirement_id"], r["outcome"]) for r in report["results"]] == [
        (r["requirement_id"], r["outcome"]) for r in example["results"]
    ], report["results"]
    assert [s["path"] for s in report["sources"] if s["tool"] == "junit"] == [
        "target/surefire-reports/TEST-com.example.RoutingTest.xml"
    ]

    # A recorded result file that is deleted: what is left no longer counts.
    (reports / "TEST-com.example.RoutingTest.xml").unlink()
    gone = json.loads(
        govkit("evidence", "--target", target, "--feature", feature, "--json", expected=1)
    )
    assert gone["provenance"]["state"] == "stale", gone["provenance"]
    print("  stated location: refused patterns, record, report and a removed file [synthetic]")


def changed_run(workspace: Path, example: dict) -> None:
    """`--changed-since`: every feature the change touches, and no other."""
    target = workspace / "changed"
    feature = example["feature"]["name"]
    example_project(target, feature)
    untouched = govkit("evidence", "--target", target, "--changed-since", "HEAD")
    assert "no feature was judged" in untouched, untouched

    (target / "features" / feature / "plan.md").write_text("# Plan\n", encoding="utf-8")
    other = target / "features" / "08_untouched"
    other.mkdir()
    shutil.copy(EXAMPLE / "acceptance.feature", other)
    git(target, "add", "features/08_untouched")
    git(target, "commit", "-q", "-m", "another feature")
    govkit("evidence", "--target", target, "--record")
    # The example's own outcome is not a pass, so its feature fails the run.
    assert example["outcome"] != "PASS"
    touched = govkit("evidence", "--target", target, "--changed-since", "HEAD", expected=1)
    assert f"feature {feature}" in touched and "08_untouched" not in touched, touched
    assert "1 of 1 changed feature(s) did not pass." in touched, touched
    both = govkit("evidence", "--target", target, "--changed-since", "HEAD~1", expected=1)
    assert "2 changed feature(s) did not pass." in both, both
    govkit("evidence", "--target", target, "--changed-since", "no-such-ref", expected=2)
    govkit("evidence", "--target", target, "--changed-since", "HEAD", "--json", expected=2)


def verification_run(workspace: Path, example: dict) -> None:
    """`verification-run build`: the run for the graph, from a real tagged baseline."""
    target = workspace / "run"
    feature = example["feature"]["name"]
    example_project(target, feature)
    build = (
        "verification-run", "build", "--target", target, "--baseline", "baseline-1",
        "--repository", "acme/invoices", "--run-reference", "github:1234567890-1",
        "--build-ref", "1234567890", "--artifact", "https://ci.example.invalid/runs/1234567890",
    )  # fmt: skip
    govkit(*build, expected=2)  # the baseline is not tagged yet
    git(target, "tag", "baseline-1")
    before = sorted(p.as_posix() for p in target.rglob("*") if "/.git/" not in p.as_posix())
    document = json.loads(govkit(*build))
    validate_document(document, "verification-run")
    after = sorted(p.as_posix() for p in target.rglob("*") if "/.git/" not in p.as_posix())
    assert after == before, "the build wrote a file"
    sent = {r["requirement_id"]: r for r in document["request"]["results"]}
    reported = {r["requirement_id"]: r for r in example["results"]}
    assert len(sent) == 5 and document["summary"]["reasons"]["no-result"] == 3, document
    for identifier, result in sent.items():
        assert result["revision_digest"] == reported[identifier]["revision_digest"]
        assert result["result"] == reported[identifier]["outcome"]
    assert json.loads(govkit(*build)) == document, "a second build differs"

    # Publication refuses a path through a link, and a temporary folder may be one.
    output = workspace.resolve() / "run.json"
    govkit(*build, "--output", output)
    assert json.loads(output.read_text(encoding="utf-8")) == document
    govkit(*build, "--output", output, expected=2)
    govkit(*build, "--output", target / "run.json", expected=2)

    # An edited scenario is left out; the baseline still holds the others.
    source = target / "features" / feature / "acceptance.feature"
    text = source.read_text(encoding="utf-8")
    source.write_text(text.replace("Given 100 invoices", "Given 500 invoices"), encoding="utf-8")
    edited = json.loads(govkit(*build, expected=1))
    assert edited["request"] is None and edited["features"][0]["evidence"] == "stale", edited
    git(target, "add", "-A", "--", "features")
    git(target, "commit", "-q", "-m", "edit a scenario")
    govkit("evidence", "--target", target, "--record")
    changed = json.loads(govkit(*build))
    assert changed["summary"]["reasons"]["revision-changed"] == 1, changed["summary"]
    assert len(changed["request"]["results"]) == 4
    assert changed["request"]["build"]["commit"] != document["request"]["build"]["commit"]
    print("  verification run: built, replayed, published, left out by revision [real Git]")


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
    assert without_provenance(report) == without_provenance(example), report
    assert report["provenance"]["state"] == "current", report["provenance"]
    print("  legacy level 4: the same report [bundled-example]")


def main():
    example = bundled_contract()
    with tempfile.TemporaryDirectory() as folder:
        level_free_run(Path(folder), example)
        stated_location_run(Path(folder), example)
        changed_run(Path(folder), example)
        verification_run(Path(folder), example)
        legacy_run(Path(folder), example)
    print("wheel evidence smoke: OK")


if __name__ == "__main__":
    main()
