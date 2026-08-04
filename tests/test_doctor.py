"""Tests for cli/doctor.py — govkit doctor command + ValidationFinding model.

PR 4. Doctor is the read-only validation pass: loads .govkit, builds a
RepoProfile, runs checks D001-D014, emits findings grouped by severity,
exits non-zero on errors. Designed to run in CI.
"""

import argparse
import json
import os
from pathlib import Path
from unittest import mock

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_marker(target: Path, **overrides) -> dict:
    """Create a .govkit/marker.json with a sensible baseline shape."""
    marker_dir = target / ".govkit"
    marker_dir.mkdir(parents=True, exist_ok=True)
    base = {
        "version": "0.10.0",
        "level": "4",
        "agent": "claude-code",
        "options": {"type": "api", "ci": "github", "stack": "python-fastapi"},
        "applied_at": "2026-05-27T10:00:00+00:00",
        "stack": {
            "id": "python-fastapi", "version": "0.10.0",
            "display_name": "Python 3.11+ / FastAPI",
            "applied_at": "2026-05-27T10:00:00+00:00",
        },
        "assumptions": [],
        "calibration": {"completed_at": None, "decisions": []},
    }
    base.update(overrides)
    (marker_dir / "marker.json").write_text(json.dumps(base), encoding="utf-8")
    return base


# ---------------------------------------------------------------------------
# ValidationFinding shape
# ---------------------------------------------------------------------------


class TestValidationFinding:
    def test_fields(self):
        from cli.doctor import ValidationFinding

        f = ValidationFinding(
            id="D001",
            severity="error",
            category="rule-glob",
            file=".claude/rules/ports.md",
            message="globs `**/ports/**` resolves to 0 files",
            suggested_action="edit ports.md or remove the rule",
        )
        assert f.id == "D001"
        assert f.severity == "error"
        assert f.category == "rule-glob"
        assert f.file == ".claude/rules/ports.md"
        assert "globs" in f.message
        assert "edit" in f.suggested_action


# ---------------------------------------------------------------------------
# run_doctor — entry point that gathers findings
# ---------------------------------------------------------------------------


class TestRunDoctor:
    def test_pristine_install_has_no_errors(self, tmp_path):
        """A freshly-applied install with no edits should have zero errors.

        Warnings or info findings may exist (e.g. review_required assumption),
        but nothing should be at the error severity."""
        from cli.doctor import run_doctor

        _write_marker(tmp_path)
        findings = run_doctor(tmp_path)

        errors = [f for f in findings if f.severity == "error"]
        assert errors == [], f"pristine install should have no errors; got: {[f.message for f in errors]}"

    def test_returns_empty_list_when_no_marker(self, tmp_path):
        """run_doctor on a target with no .govkit marker returns an error
        finding (so the caller knows the doctor couldn't run)."""
        from cli.doctor import run_doctor

        findings = run_doctor(tmp_path)
        # At least one finding signaling the missing marker.
        assert any(f.severity == "error" and "marker" in f.message.lower() for f in findings)


# ---------------------------------------------------------------------------
# D015 — unexpanded skill tokens
# ---------------------------------------------------------------------------


class TestUnexpandedSkillTokens:
    def test_flags_unexpanded_docs_area_token_in_installed_skill(self, tmp_path):
        """Skill templating degrades by leaving {{docs_area}} in place when
        the marker type is unknown; doctor must surface the leftover."""
        from cli.doctor import run_doctor

        _write_marker(tmp_path)
        skill = tmp_path / ".claude" / "skills" / "govkit-spec-planning"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            "---\nname: govkit-spec-planning\ndescription: x\n---\n"
            "Read docs/{{docs_area}}/architecture/ first.\n",
            encoding="utf-8",
        )

        findings = run_doctor(tmp_path)
        hits = [f for f in findings if f.id == "D015"]
        assert hits
        assert hits[0].severity == "warning"
        assert "{{docs_area}}" in hits[0].message

    def test_expanded_skill_files_are_clean(self, tmp_path):
        from cli.doctor import run_doctor

        _write_marker(tmp_path)
        skill = tmp_path / ".claude" / "skills" / "govkit-spec-planning"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            "---\nname: govkit-spec-planning\ndescription: x\n---\n"
            "Read docs/backend/architecture/ first.\n",
            encoding="utf-8",
        )

        findings = run_doctor(tmp_path)
        assert [f for f in findings if f.id == "D015"] == []


class TestD008LlmDependencies:
    def test_does_not_fire_for_a_claude_agent_sdk_service(self, tmp_path):
        """The reported false negative: a service driving the Claude Code CLI
        has no `anthropic` dependency, so the old marker list saw nothing."""
        from cli.doctor import run_doctor

        _write_marker(tmp_path, level="5")
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname="x"\ndependencies = ["claude-agent-sdk>=0.1"]\n',
            encoding="utf-8",
        )
        assert [f for f in run_doctor(tmp_path) if f.id == "D008"] == []

    def test_does_not_fire_for_a_dotnet_llm_service(self, tmp_path):
        """govkit ships a dotnet-aspnet stack, but .csproj was never scanned."""
        from cli.doctor import run_doctor

        _write_marker(tmp_path, level="5")
        (tmp_path / "app.csproj").write_text(
            '<PackageReference Include="Azure.AI.OpenAI" Version="2.0.0" />',
            encoding="utf-8",
        )
        assert [f for f in run_doctor(tmp_path) if f.id == "D008"] == []

    def test_still_fires_for_an_l5_install_with_no_llm_dependency(self, tmp_path):
        from cli.doctor import run_doctor

        _write_marker(tmp_path, level="5")
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname="x"\ndependencies = ["fastapi"]\n', encoding="utf-8",
        )
        hits = [f for f in run_doctor(tmp_path) if f.id == "D008"]
        assert len(hits) == 1
        assert hits[0].severity == "info"

    def test_message_names_every_manifest_the_scan_actually_reads(self, tmp_path):
        """The message used to restate the file list in prose, which is how it
        came to advertise four manifests while the scan covered three of
        govkit's own stacks not at all. Deriving it removes the drift."""
        from cli.detect import _DEP_FILE_PATTERNS
        from cli.doctor import run_doctor

        _write_marker(tmp_path, level="5")
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname="x"\ndependencies = ["fastapi"]\n', encoding="utf-8",
        )
        message = [f for f in run_doctor(tmp_path) if f.id == "D008"][0].message
        for pattern in _DEP_FILE_PATTERNS:
            assert pattern in message, f"{pattern} scanned but not named in D008"


class TestNextjsBoundary:
    def test_database_dependency_is_a_non_waivable_error(self, tmp_path):
        from cli.doctor import run_doctor

        _write_marker(
            tmp_path,
            options={"type": "ui-nextjs", "ci": "github"},
            stack=None,
        )
        (tmp_path / "package.json").write_text(
            '{"dependencies":{"next":"^16","@prisma/client":"^7"}}',
            encoding="utf-8",
        )

        hits = [finding for finding in run_doctor(tmp_path) if finding.id == "D016"]
        assert hits
        assert hits[0].severity == "error"
        assert hits[0].file == "package.json"
        assert "cannot be waived" in hits[0].suggested_action

    def test_typed_backend_fetch_is_clean(self, tmp_path):
        from cli.doctor import run_doctor

        _write_marker(
            tmp_path,
            options={"type": "ui-nextjs", "ci": "github"},
            stack=None,
        )
        source = tmp_path / "src" / "features" / "orders" / "api"
        source.mkdir(parents=True)
        (source / "get-orders.ts").write_text(
            "export const getOrders = () => fetch('/backend/orders');\n",
            encoding="utf-8",
        )

        assert [finding for finding in run_doctor(tmp_path) if finding.id == "D016"] == []

    def test_framework_mismatch_is_warning(self, tmp_path):
        from cli.doctor import run_doctor

        _write_marker(
            tmp_path,
            options={"type": "ui-nextjs", "ci": "github"},
            stack=None,
        )
        (tmp_path / "package.json").write_text(
            '{"dependencies":{"react":"^19"},"devDependencies":{"vite":"^7"}}',
            encoding="utf-8",
        )

        hits = [finding for finding in run_doctor(tmp_path) if finding.id == "D017"]
        assert hits and hits[0].severity == "warning"


