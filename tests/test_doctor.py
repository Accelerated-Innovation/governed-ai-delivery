"""Tests for cli/doctor.py — govkit doctor command + ValidationFinding model.

PR 4. Doctor is the read-only validation pass: loads .govkit, builds a
RepoProfile, runs checks D001-D014, emits findings grouped by severity,
exits non-zero on errors. Designed to run in CI.
"""

import argparse
import json
from pathlib import Path

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

    def test_root_marker_takes_precedence_over_nested(self, tmp_path):
        """If the root has its own .govkit, scope to root only — don't dive
        into subdirs looking for more installs."""
        from cli.doctor import discover_install_targets

        _write_marker(tmp_path)
        _write_marker(tmp_path / "apps" / "api")

        targets = discover_install_targets(tmp_path)
        assert targets == [tmp_path]

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
        from cli.headers import format_editable_header
        from cli.doctor import run_doctor

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
        from cli.headers import format_editable_header
        from cli.doctor import run_doctor

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
        from cli.headers import format_editable_header
        from cli.doctor import run_doctor

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
        from cli.headers import format_editable_header
        from cli.doctor import run_doctor

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
        from cli.headers import format_editable_header
        from cli.doctor import run_doctor

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
        from cli.headers import format_editable_header
        from cli.doctor import run_doctor

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
        from cli.headers import format_editable_header
        from cli.doctor import run_doctor

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
        from cli.headers import format_editable_header
        from cli.doctor import run_doctor

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
