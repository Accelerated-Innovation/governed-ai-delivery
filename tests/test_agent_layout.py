"""Tests for cli/agent_layout.py — the single owner of per-agent on-disk layout.

AGENT_LAYOUT_REFACTOR_PLAN.md increment 1. One frozen dataclass + one table
replaces the four private copies of these facts that previously lived in
calibrate.py, setup_review.py, doctor.py, and rule_templating.py.
"""

import dataclasses

import pytest


class TestAgentLayoutTable:
    def test_all_three_production_agents_present(self):
        from cli.agent_layout import AGENT_LAYOUTS

        assert set(AGENT_LAYOUTS) == {"claude-code", "copilot", "codex"}

    def test_claude_code_layout(self):
        from cli.agent_layout import AGENT_LAYOUTS

        layout = AGENT_LAYOUTS["claude-code"]
        assert layout.instruction_file == "CLAUDE.md"
        assert layout.rules_dir == ".claude/rules"
        assert layout.rules_glob == ".claude/rules/*.md"
        assert layout.frontmatter_glob_key == "paths"
        assert layout.glob_value_shape == "list"

    def test_copilot_layout(self):
        from cli.agent_layout import AGENT_LAYOUTS

        layout = AGENT_LAYOUTS["copilot"]
        assert layout.instruction_file == ".github/copilot-instructions.md"
        assert layout.rules_dir == ".github/instructions"
        assert layout.rules_glob == ".github/instructions/*.instructions.md"
        assert layout.frontmatter_glob_key == "applyTo"
        assert layout.glob_value_shape == "comma-string"

    def test_codex_has_no_glob_scoped_rules(self):
        """Codex places nested AGENTS.md files instead of a glob-scoped rules
        dir. Its absence is one typed None, not per-consumer sentinel strings."""
        from cli.agent_layout import AGENT_LAYOUTS

        layout = AGENT_LAYOUTS["codex"]
        assert layout.instruction_file == "AGENTS.md"
        assert layout.rules_dir is None
        assert layout.rules_glob is None
        assert layout.frontmatter_glob_key is None
        assert layout.glob_value_shape is None

    def test_layout_is_frozen(self):
        from cli.agent_layout import AGENT_LAYOUTS

        with pytest.raises(dataclasses.FrozenInstanceError):
            AGENT_LAYOUTS["claude-code"].rules_dir = "elsewhere"


class TestBundleParity:
    def test_layout_keys_match_bundled_agents(self):
        """Every bundled agent (a dir under agents/ with a manifest.json) has a
        layout row, and every layout row has a bundled agent. A fourth agent
        cannot be added to one without the other."""
        from cli import paths
        from cli.agent_layout import AGENT_LAYOUTS

        bundled = {
            d.name
            for d in paths.AGENTS_DIR.iterdir()
            if d.is_dir() and (d / "manifest.json").is_file()
        }
        assert set(AGENT_LAYOUTS) == bundled