# ---------------------------------------------------------------------------
# cmd_doctor — CLI dispatch + exit codes + monorepo discovery (A9)
# ---------------------------------------------------------------------------


class TestCmdDoctorExitCodes:
    def test_exits_0_when_no_errors(self, tmp_path):
        from cli.doctor import cmd_doctor

        _write_marker(tmp_path)
        with pytest.raises(SystemExit) as exc:
            cmd_doctor(argparse.Namespace(target=str(tmp_path)))
        assert exc.value.code == 0

    def test_exits_1_when_marker_missing(self, tmp_path):
        from cli.doctor import cmd_doctor

        with pytest.raises(SystemExit) as exc:
            cmd_doctor(argparse.Namespace(target=str(tmp_path)))
        assert exc.value.code == 1

    def test_prints_no_findings_summary_for_clean_install(self, tmp_path, capsys):
        from cli.doctor import cmd_doctor

        _write_marker(tmp_path)
        with pytest.raises(SystemExit):
            cmd_doctor(argparse.Namespace(target=str(tmp_path)))

        out = capsys.readouterr().out
        # Doctor should say something positive — either "no errors", "ok", or "clean"
        assert any(k in out.lower() for k in ("no errors", "no findings", "clean", "ok"))


class TestMonorepoDiscovery:
    """A9: when --target is omitted, doctor scans the cwd for .govkit/
    directories so monorepos with apps/api + apps/web both get checked."""

    def test_discover_install_targets_finds_marker_at_root(self, tmp_path):
        from cli.doctor import discover_install_targets

        _write_marker(tmp_path)
        targets = discover_install_targets(tmp_path)
        assert targets == [tmp_path]

    def test_discover_install_targets_returns_empty_when_no_markers(self, tmp_path):
        from cli.doctor import discover_install_targets

        targets = discover_install_targets(tmp_path)
        assert targets == []

    def test_discover_install_targets_walks_for_nested_markers(self, tmp_path):
        from cli.doctor import discover_install_targets

        # Monorepo: apps/api/.govkit and apps/web/.govkit, but NOT root.
        api = tmp_path / "apps" / "api"
        web = tmp_path / "apps" / "web"
        _write_marker(api)
        _write_marker(web)

        targets = discover_install_targets(tmp_path)
        assert api in targets
        assert web in targets
        assert tmp_path not in targets

    def test_a_governed_root_does_not_hide_nested_installs(self, tmp_path):
        """A governed root plus governed subprojects is a supported shape, so
        every install must be discovered.

        This previously returned `[root]` and stopped. The rule was justified
        as stopping `apps/` subdirs of a single install being double-counted —
        but a subdirectory holding its own marker is by definition a separate
        install, with its own agent, level, type and stack. `run_doctor` is
        per-target and reads each marker independently, so there was nothing
        to double-count; the rule only skipped real installs.

        It matters more now that `marker.json` holds one `type` and UI types
        reject `--stack`: a backend+frontend monorepo *has* to be a governed
        root plus a governed `apps/web`."""
        from cli.doctor import discover_install_targets

        _write_marker(tmp_path)
        _write_marker(tmp_path / "apps" / "api")
        _write_marker(tmp_path / "apps" / "web")

        targets = discover_install_targets(tmp_path)
        assert targets == [
            tmp_path,
            tmp_path / "apps" / "api",
            tmp_path / "apps" / "web",
        ]

    def test_each_install_is_returned_once(self, tmp_path):
        from cli.doctor import discover_install_targets

        _write_marker(tmp_path)
        _write_marker(tmp_path / "apps" / "api")

        targets = discover_install_targets(tmp_path)
        assert len(targets) == len(set(targets))

    def test_installs_nested_more_than_one_level_are_found(self, tmp_path):
        from cli.doctor import discover_install_targets

        _write_marker(tmp_path)
        deep = tmp_path / "packages" / "backend" / "svc"
        _write_marker(deep)

        assert deep in discover_install_targets(tmp_path)

    def test_noise_directories_are_not_searched(self, tmp_path):
        """A vendored copy of a governed project must not be reported, and
        the walk must not descend into it to find out."""
        from cli.doctor import discover_install_targets

        _write_marker(tmp_path)
        _write_marker(tmp_path / "node_modules" / "vendored")
        _write_marker(tmp_path / ".venv" / "lib" / "copied")

        assert discover_install_targets(tmp_path) == [tmp_path]

    def test_walk_prunes_noise_directories_instead_of_filtering_after(self, tmp_path):
        """Now that a governed root no longer short-circuits the walk, every
        `doctor` run scans the tree. It must prune noise dirs during traversal
        rather than walking them and discarding the results, or the cost lands
        on exactly the large repos that can least afford it."""
        from cli.doctor import discover_install_targets

        _write_marker(tmp_path)
        buried = tmp_path / "node_modules" / "pkg"
        buried.mkdir(parents=True)
        for i in range(50):
            (buried / f"nested{i}").mkdir()

        visited: list[str] = []
        real_walk = os.walk

        def counting_walk(top, *a, **kw):
            for dirpath, dirnames, filenames in real_walk(top, *a, **kw):
                visited.append(dirpath)
                yield dirpath, dirnames, filenames

        with mock.patch.object(os, "walk", counting_walk):
            discover_install_targets(tmp_path)

        assert not any("node_modules" in v for v in visited), (
            "walked into node_modules instead of pruning it"
        )

    def test_d001_passes_when_rule_globs_match_files(self, tmp_path):
        from cli.doctor import run_doctor

        _write_marker(tmp_path, agent="claude-code")
        rules_dir = tmp_path / ".claude" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "adapters.md").write_text(
            '---\npaths:\n  - "**/adapters/**"\n---\n# Adapters\n', encoding="utf-8",
        )
        # Source tree contains the adapters folder.
        (tmp_path / "src" / "adapters").mkdir(parents=True)
        (tmp_path / "src" / "adapters" / "db.py").write_text("x", encoding="utf-8")

        findings = run_doctor(tmp_path)
        d001s = [f for f in findings if f.id == "D001"]
        assert d001s == [], f"D001 should not fire when glob resolves; got: {d001s}"

    def test_d001_fires_when_rule_glob_resolves_to_zero_files(self, tmp_path):
        from cli.doctor import run_doctor

        _write_marker(tmp_path, agent="claude-code")
        rules_dir = tmp_path / ".claude" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "ports.md").write_text(
            '---\npaths:\n  - "**/ports/**"\n---\n# Ports\n', encoding="utf-8",
        )
        # No ports/ folder anywhere in target.

        findings = run_doctor(tmp_path)
        d001s = [f for f in findings if f.id == "D001"]
        assert len(d001s) == 1
        assert d001s[0].severity == "error"
        assert "ports" in d001s[0].message
        assert d001s[0].file and "ports.md" in d001s[0].file

    def test_d001_resolves_brace_expansion_globs(self, tmp_path):
        """`**/*.{py,go,ts}` is one glob with three alternatives. Path.glob has
        no brace expansion, so passing it through verbatim matches nothing and
        reports D001 against a repo that plainly contains matching files.

        Two shipped rules use this form — copilot's repo-scope-backend
        (`{py,go,ts,js,java,rs,cs,rb,php}`) and its UI counterpart
        (`{ts,tsx,js,jsx,html}`) — so every copilot install carried a
        permanent, unfixable D001 error."""
        from cli.doctor import run_doctor

        _write_marker(tmp_path, agent="claude-code")
        rules_dir = tmp_path / ".claude" / "rules" / "govkit"
        rules_dir.mkdir(parents=True)
        (rules_dir / "repo-scope.md").write_text(
            '---\npaths:\n  - "**/*.{py,go,ts,js,java,rs,cs,rb,php}"\n---\n# Scope\n',
            encoding="utf-8",
        )
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("x", encoding="utf-8")

        findings = run_doctor(tmp_path)
        d001s = [f for f in findings if f.id == "D001"]
        assert d001s == [], f"brace glob should resolve against src/main.py; got: {d001s}"

    def test_d001_still_fires_when_no_brace_alternative_matches(self, tmp_path):
        """Expansion must not turn D001 into a rubber stamp — a brace glob
        whose every alternative is absent still reports."""
        from cli.doctor import run_doctor

        _write_marker(tmp_path, agent="claude-code")
        rules_dir = tmp_path / ".claude" / "rules" / "govkit"
        rules_dir.mkdir(parents=True)
        (rules_dir / "repo-scope.md").write_text(
            '---\npaths:\n  - "**/*.{py,go,rs}"\n---\n# Scope\n', encoding="utf-8",
        )
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "README.md").write_text("x", encoding="utf-8")

        findings = run_doctor(tmp_path)
        d001s = [f for f in findings if f.id == "D001"]
        assert len(d001s) == 1
        assert "{py,go,rs}" in d001s[0].message, (
            "the reported glob should be the rule's own pattern, not an expansion"
        )

    def test_d001_resolves_copilot_brace_glob_in_comma_string(self, tmp_path):
        """copilot combines both features: an `applyTo` comma-string whose
        members may themselves contain brace alternation."""
        from cli.doctor import run_doctor

        _write_marker(tmp_path, agent="copilot")
        rules_dir = tmp_path / ".github" / "instructions" / "govkit"
        rules_dir.mkdir(parents=True)
        (rules_dir / "ui.instructions.md").write_text(
            '---\napplyTo: "**/*.{ts,tsx,js,jsx,html},**/components/**"\n---\n# UI\n',
            encoding="utf-8",
        )
        (tmp_path / "src" / "components").mkdir(parents=True)
        (tmp_path / "src" / "app.tsx").write_text("x", encoding="utf-8")

        findings = run_doctor(tmp_path)
        d001s = [f for f in findings if f.id == "D001"]
        assert d001s == [], f"both members should resolve; got: {d001s}"

    def test_d001_checks_rules_in_govkit_subdirectory(self, tmp_path):
        """Rules live in `.claude/rules/govkit/` once govkit owns its own
        namespace; doctor must descend into subdirectories, not just glob the
        top level, or it silently stops validating govkit's own rule globs."""
        from cli.doctor import run_doctor

        _write_marker(tmp_path, agent="claude-code")
        govkit_rules = tmp_path / ".claude" / "rules" / "govkit"
        govkit_rules.mkdir(parents=True)
        (govkit_rules / "ports.md").write_text(
            '---\npaths:\n  - "**/ports/**"\n---\n# Ports\n', encoding="utf-8",
        )
        # No ports/ folder anywhere in target — the glob resolves to nothing.

        findings = run_doctor(tmp_path)
        d001s = [f for f in findings if f.id == "D001"]
        assert len(d001s) == 1
        assert d001s[0].file and "ports.md" in d001s[0].file

    def test_d001_still_checks_flat_team_rules_alongside_subdir(self, tmp_path):
        """The recursive scan is additive: a team's own flat rule is still
        validated, not shadowed by the govkit/ subtree."""
        from cli.doctor import run_doctor

        _write_marker(tmp_path, agent="claude-code")
        rules_dir = tmp_path / ".claude" / "rules"
        (rules_dir / "govkit").mkdir(parents=True)
        # govkit's rule resolves (folder exists); the team's flat rule does not.
        (rules_dir / "govkit" / "api.md").write_text(
            '---\npaths:\n  - "**/api/**"\n---\n# Api\n', encoding="utf-8",
        )
        (rules_dir / "team-thing.md").write_text(
            '---\npaths:\n  - "**/nonexistent-team-folder/**"\n---\n# Team\n',
            encoding="utf-8",
        )
        (tmp_path / "src" / "api").mkdir(parents=True)

        findings = run_doctor(tmp_path)
        d001s = [f for f in findings if f.id == "D001"]
        assert len(d001s) == 1
        assert d001s[0].file and "team-thing.md" in d001s[0].file

    def test_d001_handles_copilot_applyto_format(self, tmp_path):
        """Copilot rules carry `applyTo: "<glob>"` (string), not the
        claude-code `paths:` list."""
        from cli.doctor import run_doctor

        _write_marker(tmp_path, agent="copilot")
        instr_dir = tmp_path / ".github" / "instructions"
        instr_dir.mkdir(parents=True)
        (instr_dir / "adapters.instructions.md").write_text(
            '---\napplyTo: "**/adapters/**"\n---\n# Adapters\n', encoding="utf-8",
        )
        # No adapters folder.
        findings = run_doctor(tmp_path)
        d001s = [f for f in findings if f.id == "D001"]
        assert len(d001s) == 1
        assert d001s[0].file and "adapters.instructions.md" in d001s[0].file

    def test_d001_codex_agent_skips_glob_check(self, tmp_path):
        """Codex uses nested AGENTS.md placement, not globs — D001 doesn't
        apply (the path IS the rule scope)."""
        from cli.doctor import run_doctor

        _write_marker(tmp_path, agent="codex")
        # Root AGENTS.md, no globs.
        (tmp_path / "AGENTS.md").write_text("# top-level agent guidance\n", encoding="utf-8")

        findings = run_doctor(tmp_path)
        d001s = [f for f in findings if f.id == "D001"]
        assert d001s == []

    def test_d001_no_rules_dir_no_findings(self, tmp_path):
        """If the rules directory doesn't exist, D001 has nothing to check
        (and doesn't crash)."""
        from cli.doctor import run_doctor

        _write_marker(tmp_path, agent="claude-code")
        findings = run_doctor(tmp_path)
        d001s = [f for f in findings if f.id == "D001"]
        assert d001s == []

    def test_d001_skips_files_without_globs_frontmatter(self, tmp_path):
        from cli.doctor import run_doctor

        _write_marker(tmp_path, agent="claude-code")
        rules_dir = tmp_path / ".claude" / "rules"
        rules_dir.mkdir(parents=True)
        # A rule with no frontmatter — no globs to check.
        (rules_dir / "notes.md").write_text("# Just notes, no frontmatter\n", encoding="utf-8")

        findings = run_doctor(tmp_path)
        d001s = [f for f in findings if f.id == "D001"]
        assert d001s == []

    def test_d001_handles_multiple_globs_per_rule(self, tmp_path):
        """If a rule lists multiple paths and ANY one of them has no matches,
        D001 fires for the missing one(s) but the resolving ones don't."""
        from cli.doctor import run_doctor

        _write_marker(tmp_path, agent="claude-code")
        rules_dir = tmp_path / ".claude" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "security.md").write_text(
            '---\npaths:\n  - "**/security/**"\n  - "**/auth/**"\n---\n', encoding="utf-8",
        )
        # Only security/ exists, not auth/.
        (tmp_path / "src" / "security" / "x.py").parent.mkdir(parents=True)
        (tmp_path / "src" / "security" / "x.py").write_text("x", encoding="utf-8")

        findings = run_doctor(tmp_path)
        d001s = [f for f in findings if f.id == "D001"]
        # One finding for the missing **/auth/** glob.
        assert len(d001s) == 1
        assert "auth" in d001s[0].message


    # -----------------------------------------------------------------------
    # D003/D004 — CI mismatch (per A7: warnings, not errors)
    # -----------------------------------------------------------------------

    def test_d003_fires_when_marker_says_azure_but_github_workflows_present(self, tmp_path):
        from cli.doctor import run_doctor

        _write_marker(tmp_path, options={"type": "api", "ci": "azure", "stack": "python-fastapi"})
        wf = tmp_path / ".github" / "workflows"
        wf.mkdir(parents=True)
        (wf / "ci.yml").write_text("name: CI\n", encoding="utf-8")

        findings = run_doctor(tmp_path)
        d003s = [f for f in findings if f.id == "D003"]
        assert len(d003s) == 1
        assert d003s[0].severity == "warning"
        assert "azure" in d003s[0].message
        assert "github" in d003s[0].message.lower()

    def test_d003_fires_when_marker_says_github_but_azure_pipelines_present(self, tmp_path):
        from cli.doctor import run_doctor

        _write_marker(tmp_path, options={"type": "api", "ci": "github", "stack": "python-fastapi"})
        (tmp_path / "azure-pipelines.yml").write_text("trigger:\n  - main\n", encoding="utf-8")

        findings = run_doctor(tmp_path)
        d003s = [f for f in findings if f.id == "D003"]
        assert len(d003s) == 1
        assert d003s[0].severity == "warning"

    def test_d003_does_not_fire_when_ci_matches_marker(self, tmp_path):
        from cli.doctor import run_doctor

        _write_marker(tmp_path, options={"type": "api", "ci": "github", "stack": "python-fastapi"})
        wf = tmp_path / ".github" / "workflows"
        wf.mkdir(parents=True)
        (wf / "ci.yml").write_text("name: CI\n", encoding="utf-8")

        findings = run_doctor(tmp_path)
        assert not any(f.id == "D003" for f in findings)

    def test_d004_fires_when_both_ci_platforms_present(self, tmp_path):
        from cli.doctor import run_doctor

        _write_marker(tmp_path, options={"type": "api", "ci": "github", "stack": "python-fastapi"})
        wf = tmp_path / ".github" / "workflows"
        wf.mkdir(parents=True)
        (wf / "ci.yml").write_text("name: CI\n", encoding="utf-8")
        (tmp_path / "azure-pipelines.yml").write_text("trigger:\n", encoding="utf-8")

        findings = run_doctor(tmp_path)
        d004s = [f for f in findings if f.id == "D004"]
        assert len(d004s) == 1
        assert d004s[0].severity == "warning"
        assert "ambiguous" in d004s[0].message.lower() or "both" in d004s[0].message.lower()

    def test_d004_does_not_fire_with_only_one_platform(self, tmp_path):
        from cli.doctor import run_doctor

        _write_marker(tmp_path, options={"type": "api", "ci": "github", "stack": "python-fastapi"})
        wf = tmp_path / ".github" / "workflows"
        wf.mkdir(parents=True)
        (wf / "ci.yml").write_text("name: CI\n", encoding="utf-8")

        findings = run_doctor(tmp_path)
        assert not any(f.id == "D004" for f in findings)


    # -----------------------------------------------------------------------
    # D005/D006 — stack mismatch
    # -----------------------------------------------------------------------

    def test_d005_fires_when_marker_stack_language_does_not_match_detected(self, tmp_path):
        """marker.stack.id implies a language; detected languages differ."""
        from cli.doctor import run_doctor

        _write_marker(tmp_path, stack={
            "id": "python-fastapi", "version": "0.10.0",
            "display_name": "Python 3.11+ / FastAPI",
            "applied_at": "2026-05-27T10:00:00+00:00",
        })
        # Repo is actually .NET
        (tmp_path / "Api.csproj").write_text(
            '<Project Sdk="Microsoft.NET.Sdk.Web"></Project>\n', encoding="utf-8",
        )
        (tmp_path / "global.json").write_text('{}', encoding="utf-8")

        findings = run_doctor(tmp_path)
        d005s = [f for f in findings if f.id == "D005"]
        assert len(d005s) == 1
        assert d005s[0].severity == "warning"
        assert "python-fastapi" in d005s[0].message
        assert "csharp" in d005s[0].message

    def test_d005_does_not_fire_when_language_matches(self, tmp_path):
        from cli.doctor import run_doctor

        _write_marker(tmp_path, stack={
            "id": "python-fastapi", "version": "0.10.0",
            "display_name": "Python", "applied_at": "2026-05-27T10:00:00+00:00",
        })
        (tmp_path / "pyproject.toml").write_text('[project]\nname="x"\n', encoding="utf-8")

        findings = run_doctor(tmp_path)
        assert not any(f.id == "D005" for f in findings)

    def test_d005_recognizes_databricks_lakehouse_as_python_stack(self, tmp_path):
        from cli.doctor import run_doctor

        _write_marker(tmp_path, stack={
            "id": "databricks-lakehouse", "version": "0.10.0",
            "display_name": "Databricks Lakehouse",
            "applied_at": "2026-05-27T10:00:00+00:00",
        })
        (tmp_path / "package.json").write_text(
            '{"devDependencies":{"typescript":"^5.0.0"}}\n',
            encoding="utf-8",
        )
        (tmp_path / "tsconfig.json").write_text('{}\n', encoding="utf-8")

        findings = run_doctor(tmp_path)
        d005s = [f for f in findings if f.id == "D005"]
        assert len(d005s) == 1
        assert d005s[0].severity == "warning"
        assert "databricks-lakehouse" in d005s[0].message
        assert "typescript" in d005s[0].message

    def test_d005_does_not_fire_when_no_language_detected(self, tmp_path):
        """Empty repo has nothing to disagree with — D005 silent."""
        from cli.doctor import run_doctor

        _write_marker(tmp_path, stack={
            "id": "python-fastapi", "version": "0.10.0",
            "display_name": "Python", "applied_at": "2026-05-27T10:00:00+00:00",
        })
        findings = run_doctor(tmp_path)
        assert not any(f.id == "D005" for f in findings)

    def test_d005_does_not_fire_when_marker_has_no_stack(self, tmp_path):
        """Legacy markers (pre-PR-2) may not carry a stack block."""
        from cli.doctor import run_doctor

        _write_marker(tmp_path, stack=None)
        (tmp_path / "Api.csproj").write_text('<Project Sdk="Microsoft.NET.Sdk.Web"></Project>\n', encoding="utf-8")

        findings = run_doctor(tmp_path)
        assert not any(f.id == "D005" for f in findings)

    def test_d006_fires_when_installed_doc_baseline_is_older(self, tmp_path):
        """Installed TECH_STACK.md carries baseline=python-fastapi@0.9.0 but
        the bundled overlay is at 0.10.0 — user should refresh."""
        from cli.doctor import run_doctor
        from cli.headers import format_editable_header

        _write_marker(tmp_path, stack={
            "id": "python-fastapi", "version": "0.10.0",
            "display_name": "Python", "applied_at": "2026-05-27T10:00:00+00:00",
        })
        tech_stack = tmp_path / "docs" / "backend" / "architecture" / "TECH_STACK.md"
        tech_stack.parent.mkdir(parents=True)
        header = format_editable_header(baseline="python-fastapi@0.9.0")
        tech_stack.write_text(header + "# old\n", encoding="utf-8")

        findings = run_doctor(tmp_path)
        d006s = [f for f in findings if f.id == "D006"]
        assert len(d006s) == 1
        assert d006s[0].severity == "warning"
        assert "0.9.0" in d006s[0].message
        assert "0.10.0" in d006s[0].message

    def test_d006_does_not_fire_when_baseline_matches_current_overlay(self, tmp_path):
        from cli.doctor import run_doctor
        from cli.headers import format_editable_header

        _write_marker(tmp_path, stack={
            "id": "python-fastapi", "version": "0.10.0",
            "display_name": "Python", "applied_at": "2026-05-27T10:00:00+00:00",
        })
        tech_stack = tmp_path / "docs" / "backend" / "architecture" / "TECH_STACK.md"
        tech_stack.parent.mkdir(parents=True)
        header = format_editable_header(baseline="python-fastapi@0.10.0")
        tech_stack.write_text(header + "# current\n", encoding="utf-8")

        findings = run_doctor(tmp_path)
        assert not any(f.id == "D006" for f in findings)

    def test_d006_does_not_fire_for_docs_with_no_header(self, tmp_path):
        """A doc without the editable header isn't govkit-managed; D006 skips."""
        from cli.doctor import run_doctor

        _write_marker(tmp_path)
        tech_stack = tmp_path / "docs" / "backend" / "architecture" / "TECH_STACK.md"
        tech_stack.parent.mkdir(parents=True)
        tech_stack.write_text("# Hand-authored, no header\n", encoding="utf-8")

        findings = run_doctor(tmp_path)
        assert not any(f.id == "D006" for f in findings)


    # -----------------------------------------------------------------------
    # D007/D008 — level leakage
    # -----------------------------------------------------------------------

    def test_d007_fires_at_l4_when_tech_stack_mentions_litellm(self, tmp_path):
        from cli.doctor import run_doctor
        from cli.headers import format_editable_header

        _write_marker(tmp_path, level="4")
        tech_stack = tmp_path / "docs" / "backend" / "architecture" / "TECH_STACK.md"
        tech_stack.parent.mkdir(parents=True)
        # Carry the editable header so D006 won't fire alongside.
        header = format_editable_header(baseline="python-fastapi@0.10.0")
        tech_stack.write_text(
            header
            + "# Tech Stack\n\n## LLM Gateway\nLiteLLM is the sole LLM gateway.\n",
            encoding="utf-8",
        )

        findings = run_doctor(tmp_path)
        d007s = [f for f in findings if f.id == "D007"]
        assert len(d007s) == 1
        assert d007s[0].severity == "warning"
        assert "LiteLLM" in d007s[0].message or "L5" in d007s[0].message

    def test_d007_does_not_fire_at_l5(self, tmp_path):
        from cli.doctor import run_doctor
        from cli.headers import format_editable_header

        _write_marker(tmp_path, level="5")
        tech_stack = tmp_path / "docs" / "backend" / "architecture" / "TECH_STACK.md"
        tech_stack.parent.mkdir(parents=True)
        header = format_editable_header(baseline="python-fastapi@0.10.0")
        tech_stack.write_text(
            header + "## LLM Gateway\nLiteLLM is the sole LLM gateway.\n",
            encoding="utf-8",
        )

        findings = run_doctor(tmp_path)
        assert not any(f.id == "D007" for f in findings)

    def test_d007_does_not_fire_when_no_llm_keywords(self, tmp_path):
        from cli.doctor import run_doctor
        from cli.headers import format_editable_header

        _write_marker(tmp_path, level="4")
        tech_stack = tmp_path / "docs" / "backend" / "architecture" / "TECH_STACK.md"
        tech_stack.parent.mkdir(parents=True)
        header = format_editable_header(baseline="python-fastapi@0.10.0")
        tech_stack.write_text(header + "# Tech Stack\n\nPython 3.11+\n", encoding="utf-8")

        findings = run_doctor(tmp_path)
        assert not any(f.id == "D007" for f in findings)

    def test_d008_fires_at_l5_with_no_llm_signals_in_deps(self, tmp_path):
        from cli.doctor import run_doctor

        _write_marker(tmp_path, level="5")
        # Repo has Python deps but no LLM SDK
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname="x"\ndependencies = ["fastapi", "uvicorn"]\n',
            encoding="utf-8",
        )

        findings = run_doctor(tmp_path)
        d008s = [f for f in findings if f.id == "D008"]
        assert len(d008s) == 1
        assert d008s[0].severity == "info"

    def test_d008_does_not_fire_at_l5_with_litellm_in_deps(self, tmp_path):
        from cli.doctor import run_doctor

        _write_marker(tmp_path, level="5")
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname="x"\ndependencies = ["litellm>=1.0", "openai"]\n',
            encoding="utf-8",
        )

        findings = run_doctor(tmp_path)
        assert not any(f.id == "D008" for f in findings)

    def test_d008_does_not_fire_at_lower_levels(self, tmp_path):
        from cli.doctor import run_doctor

        _write_marker(tmp_path, level="4")

        findings = run_doctor(tmp_path)
        assert not any(f.id == "D008" for f in findings)


    # -----------------------------------------------------------------------
    # D009 — testing framework declared in TESTING.md missing from deps
    # -----------------------------------------------------------------------

    def test_d009_fires_when_testing_md_names_framework_not_in_deps(self, tmp_path):
        from cli.doctor import run_doctor
        from cli.headers import format_editable_header

        _write_marker(tmp_path)
        testing = tmp_path / "docs" / "backend" / "architecture" / "TESTING.md"
        testing.parent.mkdir(parents=True)
        header = format_editable_header(baseline="python-fastapi@0.10.0")
        testing.write_text(header + "Primary testing tools: pytest, pytest-bdd\n", encoding="utf-8")
        # pyproject does NOT include pytest
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname="x"\ndependencies = ["fastapi"]\n', encoding="utf-8",
        )

        findings = run_doctor(tmp_path)
        d009s = [f for f in findings if f.id == "D009"]
        assert len(d009s) >= 1
        assert d009s[0].severity == "warning"
        assert "pytest" in d009s[0].message

    def test_d009_does_not_fire_when_framework_in_deps(self, tmp_path):
        from cli.doctor import run_doctor
        from cli.headers import format_editable_header

        _write_marker(tmp_path)
        testing = tmp_path / "docs" / "backend" / "architecture" / "TESTING.md"
        testing.parent.mkdir(parents=True)
        header = format_editable_header(baseline="python-fastapi@0.10.0")
        testing.write_text(header + "Primary testing tools: pytest\n", encoding="utf-8")
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname="x"\ndependencies = ["fastapi"]\n[project.optional-dependencies]\ntest = ["pytest"]\n',
            encoding="utf-8",
        )

        findings = run_doctor(tmp_path)
        assert not any(f.id == "D009" for f in findings)

    def test_d009_silent_when_no_testing_md(self, tmp_path):
        from cli.doctor import run_doctor

        _write_marker(tmp_path)
        findings = run_doctor(tmp_path)
        assert not any(f.id == "D009" for f in findings)

    def test_d009_silent_when_no_dep_manifest(self, tmp_path):
        """Without any dep manifest to cross-check, D009 has nothing to compare against."""
        from cli.doctor import run_doctor
        from cli.headers import format_editable_header

        _write_marker(tmp_path)
        testing = tmp_path / "docs" / "backend" / "architecture" / "TESTING.md"
        testing.parent.mkdir(parents=True)
        header = format_editable_header(baseline="python-fastapi@0.10.0")
        testing.write_text(header + "Primary testing tools: pytest\n", encoding="utf-8")

        findings = run_doctor(tmp_path)
        assert not any(f.id == "D009" for f in findings)

    # -----------------------------------------------------------------------
    # D010 — stale review_required assumption
    # -----------------------------------------------------------------------

    def test_d010_fires_for_old_review_required_assumption(self, tmp_path):
        """An assumption marked review_required: true with no calibration
        and an applied_at > 30 days ago triggers D010."""
        from cli.doctor import run_doctor

        _write_marker(tmp_path,
            applied_at="2026-01-01T00:00:00+00:00",  # well over 30 days before 2026-05-27
            assumptions=[{
                "id": "architecture.style",
                "value": "hexagonal",
                "source": "default",
                "confidence": "low",
                "evidence": [],
                "files_affected": [],
                "review_required": True,
                "warning_message": "Defaulted to hexagonal.",
                "calibrated_at": None,
                "calibrated_against_overlay_version": None,
            }],
        )

        findings = run_doctor(tmp_path)
        d010s = [f for f in findings if f.id == "D010"]
        assert len(d010s) == 1
        assert d010s[0].severity == "warning"
        assert "architecture.style" in d010s[0].message

    def test_d010_does_not_fire_for_recent_assumption(self, tmp_path):
        """A review_required assumption applied recently isn't yet stale."""
        from datetime import datetime, timezone

        from cli.doctor import run_doctor

        recent = datetime.now(timezone.utc).isoformat()
        _write_marker(tmp_path,
            applied_at=recent,
            assumptions=[{
                "id": "architecture.style", "value": "hexagonal",
                "source": "default", "confidence": "low",
                "evidence": [], "files_affected": [],
                "review_required": True, "warning_message": "",
                "calibrated_at": None, "calibrated_against_overlay_version": None,
            }],
        )

        findings = run_doctor(tmp_path)
        assert not any(f.id == "D010" for f in findings)

    def test_d010_does_not_fire_when_assumption_is_calibrated(self, tmp_path):
        from cli.doctor import run_doctor

        _write_marker(tmp_path,
            applied_at="2026-01-01T00:00:00+00:00",
            assumptions=[{
                "id": "architecture.style", "value": "hexagonal",
                "source": "default", "confidence": "low",
                "evidence": [], "files_affected": [],
                "review_required": True, "warning_message": "",
                "calibrated_at": "2026-02-01T00:00:00+00:00",
                "calibrated_against_overlay_version": "0.10.0",
            }],
        )

        findings = run_doctor(tmp_path)
        assert not any(f.id == "D010" for f in findings)

    def test_d010_does_not_fire_when_review_not_required(self, tmp_path):
        from cli.doctor import run_doctor

        _write_marker(tmp_path,
            applied_at="2026-01-01T00:00:00+00:00",
            assumptions=[{
                "id": "stack.language", "value": "python",
                "source": "detected", "confidence": "high",
                "evidence": ["pyproject.toml"], "files_affected": [],
                "review_required": False, "warning_message": None,
                "calibrated_at": None, "calibrated_against_overlay_version": None,
            }],
        )

        findings = run_doctor(tmp_path)
        assert not any(f.id == "D010" for f in findings)

    # -----------------------------------------------------------------------
    # D011 — marker references files that no longer exist
    # -----------------------------------------------------------------------

    def test_d011_fires_for_missing_files_affected_entry(self, tmp_path):
        from cli.doctor import run_doctor

        _write_marker(tmp_path,
            assumptions=[{
                "id": "stack.id", "value": "dotnet-aspnet",
                "source": "flag", "confidence": "high",
                "evidence": [],
                "files_affected": ["docs/backend/architecture/TECH_STACK.md"],
                "review_required": False, "warning_message": None,
                "calibrated_at": None, "calibrated_against_overlay_version": None,
            }],
        )
        # TECH_STACK.md does not exist at target — file was deleted.

        findings = run_doctor(tmp_path)
        d011s = [f for f in findings if f.id == "D011"]
        assert len(d011s) == 1
        assert d011s[0].severity == "error"
        assert "TECH_STACK.md" in d011s[0].message

    def test_d011_does_not_fire_when_files_affected_exist(self, tmp_path):
        from cli.doctor import run_doctor

        path = tmp_path / "docs" / "backend" / "architecture" / "TECH_STACK.md"
        path.parent.mkdir(parents=True)
        path.write_text("# x\n", encoding="utf-8")
        _write_marker(tmp_path,
            assumptions=[{
                "id": "stack.id", "value": "dotnet-aspnet",
                "source": "flag", "confidence": "high",
                "evidence": [],
                "files_affected": ["docs/backend/architecture/TECH_STACK.md"],
                "review_required": False, "warning_message": None,
                "calibrated_at": None, "calibrated_against_overlay_version": None,
            }],
        )

        findings = run_doctor(tmp_path)
        assert not any(f.id == "D011" for f in findings)


    # -----------------------------------------------------------------------
    # D013/D014 — extension contract validation (delegate to cli/extensions.py)
    # -----------------------------------------------------------------------

    def _write_extension(self, target: Path, ext_id: str, manifest: dict) -> Path:
        import yaml
        ext_dir = target / "extensions" / ext_id
        ext_dir.mkdir(parents=True)
        (ext_dir / "manifest.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")
        return ext_dir

    def test_d013_fires_when_extension_contract_paths_missing(self, tmp_path):
        from cli.doctor import run_doctor

        _write_marker(tmp_path)
        self._write_extension(tmp_path, "ext-a", {
            "id": "ext-a",
            "name": "Ext A",
            "version": "0.1.0",
            "extension_type": "architecture",
            "contract_sets": [
                {"id": "x", "description": "x",
                 "paths": ["docs/MISSING_CONTRACT.md"]},
            ],
        })

        findings = run_doctor(tmp_path)
        d013s = [f for f in findings if f.id == "D013"]
        assert len(d013s) >= 1
        assert d013s[0].severity == "error"
        assert "ext-a" in d013s[0].message or "MISSING_CONTRACT" in d013s[0].message

    def test_d013_does_not_fire_when_contracts_exist(self, tmp_path):
        from cli.doctor import run_doctor

        _write_marker(tmp_path)
        # Put a real contract file there
        (tmp_path / "extensions" / "ext-a").mkdir(parents=True)
        (tmp_path / "extensions" / "ext-a" / "C.md").write_text("# x", encoding="utf-8")
        import yaml
        (tmp_path / "extensions" / "ext-a" / "manifest.yaml").write_text(
            yaml.safe_dump({
                "id": "ext-a", "name": "Ext A", "version": "0.1.0",
                "extension_type": "architecture",
                "contract_sets": [{"id": "x", "description": "x", "paths": ["C.md"]}],
            }),
            encoding="utf-8",
        )

        findings = run_doctor(tmp_path)
        assert not any(f.id == "D013" for f in findings)

    def test_d014_fires_when_extension_extends_missing_file(self, tmp_path):
        from cli.doctor import run_doctor

        _write_marker(tmp_path)
        # Extension is otherwise valid (contract files exist) but extends a
        # missing baseline contract.
        (tmp_path / "extensions" / "ext-b").mkdir(parents=True)
        (tmp_path / "extensions" / "ext-b" / "C.md").write_text("# x", encoding="utf-8")
        import yaml
        (tmp_path / "extensions" / "ext-b" / "manifest.yaml").write_text(
            yaml.safe_dump({
                "id": "ext-b", "name": "Ext B", "version": "0.1.0",
                "extension_type": "architecture",
                "contract_sets": [{
                    "id": "x", "description": "x", "paths": ["C.md"],
                    "relates_to": {
                        "extends": ["docs/backend/architecture/MISSING_BASELINE.md"],
                        "supersedes": [],
                    },
                }],
            }),
            encoding="utf-8",
        )

        findings = run_doctor(tmp_path)
        d014s = [f for f in findings if f.id == "D014"]
        assert len(d014s) >= 1
        assert d014s[0].severity == "warning"

    def test_d013_and_d014_silent_when_no_extensions(self, tmp_path):
        from cli.doctor import run_doctor

        _write_marker(tmp_path)
        findings = run_doctor(tmp_path)
        assert not any(f.id in ("D013", "D014") for f in findings)


    def test_cmd_doctor_runs_against_all_discovered_targets(self, tmp_path, monkeypatch, capsys):
        """When --target omitted and cwd has multiple markers, doctor runs
        once per install and prints a per-install summary."""
        from cli.doctor import cmd_doctor

        api = tmp_path / "apps" / "api"
        web = tmp_path / "apps" / "web"
        _write_marker(api)
        _write_marker(web)
        monkeypatch.chdir(tmp_path)

        with pytest.raises(SystemExit) as exc:
            cmd_doctor(argparse.Namespace(target=None))

        out = capsys.readouterr().out
        # Per-install banners present
        assert "apps/api" in out.replace("\\", "/")
        assert "apps/web" in out.replace("\\", "/")
        # Both clean → exit 0
        assert exc.value.code == 0


