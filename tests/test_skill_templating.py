"""Tests for cli/skill_templating.py — install-time {{docs_area}} expansion.

Increment 5 of the data-enforcement hardening plan: skill sources reference
docs/{{docs_area}}/... instead of hardcoding docs/backend/, and the token is
expanded at install time from skill_context (agents cannot resolve it at
runtime). Degradation mirrors rule templating: an unresolvable token is left
in the text for doctor to flag, never guessed.
"""

import pytest


class TestExpandSkillTokens:
    def test_replaces_docs_area_token(self):
        from cli.skill_templating import expand_skill_tokens

        text = "Read docs/{{docs_area}}/architecture/BOUNDARIES.md first."
        out = expand_skill_tokens(text, "data")
        assert out == "Read docs/data/architecture/BOUNDARIES.md first."

    def test_replaces_every_occurrence(self):
        from cli.skill_templating import expand_skill_tokens

        text = "docs/{{docs_area}}/architecture/ and docs/{{docs_area}}/evaluation/"
        out = expand_skill_tokens(text, "backend")
        assert out == "docs/backend/architecture/ and docs/backend/evaluation/"

    def test_empty_docs_area_leaves_token_in_place(self):
        from cli.skill_templating import expand_skill_tokens

        text = "Read docs/{{docs_area}}/architecture/."
        assert expand_skill_tokens(text, "") == text

    def test_unknown_tokens_are_left_untouched(self):
        from cli.skill_templating import expand_skill_tokens

        text = "docs/{{docs_area}}/x and {{other_token}} stays"
        out = expand_skill_tokens(text, "ui")
        assert "docs/ui/x" in out
        assert "{{other_token}}" in out

    def test_text_without_tokens_unchanged(self):
        from cli.skill_templating import expand_skill_tokens

        assert expand_skill_tokens("plain text\n", "backend") == "plain text\n"


AGENT_SKILLS_DIRS = [
    ("claude-code", ".claude/skills"),
    ("codex", ".agents/skills"),
    ("copilot", ".github/skills"),
]


class TestAgentLayoutSkillsDir:
    def test_layouts_declare_skills_dirs(self):
        from cli.agent_layout import AGENT_LAYOUTS

        for agent, skills_dir in AGENT_SKILLS_DIRS:
            assert AGENT_LAYOUTS[agent].skills_dir == skills_dir


class TestTemplateInstalledSkills:
    def _install_skill(self, target, skills_dir, name="govkit-spec-planning"):
        d = target / skills_dir / name
        d.mkdir(parents=True, exist_ok=True)
        f = d / "SKILL.md"
        f.write_text(
            "---\nname: govkit-spec-planning\ndescription: plan a spec\n---\n"
            "Read docs/{{docs_area}}/architecture/BOUNDARIES.md\n",
            encoding="utf-8",
        )
        return f

    @pytest.mark.parametrize("agent,skills_dir", AGENT_SKILLS_DIRS)
    def test_rewrites_installed_skill_files(self, tmp_path, agent, skills_dir):
        from cli.skill_templating import template_installed_skills

        f = self._install_skill(tmp_path, skills_dir)
        count = template_installed_skills(tmp_path, agent, "data")

        assert count == 1
        text = f.read_text(encoding="utf-8")
        assert "docs/data/architecture/BOUNDARIES.md" in text
        assert "{{docs_area}}" not in text

    def test_empty_docs_area_is_noop(self, tmp_path):
        from cli.skill_templating import template_installed_skills

        f = self._install_skill(tmp_path, ".claude/skills")
        count = template_installed_skills(tmp_path, "claude-code", "")

        assert count == 0
        assert "{{docs_area}}" in f.read_text(encoding="utf-8")

    def test_unknown_agent_is_noop(self, tmp_path):
        from cli.skill_templating import template_installed_skills

        self._install_skill(tmp_path, ".claude/skills")
        assert template_installed_skills(tmp_path, "custom-agent", "data") == 0

    def test_missing_skills_dir_is_noop(self, tmp_path):
        from cli.skill_templating import template_installed_skills

        assert template_installed_skills(tmp_path, "claude-code", "data") == 0

    def test_files_without_tokens_are_not_counted(self, tmp_path):
        from cli.skill_templating import template_installed_skills

        d = tmp_path / ".claude" / "skills" / "govkit-adr-author"
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text("---\nname: x\n---\nNo tokens here.\n", encoding="utf-8")

        assert template_installed_skills(tmp_path, "claude-code", "data") == 0


# The four backend skill sources that install for non-backend types (data L4
# installs all of them). L5-only skills keep literal docs/backend/ — their
# extension contract paths are backend-real, and data has no L5.
TOKENIZED_SKILLS = [
    "adr-author",
    "spec-planning",
    "architecture-preflight",
    "implementation-plan",
]


