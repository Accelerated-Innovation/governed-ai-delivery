"""Tests for stack-overlaid agent rules (hardening plan Increment 9).

A stack overlay may ship `rules:` that replace the type-default rule set for
the overlapping entries — databricks-lakehouse ships medallion-worded layer
rules (bronze/silver/gold) while python-dbt keeps the dbt defaults.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
STACK_DIR = REPO_ROOT / "cli" / "stacks" / "databricks-lakehouse"


def _apply(target: Path, agent: str, stack: str) -> None:
    from cli.cmd_apply import cmd_apply

    cmd_apply(
        argparse.Namespace(
            agent=agent,
            target=str(target),
            level="4",
            type="data",
            ci="github",
            stack=stack,
            force=False,
            detect=False,
        )
    )


class TestApplyRuleOverrides:
    def _overlay(self, tmp_path, rules):
        from cli.overlay import Overlay

        root = tmp_path / "stack"
        root.mkdir(exist_ok=True)
        return Overlay(
            id="test-stack",
            root=root,
            version="0.1.0",
            display_name="Test",
            summary="",
            rules=rules,
        )

    def test_replaces_matching_entry_and_points_at_overlay(self, tmp_path):
        from cli.overlay import apply_rule_overrides

        overlay = self._overlay(
            tmp_path,
            [
                {
                    "agent": "claude-code",
                    "src": "rules/bronze.md",
                    "dest": ".claude/rules/govkit/staging.md",
                    "replaces": "rules/data/staging.md",
                }
            ],
        )
        (overlay.root / "rules").mkdir()
        (overlay.root / "rules" / "bronze.md").write_text("# Bronze\n", encoding="utf-8")

        files = [
            {"src": "rules/data/staging.md", "dest": ".claude/rules/govkit/staging.md"},
            {"src": "rules/data/pii.md", "dest": ".claude/rules/govkit/pii.md"},
        ]
        out = apply_rule_overrides(files, overlay, "claude-code")

        srcs = [e["src"] for e in out]
        assert "rules/data/staging.md" not in srcs
        assert "rules/data/pii.md" in srcs
        override = next(e for e in out if e["src"] == "rules/bronze.md")
        assert override["src_root"] == str(overlay.root)
        assert override["dest"] == ".claude/rules/govkit/staging.md"

    def test_missing_overlay_source_keeps_type_default(self, tmp_path):
        from cli.overlay import apply_rule_overrides

        overlay = self._overlay(
            tmp_path,
            [
                {
                    "agent": "claude-code",
                    "src": "rules/not-there.md",
                    "dest": ".claude/rules/govkit/staging.md",
                    "replaces": "rules/data/staging.md",
                }
            ],
        )
        files = [{"src": "rules/data/staging.md", "dest": ".claude/rules/govkit/staging.md"}]

        out = apply_rule_overrides(files, overlay, "claude-code")
        assert out == files

    def test_other_agents_entries_are_ignored(self, tmp_path):
        from cli.overlay import apply_rule_overrides

        overlay = self._overlay(
            tmp_path,
            [
                {
                    "agent": "codex",
                    "src": "rules/bronze.md",
                    "dest": ".agents/rules/bronze.md",
                }
            ],
        )
        files = [{"src": "rules/data/staging.md", "dest": ".claude/rules/govkit/staging.md"}]

        assert apply_rule_overrides(files, overlay, "claude-code") == files

    def test_no_overlay_or_no_rules_is_noop(self, tmp_path):
        from cli.overlay import apply_rule_overrides

        files = [{"src": "a", "dest": "b"}]
        assert apply_rule_overrides(files, None, "claude-code") == files
        assert apply_rule_overrides(files, self._overlay(tmp_path, []), "claude-code") == files


class TestMedallionSourcesParity:
    LAYERS = ("bronze", "silver", "gold")

    def _body(self, text: str) -> str:
        if text.startswith("---"):
            return text.split("---", 2)[2].lstrip("\n")
        return text

    @pytest.mark.parametrize("layer", LAYERS)
    def test_bodies_identical_across_agents(self, layer):
        texts = {
            "claude-code": (STACK_DIR / "rules" / "claude-code" / f"{layer}.md").read_text(
                encoding="utf-8"
            ),
            "copilot": (STACK_DIR / "rules" / "copilot" / f"{layer}.instructions.md").read_text(
                encoding="utf-8"
            ),
            "codex": (STACK_DIR / "rules" / "codex" / f"{layer}.md").read_text(encoding="utf-8"),
        }
        bodies = {agent: self._body(t) for agent, t in texts.items()}
        assert bodies["claude-code"] == bodies["copilot"] == bodies["codex"]

    @pytest.mark.parametrize("layer", LAYERS)
    def test_bodies_are_medallion_not_dbt_worded(self, layer):
        body = (STACK_DIR / "rules" / "codex" / f"{layer}.md").read_text(encoding="utf-8")
        assert "{{ source(" not in body
        assert "stg_<source>" not in body


class TestDataInstallStackRules:
    def test_databricks_claude_rules_are_medallion(self, tmp_path):
        target = tmp_path / "p"
        target.mkdir()
        _apply(target, "claude-code", "databricks-lakehouse")

        staging = (target / ".claude" / "rules" / "govkit" / "staging.md").read_text(
            encoding="utf-8"
        )
        assert "Bronze Layer" in staging
        assert "{{ source(" not in staging
        assert "**/bronze/**" in staging
        marts = (target / ".claude" / "rules" / "govkit" / "marts.md").read_text(encoding="utf-8")
        assert "Gold Layer" in marts

    def test_databricks_codex_rules_are_plain_files_not_nested_blocks(self, tmp_path):
        target = tmp_path / "p"
        target.mkdir()
        _apply(target, "codex", "databricks-lakehouse")

        assert (target / ".agents" / "rules" / "bronze.md").is_file()
        assert (target / ".agents" / "rules" / "gold.md").is_file()
        # The dbt-specific nested AGENTS.md blocks must not be created in a
        # medallion repo (there is no models/ tree to scope them to).
        assert not (target / "models").exists()

    def test_databricks_copilot_rules_are_medallion(self, tmp_path):
        target = tmp_path / "p"
        target.mkdir()
        _apply(target, "copilot", "databricks-lakehouse")

        staging = (
            target / ".github" / "instructions" / "govkit" / "staging.instructions.md"
        ).read_text(encoding="utf-8")
        assert "Bronze Layer" in staging
        assert "applyTo" in staging

    def test_python_dbt_rules_stay_dbt_worded(self, tmp_path):
        target = tmp_path / "p"
        target.mkdir()
        _apply(target, "claude-code", "python-dbt")

        staging = (target / ".claude" / "rules" / "govkit" / "staging.md").read_text(
            encoding="utf-8"
        )
        assert "{{ source(" in staging
        assert "Bronze" not in staging


class TestStackApplySwapsRules:
    def test_swap_to_databricks_and_back(self, tmp_path):
        from cli.cmd_stack import cmd_stack_apply

        target = tmp_path / "p"
        target.mkdir()
        _apply(target, "claude-code", "python-dbt")
        staging = target / ".claude" / "rules" / "govkit" / "staging.md"
        assert "{{ source(" in staging.read_text(encoding="utf-8")

        cmd_stack_apply(
            argparse.Namespace(
                stack_id="databricks-lakehouse",
                target=str(target),
                force=False,
            )
        )
        assert "Bronze Layer" in staging.read_text(encoding="utf-8")

        cmd_stack_apply(
            argparse.Namespace(
                stack_id="python-dbt",
                target=str(target),
                force=False,
            )
        )
        text = staging.read_text(encoding="utf-8")
        assert "{{ source(" in text
        assert "Bronze Layer" not in text


class TestMedallionGlobsResolve:
    def test_doctor_d001_clean_when_bronze_dirs_exist(self, tmp_path):
        from cli.doctor import run_doctor

        target = tmp_path / "p"
        target.mkdir()
        for layer in ("bronze", "silver", "gold"):
            (target / "src" / layer).mkdir(parents=True)
        _apply(target, "claude-code", "databricks-lakehouse")

        findings = run_doctor(target)
        d001 = [f for f in findings if f.id == "D001" and "bronze" in f.message]
        assert d001 == [], [f.message for f in d001]

    def test_doctor_d001_flags_missing_medallion_dirs(self, tmp_path):
        from cli.doctor import run_doctor

        target = tmp_path / "p"
        target.mkdir()
        _apply(target, "claude-code", "databricks-lakehouse")

        findings = run_doctor(target)
        assert any(f.id == "D001" and "bronze" in f.message for f in findings)