# ---------------------------------------------------------------------------
# D018 — path-scoped rules left where govkit no longer writes them
# ---------------------------------------------------------------------------

BACKEND_LAYERS = ("api", "ports", "services", "models", "adapters", "common")

GOVKIT_BLOCK = (
    "<!-- BEGIN GOVKIT GOVERNANCE -->\n# govkit rule\n"
    "<!-- END GOVKIT GOVERNANCE -->\n"
)


def _multi_service_repo(target: Path) -> None:
    for svc in ("orders", "billing"):
        for layer in BACKEND_LAYERS:
            (target / "src" / svc / layer).mkdir(parents=True)


class TestD018StalePathScopedRules:
    """Fanning codex's layer rules out per service leaves any earlier
    root-level copy behind.

    govkit never deletes it — a team may have written that file, and even
    when it did not, a stale copy here is inert rather than contradictory:
    codex resolves AGENTS.md upward from the file being edited and never
    reaches a root `api/AGENTS.md` from `src/orders/api/`. That is why this
    reports rather than retiring the file the way
    `reconcile_legacy_instruction_files` does, where the alternative is the
    agent loading governance twice.
    """

    def test_fires_for_a_govkit_orphan_left_at_the_root(self, tmp_path):
        from cli.doctor import run_doctor

        _multi_service_repo(tmp_path)
        _write_marker(tmp_path, agent="codex")
        (tmp_path / "api").mkdir()
        (tmp_path / "api" / "AGENTS.md").write_text(GOVKIT_BLOCK, encoding="utf-8")

        d018s = [f for f in run_doctor(tmp_path) if f.id == "D018"]
        assert len(d018s) == 1
        assert d018s[0].file.replace("\\", "/") == "api/AGENTS.md"
        assert d018s[0].severity == "warning"

    def test_a_govkit_orphan_may_be_deleted(self, tmp_path):
        """It holds nothing the team wrote, so the advice can say so."""
        from cli.doctor import run_doctor

        _multi_service_repo(tmp_path)
        _write_marker(tmp_path, agent="codex")
        (tmp_path / "api").mkdir()
        (tmp_path / "api" / "AGENTS.md").write_text(GOVKIT_BLOCK, encoding="utf-8")

        finding = [f for f in run_doctor(tmp_path) if f.id == "D018"][0]
        assert "delete" in finding.suggested_action.lower()

    def test_a_team_authored_file_is_never_advised_away(self, tmp_path):
        """The same location, but the team wrote content outside the block.
        govkit must not suggest removing a file it did not author."""
        from cli.doctor import run_doctor

        _multi_service_repo(tmp_path)
        _write_marker(tmp_path, agent="codex")
        (tmp_path / "api").mkdir()
        (tmp_path / "api" / "AGENTS.md").write_text(
            "# Team notes\n\nOur own guidance.\n\n" + GOVKIT_BLOCK, encoding="utf-8",
        )

        action = [f for f in run_doctor(tmp_path) if f.id == "D018"][0].suggested_action.lower()
        # The file itself is never a delete target — only govkit's own block
        # inside it, which is content govkit put there.
        assert "leave the file" in action
        assert "delete api/agents.md" not in action
        assert "remove api/agents.md" not in action
        assert "block" in action

    def test_names_the_live_location_so_the_advice_is_actionable(self, tmp_path):
        from cli.doctor import run_doctor

        _multi_service_repo(tmp_path)
        _write_marker(tmp_path, agent="codex")
        (tmp_path / "api").mkdir()
        (tmp_path / "api" / "AGENTS.md").write_text(GOVKIT_BLOCK, encoding="utf-8")

        finding = [f for f in run_doctor(tmp_path) if f.id == "D018"][0]
        text = (finding.message + finding.suggested_action).replace("\\", "/")
        assert "src/orders" in text or "src/billing" in text

    def test_silent_on_a_clean_multi_service_install(self, tmp_path):
        from cli.doctor import run_doctor

        _multi_service_repo(tmp_path)
        _write_marker(tmp_path, agent="codex")

        assert [f for f in run_doctor(tmp_path) if f.id == "D018"] == []

    def test_silent_when_the_rules_are_where_they_belong(self, tmp_path):
        """The fanned-out copies must not be mistaken for stale ones."""
        from cli.doctor import run_doctor

        _multi_service_repo(tmp_path)
        _write_marker(tmp_path, agent="codex")
        for svc in ("orders", "billing"):
            (tmp_path / "src" / svc / "api" / "AGENTS.md").write_text(
                GOVKIT_BLOCK, encoding="utf-8",
            )

        assert [f for f in run_doctor(tmp_path) if f.id == "D018"] == []

    def test_silent_on_a_single_service_repo_where_the_root_is_correct(self, tmp_path):
        """A flat repo is where govkit *does* write root-relative layer
        rules. Flagging them would call a correct install broken."""
        from cli.doctor import run_doctor

        for layer in BACKEND_LAYERS:
            (tmp_path / layer).mkdir(parents=True)
        _write_marker(tmp_path, agent="codex")
        (tmp_path / "api" / "AGENTS.md").write_text(GOVKIT_BLOCK, encoding="utf-8")

        assert [f for f in run_doctor(tmp_path) if f.id == "D018"] == []

    def test_silent_for_a_documented_package_layout(self, tmp_path):
        from cli.doctor import run_doctor

        for layer in BACKEND_LAYERS:
            (tmp_path / "src" / "mypkg" / layer).mkdir(parents=True)
        _write_marker(tmp_path, agent="codex")
        (tmp_path / "src" / "mypkg" / "api" / "AGENTS.md").write_text(
            GOVKIT_BLOCK, encoding="utf-8",
        )

        assert [f for f in run_doctor(tmp_path) if f.id == "D018"] == []

    @pytest.mark.parametrize("agent", ["claude-code", "copilot"])
    def test_silent_for_agents_with_no_path_scoped_rules(self, tmp_path, agent):
        """Their rules are globs, never files inside layer folders. A stray
        root `api/AGENTS.md` in such an install is not govkit's business."""
        from cli.doctor import run_doctor

        _multi_service_repo(tmp_path)
        _write_marker(tmp_path, agent=agent)
        (tmp_path / "api").mkdir()
        (tmp_path / "api" / "AGENTS.md").write_text(GOVKIT_BLOCK, encoding="utf-8")

        assert [f for f in run_doctor(tmp_path) if f.id == "D018"] == []

    def test_a_file_without_a_govkit_block_is_not_govkits_business(self, tmp_path):
        """A root `api/AGENTS.md` the team wrote and govkit never touched is
        not a stale govkit rule — it is just their file."""
        from cli.doctor import run_doctor

        _multi_service_repo(tmp_path)
        _write_marker(tmp_path, agent="codex")
        (tmp_path / "api").mkdir()
        (tmp_path / "api" / "AGENTS.md").write_text(
            "# Purely ours\n", encoding="utf-8",
        )

        assert [f for f in run_doctor(tmp_path) if f.id == "D018"] == []

    def test_every_stale_location_is_reported(self, tmp_path):
        from cli.doctor import run_doctor

        _multi_service_repo(tmp_path)
        _write_marker(tmp_path, agent="codex")
        for layer in ("api", "ports", "services"):
            (tmp_path / layer).mkdir(exist_ok=True)
            (tmp_path / layer / "AGENTS.md").write_text(GOVKIT_BLOCK, encoding="utf-8")

        reported = {
            f.file.replace("\\", "/") for f in run_doctor(tmp_path) if f.id == "D018"
        }
        assert reported == {"api/AGENTS.md", "ports/AGENTS.md", "services/AGENTS.md"}