class TestSkillSourcesTokenized:
    @pytest.mark.parametrize("agent", ["claude-code", "codex", "copilot"])
    def test_planning_skill_sources_carry_token_not_literal(self, agent):
        """Source-level parity guard: the tokenized skills must reference
        docs/{{docs_area}}/ in every agent, never a hardcoded docs/backend/."""
        from cli import paths

        for skill in TOKENIZED_SKILLS:
            src = paths.AGENTS_DIR / agent / "skills" / "backend" / skill / "SKILL.md"
            text = src.read_text(encoding="utf-8")
            assert "docs/backend/" not in text, (agent, skill)
            assert "{{docs_area}}" in text, (agent, skill)


class TestPiiKeywordTemplating:
    """Increment 10: the PII keyword list lives in skill_context, and rule
    bodies carry {{pii_keywords}} rendered at install time."""

    def test_render_pii_keywords(self):
        from cli.skill_templating import render_pii_keywords

        assert render_pii_keywords(["email", "ssn"]) == "`email`, `ssn`"

    def test_expands_token_in_rules_dir(self, tmp_path):
        from cli.skill_templating import template_installed_rule_bodies

        rule = tmp_path / ".claude" / "rules" / "govkit" / "staging.md"
        rule.parent.mkdir(parents=True)
        rule.write_text("PII list ({{pii_keywords}}) MUST be tagged\n", encoding="utf-8")

        count = template_installed_rule_bodies(tmp_path, "claude-code", ["email", "dob"])

        assert count == 1
        text = rule.read_text(encoding="utf-8")
        assert "`email`, `dob`" in text
        assert "{{pii_keywords}}" not in text

    def test_expands_codex_nested_blocks_and_plain_rules(self, tmp_path):
        from cli.skill_templating import template_installed_rule_bodies

        nested = tmp_path / "models" / "staging" / "AGENTS.md"
        nested.parent.mkdir(parents=True)
        nested.write_text("list ({{pii_keywords}})\n", encoding="utf-8")
        plain = tmp_path / ".agents" / "rules" / "bronze.md"
        plain.parent.mkdir(parents=True)
        plain.write_text("list ({{pii_keywords}})\n", encoding="utf-8")

        count = template_installed_rule_bodies(tmp_path, "codex", ["email"])

        assert count == 2
        assert "`email`" in nested.read_text(encoding="utf-8")
        assert "`email`" in plain.read_text(encoding="utf-8")

    def test_empty_keyword_list_leaves_token(self, tmp_path):
        from cli.skill_templating import template_installed_rule_bodies

        rule = tmp_path / ".claude" / "rules" / "govkit" / "staging.md"
        rule.parent.mkdir(parents=True)
        rule.write_text("({{pii_keywords}})\n", encoding="utf-8")

        assert template_installed_rule_bodies(tmp_path, "claude-code", []) == 0
        assert "{{pii_keywords}}" in rule.read_text(encoding="utf-8")

    @pytest.mark.parametrize(
        "src",
        [
            "agents/claude-code/rules/data/staging.md",
            "agents/codex/rules/data/staging.md",
            "agents/copilot/instructions/data/staging.instructions.md",
        ],
    )
    def test_staging_sources_carry_token_not_literal_list(self, src):
        from cli import paths

        text = (paths.REPO_ROOT / src).read_text(encoding="utf-8")
        assert "{{pii_keywords}}" in text
        assert "`ssn`,\n`dob`" not in text

    def test_data_install_renders_pii_list_claude(self, tmp_path):
        import argparse

        from cli.cmd_apply import cmd_apply

        target = tmp_path / "p"
        target.mkdir()
        cmd_apply(
            argparse.Namespace(
                agent="claude-code",
                target=str(target),
                level="4",
                type="data",
                ci="github",
                stack="python-dbt",
                force=False,
                detect=False,
            )
        )

        staging = (target / ".claude" / "rules" / "govkit" / "staging.md").read_text(
            encoding="utf-8"
        )
        assert "`email`, `phone`, `ssn`, `dob`, `birth`, `address`, `name`" in staging
        assert "{{pii_keywords}}" not in staging

    def test_data_install_renders_pii_list_codex_nested_block(self, tmp_path):
        import argparse

        from cli.cmd_apply import cmd_apply

        target = tmp_path / "p"
        target.mkdir()
        cmd_apply(
            argparse.Namespace(
                agent="codex",
                target=str(target),
                level="4",
                type="data",
                ci="github",
                stack="python-dbt",
                force=False,
                detect=False,
            )
        )

        nested = (target / "models" / "staging" / "AGENTS.md").read_text(encoding="utf-8")
        assert "`email`, `phone`, `ssn`" in nested
        assert "{{pii_keywords}}" not in nested


