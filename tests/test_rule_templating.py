"""Tests for cli/rule_templating.py — apply-time expansion of `paths_template`
frontmatter into concrete `paths:` globs using SkillContext layers.

PR 6b. Rule files in the source tree may declare `paths_template: layers.<key>`
to defer their glob list until install time, when govkit knows which
architecture style the team uses. This avoids the D001 false-positive
where a rule scoped to `**/adapters/**` produces no matches in a
Clean Architecture repo using `Infrastructure/`.
"""

import yaml


def _parsed_paths(text: str) -> list[str]:
    """Return the `paths:` list from a rule file's frontmatter, quote-agnostic."""
    assert text.startswith("---"), f"no frontmatter in: {text!r}"
    end = text.find("\n---", 3)
    assert end != -1, f"unterminated frontmatter in: {text!r}"
    fm = yaml.safe_load(text[3:end]) or {}
    return fm.get("paths") or []


class TestExpandRuleTemplate:
    def test_no_change_when_no_template_key(self):
        """Files without `paths_template:` come through unchanged."""
        from cli.rule_templating import expand_rule_template

        text = (
            "---\n"
            "paths:\n"
            '  - "**/security/**"\n'
            "---\n"
            "\n# Security rule body\n"
        )
        layers = {"inbound": ["api/"], "outbound": ["adapters/"], "domain": ["services/"]}
        assert expand_rule_template(text, layers) == text

    def test_expands_paths_template_to_paths_block(self):
        """`paths_template: layers.inbound` becomes a `paths:` list of
        `**/<hint>/**` globs for each hint in layers.inbound."""
        from cli.rule_templating import expand_rule_template

        text = (
            "---\n"
            "paths_template: layers.inbound\n"
            "---\n"
            "\n# Inbound rule body\n"
        )
        layers = {
            "inbound":  ["api/", "Controllers/"],
            "outbound": ["adapters/", "Infrastructure/"],
            "domain":   ["services/", "Application/"],
        }
        out = expand_rule_template(text, layers)
        assert "paths_template:" not in out
        paths = _parsed_paths(out)
        assert "**/api/**" in paths
        assert "**/Controllers/**" in paths
        # Body preserved
        assert "Inbound rule body" in out

    def test_template_with_no_matching_layer_keeps_existing_paths(self):
        """If `paths_template: layers.foo` references an unknown layer key,
        we leave the file unchanged so the fallback `paths:` (if any) still
        scopes the rule. Doctor's D001 then surfaces the real problem."""
        from cli.rule_templating import expand_rule_template

        text = (
            "---\n"
            "paths_template: layers.unknown-key\n"
            "paths:\n"
            '  - "**/fallback/**"\n'
            "---\n"
        )
        layers = {"inbound": ["api/"]}
        out = expand_rule_template(text, layers)
        # Fallback survives (template directive removed so it's not re-processed).
        assert "**/fallback/**" in _parsed_paths(out)
        assert "paths_template:" not in out

    def test_template_with_empty_layer_keeps_existing_paths(self):
        """`paths_template: layers.inbound` when layers.inbound is [] should
        leave the original frontmatter intact (degrades gracefully on
        'unknown' architecture style where _STYLE_LAYERS has empty lists)."""
        from cli.rule_templating import expand_rule_template

        text = (
            "---\n"
            "paths_template: layers.inbound\n"
            "paths:\n"
            '  - "**/api/**"\n'
            "---\n"
        )
        layers = {"inbound": [], "outbound": [], "domain": []}
        out = expand_rule_template(text, layers)
        # Fallback paths survive when the template resolves to nothing.
        assert "**/api/**" in _parsed_paths(out)
        # Template directive removed so apply doesn't re-process it.
        assert "paths_template:" not in out

    def test_replaces_existing_paths_when_template_resolves(self):
        """When the template resolves to non-empty values, the new paths
        REPLACE the old (fallback) paths."""
        from cli.rule_templating import expand_rule_template

        text = (
            "---\n"
            "paths_template: layers.outbound\n"
            "paths:\n"
            '  - "**/adapters/**"\n'
            "---\n"
        )
        layers = {"outbound": ["Infrastructure/", "Repositories/"]}
        out = expand_rule_template(text, layers)
        paths = _parsed_paths(out)
        assert "**/Infrastructure/**" in paths
        assert "**/Repositories/**" in paths
        # Old hexagonal default is gone — it was the fallback.
        assert "**/adapters/**" not in paths

    def test_file_without_frontmatter_returns_unchanged(self):
        from cli.rule_templating import expand_rule_template

        text = "# Just a markdown doc\n\nNo frontmatter here.\n"
        assert expand_rule_template(text, {"inbound": ["api/"]}) == text

    def test_empty_input_returns_empty(self):
        from cli.rule_templating import expand_rule_template

        assert expand_rule_template("", {}) == ""

    def test_copilot_applyto_template_expands_to_comma_string(self):
        """Copilot rules use `applyTo:` (single string with comma-separated
        globs), not `paths:` (list). The templating helper handles both."""
        from cli.rule_templating import expand_rule_template

        text = (
            "---\n"
            "applyTo_template: layers.inbound\n"
            "---\n"
            "# Inbound rule body\n"
        )
        layers = {"inbound": ["api/", "Controllers/"]}
        out = expand_rule_template(text, layers)
        assert "applyTo_template:" not in out
        # applyTo is a single string with comma-separated globs.
        fm = yaml.safe_load(out.split("---", 2)[1])
        assert "applyTo" in fm
        assert "**/api/**" in fm["applyTo"]
        assert "**/Controllers/**" in fm["applyTo"]
        assert "," in fm["applyTo"]

    def test_copilot_applyto_fallback_preserved_when_layer_empty(self):
        from cli.rule_templating import expand_rule_template

        text = (
            "---\n"
            "applyTo_template: layers.inbound\n"
            'applyTo: "**/api/**"\n'
            "---\n"
        )
        layers = {"inbound": []}
        out = expand_rule_template(text, layers)
        fm = yaml.safe_load(out.split("---", 2)[1])
        # Fallback survives intact.
        assert fm["applyTo"] == "**/api/**"
        # Template directive removed.
        assert "applyTo_template:" not in out

    def test_strips_trailing_slash_from_layer_hint(self):
        """Layer hints come in like 'api/' or 'Controllers/'. The expansion
        normalises to `**/api/**` style globs — trailing slash is dropped."""
        from cli.rule_templating import expand_rule_template

        text = (
            "---\n"
            "paths_template: layers.inbound\n"
            "---\n"
        )
        layers = {"inbound": ["api/", "Controllers/"]}
        out = expand_rule_template(text, layers)
        paths = _parsed_paths(out)
        assert "**/api/**" in paths
        assert "**/api//**" not in paths  # no double slash
        assert "**/Controllers/**" in paths


