"""Tests for cli/fs.py — content-hash edit-protection.

Increment 1 of the data-enforcement hardening plan: `is_user_edited` prefers
the header's recorded `hash:` (SHA-256 of the doc body) over the legacy
mtime-vs-applied_at comparison. Content decides ownership; timestamps stop
mattering for hashed files.

The legacy mtime-path pins (hashless headers, copy_entry refusal flow) live
in tests/test_govkit.py (TestIsUserEdited, TestCopyEntryEditProtection) and
are unchanged — those now ARE the legacy-fallback tests.
"""

# applied_at fixtures: with hash-based detection the timestamp must not
# matter, so tests pin both extremes explicitly.
PAST = "2000-01-01T00:00:00+00:00"
FUTURE = "2099-01-01T00:00:00+00:00"


def _write_hashed_doc(path, body, recorded_body=None):
    """Write a doc with an editable header whose hash: records
    `recorded_body` (defaults to `body` — an unedited install)."""
    from cli.headers import compute_body_hash, format_editable_header

    header = format_editable_header(
        baseline="govkit@0.14.0",
        body_hash=compute_body_hash(recorded_body if recorded_body is not None else body),
    )
    path.write_text(header + body, encoding="utf-8")


class TestIsUserEditedHashBranch:
    def test_edited_body_detected_despite_restamped_applied_at(self, tmp_path):
        """The amnesia repro: upgrade re-stamps applied_at to now, so the
        edited file's mtime is older than applied_at. mtime logic forgets the
        edit; the hash must not."""
        from cli.fs import is_user_edited

        doc = tmp_path / "contract.md"
        _write_hashed_doc(doc, body="# Doc\n\nTeam edit.\n", recorded_body="# Doc\n\nOriginal.\n")

        assert is_user_edited(doc, FUTURE) is True

    def test_unchanged_body_not_flagged_when_mtime_newer(self, tmp_path):
        """The fresh-clone repro: a clone gives every file a new mtime. An
        unedited body must not trigger refusal."""
        from cli.fs import is_user_edited

        doc = tmp_path / "contract.md"
        _write_hashed_doc(doc, body="# Doc\n\nOriginal.\n")

        assert is_user_edited(doc, PAST) is False

    def test_hash_decides_despite_malformed_applied_at(self, tmp_path):
        """The hash branch must not depend on applied_at being parseable."""
        from cli.fs import is_user_edited

        doc = tmp_path / "contract.md"
        _write_hashed_doc(doc, body="# Doc\n\nTeam edit.\n", recorded_body="# Doc\n\nOriginal.\n")

        assert is_user_edited(doc, "not-a-timestamp") is True

    def test_empty_body_round_trip_not_flagged(self, tmp_path):
        from cli.fs import is_user_edited

        doc = tmp_path / "empty.md"
        _write_hashed_doc(doc, body="")

        assert is_user_edited(doc, PAST) is False

    def test_hashless_header_falls_back_to_mtime(self, tmp_path):
        """Pre-hash installs keep the old semantics: mtime newer than
        applied_at means edited, older means not."""
        from cli.fs import is_user_edited
        from cli.headers import format_editable_header

        doc = tmp_path / "legacy.md"
        doc.write_text(
            format_editable_header(baseline="govkit@0.13.0") + "# Doc\n",
            encoding="utf-8",
        )

        assert is_user_edited(doc, PAST) is True
        assert is_user_edited(doc, FUTURE) is False

    def test_force_overwrite_refreshes_recorded_hash(self, tmp_path):
        """--force over an edited hashed doc installs the new body and
        records ITS hash, so the file reads as unedited afterwards."""
        from cli.fs import copy_entry, is_user_edited
        from cli.headers import compute_body_hash, parse_editable_header

        src = tmp_path / "src.md"
        src.write_text("# New baseline\n", encoding="utf-8")
        dest = tmp_path / "dest.md"
        _write_hashed_doc(dest, body="# Edited\n", recorded_body="# Original\n")

        copy_entry(
            src,
            dest,
            applied_at=FUTURE,
            force=True,
            header_baseline="govkit@0.14.0",
        )

        content = dest.read_text(encoding="utf-8")
        assert parse_editable_header(content)["hash"] == compute_body_hash("# New baseline\n")
        assert is_user_edited(dest, FUTURE) is False

    def test_refusing_hashless_file_notes_migration_gap(self, tmp_path, capsys):
        """A pre-hash file is still under mtime semantics: its edits survive
        only until the next upgrade re-stamps applied_at. The refusal must
        say so."""
        from cli.fs import copy_entry
        from cli.headers import format_editable_header

        src = tmp_path / "src.md"
        src.write_text("# New baseline\n", encoding="utf-8")
        dest = tmp_path / "dest.md"
        dest.write_text(
            format_editable_header(baseline="govkit@0.13.0") + "# Edited\n",
            encoding="utf-8",
        )

        copy_entry(
            src,
            dest,
            applied_at=PAST,
            force=False,
            header_baseline="govkit@0.14.0",
        )

        err = capsys.readouterr().err
        assert "refused" in err
        assert "predates content-hash protection" in err

    def test_refusing_hashed_file_emits_no_migration_note(self, tmp_path, capsys):
        from cli.fs import copy_entry

        src = tmp_path / "src.md"
        src.write_text("# New baseline\n", encoding="utf-8")
        dest = tmp_path / "dest.md"
        _write_hashed_doc(dest, body="# Edited\n", recorded_body="# Original\n")

        copy_entry(
            src,
            dest,
            applied_at=FUTURE,
            force=False,
            header_baseline="govkit@0.14.0",
        )

        err = capsys.readouterr().err
        assert "refused" in err
        assert "predates content-hash protection" not in err

    def test_naive_applied_at_on_fallback_path_returns_false(self, tmp_path):
        """A timezone-naive applied_at parses fine but cannot be compared to
        the aware UTC mtime; unknown history must mean 'not edited', not
        TypeError (mirrors install_common._unmodified_since)."""
        from cli.fs import is_user_edited
        from cli.headers import format_editable_header

        doc = tmp_path / "legacy.md"
        doc.write_text(
            format_editable_header(baseline="govkit@0.13.0") + "# Doc\n",
            encoding="utf-8",
        )

        assert is_user_edited(doc, "2000-01-01T00:00:00") is False
        assert is_user_edited(doc, "2099-01-01T00:00:00") is False

    def test_unterminated_header_falls_back_without_crash(self, tmp_path):
        """A user edit that deletes the closing --> makes the header
        unparseable (parse returns None). That must degrade to the mtime
        path, not raise."""
        from cli.fs import is_user_edited

        doc = tmp_path / "broken.md"
        doc.write_text(
            "<!-- govkit:editable\n  baseline: govkit@0.14.0\n  hash: deadbeef\n# Doc\n",
            encoding="utf-8",
        )

        assert is_user_edited(doc, PAST) is True
        assert is_user_edited(doc, FUTURE) is False
