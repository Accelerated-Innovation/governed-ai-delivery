"""Feature-scoped `govkit validate` and the known-failures record (#248)."""

import argparse
import hashlib
import json
import re
from pathlib import Path

import pytest

from cli import known_failures, paths
from cli.cmd_validate import cmd_validate, register
from cli.validate import FEATURE_CHECK_IDS, _build_checks, _named_checks, run_validation
from cli.validate_scope import run_scoped_validation
from tests.test_validate import make_full_feature

GOOD_ACCEPTANCE = """\
    Feature: Good feature

      @nfr-performance
      Scenario: Fast
        Given a request
        When processed
        Then fast

      @nfr-security
      Scenario: Secure
        Given auth
        When request
        Then ok
"""


def good(target: Path, name: str) -> Path:
    feature = target / "features" / name
    make_full_feature(feature, **{"acceptance.feature": GOOD_ACCEPTANCE})
    return feature


def bad(target: Path, name: str) -> Path:
    """A feature missing plan.md and carrying a TBD in nfrs.md."""
    feature = good(target, name)
    (feature / "plan.md").unlink()
    with (feature / "nfrs.md").open("a", encoding="utf-8") as stream:
        stream.write("\n## Reliability\n- TBD\n")
    return feature


def entry(kind, name, check, finding=None):
    scope = {"kind": kind}
    if name is not None:
        scope["name"] = name
    item = {"scope": scope, "check": check}
    if finding is not None:
        item["finding"] = finding
    return item


def write_record(path: Path, entries) -> Path:
    path.write_text(
        json.dumps({"schema_version": 1, "kind": "known-failures", "known_failures": entries}),
        encoding="utf-8",
    )
    return path


_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def generate(target: Path, capsys, **options) -> str:
    capsys.readouterr()
    assert run_scoped_validation(target, level="4", print_record=True, **options) == 0
    return capsys.readouterr().out


def run(target: Path, capsys, **options):
    capsys.readouterr()
    code = run_scoped_validation(target, level="4", **options)
    return code, _ANSI.sub("", capsys.readouterr().out)


class TestIdentifiers:
    def test_named_checks_match_the_legacy_check_list(self):
        for level in ("4", "5"):
            for marker_type in (None, "data"):
                artifacts, named = _named_checks(level, marker_type)
                legacy_artifacts, legacy = _build_checks(level, marker_type)
                assert artifacts == legacy_artifacts
                assert len(named) == len(legacy)
                names = [name for name, _ in named]
                assert len(set(names)) == len(names)
                assert set(names) <= set(FEATURE_CHECK_IDS)

    def test_identifiers_do_not_depend_on_project_type(self):
        api = [name for name, _ in _named_checks("5", "api")[1]]
        data = [name for name, _ in _named_checks("5", "data")[1]]
        assert api == data
        assert api[: len(_named_checks("4")[1])] == [n for n, _ in _named_checks("4")[1]]


class TestUnscopedOutputUnchanged:
    def test_plain_run_prints_no_identifiers_or_new_summary(self, tmp_path, capsys):
        good(tmp_path, "alpha")
        bad(tmp_path, "beta")
        assert run_validation(tmp_path, level="4") == 1
        out = capsys.readouterr().out
        assert "[completeness" not in out
        assert "selected" not in out
        assert "2 feature(s) checked, 1 passed, 1 failed" in out

    def test_cmd_without_new_options_calls_the_legacy_runner_unchanged(self, tmp_path, monkeypatch):
        seen = {}

        def legacy(target, level=None, strict=False, only=None):
            seen.update(target=target, level=level, strict=strict, only=only)
            return 0

        monkeypatch.setattr("cli.cmd_validate.run_validation", legacy)
        parser = argparse.ArgumentParser()
        register(parser.add_subparsers())
        args = parser.parse_args(["validate", "--target", str(tmp_path)])
        with pytest.raises(SystemExit) as excinfo:
            cmd_validate(args)
        assert excinfo.value.code == 0
        assert seen == {"target": tmp_path.resolve(), "level": None, "strict": False, "only": None}


