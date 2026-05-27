"""Tests for cli/calibrate.py — govkit calibrate command.

PR 5. Calibrate walks the team through reviewing the installed governance:
TECH_STACK, BOUNDARIES, API_CONVENTIONS, TESTING, the agent instruction file,
the rule tree, CI gates, and the skill context. Decisions are recorded in
marker.json's calibration block + per-assumption calibrated_at fields.
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
# CalibrationStep shape
# ---------------------------------------------------------------------------


class TestCalibrationStep:
    def test_fields(self):
        from cli.calibrate import CalibrationStep

        step = CalibrationStep(
            id="step.tech_stack",
            title="Tech Stack",
            description="Confirm language and framework",
            file_path="docs/backend/architecture/TECH_STACK.md",
            installed_summary="python-fastapi@0.10.0",
            detected_value="python",
            suggestion="Confirm Python version in §1",
            assumption_id=None,
        )
        assert step.id == "step.tech_stack"
        assert step.file_path == "docs/backend/architecture/TECH_STACK.md"
        assert step.detected_value == "python"


# ---------------------------------------------------------------------------
# build_checklist — generates the per-install step list
# ---------------------------------------------------------------------------


class TestBuildChecklist:
    def test_emits_the_nine_step_canonical_list(self, tmp_path):
        """Per the plan's Section 7, calibrate walks a 9-step checklist."""
        from cli.calibrate import build_checklist

        marker = _write_marker(tmp_path)
        steps = build_checklist(tmp_path, marker)
        assert len(steps) == 9

    def test_step_one_covers_marker(self, tmp_path):
        from cli.calibrate import build_checklist

        marker = _write_marker(tmp_path)
        steps = build_checklist(tmp_path, marker)
        assert steps[0].id == "step.marker"
        assert "agent" in steps[0].installed_summary
        assert "level" in steps[0].installed_summary

    def test_backend_steps_target_backend_architecture_dir(self, tmp_path):
        """For type=api/cli the architecture steps point at docs/backend/architecture/."""
        from cli.calibrate import build_checklist

        marker = _write_marker(tmp_path, options={"type": "api", "ci": "github", "stack": "python-fastapi"})
        steps = build_checklist(tmp_path, marker)
        paths = [s.file_path for s in steps if s.file_path]
        assert any("docs/backend/architecture/TECH_STACK.md" in p for p in paths)
        assert any("docs/backend/architecture/BOUNDARIES.md" in p for p in paths)
        assert any("docs/backend/architecture/TESTING.md" in p for p in paths)

    def test_ui_steps_target_ui_architecture_dir(self, tmp_path):
        from cli.calibrate import build_checklist

        marker = _write_marker(tmp_path, options={"type": "ui-react", "ci": "github", "stack": "python-fastapi"})
        steps = build_checklist(tmp_path, marker)
        paths = [s.file_path for s in steps if s.file_path]
        # No backend/architecture; should reference docs/ui/architecture for UI installs.
        assert any("docs/ui/architecture" in p for p in paths)
        assert not any("docs/backend/architecture" in p for p in paths)

    def test_agent_step_path_matches_agent(self, tmp_path):
        """The agent-instruction step uses the correct path per agent."""
        from cli.calibrate import build_checklist

        for agent, expected_filename in [
            ("claude-code", "CLAUDE.md"),
            ("copilot", "copilot-instructions.md"),
            ("codex", "AGENTS.md"),
        ]:
            marker = _write_marker(tmp_path, agent=agent)
            steps = build_checklist(tmp_path, marker)
            paths = [s.file_path for s in steps if s.file_path]
            assert any(expected_filename in p for p in paths), \
                f"agent={agent}: expected a step path containing {expected_filename}"

    def test_rules_step_path_matches_agent(self, tmp_path):
        from cli.calibrate import build_checklist

        for agent, expected_dir in [
            ("claude-code", ".claude/rules"),
            ("copilot", ".github/instructions"),
            ("codex", "AGENTS.md"),  # codex uses nested AGENTS.md
        ]:
            marker = _write_marker(tmp_path, agent=agent)
            steps = build_checklist(tmp_path, marker)
            rules_step = next((s for s in steps if s.id == "step.rules"), None)
            assert rules_step is not None
            assert rules_step.file_path is not None
            assert expected_dir in rules_step.file_path

    def test_detection_values_are_populated_from_repo(self, tmp_path):
        """build_checklist seeds detected_value from the RepoProfile so the
        team sees what govkit inferred."""
        from cli.calibrate import build_checklist

        marker = _write_marker(tmp_path)
        # Put real signals in the target
        (tmp_path / "Api.csproj").write_text(
            '<Project Sdk="Microsoft.NET.Sdk.Web"></Project>', encoding="utf-8",
        )
        (tmp_path / "global.json").write_text("{}", encoding="utf-8")

        steps = build_checklist(tmp_path, marker)
        tech_step = next((s for s in steps if s.id == "step.tech_stack"), None)
        assert tech_step is not None
        # Detected csharp should surface as the detected_value or in the suggestion.
        joined = (tech_step.detected_value or "") + " " + (tech_step.suggestion or "")
        assert "csharp" in joined or "dotnet" in joined.lower()


