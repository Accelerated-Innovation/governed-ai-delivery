"""Tests for `govkit extension` — listing and adding bundled extension packs.

Increment 1 (this file): packaging path resolution + `extension list`.
Later increments add `extension add` (copy + overwrite guard + compat warning).
"""

import argparse

import pytest

from cli import paths
from cli.cmd_extension import cmd_extension_add, cmd_extension_list


def _add_args(ext_id, target, force=False):
    return argparse.Namespace(extension_id=ext_id, target=str(target), force=force)


def test_extension_packs_dir_exists_and_has_bundled_packs():
    """EXTENSION_PACKS_DIR resolves to the bundled packs (repo: extensions/;
    wheel: cli/extension_packs/). Both reference copies must be discoverable."""
    assert paths.EXTENSION_PACKS_DIR.is_dir(), f"{paths.EXTENSION_PACKS_DIR} should exist"
    ids = {
        p.name
        for p in paths.EXTENSION_PACKS_DIR.iterdir()
        if p.is_dir() and not p.name.startswith(".")
    }
    assert {"agentic-skills", "vision-inference"} <= ids, f"bundled packs missing; found {ids}"


def test_extension_list_prints_bundled_packs(capsys):
    cmd_extension_list(argparse.Namespace())
    out = capsys.readouterr().out
    assert "vision-inference" in out
    assert "agentic-skills" in out


def test_extension_list_shows_supported_levels_and_types(capsys):
    """The list is the source of truth for `govkit extension add` — it must
    surface supported levels/types so a user can judge applicability."""
    cmd_extension_list(argparse.Namespace())
    out = capsys.readouterr().out
    # vision-inference declares api/cli and levels 4,5
    assert "api" in out
    assert "4" in out and "5" in out


class TestExtensionAdd:
    def test_copies_pack_into_target(self, tmp_path):
        cmd_extension_add(_add_args("vision-inference", tmp_path))
        dest = tmp_path / "extensions" / "vision-inference"
        assert (dest / "manifest.yaml").exists()
        assert (
            dest / "docs" / "backend" / "architecture" / "VISION_MODEL_ADAPTER_CONTRACT.md"
        ).exists()
        assert (dest / "schemas" / "prediction-record.schema.json").exists()

    def test_unknown_id_exits(self, tmp_path):
        with pytest.raises(SystemExit):
            cmd_extension_add(_add_args("does-not-exist", tmp_path))

    def test_missing_target_exits(self, tmp_path):
        with pytest.raises(SystemExit):
            cmd_extension_add(_add_args("vision-inference", tmp_path / "nope"))

    def test_existing_without_force_exits(self, tmp_path):
        cmd_extension_add(_add_args("vision-inference", tmp_path))
        with pytest.raises(SystemExit):
            cmd_extension_add(_add_args("vision-inference", tmp_path))

    def test_existing_with_force_overwrites(self, tmp_path):
        cmd_extension_add(_add_args("vision-inference", tmp_path))
        manifest = tmp_path / "extensions" / "vision-inference" / "manifest.yaml"
        manifest.write_text("tampered", encoding="utf-8")
        cmd_extension_add(_add_args("vision-inference", tmp_path, force=True))
        assert manifest.read_text(encoding="utf-8") != "tampered", "force should restore bundle"

    def test_reports_validation_notes_in_bare_project(self, tmp_path, capsys):
        # vision-inference's generative set extends L5 contracts not present in a
        # bare project -> add surfaces them as notes but still succeeds (warn+proceed).
        cmd_extension_add(_add_args("vision-inference", tmp_path))
        out = capsys.readouterr().out
        assert (tmp_path / "extensions" / "vision-inference" / "manifest.yaml").exists()
        assert "Validation notes" in out


class TestExtensionAddCompat:
    """`add` checks the target marker's level/type against the pack's
    supported_levels / supported_project_types and WARNS on mismatch — but
    proceeds (the warn-and-proceed policy). Makes those fields non-inert."""

    @staticmethod
    def _write_marker(target, level="4", type_="api"):
        from cli.marker import write_govkit_marker

        write_govkit_marker(target, "claude-code", level, {"type": type_, "ci": "github"})

    def test_warns_on_level_mismatch_but_proceeds(self, tmp_path, capsys):
        self._write_marker(tmp_path, level="3", type_="api")  # vision-inference: levels 4,5
        cmd_extension_add(_add_args("vision-inference", tmp_path))
        out = capsys.readouterr().out
        assert (tmp_path / "extensions" / "vision-inference" / "manifest.yaml").exists()
        assert "supported_levels" in out

    def test_warns_on_type_mismatch_but_proceeds(self, tmp_path, capsys):
        self._write_marker(tmp_path, level="4", type_="ui-react")  # vision-inference: api,cli
        cmd_extension_add(_add_args("vision-inference", tmp_path))
        out = capsys.readouterr().out
        assert (tmp_path / "extensions" / "vision-inference" / "manifest.yaml").exists()
        assert "supported_project_types" in out

    def test_no_compat_warning_when_compatible(self, tmp_path, capsys):
        self._write_marker(tmp_path, level="4", type_="api")
        cmd_extension_add(_add_args("vision-inference", tmp_path))
        out = capsys.readouterr().out
        assert "supported_levels" not in out
        assert "supported_project_types" not in out


class TestExtensionAddSafety:
    """`add` must not let a malicious manifest id traverse outside
    <target>/extensions/ before the rmtree/copytree filesystem ops."""

    @staticmethod
    def _bundle_pack_with_id(packs_dir, folder, manifest_id):
        pack = packs_dir / folder
        pack.mkdir(parents=True)
        (pack / "manifest.yaml").write_text(
            f"id: {manifest_id}\n"
            "name: Crafted\nversion: 0.1.0\nextension_type: architecture\n"
            "contract_sets: []\n",
            encoding="utf-8",
        )
        return pack

    def test_rejects_unsafe_manifest_id_before_touching_fs(self, tmp_path, monkeypatch):
        packs = tmp_path / "packs"
        self._bundle_pack_with_id(packs, "evil", "../../escape")
        monkeypatch.setattr(paths, "EXTENSION_PACKS_DIR", packs)
        target = tmp_path / "proj"
        target.mkdir()

        with pytest.raises(SystemExit):
            cmd_extension_add(_add_args("../../escape", target))

        # nothing was created/deleted outside target/extensions/
        assert not (tmp_path / "escape").exists()
        assert not (target.parent / "escape").exists()

    def test_safe_id_from_fake_bundle_still_installs(self, tmp_path, monkeypatch):
        # control: a well-formed id from a fake bundle installs normally
        packs = tmp_path / "packs"
        self._bundle_pack_with_id(packs, "okay-ext", "okay-ext")
        monkeypatch.setattr(paths, "EXTENSION_PACKS_DIR", packs)
        target = tmp_path / "proj"
        target.mkdir()

        cmd_extension_add(_add_args("okay-ext", target))
        assert (target / "extensions" / "okay-ext" / "manifest.yaml").exists()