class TestFeatureSelection:
    def test_scoped_run_ignores_other_failing_features(self, tmp_path, capsys):
        good(tmp_path, "alpha")
        bad(tmp_path, "beta")
        code, out = run(tmp_path, capsys, features=["alpha"])
        assert code == 0
        assert "features/alpha/" in out
        assert "features/beta/" not in out
        assert "[completeness]" in out
        assert "1 feature(s) selected: 0 new failure(s), 0 known, 0 resolved" in out

    def test_two_features_are_exactly_those_two(self, tmp_path, capsys):
        good(tmp_path, "alpha")
        bad(tmp_path, "beta")
        bad(tmp_path, "gamma")
        code, out = run(tmp_path, capsys, features=["alpha", "beta", "alpha"])
        assert code == 1
        assert "features/alpha/" in out and "features/beta/" in out
        assert "features/gamma/" not in out
        assert "2 feature(s) selected" in out

    def test_unknown_feature_is_an_error_naming_the_value(self, tmp_path, capsys):
        good(tmp_path, "alpha")
        code, out = run(tmp_path, capsys, features=["alpha", "nope"])
        assert code != 0
        assert "nope" in out
        assert "features/alpha/" not in out

    def test_starter_directories_cannot_be_selected(self, tmp_path, capsys):
        good(tmp_path, "starter_backend")
        good(tmp_path, "alpha")
        code, out = run(tmp_path, capsys, features=["starter_backend"])
        assert code != 0 and "starter_backend" in out

    def test_level_three_reports_no_per_feature_artifacts(self, tmp_path, capsys):
        capsys.readouterr()
        assert run_scoped_validation(tmp_path, level="3", features=["anything"]) == 0
        assert "no per-feature artifacts" in capsys.readouterr().out

    def test_only_experiments_honours_feature(self, tmp_path, capsys):
        for name in ("alpha", "beta"):
            feature = good(tmp_path, name)
            (feature / "experiments.yaml").write_text("not: [valid\n", encoding="utf-8")
        code, out = run(tmp_path, capsys, features=["alpha"], only="experiments")
        assert code == 1
        assert "features/alpha/" in out and "features/beta/" not in out
        assert "[architecture-experiments/invalid-record]" in out