# ---------------------------------------------------------------------------
# cmd_calibrate — CLI dispatch
# ---------------------------------------------------------------------------


class TestCmdCalibrateBasics:
    def test_errors_when_no_marker_at_target(self, tmp_path):
        from cli.calibrate import cmd_calibrate

        with pytest.raises(SystemExit) as exc:
            cmd_calibrate(argparse.Namespace(
                target=str(tmp_path),
                non_interactive=True,
                only=None,
            ))
        assert exc.value.code == 1

    def test_non_interactive_runs_without_prompting(self, tmp_path):
        """In --non-interactive mode the user is never prompted."""
        from cli.calibrate import cmd_calibrate

        _write_marker(tmp_path)
        # Should not raise (no input() call expected).
        cmd_calibrate(argparse.Namespace(
            target=str(tmp_path),
            non_interactive=True,
            only=None,
        ))


class TestMonorepoDispatch:
    def test_auto_discovers_multiple_installs(self, tmp_path, monkeypatch, capsys):
        """When --target omitted and cwd has multiple .govkit/ dirs, calibrate
        processes each one (mirrors doctor's A9 behavior)."""
        from cli.calibrate import cmd_calibrate

        api = tmp_path / "apps" / "api"
        web = tmp_path / "apps" / "web"
        _write_marker(api)
        _write_marker(web)
        monkeypatch.chdir(tmp_path)

        cmd_calibrate(argparse.Namespace(
            target=None,
            non_interactive=True,
            only=None,
        ))

        out = capsys.readouterr().out
        assert "apps/api" in out.replace("\\", "/")
        assert "apps/web" in out.replace("\\", "/")

    def test_errors_when_no_marker_anywhere(self, tmp_path, monkeypatch):
        from cli.calibrate import cmd_calibrate

        monkeypatch.chdir(tmp_path)
        with pytest.raises(SystemExit) as exc:
            cmd_calibrate(argparse.Namespace(
                target=None,
                non_interactive=True,
                only=None,
            ))
        assert exc.value.code == 1


# ---------------------------------------------------------------------------
# Interactive mode + decision recording (PR5-C, PR5-D)
# ---------------------------------------------------------------------------


def _queue_inputs(monkeypatch, answers):
    """Patch input() to return successive answers from a list."""
    it = iter(answers)
    monkeypatch.setattr("builtins.input", lambda *_a, **_k: next(it))


