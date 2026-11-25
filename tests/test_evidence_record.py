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
        monkeypatch.setattr(rec, "discover", lambda target, patterns=None: many)
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
        monkeypatch.setattr(rec, "discover", lambda target, patterns=None: self._many(1100))
        with pytest.raises(rec.RecordError) as error:
            rec.write_record(tmp_path, observe=Tree(), now=NOW)
        assert "larger" in str(error.value)
        assert not (tmp_path / rec.NAME).exists()

    def test_a_large_record_within_the_limit_is_written_and_read_back(self, tmp_path, monkeypatch):
        _junit(tmp_path)
        monkeypatch.setattr(rec, "discover", lambda target, patterns=None: self._many(700))
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


SUREFIRE = "target/surefire-reports/TEST-com.example.RoutingTest.xml"
SUREFIRE_BODY = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<testsuite name="com.example.RoutingTest" tests="1" errors="0" skipped="0" failures="0">'
    '<testcase name="routesAnInvoice" classname="com.example.RoutingTest" time="0.01"/>'
    "</testsuite>"
)


class TestARemovedResultFile:
    """Deleting the file that holds a failure must not leave the rest current."""

    def test_a_recorded_file_that_is_gone_is_stale(self, tmp_path):
        _junit(tmp_path)
        _junit(tmp_path, name="junit-failing.xml")
        tree = Tree()
        rec.write_record(tmp_path, observe=tree, now=NOW)
        (tmp_path / "junit-failing.xml").unlink()
        answer = rec.provenance(tmp_path, _sources(tmp_path), observe=tree)
        assert answer["state"] == "stale"
        assert "junit-failing.xml was removed" in answer["detail"]

    def test_a_recorded_file_the_report_did_not_read_may_stay(self, tmp_path):
        """A feature with no criteria reads no evaluation results; they are still there."""
        _junit(tmp_path)
        (tmp_path / "govkit-eval-results.json").write_text("{}", encoding="utf-8")
        tree = Tree()
        rec.write_record(tmp_path, observe=tree, now=NOW)
        only_junit = [s for s in _sources(tmp_path) if s["tool"] == "junit"]
        assert rec.provenance(tmp_path, only_junit, observe=tree)["state"] == "current"


