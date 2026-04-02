"""Tests for cli/govkit.py — copy_entry, load_manifest, resolve_options, resolve_variant_files."""

import argparse
import json
import textwrap
from pathlib import Path

import pytest

from cli.govkit import copy_entry, load_manifest, resolve_options, resolve_variant_files


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_tree(tmp_path):
    """Create a minimal directory tree for copy/manifest tests."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "file_a.txt").write_text("aaa", encoding="utf-8")
    sub = src / "sub"
    sub.mkdir()
    (sub / "file_b.txt").write_text("bbb", encoding="utf-8")
    return tmp_path


@pytest.fixture()
def agent_dir(tmp_path):
    """Create a fake agents directory with a valid manifest."""
    agents = tmp_path / "agents" / "test-agent"
    agents.mkdir(parents=True)
    manifest = {
        "agent": "test-agent",
        "description": "A test agent",
        "options": {
            "ci": {
                "prompt": "CI platform?",
                "choices": ["github", "azure"],
                "default": "github",
            }
        },
        "variants": {
            "ci": {
                "github": {"files": [{"src": "gh.yml", "dest": ".github/gh.yml"}]},
                "azure": {"files": [{"src": "az.yml", "dest": ".azure/az.yml"}]},
            }
        },
        "base_files": [{"src": "base.md", "dest": "base.md"}],
    }
    (agents / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return tmp_path


# ---------------------------------------------------------------------------
# copy_entry
# ---------------------------------------------------------------------------


class TestCopyEntry:
    def test_copies_single_file(self, tmp_tree):
        src = tmp_tree / "src" / "file_a.txt"
        dest = tmp_tree / "out" / "file_a.txt"
        copy_entry(src, dest)
        assert dest.read_text(encoding="utf-8") == "aaa"

    def test_copies_directory_recursively(self, tmp_tree):
        src = tmp_tree / "src"
        dest = tmp_tree / "out"
        copy_entry(src, dest)
        assert (dest / "file_a.txt").read_text(encoding="utf-8") == "aaa"
        assert (dest / "sub" / "file_b.txt").read_text(encoding="utf-8") == "bbb"

    def test_skip_existing_preserves_file(self, tmp_tree):
        src = tmp_tree / "src" / "file_a.txt"
        dest = tmp_tree / "out" / "file_a.txt"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("original", encoding="utf-8")
        copy_entry(src, dest, skip_existing=True)
        assert dest.read_text(encoding="utf-8") == "original"

    def test_skip_existing_false_overwrites(self, tmp_tree):
        src = tmp_tree / "src" / "file_a.txt"
        dest = tmp_tree / "out" / "file_a.txt"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("original", encoding="utf-8")
        copy_entry(src, dest, skip_existing=False)
        assert dest.read_text(encoding="utf-8") == "aaa"

    def test_missing_source_exits(self, tmp_path):
        with pytest.raises(SystemExit):
            copy_entry(tmp_path / "nonexistent", tmp_path / "dest")


# ---------------------------------------------------------------------------
# load_manifest
# ---------------------------------------------------------------------------


class TestLoadManifest:
    def test_loads_valid_manifest(self, agent_dir, monkeypatch):
        import cli.govkit as mod

        monkeypatch.setattr(mod, "AGENTS_DIR", agent_dir / "agents")
        m = load_manifest("test-agent")
        assert m["agent"] == "test-agent"
        assert "variants" in m

    def test_missing_agent_exits(self, tmp_path, monkeypatch):
        import cli.govkit as mod

        monkeypatch.setattr(mod, "AGENTS_DIR", tmp_path)
        with pytest.raises(SystemExit):
            load_manifest("no-such-agent")

    def test_invalid_json_exits(self, tmp_path, monkeypatch):
        import cli.govkit as mod

        agent = tmp_path / "bad-agent"
        agent.mkdir()
        (agent / "manifest.json").write_text("not json!", encoding="utf-8")
        monkeypatch.setattr(mod, "AGENTS_DIR", tmp_path)
        with pytest.raises(SystemExit):
            load_manifest("bad-agent")

    def test_missing_required_keys_exits(self, tmp_path, monkeypatch):
        import cli.govkit as mod

        agent = tmp_path / "incomplete"
        agent.mkdir()
        (agent / "manifest.json").write_text('{"agent": "x"}', encoding="utf-8")
        monkeypatch.setattr(mod, "AGENTS_DIR", tmp_path)
        with pytest.raises(SystemExit):
            load_manifest("incomplete")


# ---------------------------------------------------------------------------
# resolve_options
# ---------------------------------------------------------------------------


class TestResolveOptions:
    def test_cli_flags_override_prompt(self):
        manifest = {
            "options": {
                "ci": {
                    "prompt": "CI platform?",
                    "choices": ["github", "azure"],
                    "default": "github",
                }
            }
        }
        args = argparse.Namespace(ci="azure")
        result = resolve_options(manifest, args)
        assert result == {"ci": "azure"}

    def test_interactive_default(self, monkeypatch):
        manifest = {
            "options": {
                "ci": {
                    "prompt": "CI platform?",
                    "choices": ["github", "azure"],
                    "default": "github",
                }
            }
        }
        args = argparse.Namespace(ci=None)
        monkeypatch.setattr("builtins.input", lambda _: "")
        result = resolve_options(manifest, args)
        assert result == {"ci": "github"}

    def test_interactive_explicit_choice(self, monkeypatch):
        manifest = {
            "options": {
                "ci": {
                    "prompt": "CI platform?",
                    "choices": ["github", "azure"],
                    "default": "github",
                }
            }
        }
        args = argparse.Namespace(ci=None)
        monkeypatch.setattr("builtins.input", lambda _: "azure")
        result = resolve_options(manifest, args)
        assert result == {"ci": "azure"}

    def test_invalid_choice_exits(self, monkeypatch):
        manifest = {
            "options": {
                "ci": {
                    "prompt": "CI platform?",
                    "choices": ["github", "azure"],
                    "default": "github",
                }
            }
        }
        args = argparse.Namespace(ci=None)
        monkeypatch.setattr("builtins.input", lambda _: "jenkins")
        with pytest.raises(SystemExit):
            resolve_options(manifest, args)

    def test_empty_options(self):
        manifest = {"options": {}}
        args = argparse.Namespace()
        assert resolve_options(manifest, args) == {}


# ---------------------------------------------------------------------------
# resolve_variant_files
# ---------------------------------------------------------------------------


class TestResolveVariantFiles:
    def test_base_plus_variant_files(self):
        manifest = {
            "base_files": [{"src": "base.md", "dest": "base.md"}],
            "variants": {
                "ci": {
                    "github": {
                        "files": [{"src": "gh.yml", "dest": ".github/gh.yml"}],
                        "shared": ["governance/schemas/"],
                    }
                }
            },
        }
        files, shared = resolve_variant_files(manifest, {"ci": "github"})
        assert len(files) == 2
        assert files[0]["src"] == "base.md"
        assert files[1]["src"] == "gh.yml"
        assert shared == ["governance/schemas/"]

    def test_deduplication(self):
        manifest = {
            "base_files": [{"src": "a.md", "dest": "a.md"}],
            "variants": {
                "ci": {
                    "github": {
                        "files": [{"src": "a.md", "dest": "a.md"}],
                        "shared": ["gov/"],
                    }
                },
                "type": {
                    "api": {
                        "files": [{"src": "a.md", "dest": "a.md"}],
                        "shared": ["gov/"],
                    }
                },
            },
        }
        files, shared = resolve_variant_files(manifest, {"ci": "github", "type": "api"})
        assert len(files) == 1  # deduplicated
        assert len(shared) == 1  # deduplicated

    def test_no_base_files(self):
        manifest = {
            "variants": {
                "ci": {
                    "azure": {
                        "files": [{"src": "az.yml", "dest": "az.yml"}],
                    }
                }
            }
        }
        files, shared = resolve_variant_files(manifest, {"ci": "azure"})
        assert len(files) == 1
        assert shared == []

    def test_unknown_variant_value(self):
        manifest = {
            "base_files": [],
            "variants": {"ci": {"github": {"files": [{"src": "g.yml", "dest": "g.yml"}]}}},
        }
        files, shared = resolve_variant_files(manifest, {"ci": "nonexistent"})
        assert files == []
        assert shared == []
