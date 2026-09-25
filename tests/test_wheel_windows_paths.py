"""Regress the Windows install limit at the actual wheel-file boundary."""

import zipfile
from pathlib import Path

import pytest

from tests.wheel_windows_smoke import check_wheel


def make_wheel(tmp_path: Path, name: str) -> Path:
    wheel = tmp_path / "govkit-test.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(name, b"payload")
    return wheel


def test_original_architecture_contract_path_exceeds_windows_budget(tmp_path):
    member = (
        "cli/extension_packs/skill-oriented-agent-architecture/docs/backend/architecture/"
        "SKILL_LIFECYCLE_AND_INTEROPERABILITY_CONTRACT.md"
    )
    with pytest.raises(ValueError, match="128: cli/extension_packs/"):
        check_wheel(make_wheel(tmp_path, member))


def test_last_path_that_leaves_room_for_windows_terminator_passes(tmp_path):
    check_wheel(make_wheel(tmp_path, "x" * 116))


def test_path_consuming_windows_terminator_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="116-character Windows member budget"):
        check_wheel(make_wheel(tmp_path, "x" * 117))


def test_unicode_paths_count_utf16_units_not_python_characters(tmp_path):
    with pytest.raises(ValueError, match="118:"):
        check_wheel(make_wheel(tmp_path, "x" * 114 + "\U0001f600\U0001f600"))


def test_pip_generated_bytecode_must_fit_too(tmp_path):
    with pytest.raises(ValueError, match="__pycache__/"):
        check_wheel(make_wheel(tmp_path, "cli/" + "x" * 100 + ".py"))


def test_empty_wheel_cannot_claim_a_passing_budget(tmp_path):
    wheel = tmp_path / "empty.whl"
    with zipfile.ZipFile(wheel, "w"):
        pass
    with pytest.raises(ValueError, match="no files"):
        check_wheel(wheel)
