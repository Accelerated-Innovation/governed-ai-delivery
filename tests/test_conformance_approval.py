"""Reproduce PR #184 review findings against real approval adapters."""

import hashlib
import shutil
from pathlib import Path

import pytest

from cli import paths
from cli.check_adapters import offline_instance
from cli.check_models import Execution, State
from cli.conformance import inspect_repository
from cli.validate import CheckStatus
from tests.test_capability_packs import profile
from tests.test_conformance import result
from tests.test_pack_store import snapshot, write_profile


def approval_project(target):
    write_profile(target, profile([], checks=["legacy:approval-policy"]))
    policy = target / "governance/approval_policy.yaml"
    policy.parent.mkdir()
    policy.write_text("version: 1\napprovers:\n  - login: example-user\n    role: approver\n")
    schema = policy.parent / "schemas/approval_policy.schema.json"
    schema.parent.mkdir()
    shutil.copyfile(paths.GOVERNANCE_DIR / "schemas/approval_policy.schema.json", schema)
    return policy


def adr(target, name="0001.md", content="## Status\nProposed\n"):
    path = target / "docs/backend/architecture/ADR" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


@pytest.mark.parametrize("node", ["policy", "governance", "adr", "docs"])
def test_external_approval_sources_cannot_satisfy_a_required_check(tmp_path, node, monkeypatch):
    target, external = tmp_path / "consumer", tmp_path / "external"
    target.mkdir()
    external.mkdir()
    policy = approval_project(target)
    record = adr(target)
    source = {
        "policy": policy,
        "governance": policy.parent,
        "adr": record,
        "docs": target / "docs",
    }[node]
    destination = external / source.name
    shutil.move(source, destination)
    source.symlink_to(destination, target_is_directory=destination.is_dir())
    original_open = Path.open
    external_reads = []

    def observed_open(path, *args, **kwargs):
        if path.resolve().is_relative_to(external.resolve()):
            external_reads.append(path)
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", observed_open)
    report = inspect_repository(target)
    assert result(report, "legacy:approval-policy").outcome.state is not State.PASS
    assert result(report, "govkit:profile").outcome.state is State.PASS
    assert report.exit_code == 1
    assert external_reads == []


def test_offline_instance_refuses_external_instance_before_reading_it(tmp_path):
    target = tmp_path / "consumer"
    target.mkdir()
    schema = target / "schema.json"
    schema.write_text('{"type":"object"}')
    external = tmp_path / "external.json"
    external.write_text("{}")
    instance = target / "instance.json"
    instance.symlink_to(external)
    state, message = offline_instance(target, schema, instance)
    assert state is CheckStatus.WARN
    assert "repository" in message


def test_approval_evidence_names_hashes_and_scopes_the_records_actually_read(tmp_path):
    policy = approval_project(tmp_path)
    record = adr(tmp_path)
    adr(tmp_path, "TEMPLATE.md")
    outside_scope = tmp_path / "docs/ui/architecture/ADR/0002.md"
    outside_scope.parent.mkdir(parents=True)
    outside_scope.write_text("## Status\nAccepted\n")
    policy.write_text(policy.read_text() + "require_approval_for:\n  - docs/backend/\n")
    before = snapshot(tmp_path)
    report = inspect_repository(tmp_path)
    outcome = result(report, "legacy:approval-policy").outcome
    assert outcome.state is State.PASS
    by_source = {e.source: e for e in outcome.evidence}
    source = record.relative_to(tmp_path).as_posix()
    assert set(by_source) == {"governance/approval_policy.yaml", source}
    assert by_source[source].scope == (source,)
    assert by_source[source].digest == hashlib.sha256(record.read_bytes()).hexdigest()
    assert by_source[source].origin == "local-check"
    assert by_source[source].limitations
    assert snapshot(tmp_path) == before
    record.write_text("## Status\nRejected\n")
    changed = result(inspect_repository(tmp_path), "legacy:approval-policy").outcome
    assert (
        next(e.digest for e in changed.evidence if e.source == source) != by_source[source].digest
    )