class TestApplyExpandsSkillDocsArea:
    @pytest.mark.parametrize("agent,skills_dir", AGENT_SKILLS_DIRS)
    def test_data_install_skills_cite_data_docs(self, tmp_path, agent, skills_dir):
        """The increment's guard: after apply --type data, no installed skill
        file contains the literal docs/backend/ and no token survives."""
        import argparse

        from cli.cmd_apply import cmd_apply

        target = tmp_path / "project"
        target.mkdir()
        cmd_apply(
            argparse.Namespace(
                agent=agent,
                target=str(target),
                level="4",
                type="data",
                ci="github",
                stack="databricks-lakehouse",
                force=False,
                detect=False,
            )
        )

        skill_files = sorted((target / skills_dir).rglob("*.md"))
        assert skill_files
        joined = ""
        for f in skill_files:
            text = f.read_text(encoding="utf-8")
            assert "docs/backend/" not in text, f
            assert "{{docs_area}}" not in text, f
            joined += text
        assert "docs/data/architecture" in joined

    def test_api_install_skills_still_cite_backend_docs(self, tmp_path):
        import argparse

        from cli.cmd_apply import cmd_apply

        target = tmp_path / "project"
        target.mkdir()
        cmd_apply(
            argparse.Namespace(
                agent="claude-code",
                target=str(target),
                level="4",
                type="api",
                ci="github",
                stack="python-fastapi",
                force=False,
                detect=False,
            )
        )

        spec = target / ".claude" / "skills" / "govkit-spec-planning" / "SKILL.md"
        text = spec.read_text(encoding="utf-8")
        assert "docs/backend/architecture" in text
        assert "{{docs_area}}" not in text


class TestPiiKeywordReRendering:
    """Tuning `pii.keyword_list` must reach the rule bodies seeded from it.

    The list is documented as team-tunable and is preserved across rewrites,
    but the rendering was one-way: the first install consumed
    `{{pii_keywords}}`, leaving nothing for a later pass to re-render from.

    `apply` and `upgrade` were unaffected — they re-copy each rule from the
    bundle, which restores the token before re-expanding. `calibrate` does
    not re-copy, so it silently kept the original defaults. Calibrating is
    exactly when a team would tune the list.
    """

    def test_rendering_is_repeatable(self):
        from cli.skill_templating import expand_pii_keywords

        source = "PII list ({{pii_keywords}}) MUST be tagged\n"
        first = expand_pii_keywords(source, ["email", "dob"])
        assert "`email`, `dob`" in first

        second = expand_pii_keywords(first, ["email", "iban", "national_id"])
        assert "`email`, `iban`, `national_id`" in second
        assert "`dob`" not in second, "the previous rendering was not replaced"
        assert "MUST be tagged" in second

    def test_re_rendering_is_idempotent(self):
        from cli.skill_templating import expand_pii_keywords

        once = expand_pii_keywords("list ({{pii_keywords}})\n", ["email"])
        twice = expand_pii_keywords(once, ["email"])
        assert once == twice

    def test_installed_bodies_re_render_from_a_tuned_list(self, tmp_path):
        from cli.skill_templating import template_installed_rule_bodies

        rule = tmp_path / ".claude" / "rules" / "govkit" / "staging.md"
        rule.parent.mkdir(parents=True)
        rule.write_text("PII list ({{pii_keywords}}) MUST be tagged\n", encoding="utf-8")

        template_installed_rule_bodies(tmp_path, "claude-code", ["email", "dob"])
        count = template_installed_rule_bodies(tmp_path, "claude-code", ["email", "iban"])

        assert count == 1, "second pass found nothing to re-render"
        text = rule.read_text(encoding="utf-8")
        assert "`email`, `iban`" in text
        assert "`dob`" not in text

    def test_calibrate_re_renders_after_the_list_is_tuned(self, tmp_path):
        """End-to-end: the case from the issue."""
        import argparse

        import yaml

        from cli.calibrate import cmd_calibrate
        from cli.cmd_apply import cmd_apply

        target = tmp_path / "project"
        target.mkdir()
        cmd_apply(argparse.Namespace(
            agent="claude-code", target=str(target), level="4", type="data",
            ci="github", stack=None, force=False, detect=False,
        ))
        rule = target / ".claude" / "rules" / "govkit" / "staging.md"
        assert "`phone`" in rule.read_text(encoding="utf-8")

        context = target / ".govkit" / "skill_context.yaml"
        data = yaml.safe_load(context.read_text(encoding="utf-8"))
        data["pii"]["keyword_list"] = ["email", "iban", "national_id"]
        context.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

        cmd_calibrate(argparse.Namespace(
            target=str(target), non_interactive=True, only=None,
        ))

        text = rule.read_text(encoding="utf-8")
        assert "`email`, `iban`, `national_id`" in text
        assert "`phone`" not in text, "rule body kept the pre-tuning defaults"