class TestD018SupersededSingleRootRules:
    """#83 — the single-source-root half of the same defect.

    #82 moved codex's path-scoped rules onto the detected source root, so an
    install made before it has them at the repo root. D018 shipped in #118
    reporting only the multi-service case, because its guard asked whether
    services were detected rather than whether govkit still writes to the
    root-relative location. The check is the same one; only the question was
    too narrow.
    """

    def _src_layout(self, target: Path, prefix: str = "src") -> None:
        for layer in BACKEND_LAYERS:
            (target / prefix / layer).mkdir(parents=True)

    def _orphan_at_root(self, target: Path, *layers: str) -> None:
        for layer in layers:
            (target / layer).mkdir(parents=True, exist_ok=True)
            (target / layer / "AGENTS.md").write_text(GOVKIT_BLOCK, encoding="utf-8")

    def test_fires_for_a_root_orphan_when_the_source_root_is_src(self, tmp_path):
        from cli.doctor import run_doctor

        self._src_layout(tmp_path)
        _write_marker(tmp_path, agent="codex")
        self._orphan_at_root(tmp_path, "api")

        d018s = [f for f in run_doctor(tmp_path) if f.id == "D018"]
        assert len(d018s) == 1
        assert d018s[0].file.replace("\\", "/") == "api/AGENTS.md"

    def test_names_the_live_location_under_the_source_root(self, tmp_path):
        from cli.doctor import run_doctor

        self._src_layout(tmp_path)
        _write_marker(tmp_path, agent="codex")
        self._orphan_at_root(tmp_path, "api")

        finding = [f for f in run_doctor(tmp_path) if f.id == "D018"][0]
        text = (finding.message + finding.suggested_action).replace("\\", "/")
        assert "src/api/AGENTS.md" in text

    def test_fires_for_the_documented_package_layout(self, tmp_path):
        from cli.doctor import run_doctor

        self._src_layout(tmp_path, "src/mypkg")
        _write_marker(tmp_path, agent="codex")
        self._orphan_at_root(tmp_path, "api", "ports", "services")

        reported = {
            f.file.replace("\\", "/") for f in run_doctor(tmp_path) if f.id == "D018"
        }
        assert reported == {"api/AGENTS.md", "ports/AGENTS.md", "services/AGENTS.md"}

    def test_a_team_authored_root_orphan_is_never_advised_away(self, tmp_path):
        from cli.doctor import run_doctor

        self._src_layout(tmp_path)
        _write_marker(tmp_path, agent="codex")
        (tmp_path / "api").mkdir()
        (tmp_path / "api" / "AGENTS.md").write_text(
            "# Team notes\n\nOurs.\n\n" + GOVKIT_BLOCK, encoding="utf-8",
        )

        action = [f for f in run_doctor(tmp_path) if f.id == "D018"][0].suggested_action.lower()
        assert "leave the file" in action
        assert "delete api/agents.md" not in action

    def test_silent_when_the_root_is_where_govkit_still_writes(self, tmp_path):
        """A flat repo: the root-relative destination *is* the live one.
        Reporting it would call a correct install broken."""
        from cli.doctor import run_doctor

        for layer in BACKEND_LAYERS:
            (tmp_path / layer).mkdir(parents=True)
        (tmp_path / "api" / "handlers.py").write_text("x = 1\n", encoding="utf-8")
        (tmp_path / "services" / "orders.py").write_text("x = 1\n", encoding="utf-8")
        _write_marker(tmp_path, agent="codex")
        (tmp_path / "api" / "AGENTS.md").write_text(GOVKIT_BLOCK, encoding="utf-8")

        assert [f for f in run_doctor(tmp_path) if f.id == "D018"] == []

    def test_silent_on_a_greenfield_repo(self, tmp_path):
        """No source tree at all, so destinations stay root-relative and the
        root copy is the live one."""
        from cli.doctor import run_doctor

        _write_marker(tmp_path, agent="codex")
        (tmp_path / "api").mkdir()
        (tmp_path / "api" / "AGENTS.md").write_text(GOVKIT_BLOCK, encoding="utf-8")

        assert [f for f in run_doctor(tmp_path) if f.id == "D018"] == []

    def test_the_live_copy_itself_is_never_reported(self, tmp_path):
        """Both copies present — the one under the source root is current."""
        from cli.doctor import run_doctor

        self._src_layout(tmp_path)
        _write_marker(tmp_path, agent="codex")
        (tmp_path / "src" / "api" / "AGENTS.md").write_text(GOVKIT_BLOCK, encoding="utf-8")
        self._orphan_at_root(tmp_path, "api")

        reported = {
            f.file.replace("\\", "/") for f in run_doctor(tmp_path) if f.id == "D018"
        }
        assert reported == {"api/AGENTS.md"}