class TestKnownFailures:
    def test_generated_record_round_trips_to_exit_zero(self, tmp_path, capsys):
        good(tmp_path, "alpha")
        bad(tmp_path, "beta")
        text = generate(tmp_path, capsys)
        document = json.loads(text)
        assert document["schema_version"] == 1 and document["kind"] == "known-failures"
        assert entry("feature", "beta", "completeness", "plan.md") in document["known_failures"]
        assert entry("feature", "beta", "nfrs-no-tbd") in document["known_failures"]
        record = tmp_path.parent / f"{tmp_path.name}-record.json"
        record.write_text(text, encoding="utf-8")
        code, out = run(tmp_path, capsys, known_failures=record)
        assert code == 0
        assert "KNOWN" in out and "FAIL" not in out
        assert "0 new failure(s)" in out and "0 resolved" in out

    def test_generated_record_honours_feature_selection(self, tmp_path, capsys):
        bad(tmp_path, "alpha")
        bad(tmp_path, "beta")
        document = json.loads(generate(tmp_path, capsys, features=["alpha"]))
        assert {item["scope"]["name"] for item in document["known_failures"]} == {"alpha"}

    def test_failure_absent_from_record_is_new(self, tmp_path, capsys):
        bad(tmp_path, "beta")
        record = write_record(
            tmp_path.parent / f"{tmp_path.name}-r.json",
            [entry("feature", "beta", "nfrs-no-tbd")],
        )
        code, out = run(tmp_path, capsys, known_failures=record)
        assert code == 1
        assert "KNOWN  [nfrs-no-tbd]" in out
        assert "FAIL  [completeness/plan.md]" in out
        assert "new failure(s), 1 known, 0 resolved" in out

    def test_second_finding_of_a_known_check_is_new(self, tmp_path, capsys):
        feature = bad(tmp_path, "beta")
        record = tmp_path.parent / f"{tmp_path.name}-r.json"
        record.write_text(generate(tmp_path, capsys), encoding="utf-8")
        assert run(tmp_path, capsys, known_failures=record)[0] == 0
        (feature / "architecture_preflight.md").unlink()
        code, out = run(tmp_path, capsys, known_failures=record)
        assert code == 1
        assert "FAIL  [completeness/architecture_preflight.md]" in out
        assert "KNOWN  [completeness/plan.md]" in out

    def test_resolved_entry_is_lenient_then_fails_under_strict(self, tmp_path, capsys):
        good(tmp_path, "alpha")
        record = write_record(
            tmp_path.parent / f"{tmp_path.name}-r.json",
            [entry("feature", "alpha", "nfrs-no-tbd")],
        )
        code, out = run(tmp_path, capsys, known_failures=record)
        assert code == 0
        assert "RESOLVED" in out and "1 resolved" in out
        code, out = run(tmp_path, capsys, known_failures=record, strict=True)
        assert code == 1 and "1 resolved" in out

    def test_entries_outside_the_selection_are_ignored(self, tmp_path, capsys):
        good(tmp_path, "alpha")
        good(tmp_path, "beta")
        record = write_record(
            tmp_path.parent / f"{tmp_path.name}-r.json",
            [entry("feature", "beta", "nfrs-no-tbd")],
        )
        code, out = run(tmp_path, capsys, known_failures=record, features=["alpha"], strict=True)
        assert code == 0
        assert "0 resolved" in out and "1 record entr" in out

    def test_entry_for_a_deleted_feature_is_resolved(self, tmp_path, capsys):
        good(tmp_path, "alpha")
        record = write_record(
            tmp_path.parent / f"{tmp_path.name}-r.json",
            [entry("feature", "gone", "completeness", "plan.md")],
        )
        code, out = run(tmp_path, capsys, known_failures=record)
        assert code == 0 and "1 resolved" in out
        assert run(tmp_path, capsys, known_failures=record, strict=True)[0] == 1

    def test_only_experiments_ignores_entries_for_other_checks(self, tmp_path, capsys):
        bad(tmp_path, "beta")
        record = tmp_path.parent / f"{tmp_path.name}-r.json"
        record.write_text(generate(tmp_path, capsys), encoding="utf-8")
        code, out = run(tmp_path, capsys, known_failures=record, only="experiments", strict=True)
        assert code == 0 and "0 resolved" in out

    def test_location_and_digest_are_reported(self, tmp_path, capsys):
        good(tmp_path, "alpha")
        outside = write_record(tmp_path.parent / f"{tmp_path.name}-r.json", [])
        inside = write_record(tmp_path / "known-failures.json", [])
        _, out = run(tmp_path, capsys, known_failures=outside)
        assert "outside the inspected tree" in out
        digest = hashlib.sha256(outside.read_bytes()).hexdigest()
        assert f"sha256:{digest}" in out
        _, out = run(tmp_path, capsys, known_failures=inside)
        assert "inside the inspected tree" in out
        write_record(outside, [entry("feature", "alpha", "nfrs-no-tbd")])
        _, changed = run(tmp_path, capsys, known_failures=outside)
        assert f"sha256:{digest}" not in changed

    def test_expected_digest_pins_the_record(self, tmp_path, capsys):
        good(tmp_path, "alpha")
        record = write_record(tmp_path.parent / f"{tmp_path.name}-r.json", [])
        digest = hashlib.sha256(record.read_bytes()).hexdigest()
        for accepted in (digest, f"sha256:{digest}", digest.upper()):
            assert run(tmp_path, capsys, known_failures=record, expected_digest=accepted)[0] == 0
        code, out = run(tmp_path, capsys, known_failures=record, expected_digest="0" * 64)
        assert code != 0 and "digest" in out
        assert "features/alpha/" not in out

    @pytest.mark.parametrize(
        "content",
        [
            None,
            "{not json",
            "[]",
            json.dumps({"schema_version": 1, "kind": "known-failures"}),
            json.dumps({"schema_version": 2, "kind": "known-failures", "known_failures": []}),
            json.dumps(
                {
                    "schema_version": 1,
                    "kind": "known-failures",
                    "known_failures": [entry("feature", "alpha", "no-such-check")],
                }
            ),
            json.dumps(
                {
                    "schema_version": 1,
                    "kind": "known-failures",
                    "known_failures": [entry("feature", None, "completeness")],
                }
            ),
            json.dumps(
                {
                    "schema_version": 1,
                    "kind": "known-failures",
                    "known_failures": [entry("approval", None, "completeness")],
                }
            ),
            json.dumps(
                {
                    "schema_version": 1,
                    "kind": "known-failures",
                    "known_failures": [entry("feature", "alpha", "nfrs-no-tbd")] * 2,
                }
            ),
        ],
    )
    def test_unusable_record_fails_and_is_never_empty(self, tmp_path, capsys, content):
        bad(tmp_path, "alpha")
        record = tmp_path.parent / f"{tmp_path.name}-r.json"
        if content is None:
            record.unlink(missing_ok=True)
        else:
            record.write_text(content, encoding="utf-8")
        code, out = run(tmp_path, capsys, known_failures=record)
        assert code != 0
        assert "known-failures record" in out
        assert "features/alpha/" not in out

    def test_record_that_is_a_directory_fails(self, tmp_path, capsys):
        good(tmp_path, "alpha")
        code, out = run(tmp_path, capsys, known_failures=tmp_path / "features")
        assert code != 0 and "known-failures record" in out

    def test_note_is_allowed_on_an_entry(self, tmp_path, capsys):
        bad(tmp_path, "beta")
        item = entry("feature", "beta", "nfrs-no-tbd")
        item["note"] = "Predates the placeholder check; tracked in the backlog."
        record = write_record(tmp_path.parent / f"{tmp_path.name}-r.json", [item])
        code, out = run(tmp_path, capsys, known_failures=record)
        assert code == 1 and "KNOWN  [nfrs-no-tbd]" in out


