"""Internal Git budgets are bounded before I/O; activation remains policy-gated."""

import subprocess
from dataclasses import FrozenInstanceError

import pytest

from cli.change_scope import capture_change
from cli.observation_limits import ObservationLimits
from cli.schema_validation import DocumentError, content_digest, validate_document
from tests.test_change_conformance import git
from tests.test_change_scope_limits import repository
from tests.test_pack_store import snapshot


@pytest.mark.parametrize(
    "arguments",
    [
        {"max_bytes": True},
        {"max_bytes": 1.0},
        {"max_bytes": None},
        {"max_bytes": "1048576"},
        {"max_bytes": 0},
        {"max_bytes": -1},
        {"max_bytes": 8 * 1024 * 1024 + 1},
        {"max_files": False},
        {"max_files": 0},
        {"max_files": 2049},
        {"max_total_bytes": float("inf")},
        {"max_total_bytes": -1},
        {"max_total_bytes": 16 * 1024 * 1024 + 1},
        {"max_changed": True},
        {"max_changed": 0},
        {"max_changed": 257},
    ],
)
def test_invalid_capture_budget_is_rejected_before_git(tmp_path, monkeypatch, arguments):
    def unexpected_git(*args, **kwargs):
        pytest.fail("Invalid budget reached Git instead of failing validation")

    monkeypatch.setattr(subprocess, "run", unexpected_git)

    with pytest.raises(ValueError, match="observation limit"):
        capture_change(tmp_path, "HEAD", **arguments)


@pytest.mark.parametrize("value", [1, 1024 * 1024, 8 * 1024 * 1024])
def test_per_file_budget_preserves_fixed_companion_defaults(value):
    limits = ObservationLimits(max_file_bytes=value)

    assert limits.max_file_bytes == value
    assert limits.max_files == 2048
    assert limits.max_total_bytes == 16 * 1024 * 1024
    assert limits.max_changed_paths == 256


@pytest.mark.parametrize("value", [None, True, 1.0, "1", 0, -1, 8 * 1024 * 1024 + 1])
def test_limit_value_cannot_represent_an_invalid_per_file_budget(value):
    with pytest.raises(ValueError, match="max_file_bytes"):
        ObservationLimits(max_file_bytes=value)


def test_validated_budget_cannot_be_mutated():
    limits = ObservationLimits()

    with pytest.raises(FrozenInstanceError):
        limits.max_file_bytes = 8 * 1024 * 1024


@pytest.mark.parametrize("phase", ["baseline", "working-tree"])
@pytest.mark.parametrize(
    "size,budget,complete",
    [
        (1024 * 1024, None, True),
        (1024 * 1024 + 1, None, False),
        (8 * 1024 * 1024, 8 * 1024 * 1024, True),
        (8 * 1024 * 1024 + 1, 8 * 1024 * 1024, False),
    ],
)
def test_capture_obeys_default_and_candidate_per_file_boundaries(
    tmp_path, phase, size, budget, complete
):
    target, base = repository(tmp_path, {"asset.bin": ""})
    content = b"\x00" * size
    (target / "asset.bin").write_bytes(content)
    if phase == "baseline":
        git(target, "add", ".")
        git(target, "commit", "-qm", "binary baseline")
        base = git(target, "rev-parse", "HEAD")
    limits = ObservationLimits() if budget is None else ObservationLimits(max_file_bytes=budget)
    before = snapshot(target)

    change = capture_change(target, base, limits=limits)

    assert change.complete is complete, change.problems
    assert snapshot(target) == before
    if complete:
        assert change.files["asset.bin"] == content
        if phase == "working-tree":
            assert change.paths == ("asset.bin",)
            assert change.changes[0].after == content_digest(content)
    else:
        assert f"per-file limit of {limits.max_file_bytes} bytes" in change.problems[0]


@pytest.mark.parametrize("phase", ["baseline", "working-tree"])
def test_candidate_budget_does_not_relax_total_content_bound(tmp_path, phase):
    target, base = repository(tmp_path, {"seed": ""})
    for name, size in (("one", 6), ("two", 6), ("three", 5)):
        (target / name).write_bytes(b"\x00" * (size * 1024 * 1024))
    if phase == "baseline":
        git(target, "add", ".")
        git(target, "commit", "-qm", "large aggregate")
        base = git(target, "rev-parse", "HEAD")
    before = snapshot(target)

    change = capture_change(target, base, limits=ObservationLimits(max_file_bytes=8 * 1024 * 1024))

    assert not change.complete
    assert "total-content limit of 16777216 bytes" in change.problems[0]
    assert snapshot(target) == before


@pytest.mark.parametrize(
    "arguments",
    [{"max_bytes": 4}, {"max_files": 1}, {"max_total_bytes": 8}, {"max_changed": 1}],
)
def test_nondefault_legacy_arguments_cannot_override_a_limits_value(
    tmp_path, monkeypatch, arguments
):
    def unexpected_git(*args, **kwargs):
        pytest.fail("Ambiguous budgets reached Git")

    monkeypatch.setattr(subprocess, "run", unexpected_git)

    with pytest.raises(ValueError, match="combine"):
        capture_change(tmp_path, "HEAD", limits=ObservationLimits(), **arguments)


def test_wrong_limits_object_is_rejected_before_git(tmp_path, monkeypatch):
    def unexpected_git(*args, **kwargs):
        pytest.fail("Unvalidated budget reached Git")

    monkeypatch.setattr(subprocess, "run", unexpected_git)

    with pytest.raises(ValueError, match="ObservationLimits"):
        capture_change(tmp_path, "HEAD", limits={"max_file_bytes": 8388608})


def test_accepted_configuration_keeps_companion_bounds_closed():
    policy = {
        "schema_version": 1,
        "impact_rules": [],
        "commands": [],
        "artifacts": [],
        "constraints": [],
        "observation_limits": {"max_file_bytes": 8388608, "max_total_bytes": 33554432},
    }

    with pytest.raises(DocumentError, match="observation_limits"):
        validate_document(policy, "change-policy")
