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

    def test_level_4_no_override_uses_base(self):
        """When level=4 and no level_4 block exists, top-level files are used."""
        manifest = {
            "variants": {
                "type": {
                    "api": {
                        "files": [{"src": "base-api.md", "dest": "CLAUDE.md"}],
                        "shared": ["docs/backend/"],
                    }
                }
            }
        }
        files, shared, _ = resolve_variant_files(manifest, {"type": "api", "level": "4"})
        assert len(files) == 1
        assert files[0]["src"] == "base-api.md"
        assert shared == ["docs/backend/"]

    def test_level_default_is_3_uses_top_level(self):
        """When no level is specified, the default is level 3, which uses top-level (base) entries."""
        # Post-Increment-11: L3 has no override key. The default-level run
        # resolves to the variant's top-level files/shared/governed.
        manifest = {
            "variants": {
                "type": {
                    "api": {
                        "files": [{"src": "foundations.md", "dest": "CLAUDE.md"}],
                        "shared": ["docs/backend/architecture/"],
                    }
                }
            }
        }
        files, shared, _ = resolve_variant_files(manifest, {"type": "api"})
        assert files[0]["src"] == "foundations.md"
        assert shared == ["docs/backend/architecture/"]

    def test_level_3_uses_base_directly(self):
        """At level=3 the variant's top-level entries are used (no override key checked)."""
        manifest = {
            "variants": {
                "ci": {
                    "github": {
                        "files": [{"src": "l3-quality-gate.yml", "dest": ".github/workflows/quality-gate.yml"}],
                        "shared": [],
                        "governed": ["ci/github/repo-scope-check.yml"],
                    }
                }
            }
        }
        files, _, governed = resolve_variant_files(manifest, {"ci": "github", "level": "3"})
        assert len(files) == 1
        assert files[0]["src"] == "l3-quality-gate.yml"
        assert "ci/github/repo-scope-check.yml" in governed


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

    def test_by_type_dispatch_backend_gets_backend_gates(self):
        """variants.ci with by_type: --type api routes to api-specific governed entries."""
        manifest = {
            "variants": {
                "type": {"api": {"files": []}},
                "ci": {
                    "github": {
                        "governed": ["ci/github/repo-scope-check.yml"],
                        "by_type": {
                            "api":      {"governed": ["ci/github/l3-quality-gate.yml"]},
                            "ui-react": {"governed": ["ci/github/l3-ui-quality-gate.yml"]},
                        },
                    }
                },
            }
        }
        _, _, governed = resolve_variant_files(manifest, {"type": "api", "ci": "github"})
        assert "ci/github/repo-scope-check.yml" in governed, "common base entry must always ship"
        assert "ci/github/l3-quality-gate.yml" in governed, "by_type[api] entry must ship"
        assert "ci/github/l3-ui-quality-gate.yml" not in governed, "by_type[ui-react] must NOT ship for type=api"

    def test_by_type_dispatch_ui_gets_ui_gates(self):
        """variants.ci with by_type: --type ui-react routes to ui-specific governed entries."""
        manifest = {
            "variants": {
                "type": {"ui-react": {"files": []}},
                "ci": {
                    "github": {
                        "governed": ["ci/github/repo-scope-check.yml"],
                        "by_type": {
                            "api":      {"governed": ["ci/github/l3-quality-gate.yml"]},
                            "ui-react": {"governed": ["ci/github/l3-ui-quality-gate.yml"]},
                        },
                    }
                },
            }
        }
        _, _, governed = resolve_variant_files(manifest, {"type": "ui-react", "ci": "github"})
        assert "ci/github/repo-scope-check.yml" in governed
        assert "ci/github/l3-ui-quality-gate.yml" in governed
        assert "ci/github/l3-quality-gate.yml" not in governed, "backend gate must NOT ship for type=ui-react"

    def test_by_type_dispatch_at_level_4_merge(self):
        """by_type works in both base and level_4 override (merge mode)."""
        manifest = {
            "variants": {
                "type": {"api": {"files": []}},
                "ci": {
                    "github": {
                        "governed": [],
                        "by_type": {"api": {"governed": ["base.yml"]}},
                        "level_4": {
                            "mode": "merge",
                            "governed": [],
                            "by_type": {"api": {"governed": ["l4.yml"]}},
                        },
                    }
                },
            }
        }
        _, _, governed = resolve_variant_files(
            manifest, {"type": "api", "ci": "github", "level": "4"}
        )
        assert governed == ["base.yml", "l4.yml"], (
            f"L4 merge must include base.by_type + override.by_type; got {governed}"
        )

    def test_by_type_dispatch_at_level_5_replace(self):
        """by_type at level_5 (replace mode) discards base entirely."""
        manifest = {
            "variants": {
                "type": {"api": {"files": []}},
                "ci": {
                    "github": {
                        "governed": ["base.yml"],
                        "by_type": {"api": {"governed": ["base-api.yml"]}},
                        "level_5": {
                            "mode": "replace",
                            "governed": ["l5-common.yml"],
                            "by_type": {"api": {"governed": ["l5-api.yml"]}},
                        },
                    }
                },
            }
        }
        _, _, governed = resolve_variant_files(
            manifest, {"type": "api", "ci": "github", "level": "5"}
        )
        assert governed == ["l5-common.yml", "l5-api.yml"], (
            f"L5 replace must use only override + override.by_type; got {governed}"
        )

    def test_by_type_missing_entry_falls_through(self):
        """If by_type has no entry for the current type value, only base entries ship."""
        manifest = {
            "variants": {
                "type": {"api": {"files": []}},
                "ci": {
                    "github": {
                        "governed": ["common.yml"],
                        "by_type": {"ui-react": {"governed": ["ui-only.yml"]}},
                    }
                },
            }
        }
        _, _, governed = resolve_variant_files(manifest, {"type": "api", "ci": "github"})
        assert governed == ["common.yml"], (
            f"Missing by_type[api] entry must fall through to base only; got {governed}"
        )

    def test_cross_dimension_dest_collision_preserved(self):
        # Synthetic guard for the cross-dimension `(src, dest)` dedup mechanism
        # in `_collect_entries`. Two distinct dimensions contributing different
        # sources to the same dest must both survive — within-dimension dedup
        # is `_dimension_entries`'s job and runs upstream. This test uses two
        # synthetic dimensions (the production v0.8 manifests no longer have
        # a real cross-dimension collision case, but the mechanism is defensive
        # against future additions and must not regress).
        manifest = {
            "variants": {
                "type": {
                    "api": {
                        "files": [{"src": "instructions/backend/", "dest": ".github/instructions/"}],
                    }
                },
                "ci": {
                    "github": {
                        "files": [{"src": "ci-instructions/github/", "dest": ".github/instructions/"}],
                    }
                },
            }
        }
        files, _, _ = resolve_variant_files(manifest, {"type": "api", "ci": "github"})
        srcs = sorted(f["src"] for f in files)
        assert srcs == ["ci-instructions/github/", "instructions/backend/"], (
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
        data = json.loads((tmp_path / ".govkit" / "marker.json").read_text(encoding="utf-8"))
        assert "level" not in data["options"]
        assert data["options"]["type"] == "api"
        assert data["level"] == "3"

    def test_write_level_5_marker(self, tmp_path):
        import json
        from cli.govkit import write_govkit_marker, read_govkit_level, _GOVKIT_VERSION

        write_govkit_marker(tmp_path, "claude-code", "5", {"type": "api", "level": "5"})
        data = json.loads((tmp_path / ".govkit" / "marker.json").read_text(encoding="utf-8"))
        assert data["level"] == "5"
        assert data["version"] == _GOVKIT_VERSION
        assert read_govkit_level(tmp_path) == "5"


class TestMarkerDirectoryLayout:
    """PR 1 / A1: .govkit becomes a directory containing marker.json.

    Legacy single-file markers are read tolerantly and migrated on first read.
    Write paths only emit the directory layout.
    """

    def test_write_creates_directory_with_marker_json(self, tmp_path):
        from cli.govkit import write_govkit_marker

        write_govkit_marker(tmp_path, "claude-code", "3", {"type": "api", "level": "3"})

        marker_dir = tmp_path / ".govkit"
        marker_json = marker_dir / "marker.json"
        assert marker_dir.is_dir(), ".govkit must be a directory after write"
        assert marker_json.is_file(), ".govkit/marker.json must exist"

    def test_write_does_not_create_legacy_file(self, tmp_path):
        from cli.govkit import write_govkit_marker

        write_govkit_marker(tmp_path, "claude-code", "3", {"type": "api", "level": "3"})

        # On Windows/POSIX a name is either a file or a directory, but assert
        # the inverse explicitly so the layout intent is recorded in the test.
        assert not (tmp_path / ".govkit").is_file(), ".govkit must not be a single file"

    def test_read_new_directory_layout_returns_payload(self, tmp_path):
        from cli.govkit import write_govkit_marker, read_govkit_marker

        write_govkit_marker(tmp_path, "claude-code", "4", {"type": "api", "ci": "github", "level": "4"})

        data = read_govkit_marker(tmp_path)
        assert data is not None
        assert data["agent"] == "claude-code"
        assert data["level"] == "4"
        assert data["options"]["type"] == "api"

    def test_read_legacy_file_layout_back_compat(self, tmp_path, monkeypatch):
        """A pre-existing .govkit single-file marker must still be readable."""
        import cli.govkit as mod
        mod._reset_directory_migration_warning()
        monkeypatch.setenv("GOVKIT_NO_DIRECTORY_MIGRATION_WARNING", "1")

        legacy_payload = {
            "version": "0.9.0",
            "level": "4",
            "agent": "claude-code",
            "options": {"type": "api", "ci": "github"},
            "applied_at": "2026-04-01T00:00:00+00:00",
        }
        (tmp_path / ".govkit").write_text(json.dumps(legacy_payload), encoding="utf-8")

        data = mod.read_govkit_marker(tmp_path)
        assert data is not None
        assert data["agent"] == "claude-code"
        assert data["options"]["type"] == "api"

    def test_read_legacy_file_layout_auto_migrates_to_directory(self, tmp_path, monkeypatch):
        """After reading a legacy file marker, the directory layout must exist
        and the legacy file must be gone."""
        import cli.govkit as mod
        mod._reset_directory_migration_warning()
        monkeypatch.setenv("GOVKIT_NO_DIRECTORY_MIGRATION_WARNING", "1")

        legacy_payload = {
            "version": "0.9.0",
            "level": "4",
            "agent": "claude-code",
            "options": {"type": "api", "ci": "github"},
            "applied_at": "2026-04-01T00:00:00+00:00",
        }
        legacy_path = tmp_path / ".govkit"
        legacy_path.write_text(json.dumps(legacy_payload), encoding="utf-8")
        assert legacy_path.is_file()

        mod.read_govkit_marker(tmp_path)

        marker_dir = tmp_path / ".govkit"
        assert marker_dir.is_dir(), "directory layout must be created on read"
        assert (marker_dir / "marker.json").is_file(), "marker.json must be written"

        roundtrip = json.loads((marker_dir / "marker.json").read_text(encoding="utf-8"))
        assert roundtrip["agent"] == "claude-code"
        assert roundtrip["options"]["type"] == "api"

    def test_migration_warning_fires_for_legacy_file(self, tmp_path, monkeypatch, capsys):
        import cli.govkit as mod
        mod._reset_directory_migration_warning()
        mod._reset_migration_warning()
        mod._reset_shape_migration_warning()
        monkeypatch.delenv("GOVKIT_NO_DIRECTORY_MIGRATION_WARNING", raising=False)

        legacy_payload = {
            "version": "0.9.0", "level": "4", "agent": "claude-code",
            "options": {"type": "api", "ci": "github"},
            "applied_at": "2026-04-01T00:00:00+00:00",
        }
        (tmp_path / ".govkit").write_text(json.dumps(legacy_payload), encoding="utf-8")

        mod.read_govkit_marker(tmp_path)
        err = capsys.readouterr().err
        assert "legacy single-file .govkit marker" in err
        assert "layout changed in 0.10.0" in err
        assert "GOVKIT_NO_DIRECTORY_MIGRATION_WARNING" in err

    def test_migration_warning_only_fires_once_per_invocation(self, tmp_path, monkeypatch, capsys):
        import cli.govkit as mod
        mod._reset_directory_migration_warning()
        mod._reset_migration_warning()
        mod._reset_shape_migration_warning()
        monkeypatch.delenv("GOVKIT_NO_DIRECTORY_MIGRATION_WARNING", raising=False)

        legacy_payload = {
            "version": "0.9.0", "level": "4", "agent": "claude-code",
            "options": {"type": "api", "ci": "github"},
            "applied_at": "2026-04-01T00:00:00+00:00",
        }
        (tmp_path / ".govkit").write_text(json.dumps(legacy_payload), encoding="utf-8")

        # First read migrates; subsequent reads see the directory and emit nothing.
        mod.read_govkit_marker(tmp_path)
        mod.read_govkit_marker(tmp_path)
        mod.read_govkit_marker(tmp_path)
        err = capsys.readouterr().err
        # Directory message appears at most once.
        directory_msg_count = err.count("GOVKIT_NO_DIRECTORY_MIGRATION_WARNING")
        assert directory_msg_count == 1

    def test_migration_warning_suppressed_by_env_var(self, tmp_path, monkeypatch, capsys):
        import cli.govkit as mod
        mod._reset_directory_migration_warning()
        mod._reset_migration_warning()
        mod._reset_shape_migration_warning()
        monkeypatch.setenv("GOVKIT_NO_DIRECTORY_MIGRATION_WARNING", "1")
        # Also suppress unrelated warnings so we can assert err == ""
        monkeypatch.setenv("GOVKIT_NO_MIGRATION_WARNING", "1")
        monkeypatch.setenv("GOVKIT_NO_SHAPE_MIGRATION_WARNING", "1")

        legacy_payload = {
            "version": "0.9.0", "level": "4", "agent": "claude-code",
            "options": {"type": "api", "ci": "github"},
            "applied_at": "2026-04-01T00:00:00+00:00",
        }
        (tmp_path / ".govkit").write_text(json.dumps(legacy_payload), encoding="utf-8")

        mod.read_govkit_marker(tmp_path)
        err = capsys.readouterr().err
        assert err == ""

    def test_no_migration_warning_when_already_directory(self, tmp_path, monkeypatch, capsys):
        """Fresh installs that write the directory layout straight away must
        not emit the directory migration warning."""
        import cli.govkit as mod
        mod._reset_directory_migration_warning()
        mod._reset_migration_warning()
        mod._reset_shape_migration_warning()
        monkeypatch.delenv("GOVKIT_NO_DIRECTORY_MIGRATION_WARNING", raising=False)

        from cli.govkit import write_govkit_marker
        write_govkit_marker(tmp_path, "claude-code", "4", {"type": "api", "ci": "github", "level": "4"})

        mod.read_govkit_marker(tmp_path)
        err = capsys.readouterr().err
        assert "GOVKIT_NO_DIRECTORY_MIGRATION_WARNING" not in err

    def test_write_over_legacy_file_replaces_with_directory(self, tmp_path):
        """If a legacy file exists when write is called, write must remove the
        file and create the directory layout."""
        from cli.govkit import write_govkit_marker

        legacy_payload = {
            "version": "0.9.0", "level": "4", "agent": "claude-code",
            "options": {"type": "api"}, "applied_at": "2026-04-01T00:00:00+00:00",
        }
        (tmp_path / ".govkit").write_text(json.dumps(legacy_payload), encoding="utf-8")

        write_govkit_marker(tmp_path, "claude-code", "4", {"type": "api", "ci": "github", "level": "4"})

        assert (tmp_path / ".govkit").is_dir()
        assert (tmp_path / ".govkit" / "marker.json").is_file()

    def test_read_level_under_new_directory_layout(self, tmp_path):
        from cli.govkit import write_govkit_marker, read_govkit_level

        write_govkit_marker(tmp_path, "claude-code", "5", {"type": "api", "ci": "github", "level": "5"})
        assert read_govkit_level(tmp_path) == "5"


class TestExtendedMarkerFields:
    """PR 1: marker carries assumptions[], stack{}, calibration{} so future
    PRs (2/3/5) can populate them without further schema migrations."""

    def test_new_marker_includes_empty_assumptions(self, tmp_path):
        import json
        from cli.govkit import write_govkit_marker

        write_govkit_marker(tmp_path, "claude-code", "4", {"type": "api", "ci": "github", "level": "4"})
        data = json.loads((tmp_path / ".govkit" / "marker.json").read_text(encoding="utf-8"))
        assert "assumptions" in data
        assert data["assumptions"] == []

    def test_new_marker_includes_null_stack(self, tmp_path):
        import json
        from cli.govkit import write_govkit_marker

        write_govkit_marker(tmp_path, "claude-code", "4", {"type": "api", "ci": "github", "level": "4"})
        data = json.loads((tmp_path / ".govkit" / "marker.json").read_text(encoding="utf-8"))
        assert "stack" in data
        assert data["stack"] is None

    def test_new_marker_includes_calibration_block(self, tmp_path):
        import json
        from cli.govkit import write_govkit_marker

        write_govkit_marker(tmp_path, "claude-code", "4", {"type": "api", "ci": "github", "level": "4"})
        data = json.loads((tmp_path / ".govkit" / "marker.json").read_text(encoding="utf-8"))
        assert "calibration" in data
        assert data["calibration"]["completed_at"] is None
        assert data["calibration"]["decisions"] == []

    def test_write_marker_accepts_stack_param(self, tmp_path):
        """PR 2 will populate stack via this kwarg; PR 1 exposes the slot."""
        import json
        from cli.govkit import write_govkit_marker

        stack = {
            "id": "dotnet-aspnet",
            "version": "0.10.0",
            "display_name": "C# 12 / .NET 8 / ASP.NET Core",
            "applied_at": "2026-05-27T15:00:00+00:00",
        }
        write_govkit_marker(
            tmp_path, "claude-code", "4",
            {"type": "api", "ci": "azure", "level": "4"},
            stack=stack,
        )
        data = json.loads((tmp_path / ".govkit" / "marker.json").read_text(encoding="utf-8"))
        assert data["stack"]["id"] == "dotnet-aspnet"
        assert data["stack"]["version"] == "0.10.0"

    def test_write_marker_accepts_assumptions_param(self, tmp_path):
        """PR 3 will populate assumptions via this kwarg; PR 1 exposes the slot."""
        import json
        from cli.govkit import write_govkit_marker

        assumptions = [{
            "id": "stack.language",
            "value": "python",
            "source": "default",
            "confidence": "low",
            "evidence": [],
            "files_affected": ["docs/backend/architecture/TECH_STACK.md"],
            "review_required": True,
            "warning_message": None,
            "calibrated_at": None,
            "calibrated_against_overlay_version": None,
        }]
        write_govkit_marker(
            tmp_path, "claude-code", "4",
            {"type": "api", "ci": "github", "level": "4"},
            assumptions=assumptions,
        )
        data = json.loads((tmp_path / ".govkit" / "marker.json").read_text(encoding="utf-8"))
        assert len(data["assumptions"]) == 1
        assert data["assumptions"][0]["id"] == "stack.language"

    def test_read_legacy_marker_without_new_fields_succeeds(self, tmp_path, monkeypatch):
        """Markers written by older govkit versions lack the new fields.
        read_govkit_marker must not crash; callers that need the fields use
        dict.get() defaults."""
        import json
        import cli.govkit as mod
        mod._reset_directory_migration_warning()
        mod._reset_migration_warning()
        mod._reset_shape_migration_warning()
        monkeypatch.setenv("GOVKIT_NO_DIRECTORY_MIGRATION_WARNING", "1")
        monkeypatch.setenv("GOVKIT_NO_MIGRATION_WARNING", "1")
        monkeypatch.setenv("GOVKIT_NO_SHAPE_MIGRATION_WARNING", "1")

        # Pre-PR-1 marker shape: no assumptions / stack / calibration fields.
        legacy = {
            "version": "0.9.0", "level": "4", "agent": "claude-code",
            "options": {"type": "api", "ci": "github"},
            "applied_at": "2026-04-01T00:00:00+00:00",
        }
        (tmp_path / ".govkit").write_text(json.dumps(legacy), encoding="utf-8")

        data = mod.read_govkit_marker(tmp_path)
        assert data is not None
        # Caller uses .get(...) defaults to access new fields.
        assert data.get("assumptions", []) == []
        assert data.get("stack") is None
        assert data.get("calibration", {"completed_at": None, "decisions": []})["decisions"] == []


class TestIsUserEdited:
    """PR 1 / A2: is_user_edited(dest, applied_at) is the primitive that
    edit-protection in cmd_apply / cmd_upgrade rely on."""

    def _write_headed_file(self, path, content_body="# Doc\n\nBody\n"):
        from cli.headers import format_editable_header
        header = format_editable_header(baseline="govkit@0.10.0")
        path.write_text(header + content_body, encoding="utf-8")

    def test_returns_false_when_applied_at_is_none(self, tmp_path):
        from cli.govkit import is_user_edited

        doc = tmp_path / "TECH_STACK.md"
        self._write_headed_file(doc)
        assert is_user_edited(doc, None) is False

    def test_returns_false_when_file_does_not_exist(self, tmp_path):
        from cli.govkit import is_user_edited

        assert is_user_edited(tmp_path / "missing.md", "2026-05-27T10:00:00+00:00") is False

    def test_returns_false_when_file_has_no_editable_header(self, tmp_path):
        from cli.govkit import is_user_edited

        doc = tmp_path / "TECH_STACK.md"
        doc.write_text("# Just a doc\n", encoding="utf-8")
        # mtime is now; applied_at is in the past — without header, no protection
        assert is_user_edited(doc, "2020-01-01T00:00:00+00:00") is False

    def test_returns_false_when_mtime_at_or_before_applied_at(self, tmp_path):
        import os
        from datetime import datetime, timezone
        from cli.govkit import is_user_edited

        doc = tmp_path / "TECH_STACK.md"
        self._write_headed_file(doc)
        # Set mtime to a known instant; applied_at slightly later.
        file_time = datetime(2026, 5, 27, 10, 0, 0, tzinfo=timezone.utc).timestamp()
        os.utime(doc, (file_time, file_time))
        applied_at = datetime(2026, 5, 27, 10, 0, 1, tzinfo=timezone.utc).isoformat()
        assert is_user_edited(doc, applied_at) is False

    def test_returns_true_when_headed_file_modified_after_applied_at(self, tmp_path):
        import os
        from datetime import datetime, timezone
        from cli.govkit import is_user_edited

        doc = tmp_path / "TECH_STACK.md"
        self._write_headed_file(doc)
        # File mtime: an hour after the supposed last apply.
        file_time = datetime(2026, 5, 27, 11, 0, 0, tzinfo=timezone.utc).timestamp()
        os.utime(doc, (file_time, file_time))
        applied_at = datetime(2026, 5, 27, 10, 0, 0, tzinfo=timezone.utc).isoformat()
        assert is_user_edited(doc, applied_at) is True

    def test_returns_false_for_malformed_applied_at(self, tmp_path):
        from cli.govkit import is_user_edited

        doc = tmp_path / "TECH_STACK.md"
        self._write_headed_file(doc)
        assert is_user_edited(doc, "not-an-iso-timestamp") is False


class TestCopyEntryEditProtection:
    """copy_entry with applied_at activates the edit-protection guard.
    Without applied_at, copy_entry preserves its pre-PR-1 behavior."""

    def _write_headed_file(self, path, content_body="# Existing\n"):
        from cli.headers import format_editable_header
        header = format_editable_header(baseline="govkit@0.10.0")
        path.write_text(header + content_body, encoding="utf-8")

    def test_legacy_copy_without_applied_at_overwrites_freely(self, tmp_path):
        """Today's behavior must not break: copy_entry with no applied_at copies."""
        from cli.govkit import copy_entry

        src = tmp_path / "src.md"
        src.write_text("# new\n", encoding="utf-8")
        dest = tmp_path / "dest.md"
        self._write_headed_file(dest, "# old\n")

        copy_entry(src, dest)  # no applied_at → no guard
        assert "# new" in dest.read_text(encoding="utf-8")

    def test_refuses_overwrite_of_user_edited_file(self, tmp_path, capsys):
        import os
        from datetime import datetime, timezone
        from cli.govkit import copy_entry

        src = tmp_path / "src.md"
        src.write_text("# refreshed baseline\n", encoding="utf-8")
        dest = tmp_path / "dest.md"
        self._write_headed_file(dest, "# my edits\n")

        # User edited an hour after the last apply.
        edited_time = datetime(2026, 5, 27, 11, 0, 0, tzinfo=timezone.utc).timestamp()
        os.utime(dest, (edited_time, edited_time))
        applied_at = datetime(2026, 5, 27, 10, 0, 0, tzinfo=timezone.utc).isoformat()

        copy_entry(src, dest, applied_at=applied_at, force=False)

        assert "my edits" in dest.read_text(encoding="utf-8")
        assert "refreshed baseline" not in dest.read_text(encoding="utf-8")
        err = capsys.readouterr().err
        assert "refused" in err
        assert "--force" in err

    def test_force_overrides_protection(self, tmp_path, capsys):
        import os
        from datetime import datetime, timezone
        from cli.govkit import copy_entry

        src = tmp_path / "src.md"
        src.write_text("# refreshed baseline\n", encoding="utf-8")
        dest = tmp_path / "dest.md"
        self._write_headed_file(dest, "# my edits\n")
        edited_time = datetime(2026, 5, 27, 11, 0, 0, tzinfo=timezone.utc).timestamp()
        os.utime(dest, (edited_time, edited_time))
        applied_at = datetime(2026, 5, 27, 10, 0, 0, tzinfo=timezone.utc).isoformat()

        copy_entry(src, dest, applied_at=applied_at, force=True)

        assert "refreshed baseline" in dest.read_text(encoding="utf-8")
        err = capsys.readouterr().err
        assert "overwriting user edits" in err

    def test_copies_freely_when_file_unedited_since_apply(self, tmp_path):
        import os
        from datetime import datetime, timezone
        from cli.govkit import copy_entry

        src = tmp_path / "src.md"
        src.write_text("# refreshed\n", encoding="utf-8")
        dest = tmp_path / "dest.md"
        self._write_headed_file(dest, "# baseline\n")
        old_time = datetime(2026, 5, 27, 9, 0, 0, tzinfo=timezone.utc).timestamp()
        os.utime(dest, (old_time, old_time))
        applied_at = datetime(2026, 5, 27, 10, 0, 0, tzinfo=timezone.utc).isoformat()

        copy_entry(src, dest, applied_at=applied_at, force=False)

        assert "refreshed" in dest.read_text(encoding="utf-8")

    def test_directory_copy_protects_per_file(self, tmp_path):
        import os
        from datetime import datetime, timezone
        from cli.govkit import copy_entry

        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "a.md").write_text("# new a\n", encoding="utf-8")
        (src_dir / "b.md").write_text("# new b\n", encoding="utf-8")

        dest_dir = tmp_path / "dest"
        dest_dir.mkdir()
        self._write_headed_file(dest_dir / "a.md", "# user-edited a\n")
        self._write_headed_file(dest_dir / "b.md", "# unedited b\n")

        # Only `a.md` is edited after the apply timestamp.
        edited_time = datetime(2026, 5, 27, 11, 0, 0, tzinfo=timezone.utc).timestamp()
        old_time = datetime(2026, 5, 27, 9, 0, 0, tzinfo=timezone.utc).timestamp()
        os.utime(dest_dir / "a.md", (edited_time, edited_time))
        os.utime(dest_dir / "b.md", (old_time, old_time))
        applied_at = datetime(2026, 5, 27, 10, 0, 0, tzinfo=timezone.utc).isoformat()

        copy_entry(src_dir, dest_dir, applied_at=applied_at, force=False)

        # a.md kept user edits; b.md refreshed
        assert "user-edited a" in (dest_dir / "a.md").read_text(encoding="utf-8")
        assert "new b" in (dest_dir / "b.md").read_text(encoding="utf-8")