def test_d018_covers_every_layout_where_rules_move():
    """Completeness guard. D018 exists because govkit relocates path-scoped
    rules; it must fire for every layout that relocates them and stay quiet
    for every layout that does not. A guard scoped to one relocation shape
    is how #83 stayed open after #118 shipped the check.
    """
    import tempfile
    from pathlib import Path as _P

    from cli.doctor import run_doctor

    relocating = {
        "src": ["src"],
        "src/mypkg": ["src/mypkg"],
        "multi-service": ["src/orders", "src/billing"],
    }
    stationary = {
        "flat-at-root": [""],
        "greenfield": [],
    }
    for name, prefixes in {**relocating, **stationary}.items():
        with tempfile.TemporaryDirectory() as tmp:
            target = _P(tmp)
            for prefix in prefixes:
                base = target / prefix if prefix else target
                for layer in BACKEND_LAYERS:
                    (base / layer).mkdir(parents=True, exist_ok=True)
            if name == "flat-at-root":
                (target / "api" / "handlers.py").write_text("x = 1\n", encoding="utf-8")
                (target / "services" / "o.py").write_text("x = 1\n", encoding="utf-8")
            _write_marker(target, agent="codex")
            (target / "api").mkdir(parents=True, exist_ok=True)
            (target / "api" / "AGENTS.md").write_text(GOVKIT_BLOCK, encoding="utf-8")

            fired = bool([f for f in run_doctor(target) if f.id == "D018"])
            assert fired == (name in relocating), (
                f"{name}: D018 fired={fired}, expected {name in relocating}"
            )


