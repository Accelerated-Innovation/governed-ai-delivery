"""Tests for cli/extensions.py — Increment 1 (discovery only).

Validation, --strict, and overlap detection are added in later increments.
"""

import textwrap
from pathlib import Path

import pytest

from cli.extensions import (
    EXTENSIONS_DIR,
    MANIFEST_FILE,
    Extension,
    discover_extensions,
    load_manifest,
    report_extensions,
    validate_extension,
)
from cli.validate import run_validation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_extension(target: Path, ext_id: str, manifest_body: str | None) -> Path:
    """Create an extension folder under <target>/extensions/<ext_id>/.
    If manifest_body is None, the manifest.yaml is omitted."""
    ext_dir = target / EXTENSIONS_DIR / ext_id
    ext_dir.mkdir(parents=True, exist_ok=True)
    if manifest_body is not None:
        (ext_dir / MANIFEST_FILE).write_text(
            textwrap.dedent(manifest_body), encoding="utf-8"
        )
    return ext_dir


VALID_MANIFEST = """\
id: sample-ext
name: Sample Extension
version: 1.2.3
description: A test extension
extension_type: architecture
contract_sets:
  - id: sample
    description: example
    paths:
      - docs/SAMPLE.md
"""


def _write_valid_extension(target: Path, ext_id: str = "sample-ext") -> Path:
    """Write a fully-valid extension (manifest + the contract path it declares)."""
    body = VALID_MANIFEST.replace("sample-ext", ext_id)
    ext_dir = _write_extension(target, ext_id, body)
    (ext_dir / "docs").mkdir(exist_ok=True)
    (ext_dir / "docs" / "SAMPLE.md").write_text("# sample", encoding="utf-8")
    return ext_dir


# ---------------------------------------------------------------------------
# discover_extensions
# ---------------------------------------------------------------------------


class TestDiscoverExtensions:
    def test_no_extensions_folder_returns_empty(self, tmp_path):
        assert discover_extensions(tmp_path) == []

    def test_empty_extensions_folder_returns_empty(self, tmp_path):
        (tmp_path / EXTENSIONS_DIR).mkdir()
        assert discover_extensions(tmp_path) == []

    def test_valid_manifest_discovered(self, tmp_path):
        _write_extension(tmp_path, "sample-ext", VALID_MANIFEST)
        results = discover_extensions(tmp_path)
        assert len(results) == 1
        ext = results[0]
        assert ext.id == "sample-ext"
        assert ext.name == "Sample Extension"
        assert ext.version == "1.2.3"
        assert ext.errors == []
        assert ext.root.name == "sample-ext"

    def test_multiple_extensions_discovered(self, tmp_path):
        _write_extension(tmp_path, "alpha", VALID_MANIFEST.replace("sample-ext", "alpha"))
        _write_extension(tmp_path, "beta", VALID_MANIFEST.replace("sample-ext", "beta"))
        results = discover_extensions(tmp_path)
        assert [e.id for e in results] == ["alpha", "beta"]   # sorted by folder name
        assert all(e.errors == [] for e in results)

    def test_extension_folder_without_manifest_yields_error_entry(self, tmp_path):
        _write_extension(tmp_path, "no-manifest", None)
        results = discover_extensions(tmp_path)
        assert len(results) == 1
        assert results[0].id == "no-manifest"
        assert results[0].errors == [f"missing {MANIFEST_FILE}"]
        assert results[0].manifest == {}

    def test_invalid_yaml_yields_error_entry(self, tmp_path):
        ext_dir = tmp_path / EXTENSIONS_DIR / "bad-yaml"
        ext_dir.mkdir(parents=True)
        (ext_dir / MANIFEST_FILE).write_text("id: bad\n: : : not valid yaml", encoding="utf-8")
        results = discover_extensions(tmp_path)
        assert len(results) == 1
        assert results[0].id == "bad-yaml"
        assert len(results[0].errors) == 1
        assert "invalid YAML" in results[0].errors[0]

    def test_dotfolders_skipped(self, tmp_path):
        _write_extension(tmp_path, ".hidden", VALID_MANIFEST)
        _write_extension(tmp_path, "visible", VALID_MANIFEST.replace("sample-ext", "visible"))
        results = discover_extensions(tmp_path)
        assert [e.id for e in results] == ["visible"]

    def test_files_at_extensions_root_skipped(self, tmp_path):
        ext_root = tmp_path / EXTENSIONS_DIR
        ext_root.mkdir()
        (ext_root / "README.md").write_text("stray file", encoding="utf-8")
        assert discover_extensions(tmp_path) == []

    def test_id_falls_back_to_folder_name_when_missing(self, tmp_path):
        body = "name: No Id\nversion: 0.0.1\nextension_type: architecture\ncontract_sets: []\n"
        _write_extension(tmp_path, "folder-id", body)
        results = discover_extensions(tmp_path)
        assert results[0].id == "folder-id"