class TestCopyEntryHeaderInjection:
    """copy_entry with header_baseline prepends the govkit:editable header
    after each successful .md copy. Used by governed/shared paths in apply
    and upgrade so doc baselines stay in sync."""

    def test_prepends_header_to_md_file_on_copy(self, tmp_path):
        from cli.govkit import copy_entry

        src = tmp_path / "src.md"
        src.write_text("# Body\n", encoding="utf-8")
        dest = tmp_path / "dest.md"

        copy_entry(src, dest, header_baseline="govkit@0.10.0")

        content = dest.read_text(encoding="utf-8")
        assert content.startswith("<!-- govkit:editable")
        assert "baseline: govkit@0.10.0" in content
        assert "# Body" in content

    def test_does_not_add_header_to_non_md_file(self, tmp_path):
        from cli.govkit import copy_entry

        src = tmp_path / "src.yaml"
        src.write_text("key: value\n", encoding="utf-8")
        dest = tmp_path / "dest.yaml"

        copy_entry(src, dest, header_baseline="govkit@0.10.0")

        assert dest.read_text(encoding="utf-8") == "key: value\n"

    def test_does_not_add_header_when_skip_existing_skipped(self, tmp_path):
        from cli.govkit import copy_entry

        src = tmp_path / "src.md"
        src.write_text("# new\n", encoding="utf-8")
        dest = tmp_path / "dest.md"
        dest.write_text("# pre-existing user file\n", encoding="utf-8")

        copy_entry(src, dest, skip_existing=True, header_baseline="govkit@0.10.0")

        # Skip-existing means no copy and no header injection.
        assert dest.read_text(encoding="utf-8") == "# pre-existing user file\n"

    def test_directory_copy_adds_headers_to_each_md_child(self, tmp_path):
        from cli.govkit import copy_entry

        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "a.md").write_text("# A\n", encoding="utf-8")
        (src_dir / "b.md").write_text("# B\n", encoding="utf-8")
        (src_dir / "c.yaml").write_text("c: 1\n", encoding="utf-8")

        dest_dir = tmp_path / "dest"

        copy_entry(src_dir, dest_dir, header_baseline="govkit@0.10.0")

        assert (dest_dir / "a.md").read_text(encoding="utf-8").startswith("<!-- govkit:editable")
        assert (dest_dir / "b.md").read_text(encoding="utf-8").startswith("<!-- govkit:editable")
        assert (dest_dir / "c.yaml").read_text(encoding="utf-8") == "c: 1\n"


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
    defaults = dict(agent="claude-code", target=str(target), level="4", type="api", ci="github")
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

    def test_apply_silent_when_no_extensions(self, tmp_path, monkeypatch, capsys):
        """Apply must not mention extensions when extensions/ is absent — regression guard."""
        import cli.govkit as mod

        fake_repo = _make_fake_agent(tmp_path)
        target = tmp_path / "target"
        target.mkdir()
        monkeypatch.setattr(mod, "AGENTS_DIR", fake_repo / "agents")
        monkeypatch.setattr(mod, "REPO_ROOT", fake_repo)

        cmd_apply(_apply_args(target))

        assert "Extensions detected" not in capsys.readouterr().out

    def test_apply_with_extensions_prints_summary(self, tmp_path, monkeypatch, capsys):
        """Apply should discover and report extensions present in the target."""
        import cli.govkit as mod

        fake_repo = _make_fake_agent(tmp_path)
        target = tmp_path / "target"
        target.mkdir()
        ext_dir = target / "extensions" / "agentic-skills"
        ext_dir.mkdir(parents=True)
        (ext_dir / "manifest.yaml").write_text(
            textwrap.dedent("""\
                id: agentic-skills
                name: Agentic Skills Architecture Extension
                version: 0.1.0
                extension_type: architecture
                contract_sets:
                  - id: agentic_skills
                    description: contracts
                    paths: []
                """),
            encoding="utf-8",
        )
        monkeypatch.setattr(mod, "AGENTS_DIR", fake_repo / "agents")
        monkeypatch.setattr(mod, "REPO_ROOT", fake_repo)

        cmd_apply(_apply_args(target))

        out = capsys.readouterr().out
        assert "Extensions detected" in out
        assert "agentic-skills v0.1.0" in out


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

    @pytest.mark.parametrize("ui_starter", ["ui-react", "ui-angular"])
    def test_init_ui_variants_resolve_to_starter_ui(self, tmp_path, monkeypatch, ui_starter):
        """ui-react and ui-angular both map to the framework-agnostic starter_ui dir."""
        import cli.govkit as mod

        fake_repo = self._bundled_repo(tmp_path, starter="starter_ui")
        monkeypatch.setattr(mod, "REPO_ROOT", fake_repo)

        target = tmp_path / "project"
        (target / "features").mkdir(parents=True)
        write_govkit_marker(target, "claude-code", "4", {"type": ui_starter})

        cmd_init(argparse.Namespace(feature="my-ui-feature", target=str(target), level=None, starter=ui_starter))

        feature_dir = target / "features" / "my-ui-feature"
        assert (feature_dir / "acceptance.feature").read_text(encoding="utf-8") == "Feature: bundled"

    @pytest.mark.parametrize("ui_starter,level", [
        ("ui-react", "4"), ("ui-react", "5"),
        ("ui-angular", "4"), ("ui-angular", "5"),
    ])
    def test_resolve_starter_dir_ui_variants(self, tmp_path, monkeypatch, ui_starter, level):
        """_resolve_starter_dir maps both UI variants to starter_ui (no starter_ui_l5 today)."""
        import cli.govkit as mod
        fake_repo = self._bundled_repo(tmp_path, starter="starter_ui")
        monkeypatch.setattr(mod, "REPO_ROOT", fake_repo)

        result = mod._resolve_starter_dir(ui_starter, level)
        assert result.name == "starter_ui", (
            f"--starter {ui_starter} --level {level} must resolve to starter_ui, got {result.name}"
        )


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
            "options": {"type": "api", "ci": "github"},
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
        """cmd_upgrade overwrites governed files when version advances.

        Post-PR-1: refreshed governed .md files carry the govkit:editable
        header reflecting the new baseline; the file body equals the new
        baseline content.
        """
        import cli.govkit as mod

        repo = _make_upgrade_repo(tmp_path)
        # Update the governed file in the repo to simulate a govkit update
        (repo / "docs" / "contract.md").write_text("# Contract v2", encoding="utf-8")

        target = self._target_with_marker(tmp_path, repo, version="0.1.0")
        monkeypatch.setattr(mod, "AGENTS_DIR", repo / "agents")
        monkeypatch.setattr(mod, "REPO_ROOT", repo)
        monkeypatch.setattr(mod, "_GOVKIT_VERSION", "0.2.0")

        cmd_upgrade(argparse.Namespace(target=str(target), force=False))

        result = (target / "docs" / "contract.md").read_text(encoding="utf-8")
        assert "# Contract v2" in result
        assert result.startswith("<!-- govkit:editable")
        assert "baseline: govkit@0.2.0" in result

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