class TestRepositoryLevelChecks:
    def broken_fix(self, target: Path) -> None:
        fix = target / "fixes" / "bad-one"
        fix.mkdir(parents=True)
        (fix / "fix.yaml").write_text("id: [unclosed\n", encoding="utf-8")

    def test_fix_record_failure_counts_in_a_scoped_run(self, tmp_path, capsys):
        good(tmp_path, "alpha")
        self.broken_fix(tmp_path)
        code, out = run(tmp_path, capsys, features=["alpha"])
        assert code == 1
        assert "[fix-record]" in out and "fixes/bad-one/fix.yaml" in out

    def test_fix_record_failure_can_be_known(self, tmp_path, capsys):
        good(tmp_path, "alpha")
        self.broken_fix(tmp_path)
        document = json.loads(generate(tmp_path, capsys, features=["alpha"]))
        assert document["known_failures"] == [entry("fix", "fixes/bad-one/fix.yaml", "fix-record")]
        record = tmp_path.parent / f"{tmp_path.name}-r.json"
        record.write_text(json.dumps(document), encoding="utf-8")
        code, out = run(tmp_path, capsys, known_failures=record, features=["alpha"])
        assert code == 0 and "1 known" in out

    def test_approval_policy_failure_can_be_known(self, tmp_path, capsys):
        from cli.approval import POLICY_REL

        good(tmp_path, "alpha")
        policy = tmp_path / POLICY_REL
        policy.parent.mkdir(parents=True, exist_ok=True)
        policy.write_text("- not\n- a mapping\n", encoding="utf-8")
        code, out = run(tmp_path, capsys)
        assert code == 1 and "[approval-policy]" in out
        record = tmp_path.parent / f"{tmp_path.name}-r.json"
        record.write_text(generate(tmp_path, capsys), encoding="utf-8")
        assert run(tmp_path, capsys, known_failures=record)[0] == 0

    def test_strict_only_extension_failure_is_not_resolved_in_a_lenient_run(self, tmp_path, capsys):
        good(tmp_path, "alpha")
        (tmp_path / "extensions" / "broken").mkdir(parents=True)
        code, out = run(tmp_path, capsys, strict=True)
        assert code == 1 and "FAIL  [extension-manifest] broken:" in out
        record = tmp_path.parent / f"{tmp_path.name}-r.json"
        record.write_text(generate(tmp_path, capsys, strict=True), encoding="utf-8")
        assert json.loads(record.read_text(encoding="utf-8"))["known_failures"] == [
            entry("extension", "broken", "extension-manifest")
        ]
        code, out = run(tmp_path, capsys, known_failures=record, strict=True)
        assert code == 0 and "KNOWN  [extension-manifest]" in out
        code, out = run(tmp_path, capsys, known_failures=record)
        assert code == 0 and "WARN  [extension-manifest]" in out
        assert "0 resolved" in out and "1 record entry not applicable" in out

    def test_level_three_still_classifies_extension_failures(self, tmp_path, capsys):
        (tmp_path / "extensions" / "broken").mkdir(parents=True)
        capsys.readouterr()
        assert run_scoped_validation(tmp_path, level="3", strict=True, features=["x"]) == 1
        out = _ANSI.sub("", capsys.readouterr().out)
        assert "FAIL  [extension-manifest]" in out
        assert "0 feature(s) selected: 1 new failure(s)" in out


