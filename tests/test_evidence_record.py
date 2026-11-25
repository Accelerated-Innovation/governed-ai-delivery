"""The evidence record, and whether results still belong to the repository.

The record is written straight after a test run. Results count only while the
commit, the working tree and the result files are as it describes them. These
tests use a stand-in for Git; `tests/test_tree_identity.py` covers the real one.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from cli import evidence_record as rec
from cli import tree_identity
from cli.schema_validation import validate_document

COMMIT = "c" * 40
NOW = datetime(2026, 11, 24, 12, 0, 0, tzinfo=timezone.utc)


class Tree:
    """A stand-in for Git: an identity the test can change, and the excludes it was asked for."""

    def __init__(self):
        self.commit, self.digest, self.clean = COMMIT, "d" * 64, True
        self.excluded: tuple[str, ...] = ()
        self.unavailable = False

    def __call__(self, target, exclude=()):
        if self.unavailable:
            raise tree_identity.Unavailable("`git rev-parse` failed")
        self.excluded = exclude
        return tree_identity.Identity(self.commit, self.digest, self.clean)


def _junit(target: Path, name: str = "junit.xml", body: str = "<testsuite/>") -> None:
    (target / name).parent.mkdir(parents=True, exist_ok=True)
    (target / name).write_text(body, encoding="utf-8")


def _sources(target: Path) -> list[dict]:
    return rec.discover(target)


class TestWriting:
    def test_the_record_holds_the_commit_tree_time_and_result_files(self, tmp_path):
        import hashlib

        _junit(tmp_path)
        (tmp_path / "reports").mkdir()
        (tmp_path / "reports" / "govkit-eval-results.json").write_text("{}", encoding="utf-8")
        record = rec.write_record(tmp_path, observe=Tree(), now=NOW)
        assert record == json.loads((tmp_path / rec.NAME).read_text(encoding="utf-8"))
        validate_document(record, rec.SCHEMA)
        assert (record["commit"], record["tree_digest"], record["clean"]) == (
            COMMIT,
            "d" * 64,
            True,
        )
        assert record["recorded_at"] == "2026-11-24T12:00:00Z"
        assert record["results"] == [
            {
                "tool": "junit",
                "path": "junit.xml",
                "content_digest": hashlib.sha256(b"<testsuite/>").hexdigest(),
            },
            {
                "tool": "evaluation-results",
                "path": "reports/govkit-eval-results.json",
                "content_digest": hashlib.sha256(b"{}").hexdigest(),
            },
        ]

    def test_the_result_files_and_the_record_are_left_out_of_the_tree(self, tmp_path):
        _junit(tmp_path)
        tree = Tree()
        rec.write_record(tmp_path, observe=tree, now=NOW)
        assert tree.excluded == (rec.NAME, "junit.xml")

    def test_a_second_record_replaces_the_first(self, tmp_path):
        _junit(tmp_path)
        rec.write_record(tmp_path, observe=Tree(), now=NOW)
        _junit(tmp_path, body="<testsuite tests='1'/>")
        second = rec.write_record(tmp_path, observe=Tree(), now=NOW)
        assert rec.read_record(tmp_path) == second

    def test_the_record_is_not_itself_a_result_file(self, tmp_path):
        _junit(tmp_path)
        rec.write_record(tmp_path, observe=Tree(), now=NOW)
        assert [r["path"] for r in rec.discover(tmp_path)] == ["junit.xml"]

    def test_nothing_to_record_is_an_error(self, tmp_path):
        with pytest.raises(rec.RecordError) as error:
            rec.write_record(tmp_path, observe=Tree(), now=NOW)
        assert "no result files" in str(error.value)
        assert not (tmp_path / rec.NAME).exists()

    def test_no_git_is_an_error_and_writes_nothing(self, tmp_path):
        _junit(tmp_path)
        tree = Tree()
        tree.unavailable = True
        with pytest.raises(rec.RecordError) as error:
            rec.write_record(tmp_path, observe=tree, now=NOW)
        assert "cannot be identified" in str(error.value)
        assert not (tmp_path / rec.NAME).exists()

    def test_a_link_in_the_records_place_is_not_written_through(self, tmp_path):
        _junit(tmp_path)
        elsewhere = tmp_path / "elsewhere.txt"
        elsewhere.write_text("keep", encoding="utf-8")
        (tmp_path / rec.NAME).symlink_to(elsewhere)
        with pytest.raises(rec.RecordError):
            rec.write_record(tmp_path, observe=Tree(), now=NOW)
        assert elsewhere.read_text(encoding="utf-8") == "keep"

    def test_a_result_file_that_is_a_link_is_not_recorded(self, tmp_path):
        real = tmp_path / "elsewhere.txt"
        real.write_text("<testsuite/>", encoding="utf-8")
        (tmp_path / "junit.xml").symlink_to(real)
        with pytest.raises(rec.RecordError) as error:
            rec.write_record(tmp_path, observe=Tree(), now=NOW)
        assert "junit.xml" in str(error.value)


class TestProvenance:
    def _recorded(self, tmp_path) -> Tree:
        _junit(tmp_path)
        tree = Tree()
        rec.write_record(tmp_path, observe=tree, now=NOW)
        return tree

    def _state(self, tmp_path, tree) -> tuple[str, str]:
        answer = rec.provenance(tmp_path, _sources(tmp_path), observe=tree)
        return answer["state"], answer["detail"]

    def test_unchanged_results_are_current(self, tmp_path):
        tree = self._recorded(tmp_path)
        answer = rec.provenance(tmp_path, _sources(tmp_path), observe=tree)
        assert answer == {
            "state": "current",
            "detail": "the commit and the working tree are as they were recorded",
            "commit": COMMIT,
            "tree_digest": "d" * 64,
            "recorded_at": "2026-11-24T12:00:00Z",
        }

    def test_no_record_is_unrecorded(self, tmp_path):
        _junit(tmp_path)
        state, detail = self._state(tmp_path, Tree())
        assert state == "unrecorded"
        assert "govkit evidence --record" in detail

    def test_a_changed_working_tree_is_stale(self, tmp_path):
        tree = self._recorded(tmp_path)
        tree.digest = "e" * 64
        state, detail = self._state(tmp_path, tree)
        assert (state, "working tree changed" in detail) == ("stale", True)

    def test_a_new_commit_is_stale(self, tmp_path):
        tree = self._recorded(tmp_path)
        tree.commit, tree.digest = "f" * 40, "e" * 64
        state, detail = self._state(tmp_path, tree)
        assert (state, "commit changed" in detail) == ("stale", True)

    def test_a_result_file_rewritten_after_the_record_is_stale(self, tmp_path):
        tree = self._recorded(tmp_path)
        _junit(tmp_path, body="<testsuite tests='2'/>")
        state, detail = self._state(tmp_path, tree)
        assert (state, "junit.xml changed" in detail) == ("stale", True)

    def test_a_result_file_that_was_not_recorded_is_stale(self, tmp_path):
        tree = self._recorded(tmp_path)
        _junit(tmp_path, name="junit-extra.xml")
        state, detail = self._state(tmp_path, tree)
        assert (state, "junit-extra.xml" in detail) == ("stale", True)

    def test_the_tree_is_compared_without_the_files_the_record_names(self, tmp_path):
        tree = self._recorded(tmp_path)
        rec.provenance(tmp_path, _sources(tmp_path), observe=tree)
        assert tree.excluded == (rec.NAME, "junit.xml")

    def test_no_git_is_unavailable(self, tmp_path):
        tree = self._recorded(tmp_path)
        tree.unavailable = True
        assert self._state(tmp_path, tree)[0] == "unavailable"

    @pytest.mark.parametrize(
        "content",
        ["{", "[]", '{"schema_version": 1, "kind": "govkit.evidence-record"}', '{"a": 1, "a": 2}'],
    )
    def test_an_unusable_record_is_unavailable_not_unrecorded(self, tmp_path, content):
        """A broken record must not read as "no record": that would hide tampering."""
        _junit(tmp_path)
        (tmp_path / rec.NAME).write_text(content, encoding="utf-8")
        state, detail = self._state(tmp_path, Tree())
        assert state == "unavailable"
        assert rec.NAME in detail

    def test_a_record_that_is_a_link_is_unavailable(self, tmp_path):
        tree = self._recorded(tmp_path)
        real = tmp_path / "real.json"
        (tmp_path / rec.NAME).rename(real)
        (tmp_path / rec.NAME).symlink_to(real)
        assert self._state(tmp_path, tree)[0] == "unavailable"

    def test_with_no_result_files_nothing_is_checked(self, tmp_path):
        answer = rec.provenance(tmp_path, [], observe=Tree())
        assert answer["state"] == "not-checked"

    def test_every_state_is_in_the_report_schema(self):
        from cli import paths

        schema = json.loads(
            (paths.GOVERNANCE_DIR / "schemas/evidence-report.schema.json").read_text("utf-8")
        )
        states = schema["properties"]["provenance"]["properties"]["state"]["enum"]
        assert tuple(states) == rec.STATES


def test_the_bundled_example_record_validates_and_is_not_read_as_a_record():
    from cli import paths

    example = paths.GOVERNANCE_DIR / "examples" / "evidence-report"
    validate_document(json.loads((example / "record.json").read_text("utf-8")), rec.SCHEMA)
    assert rec.read_record(example) is None


class TestWritingSafely:
    def test_a_failed_write_keeps_the_previous_record(self, tmp_path, monkeypatch):
        _junit(tmp_path)
        first = rec.write_record(tmp_path, observe=Tree(), now=NOW)

        def fail(*args, **kwargs):
            raise OSError("disk full")

        monkeypatch.setattr(rec.os, "replace", fail)
        _junit(tmp_path, body="<testsuite tests='1'/>")
        with pytest.raises(rec.RecordError):
            rec.write_record(tmp_path, observe=Tree(), now=NOW)
        assert json.loads((tmp_path / rec.NAME).read_text(encoding="utf-8")) == first
        assert [p.name for p in tmp_path.iterdir() if rec.NAME in p.name] == [rec.NAME]

    def test_a_record_the_reader_would_refuse_is_not_written(self, tmp_path, monkeypatch):
        """More result files than the schema allows: say so now, not on the next read."""
        _junit(tmp_path)
        many = [
            {"tool": "junit", "path": f"junit-{n}.xml", "content_digest": "0" * 64}
            for n in range(5001)
        ]
        monkeypatch.setattr(rec, "discover", lambda target: many)
        with pytest.raises(rec.RecordError) as error:
            rec.write_record(tmp_path, observe=Tree(), now=NOW)
        assert "too many" in str(error.value) or "5000" in str(error.value)
        assert not (tmp_path / rec.NAME).exists()

    def test_what_is_written_can_be_read_back(self, tmp_path):
        _junit(tmp_path)
        written = rec.write_record(tmp_path, observe=Tree(), now=NOW)
        assert rec.read_record(tmp_path) == written


def test_the_result_file_limit_matches_the_schema():
    from cli import paths

    schema = json.loads(
        (paths.GOVERNANCE_DIR / "schemas/evidence-record.schema.json").read_text("utf-8")
    )
    assert schema["properties"]["results"]["maxItems"] == rec.MAX_RESULTS


class TestRecordSize:
    def _many(self, length: int) -> list[dict]:
        return [
            {"tool": "junit", "path": f"{n:04d}/" + "p" * length, "content_digest": "0" * 64}
            for n in range(rec.MAX_RESULTS)
        ]

    def test_a_record_larger_than_the_reader_accepts_is_not_written(self, tmp_path, monkeypatch):
        _junit(tmp_path)
        monkeypatch.setattr(rec, "discover", lambda target: self._many(1100))
        with pytest.raises(rec.RecordError) as error:
            rec.write_record(tmp_path, observe=Tree(), now=NOW)
        assert "larger" in str(error.value)
        assert not (tmp_path / rec.NAME).exists()

    def test_a_large_record_within_the_limit_is_written_and_read_back(self, tmp_path, monkeypatch):
        _junit(tmp_path)
        monkeypatch.setattr(rec, "discover", lambda target: self._many(700))
        written = rec.write_record(tmp_path, observe=Tree(), now=NOW)
        size = (tmp_path / rec.NAME).stat().st_size
        assert 4 * 1024 * 1024 < size <= rec.evaluation_results.MAX_BYTES, size
        assert rec.read_record(tmp_path) == written


def test_the_bytes_that_were_measured_are_the_bytes_written(tmp_path):
    """Text mode turns each newline into two bytes on Windows, after the size check."""
    data = b'{\n  "a": 1\n}\n'
    rec._replace(tmp_path / rec.NAME, data)
    assert (tmp_path / rec.NAME).read_bytes() == data


def test_a_record_has_unix_line_endings(tmp_path):
    _junit(tmp_path)
    rec.write_record(tmp_path, observe=Tree(), now=NOW)
    assert b"\r" not in (tmp_path / rec.NAME).read_bytes()