# ---------------------------------------------------------------------------
# load_manifest
# ---------------------------------------------------------------------------


class TestLoadManifest:
    def test_loads_valid_yaml(self, tmp_path):
        p = tmp_path / "m.yaml"
        p.write_text(VALID_MANIFEST, encoding="utf-8")
        data, err = load_manifest(p)
        assert err is None
        assert data["id"] == "sample-ext"

    def test_invalid_yaml_returns_error(self, tmp_path):
        p = tmp_path / "m.yaml"
        p.write_text(": : : nope", encoding="utf-8")
        data, err = load_manifest(p)
        assert data is None
        assert "invalid YAML" in err

    def test_empty_manifest_returns_error(self, tmp_path):
        p = tmp_path / "m.yaml"
        p.write_text("", encoding="utf-8")
        data, err = load_manifest(p)
        assert data is None
        assert err == "manifest is empty"

    def test_non_mapping_returns_error(self, tmp_path):
        p = tmp_path / "m.yaml"
        p.write_text("- just\n- a\n- list\n", encoding="utf-8")
        data, err = load_manifest(p)
        assert data is None
        assert "mapping" in err

    def test_missing_file_returns_error(self, tmp_path):
        data, err = load_manifest(tmp_path / "nope.yaml")
        assert data is None
        assert "could not read" in err


# ---------------------------------------------------------------------------
# report_extensions
# ---------------------------------------------------------------------------


class TestReportExtensions:
    def test_silent_when_no_extensions(self, tmp_path, capsys):
        count = report_extensions(tmp_path)
        captured = capsys.readouterr()
        assert count == 0
        assert captured.out == ""

    def test_prints_id_name_version_for_valid_extension(self, tmp_path, capsys):
        _write_extension(tmp_path, "sample-ext", VALID_MANIFEST)
        count = report_extensions(tmp_path)
        captured = capsys.readouterr()
        assert count == 1
        assert "Extensions detected:" in captured.out
        assert "sample-ext v1.2.3" in captured.out
        assert "Sample Extension" in captured.out

    def test_prints_warning_for_broken_extension(self, tmp_path, capsys):
        _write_extension(tmp_path, "no-manifest", None)
        count = report_extensions(tmp_path)
        captured = capsys.readouterr()
        assert count == 1
        assert "no-manifest" in captured.out
        assert "WARN" in captured.out

    def test_prints_multiple_extensions(self, tmp_path, capsys):
        _write_extension(tmp_path, "alpha", VALID_MANIFEST.replace("sample-ext", "alpha"))
        _write_extension(tmp_path, "beta", VALID_MANIFEST.replace("sample-ext", "beta"))
        count = report_extensions(tmp_path)
        captured = capsys.readouterr()
        assert count == 2
        assert "alpha" in captured.out
        assert "beta" in captured.out


# ---------------------------------------------------------------------------
# validate_extension
# ---------------------------------------------------------------------------