@pytest.mark.parametrize(
    "node",
    [
        "docs",
        "docs/backend",
        "docs/backend/architecture",
        "docs/backend/architecture/ADR",
        "docs/backend/architecture/ADR/0001.md",
    ],
)
def test_untraversable_adr_paths_are_unknown_instead_of_an_empty_inventory(tmp_path, node):
    approval_project(tmp_path)
    adr(tmp_path)
    path = tmp_path / node
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()
    path.symlink_to(path.name)  # ELOOP is suppressed by Path.exists/is_dir/is_file.
    report = inspect_repository(tmp_path)
    assert result(report, "legacy:approval-policy").outcome.state is State.UNKNOWN
    assert report.exit_code == 1


@pytest.mark.parametrize(
    "node",
    [
        "docs",
        "docs/backend",
        "docs/backend/architecture",
        "docs/backend/architecture/ADR",
        "docs/backend/architecture/ADR/0001.md",
    ],
)
def test_adr_metadata_permission_errors_do_not_become_absence(tmp_path, monkeypatch, node):
    approval_project(tmp_path)
    adr(tmp_path)
    unreadable = tmp_path / node
    original = Path.stat

    def denied(path, *args, **kwargs):
        if path == unreadable:
            raise PermissionError("Unreadable ADR metadata")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", denied)
    report = inspect_repository(tmp_path)
    assert result(report, "legacy:approval-policy").outcome.state is State.UNKNOWN
    assert report.exit_code == 1


def test_unreadable_policy_keeps_its_file_diagnosis_and_unverified_evidence(tmp_path, monkeypatch):
    policy = approval_project(tmp_path)
    original = Path.open

    def denied(path, *args, **kwargs):
        if path == policy:
            raise PermissionError("sensitive-exception-payload")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", denied)
    report = inspect_repository(tmp_path)
    outcome = result(report, "legacy:approval-policy").outcome
    assert outcome.state in (State.FAIL, State.UNKNOWN)
    assert outcome.execution is Execution.EXECUTED
    assert any(
        f.location == "governance/approval_policy.yaml" and "read" in f.message
        for f in outcome.findings
    )
    proof = next(e for e in outcome.evidence if e.source == "governance/approval_policy.yaml")
    assert proof.digest is None and proof.origin == "unverified-artifact"
    assert "sensitive-exception-payload" not in report.to_json()
    assert result(report, "govkit:profile").outcome.state is State.PASS
    assert report.exit_code == 1


def test_symlinks_within_the_repository_keep_lexical_evidence_identity(tmp_path):
    policy = approval_project(tmp_path)
    record = adr(tmp_path)
    for source in (policy, record):
        destination = tmp_path / source.name
        shutil.move(source, destination)
        source.symlink_to(destination)
    outcome = result(inspect_repository(tmp_path), "legacy:approval-policy").outcome
    assert outcome.state is State.PASS
    assert {e.source for e in outcome.evidence} == {
        "governance/approval_policy.yaml",
        "docs/backend/architecture/ADR/0001.md",
    }


def test_one_unreadable_adr_retains_other_records_and_its_own_diagnosis(tmp_path, monkeypatch):
    approval_project(tmp_path)
    readable = adr(tmp_path)
    unreadable = adr(tmp_path, "0001.md-extra.md")
    original = Path.open

    def denied(path, *args, **kwargs):
        if path == unreadable:
            raise PermissionError("sensitive-exception-payload")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", denied)
    report = inspect_repository(tmp_path)
    outcome = result(report, "legacy:approval-policy").outcome
    assert outcome.state is State.UNKNOWN
    by_source = {e.source: e for e in outcome.evidence}
    source = unreadable.relative_to(tmp_path).as_posix()
    assert by_source[readable.relative_to(tmp_path).as_posix()].digest is not None
    assert by_source[source].digest is None
    assert by_source[source].origin == "unverified-artifact"
    assert any(f.location == source and "read" in f.message for f in outcome.findings)
    assert "sensitive-exception-payload" not in report.to_json()
    assert report.exit_code == 1