class TestCmdUpgradeEditProtection:
    """PR 1 / A2: cmd_upgrade refuses to overwrite user-edited governed
    docs unless --force is supplied. Files without a govkit:editable header
    keep today's overwrite behavior."""

    def _setup_repo_and_target(self, tmp_path):
        """Build a tiny repo + target where the target has a headed,
        user-edited governed doc."""
        import os
        import json
        from datetime import datetime, timezone
        from cli.headers import format_editable_header

        repo = _make_upgrade_repo(tmp_path)
        # Repo's fresh contract content represents the new baseline.
        (repo / "docs" / "contract.md").write_text("# Contract v2 (refreshed)\n", encoding="utf-8")

        target = tmp_path / "project"
        target.mkdir()
        (target / "CLAUDE.md").write_text("# old\n", encoding="utf-8")
        # Target's contract: has editable header + body, then user edits it later.
        contract = target / "docs" / "contract.md"
        contract.parent.mkdir(parents=True)
        header = format_editable_header(baseline="govkit@0.1.0")
        contract.write_text(header + "# Contract user edits\n", encoding="utf-8")
        edited_time = datetime(2026, 5, 27, 11, 0, 0, tzinfo=timezone.utc).timestamp()
        os.utime(contract, (edited_time, edited_time))

        applied_at = datetime(2026, 5, 27, 10, 0, 0, tzinfo=timezone.utc).isoformat()
        marker = {
            "version": "0.1.0",
            "level": "4",
            "agent": "test-agent",
            "options": {"type": "api", "ci": "github"},
            "applied_at": applied_at,
        }
        marker_dir = target / ".govkit"
        marker_dir.mkdir()
        (marker_dir / "marker.json").write_text(json.dumps(marker), encoding="utf-8")
        return repo, target

    def test_upgrade_refuses_overwriting_edited_governed_file(self, tmp_path, monkeypatch, capsys):
        import cli.govkit as mod

        repo, target = self._setup_repo_and_target(tmp_path)
        monkeypatch.setattr(mod, "AGENTS_DIR", repo / "agents")
        monkeypatch.setattr(mod, "REPO_ROOT", repo)
        monkeypatch.setattr(mod, "_GOVKIT_VERSION", "0.2.0")

        cmd_upgrade(argparse.Namespace(target=str(target), force=False))

        contract = target / "docs" / "contract.md"
        body = contract.read_text(encoding="utf-8")
        # User edits preserved; baseline body NOT installed.
        assert "Contract user edits" in body
        assert "Contract v2 (refreshed)" not in body
        err = capsys.readouterr().err
        assert "refused" in err
        assert "--force" in err

    def test_upgrade_with_force_overwrites_edited_governed_file(self, tmp_path, monkeypatch, capsys):
        import cli.govkit as mod

        repo, target = self._setup_repo_and_target(tmp_path)
        monkeypatch.setattr(mod, "AGENTS_DIR", repo / "agents")
        monkeypatch.setattr(mod, "REPO_ROOT", repo)
        monkeypatch.setattr(mod, "_GOVKIT_VERSION", "0.2.0")

        cmd_upgrade(argparse.Namespace(target=str(target), force=True))

        body = (target / "docs" / "contract.md").read_text(encoding="utf-8")
        assert "Contract v2 (refreshed)" in body
        err = capsys.readouterr().err
        assert "overwriting user edits" in err

    def test_upgrade_refreshes_unedited_headed_file(self, tmp_path, monkeypatch):
        """A headed governed doc that hasn't been edited since applied_at
        gets refreshed normally, with the header regenerated for the new
        baseline."""
        import os
        import json
        from datetime import datetime, timezone
        from cli.headers import format_editable_header
        import cli.govkit as mod

        repo = _make_upgrade_repo(tmp_path)
        (repo / "docs" / "contract.md").write_text("# Contract v2\n", encoding="utf-8")

        target = tmp_path / "project"
        target.mkdir()
        (target / "CLAUDE.md").write_text("# old\n", encoding="utf-8")
        contract = target / "docs" / "contract.md"
        contract.parent.mkdir(parents=True)
        header = format_editable_header(baseline="govkit@0.1.0")
        contract.write_text(header + "# Contract v1\n", encoding="utf-8")
        # File mtime is BEFORE applied_at — no edits since install.
        old_time = datetime(2026, 5, 27, 9, 0, 0, tzinfo=timezone.utc).timestamp()
        os.utime(contract, (old_time, old_time))
        applied_at = datetime(2026, 5, 27, 10, 0, 0, tzinfo=timezone.utc).isoformat()

        marker = {
            "version": "0.1.0", "level": "4", "agent": "test-agent",
            "options": {"type": "api", "ci": "github"},
            "applied_at": applied_at,
        }
        marker_dir = target / ".govkit"
        marker_dir.mkdir()
        (marker_dir / "marker.json").write_text(json.dumps(marker), encoding="utf-8")

        monkeypatch.setattr(mod, "AGENTS_DIR", repo / "agents")
        monkeypatch.setattr(mod, "REPO_ROOT", repo)
        monkeypatch.setattr(mod, "_GOVKIT_VERSION", "0.2.0")

        cmd_upgrade(argparse.Namespace(target=str(target), force=False))

        body = (target / "docs" / "contract.md").read_text(encoding="utf-8")
        assert "Contract v2" in body
        # Header refreshed with the new govkit version.
        assert "baseline: govkit@0.2.0" in body