class TestValidateExtension:
    def test_valid_manifest_no_issues(self, tmp_path):
        _write_valid_extension(tmp_path)
        ext = discover_extensions(tmp_path)[0]
        assert validate_extension(ext, tmp_path) == []

    def test_discovery_errors_passed_through(self, tmp_path):
        _write_extension(tmp_path, "no-manifest", None)
        ext = discover_extensions(tmp_path)[0]
        issues = validate_extension(ext, tmp_path)
        assert issues == [f"missing {MANIFEST_FILE}"]

    def test_missing_required_field_reported(self, tmp_path):
        body = "id: sample-ext\nname: Sample\nversion: 0.1.0\nextension_type: architecture\n"
        _write_extension(tmp_path, "sample-ext", body)
        ext = discover_extensions(tmp_path)[0]
        issues = validate_extension(ext, tmp_path)
        assert any("contract_sets" in i for i in issues)

    def test_invalid_id_format_reported(self, tmp_path):
        body = VALID_MANIFEST.replace("id: sample-ext", "id: Sample_Ext")
        ext_dir = tmp_path / EXTENSIONS_DIR / "Sample_Ext"
        ext_dir.mkdir(parents=True)
        (ext_dir / MANIFEST_FILE).write_text(body, encoding="utf-8")
        (ext_dir / "docs").mkdir()
        (ext_dir / "docs" / "SAMPLE.md").write_text("x", encoding="utf-8")
        ext = discover_extensions(tmp_path)[0]
        issues = validate_extension(ext, tmp_path)
        assert any("invalid id format" in i for i in issues)

    def test_id_folder_mismatch_reported(self, tmp_path):
        body = VALID_MANIFEST  # declares id: sample-ext
        _write_extension(tmp_path, "different-folder", body)
        ext = discover_extensions(tmp_path)[0]
        issues = validate_extension(ext, tmp_path)
        assert any("does not match folder name" in i for i in issues)

    def test_missing_contract_path_reported(self, tmp_path):
        _write_extension(tmp_path, "sample-ext", VALID_MANIFEST)
        # NOTE: do NOT create docs/SAMPLE.md
        ext = discover_extensions(tmp_path)[0]
        issues = validate_extension(ext, tmp_path)
        assert any("docs/SAMPLE.md" in i and "does not exist" in i for i in issues)

    def test_missing_template_path_reported(self, tmp_path):
        body = VALID_MANIFEST + textwrap.dedent("""\
            templates:
              - id: tpl
                path: governance/missing.md
            """)
        _write_extension(tmp_path, "sample-ext", body)
        ext_dir = tmp_path / EXTENSIONS_DIR / "sample-ext"
        (ext_dir / "docs").mkdir()
        (ext_dir / "docs" / "SAMPLE.md").write_text("x", encoding="utf-8")
        ext = discover_extensions(tmp_path)[0]
        issues = validate_extension(ext, tmp_path)
        assert any("governance/missing.md" in i for i in issues)

    def test_malformed_contract_sets_entry_reported(self, tmp_path):
        body = """\
id: sample-ext
name: Sample
version: 0.1.0
extension_type: architecture
contract_sets:
  - not a mapping
"""
        _write_extension(tmp_path, "sample-ext", body)
        ext = discover_extensions(tmp_path)[0]
        issues = validate_extension(ext, tmp_path)
        assert any("contract_sets[0] must be a mapping" in i for i in issues)


# ---------------------------------------------------------------------------
# run_validation — extension-aware paths
# ---------------------------------------------------------------------------


class TestRunValidationExtensions:
    def test_no_extensions_l3_unchanged(self, tmp_path, capsys):
        # L3 with no extensions: existing behavior — exit 0, no extensions section
        exit_code = run_validation(tmp_path, level="3")
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Level 3" in out
        assert "govkit validate — extensions" not in out

    def test_no_extensions_l4_unchanged(self, tmp_path, capsys):
        # L4 with no features dir + no extensions: exit 1 (no features/) — existing behavior
        exit_code = run_validation(tmp_path, level="4")
        out = capsys.readouterr().out
        assert exit_code == 1
        assert "no features/ directory" in out
        assert "govkit validate — extensions" not in out

    def test_valid_extension_passes_default_mode(self, tmp_path, capsys):
        _write_valid_extension(tmp_path)
        exit_code = run_validation(tmp_path, level="3")
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "govkit validate — extensions" in out
        assert "sample-ext v1.2.3" in out

    def test_valid_extension_passes_strict_mode(self, tmp_path, capsys):
        _write_valid_extension(tmp_path)
        exit_code = run_validation(tmp_path, level="3", strict=True)
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "sample-ext v1.2.3" in out

    def test_invalid_manifest_warns_default_exit_zero(self, tmp_path, capsys):
        # Missing contract path → issue surfaced, but exit stays 0 in default mode
        _write_extension(tmp_path, "sample-ext", VALID_MANIFEST)
        exit_code = run_validation(tmp_path, level="3")
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "WARN" in out
        assert "sample-ext" in out

    def test_invalid_manifest_fails_strict_exit_one(self, tmp_path, capsys):
        _write_extension(tmp_path, "sample-ext", VALID_MANIFEST)
        exit_code = run_validation(tmp_path, level="3", strict=True)
        out = capsys.readouterr().out
        assert exit_code == 1
        assert "FAIL" in out
        assert "sample-ext" in out

    def test_extension_failure_does_not_mask_feature_pass(self, tmp_path, capsys, monkeypatch):
        # Extension warning at L3 still exits 0 even when no feature checks run
        _write_extension(tmp_path, "sample-ext", VALID_MANIFEST)
        exit_code = run_validation(tmp_path, level="3")
        assert exit_code == 0
        capsys.readouterr()  # drain
