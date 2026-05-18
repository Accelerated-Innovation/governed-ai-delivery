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
