"""Tests for cli/govkit.py — copy_entry, load_manifest, resolve_options, resolve_variant_files."""

import argparse
import json
import textwrap
from pathlib import Path

import pytest

from cli.govkit import copy_entry, load_manifest, resolve_options, resolve_variant_files, cmd_apply, cmd_init, cmd_upgrade, write_govkit_marker, read_govkit_marker, _GOVKIT_VERSION


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
        files, shared, governed = resolve_variant_files(manifest, {"ci": "github"})
        assert len(files) == 2
        assert files[0]["src"] == "base.md"
        assert files[1]["src"] == "gh.yml"
        assert shared == ["governance/schemas/"]
        assert governed == []

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
        files, shared, _ = resolve_variant_files(manifest, {"ci": "github", "type": "api"})
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
        files, shared, governed = resolve_variant_files(manifest, {"ci": "azure"})
        assert len(files) == 1
        assert shared == []
        assert governed == []

    def test_unknown_variant_value(self):
        manifest = {
            "base_files": [],
            "variants": {"ci": {"github": {"files": [{"src": "g.yml", "dest": "g.yml"}]}}},
        }
        files, shared, governed = resolve_variant_files(manifest, {"ci": "nonexistent"})
        assert files == []
        assert shared == []
        assert governed == []

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
        files, shared, _ = resolve_variant_files(manifest, {"type": "api", "level": "3"})
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
        files, shared, _ = resolve_variant_files(manifest, {"type": "api", "level": "4"})
        assert len(files) == 1
        assert files[0]["src"] == "l4-api.md"
        assert shared == ["docs/backend/"]

    def test_level_default_is_3(self):
        """When level is not specified, behaves as level 3 (v0.7+)."""
        # The fixture's `level_3` block (legacy replace override) takes effect
        # at the new default level 3, so the L3 src wins. After Increment 6
        # (manifest cleanup) live manifests no longer have `level_3` blocks
        # and the top-level files are themselves the L3 foundation content.
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
        files, _, _ = resolve_variant_files(manifest, {"type": "api"})
        assert files[0]["src"] == "l3-api.md"

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
        files, _, _ = resolve_variant_files(manifest, {"ci": "github", "level": "3"})
        assert len(files) == 1
        assert files[0]["src"] == "gh.yml"

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
        files, shared, _ = resolve_variant_files(
            manifest, {"type": "api", "ci": "github", "level": "3"}
        )
        assert len(files) == 1
        assert files[0]["src"] == "l3.md"
        assert "docs/DESIGN_PRINCIPLES.md" in shared
        assert "ci/github/l3-quality-gate.yml" in shared


# ---------------------------------------------------------------------------
# Merge-mode semantics (Increment 2 — new in v0.7.0)
#
# merge mode applies override entries on top of base entries within a single
# dimension. Files dedup by `dest` (override wins on collision); shared/governed
# dedup by string equality (append + skip duplicates).
# Cross-dimension entries continue to dedup by `(src, dest)` so legitimate
# directory accumulation patterns (e.g. copilot's .github/instructions/) still work.
# ---------------------------------------------------------------------------


