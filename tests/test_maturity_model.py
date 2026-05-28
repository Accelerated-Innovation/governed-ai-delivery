"""
Increment 0 of the L3/L4 maturity-model swap (plan: plans/MATURITY_MODEL_L3_L4_SWAP_PLAN.md).

These tests lock in the v0.7.0 target behavior:
  L3 = Governed AI Delivery (Foundations) — agent rules + architecture docs only;
       no features/ directory; govkit init errors; govkit validate is a no-op.
  L4 = Spec-Driven Add-On — adds features/ + 5-artifact contract on top of L3
       via merge-mode manifest semantics.
  L5 = GenAI Operations — unchanged content; replace-mode preserved.

Most of these tests FAIL against the current v0.6.x code. A few are regression
guards (already-passing behaviors we want to preserve through the refactor); they
are kept here alongside the failing ones so the file documents the full target
contract in one place. See §8.1 of the plan for the inventory.
"""

import argparse
import json
import textwrap
from pathlib import Path

import pytest

from cli import paths, validate
from cli.cmd_apply import cmd_apply
from cli.cmd_init import _resolve_starter_dir, cmd_init
from cli.manifest import resolve_variant_files
from cli.marker import write_govkit_marker

# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")


VALID_FEATURE = """\
    Feature: Sample feature

      @nfr-performance
      Scenario: Fast
        Given a request
        When processed
        Then fast

      @nfr-security
      Scenario: Secure
        Given auth
        When request
        Then ok
"""

VALID_NFRS = """\
    ## Performance
    - Response time < 200ms

    ## Security
    - Auth required
"""

VALID_EVAL_CRITERIA = """\
    version: "1"
    mode: deterministic
    criteria:
      - name: output_structure
        type: structure_validator
"""

VALID_PLAN = """\
    # Plan

    ```yaml
    evaluation_prediction:
      first:
        average: 4.6
      virtues:
        average: 4.4
    ```
"""


def _make_l4_feature(feature_dir: Path) -> None:
    """Create a complete 5-artifact feature dir (the new-L4 / current-L4 shape)."""
    feature_dir.mkdir(parents=True, exist_ok=True)
    _write(feature_dir / "acceptance.feature", VALID_FEATURE)
    _write(feature_dir / "nfrs.md", VALID_NFRS)
    _write(feature_dir / "eval_criteria.yaml", VALID_EVAL_CRITERIA)
    _write(feature_dir / "plan.md", VALID_PLAN)
    _write(feature_dir / "architecture_preflight.md", "# Architecture Preflight\nAll checks passed.\n")