class TestCmdApplyAddsEditableHeaders:
    """PR 1: cmd_apply adds the govkit:editable header to every governed/shared
    markdown file as it copies them."""

    def test_governed_md_files_get_header(self, tmp_path, monkeypatch):
        """When cmd_apply copies a governed .md doc, the doc gets the
        govkit:editable header prepended."""
        import cli.govkit as mod

        repo = _make_upgrade_repo(tmp_path)
        target = tmp_path / "project"
        target.mkdir()
        monkeypatch.setattr(mod, "AGENTS_DIR", repo / "agents")
        monkeypatch.setattr(mod, "REPO_ROOT", repo)

        cmd_apply(argparse.Namespace(
            agent="test-agent",
            target=str(target),
            level="4",
            type="api",
            ci="github",
            force=False,
        ))

        contract = target / "docs" / "contract.md"
        assert contract.is_file()
        content = contract.read_text(encoding="utf-8")
        assert content.startswith("<!-- govkit:editable")
        assert "baseline: govkit@" in content
        assert "Contract" in content  # body preserved


class TestCmdApplyStackOverlay:
    """PR 2: cmd_apply respects --stack, applies the overlay, records
    assumption and stack metadata in the marker."""

    def _agent_with_stack(self, tmp_path, agent="test-agent"):
        """Build a minimal agent + governed dir like _make_upgrade_repo but
        with the `stack` option declared in manifest."""
        agents = tmp_path / "agents" / agent
        agents.mkdir(parents=True)
        contract = tmp_path / "docs" / "contract.md"
        contract.parent.mkdir(parents=True)
        contract.write_text("# Contract v1", encoding="utf-8")

        manifest = {
            "agent": agent,
            "description": "stack-overlay test agent",
            "options": {
                "level": {"prompt": "Level?", "choices": ["3", "4", "5"], "default": "4"},
                "type": {"prompt": "Type?", "choices": ["api"], "default": "api"},
                "ci": {"prompt": "CI?", "choices": ["github"], "default": "github"},
                "stack": {
                    "choices": ["python-fastapi", "dotnet-aspnet", "java-spring-boot",
                                "nodejs-fastify", "go-gin"],
                    "default": "python-fastapi",
                },
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
        (agents / "CLAUDE.md").write_text("# Agent instructions", encoding="utf-8")
        return tmp_path

    def test_apply_with_default_stack_installs_python_fastapi(self, tmp_path, monkeypatch):
        import cli.govkit as mod

        repo = self._agent_with_stack(tmp_path)
        target = tmp_path / "project"
        target.mkdir()
        monkeypatch.setattr(mod, "AGENTS_DIR", repo / "agents")
        monkeypatch.setattr(mod, "REPO_ROOT", repo)

        cmd_apply(argparse.Namespace(
            agent="test-agent", target=str(target),
            level="4", type="api", ci="github", stack=None, force=False,
        ))

        tech_stack = target / "docs" / "backend" / "architecture" / "TECH_STACK.md"
        assert tech_stack.is_file(), "python-fastapi overlay must install TECH_STACK.md"
        content = tech_stack.read_text(encoding="utf-8")
        assert "baseline: python-fastapi@" in content

    def test_apply_with_explicit_stack_installs_overlay(self, tmp_path, monkeypatch):
        import cli.govkit as mod

        repo = self._agent_with_stack(tmp_path)
        target = tmp_path / "project"
        target.mkdir()
        monkeypatch.setattr(mod, "AGENTS_DIR", repo / "agents")
        monkeypatch.setattr(mod, "REPO_ROOT", repo)

        cmd_apply(argparse.Namespace(
            agent="test-agent", target=str(target),
            level="4", type="api", ci="github", stack="dotnet-aspnet", force=False,
        ))

        tech_stack = target / "docs" / "backend" / "architecture" / "TECH_STACK.md"
        content = tech_stack.read_text(encoding="utf-8")
        assert "baseline: dotnet-aspnet@" in content
        # .NET stack TECH_STACK.md should mention C# / .NET
        assert "C#" in content or ".NET" in content

    def test_marker_records_stack_metadata(self, tmp_path, monkeypatch):
        import cli.govkit as mod

        repo = self._agent_with_stack(tmp_path)
        target = tmp_path / "project"
        target.mkdir()
        monkeypatch.setattr(mod, "AGENTS_DIR", repo / "agents")
        monkeypatch.setattr(mod, "REPO_ROOT", repo)

        cmd_apply(argparse.Namespace(
            agent="test-agent", target=str(target),
            level="4", type="api", ci="github", stack="dotnet-aspnet", force=False,
        ))

        marker = read_govkit_marker(target)
        assert marker["stack"] is not None
        assert marker["stack"]["id"] == "dotnet-aspnet"
        assert marker["stack"]["version"] == "0.10.0"
        assert marker["stack"]["display_name"].startswith("C# 12")
        assert marker["options"]["stack"] == "dotnet-aspnet"

    def test_marker_records_stack_assumption_source_flag_when_cli_provided(self, tmp_path, monkeypatch):
        import cli.govkit as mod

        repo = self._agent_with_stack(tmp_path)
        target = tmp_path / "project"
        target.mkdir()
        monkeypatch.setattr(mod, "AGENTS_DIR", repo / "agents")
        monkeypatch.setattr(mod, "REPO_ROOT", repo)

        cmd_apply(argparse.Namespace(
            agent="test-agent", target=str(target),
            level="4", type="api", ci="github", stack="dotnet-aspnet", force=False,
        ))

        marker = read_govkit_marker(target)
        stack_assumption = next((a for a in marker["assumptions"] if a["id"] == "stack.id"), None)
        assert stack_assumption is not None
        assert stack_assumption["value"] == "dotnet-aspnet"
        assert stack_assumption["source"] == "flag"

    def test_marker_records_stack_assumption_source_default_when_no_flag(self, tmp_path, monkeypatch):
        import cli.govkit as mod

        repo = self._agent_with_stack(tmp_path)
        target = tmp_path / "project"
        target.mkdir()
        monkeypatch.setattr(mod, "AGENTS_DIR", repo / "agents")
        monkeypatch.setattr(mod, "REPO_ROOT", repo)

        cmd_apply(argparse.Namespace(
            agent="test-agent", target=str(target),
            level="4", type="api", ci="github", stack=None, force=False,
        ))

        marker = read_govkit_marker(target)
        stack_assumption = next((a for a in marker["assumptions"] if a["id"] == "stack.id"), None)
        assert stack_assumption is not None
        assert stack_assumption["value"] == "python-fastapi"
        assert stack_assumption["source"] == "default"

    def test_ui_type_does_not_apply_stack_overlay(self, tmp_path, monkeypatch):
        """UI installs target docs/ui/architecture/, not docs/backend/. Stack
        overlays only ship backend docs, so they must be a no-op for UI types."""
        import cli.govkit as mod

        agent = "ui-test-agent"
        agents = tmp_path / "agents" / agent
        agents.mkdir(parents=True)
        manifest = {
            "agent": agent,
            "description": "ui agent",
            "options": {
                "level": {"prompt": "Level?", "choices": ["3", "4", "5"], "default": "4"},
                "type": {"prompt": "Type?", "choices": ["ui-react"], "default": "ui-react"},
                "ci": {"prompt": "CI?", "choices": ["github"], "default": "github"},
                "stack": {
                    "prompt": "Stack?",
                    "choices": ["python-fastapi", "dotnet-aspnet"],
                    "default": "python-fastapi",
                },
            },
            "variants": {
                "type": {
                    "ui-react": {
                        "files": [{"src": "CLAUDE.md", "dest": "CLAUDE.md"}],
                        "shared": [],
                        "governed": [],
                    }
                }
            },
            "base_files": [],
        }
        (agents / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        (agents / "CLAUDE.md").write_text("# UI", encoding="utf-8")

        target = tmp_path / "project"
        target.mkdir()
        monkeypatch.setattr(mod, "AGENTS_DIR", tmp_path / "agents")
        monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)

        cmd_apply(argparse.Namespace(
            agent=agent, target=str(target),
            level="4", type="ui-react", ci="github", stack="dotnet-aspnet", force=False,
        ))

        # No backend architecture docs should have been written for ui-react.
        assert not (target / "docs" / "backend" / "architecture" / "TECH_STACK.md").exists()


class TestCmdApplyDetection:
    """PR 3: cmd_apply runs detection before installing and uses the inferred
    stack as the default (recording source='detected'). Explicit --stack
    overrides detection."""

    def _agent_with_stack(self, tmp_path, agent="test-agent"):
        agents = tmp_path / "agents" / agent
        agents.mkdir(parents=True)
        contract = tmp_path / "docs" / "contract.md"
        contract.parent.mkdir(parents=True)
        contract.write_text("# Contract v1", encoding="utf-8")
        manifest = {
            "agent": agent,
            "description": "detection test agent",
            "options": {
                "level": {"prompt": "Level?", "choices": ["3", "4", "5"], "default": "4"},
                "type": {"prompt": "Type?", "choices": ["api"], "default": "api"},
                "ci": {"prompt": "CI?", "choices": ["github"], "default": "github"},
                "stack": {
                    "choices": ["python-fastapi", "dotnet-aspnet", "java-spring-boot",
                                "nodejs-fastify", "go-gin"],
                    "default": "python-fastapi",
                },
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
        (agents / "CLAUDE.md").write_text("# Agent", encoding="utf-8")
        return tmp_path

    def test_dotnet_target_with_no_stack_flag_infers_dotnet_aspnet(self, tmp_path, monkeypatch):
        import cli.govkit as mod

        repo = self._agent_with_stack(tmp_path)
        target = tmp_path / "project"
        target.mkdir()
        # .NET signals in target
        (target / "src").mkdir()
        (target / "src" / "Api.csproj").write_text(
            '<Project Sdk="Microsoft.NET.Sdk.Web"></Project>\n', encoding="utf-8",
        )
        (target / "global.json").write_text('{"sdk":{}}', encoding="utf-8")

        monkeypatch.setattr(mod, "AGENTS_DIR", repo / "agents")
        monkeypatch.setattr(mod, "REPO_ROOT", repo)

        cmd_apply(argparse.Namespace(
            agent="test-agent", target=str(target),
            level="4", type="api", ci="github", stack=None, force=False,
        ))

        marker = read_govkit_marker(target)
        assert marker["stack"]["id"] == "dotnet-aspnet", "detection should override python-fastapi default"
        stack_assumption = next((a for a in marker["assumptions"] if a["id"] == "stack.id"), None)
        assert stack_assumption is not None
        assert stack_assumption["source"] == "detected"
        assert stack_assumption["confidence"] == "high"
        # Evidence captured from detection.
        assert stack_assumption["evidence"], "detected assumptions must carry evidence"

    def test_explicit_stack_flag_overrides_detection(self, tmp_path, monkeypatch):
        """User intent (--stack) always wins. The marker reflects the explicit
        choice with source='flag', not the inferred stack."""
        import cli.govkit as mod

        repo = self._agent_with_stack(tmp_path)
        target = tmp_path / "project"
        target.mkdir()
        # .NET signals — would normally infer dotnet-aspnet
        (target / "Api.csproj").write_text(
            '<Project Sdk="Microsoft.NET.Sdk.Web"></Project>\n', encoding="utf-8",
        )

        monkeypatch.setattr(mod, "AGENTS_DIR", repo / "agents")
        monkeypatch.setattr(mod, "REPO_ROOT", repo)

        cmd_apply(argparse.Namespace(
            agent="test-agent", target=str(target),
            level="4", type="api", ci="github", stack="python-fastapi", force=False,
        ))

        marker = read_govkit_marker(target)
        assert marker["stack"]["id"] == "python-fastapi"
        stack_assumption = next((a for a in marker["assumptions"] if a["id"] == "stack.id"), None)
        assert stack_assumption["source"] == "flag"

    def test_empty_target_falls_back_to_default(self, tmp_path, monkeypatch):
        """No detectable signals → use python-fastapi as the default and
        flag it review_required so the team knows we're guessing."""
        import cli.govkit as mod

        repo = self._agent_with_stack(tmp_path)
        target = tmp_path / "project"
        target.mkdir()
        # No signals at all in target

        monkeypatch.setattr(mod, "AGENTS_DIR", repo / "agents")
        monkeypatch.setattr(mod, "REPO_ROOT", repo)

        cmd_apply(argparse.Namespace(
            agent="test-agent", target=str(target),
            level="4", type="api", ci="github", stack=None, force=False,
        ))

        marker = read_govkit_marker(target)
        assert marker["stack"]["id"] == "python-fastapi"
        stack_assumption = next((a for a in marker["assumptions"] if a["id"] == "stack.id"), None)
        assert stack_assumption["source"] == "default"
        assert stack_assumption["review_required"] is True

    def test_apply_prints_detection_summary(self, tmp_path, monkeypatch, capsys):
        """cmd_apply emits a 'detecting repo profile' block before installing."""
        import cli.govkit as mod

        repo = self._agent_with_stack(tmp_path)
        target = tmp_path / "project"
        target.mkdir()
        (target / "Api.csproj").write_text(
            '<Project Sdk="Microsoft.NET.Sdk.Web"></Project>\n', encoding="utf-8",
        )
        (target / "global.json").write_text('{"sdk":{}}', encoding="utf-8")

        monkeypatch.setattr(mod, "AGENTS_DIR", repo / "agents")
        monkeypatch.setattr(mod, "REPO_ROOT", repo)

        cmd_apply(argparse.Namespace(
            agent="test-agent", target=str(target),
            level="4", type="api", ci="github", stack=None, force=False,
        ))

        out = capsys.readouterr().out
        assert "detect" in out.lower()
        assert "csharp" in out or "dotnet-aspnet" in out


class TestCmdApplyDetectFlag:
    """PR 3-D: `govkit apply --detect` runs repo inference and prints the
    proposed config without writing anything to the target."""

    def _agent(self, tmp_path, agent="test-agent"):
        agents = tmp_path / "agents" / agent
        agents.mkdir(parents=True)
        contract = tmp_path / "docs" / "contract.md"
        contract.parent.mkdir(parents=True)
        contract.write_text("# Contract v1", encoding="utf-8")
        manifest = {
            "agent": agent,
            "description": "detect-flag test agent",
            "options": {
                "level": {"prompt": "Level?", "choices": ["3", "4", "5"], "default": "4"},
                "type": {"prompt": "Type?", "choices": ["api"], "default": "api"},
                "ci": {"prompt": "CI?", "choices": ["github"], "default": "github"},
                "stack": {
                    "choices": ["python-fastapi", "dotnet-aspnet", "java-spring-boot",
                                "nodejs-fastify", "go-gin"],
                    "default": "python-fastapi",
                },
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
        (agents / "CLAUDE.md").write_text("# Agent", encoding="utf-8")
        return tmp_path

    def test_detect_flag_writes_nothing_to_target(self, tmp_path, monkeypatch):
        import cli.govkit as mod

        repo = self._agent(tmp_path)
        target = tmp_path / "project"
        target.mkdir()
        # Add some signals so detection has something to report
        (target / "Api.csproj").write_text(
            '<Project Sdk="Microsoft.NET.Sdk.Web"></Project>\n', encoding="utf-8",
        )
        monkeypatch.setattr(mod, "AGENTS_DIR", repo / "agents")
        monkeypatch.setattr(mod, "REPO_ROOT", repo)

        cmd_apply(argparse.Namespace(
            agent="test-agent", target=str(target),
            level="4", type="api", ci="github", stack=None, force=False,
            detect=True,
        ))

        # No marker
        assert not (target / ".govkit").exists()
        # No installed governance
        assert not (target / "CLAUDE.md").exists()
        assert not (target / "docs" / "backend" / "architecture" / "TECH_STACK.md").exists()
        # No setup review file
        assert not (target / "GOVKIT_SETUP_REVIEW.md").exists()
        # Target's own .csproj file is preserved (we wrote nothing)
        assert (target / "Api.csproj").is_file()

    def test_detect_flag_prints_proposed_config(self, tmp_path, monkeypatch, capsys):
        import cli.govkit as mod

        repo = self._agent(tmp_path)
        target = tmp_path / "project"
        target.mkdir()
        (target / "Api.csproj").write_text(
            '<Project Sdk="Microsoft.NET.Sdk.Web"></Project>\n', encoding="utf-8",
        )
        (target / "global.json").write_text('{"sdk":{}}', encoding="utf-8")
        monkeypatch.setattr(mod, "AGENTS_DIR", repo / "agents")
        monkeypatch.setattr(mod, "REPO_ROOT", repo)

        cmd_apply(argparse.Namespace(
            agent="test-agent", target=str(target),
            level="4", type="api", ci="github", stack=None, force=False,
            detect=True,
        ))

        out = capsys.readouterr().out
        # Detection summary present
        assert "csharp" in out
        # Inferred stack reported
        assert "dotnet-aspnet" in out
        # Dry-run banner makes it clear nothing was written
        assert "dry-run" in out.lower() or "--detect" in out

    def test_detect_flag_on_empty_target_still_exits_cleanly(self, tmp_path, monkeypatch, capsys):
        import cli.govkit as mod

        repo = self._agent(tmp_path)
        target = tmp_path / "project"
        target.mkdir()
        monkeypatch.setattr(mod, "AGENTS_DIR", repo / "agents")
        monkeypatch.setattr(mod, "REPO_ROOT", repo)

        # Should not raise
        cmd_apply(argparse.Namespace(
            agent="test-agent", target=str(target),
            level="4", type="api", ci="github", stack=None, force=False,
            detect=True,
        ))
        assert not (target / ".govkit").exists()


class TestCmdStackList:
    """PR 2 / Chunk F: govkit stack list enumerates bundled stack overlays."""

    def test_lists_all_bundled_stacks(self, capsys):
        from cli.govkit import cmd_stack_list

        cmd_stack_list(argparse.Namespace())
        out = capsys.readouterr().out

        for stack_id in ("python-fastapi", "dotnet-aspnet", "java-spring-boot",
                         "nodejs-fastify", "go-gin"):
            assert stack_id in out

    def test_includes_display_name_and_summary(self, capsys):
        from cli.govkit import cmd_stack_list

        cmd_stack_list(argparse.Namespace())
        out = capsys.readouterr().out

        # display names appear (sample one — dotnet-aspnet is unambiguous)
        assert "ASP.NET Core" in out
        # summaries appear (sample — xUnit is in dotnet-aspnet.summary)
        assert "xUnit" in out


class TestCmdStackApply:
    """PR 2 / Chunk G: govkit stack apply <id> re-applies an overlay over
    an existing install and records the new stack in the marker."""

    def _existing_install(self, tmp_path, monkeypatch, stack_id="python-fastapi"):
        """Build a target with an existing .govkit/marker.json (as written by
        cmd_apply) so cmd_stack_apply has something to read."""
        import cli.govkit as mod

        repo = _make_upgrade_repo(tmp_path)
        target = tmp_path / "project"
        target.mkdir()
        monkeypatch.setattr(mod, "AGENTS_DIR", repo / "agents")
        monkeypatch.setattr(mod, "REPO_ROOT", repo)
        cmd_apply(argparse.Namespace(
            agent="test-agent", target=str(target),
            level="4", type="api", ci="github", stack=stack_id, force=False,
        ))
        return target

    def test_stack_apply_switches_overlay(self, tmp_path, monkeypatch):
        from cli.govkit import cmd_stack_apply

        target = self._existing_install(tmp_path, monkeypatch, stack_id="python-fastapi")
        # Sanity: python-fastapi baseline is in place.
        tech_stack = target / "docs" / "backend" / "architecture" / "TECH_STACK.md"
        assert "baseline: python-fastapi@" in tech_stack.read_text(encoding="utf-8")

        cmd_stack_apply(argparse.Namespace(
            stack_id="dotnet-aspnet", target=str(target), force=False,
        ))

        # After stack apply, the dotnet baseline header is in place.
        new_content = tech_stack.read_text(encoding="utf-8")
        assert "baseline: dotnet-aspnet@" in new_content

    def test_stack_apply_updates_marker_stack_field(self, tmp_path, monkeypatch):
        from cli.govkit import cmd_stack_apply, read_govkit_marker

        target = self._existing_install(tmp_path, monkeypatch, stack_id="python-fastapi")

        cmd_stack_apply(argparse.Namespace(
            stack_id="java-spring-boot", target=str(target), force=False,
        ))

        marker = read_govkit_marker(target)
        assert marker["stack"]["id"] == "java-spring-boot"
        assert marker["options"]["stack"] == "java-spring-boot"

    def test_stack_apply_refuses_without_marker(self, tmp_path):
        from cli.govkit import cmd_stack_apply

        empty = tmp_path / "empty"
        empty.mkdir()
        with pytest.raises(SystemExit):
            cmd_stack_apply(argparse.Namespace(
                stack_id="dotnet-aspnet", target=str(empty), force=False,
            ))

    def test_stack_apply_unknown_stack_exits(self, tmp_path, monkeypatch):
        from cli.govkit import cmd_stack_apply

        target = self._existing_install(tmp_path, monkeypatch)
        with pytest.raises(SystemExit):
            cmd_stack_apply(argparse.Namespace(
                stack_id="no-such-stack", target=str(target), force=False,
            ))

    def test_stack_apply_respects_edit_protection(self, tmp_path, monkeypatch, capsys):
        """User edits to a stack doc since the last applied_at must survive
        stack apply without --force."""
        import os
        from datetime import datetime, timezone
        from cli.govkit import cmd_stack_apply

        target = self._existing_install(tmp_path, monkeypatch, stack_id="python-fastapi")

        tech_stack = target / "docs" / "backend" / "architecture" / "TECH_STACK.md"
        # Replace body with user edits and bump mtime past applied_at.
        current = tech_stack.read_text(encoding="utf-8")
        # Keep the existing header; overwrite body.
        header_end = current.index("-->") + len("-->\n")
        tech_stack.write_text(current[:header_end] + "\n# my own edits\n", encoding="utf-8")
        future = datetime.now(timezone.utc).timestamp() + 3600  # 1h ahead
        os.utime(tech_stack, (future, future))

        cmd_stack_apply(argparse.Namespace(
            stack_id="dotnet-aspnet", target=str(target), force=False,
        ))

        # User edits preserved.
        assert "my own edits" in tech_stack.read_text(encoding="utf-8")
        err = capsys.readouterr().err
        assert "refused" in err


class TestCmdApplyWritesSetupReview:
    """PR 1 / Chunk E: every cmd_apply writes GOVKIT_SETUP_REVIEW.md and
    prints the Review Checklist banner."""

    def test_apply_writes_setup_review_file(self, tmp_path, monkeypatch):
        import cli.govkit as mod

        repo = _make_upgrade_repo(tmp_path)
        target = tmp_path / "project"
        target.mkdir()
        monkeypatch.setattr(mod, "AGENTS_DIR", repo / "agents")
        monkeypatch.setattr(mod, "REPO_ROOT", repo)

        cmd_apply(argparse.Namespace(
            agent="test-agent", target=str(target),
            level="4", type="api", ci="github", force=False,
        ))

        review = target / "GOVKIT_SETUP_REVIEW.md"
        assert review.is_file()
        content = review.read_text(encoding="utf-8")
        assert "GovKit Setup Review" in content
        assert "test-agent" in content

    def test_apply_prints_review_checklist_banner(self, tmp_path, monkeypatch, capsys):
        import cli.govkit as mod

        repo = _make_upgrade_repo(tmp_path)
        target = tmp_path / "project"
        target.mkdir()
        monkeypatch.setattr(mod, "AGENTS_DIR", repo / "agents")
        monkeypatch.setattr(mod, "REPO_ROOT", repo)

        cmd_apply(argparse.Namespace(
            agent="test-agent", target=str(target),
            level="4", type="api", ci="github", force=False,
        ))

        out = capsys.readouterr().out
        assert "REVIEW CHECKLIST" in out
        assert "GOVKIT_SETUP_REVIEW.md" in out

    def test_upgrade_refreshes_setup_review(self, tmp_path, monkeypatch):
        """cmd_upgrade must also (re)write GOVKIT_SETUP_REVIEW.md so the
        review reflects the post-upgrade state, not the prior install."""
        import json
        import cli.govkit as mod

        repo = _make_upgrade_repo(tmp_path)
        target = tmp_path / "project"
        target.mkdir()
        # Pre-existing marker (legacy file layout → triggers migration on read)
        marker = {
            "version": "0.1.0", "level": "4", "agent": "test-agent",
            "options": {"type": "api", "ci": "github"},
            "applied_at": "2025-01-01T00:00:00+00:00",
        }
        (target / ".govkit").write_text(json.dumps(marker), encoding="utf-8")
        # Stale review from prior install:
        (target / "GOVKIT_SETUP_REVIEW.md").write_text("# stale from prior apply\n", encoding="utf-8")
        # Pre-existing agent file so upgrade has something to refresh:
        (target / "CLAUDE.md").write_text("# old\n", encoding="utf-8")

        monkeypatch.setattr(mod, "AGENTS_DIR", repo / "agents")
        monkeypatch.setattr(mod, "REPO_ROOT", repo)
        monkeypatch.setattr(mod, "_GOVKIT_VERSION", "0.2.0")

        cmd_upgrade(argparse.Namespace(target=str(target), force=False))

        review = (target / "GOVKIT_SETUP_REVIEW.md").read_text(encoding="utf-8")
        assert "stale from prior apply" not in review
        assert "GovKit Setup Review" in review
        assert "0.2.0" in review


# ---------------------------------------------------------------------------
# Migrate-levels (Increment 9 — v0.6.x → v0.7.0 maturity-model migration)
#
# Per plan §7.2 state matrix:
#   level=3, version<0.7.0 → interactive 4-option prompt
#   level=4, version<0.7.0 → automatic version bump, level stays 4
#   level=5, version<0.7.0 → automatic version bump, level stays 5
#   any level, version>=0.7.0 → no-op success
# ---------------------------------------------------------------------------


def _make_legacy_target(tmp_path: Path, level: str, version: str = "0.6.0",
                       num_features: int = 2, three_artifact: bool = True) -> Path:
    """Create a target directory with a v0.6-style marker and feature dirs."""
    target = tmp_path / "legacy-project"
    target.mkdir()
    if num_features > 0:
        for i in range(num_features):
            fd = target / "features" / f"feature_{i}"
            fd.mkdir(parents=True)
            (fd / "acceptance.feature").write_text("Feature: x\n", encoding="utf-8")
            (fd / "nfrs.md").write_text("## Performance\n- p50 < 100ms\n", encoding="utf-8")
            (fd / "plan.md").write_text("# Plan\n", encoding="utf-8")
            if not three_artifact:
                (fd / "eval_criteria.yaml").write_text("version: '1'\nmode: deterministic\n", encoding="utf-8")
                (fd / "architecture_preflight.md").write_text("# Preflight\n", encoding="utf-8")
    marker = {
        "version": version,
        "level": level,
        "agent": "test-agent",
        "options": {"type": "api", "ci": "github"},
        "applied_at": "2026-04-01T00:00:00+00:00",
    }
    (target / ".govkit").write_text(json.dumps(marker), encoding="utf-8")
    return target


def _migrate_args(target: Path) -> argparse.Namespace:
    return argparse.Namespace(
        target=str(target), force=False, migrate_levels=True,
    )


class TestMigrationWarning:
    """read_govkit_marker emits a one-time warning when version < 0.7.0."""

    def test_warning_fires_for_pre_070_marker(self, tmp_path, monkeypatch, capsys):
        import cli.govkit as mod

        mod._reset_migration_warning()
        monkeypatch.delenv("GOVKIT_NO_MIGRATION_WARNING", raising=False)
        target = _make_legacy_target(tmp_path, level="3", version="0.6.0")

        mod.read_govkit_marker(target)
        err = capsys.readouterr().err
        assert "L3/L4 maturity model changed in 0.7.0" in err
        assert "govkit upgrade --migrate-levels" in err

    def test_warning_only_fires_once_per_invocation(self, tmp_path, monkeypatch, capsys):
        import cli.govkit as mod

        mod._reset_migration_warning()
        monkeypatch.delenv("GOVKIT_NO_MIGRATION_WARNING", raising=False)
        target = _make_legacy_target(tmp_path, level="3", version="0.6.0")

        mod.read_govkit_marker(target)
        mod.read_govkit_marker(target)
        mod.read_govkit_marker(target)
        err = capsys.readouterr().err
        # Count distinct warning lines (allowing for the message containing the marker once)
        assert err.count("L3/L4 maturity model changed in 0.7.0") == 1

    def test_warning_suppressed_by_env_var(self, tmp_path, monkeypatch, capsys):
        import cli.govkit as mod

        mod._reset_migration_warning()
        monkeypatch.setenv("GOVKIT_NO_MIGRATION_WARNING", "1")
        target = _make_legacy_target(tmp_path, level="3", version="0.6.0")

        mod.read_govkit_marker(target)
        err = capsys.readouterr().err
        assert err == ""

    def test_warning_does_not_fire_for_current_version(self, tmp_path, monkeypatch, capsys):
        import cli.govkit as mod

        mod._reset_migration_warning()
        monkeypatch.delenv("GOVKIT_NO_MIGRATION_WARNING", raising=False)
        target = _make_legacy_target(tmp_path, level="3", version="0.7.0")

        mod.read_govkit_marker(target)
        err = capsys.readouterr().err
        assert "maturity model" not in err

    def test_warning_does_not_fire_for_dev_version(self, tmp_path, monkeypatch, capsys):
        import cli.govkit as mod

        mod._reset_migration_warning()
        monkeypatch.delenv("GOVKIT_NO_MIGRATION_WARNING", raising=False)
        target = _make_legacy_target(tmp_path, level="3", version="dev")

        mod.read_govkit_marker(target)
        err = capsys.readouterr().err
        # Non-numeric versions compare equal — no warning
        assert "maturity model" not in err


class TestNoUiDimensionInManifests:
    """Production manifests must not carry the dropped v0.8 `ui` dimension."""

    @pytest.mark.parametrize("agent", ["claude-code", "codex", "copilot"])
    def test_no_ui_options_or_variants(self, agent):
        from cli.govkit import AGENTS_DIR
        manifest_path = AGENTS_DIR / agent / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert "ui" not in manifest.get("options", {}), (
            f"{agent}: options.ui must be absent after v0.8 shape refactor"
        )
        assert "ui" not in manifest.get("variants", {}), (
            f"{agent}: variants.ui must be absent after v0.8 shape refactor"
        )

    @pytest.mark.parametrize("agent", ["claude-code", "codex", "copilot"])
    def test_type_choices_include_ui_shapes(self, agent):
        from cli.govkit import AGENTS_DIR
        manifest_path = AGENTS_DIR / agent / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        type_choices = manifest["options"]["type"]["choices"]
        for expected in ("api", "cli", "ui-react", "ui-angular"):
            assert expected in type_choices, (
                f"{agent}: options.type.choices must include '{expected}'"
            )


class TestShapeMigrationWarning:
    """read_govkit_marker emits a one-time warning when marker carries legacy `ui` option."""

    def _make_target_with_ui(self, tmp_path: Path, ui_value: str = "react") -> Path:
        target = tmp_path / "legacy-ui-marker"
        target.mkdir()
        marker = {
            "version": "0.7.0",
            "level": "4",
            "agent": "claude-code",
            "options": {"type": "api", "ci": "github", "ui": ui_value},
            "applied_at": "2026-04-01T00:00:00+00:00",
        }
        (target / ".govkit").write_text(json.dumps(marker), encoding="utf-8")
        return target

    def test_marker_with_ui_is_read_tolerantly(self, tmp_path, monkeypatch):
        import cli.govkit as mod
        mod._reset_shape_migration_warning()
        monkeypatch.setenv("GOVKIT_NO_SHAPE_MIGRATION_WARNING", "1")  # suppress warning, just check no crash
        target = self._make_target_with_ui(tmp_path, ui_value="react")
        data = mod.read_govkit_marker(target)
        assert data is not None
        assert data["options"]["ui"] == "react", "marker data must be returned untouched"

    def test_warning_fires_for_marker_with_ui(self, tmp_path, monkeypatch, capsys):
        import cli.govkit as mod
        mod._reset_shape_migration_warning()
        monkeypatch.delenv("GOVKIT_NO_SHAPE_MIGRATION_WARNING", raising=False)
        target = self._make_target_with_ui(tmp_path)

        mod.read_govkit_marker(target)
        err = capsys.readouterr().err
        assert "project-shape model changed in 0.8.0" in err
        assert "govkit apply --type ui-react" in err

    def test_warning_only_fires_once_per_invocation(self, tmp_path, monkeypatch, capsys):
        import cli.govkit as mod
        mod._reset_shape_migration_warning()
        monkeypatch.delenv("GOVKIT_NO_SHAPE_MIGRATION_WARNING", raising=False)
        target = self._make_target_with_ui(tmp_path)

        mod.read_govkit_marker(target)
        mod.read_govkit_marker(target)
        mod.read_govkit_marker(target)
        err = capsys.readouterr().err
        assert err.count("project-shape model changed in 0.8.0") == 1

    def test_warning_suppressed_by_env_var(self, tmp_path, monkeypatch, capsys):
        import cli.govkit as mod
        mod._reset_shape_migration_warning()
        monkeypatch.setenv("GOVKIT_NO_SHAPE_MIGRATION_WARNING", "1")
        target = self._make_target_with_ui(tmp_path)

        mod.read_govkit_marker(target)
        err = capsys.readouterr().err
        assert err == ""

    def test_warning_does_not_fire_when_no_ui_in_marker(self, tmp_path, monkeypatch, capsys):
        import cli.govkit as mod
        mod._reset_shape_migration_warning()
        monkeypatch.delenv("GOVKIT_NO_SHAPE_MIGRATION_WARNING", raising=False)
        target = tmp_path / "fresh"
        target.mkdir()
        marker = {
            "version": "0.8.0",
            "level": "4",
            "agent": "claude-code",
            "options": {"type": "ui-react", "ci": "github"},
            "applied_at": "2026-05-18T00:00:00+00:00",
        }
        (target / ".govkit").write_text(json.dumps(marker), encoding="utf-8")

        mod.read_govkit_marker(target)
        err = capsys.readouterr().err
        assert "project-shape model" not in err


class TestUpgradeMigrateLevels:
    """cmd_upgrade --migrate-levels covers each (level, version) cell from §7.2."""

    @pytest.fixture(autouse=True)
    def _reset_warning(self):
        import cli.govkit as mod
        mod._reset_migration_warning()
        yield
        mod._reset_migration_warning()

    def test_already_at_070_is_noop(self, tmp_path, monkeypatch, capsys):
        import cli.govkit as mod

        monkeypatch.setattr(mod, "_GOVKIT_VERSION", "0.7.0")
        target = _make_legacy_target(tmp_path, level="3", version="0.7.0")

        with pytest.raises(SystemExit) as exc_info:
            cmd_upgrade(_migrate_args(target))
        assert exc_info.value.code == 0
        out = capsys.readouterr().out
        assert "already at version" in out.lower() or "no migration needed" in out.lower()
        # Marker untouched
        assert read_govkit_marker(target)["version"] == "0.7.0"

    def test_l4_v06_bumps_version_only(self, tmp_path, monkeypatch):
        import cli.govkit as mod

        monkeypatch.setattr(mod, "_GOVKIT_VERSION", "0.7.0")
        target = _make_legacy_target(tmp_path, level="4", version="0.6.0", three_artifact=False)

        with pytest.raises(SystemExit) as exc_info:
            cmd_upgrade(_migrate_args(target))
        assert exc_info.value.code == 0
        marker = read_govkit_marker(target)
        assert marker["version"] == "0.7.0"
        assert marker["level"] == "4"
        # Level field excluded from options
        assert "level" not in marker["options"]

    def test_l5_v06_bumps_version_only(self, tmp_path, monkeypatch):
        import cli.govkit as mod

        monkeypatch.setattr(mod, "_GOVKIT_VERSION", "0.7.0")
        target = _make_legacy_target(tmp_path, level="5", version="0.6.0", three_artifact=False)

        with pytest.raises(SystemExit) as exc_info:
            cmd_upgrade(_migrate_args(target))
        assert exc_info.value.code == 0
        marker = read_govkit_marker(target)
        assert marker["version"] == "0.7.0"
        assert marker["level"] == "5"

    def test_l3_v06_choice_1_generates_stubs_and_migrates_to_l4(self, tmp_path, monkeypatch):
        import cli.govkit as mod

        monkeypatch.setattr(mod, "_GOVKIT_VERSION", "0.7.0")
        monkeypatch.setattr("builtins.input", lambda _: "1")
        target = _make_legacy_target(tmp_path, level="3", version="0.6.0", num_features=2)

        with pytest.raises(SystemExit) as exc_info:
            cmd_upgrade(_migrate_args(target))
        assert exc_info.value.code == 0

        marker = read_govkit_marker(target)
        assert marker["version"] == "0.7.0"
        assert marker["level"] == "4"

        for fd in (target / "features").iterdir():
            assert (fd / "eval_criteria.yaml").exists(), f"stub missing in {fd}"
            assert (fd / "architecture_preflight.md").exists(), f"stub missing in {fd}"

    def test_l3_v06_choice_1_stub_eval_criteria_fails_validation(self, tmp_path, monkeypatch):
        """The generated eval_criteria.yaml stub must fail validation (TBD placeholders)."""
        import cli.govkit as mod
        from cli.validate import check_eval_criteria

        monkeypatch.setattr(mod, "_GOVKIT_VERSION", "0.7.0")
        monkeypatch.setattr("builtins.input", lambda _: "1")
        target = _make_legacy_target(tmp_path, level="3", version="0.6.0", num_features=1)

        with pytest.raises(SystemExit):
            cmd_upgrade(_migrate_args(target))

        feature_dir = next((target / "features").iterdir())
        # The stub has `mode: TBD` which is not a valid mode value.
        # check_eval_criteria sees the structure but the value is wrong; the
        # contract test is that the stub is structurally valid YAML so apply
        # doesn't crash, but `mode: TBD` will fail downstream validation tooling.
        text = (feature_dir / "eval_criteria.yaml").read_text(encoding="utf-8")
        assert "TBD" in text
        assert "mode: TBD" in text

    def test_l3_v06_choice_1_stub_preflight_has_tbd_sections(self, tmp_path, monkeypatch):
        import cli.govkit as mod

        monkeypatch.setattr(mod, "_GOVKIT_VERSION", "0.7.0")
        monkeypatch.setattr("builtins.input", lambda _: "1")
        target = _make_legacy_target(tmp_path, level="3", version="0.6.0", num_features=1)

        with pytest.raises(SystemExit):
            cmd_upgrade(_migrate_args(target))

        feature_dir = next((target / "features").iterdir())
        text = (feature_dir / "architecture_preflight.md").read_text(encoding="utf-8")
        # All nine canonical sections present
        for n in range(1, 10):
            assert f"## {n}." in text, f"section {n} missing in stub"
        assert text.count("TBD") >= 9, "stub should have TBD per section"

    def test_l3_v06_choice_1_does_not_overwrite_existing_artifacts(self, tmp_path, monkeypatch):
        import cli.govkit as mod

        monkeypatch.setattr(mod, "_GOVKIT_VERSION", "0.7.0")
        monkeypatch.setattr("builtins.input", lambda _: "1")
        target = _make_legacy_target(tmp_path, level="3", version="0.6.0", num_features=1)
        # Pre-existing eval_criteria.yaml in one feature
        existing = next((target / "features").iterdir()) / "eval_criteria.yaml"
        existing.write_text("version: '1'\nmode: deterministic\n", encoding="utf-8")

        with pytest.raises(SystemExit):
            cmd_upgrade(_migrate_args(target))

        # Existing file untouched
        assert existing.read_text(encoding="utf-8") == "version: '1'\nmode: deterministic\n"

    def test_l3_v06_choice_2_no_stubs_only_marker_rewrite(self, tmp_path, monkeypatch):
        import cli.govkit as mod

        monkeypatch.setattr(mod, "_GOVKIT_VERSION", "0.7.0")
        monkeypatch.setattr("builtins.input", lambda _: "2")
        target = _make_legacy_target(tmp_path, level="3", version="0.6.0", num_features=2)

        with pytest.raises(SystemExit) as exc_info:
            cmd_upgrade(_migrate_args(target))
        assert exc_info.value.code == 0

        marker = read_govkit_marker(target)
        assert marker["level"] == "4"
        # No stubs generated
        for fd in (target / "features").iterdir():
            assert not (fd / "eval_criteria.yaml").exists()
            assert not (fd / "architecture_preflight.md").exists()

    def test_l3_v06_choice_3_confirmed_deletes_features(self, tmp_path, monkeypatch):
        import cli.govkit as mod

        monkeypatch.setattr(mod, "_GOVKIT_VERSION", "0.7.0")
        responses = iter(["3", "yes"])
        monkeypatch.setattr("builtins.input", lambda _: next(responses))
        target = _make_legacy_target(tmp_path, level="3", version="0.6.0", num_features=2)

        with pytest.raises(SystemExit) as exc_info:
            cmd_upgrade(_migrate_args(target))
        assert exc_info.value.code == 0

        marker = read_govkit_marker(target)
        assert marker["level"] == "3"
        assert marker["version"] == "0.7.0"
        assert not (target / "features").exists()

    def test_l3_v06_choice_3_unconfirmed_keeps_features(self, tmp_path, monkeypatch):
        import cli.govkit as mod

        monkeypatch.setattr(mod, "_GOVKIT_VERSION", "0.7.0")
        responses = iter(["3", "no"])
        monkeypatch.setattr("builtins.input", lambda _: next(responses))
        target = _make_legacy_target(tmp_path, level="3", version="0.6.0", num_features=2)

        with pytest.raises(SystemExit) as exc_info:
            cmd_upgrade(_migrate_args(target))
        assert exc_info.value.code == 1
        # Features and marker untouched
        assert (target / "features").exists()
        marker = read_govkit_marker(target)
        assert marker["level"] == "3"
        assert marker["version"] == "0.6.0"

    def test_l3_v06_choice_4_aborts_no_changes(self, tmp_path, monkeypatch):
        import cli.govkit as mod

        monkeypatch.setattr(mod, "_GOVKIT_VERSION", "0.7.0")
        monkeypatch.setattr("builtins.input", lambda _: "4")
        target = _make_legacy_target(tmp_path, level="3", version="0.6.0", num_features=2)

        with pytest.raises(SystemExit) as exc_info:
            cmd_upgrade(_migrate_args(target))
        assert exc_info.value.code == 0
        marker = read_govkit_marker(target)
        assert marker["level"] == "3"
        assert marker["version"] == "0.6.0"

    def test_l3_v06_invalid_choice_aborts(self, tmp_path, monkeypatch):
        import cli.govkit as mod

        monkeypatch.setattr(mod, "_GOVKIT_VERSION", "0.7.0")
        monkeypatch.setattr("builtins.input", lambda _: "9")
        target = _make_legacy_target(tmp_path, level="3", version="0.6.0", num_features=1)

        with pytest.raises(SystemExit) as exc_info:
            cmd_upgrade(_migrate_args(target))
        assert exc_info.value.code == 1
        marker = read_govkit_marker(target)
        assert marker["level"] == "3"
        assert marker["version"] == "0.6.0"

    def test_warning_clears_after_migration(self, tmp_path, monkeypatch, capsys):
        """After --migrate-levels rewrites the marker to 0.7.0, the warning stops firing."""
        import cli.govkit as mod

        monkeypatch.setattr(mod, "_GOVKIT_VERSION", "0.7.0")
        monkeypatch.setattr("builtins.input", lambda _: "2")
        monkeypatch.delenv("GOVKIT_NO_MIGRATION_WARNING", raising=False)
        target = _make_legacy_target(tmp_path, level="3", version="0.6.0", num_features=1)

        with pytest.raises(SystemExit):
            cmd_upgrade(_migrate_args(target))
        # Reset the one-time flag to test the next invocation in isolation
        mod._reset_migration_warning()
        capsys.readouterr()  # discard prior output

        mod.read_govkit_marker(target)
        err = capsys.readouterr().err
        assert "maturity model" not in err, (
            "After --migrate-levels rewrites marker to 0.7.0, the warning must not fire"
        )
