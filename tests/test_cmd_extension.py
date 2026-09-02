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
    assert {
        "llm-application",
        "otter-skills",
        "skill-oriented-agent-architecture",
        "vision-inference",
    } <= ids, f"bundled packs missing; found {ids}"


def test_extension_list_prints_bundled_packs(capsys):
    cmd_extension_list(argparse.Namespace())
    out = capsys.readouterr().out
    assert "vision-inference" in out
    assert "llm-application" in out
    assert "skill-oriented-agent-architecture" in out


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


class TestExtensionAddSkills:
    """A pack may declare skills[]; `add` installs each into the applied
    agent's skills dir. Third-party content is skip-not-clobber: an existing
    destination survives unless --force, and govkit never installs skills
    into a target with no applied agent."""

    SKILL_BODY = "---\nname: unit-testing\ndescription: d\n---\nbody v1\n"

    @classmethod
    def _bundle_skills_pack(cls, packs_dir, manifest_extra=""):
        pack = packs_dir / "craft-pack"
        skill = pack / "skills" / "unit-testing"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(cls.SKILL_BODY, encoding="utf-8")
        (skill / "references").mkdir()
        (skill / "references" / "notes.md").write_text("ref", encoding="utf-8")
        (pack / "manifest.yaml").write_text(
            "id: craft-pack\nname: Craft Pack\nversion: 0.1.0\n"
            "extension_type: skills\ncontract_sets: []\n"
            "skills:\n"
            "  - path: skills/unit-testing\n"
            "    install_as: craft-unit-testing\n" + manifest_extra,
            encoding="utf-8",
        )
        return pack

    def _target_with_marker(self, tmp_path, agent="claude-code"):
        from cli.marker import write_govkit_marker

        target = tmp_path / "proj"
        target.mkdir()
        write_govkit_marker(target, agent, "4", {"type": "api", "ci": "github"})
        return target

    @pytest.mark.parametrize(
        "agent, skills_dir",
        [
            ("claude-code", ".claude/skills"),
            ("codex", ".agents/skills"),
            ("copilot", ".github/skills"),
        ],
    )
    def test_installs_skills_into_the_applied_agents_dir(
        self, tmp_path, monkeypatch, agent, skills_dir
    ):
        monkeypatch.setattr(paths, "EXTENSION_PACKS_DIR", tmp_path / "packs")
        self._bundle_skills_pack(tmp_path / "packs")
        target = self._target_with_marker(tmp_path, agent)

        cmd_extension_add(_add_args("craft-pack", target))

        installed = target / skills_dir / "craft-unit-testing"
        assert (installed / "SKILL.md").read_text(encoding="utf-8") == self.SKILL_BODY
        assert (installed / "references" / "notes.md").is_file()

    def test_existing_skill_dir_is_skipped_not_clobbered(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(paths, "EXTENSION_PACKS_DIR", tmp_path / "packs")
        self._bundle_skills_pack(tmp_path / "packs")
        target = self._target_with_marker(tmp_path)
        team_copy = target / ".claude" / "skills" / "craft-unit-testing"
        team_copy.mkdir(parents=True)
        (team_copy / "SKILL.md").write_text("team-edited", encoding="utf-8")

        cmd_extension_add(_add_args("craft-pack", target))

        assert (team_copy / "SKILL.md").read_text(encoding="utf-8") == "team-edited"
        assert "skip: .claude/skills/craft-unit-testing/" in capsys.readouterr().out

    def test_force_refreshes_the_skill_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr(paths, "EXTENSION_PACKS_DIR", tmp_path / "packs")
        self._bundle_skills_pack(tmp_path / "packs")
        target = self._target_with_marker(tmp_path)
        team_copy = target / ".claude" / "skills" / "craft-unit-testing"
        team_copy.mkdir(parents=True)
        (team_copy / "SKILL.md").write_text("team-edited", encoding="utf-8")

        cmd_extension_add(_add_args("craft-pack", target, force=True))

        assert (team_copy / "SKILL.md").read_text(encoding="utf-8") == self.SKILL_BODY

    def test_no_marker_warns_and_installs_pack_but_not_skills(
        self, tmp_path, monkeypatch, capsys
    ):
        monkeypatch.setattr(paths, "EXTENSION_PACKS_DIR", tmp_path / "packs")
        self._bundle_skills_pack(tmp_path / "packs")
        target = tmp_path / "proj"
        target.mkdir()

        cmd_extension_add(_add_args("craft-pack", target))

        out = capsys.readouterr().out
        assert (target / "extensions" / "craft-pack" / "manifest.yaml").exists()
        assert not (target / ".claude" / "skills").exists()
        assert "no applied agent" in out

    def test_traversal_path_and_install_as_are_skipped(self, tmp_path, monkeypatch, capsys):
        """Validation only reports; the installer itself must refuse to copy
        from outside the pack or to a name that escapes the skills dir."""
        monkeypatch.setattr(paths, "EXTENSION_PACKS_DIR", tmp_path / "packs")
        self._bundle_skills_pack(
            tmp_path / "packs",
            manifest_extra=(
                "  - path: ../../outside\n    install_as: craft-outside\n"
                "  - path: skills/unit-testing\n    install_as: ../evil\n"
            ),
        )
        outside = tmp_path / "packs" / "outside"
        outside.mkdir()
        (outside / "SKILL.md").write_text("outside", encoding="utf-8")
        target = self._target_with_marker(tmp_path)

        cmd_extension_add(_add_args("craft-pack", target))

        out = capsys.readouterr().out
        assert (target / ".claude" / "skills" / "craft-unit-testing" / "SKILL.md").is_file()
        assert not (target / ".claude" / "skills" / "craft-outside").exists()
        assert not (target / ".claude" / "evil").exists()
        assert out.count("WARN: skipping") == 2

    def test_pack_without_skills_key_installs_nothing_extra(self, tmp_path, monkeypatch):
        # control: existing architecture packs are untouched by the skills path
        cmd_extension_add(_add_args("vision-inference", self._target_with_marker(tmp_path)))
        assert not (tmp_path / "proj" / ".claude" / "skills").exists()

    def test_bundled_otter_skills_pack_installs_all_seven(self, tmp_path):
        """End-to-end with the real vendored pack: every declared skill lands
        under the otter- prefix, license and notice travel with the pack."""
        target = self._target_with_marker(tmp_path)
        cmd_extension_add(_add_args("otter-skills", target))
        assert (target / "extensions" / "otter-skills" / "LICENSE").is_file()
        assert (target / "extensions" / "otter-skills" / "NOTICE").is_file()
        installed = sorted(p.name for p in (target / ".claude" / "skills").iterdir())
        assert len(installed) == 7
        assert all(name.startswith("otter-") for name in installed)
        assert (target / ".claude" / "skills" / "otter-unit-testing" / "SKILL.md").is_file()


class TestExtensionAddFromGit:
    """`add --from-git <url>` fetches a pack from any git repo whose root
    carries a govkit manifest.yaml — govkit's only network touch, on this
    explicit opt-in. The resolved commit is pinned into the installed
    manifest's origin so the project holds the record."""

    MANIFEST = (
        "id: remote-pack\nname: Remote Pack\nversion: 1.0.0\n"
        "extension_type: skills\ncontract_sets: []\n"
        "skills:\n  - path: skills/unit-testing\n    install_as: remote-unit-testing\n"
    )

    @staticmethod
    def _git(repo, *cmd):
        import subprocess

        return subprocess.run(
            ["git", "-c", "user.email=t@example.com", "-c", "user.name=t", *cmd],
            cwd=repo, check=True, capture_output=True, text=True,
        ).stdout.strip()

    @classmethod
    def _make_remote(cls, path, manifest=None):
        """A local git repo standing in for the remote (git clones from paths)."""
        path.mkdir(parents=True)
        if manifest is not None:
            (path / "manifest.yaml").write_text(manifest, encoding="utf-8")
        skill = path / "skills" / "unit-testing"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            "---\nname: unit-testing\ndescription: d\n---\nv1\n", encoding="utf-8"
        )
        cls._git(path, "init", "--quiet")
        cls._git(path, "add", "-A")
        cls._git(path, "commit", "--quiet", "-m", "v1")
        return cls._git(path, "rev-parse", "HEAD")

    @staticmethod
    def _from_git_args(url, target, ref=None, force=False):
        return argparse.Namespace(
            extension_id=None, from_git=str(url), ref=ref, target=str(target), force=force
        )

    def _marked_target(self, tmp_path):
        from cli.marker import write_govkit_marker

        target = tmp_path / "proj"
        target.mkdir()
        write_govkit_marker(target, "claude-code", "4", {"type": "api", "ci": "github"})
        return target

    def test_fetches_installs_and_pins_the_resolved_commit(self, tmp_path):
        import yaml

        sha = self._make_remote(tmp_path / "remote", self.MANIFEST)
        target = self._marked_target(tmp_path)

        cmd_extension_add(self._from_git_args(tmp_path / "remote", target))

        installed = target / "extensions" / "remote-pack"
        assert (installed / "manifest.yaml").is_file()
        assert not (installed / ".git").exists()
        origin = yaml.safe_load((installed / "manifest.yaml").read_text(encoding="utf-8"))[
            "origin"
        ]
        assert origin["upstream_ref"] == sha
        assert origin["upstream_url"] == str(tmp_path / "remote")
        assert (
            target / ".claude" / "skills" / "remote-unit-testing" / "SKILL.md"
        ).is_file()

    def test_ref_pins_an_older_commit(self, tmp_path):
        import yaml

        remote = tmp_path / "remote"
        v1 = self._make_remote(remote, self.MANIFEST)
        (remote / "skills" / "unit-testing" / "SKILL.md").write_text(
            "---\nname: unit-testing\ndescription: d\n---\nv2\n", encoding="utf-8"
        )
        self._git(remote, "add", "-A")
        self._git(remote, "commit", "--quiet", "-m", "v2")
        target = self._marked_target(tmp_path)

        cmd_extension_add(self._from_git_args(remote, target, ref=v1))

        installed = target / "extensions" / "remote-pack"
        origin = yaml.safe_load((installed / "manifest.yaml").read_text(encoding="utf-8"))[
            "origin"
        ]
        assert origin["upstream_ref"] == v1
        assert "v1" in (
            target / ".claude" / "skills" / "remote-unit-testing" / "SKILL.md"
        ).read_text(encoding="utf-8")

    def test_repo_without_manifest_is_refused(self, tmp_path):
        self._make_remote(tmp_path / "remote", manifest=None)
        target = self._marked_target(tmp_path)
        with pytest.raises(SystemExit):
            cmd_extension_add(self._from_git_args(tmp_path / "remote", target))
        assert not (target / "extensions").exists()

    def test_symlinks_in_the_repo_are_not_copied(self, tmp_path):
        """A hostile repo's symlink must not dereference into the pack copy —
        that would commit files from the maintainer's machine."""
        secret = tmp_path / "secret.txt"
        secret.write_text("private", encoding="utf-8")
        remote = tmp_path / "remote"
        remote.mkdir()
        (remote / "manifest.yaml").write_text(self.MANIFEST, encoding="utf-8")
        skill = remote / "skills" / "unit-testing"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            "---\nname: unit-testing\ndescription: d\n---\nv1\n", encoding="utf-8"
        )
        (remote / "link.txt").symlink_to(secret)
        self._git(remote, "init", "--quiet")
        self._git(remote, "add", "-A")
        self._git(remote, "commit", "--quiet", "-m", "v1")
        target = self._marked_target(tmp_path)

        cmd_extension_add(self._from_git_args(remote, target))

        assert not (target / "extensions" / "remote-pack" / "link.txt").exists()

    def test_existing_dest_needs_force_and_force_refreshes(self, tmp_path):
        remote = tmp_path / "remote"
        self._make_remote(remote, self.MANIFEST)
        target = self._marked_target(tmp_path)
        cmd_extension_add(self._from_git_args(remote, target))

        with pytest.raises(SystemExit):
            cmd_extension_add(self._from_git_args(remote, target))
        cmd_extension_add(self._from_git_args(remote, target, force=True))
        assert (target / "extensions" / "remote-pack" / "manifest.yaml").is_file()

    def test_dispatch_requires_exactly_one_source(self, tmp_path):
        from cli.cmd_extension import _cmd_extension_add_dispatch

        both = argparse.Namespace(
            extension_id="vision-inference", from_git="url", ref=None,
            target=str(tmp_path), force=False,
        )
        neither = argparse.Namespace(
            extension_id=None, from_git=None, ref=None, target=str(tmp_path), force=False
        )
        ref_alone = argparse.Namespace(
            extension_id="vision-inference", from_git=None, ref="main",
            target=str(tmp_path), force=False,
        )
        for ns in (both, neither, ref_alone):
            with pytest.raises(SystemExit):
                _cmd_extension_add_dispatch(ns)
