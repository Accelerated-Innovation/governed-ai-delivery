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

    def test_level_3_override(self):
        """When level=3, level_3 sub-key files/shared replace the top-level ones."""
        manifest = {
            "variants": {
                "type": {
                    "api": {
                        "files": [{"src": "l4-api.md", "dest": "CLAUDE.md"}],
                        "shared": ["docs/backend/"],
                        "level_3": {
                            "files": [{"src": "l3-api.md", "dest": "CLAUDE.md"}],
                            "shared": ["docs/backend/architecture/DESIGN_PRINCIPLES.md"],
                        },
                    }
                }
            }
        }
        files, shared = resolve_variant_files(manifest, {"type": "api", "level": "3"})
        assert len(files) == 1
        assert files[0]["src"] == "l3-api.md"
        assert shared == ["docs/backend/architecture/DESIGN_PRINCIPLES.md"]

    def test_level_4_uses_default(self):
        """When level=4, top-level files/shared are used (no override)."""
        manifest = {
            "variants": {
                "type": {
                    "api": {
                        "files": [{"src": "l4-api.md", "dest": "CLAUDE.md"}],
                        "shared": ["docs/backend/"],
                        "level_3": {
                            "files": [{"src": "l3-api.md", "dest": "CLAUDE.md"}],
                            "shared": ["docs/backend/architecture/DESIGN_PRINCIPLES.md"],
                        },
                    }
                }
            }
        }
        files, shared = resolve_variant_files(manifest, {"type": "api", "level": "4"})
        assert len(files) == 1
        assert files[0]["src"] == "l4-api.md"
        assert shared == ["docs/backend/"]

    def test_level_default_is_4(self):
        """When level is not specified, behaves as level 4."""
        manifest = {
            "variants": {
                "type": {
                    "api": {
                        "files": [{"src": "l4-api.md", "dest": "CLAUDE.md"}],
                        "shared": ["docs/backend/"],
                        "level_3": {
                            "files": [{"src": "l3-api.md", "dest": "CLAUDE.md"}],
                            "shared": ["docs/backend/architecture/DESIGN_PRINCIPLES.md"],
                        },
                    }
                }
            }
        }
        files, shared = resolve_variant_files(manifest, {"type": "api"})
        assert files[0]["src"] == "l4-api.md"

    def test_level_3_missing_override_falls_through(self):
        """When level=3 but variant has no level_3 key, use top-level files."""
        manifest = {
            "variants": {
                "ci": {
                    "github": {
                        "files": [{"src": "gh.yml", "dest": ".github/gh.yml"}],
                        "shared": ["ci/github/"],
                    }
                }
            }
        }
        files, shared = resolve_variant_files(manifest, {"ci": "github", "level": "3"})
        assert len(files) == 1
        assert files[0]["src"] == "gh.yml"
        assert shared == ["ci/github/"]

    def test_level_3_multiple_dimensions(self):
        """Level 3 override applies across multiple dimensions."""
        manifest = {
            "variants": {
                "type": {
                    "api": {
                        "files": [{"src": "l4.md", "dest": "CLAUDE.md"}],
                        "shared": ["docs/"],
                        "level_3": {
                            "files": [{"src": "l3.md", "dest": "CLAUDE.md"}],
                            "shared": ["docs/DESIGN_PRINCIPLES.md"],
                        },
                    }
                },
                "ci": {
                    "github": {
                        "files": [],
                        "shared": ["ci/github/"],
                        "level_3": {
                            "files": [],
                            "shared": ["ci/github/l3-quality-gate.yml"],
                        },
                    }
                },
            }
        }
        files, shared = resolve_variant_files(
            manifest, {"type": "api", "ci": "github", "level": "3"}
        )
        assert len(files) == 1
        assert files[0]["src"] == "l3.md"
        assert "docs/DESIGN_PRINCIPLES.md" in shared
        assert "ci/github/l3-quality-gate.yml" in shared


# ---------------------------------------------------------------------------
# .govkit marker
# ---------------------------------------------------------------------------