class TestInteractiveMode:
    def test_accepting_all_defaults_completes_all_steps(self, tmp_path, monkeypatch):
        """Pressing enter at every prompt records a 'confirm' decision per step."""
        from cli.calibrate import cmd_calibrate
        from cli.govkit import read_govkit_marker

        _write_marker(tmp_path)
        _queue_inputs(monkeypatch, [""] * 9)  # 9 enters

        cmd_calibrate(argparse.Namespace(
            target=str(tmp_path), non_interactive=False, only=None,
        ))

        marker = read_govkit_marker(tmp_path)
        decisions = marker["calibration"]["decisions"]
        assert len(decisions) == 9
        assert all(d["decision"] == "confirm" for d in decisions)
        assert marker["calibration"]["completed_at"] is not None

    def test_n_records_needs_review_decision(self, tmp_path, monkeypatch):
        from cli.calibrate import cmd_calibrate
        from cli.govkit import read_govkit_marker

        _write_marker(tmp_path)
        # Confirm first 8, mark needs-review on step 9.
        _queue_inputs(monkeypatch, [""] * 8 + ["n"])

        cmd_calibrate(argparse.Namespace(
            target=str(tmp_path), non_interactive=False, only=None,
        ))

        marker = read_govkit_marker(tmp_path)
        decisions = marker["calibration"]["decisions"]
        assert decisions[-1]["decision"] == "needs-review"

    def test_s_records_skip_decision(self, tmp_path, monkeypatch):
        from cli.calibrate import cmd_calibrate
        from cli.govkit import read_govkit_marker

        _write_marker(tmp_path)
        _queue_inputs(monkeypatch, ["s"] + [""] * 8)

        cmd_calibrate(argparse.Namespace(
            target=str(tmp_path), non_interactive=False, only=None,
        ))

        marker = read_govkit_marker(tmp_path)
        decisions = marker["calibration"]["decisions"]
        assert decisions[0]["decision"] == "skip"

    def test_q_aborts_without_marker_update(self, tmp_path, monkeypatch):
        from cli.calibrate import cmd_calibrate
        from cli.govkit import read_govkit_marker

        _write_marker(tmp_path)
        # Press q at the very first prompt.
        _queue_inputs(monkeypatch, ["q"])

        cmd_calibrate(argparse.Namespace(
            target=str(tmp_path), non_interactive=False, only=None,
        ))

        marker = read_govkit_marker(tmp_path)
        # No decisions recorded; completed_at stays null.
        assert marker["calibration"]["completed_at"] is None
        assert marker["calibration"]["decisions"] == []

    def test_confirm_flips_review_required_on_linked_assumption(self, tmp_path, monkeypatch):
        """A 'confirm' decision on a step linked to an assumption sets
        review_required=false + stamps calibrated_at on that assumption."""
        from cli.calibrate import cmd_calibrate
        from cli.govkit import read_govkit_marker

        _write_marker(tmp_path, assumptions=[{
            "id": "stack.id",
            "value": "python-fastapi",
            "source": "default",
            "confidence": "low",
            "evidence": [],
            "files_affected": [],
            "review_required": True,
            "warning_message": "Defaulted to python-fastapi.",
            "calibrated_at": None,
            "calibrated_against_overlay_version": None,
        }])
        _queue_inputs(monkeypatch, [""] * 9)

        cmd_calibrate(argparse.Namespace(
            target=str(tmp_path), non_interactive=False, only=None,
        ))

        marker = read_govkit_marker(tmp_path)
        stack_assumption = next(a for a in marker["assumptions"] if a["id"] == "stack.id")
        assert stack_assumption["review_required"] is False
        assert stack_assumption["calibrated_at"] is not None
        assert stack_assumption["calibrated_against_overlay_version"] == "0.10.0"

    def test_needs_review_keeps_review_required_true(self, tmp_path, monkeypatch):
        """A 'needs-review' decision must NOT mark the assumption resolved."""
        from cli.calibrate import cmd_calibrate
        from cli.govkit import read_govkit_marker

        _write_marker(tmp_path, assumptions=[{
            "id": "stack.id",
            "value": "python-fastapi",
            "source": "default",
            "confidence": "low",
            "evidence": [],
            "files_affected": [],
            "review_required": True,
            "warning_message": "",
            "calibrated_at": None,
            "calibrated_against_overlay_version": None,
        }])
        # step.marker (linked to stack.id) is step 1 → mark needs-review
        _queue_inputs(monkeypatch, ["n"] + [""] * 8)

        cmd_calibrate(argparse.Namespace(
            target=str(tmp_path), non_interactive=False, only=None,
        ))

        marker = read_govkit_marker(tmp_path)
        stack_assumption = next(a for a in marker["assumptions"] if a["id"] == "stack.id")
        assert stack_assumption["review_required"] is True
        assert stack_assumption["calibrated_at"] is None


class TestOnlyFlag:
    def test_calibrate_preserves_applied_at(self, tmp_path, monkeypatch):
        """Calibrate writes the marker but must NOT bump applied_at. The
        original applied_at is what edit-protection (A2) consults; resetting
        it on every calibrate would silently un-protect user edits made
        before calibration."""
        from cli.calibrate import cmd_calibrate
        from cli.govkit import read_govkit_marker

        original_applied_at = "2026-01-15T12:00:00+00:00"
        _write_marker(tmp_path, applied_at=original_applied_at)
        _queue_inputs(monkeypatch, [""] * 9)

        cmd_calibrate(argparse.Namespace(
            target=str(tmp_path), non_interactive=False, only=None,
        ))

        marker = read_govkit_marker(tmp_path)
        assert marker["applied_at"] == original_applied_at, (
            "calibrate must preserve applied_at; bumping it would weaken "
            "edit-protection for files edited before calibration"
        )


    def test_only_runs_a_single_step(self, tmp_path, monkeypatch):
        """--only tech_stack walks just that step."""
        from cli.calibrate import cmd_calibrate
        from cli.govkit import read_govkit_marker

        _write_marker(tmp_path)
        _queue_inputs(monkeypatch, [""])  # one confirmation

        cmd_calibrate(argparse.Namespace(
            target=str(tmp_path), non_interactive=False, only="tech_stack",
        ))

        marker = read_govkit_marker(tmp_path)
        decisions = marker["calibration"]["decisions"]
        assert len(decisions) == 1
        assert decisions[0]["step_id"].endswith("tech_stack")