class TestCommand:
    def parser(self):
        parser = argparse.ArgumentParser()
        register(parser.add_subparsers())
        return parser

    def test_new_options_reach_the_scoped_runner(self, tmp_path, monkeypatch):
        seen = {}

        def scoped(target, **options):
            seen.update(options, target=target)
            return 4

        monkeypatch.setattr("cli.cmd_validate.run_scoped_validation", scoped)
        record = tmp_path / "r.json"
        args = self.parser().parse_args(
            [
                "validate",
                "--target",
                str(tmp_path),
                "--strict",
                "--only",
                "experiments",
                "--feature",
                "a",
                "--feature",
                "b",
                "--known-failures",
                str(record),
                "--known-failures-digest",
                "ab" * 32,
            ]
        )
        with pytest.raises(SystemExit) as excinfo:
            cmd_validate(args)
        assert excinfo.value.code == 4
        assert seen == {
            "target": tmp_path.resolve(),
            "level": None,
            "strict": True,
            "only": "experiments",
            "features": ["a", "b"],
            "known_failures": record,
            "expected_digest": "ab" * 32,
            "print_record": False,
        }

    def test_print_and_record_are_mutually_exclusive(self, tmp_path):
        with pytest.raises(SystemExit):
            self.parser().parse_args(
                [
                    "validate",
                    "--target",
                    ".",
                    "--known-failures",
                    "r.json",
                    "--print-known-failures",
                ]
            )

    def test_digest_requires_a_record(self, tmp_path, capsys):
        args = self.parser().parse_args(
            ["validate", "--target", str(tmp_path), "--known-failures-digest", "ab" * 32]
        )
        with pytest.raises(SystemExit) as excinfo:
            cmd_validate(args)
        assert excinfo.value.code not in (0, None)
        assert "--known-failures" in capsys.readouterr().out


class TestSchemaAndExample:
    def test_example_is_valid_and_every_check_identifier_is_registered(self):
        example = paths.GOVERNANCE_DIR / "examples/known-failures/known-failures.json"
        record = known_failures.load(example)
        assert record.entries
        assert {kind for kind, _name, _check, _finding in record.entries} == {
            "feature",
            "extension",
            "fix",
            "approval",
        }

    def test_schema_pins_the_scope_kinds(self):
        schema = json.loads(
            (paths.GOVERNANCE_DIR / "schemas/known-failures.schema.json").read_text(
                encoding="utf-8"
            )
        )
        assert set(schema["$defs"]["scope"]["properties"]["kind"]["enum"]) == set(
            known_failures.CHECKS_BY_SCOPE
        )

    def test_rendered_record_is_deterministic_and_valid(self, tmp_path):
        keys = [("feature", "b", "nfrs-no-tbd", None), ("feature", "a", "completeness", "plan.md")]
        text = known_failures.render(keys)
        assert text == known_failures.render(list(reversed(keys)) + keys[:1])
        path = tmp_path / "r.json"
        path.write_text(text, encoding="utf-8")
        assert known_failures.load(path).entries == frozenset(keys)