class TestD019SkippedServicePackages:
    """#120 — govkit names what it did not list.

    `architecture.services` omits packages that hold too few architecture
    layers. Correct, but silent: a team reading `services: [orders, billing]`
    cannot tell whether that is the whole repo, and since #118 the planning
    skills offer only the names govkit found.
    """

    def _services(self, target: Path) -> None:
        for svc in ("orders", "billing"):
            for layer in BACKEND_LAYERS:
                (target / "src" / svc / layer).mkdir(parents=True)

    def test_names_a_near_miss_package(self, tmp_path):
        from cli.doctor import run_doctor

        self._services(tmp_path)
        (tmp_path / "src" / "legacy" / "ports").mkdir(parents=True)
        _write_marker(tmp_path)

        d019s = [f for f in run_doctor(tmp_path) if f.id == "D019"]
        assert len(d019s) == 1
        assert "src/legacy" in d019s[0].message.replace("\\", "/")

    def test_is_informational_not_a_failure(self, tmp_path):
        """Nothing is broken — the repo just is not fully described. Doctor
        exits non-zero only on errors, and this must not change that."""
        from cli.doctor import run_doctor

        self._services(tmp_path)
        (tmp_path / "src" / "legacy" / "ports").mkdir(parents=True)
        _write_marker(tmp_path)

        finding = [f for f in run_doctor(tmp_path) if f.id == "D019"][0]
        assert finding.severity == "info"

    def test_says_what_it_saw_and_what_was_missing(self, tmp_path):
        from cli.doctor import run_doctor

        self._services(tmp_path)
        (tmp_path / "src" / "legacy" / "ports").mkdir(parents=True)
        _write_marker(tmp_path)

        finding = [f for f in run_doctor(tmp_path) if f.id == "D019"][0]
        text = finding.message + finding.suggested_action
        assert "ports" in text
        assert "architecture.services" in text

    def test_silent_when_every_package_is_a_service(self, tmp_path):
        from cli.doctor import run_doctor

        self._services(tmp_path)
        _write_marker(tmp_path)

        assert [f for f in run_doctor(tmp_path) if f.id == "D019"] == []

    def test_silent_for_packages_that_look_nothing_like_services(self, tmp_path):
        from cli.doctor import run_doctor

        self._services(tmp_path)
        (tmp_path / "src" / "utils" / "helpers").mkdir(parents=True)
        (tmp_path / "src" / "config").mkdir(parents=True)
        _write_marker(tmp_path)

        assert [f for f in run_doctor(tmp_path) if f.id == "D019"] == []

    def test_reports_each_near_miss_separately(self, tmp_path):
        from cli.doctor import run_doctor

        self._services(tmp_path)
        (tmp_path / "src" / "legacy" / "ports").mkdir(parents=True)
        (tmp_path / "src" / "shared" / "Domain").mkdir(parents=True)
        _write_marker(tmp_path)

        reported = {
            f.file.replace("\\", "/") for f in run_doctor(tmp_path) if f.id == "D019"
        }
        assert reported == {"src/legacy", "src/shared"}

    def test_fires_on_a_single_service_repo(self, tmp_path):
        from cli.doctor import run_doctor

        for layer in BACKEND_LAYERS:
            (tmp_path / "src" / "orders" / layer).mkdir(parents=True)
        (tmp_path / "src" / "legacy" / "ports").mkdir(parents=True)
        _write_marker(tmp_path)

        assert len([f for f in run_doctor(tmp_path) if f.id == "D019"]) == 1

    def test_silent_on_a_flat_repo(self, tmp_path):
        from cli.doctor import run_doctor

        for layer in BACKEND_LAYERS:
            (tmp_path / layer).mkdir(parents=True)
        _write_marker(tmp_path)

        assert [f for f in run_doctor(tmp_path) if f.id == "D019"] == []

    def test_does_not_change_the_exit_code(self, tmp_path):
        """An info finding alone must leave `govkit doctor` green."""
        import argparse

        import pytest as _pytest

        from cli.doctor import cmd_doctor

        self._services(tmp_path)
        (tmp_path / "src" / "legacy" / "ports").mkdir(parents=True)
        _write_marker(tmp_path)

        with _pytest.raises(SystemExit) as exc:
            cmd_doctor(argparse.Namespace(target=str(tmp_path)))
        assert exc.value.code == 0
