"""Exceeded scope budgets explain the blocker without weakening conformance."""

import json
import sys

import pytest

from cli.change_conformance import parse_change_report
from cli.change_scope import capture_change
from cli.conformance import render_report
from cli.govkit import main
from cli.posture import reference
from cli.posture_change import export_change_posture
from cli.schema_validation import content_digest
from tests.test_change_conformance import git, inspect, setup
from tests.test_discovery import write
from tests.test_pack_store import snapshot
from tests.test_workflows import request


def repository(tmp_path, files):
    target = tmp_path / "repository"
    target.mkdir()
    git(target, "init", "-q")
    git(target, "config", "user.email", "test@example.invalid")
    git(target, "config", "user.name", "Test")
    for name, content in files.items():
        write(target, name, content)
    git(target, "add", ".")
    git(target, "commit", "-qm", "baseline")
    return target, git(target, "rev-parse", "HEAD")


@pytest.mark.parametrize("phase", ["baseline", "tracked", "untracked"])
@pytest.mark.parametrize("limit", [3, 4])
def test_per_file_limit_reports_phase_path_and_bounded_size(tmp_path, phase, limit):
    target, base = repository(tmp_path, {"asset.js": "DATA" if phase == "baseline" else ""})
    name = "asset.js" if phase != "untracked" else "new.js"
    if phase != "baseline":
        write(target, name, "DATA")
    before = snapshot(target)

    change = capture_change(target, base, max_bytes=limit)

    assert change.complete is (limit == 4), change.problems
    assert snapshot(target) == before
    if limit == 3:
        message = change.problems[0]
        assert ("Baseline" if phase == "baseline" else "Working-tree") in message
        assert json.dumps(name) in message
        assert "4 bytes" in message and "per-file limit of 3 bytes" in message
        assert "DATA" not in message and str(target) not in message


@pytest.mark.parametrize("phase", ["baseline", "working-tree"])
@pytest.mark.parametrize("limit", [7, 8])
def test_total_limit_reports_phase_and_budget_without_file_contents(tmp_path, phase, limit):
    target, base = repository(tmp_path, {"first.txt": "AAAA"})
    write(target, "second.txt", "BBBB")
    if phase == "baseline":
        git(target, "add", ".")
        git(target, "commit", "-qm", "second asset")
        base = git(target, "rev-parse", "HEAD")
    before = snapshot(target)

    change = capture_change(target, base, max_total_bytes=limit)

    assert change.complete is (limit == 8), change.problems
    assert snapshot(target) == before
    if limit == 7:
        message = change.problems[0]
        assert ("Baseline" if phase == "baseline" else "Working-tree") in message
        assert "8 bytes" in message and "total-content limit of 7 bytes" in message
        assert "AAAA" not in message and "BBBB" not in message


@pytest.mark.parametrize(
    "phase,label",
    [("baseline", "Baseline file"), ("index", "Index entry"), ("untracked", "Git-visible path")],
)
@pytest.mark.parametrize("limit", [1, 2])
def test_file_count_limit_identifies_the_inventory_that_exceeds_it(tmp_path, phase, label, limit):
    target, base = repository(tmp_path, {"first.txt": ""})
    write(target, "second.txt", "")
    if phase in {"baseline", "index"}:
        git(target, "add", ".")
    if phase == "baseline":
        git(target, "commit", "-qm", "second asset")
        base = git(target, "rev-parse", "HEAD")
    before = snapshot(target)

    change = capture_change(target, base, max_files=limit)

    assert change.complete is (limit == 2), change.problems
    assert snapshot(target) == before
    if limit == 1:
        assert f"{label} count 2 exceeds limit 1" in change.problems[0]


@pytest.mark.parametrize("limit", [1, 2])
def test_changed_path_budget_reports_count_and_remains_blocking(tmp_path, limit):
    target, base = repository(tmp_path, {"first.txt": "", "second.txt": ""})
    write(target, "first.txt", "one")
    write(target, "second.txt", "two")
    before = snapshot(target)

    change = capture_change(target, base, max_changed=limit)

    assert change.complete is (limit == 2), change.problems
    assert change.paths == ("first.txt", "second.txt")
    assert snapshot(target) == before
    if limit == 1:
        assert "Changed-path count 2 exceeds limit 1" in change.problems[0]


@pytest.mark.skipif(sys.platform == "win32", reason="Windows forbids these path characters")
def test_limit_diagnostic_escapes_control_characters_in_repository_paths(tmp_path):
    name = 'asset\n\x1b[31m".js'
    target, base = repository(tmp_path, {name: "DATA"})

    change = capture_change(target, base, max_bytes=3)

    assert not change.complete
    assert json.dumps(name) in change.problems[0]
    assert "\n" not in change.problems[0] and "\x1b" not in change.problems[0]
    assert "DATA" not in change.problems[0]


def test_unavailable_git_input_does_not_echo_arbitrary_errors_or_arguments(tmp_path):
    target, _ = repository(tmp_path, {"file.txt": ""})

    change = capture_change(target, "secret-looking-missing-ref")

    assert not change.complete
    assert "Git scope is incomplete" in change.problems[0]
    assert "secret-looking" not in change.problems[0]
    assert str(target) not in change.problems[0]