class TestAStatedLocation:
    """`--junit`: a project says where its test results are, once, when it records them."""

    def test_a_pattern_finds_results_the_name_rule_does_not(self, tmp_path):
        _junit(tmp_path, name=SUREFIRE, body=SUREFIRE_BODY)
        assert rec.discover(tmp_path) == []
        record = rec.write_record(
            tmp_path, junit=["target/surefire-reports/TEST-*.xml"], observe=Tree(), now=NOW
        )
        assert [r["path"] for r in record["results"]] == [SUREFIRE]
        assert record["junit_patterns"] == ["target/surefire-reports/TEST-*.xml"]
        validate_document(record, rec.SCHEMA)
        assert rec.read_record(tmp_path) == record

    def test_patterns_replace_the_name_rule(self, tmp_path):
        _junit(tmp_path, name=SUREFIRE, body=SUREFIRE_BODY)
        _junit(tmp_path, name="node_modules/pkg/junit.xml")
        record = rec.write_record(tmp_path, junit=["target/**/*.xml"], observe=Tree(), now=NOW)
        assert [r["path"] for r in record["results"]] == [SUREFIRE]

    def test_evaluation_results_are_still_found_by_name(self, tmp_path):
        _junit(tmp_path, name=SUREFIRE, body=SUREFIRE_BODY)
        (tmp_path / "govkit-eval-results.json").write_text("{}", encoding="utf-8")
        record = rec.write_record(tmp_path, junit=["target/**/*.xml"], observe=Tree(), now=NOW)
        assert [r["tool"] for r in record["results"]] == ["evaluation-results", "junit"]

    def test_without_a_pattern_the_record_is_as_before(self, tmp_path):
        _junit(tmp_path)
        record = rec.write_record(tmp_path, observe=Tree(), now=NOW)
        assert "junit_patterns" not in record
        assert rec.junit_patterns(tmp_path) is None

    def test_the_report_can_read_the_patterns_back(self, tmp_path):
        _junit(tmp_path, name=SUREFIRE, body=SUREFIRE_BODY)
        rec.write_record(tmp_path, junit=["target/**/*.xml"], observe=Tree(), now=NOW)
        assert rec.junit_patterns(tmp_path) == ("target/**/*.xml",)

    def test_no_record_or_an_unusable_one_states_no_location(self, tmp_path):
        assert rec.junit_patterns(tmp_path) is None
        (tmp_path / rec.NAME).write_text("{", encoding="utf-8")
        assert rec.junit_patterns(tmp_path) is None

    def test_a_file_that_is_not_junit_xml_is_refused(self, tmp_path):
        """Recorded result files are left out of the tree digest. A pattern must
        not be able to hide a source file from the freshness check that way."""
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "app.py").write_text("print('hi')\n", encoding="utf-8")
        (tmp_path / "src" / "config.xml").write_text("<settings/>", encoding="utf-8")
        for pattern in ("src/*.py", "src/*.xml"):
            with pytest.raises(rec.RecordError) as error:
                rec.write_record(tmp_path, junit=[pattern], observe=Tree(), now=NOW)
            assert "is not JUnit XML" in str(error.value)
        assert not (tmp_path / rec.NAME).exists()

    def test_a_pattern_that_matches_nothing_is_refused(self, tmp_path):
        _junit(tmp_path, name=SUREFIRE, body=SUREFIRE_BODY)
        with pytest.raises(rec.RecordError) as error:
            rec.write_record(
                tmp_path, junit=["target/**/*.xml", "build/**/*.xml"], observe=Tree(), now=NOW
            )
        assert "build/**/*.xml" in str(error.value) and "matched no file" in str(error.value)
        assert not (tmp_path / rec.NAME).exists()

    @pytest.mark.parametrize(
        "pattern",
        ["", "/abs/*.xml", "../other/*.xml", "a/../../b.xml", "a\\b.xml", "C:/x/*.xml", "a/**b/*.xml", "x" * 513],
    )  # fmt: skip
    def test_a_pattern_that_cannot_stay_inside_the_target_is_refused(self, tmp_path, pattern):
        _junit(tmp_path)
        with pytest.raises(rec.RecordError) as error:
            rec.write_record(tmp_path, junit=[pattern], observe=Tree(), now=NOW)
        assert "--junit" in str(error.value)
        assert not (tmp_path / rec.NAME).exists()

    def test_too_many_patterns_are_refused(self, tmp_path):
        _junit(tmp_path)
        with pytest.raises(rec.RecordError):
            rec.write_record(
                tmp_path,
                junit=[f"a{n}/*.xml" for n in range(rec.MAX_PATTERNS + 1)],
                observe=Tree(),
                now=NOW,
            )

    def test_the_pattern_limit_matches_the_schema(self):
        from cli import paths

        schema = json.loads(
            (paths.GOVERNANCE_DIR / "schemas/evidence-record.schema.json").read_text("utf-8")
        )
        patterns = schema["properties"]["junit_patterns"]
        assert patterns["maxItems"] == rec.MAX_PATTERNS
        assert patterns["items"]["maxLength"] == rec.MAX_PATTERN_LENGTH

    def test_a_match_reached_through_a_link_out_of_the_target_is_refused(self, tmp_path):
        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / "r.xml").write_text("<testsuite/>", encoding="utf-8")
        target = tmp_path / "project"
        target.mkdir()
        (target / "reports").symlink_to(outside, target_is_directory=True)
        with pytest.raises(rec.RecordError) as error:
            rec.write_record(target, junit=["reports/*.xml"], observe=Tree(), now=NOW)
        assert "outside the target" in str(error.value)

    def test_a_record_whose_patterns_leave_the_target_is_not_usable(self, tmp_path):
        """A hand-edited record is read with the same rules it was written with."""
        _junit(tmp_path, name=SUREFIRE, body=SUREFIRE_BODY)
        tree = Tree()
        record = rec.write_record(tmp_path, junit=["target/**/*.xml"], observe=tree, now=NOW)
        record["junit_patterns"] = ["../elsewhere/*.xml"]
        (tmp_path / rec.NAME).write_text(json.dumps(record), encoding="utf-8")
        with pytest.raises(rec.RecordError):
            rec.read_record(tmp_path)
        sources = rec.discover(tmp_path, ["target/**/*.xml"])
        assert rec.provenance(tmp_path, sources, observe=tree)["state"] == "unavailable"

    def test_a_new_file_at_the_stated_location_is_stale(self, tmp_path):
        _junit(tmp_path, name=SUREFIRE, body=SUREFIRE_BODY)
        tree = Tree()
        rec.write_record(tmp_path, junit=["target/**/*.xml"], observe=tree, now=NOW)
        _junit(tmp_path, name="target/surefire-reports/TEST-Other.xml", body=SUREFIRE_BODY)
        sources = rec.discover(tmp_path, rec.junit_patterns(tmp_path))
        assert rec.provenance(tmp_path, sources, observe=tree)["state"] == "stale"


class TestReviewOfTheStatedLocation:
    def test_a_folder_in_a_recorded_files_place_is_stale(self, tmp_path):
        _junit(tmp_path)
        _junit(tmp_path, name="junit-failing.xml")
        tree = Tree()
        rec.write_record(tmp_path, observe=tree, now=NOW)
        (tmp_path / "junit-failing.xml").unlink()
        (tmp_path / "junit-failing.xml").mkdir()
        answer = rec.provenance(tmp_path, _sources(tmp_path), observe=tree)
        assert answer["state"] == "stale"
        assert "junit-failing.xml is no longer a regular file" in answer["detail"]

    def test_provenance_judges_the_record_it_is_given(self, tmp_path):
        """The report selects files and checks them against one reading of the record."""
        _junit(tmp_path)
        tree = Tree()
        rec.write_record(tmp_path, observe=tree, now=NOW)
        loaded = rec.load(tmp_path)
        sources = _sources(tmp_path)
        _junit(tmp_path, body="<testsuite tests='9'/>")
        rec.write_record(tmp_path, observe=tree, now=NOW)  # a second record, written meanwhile
        changed = _sources(tmp_path)
        assert rec.provenance(tmp_path, changed, observe=tree)["state"] == "current"
        assert rec.provenance(tmp_path, changed, observe=tree, loaded=loaded)["state"] == "stale"
        assert rec.provenance(tmp_path, sources, observe=tree, loaded=loaded)["state"] == "current"

    def test_load_keeps_no_record_and_an_unusable_one_apart(self, tmp_path):
        assert rec.load(tmp_path) == (None, None)
        (tmp_path / rec.NAME).write_text("{", encoding="utf-8")
        record, error = rec.load(tmp_path)
        assert record is None and rec.NAME in error
        assert (
            rec.provenance(tmp_path, [{"path": "x", "content_digest": "0"}], loaded=(None, error))[
                "state"
            ]
            == "unavailable"
        )