class TestMergeMode:
    def test_merge_appends_files_when_dests_distinct(self):
        manifest = {
            "variants": {
                "type": {
                    "api": {
                        "files": [{"src": "base.md", "dest": "BASE.md"}],
                        "level_4": {
                            "mode": "merge",
                            "files": [{"src": "addon.md", "dest": "ADDON.md"}],
                        },
                    }
                }
            }
        }
        files, _, _ = resolve_variant_files(manifest, {"type": "api", "level": "4"})
        srcs = [f["src"] for f in files]
        assert srcs == ["base.md", "addon.md"]

    def test_merge_dest_collision_override_wins(self):
        manifest = {
            "variants": {
                "type": {
                    "api": {
                        "files": [{"src": "l3.md", "dest": "CLAUDE.md"}],
                        "level_4": {
                            "mode": "merge",
                            "files": [{"src": "l4.md", "dest": "CLAUDE.md"}],
                        },
                    }
                }
            }
        }
        files, _, _ = resolve_variant_files(manifest, {"type": "api", "level": "4"})
        claude = [f for f in files if f["dest"] == "CLAUDE.md"]
        assert len(claude) == 1
        assert claude[0]["src"] == "l4.md"

    def test_merge_appends_shared(self):
        manifest = {
            "variants": {
                "type": {
                    "api": {
                        "files": [],
                        "shared": ["features/starter_backend/"],
                        "level_4": {
                            "mode": "merge",
                            "shared": ["features/schema_contract_example/"],
                        },
                    }
                }
            }
        }
        _, shared, _ = resolve_variant_files(manifest, {"type": "api", "level": "4"})
        assert "features/starter_backend/" in shared
        assert "features/schema_contract_example/" in shared

    def test_merge_dedups_shared(self):
        manifest = {
            "variants": {
                "type": {
                    "api": {
                        "files": [],
                        "shared": ["features/starter_backend/"],
                        "level_4": {
                            "mode": "merge",
                            "shared": ["features/starter_backend/", "features/schema_contract_example/"],
                        },
                    }
                }
            }
        }
        _, shared, _ = resolve_variant_files(manifest, {"type": "api", "level": "4"})
        assert shared.count("features/starter_backend/") == 1
        assert "features/schema_contract_example/" in shared

    def test_merge_appends_governed(self):
        manifest = {
            "variants": {
                "type": {
                    "api": {
                        "files": [],
                        "governed": ["docs/architecture/"],
                        "level_4": {
                            "mode": "merge",
                            "governed": ["governance/backend/"],
                        },
                    }
                }
            }
        }
        _, _, governed = resolve_variant_files(manifest, {"type": "api", "level": "4"})
        assert governed == ["docs/architecture/", "governance/backend/"]

    def test_merge_dedups_governed(self):
        manifest = {
            "variants": {
                "type": {
                    "api": {
                        "files": [],
                        "governed": ["docs/architecture/"],
                        "level_4": {
                            "mode": "merge",
                            "governed": ["docs/architecture/", "governance/backend/"],
                        },
                    }
                }
            }
        }
        _, _, governed = resolve_variant_files(manifest, {"type": "api", "level": "4"})
        assert governed.count("docs/architecture/") == 1
        assert "governance/backend/" in governed

    def test_merge_default_mode_is_merge_for_level_4(self):
        # mode key omitted → defaults to merge for level_4 blocks.
        manifest = {
            "variants": {
                "type": {
                    "api": {
                        "files": [{"src": "base.md", "dest": "BASE.md"}],
                        "level_4": {
                            "files": [{"src": "addon.md", "dest": "ADDON.md"}],
                        },
                    }
                }
            }
        }
        files, _, _ = resolve_variant_files(manifest, {"type": "api", "level": "4"})
        srcs = [f["src"] for f in files]
        assert "base.md" in srcs and "addon.md" in srcs

    def test_replace_default_mode_for_level_5(self):
        # mode key omitted → defaults to replace for level_5 blocks.
        manifest = {
            "variants": {
                "type": {
                    "api": {
                        "files": [{"src": "base.md", "dest": "BASE.md"}],
                        "level_5": {
                            "files": [{"src": "l5.md", "dest": "L5.md"}],
                        },
                    }
                }
            }
        }
        files, _, _ = resolve_variant_files(manifest, {"type": "api", "level": "5"})
        srcs = [f["src"] for f in files]
        assert srcs == ["l5.md"], "L5 default mode must be replace"

    def test_explicit_mode_overrides_default(self):
        # An explicit mode field in the override block beats the level default.
        manifest = {
            "variants": {
                "type": {
                    "api": {
                        "files": [{"src": "base.md", "dest": "BASE.md"}],
                        "level_4": {
                            "mode": "replace",
                            "files": [{"src": "l4.md", "dest": "L4.md"}],
                        },
                    }
                }
            }
        }
        files, _, _ = resolve_variant_files(manifest, {"type": "api", "level": "4"})
        srcs = [f["src"] for f in files]
        assert srcs == ["l4.md"], "Explicit mode=replace must override merge default"

    def test_cross_dimension_dest_collision_preserved(self):
        # Regression guard: copilot legitimately installs `instructions/backend/`
        # AND `instructions/ui-react/` to the same `.github/instructions/` dest
        # across the type and ui dimensions. The cross-dimension `(src, dest)`
        # dedup must keep both.
        manifest = {
            "variants": {
                "type": {
                    "api": {
                        "files": [{"src": "instructions/backend/", "dest": ".github/instructions/"}],
                    }
                },
                "ui": {
                    "react": {
                        "files": [{"src": "instructions/ui-react/", "dest": ".github/instructions/"}],
                    }
                },
            }
        }
        files, _, _ = resolve_variant_files(manifest, {"type": "api", "ui": "react"})
        srcs = sorted(f["src"] for f in files)
        assert srcs == ["instructions/backend/", "instructions/ui-react/"], (
            "Cross-dimension entries with the same dest must both survive "
            "(legitimate directory accumulation pattern)."
        )


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
        from cli.govkit import write_govkit_marker, read_govkit_level, _GOVKIT_VERSION

        write_govkit_marker(tmp_path, "claude-code", "5", {"type": "api", "level": "5"})
        data = json.loads((tmp_path / ".govkit").read_text(encoding="utf-8"))
        assert data["level"] == "5"
        assert data["version"] == _GOVKIT_VERSION
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
        files, shared, _ = resolve_variant_files(manifest, {"type": "api", "level": "5"})
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
        files, shared, _ = resolve_variant_files(manifest, {"type": "api", "level": "4"})
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
        files, shared, _ = resolve_variant_files(
            manifest, {"type": "api", "ci": "github", "level": "5"}
        )
        assert files[0]["src"] == "l5.md"
        assert "ci/github/deepeval-gate.yml" in shared
        assert "features/starter_backend_l5/" in shared