def _make_fake_agent(repo_root: Path, *, manifest: dict, agent: str = "claude-code") -> Path:
    """Write a minimal agents/<agent>/manifest.json under repo_root and return repo_root."""
    agent_dir = repo_root / "agents" / agent
    agent_dir.mkdir(parents=True, exist_ok=True)
    (agent_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return repo_root


def _apply_args(target: Path, **overrides) -> argparse.Namespace:
    defaults = dict(
        agent="claude-code",
        target=str(target),
        level=None,
        type="api",
        ci="github",
    )
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


# ---------------------------------------------------------------------------
# 1-3: Level labels
# ---------------------------------------------------------------------------


class TestLevelLabels:
    """level_labels in run_validation must match the new naming."""

    def _run_with_one_feature(self, tmp_path: Path, level: str, capsys):
        features = tmp_path / "features"
        feature_dir = features / "demo"
        _make_l4_feature(feature_dir)
        validate.run_validation(tmp_path, level=level)
        return capsys.readouterr().out

    def test_l3_label_is_governed_ai_delivery_foundations(self, tmp_path, capsys):
        out = self._run_with_one_feature(tmp_path, "3", capsys)
        assert "Governed AI Delivery (Foundations)" in out, (
            "L3 label must read 'Governed AI Delivery (Foundations)'; "
            "got output:\n" + out
        )

    def test_l4_label_is_spec_driven_addon(self, tmp_path, capsys):
        out = self._run_with_one_feature(tmp_path, "4", capsys)
        assert "Spec-Driven Add-On" in out, (
            "L4 label must read 'Spec-Driven Add-On'; got output:\n" + out
        )

    def test_l5_label_unchanged(self, tmp_path, capsys):
        # Regression guard: L5 keeps "GenAI Operations".
        out = self._run_with_one_feature(tmp_path, "5", capsys)
        assert "GenAI Operations" in out, (
            "L5 label must remain 'GenAI Operations'; got output:\n" + out
        )


# ---------------------------------------------------------------------------
# 4: Default level is 3
# ---------------------------------------------------------------------------


class TestDefaultLevelIsThree:
    """The default maturity level (no flag, no marker) is 3 in v0.7.0."""

    @pytest.mark.parametrize("agent", ["claude-code", "copilot", "codex"])
    def test_manifest_default_level_is_3(self, agent):
        manifest_path = paths.AGENTS_DIR / agent / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["options"]["level"]["default"] == "3", (
            f"{agent} manifest options.level.default must be '3'; "
            f"got {manifest['options']['level']['default']!r}"
        )

    def test_run_validation_no_marker_defaults_to_l3(self, tmp_path, capsys):
        # With no marker, no explicit level: should default to L3 → no-op success.
        # Today defaults to "4" and would error because features/ is absent.
        (tmp_path / "features").mkdir()  # present but empty
        result = validate.run_validation(tmp_path, level=None)
        out = capsys.readouterr().out
        assert result == 0
        assert "Foundations" in out or "Level 3" in out or "L3" in out, (
            "Default-level run should announce L3 / Foundations; got:\n" + out
        )


# ---------------------------------------------------------------------------
# 5-6: cmd_apply features/ behavior per level
# ---------------------------------------------------------------------------


class TestApplyFeaturesDirBehavior:
    """govkit apply must create features/ at L4+ but not at L3."""

    def _minimal_repo(self, tmp_path: Path) -> Path:
        manifest = {
            "agent": "claude-code",
            "description": "Test agent",
            "options": {
                "level": {"prompt": "Level?", "choices": ["3", "4", "5"], "default": "3"},
                "type": {"prompt": "Type?", "choices": ["api"], "default": "api"},
                "ci": {"prompt": "CI?", "choices": ["github"], "default": "github"},
            },
            "variants": {
                "type": {"api": {"files": [], "shared": [], "governed": []}},
                "ci": {"github": {"files": [], "shared": [], "governed": []}},
            },
            "base_files": [],
        }
        return _make_fake_agent(tmp_path, manifest=manifest)

    def test_l3_apply_does_not_create_features_dir(self, tmp_path, monkeypatch):
        repo = self._minimal_repo(tmp_path)
        target = tmp_path / "target"
        target.mkdir()
        monkeypatch.setattr(paths, "AGENTS_DIR", repo / "agents")
        monkeypatch.setattr(paths, "REPO_ROOT", repo)

        cmd_apply(_apply_args(target, level="3"))

        assert not (target / "features").exists(), (
            "At L3 (Foundations), govkit apply must NOT create features/."
        )

    def test_l4_apply_creates_empty_features_dir(self, tmp_path, monkeypatch):
        # Regression guard: L4 still creates features/ (current behavior, must persist).
        repo = self._minimal_repo(tmp_path)
        target = tmp_path / "target"
        target.mkdir()
        monkeypatch.setattr(paths, "AGENTS_DIR", repo / "agents")
        monkeypatch.setattr(paths, "REPO_ROOT", repo)

        cmd_apply(_apply_args(target, level="4"))

        features = target / "features"
        assert features.is_dir(), "At L4, govkit apply must create features/."
        assert list(features.iterdir()) == [], (
            "features/ must be empty after apply; starters are scaffolded by `govkit init`."
        )


# ---------------------------------------------------------------------------
# 7 + 15: govkit init at L3 errors helpfully (and never resolves a starter)
# ---------------------------------------------------------------------------


class TestInitErrorsAtL3:
    """govkit init at L3 must error with a helpful message pointing to L4."""

    def test_l3_init_errors_helpfully(self, tmp_path, capsys):
        # Today: init succeeds at L3 (uses the L3 simpler starter).
        # After refactor: init at L3 must exit non-zero with a Level 4 hint.
        target = tmp_path / "project"
        (target / "features").mkdir(parents=True)  # so today's "no features/" check passes
        write_govkit_marker(target, "claude-code", "3", {"type": "api"})

        with pytest.raises(SystemExit) as exc_info:
            cmd_init(argparse.Namespace(
                feature="my-feat",
                target=str(target),
                level="3",
                starter="backend",
            ))

        assert exc_info.value.code != 0
        out = capsys.readouterr().out + capsys.readouterr().err
        assert "Level 4" in out or "level 4" in out or "--level 4" in out, (
            "L3 init error must mention Level 4 as the path forward; got:\n" + out
        )

    def test_resolve_starter_dir_l3_raises(self):
        # _resolve_starter_dir must not silently produce a directory at L3.
        # Either it raises ValueError or cmd_init never calls it; this asserts
        # the function-level contract.
        with pytest.raises(ValueError, match=r"L3"):
            _resolve_starter_dir("backend", "3")


# ---------------------------------------------------------------------------
# 8-9: validate is a no-op at L3
# ---------------------------------------------------------------------------


class TestValidateNoOpAtL3:
    """govkit validate at L3 must return 0 regardless of features/ state."""

    def test_l3_validate_returns_zero_with_no_features(self, tmp_path, capsys):
        # Today: errors with exit 1 because features/ is absent.
        # After: returns 0 with informational message.
        result = validate.run_validation(tmp_path, level="3")
        assert result == 0, (
            "At L3, run_validation must return 0 even when features/ is absent."
        )

    def test_l3_validate_returns_zero_with_broken_features(self, tmp_path):
        # Even if features/ exists with broken artifacts, L3 doesn't validate them.
        features = tmp_path / "features" / "broken"
        features.mkdir(parents=True)
        (features / "acceptance.feature").write_text("not gherkin", encoding="utf-8")

        result = validate.run_validation(tmp_path, level="3")
        assert result == 0, (
            "At L3, run_validation must not validate per-feature artifacts."
        )


# ---------------------------------------------------------------------------
# 10: L4 validate runs the full governed checks (regression guard)
# ---------------------------------------------------------------------------


class TestL4FullValidation:
    """L4 must continue to enforce the 5-artifact governed contract."""

    def test_l4_complete_feature_passes(self, tmp_path):
        _make_l4_feature(tmp_path / "features" / "demo")
        result = validate.run_validation(tmp_path, level="4")
        assert result == 0

    def test_l4_missing_artifact_fails(self, tmp_path):
        feature_dir = tmp_path / "features" / "demo"
        _make_l4_feature(feature_dir)
        (feature_dir / "eval_criteria.yaml").unlink()
        result = validate.run_validation(tmp_path, level="4")
        assert result == 1


# ---------------------------------------------------------------------------
# 11-14: Manifest merge / replace semantics
# ---------------------------------------------------------------------------


class TestManifestMergeSemantics:
    """level_4 blocks merge additively; level_5 keeps replace semantics."""

    def test_manifest_l4_merge_appends_files(self):
        # New behavior: level_4.files appends to base files at level=4.
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
        assert "base.md" in srcs, "L4 must keep the L3 base entries (merge, not replace)."
        assert "addon.md" in srcs, "L4 must add level_4 entries on top of base."

    def test_manifest_l4_merge_dest_collision_later_wins(self):
        # When a level_4 entry collides on dest with a base entry, level_4 wins.
        manifest = {
            "variants": {
                "type": {
                    "api": {
                        "files": [{"src": "l3-claude.md", "dest": "CLAUDE.md"}],
                        "level_4": {
                            "mode": "merge",
                            "files": [{"src": "l4-claude.md", "dest": "CLAUDE.md"}],
                        },
                    }
                }
            }
        }
        files, _, _ = resolve_variant_files(manifest, {"type": "api", "level": "4"})
        claude_entries = [f for f in files if f["dest"] == "CLAUDE.md"]
        assert len(claude_entries) == 1, (
            "Merge-mode collision on dest must yield exactly one entry; "
            f"got {len(claude_entries)}: {claude_entries}"
        )
        assert claude_entries[0]["src"] == "l4-claude.md", (
            "Later (level_4) entry must win on dest collision."
        )

    def test_manifest_l3_no_override_uses_top_level(self):
        # Regression guard: if no level_3 key exists, level=3 uses top-level entries.
        manifest = {
            "variants": {
                "type": {
                    "api": {
                        "files": [{"src": "base.md", "dest": "BASE.md"}],
                    }
                }
            }
        }
        files, _, _ = resolve_variant_files(manifest, {"type": "api", "level": "3"})
        srcs = [f["src"] for f in files]
        assert srcs == ["base.md"]

    def test_manifest_l5_still_replaces(self):
        # Regression guard: level_5 must keep replace semantics.
        manifest = {
            "variants": {
                "type": {
                    "api": {
                        "files": [{"src": "base.md", "dest": "BASE.md"}],
                        "level_5": {
                            "mode": "replace",
                            "files": [{"src": "l5.md", "dest": "L5.md"}],
                        },
                    }
                }
            }
        }
        files, _, _ = resolve_variant_files(manifest, {"type": "api", "level": "5"})
        srcs = [f["src"] for f in files]
        assert "base.md" not in srcs, (
            "Replace-mode L5 must drop the L3 base entries."
        )
        assert srcs == ["l5.md"]