class TestGovkitMarker:
    def test_write_and_read_marker(self, tmp_path):
        from cli.govkit import write_govkit_marker, read_govkit_level

        write_govkit_marker(tmp_path, "claude-code", "3", {"type": "api", "level": "3"})
        assert (tmp_path / ".govkit").exists()
        level = read_govkit_level(tmp_path)
        assert level == "3"

    def test_read_missing_marker(self, tmp_path):
        from cli.govkit import read_govkit_level

        assert read_govkit_level(tmp_path) is None

    def test_read_corrupt_marker(self, tmp_path):
        from cli.govkit import read_govkit_level

        (tmp_path / ".govkit").write_text("not json", encoding="utf-8")
        assert read_govkit_level(tmp_path) is None

    def test_marker_excludes_level_from_options(self, tmp_path):
        import json
        from cli.govkit import write_govkit_marker

        write_govkit_marker(tmp_path, "claude-code", "3", {"type": "api", "level": "3", "ci": "github"})
        data = json.loads((tmp_path / ".govkit").read_text(encoding="utf-8"))
        assert "level" not in data["options"]
        assert data["options"]["type"] == "api"
        assert data["level"] == "3"

    def test_write_level_5_marker(self, tmp_path):
        import json
        from cli.govkit import write_govkit_marker, read_govkit_level

        write_govkit_marker(tmp_path, "claude-code", "5", {"type": "api", "level": "5"})
        data = json.loads((tmp_path / ".govkit").read_text(encoding="utf-8"))
        assert data["level"] == "5"
        assert data["version"] == "0.4.0"
        assert read_govkit_level(tmp_path) == "5"


# ---------------------------------------------------------------------------
# Level 5 variant resolution
# ---------------------------------------------------------------------------


class TestLevel5VariantResolution:
    def test_level_5_override(self):
        """When level=5, level_5 sub-key files/shared replace the top-level ones."""
        manifest = {
            "variants": {
                "type": {
                    "api": {
                        "files": [{"src": "l4-api.md", "dest": "CLAUDE.md"}],
                        "shared": ["docs/backend/"],
                        "level_5": {
                            "files": [
                                {"src": "l5-api.md", "dest": "CLAUDE.md"},
                                {"src": "llm-gateway.md", "dest": ".claude/rules/llm-gateway.md"},
                            ],
                            "shared": ["docs/backend/", "features/starter_backend_l5/"],
                        },
                    }
                }
            }
        }
        files, shared = resolve_variant_files(manifest, {"type": "api", "level": "5"})
        assert len(files) == 2
        assert files[0]["src"] == "l5-api.md"
        assert files[1]["src"] == "llm-gateway.md"
        assert "features/starter_backend_l5/" in shared

    def test_level_5_does_not_affect_level_4(self):
        """Level 4 still uses top-level files even when level_5 exists."""
        manifest = {
            "variants": {
                "type": {
                    "api": {
                        "files": [{"src": "l4-api.md", "dest": "CLAUDE.md"}],
                        "shared": ["docs/backend/"],
                        "level_5": {
                            "files": [{"src": "l5-api.md", "dest": "CLAUDE.md"}],
                            "shared": ["docs/backend/", "features/starter_backend_l5/"],
                        },
                    }
                }
            }
        }
        files, shared = resolve_variant_files(manifest, {"type": "api", "level": "4"})
        assert files[0]["src"] == "l4-api.md"
        assert "features/starter_backend_l5/" not in shared

    def test_level_5_multiple_dimensions(self):
        """Level 5 override applies across type + ci dimensions."""
        manifest = {
            "variants": {
                "type": {
                    "api": {
                        "files": [{"src": "l4.md", "dest": "CLAUDE.md"}],
                        "shared": ["docs/"],
                        "level_5": {
                            "files": [{"src": "l5.md", "dest": "CLAUDE.md"}],
                            "shared": ["docs/", "features/starter_backend_l5/"],
                        },
                    }
                },
                "ci": {
                    "github": {
                        "files": [],
                        "shared": ["ci/github/"],
                        "level_5": {
                            "files": [],
                            "shared": ["ci/github/", "ci/github/deepeval-gate.yml"],
                        },
                    }
                },
            }
        }
        files, shared = resolve_variant_files(
            manifest, {"type": "api", "ci": "github", "level": "5"}
        )
        assert files[0]["src"] == "l5.md"
        assert "ci/github/deepeval-gate.yml" in shared
        assert "features/starter_backend_l5/" in shared
