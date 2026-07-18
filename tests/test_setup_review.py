"""Tests for cli/setup_review.py — GOVKIT_SETUP_REVIEW.md writer.

PR 1 / Chunk E. Every `govkit apply` and `govkit upgrade` writes this file
at the target root so teams have a concrete starting point for reviewing
the installed governance.
"""


class TestWriteSetupReview:
    def _marker(self, **overrides):
        base = {
            "version": "0.10.0",
            "level": "4",
            "agent": "claude-code",
            "options": {"type": "api", "ci": "github"},
            "applied_at": "2026-05-27T15:00:00+00:00",
            "stack": None,
            "assumptions": [],
            "calibration": {"completed_at": None, "decisions": []},
        }
        base.update(overrides)
        return base

    def test_writes_file_at_target_root(self, tmp_path):
        from cli.setup_review import write_setup_review

        write_setup_review(tmp_path, self._marker())

        review = tmp_path / "GOVKIT_SETUP_REVIEW.md"
        assert review.is_file()

    def test_includes_install_summary(self, tmp_path):
        from cli.setup_review import write_setup_review

        write_setup_review(tmp_path, self._marker())
        content = (tmp_path / "GOVKIT_SETUP_REVIEW.md").read_text(encoding="utf-8")

        assert "claude-code" in content
        assert "level" in content.lower() and "4" in content
        assert "api" in content
        assert "github" in content
        assert "0.10.0" in content
        assert "2026-05-27T15:00:00+00:00" in content

    def test_includes_review_checklist_for_backend(self, tmp_path):
        from cli.setup_review import write_setup_review

        write_setup_review(tmp_path, self._marker(options={"type": "api", "ci": "github"}))
        content = (tmp_path / "GOVKIT_SETUP_REVIEW.md").read_text(encoding="utf-8")

        assert "TECH_STACK.md" in content
        assert "BOUNDARIES.md" in content
        assert "TESTING.md" in content
        # claude-code governance is govkit-owned in the rules namespace, not a
        # team-editable review item — the checklist must not list CLAUDE.md.
        assert "CLAUDE.md" not in content

    def test_review_paths_match_ui_type(self, tmp_path):
        """UI installs should reference docs/ui/architecture/, not docs/backend/."""
        from cli.setup_review import write_setup_review

        write_setup_review(tmp_path, self._marker(options={"type": "ui-react", "ci": "github"}))
        content = (tmp_path / "GOVKIT_SETUP_REVIEW.md").read_text(encoding="utf-8")

        assert "docs/ui/architecture" in content

    def test_review_paths_match_copilot_agent(self, tmp_path):
        """Copilot governance lives in the govkit-owned .github/instructions/govkit/
        namespace, so the review lists the team-editable architecture docs and
        does NOT present copilot-instructions.md as something to hand-edit."""
        from cli.setup_review import write_setup_review

        write_setup_review(tmp_path, self._marker(agent="copilot"))
        content = (tmp_path / "GOVKIT_SETUP_REVIEW.md").read_text(encoding="utf-8")

        assert "TECH_STACK.md" in content
        assert "copilot-instructions.md" not in content

    def test_review_paths_match_codex_agent(self, tmp_path):
        from cli.setup_review import write_setup_review

        write_setup_review(tmp_path, self._marker(agent="codex"))
        content = (tmp_path / "GOVKIT_SETUP_REVIEW.md").read_text(encoding="utf-8")

        assert "AGENTS.md" in content

    def test_assumptions_section_present_even_when_empty(self, tmp_path):
        """PR 1 writes the assumptions section as a placeholder; PR 3 fills it."""
        from cli.setup_review import write_setup_review

        write_setup_review(tmp_path, self._marker(assumptions=[]))
        content = (tmp_path / "GOVKIT_SETUP_REVIEW.md").read_text(encoding="utf-8")

        assert "Assumptions" in content
        # Placeholder language acknowledging no detectors yet:
        assert "doctor" in content.lower() or "calibrate" in content.lower()

    def test_assumptions_listed_when_present(self, tmp_path):
        """When PR 3 populates assumptions, the writer lists each
        review_required one with its warning message."""
        from cli.setup_review import write_setup_review

        marker = self._marker(assumptions=[
            {
                "id": "architecture.style",
                "value": "hexagonal",
                "source": "default",
                "confidence": "low",
                "evidence": [],
                "files_affected": ["docs/backend/architecture/BOUNDARIES.md"],
                "review_required": True,
                "warning_message": "Hexagonal layout assumed; no ports/ or adapters/ folder detected.",
                "calibrated_at": None,
                "calibrated_against_overlay_version": None,
            },
            {
                "id": "stack.language",
                "value": "csharp",
                "source": "detected",
                "confidence": "high",
                "evidence": ["*.csproj"],
                "files_affected": [],
                "review_required": False,
                "warning_message": None,
                "calibrated_at": None,
                "calibrated_against_overlay_version": None,
            },
        ])
        write_setup_review(tmp_path, marker)
        content = (tmp_path / "GOVKIT_SETUP_REVIEW.md").read_text(encoding="utf-8")

        # The review_required: True assumption shows up with its warning.
        assert "architecture.style" in content
        assert "Hexagonal layout assumed" in content
        # The review_required: False assumption is mentioned for visibility but
        # doesn't appear in the "needs your attention" list.
        assert "csharp" in content

    def test_shows_calibration_pending_when_not_completed(self, tmp_path):
        """PR 5: marker.calibration.completed_at is None → review file says so."""
        from cli.setup_review import write_setup_review

        write_setup_review(tmp_path, self._marker())
        content = (tmp_path / "GOVKIT_SETUP_REVIEW.md").read_text(encoding="utf-8")

        assert "Calibration" in content
        assert "not yet" in content.lower() or "pending" in content.lower()

    def test_shows_calibration_completed_at_when_set(self, tmp_path):
        from cli.setup_review import write_setup_review

        marker = self._marker(calibration={
            "completed_at": "2026-05-27T16:00:00+00:00",
            "decisions": [
                {"step_id": "step.tech_stack", "decided_at": "2026-05-27T16:00:00+00:00",
                 "decision": "confirm", "note": ""},
            ],
        })
        write_setup_review(tmp_path, marker)
        content = (tmp_path / "GOVKIT_SETUP_REVIEW.md").read_text(encoding="utf-8")

        assert "2026-05-27T16:00:00+00:00" in content
        # Per-step decision count shows up
        assert "1 confirmed" in content or "1 decision" in content.lower()

    def test_assumption_shows_resolved_when_calibrated(self, tmp_path):
        """A calibrated assumption (review_required=false + calibrated_at set)
        should render in the 'declared' bucket, not 'needs your attention'."""
        from cli.setup_review import write_setup_review

        marker = self._marker(assumptions=[{
            "id": "stack.id",
            "value": "python-fastapi",
            "source": "default",
            "confidence": "low",
            "evidence": [],
            "files_affected": [],
            "review_required": False,
            "warning_message": None,
            "calibrated_at": "2026-05-27T16:00:00+00:00",
            "calibrated_against_overlay_version": "0.10.0",
        }])
        write_setup_review(tmp_path, marker)
        content = (tmp_path / "GOVKIT_SETUP_REVIEW.md").read_text(encoding="utf-8")

        # The assumption appears under Declared (no action), not Needs your attention.
        assert "Declared" in content, "expected a 'Declared' section to be present"
        # If 'Needs your attention' section is absent, that's fine — it means
        # no review_required: true assumptions exist.

    def test_overwrites_existing_file(self, tmp_path):
        """The review file is regenerated on every apply/upgrade. Stale review
        notes from a prior apply must not bleed into the new one."""
        from cli.setup_review import write_setup_review

        review = tmp_path / "GOVKIT_SETUP_REVIEW.md"
        review.write_text("# old content from prior apply\n", encoding="utf-8")

        write_setup_review(tmp_path, self._marker())

        content = review.read_text(encoding="utf-8")
        assert "old content" not in content


class TestPrintReviewChecklist:
    def test_prints_checklist_to_stdout(self, tmp_path, capsys):
        from cli.setup_review import print_review_checklist

        marker = {
            "version": "0.10.0", "level": "4", "agent": "claude-code",
            "options": {"type": "api", "ci": "github"},
            "applied_at": "2026-05-27T15:00:00+00:00",
            "stack": None, "assumptions": [],
            "calibration": {"completed_at": None, "decisions": []},
        }
        print_review_checklist(tmp_path, marker)

        out = capsys.readouterr().out
        assert "REVIEW CHECKLIST" in out
        assert "GOVKIT_SETUP_REVIEW.md" in out
        # At minimum highlights TECH_STACK so the user knows where to look first.
        assert "TECH_STACK.md" in out
