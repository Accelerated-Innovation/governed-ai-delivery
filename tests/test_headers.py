"""Tests for cli/headers.py — govkit:editable doc header read/write helpers.

PR 1 / Chunk B. Per the plan's "Doc header strategy" in Section 4, every
installed editable doc gets a top header that records its baseline so doctor
can detect staleness and edit-protection can preserve team changes.
"""



class TestFormatEditableHeader:
    def test_minimal_header_contains_baseline_and_see(self):
        from cli.headers import format_editable_header

        out = format_editable_header(baseline="govkit@0.10.0")
        assert "<!-- govkit:editable" in out
        assert "-->" in out
        assert "baseline: govkit@0.10.0" in out
        assert "see: GOVKIT_SETUP_REVIEW.md" in out

    def test_header_includes_reason_when_provided(self):
        from cli.headers import format_editable_header

        out = format_editable_header(
            baseline="dotnet-aspnet@0.10.0",
            reason="Stack-specific tech baseline. Edit freely; doctor will warn on contradictions.",
        )
        assert "reason: Stack-specific tech baseline" in out

    def test_header_omits_reason_when_not_provided(self):
        from cli.headers import format_editable_header

        out = format_editable_header(baseline="govkit@0.10.0")
        assert "reason:" not in out

    def test_header_trailing_blank_line_for_markdown_separation(self):
        """The header must end with a blank line so it separates cleanly from
        the doc body when prepended."""
        from cli.headers import format_editable_header

        out = format_editable_header(baseline="govkit@0.10.0")
        assert out.endswith("\n\n")

    def test_header_uses_custom_see_when_provided(self):
        from cli.headers import format_editable_header

        out = format_editable_header(baseline="govkit@0.10.0", see="docs/governance.md")
        assert "see: docs/governance.md" in out


class TestHasEditableHeader:
    def test_returns_true_when_header_at_top(self):
        from cli.headers import has_editable_header

        content = "<!-- govkit:editable\n  baseline: govkit@0.10.0\n  see: REVIEW.md\n-->\n\n# Doc\n"
        assert has_editable_header(content) is True

    def test_returns_true_when_header_after_leading_whitespace(self):
        from cli.headers import has_editable_header

        content = "\n\n<!-- govkit:editable\n  baseline: x\n-->\n"
        assert has_editable_header(content) is True

    def test_returns_false_for_empty_content(self):
        from cli.headers import has_editable_header

        assert has_editable_header("") is False

    def test_returns_false_when_header_not_at_top(self):
        from cli.headers import has_editable_header

        content = "# Title\n\n<!-- govkit:editable\n  baseline: x\n-->\n"
        assert has_editable_header(content) is False

    def test_returns_false_for_regular_markdown(self):
        from cli.headers import has_editable_header

        assert has_editable_header("# Just a doc\n\nSome content.\n") is False


class TestParseEditableHeader:
    def test_returns_none_when_no_header(self):
        from cli.headers import parse_editable_header

        assert parse_editable_header("# Just a doc\n") is None

    def test_parses_baseline_and_see(self):
        from cli.headers import parse_editable_header

        content = "<!-- govkit:editable\n  baseline: govkit@0.10.0\n  see: GOVKIT_SETUP_REVIEW.md\n-->\n\n# Body\n"
        data = parse_editable_header(content)
        assert data is not None
        assert data["baseline"] == "govkit@0.10.0"
        assert data["see"] == "GOVKIT_SETUP_REVIEW.md"

    def test_parses_reason(self):
        from cli.headers import parse_editable_header

        content = (
            "<!-- govkit:editable\n"
            "  baseline: dotnet-aspnet@0.10.0\n"
            "  reason: Stack-specific tech baseline.\n"
            "  see: GOVKIT_SETUP_REVIEW.md\n"
            "-->\n"
        )
        data = parse_editable_header(content)
        assert data["reason"] == "Stack-specific tech baseline."

    def test_parses_stack_id_with_at_sign(self):
        """baseline values look like `<id>@<version>` — the @ must not split the value."""
        from cli.headers import parse_editable_header

        content = "<!-- govkit:editable\n  baseline: nodejs-fastify@0.10.0\n-->\n"
        data = parse_editable_header(content)
        assert data["baseline"] == "nodejs-fastify@0.10.0"

    def test_returns_none_for_unterminated_header(self):
        from cli.headers import parse_editable_header

        # No closing -->
        content = "<!-- govkit:editable\n  baseline: x\n# rest of doc\n"
        assert parse_editable_header(content) is None

    def test_roundtrip_format_then_parse(self):
        from cli.headers import format_editable_header, parse_editable_header

        formatted = format_editable_header(
            baseline="python-fastapi@0.10.0",
            reason="Default Python baseline.",
        )
        parsed = parse_editable_header(formatted)
        assert parsed["baseline"] == "python-fastapi@0.10.0"
        assert parsed["reason"] == "Default Python baseline."
        assert parsed["see"] == "GOVKIT_SETUP_REVIEW.md"


