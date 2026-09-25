"""Regress the Windows install limit at the actual wheel-file boundary."""

import errno
import zipfile
from pathlib import Path

import pytest

from tests.wheel_windows_smoke import check_wheel, verify_path_limit, windows_length


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


def test_crt_missing_file_error_can_represent_the_windows_path_limit(tmp_path, monkeypatch):
    write = Path.write_bytes

    def limited_write(path, content):
        if windows_length(str(path)) == 260:
            error = FileNotFoundError(errno.ENOENT, "No such file or directory", str(path))
            error.winerror = None  # io.open maps the CRT errno, as the hosted job demonstrated.
            raise error
        return write(path, content)

    monkeypatch.setattr(Path, "write_bytes", limited_write)
    verify_path_limit(tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_probe_rejects_an_environment_where_the_over_limit_write_succeeds(tmp_path, monkeypatch):
    write, unlink = Path.write_bytes, Path.unlink

    def unlimited_write(path, content):
        return len(content) if windows_length(str(path)) == 260 else write(path, content)

    def unlimited_unlink(path):
        if windows_length(str(path)) != 260:
            unlink(path)

    monkeypatch.setattr(Path, "write_bytes", unlimited_write)
    monkeypatch.setattr(Path, "unlink", unlimited_unlink)
    with pytest.raises(RuntimeError, match="unexpectedly succeeded"):
        verify_path_limit(tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_probe_does_not_accept_permission_failure_as_a_length_limit(tmp_path, monkeypatch):
    write = Path.write_bytes

    def denied_write(path, content):
        if windows_length(str(path)) == 260:
            error = PermissionError(errno.EACCES, "Permission denied", str(path))
            error.winerror = 5
            raise error
        return write(path, content)

    monkeypatch.setattr(Path, "write_bytes", denied_write)
    with pytest.raises(PermissionError):
        verify_path_limit(tmp_path)


def test_probe_requires_a_working_parent_directory(tmp_path):
    with pytest.raises(FileNotFoundError):
        verify_path_limit(tmp_path / "missing")