class TestTemplateInstalledRules:
    """End-to-end: cmd_apply runs `template_installed_rules` so source rule
    files with `paths_template:` end up with a concrete `paths:` block
    matching the team's architecture."""

    def test_after_apply_no_rule_file_has_paths_template(self, tmp_path):
        """Every installed rule must have its `paths_template:` resolved
        away; otherwise Claude Code would see invalid frontmatter."""
        import argparse

        from cli.cmd_apply import cmd_apply

        target = tmp_path / "project"
        target.mkdir()
        cmd_apply(argparse.Namespace(
            agent="claude-code", target=str(target),
            level="4", type="api", ci="github",
            stack="python-fastapi", force=False, detect=False,
        ))

        for rule in (target / ".claude" / "rules").rglob("*.md"):
            text = rule.read_text(encoding="utf-8")
            assert "paths_template:" not in text, f"{rule.name} still has paths_template"

    def test_clean_architecture_repo_gets_clean_layer_paths(self, tmp_path):
        """A target with Application/Domain/Infrastructure signals must end
        up with rule globs targeting those folders, not hexagonal defaults."""
        import argparse

        import yaml

        from cli.cmd_apply import cmd_apply

        target = tmp_path / "project"
        target.mkdir()
        # Clean-shape signals: trigger _STYLE_LAYERS["clean"]
        for folder in ("Application", "Domain", "Infrastructure"):
            (target / "src" / folder).mkdir(parents=True)

        cmd_apply(argparse.Namespace(
            agent="claude-code", target=str(target),
            level="4", type="api", ci="github",
            stack="python-fastapi", force=False, detect=False,
        ))

        # adapters.md (outbound) should now reference Infrastructure/
        adapters_text = (target / ".claude" / "rules" / "govkit" / "adapters.md").read_text(encoding="utf-8")
        fm = yaml.safe_load(adapters_text.split("---", 2)[1])
        paths = fm.get("paths") or []
        assert "**/Infrastructure/**" in paths
        # Hexagonal default replaced
        assert "**/adapters/**" not in paths

    def test_hexagonal_repo_keeps_hexagonal_defaults(self, tmp_path):
        """A target with ports/ + adapters/ folders keeps the hexagonal
        glob defaults."""
        import argparse

        import yaml

        from cli.cmd_apply import cmd_apply

        target = tmp_path / "project"
        target.mkdir()
        (target / "src" / "ports").mkdir(parents=True)
        (target / "src" / "adapters").mkdir(parents=True)

        cmd_apply(argparse.Namespace(
            agent="claude-code", target=str(target),
            level="4", type="api", ci="github",
            stack="python-fastapi", force=False, detect=False,
        ))

        adapters_text = (target / ".claude" / "rules" / "govkit" / "adapters.md").read_text(encoding="utf-8")
        fm = yaml.safe_load(adapters_text.split("---", 2)[1])
        paths = fm.get("paths") or []
        # Hexagonal-style layers include adapters/ + ports/outbound/
        assert "**/adapters/**" in paths

    def test_unknown_architecture_keeps_fallback_globs(self, tmp_path):
        """An empty target has no architecture signals → style=unknown →
        layers are []. Rule fallback paths survive intact."""
        import argparse

        import yaml

        from cli.cmd_apply import cmd_apply

        target = tmp_path / "project"
        target.mkdir()

        cmd_apply(argparse.Namespace(
            agent="claude-code", target=str(target),
            level="4", type="api", ci="github",
            stack="python-fastapi", force=False, detect=False,
        ))

        adapters_text = (target / ".claude" / "rules" / "govkit" / "adapters.md").read_text(encoding="utf-8")
        fm = yaml.safe_load(adapters_text.split("---", 2)[1])
        paths = fm.get("paths") or []
        assert "**/adapters/**" in paths

    def test_stack_apply_does_not_disturb_rule_templating(self, tmp_path):
        """stack apply changes overlay docs but architecture style is a
        property of the repo, not the stack — rule globs should stay
        consistent across stack swaps."""
        import argparse

        import yaml

        from cli.cmd_apply import cmd_apply
        from cli.cmd_stack import cmd_stack_apply

        target = tmp_path / "project"
        target.mkdir()
        for folder in ("Application", "Domain", "Infrastructure"):
            (target / "src" / folder).mkdir(parents=True)

        cmd_apply(argparse.Namespace(
            agent="claude-code", target=str(target),
            level="4", type="api", ci="github",
            stack="python-fastapi", force=False, detect=False,
        ))
        cmd_stack_apply(argparse.Namespace(
            stack_id="dotnet-aspnet", target=str(target), force=False,
        ))

        adapters_text = (target / ".claude" / "rules" / "govkit" / "adapters.md").read_text(encoding="utf-8")
        fm = yaml.safe_load(adapters_text.split("---", 2)[1])
        paths = fm.get("paths") or []
        # Still using clean-architecture layers from detected signals.
        assert "**/Infrastructure/**" in paths