class TestPrependHeaderToFile:
    """Convenience writer that adds the header to a doc body."""

    def test_prepends_to_markdown_file(self, tmp_path):
        from cli.headers import prepend_header_to_file

        doc = tmp_path / "TECH_STACK.md"
        doc.write_text("# Technology Stack\n\nContent here.\n", encoding="utf-8")

        prepend_header_to_file(doc, baseline="govkit@0.10.0")

        result = doc.read_text(encoding="utf-8")
        assert result.startswith("<!-- govkit:editable")
        assert "# Technology Stack" in result
        assert "Content here." in result

    def test_does_not_duplicate_existing_header(self, tmp_path):
        """If the file already starts with an editable header, prepending must
        not stack a second one."""
        from cli.headers import format_editable_header, prepend_header_to_file

        existing = format_editable_header(baseline="govkit@0.10.0")
        doc = tmp_path / "TECH_STACK.md"
        doc.write_text(existing + "# Technology Stack\n", encoding="utf-8")

        prepend_header_to_file(doc, baseline="govkit@0.11.0")

        result = doc.read_text(encoding="utf-8")
        # The header is overwritten, not duplicated.
        assert result.count("<!-- govkit:editable") == 1
        assert "baseline: govkit@0.11.0" in result
        assert "baseline: govkit@0.10.0" not in result

    def test_skips_non_markdown_files(self, tmp_path):
        """Only .md files get the header. YAML/JSON/etc. can't host a markdown
        comment cleanly, so they are left untouched."""
        from cli.headers import prepend_header_to_file

        yaml_doc = tmp_path / "config.yaml"
        yaml_doc.write_text("key: value\n", encoding="utf-8")

        prepend_header_to_file(yaml_doc, baseline="govkit@0.10.0")

        assert yaml_doc.read_text(encoding="utf-8") == "key: value\n"

    def test_handles_missing_file_silently(self, tmp_path):
        """Prepending to a path that doesn't exist must not raise — the caller
        may have failed to copy the source, and we don't want to compound
        errors."""
        from cli.headers import prepend_header_to_file

        missing = tmp_path / "nonexistent.md"
        # Should not raise.
        prepend_header_to_file(missing, baseline="govkit@0.10.0")
        assert not missing.exists()


class TestUpsertGovkitBlock:
    """Codex has no auto-loaded rules dir, so govkit's governance must live in
    AGENTS.md. The managed block lets govkit own its governance in-file while
    preserving whatever the team wrote around it."""

    def _markers(self):
        from cli.headers import GOVKIT_BLOCK_BEGIN, GOVKIT_BLOCK_END
        return GOVKIT_BLOCK_BEGIN, GOVKIT_BLOCK_END

    def test_new_file_is_just_the_block(self):
        from cli.headers import upsert_govkit_block
        begin, end = self._markers()

        out = upsert_govkit_block(None, "GOVERNANCE BODY")
        assert out.startswith(begin)
        assert end in out
        assert "GOVERNANCE BODY" in out

    def test_team_file_without_block_keeps_team_content(self):
        from cli.headers import upsert_govkit_block
        begin, end = self._markers()

        team = "# ACME AGENTS.md\nUse pnpm.\n"
        out = upsert_govkit_block(team, "GOVERNANCE BODY")
        assert "# ACME AGENTS.md" in out
        assert "Use pnpm." in out
        assert begin in out and end in out
        # Team content comes first; govkit's block is appended below it.
        assert out.index("ACME") < out.index(begin)

    def test_existing_block_is_replaced_in_place(self):
        from cli.headers import upsert_govkit_block
        begin, end = self._markers()

        before = f"# team top\n\n{begin}\nOLD GOVERNANCE\n{end}\n\n# team bottom\n"
        out = upsert_govkit_block(before, "NEW GOVERNANCE")
        assert "NEW GOVERNANCE" in out
        assert "OLD GOVERNANCE" not in out
        assert "# team top" in out
        assert "# team bottom" in out
        # Exactly one block after replacement.
        assert out.count(begin) == 1
        assert out.count(end) == 1

    def test_replace_unblocked_replaces_whole_file(self):
        """An existing govkit full-overwrite AGENTS.md (no block) is govkit's
        own — replace it wholesale with the block, not append to it."""
        from cli.headers import upsert_govkit_block

        old_full = "# old govkit governance, no markers\n"
        out = upsert_govkit_block(old_full, "NEW GOVERNANCE", replace_unblocked=True)
        assert "old govkit governance" not in out
        assert "NEW GOVERNANCE" in out
