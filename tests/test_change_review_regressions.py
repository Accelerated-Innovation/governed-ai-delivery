"""Reproductions of PR 187 review findings against real Git and command execution."""

import json
import shutil

import pytest

from cli.change_conformance import inspect_change
from cli.change_scope import capture_change
from cli.check_models import State
from cli.workflows import parse_request
from tests.test_change_conformance import (
    configure_transition,
    git,
    inspect,
    result,
    setup,
    transition,
)
from tests.test_discovery import write
from tests.test_fixes import _valid_record
from tests.test_workflows import request


def defect_fixture(tmp_path, script, *, regression="pass\n", baseline="good", extra=None):
    target, trusted, _ = setup(tmp_path)
    doc = request("defect")
    doc["scope"] = ["src", "tests"]
    doc["references"] = [
        {"kind": "established-behavior", "reference": "architecture.md", "authority": "accepted"},
        {"kind": "regression-test", "reference": "tests/test_service.py", "authority": "observed"},
    ]
    shutil.copy(trusted / "architecture.md", target / "architecture.md")
    if regression is not None:
        write(target, "tests/test_service.py", regression)
    record = _valid_record("restore")
    record["expectation"]["source"] = "architecture.md"
    record["reproduction"]["test"] = "tests/test_service.py"
    record["surface"]["paths"] = ["src/service.py", "tests/test_service.py"]
    write(target, "fixes/restore/fix.yaml", json.dumps(record))
    path = trusted / "conformance.json"
    config = json.loads(path.read_text())
    config["impact_rules"][0]["paths"].append("tests")
    config["artifacts"].append({"id": "fix-record", "references": ["fixes/restore/fix.yaml"]})
    config["commands"][0]["argv"] = ["{python}", "-c", script]
    path.write_text(json.dumps(config))
    write(target, "src/service.py", baseline)
    if extra:
        extra(target)
    git(target, "add", ".")
    git(target, "commit", "-qm", "defect baseline")
    return target, trusted, git(target, "rev-parse", "HEAD"), doc


def eligibility(target, trusted, base, doc):
    report = inspect(
        target, trusted, base, doc, execute_checks=("project:tests", "defect:eligibility")
    )
    return result(report, "defect:eligibility").outcome.state


@pytest.mark.parametrize("old_test", [None, "raise AssertionError('old test')\n"])
def test_same_current_regression_must_run_against_both_snapshots(tmp_path, old_test):
    target, trusted, base, doc = defect_fixture(
        tmp_path, "import runpy; runpy.run_path('tests/test_service.py')", regression=old_test
    )
    write(
        target,
        "tests/test_service.py",
        "from pathlib import Path\nassert Path('src/service.py').read_text() == 'good'\n",
    )
    assert eligibility(target, trusted, base, doc) is State.FAIL  # No production fix occurred.


def test_new_regression_can_prove_a_real_production_fix(tmp_path):
    target, trusted, base, doc = defect_fixture(
        tmp_path,
        "import runpy; runpy.run_path('tests/test_service.py')",
        regression=None,
        baseline="broken",
    )
    write(
        target,
        "tests/test_service.py",
        "from pathlib import Path\nassert Path('src/service.py').read_text() == 'good'\n",
    )
    write(target, "src/service.py", "good")
    assert eligibility(target, trusted, base, doc) is State.PASS


def test_executable_mode_is_preserved_in_defect_baseline(tmp_path):
    def executable(target):
        path = write(target, "tests/probe.sh", "#!/bin/sh\nexit 0\n")
        path.chmod(0o755)

    args = defect_fixture(
        tmp_path,
        "import subprocess; subprocess.run(['./tests/probe.sh'], check=True)",
        extra=executable,
    )
    assert eligibility(*args) is State.FAIL


@pytest.mark.parametrize("dependency", [".git", "ignored.txt"])
def test_missing_snapshot_dependencies_cannot_prove_red_green(tmp_path, dependency):
    def ignored(target):
        write(target, ".gitignore", "ignored.txt\n")
        write(target, "ignored.txt", "dependency")

    args = defect_fixture(
        tmp_path, f"from pathlib import Path; assert Path({dependency!r}).exists()", extra=ignored
    )
    assert eligibility(*args) is State.UNKNOWN


@pytest.mark.parametrize("expired_first", [False, True])
def test_each_transition_requires_its_own_valid_exception(tmp_path, expired_first):
    valid, expired = transition(), transition("2020-01-01")
    expired["id"] = "other"
    expired["exceptions"][0]["id"] = "other-old"
    target, trusted, _ = setup(
        tmp_path, transitions=[expired, valid] if expired_first else [valid, expired]
    )
    configure_transition(trusted)
    write(target, "src/old.py", "import forbidden\n")
    git(target, "add", ".")
    git(target, "commit", "-qm", "existing violation")
    outcome = result(
        inspect(target, trusted, git(target, "rev-parse", "HEAD")), "change:architecture"
    ).outcome
    assert outcome.state is State.FAIL
    assert any(f.code == "expired-exception" for f in outcome.findings)