# ---------------------------------------------------------------------------
# Smoke tests — features/ behavior after no-starters-on-apply change
# ---------------------------------------------------------------------------


def _make_fake_agent(tmp_path: Path, shared: list[str] | None = None) -> Path:
    """Minimal variant-based manifest that includes a features/ shared entry."""
    agents = tmp_path / "agents" / "claude-code"
    agents.mkdir(parents=True)
    manifest = {
        "agent": "claude-code",
        "description": "Smoke test agent",
        "options": {
            "level": {"prompt": "Level?", "choices": ["3", "4", "5"], "default": "4"},
            "type": {"prompt": "Type?", "choices": ["api"], "default": "api"},
            "ci": {"prompt": "CI?", "choices": ["github"], "default": "github"},
            "ui": {"prompt": "UI?", "choices": ["none"], "default": "none"},
        },
        "variants": {
            "type": {
                "api": {
                    "files": [],
                    "shared": shared if shared is not None else ["features/starter_backend/"],
                }
            }
        },
        "base_files": [],
    }
    (agents / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return tmp_path


def _apply_args(target: Path, **overrides) -> argparse.Namespace:
    defaults = dict(agent="claude-code", target=str(target), level="4", type="api", ci="github", ui="none")
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


class TestSmokeApply:
    def test_features_dir_created_empty(self, tmp_path, monkeypatch):
        import cli.govkit as mod

        fake_repo = _make_fake_agent(tmp_path)
        target = tmp_path / "target"
        target.mkdir()
        monkeypatch.setattr(mod, "AGENTS_DIR", fake_repo / "agents")
        monkeypatch.setattr(mod, "REPO_ROOT", fake_repo)

        cmd_apply(_apply_args(target))

        features_dir = target / "features"
        assert features_dir.is_dir(), "features/ should exist after apply"
        starters = list(features_dir.glob("starter_*"))
        assert starters == [], f"No starter_* folders should be copied; found: {starters}"

    def test_reminder_message_printed(self, tmp_path, monkeypatch, capsys):
        import cli.govkit as mod

        fake_repo = _make_fake_agent(tmp_path)
        target = tmp_path / "target"
        target.mkdir()
        monkeypatch.setattr(mod, "AGENTS_DIR", fake_repo / "agents")
        monkeypatch.setattr(mod, "REPO_ROOT", fake_repo)

        cmd_apply(_apply_args(target))

        out = capsys.readouterr().out
        assert "govkit init" in out

    def test_non_features_shared_still_copied(self, tmp_path, monkeypatch):
        """Shared entries that are not under features/ should still be copied."""
        import cli.govkit as mod

        fake_repo = _make_fake_agent(tmp_path, shared=["features/starter_backend/", "governance/"])
        (fake_repo / "governance").mkdir()
        (fake_repo / "governance" / "policy.md").write_text("policy", encoding="utf-8")

        target = tmp_path / "target"
        target.mkdir()
        monkeypatch.setattr(mod, "AGENTS_DIR", fake_repo / "agents")
        monkeypatch.setattr(mod, "REPO_ROOT", fake_repo)

        cmd_apply(_apply_args(target))

        assert (target / "governance" / "policy.md").exists()
        assert not (target / "features" / "starter_backend").exists()


class TestSmokeInit:
    def _bundled_repo(self, tmp_path: Path, starter: str = "starter_backend") -> Path:
        """Fake govkit install with a minimal bundled starter."""
        bundled = tmp_path / "govkit_install" / "features" / starter
        bundled.mkdir(parents=True)
        (bundled / "acceptance.feature").write_text("Feature: bundled", encoding="utf-8")
        (bundled / "nfrs.md").write_text("# NFRs", encoding="utf-8")
        return tmp_path / "govkit_install"

    def test_init_scaffolds_from_bundled_starters(self, tmp_path, monkeypatch):
        import cli.govkit as mod

        fake_repo = self._bundled_repo(tmp_path)
        monkeypatch.setattr(mod, "REPO_ROOT", fake_repo)

        target = tmp_path / "project"
        (target / "features").mkdir(parents=True)
        write_govkit_marker(target, "claude-code", "4", {"type": "api"})

        cmd_init(argparse.Namespace(feature="my-feature", target=str(target), level=None, starter="backend"))

        feature_dir = target / "features" / "my-feature"
        assert feature_dir.exists()
        assert (feature_dir / "acceptance.feature").read_text(encoding="utf-8") == "Feature: bundled"
        assert (feature_dir / "nfrs.md").exists()

    def test_init_ignores_starters_in_target(self, tmp_path, monkeypatch):
        """Starters left in the target project (from old govkit versions) should not be used."""
        import cli.govkit as mod

        fake_repo = self._bundled_repo(tmp_path)
        monkeypatch.setattr(mod, "REPO_ROOT", fake_repo)

        target = tmp_path / "project"
        features_dir = target / "features"
        features_dir.mkdir(parents=True)
        stale = features_dir / "starter_backend"
        stale.mkdir()
        (stale / "acceptance.feature").write_text("Feature: stale", encoding="utf-8")
        write_govkit_marker(target, "claude-code", "4", {"type": "api"})

        cmd_init(argparse.Namespace(feature="new-feature", target=str(target), level=None, starter="backend"))

        content = (target / "features" / "new-feature" / "acceptance.feature").read_text(encoding="utf-8")
        assert content == "Feature: bundled", "Should use bundled starter, not stale target starter"


# ---------------------------------------------------------------------------
# governed key in resolve_variant_files
# ---------------------------------------------------------------------------


class TestGoverned:
    def test_governed_entries_collected(self):
        """governed key in variant config is returned as the third tuple element."""
        manifest = {
            "variants": {
                "type": {
                    "api": {
                        "files": [{"src": "CLAUDE.md", "dest": "CLAUDE.md"}],
                        "shared": ["features/starter_backend/"],
                        "governed": ["docs/backend/", "governance/backend/"],
                    }
                }
            }
        }
        files, shared, governed = resolve_variant_files(manifest, {"type": "api"})
        assert governed == ["docs/backend/", "governance/backend/"]
        assert shared == ["features/starter_backend/"]

    def test_governed_deduplicated_across_dimensions(self):
        """Same governed path from two dimensions is deduplicated."""
        manifest = {
            "variants": {
                "type": {
                    "api": {"files": [], "governed": ["docs/backend/"]},
                },
                "ci": {
                    "github": {"files": [], "governed": ["docs/backend/", "ci/github/"]},
                },
            }
        }
        _, _, governed = resolve_variant_files(manifest, {"type": "api", "ci": "github"})
        assert governed.count("docs/backend/") == 1
        assert "ci/github/" in governed

    def test_level_5_governed_override(self):
        """level_5 governed entries replace the top-level ones for that dimension."""
        manifest = {
            "variants": {
                "type": {
                    "api": {
                        "files": [{"src": "l4.md", "dest": "CLAUDE.md"}],
                        "shared": ["features/starter_backend/"],
                        "governed": ["docs/backend/"],
                        "level_5": {
                            "files": [{"src": "l5.md", "dest": "CLAUDE.md"}],
                            "shared": ["features/starter_backend_l5/"],
                            "governed": ["docs/backend/", "governance/schemas/eval.json"],
                        },
                    }
                }
            }
        }
        _, shared, governed = resolve_variant_files(manifest, {"type": "api", "level": "5"})
        assert "features/starter_backend_l5/" in shared
        assert "features/starter_backend/" not in shared
        assert "governance/schemas/eval.json" in governed

    def test_no_governed_returns_empty(self):
        """Variants without a governed key return an empty list."""
        manifest = {
            "variants": {
                "ci": {"github": {"files": [], "shared": ["ci/github/"]}}
            }
        }
        _, _, governed = resolve_variant_files(manifest, {"ci": "github"})
        assert governed == []


# ---------------------------------------------------------------------------
# cmd_upgrade
# ---------------------------------------------------------------------------


def _make_upgrade_repo(tmp_path: Path, agent: str = "test-agent") -> Path:
    """Create a minimal govkit repo with a governed entry."""
    agents = tmp_path / "agents" / agent
    agents.mkdir(parents=True)
    contract = tmp_path / "docs" / "contract.md"
    contract.parent.mkdir(parents=True)
    contract.write_text("# Contract v1", encoding="utf-8")

    manifest = {
        "agent": agent,
        "description": "upgrade test agent",
        "options": {
            "level": {"prompt": "Level?", "choices": ["3", "4", "5"], "default": "4"},
            "type": {"prompt": "Type?", "choices": ["api"], "default": "api"},
            "ci": {"prompt": "CI?", "choices": ["github"], "default": "github"},
            "ui": {"prompt": "UI?", "choices": ["none"], "default": "none"},
        },
        "variants": {
            "type": {
                "api": {
                    "files": [{"src": "CLAUDE.md", "dest": "CLAUDE.md"}],
                    "shared": [],
                    "governed": ["docs/"],
                }
            }
        },
        "base_files": [],
    }
    (agents / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (agents / "CLAUDE.md").write_text("# Agent instructions v2", encoding="utf-8")
    return tmp_path


class TestCmdUpgrade:
    def _target_with_marker(self, tmp_path: Path, repo: Path, version: str = "0.1.0") -> Path:
        target = tmp_path / "project"
        target.mkdir()
        # Pre-existing CLAUDE.md from old install
        (target / "CLAUDE.md").write_text("# Agent instructions v1", encoding="utf-8")
        # Pre-existing governed file
        contract = target / "docs" / "contract.md"
        contract.parent.mkdir(parents=True)
        contract.write_text("# Contract v1", encoding="utf-8")
        # .govkit marker with old version
        marker = {
            "version": version,
            "level": "4",
            "agent": "test-agent",
            "options": {"type": "api", "ci": "github", "ui": "none"},
            "applied_at": "2025-01-01T00:00:00+00:00",
        }
        (target / ".govkit").write_text(json.dumps(marker), encoding="utf-8")
        return target

    def test_upgrade_refreshes_agent_files(self, tmp_path, monkeypatch):
        """cmd_upgrade overwrites agent files (files category)."""
        import cli.govkit as mod

        repo = _make_upgrade_repo(tmp_path)
        target = self._target_with_marker(tmp_path, repo, version="0.1.0")
        monkeypatch.setattr(mod, "AGENTS_DIR", repo / "agents")
        monkeypatch.setattr(mod, "REPO_ROOT", repo)
        monkeypatch.setattr(mod, "_GOVKIT_VERSION", "0.2.0")

        cmd_upgrade(argparse.Namespace(target=str(target), force=False))

        assert (target / "CLAUDE.md").read_text(encoding="utf-8") == "# Agent instructions v2"

    def test_upgrade_refreshes_governed_files(self, tmp_path, monkeypatch):
        """cmd_upgrade overwrites governed files when version advances."""
        import cli.govkit as mod

        repo = _make_upgrade_repo(tmp_path)
        # Update the governed file in the repo to simulate a govkit update
        (repo / "docs" / "contract.md").write_text("# Contract v2", encoding="utf-8")

        target = self._target_with_marker(tmp_path, repo, version="0.1.0")
        monkeypatch.setattr(mod, "AGENTS_DIR", repo / "agents")
        monkeypatch.setattr(mod, "REPO_ROOT", repo)
        monkeypatch.setattr(mod, "_GOVKIT_VERSION", "0.2.0")

        cmd_upgrade(argparse.Namespace(target=str(target), force=False))

        assert (target / "docs" / "contract.md").read_text(encoding="utf-8") == "# Contract v2"

    def test_upgrade_skips_when_version_current(self, tmp_path, monkeypatch, capsys):
        """cmd_upgrade does nothing when already at current version."""
        import cli.govkit as mod

        repo = _make_upgrade_repo(tmp_path)
        target = self._target_with_marker(tmp_path, repo, version=_GOVKIT_VERSION)
        monkeypatch.setattr(mod, "AGENTS_DIR", repo / "agents")
        monkeypatch.setattr(mod, "REPO_ROOT", repo)

        cmd_upgrade(argparse.Namespace(target=str(target), force=False))

        out = capsys.readouterr().out
        assert "Nothing to upgrade" in out
        # CLAUDE.md was NOT overwritten
        assert (target / "CLAUDE.md").read_text(encoding="utf-8") == "# Agent instructions v1"

    def test_upgrade_force_overwrites_even_if_current(self, tmp_path, monkeypatch):
        """cmd_upgrade --force overwrites even when version is current."""
        import cli.govkit as mod

        repo = _make_upgrade_repo(tmp_path)
        target = self._target_with_marker(tmp_path, repo, version=_GOVKIT_VERSION)
        monkeypatch.setattr(mod, "AGENTS_DIR", repo / "agents")
        monkeypatch.setattr(mod, "REPO_ROOT", repo)

        cmd_upgrade(argparse.Namespace(target=str(target), force=True))

        assert (target / "CLAUDE.md").read_text(encoding="utf-8") == "# Agent instructions v2"

    def test_upgrade_updates_marker_version(self, tmp_path, monkeypatch):
        """cmd_upgrade writes the new govkit version to the .govkit marker."""
        import cli.govkit as mod

        repo = _make_upgrade_repo(tmp_path)
        target = self._target_with_marker(tmp_path, repo, version="0.1.0")
        monkeypatch.setattr(mod, "AGENTS_DIR", repo / "agents")
        monkeypatch.setattr(mod, "REPO_ROOT", repo)
        monkeypatch.setattr(mod, "_GOVKIT_VERSION", "0.2.0")

        cmd_upgrade(argparse.Namespace(target=str(target), force=False))

        marker = read_govkit_marker(target)
        assert marker["version"] == "0.2.0"

    def test_upgrade_no_marker_exits(self, tmp_path, monkeypatch):
        """cmd_upgrade exits 1 when no .govkit marker exists."""
        import cli.govkit as mod

        target = tmp_path / "bare"
        target.mkdir()
        monkeypatch.setattr(mod, "AGENTS_DIR", tmp_path / "agents")

        with pytest.raises(SystemExit):
            cmd_upgrade(argparse.Namespace(target=str(target), force=False))