def test_working_tree_diagnostic_reports_only_the_bytes_actually_read(tmp_path):
    target, base = repository(tmp_path, {"file.txt": ""})
    write(target, "file.txt", "x" * 64)

    change = capture_change(target, base, max_bytes=3)

    assert not change.complete
    assert "at least 4 bytes" in change.problems[0]
    assert "per-file limit of 3 bytes" in change.problems[0]


def test_posture_export_preserves_incomplete_scope_without_disclosing_limit_paths(tmp_path):
    target, trusted, base = setup(tmp_path)
    write(target, "src/private-asset.js", "x" * (1024 * 1024 + 1))
    source = inspect(target, trusted, base)

    posture = export_change_posture(source.document)

    assert not posture.document["coverage"]["git_complete"]
    scope = next(
        c
        for c in posture.document["results"]["controls"]
        if c["ref"] == reference("control", "change:scope")
    )
    assert scope["state"] == "unknown"
    assert scope["execution"] == "executed"
    assert "private-asset" not in posture.to_json()
    assert "per-file limit" not in posture.to_json()


def test_incomplete_scope_reason_remains_visible_with_unclassified_changed_paths(tmp_path):
    target, trusted, base = setup(tmp_path)
    for number in range(257):
        write(target, f"unclassified/{number}.txt", "new")

    report = inspect(target, trusted, base)

    scope = next(c for c in report.checks.results if c.spec.id == "change:scope")
    assert scope.outcome.state.value == "unknown"
    assert scope.outcome.execution.value == "executed"
    assert "Changed-path count 257 exceeds limit 256" in scope.outcome.summary
    assert "Changed-path count 257 exceeds limit 256" in render_report(report.checks)
    assert report.exit_code == 1


@pytest.mark.parametrize("as_json", [False, True])
def test_conform_cli_explains_default_bound_and_cannot_pass(tmp_path, monkeypatch, capsys, as_json):
    target, trusted, base = setup(tmp_path)
    write(target, "src/large.js", "x" * (1024 * 1024 + 1))
    request_path = write(tmp_path, "request.json", json.dumps(request()))
    argv = [
        "govkit",
        "conform",
        "--target",
        str(target),
        "--policy-target",
        str(trusted),
        "--base",
        base,
        "--request",
        str(request_path),
    ]
    if as_json:
        argv.append("--json")
    monkeypatch.setattr(sys, "argv", argv)
    before = snapshot(target), snapshot(trusted)

    with pytest.raises(SystemExit) as error:
        main()

    assert error.value.code == 1
    output = capsys.readouterr().out
    if as_json:
        report = parse_change_report(json.loads(output))
        assert not report.change["complete"]
        assert report.exit_code == 1
        scope = next(c for c in report.checks.results if c.spec.id == "change:scope")
        assert scope.outcome.state.value == "unknown"
        assert scope.outcome.execution.value == "executed"
        assert scope.outcome.evidence[0].origin == "unverified-artifact"
        output = scope.outcome.summary
    assert "src/large.js" in output
    assert "per-file limit of 1048576 bytes" in output
    assert (snapshot(target), snapshot(trusted)) == before


@pytest.mark.skipif(sys.platform == "win32", reason="Windows forbids these path characters")
@pytest.mark.parametrize("phase", ["baseline", "working-tree"])
@pytest.mark.parametrize("path_kind", ["ordinary", "escaped-a", "escaped-b"])
def test_long_escaped_limit_paths_preserve_valid_unknown_reports(tmp_path, phase, path_kind):
    target, trusted, base = setup(tmp_path)
    name = (
        "src/asset.js"
        if path_kind == "ordinary"
        # The prefix boundary lands on a supplementary Unicode code point.
        else "/".join(["p" + "\x01" * 126 + "\U0001f680" + "\x01" * 44] * 4 + [path_kind + ".js"])
    )
    write(target, name, "x" * (1024 * 1024 + 1))
    if phase == "baseline":
        git(target, "add", ".")
        git(target, "commit", "-qm", "oversized asset")
        base = git(target, "rev-parse", "HEAD")
    before = snapshot(target), snapshot(trusted)

    report = inspect(target, trusted, base)

    assert not report.change["complete"]
    assert report.exit_code == 1
    message = report.change["problems"][0]
    assert len(message) <= 4096
    assert "per-file limit of 1048576 bytes" in message
    assert ("Baseline" if phase == "baseline" else "Working-tree") in message
    assert "\x01" not in message
    if path_kind == "ordinary":
        assert json.dumps(name) in message and "truncated" not in message
    else:
        assert len(json.dumps(name)) > 4096  # Escaping, not filesystem length, exceeds the bound.
        assert "truncated" in message
        assert f"path sha256:{content_digest(name.encode())}" in message
        prefix, _ = json.JSONDecoder().raw_decode(message[message.index('"') :])
        assert prefix and name.startswith(prefix) and prefix != name
        assert prefix.endswith("\U0001f680")
    scope = next(c for c in report.checks.results if c.spec.id == "change:scope")
    assert scope.outcome.state.value == "unknown"
    assert scope.outcome.execution.value == "executed"
    assert scope.outcome.evidence[0].origin == "unverified-artifact"
    assert message in render_report(report.checks)
    assert parse_change_report(json.loads(report.to_json())).document == report.document
    assert (snapshot(target), snapshot(trusted)) == before