def test_valid_transition_exception_with_shared_top_level_contract(tmp_path):
    target, trusted, _ = setup(tmp_path, transitions=[transition()])
    configure_transition(trusted)
    write(target, "src/old.py", "import forbidden\n")
    git(target, "add", ".")
    git(target, "commit", "-qm", "existing exception")
    outcome = result(
        inspect(target, trusted, git(target, "rev-parse", "HEAD")), "change:architecture"
    ).outcome
    assert outcome.state is State.PASS
    assert [f.code for f in outcome.findings] == ["existing-exception"]


def test_skip_worktree_missing_file_is_not_a_deletion(tmp_path):
    target, _, base = setup(tmp_path)
    git(target, "update-index", "--skip-worktree", "src/service.py")
    (target / "src/service.py").unlink()
    change = capture_change(target, base)
    assert not change.complete
    assert "src/service.py" not in change.paths


def test_staged_change_restored_in_worktree_still_blocks_scope(tmp_path):
    target, trusted, base = setup(tmp_path)
    original = (target / "src/service.py").read_bytes()
    write(target, "src/service.py", "import forbidden\n")
    git(target, "add", "src/service.py")
    (target / "src/service.py").write_bytes(original)
    change = capture_change(target, base)
    assert "src/service.py" in change.paths
    assert not change.complete
    report = inspect(target, trusted, base, execute_checks=("project:tests",))
    assert result(report, "change:scope").outcome.state is State.UNKNOWN
    assert report.exit_code == 1
    first_digest = change.digest
    write(target, "src/service.py", "different staged content\n")
    git(target, "add", "src/service.py")
    (target / "src/service.py").write_bytes(original)
    assert capture_change(target, base).digest != first_digest


def test_target_cannot_be_nested_under_trusted_policy(tmp_path):
    target, trusted, base = setup(tmp_path)
    nested = trusted / "consumer"
    shutil.move(target, nested)
    with pytest.raises(ValueError, match="separate trusted checkout"):
        inspect(nested, trusted, base, execute_checks=("project:tests",))


@pytest.mark.parametrize("required", [False, True])
def test_pack_arguments_require_a_selected_required_pack(tmp_path, required):
    target, trusted, base = setup(tmp_path, llm=True)
    with pytest.raises(ValueError, match="selected pack"):
        inspect(
            target,
            trusted,
            base,
            request(llm=required),
            pack_arguments={"llm-exact-match": ["--results", "results.json"]},
        )


@pytest.mark.parametrize(
    "observed_at",
    ["2026-09-23", "2026-09-23T12:00:00", "2026-09-23 12:00:00Z", "2026-09-23T12:00:00+00:60"],
)
def test_invalid_timestamp_is_rejected_before_commands(tmp_path, observed_at):
    target, trusted, base = setup(tmp_path)
    path = trusted / "conformance.json"
    config = json.loads(path.read_text())
    config["commands"][0]["argv"] = [
        "{python}",
        "-c",
        "from pathlib import Path; Path('ran.txt').write_text('ran')",
    ]
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError, match="RFC 3339"):
        inspect_change(
            target,
            parse_request(request()),
            base=base,
            policy_target=trusted,
            observed_at=observed_at,
            execute_checks=("project:tests",),
        )
    assert not (target / "ran.txt").exists()


@pytest.mark.parametrize("observed_at", ["2026-09-23T12:00:00-04:00", "2026-09-23t12:00:00z"])
def test_rfc3339_timezone_forms_are_supported(tmp_path, observed_at):
    target, trusted, base = setup(tmp_path)
    report = inspect_change(
        target,
        parse_request(request()),
        base=base,
        policy_target=trusted,
        observed_at=observed_at,
        execute_checks=("project:tests",),
    )
    assert report.exit_code == 0


@pytest.mark.parametrize("staged_kind", ["added", "deleted", "mode"])
def test_staged_only_deltas_cannot_disappear_from_scope(tmp_path, staged_kind):
    target, _, base = setup(tmp_path)
    name = "src/new.py" if staged_kind == "added" else "src/service.py"
    path = target / name
    if staged_kind == "added":
        write(target, name, "# staged\n")
        git(target, "add", name)
        path.unlink()
    elif staged_kind == "deleted":
        git(target, "rm", "--cached", name)
    else:
        git(target, "update-index", "--chmod=+x", name)
    change = capture_change(target, base)
    assert not change.complete
    assert name in change.paths


def test_index_only_mutation_during_execution_invalidates_report(tmp_path):
    target, trusted, base = setup(tmp_path)
    path = trusted / "conformance.json"
    config = json.loads(path.read_text())
    config["commands"][0]["argv"] = [
        "{python}",
        "-c",
        "import subprocess; subprocess.run(['git', 'update-index', '--chmod=+x', 'src/service.py'], check=True)",
    ]
    path.write_text(json.dumps(config))
    report = inspect(target, trusted, base, execute_checks=("project:tests",))
    assert result(report, "change:stable-inputs").outcome.state is State.FAIL
    assert report.exit_code == 1
