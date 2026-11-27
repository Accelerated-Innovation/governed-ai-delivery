"""`govkit verification-run build`: the run for the Product Definition Graph, offline.

A verification run tells the graph what one build's tests and evaluations
found. The graph refuses a whole run when one result names a requirement its
baseline does not hold at that revision, so these tests are mostly about what
is left out, and that the rest is still sent.
"""

import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest

from cli import evidence_record, paths, tree_identity
from cli import verification_run as vr
from cli.schema_validation import validate_document

EXAMPLE = paths.GOVERNANCE_DIR / "examples" / "evidence-report"
BUNDLED = paths.GOVERNANCE_DIR / "examples" / "verification-run"
FEATURE = "07_invoice_approval"
TAG = "baseline-1"
BY_AMOUNT = f"{FEATURE}#scenario:approval-routing-by-amount"
ABSENT = f"{FEATURE}#scenario:approval-routing-when-manager-absent"
P95 = f"{FEATURE}#scenario:routing-completes-within-200-ms-at-p95"
REJECTED = f"{FEATURE}#scenario:a-rejected-invoice-returns-to-its-author"
FAITHFUL = f"{FEATURE}#evaluation:routing-explanation-faithfulness"
LATENCY = f"{FEATURE}#evaluation:routing-p95-latency"
SENT = {
    BY_AMOUNT: ("test", "passed"),
    ABSENT: ("test", "skipped"),
    P95: ("test", "failed"),
    FAITHFUL: ("evaluation", "passed"),
    LATENCY: ("evaluation", "failed"),
}
FACTS = dict(
    run_reference="github:1234567890-1",
    repository="acme/invoices",
    baseline_tag=TAG,
    build_reference="https://ci.example.invalid/runs/1234567890",
    artifact_reference="https://ci.example.invalid/runs/1234567890/artifacts/1",
)


def _git(repo: Path, *args: str) -> str:
    inherited = {k: v for k, v in os.environ.items() if k not in tree_identity._LOCATION_VARIABLES}
    environment = dict(
        inherited,
        GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.invalid",
        GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid",
        GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull,
    )  # fmt: skip
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True,
        env=environment,
    ).stdout.strip()  # fmt: skip


def _commit(repo: Path, message: str = "change") -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)


def _results(repo: Path) -> None:
    """The result files of a test run, and the record written straight after it."""
    shutil.copy(EXAMPLE / "evaluation-run.json", repo / "govkit-eval-results.json")
    shutil.copy(EXAMPLE / "test-run.xml", repo / "junit.xml")
    evidence_record.write_record(repo)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A committed feature, tagged as the baseline. No results yet."""
    root = tmp_path / "repo"
    directory = root / "features" / FEATURE
    directory.mkdir(parents=True)
    shutil.copy(EXAMPLE / "acceptance.feature", directory)
    shutil.copy(EXAMPLE / "eval_criteria.yaml", directory)
    (root / ".gitignore").write_text(
        "junit.xml\ngovkit-eval-results.json\ngovkit-evidence-record.json\n", encoding="utf-8"
    )
    _git(root, "init", "-q", "-b", "main")
    _commit(root, "project")
    _git(root, "tag", TAG)
    return root


def _build(repo: Path, **facts) -> dict:
    return vr.build(repo, vr.check_facts(**{**FACTS, **facts}))


def _reasons(document: dict) -> dict:
    return {(e["requirement_id"] or e["feature"]): e["reason"] for e in document["left_out"]}


def _edit(repo: Path, name: str, old: str, new: str) -> None:
    path = repo / "features" / FEATURE / name
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


class TestRequest:
    def test_results_at_the_baseline_revision_are_sent(self, repo):
        _results(repo)
        document = _build(repo)
        request = document["request"]
        assert {r["requirement_id"]: (r["kind"], r["result"]) for r in request["results"]} == SENT
        assert vr.exit_code(document) == 0

    def test_the_run_states_the_recorded_commit_and_time(self, repo):
        _results(repo)
        record = json.loads((repo / evidence_record.NAME).read_text(encoding="utf-8"))
        request = _build(repo)["request"]
        assert request["build"] == {
            "commit": _git(repo, "rev-parse", "HEAD"),
            "ref": FACTS["build_reference"],
        }
        assert request["executed_at"] == record["recorded_at"]
        assert request["baseline_tag"] == TAG
        assert request["repository"] == "acme/invoices"
        assert request["run_reference"] == "github:1234567890-1"
        assert request["artifact_reference"] == FACTS["artifact_reference"]

    def test_building_twice_gives_the_same_document(self, repo):
        # The graph answers an identical re-send with the stored run and a
        # different one under the same reference with a conflict.
        _results(repo)
        assert _build(repo) == _build(repo)

    def test_the_request_holds_only_what_the_graph_accepts(self, repo):
        _results(repo)
        request = _build(repo)["request"]
        assert set(request) == {
            "run_reference", "repository", "baseline_tag", "build",
            "executed_at", "artifact_reference", "results",
        }  # fmt: skip
        assert {key for result in request["results"] for key in result} == {
            "requirement_id", "revision_digest", "kind", "result",
        }  # fmt: skip
        assert [r["requirement_id"] for r in request["results"]] == sorted(SENT)

    def test_nothing_from_the_feature_text_or_the_results_is_in_the_request(self, repo):
        _results(repo)
        sent = json.dumps(_build(repo)["request"])
        for private in ("Invoice amount decides", "junit.xml", "0.91", "deepeval", "ratio"):
            assert private not in sent

    def test_the_document_validates(self, repo):
        _results(repo)
        validate_document(_build(repo), vr.SCHEMA)


class TestLeftOut:
    def test_a_requirement_with_no_result_is_left_out(self, repo):
        _results(repo)
        document = _build(repo)
        assert _reasons(document) == {
            REJECTED: vr.NO_RESULT,
            f"{FEATURE}#evaluation:refusal-safety": vr.NO_RESULT,
            f"{FEATURE}#evaluation:explanation-tone-review": vr.NO_RESULT,
        }
        assert document["summary"] == {
            "features": 1,
            "sent": 5,
            "left_out": 3,
            "reasons": {**{code: 0 for code in vr.CODES}, vr.NO_RESULT: 3},
        }
        assert document["features"] == [
            {"name": FEATURE, "evidence": "current", "sent": 5, "left_out": 3}
        ]

    def test_a_scenario_edited_since_the_baseline_is_left_out_and_the_rest_sent(self, repo):
        _edit(
            repo,
            "acceptance.feature",
            "Given an invoice of <amount>",
            "Given a new invoice of <amount>",
        )
        _commit(repo)
        _results(repo)
        document = _build(repo)
        assert _reasons(document)[BY_AMOUNT] == vr.REVISION_CHANGED
        assert {r["requirement_id"] for r in document["request"]["results"]} == set(SENT) - {
            BY_AMOUNT
        }

    def test_a_scenario_added_since_the_baseline_is_left_out(self, repo):
        _git(repo, "tag", "-d", TAG)
        _edit(repo, "acceptance.feature", "@scenario:approval-routing-by-amount", "@scenario:old")
        _commit(repo)
        _git(repo, "tag", TAG)
        _edit(repo, "acceptance.feature", "@scenario:old", "@scenario:approval-routing-by-amount")
        _commit(repo)
        _results(repo)
        document = _build(repo)
        assert _reasons(document)[BY_AMOUNT] == vr.NOT_IN_BASELINE
        assert len(document["request"]["results"]) == 4

    def test_an_edited_criteria_file_changes_every_criterion(self, repo):
        # A criterion's revision is the digest of the whole file.
        _edit(repo, "eval_criteria.yaml", "# Example criteria", "# Criteria")
        _commit(repo)
        _results(repo)
        reasons = _reasons(_build(repo))
        assert reasons[FAITHFUL] == reasons[LATENCY] == vr.REVISION_CHANGED

    def test_a_feature_the_baseline_lacks_sends_nothing(self, repo):
        other = repo / "features" / "08_refunds"
        shutil.copytree(repo / "features" / FEATURE, other)
        shutil.rmtree(repo / "features" / FEATURE)
        _commit(repo)
        _results(repo)
        document = vr.build(repo, vr.check_facts(**FACTS))
        # The example's tests name the other feature, so nothing binds here.
        assert document["request"] is None
        assert vr.exit_code(document) == 1

    def test_a_feature_absent_at_the_baseline_is_not_in_it(self, repo):
        _git(repo, "tag", "-d", TAG)
        _git(repo, "commit", "-q", "--allow-empty", "-m", "later")
        first = _git(repo, "rev-list", "--max-parents=0", "HEAD")
        _git(repo, "checkout", "-q", "--orphan", "empty")
        _git(repo, "rm", "-rq", "--cached", ".")
        _git(repo, "commit", "-q", "--allow-empty", "-m", "nothing")
        _git(repo, "tag", TAG)
        _git(repo, "checkout", "-q", "-f", "main")
        assert first
        _results(repo)
        document = _build(repo)
        assert document["request"] is None
        assert {reason for key, reason in _reasons(document).items() if key in SENT} == {
            vr.NOT_IN_BASELINE
        }

    def test_a_baseline_file_that_cannot_be_identified_leaves_the_feature_out(self, repo):
        _git(repo, "tag", "-d", TAG)
        path = repo / "features" / FEATURE / "acceptance.feature"
        good = path.read_bytes()
        path.write_bytes(
            good + b"\n  Scenario: Twin\n    Given x\n\n  Scenario: Twin\n    Given y\n"
        )
        _commit(repo, "collides")
        _git(repo, "tag", TAG)
        path.write_bytes(good)
        _commit(repo, "repaired")
        _results(repo)
        document = _build(repo)
        assert document["request"] is None
        assert set(_reasons(document).values()) == {vr.BASELINE_UNREADABLE, vr.NO_RESULT}

    def test_a_baseline_file_behind_a_link_leaves_the_feature_out(self, repo):
        _git(repo, "tag", "-d", TAG)
        path = repo / "features" / FEATURE / "acceptance.feature"
        good = path.read_bytes()
        (repo / "elsewhere.feature").write_bytes(good)
        path.unlink()
        path.symlink_to("../../elsewhere.feature")
        _commit(repo, "linked")
        _git(repo, "tag", TAG)
        path.unlink()
        path.write_bytes(good)
        _commit(repo, "repaired")
        _results(repo)
        assert vr.BASELINE_UNREADABLE in _reasons(_build(repo)).values()


class TestResultsThatDoNotCount:
    def test_without_result_files_nothing_is_sent(self, repo):
        document = _build(repo)
        assert document["request"] is None
        assert set(_reasons(document).values()) == {vr.NO_RESULT}
        assert document["features"][0]["evidence"] == "not-checked"

    def test_results_without_a_record_are_not_sent(self, repo):
        _results(repo)
        (repo / evidence_record.NAME).unlink()
        document = _build(repo)
        assert document["request"] is None
        assert _reasons(document) == {FEATURE: vr.RESULTS_NOT_CURRENT}
        assert document["features"][0]["evidence"] == "unrecorded"

    def test_results_from_another_commit_are_not_sent(self, repo):
        _results(repo)
        (repo / "app.py").write_text("x = 1\n", encoding="utf-8")
        _commit(repo)
        document = _build(repo)
        assert _reasons(document) == {FEATURE: vr.RESULTS_NOT_CURRENT}
        assert document["features"][0]["evidence"] == "stale"

    def test_results_from_an_uncommitted_tree_are_not_sent(self, repo):
        # The run names a commit. A tree that differed from it ran other code.
        (repo / "app.py").write_text("x = 1\n", encoding="utf-8")
        _results(repo)
        document = _build(repo)
        assert document["request"] is None
        assert _reasons(document) == {FEATURE: vr.TREE_NOT_CLEAN}

    def test_a_feature_that_cannot_be_read_is_left_out_whole(self, repo):
        path = repo / "features" / FEATURE / "acceptance.feature"
        path.write_bytes(
            path.read_bytes() + b"\n  Scenario: Twin\n    Given x\n\n  Scenario: Twin\n"
        )
        _commit(repo)
        _results(repo)
        document = _build(repo)
        assert _reasons(document) == {FEATURE: vr.FEATURE_UNREADABLE}

    def test_one_feature_left_out_does_not_stop_another(self, repo):
        other = repo / "features" / "08_refunds"
        other.mkdir()
        (other / "acceptance.feature").write_text(
            "Feature: Refunds\n\n  Scenario: Twin\n    Given x\n\n  Scenario: Twin\n    Given y\n",
            encoding="utf-8",
        )
        _commit(repo)
        _results(repo)
        document = _build(repo)
        assert _reasons(document)["08_refunds"] == vr.FEATURE_UNREADABLE
        assert len(document["request"]["results"]) == 5
        assert [f["name"] for f in document["features"]] == [FEATURE, "08_refunds"]


class TestBaseline:
    def test_a_tag_that_does_not_exist_stops_the_run(self, repo):
        _results(repo)
        with pytest.raises(vr.RunError, match="no tag named"):
            _build(repo, baseline_tag="v9")

    @pytest.mark.parametrize("name", ["main", "HEAD"])
    def test_a_branch_is_not_a_baseline(self, repo, name):
        _results(repo)
        with pytest.raises(vr.RunError, match="baseline"):
            _build(repo, baseline_tag=name)

    def test_an_annotated_tag_is_read(self, repo):
        _git(repo, "tag", "-a", "v1", "-m", "release")
        _results(repo)
        assert len(_build(repo, baseline_tag="v1")["request"]["results"]) == 5

    def test_outside_a_repository_the_run_stops(self, tmp_path):
        (tmp_path / "features").mkdir()
        with pytest.raises(vr.RunError, match="baseline"):
            vr.build(tmp_path, vr.check_facts(**FACTS))


class TestFacts:
    @pytest.mark.parametrize(
        "fact, value",
        [
            ("run_reference", "1234"),
            ("run_reference", "GitHub:1"),
            ("run_reference", "github:" + "1" * 129),
            ("repository", "invoices"),
            ("repository", "acme/invoices/extra"),
            ("baseline_tag", ""),
            ("build_reference", "   "),
            ("artifact_reference", "http://ci.example.invalid/1"),
            ("artifact_reference", "https://ci.example.invalid/a b"),
            ("artifact_reference", "https://" + "a" * 2048),
        ],
    )
    def test_a_fact_the_graph_would_refuse_stops_the_run(self, fact, value):
        with pytest.raises(vr.RunError):
            vr.check_facts(**{**FACTS, fact: value})

    def test_surrounding_space_is_dropped_as_the_graph_does(self):
        facts = vr.check_facts(**{**FACTS, "build_reference": " 77 "})
        assert facts.build_reference == "77"


class TestProjection:
    def _report(self, name, results, state="current", outcome="PASS", sources=()):
        return {
            "feature": {"name": name},
            "outcome": outcome,
            "sources": list(sources),
            "results": results,
            "provenance": {"state": state},
        }

    def _result(self, identifier, outcome="passed", kind="test"):
        return {
            "requirement_id": identifier,
            "revision_digest": "a" * 64,
            "kind": kind,
            "outcome": outcome,
        }

    RECORD = {"commit": "c" * 40, "recorded_at": "2026-11-24T12:00:00Z", "clean": True}

    def test_a_requirement_of_the_other_kind_is_not_in_the_baseline(self):
        report = self._report("f", [self._result("f#x")])
        document = vr.project(
            [report], {"f": {"f#x": ("evaluation", "a" * 64)}}, vr.check_facts(**FACTS), self.RECORD
        )
        assert _reasons(document) == {"f#x": vr.NOT_IN_BASELINE}

    def test_a_pass_is_not_sent_when_a_result_file_hides_its_skips(self):
        results = [self._result("f#passed"), self._result("f#failed", "failed")]
        results.append(self._result("f#scored", kind="evaluation"))
        unmarked = [{"tool": "junit", "unidentified_skipped": 2}]
        baseline = {r["requirement_id"]: (r["kind"], "a" * 64) for r in results}
        document = vr.project(
            [self._report("f", results, outcome="INCONCLUSIVE", sources=unmarked)],
            {"f": baseline}, vr.check_facts(**FACTS), self.RECORD,
        )  # fmt: skip
        assert _reasons(document) == {"f#passed": vr.SKIPS_UNMARKED}
        assert len(document["request"]["results"]) == 2

    def test_an_error_in_stale_results_is_stale_and_not_unreadable(self):
        report = self._report("f", [self._result("f#x", "error")], "stale", "ERROR")
        document = vr.project([report], {}, vr.check_facts(**FACTS), self.RECORD)
        assert _reasons(document) == {"f": vr.RESULTS_NOT_CURRENT}

    def test_more_results_than_the_graph_accepts_stop_the_run(self):
        results = [self._result(f"f#{n}") for n in range(vr.RESULT_BUDGET + 1)]
        baseline = {r["requirement_id"]: ("test", "a" * 64) for r in results}
        with pytest.raises(vr.RunError, match="at most 5000"):
            vr.project(
                [self._report("f", results)], {"f": baseline},
                vr.check_facts(**FACTS), self.RECORD,
            )  # fmt: skip

    def test_a_requirement_named_twice_stops_the_run(self):
        reports = [self._report(n, [self._result("f#x")]) for n in ("f", "g")]
        baseline = {"f#x": ("test", "a" * 64)}
        with pytest.raises(vr.RunError, match="same requirement"):
            vr.project(
                reports, {"f": baseline, "g": baseline}, vr.check_facts(**FACTS), self.RECORD
            )

    def test_a_commit_the_graph_would_refuse_stops_the_run(self):
        # A repository with SHA-256 object names has 64-character commits.
        report = self._report("f", [self._result("f#x")])
        record = {**self.RECORD, "commit": "c" * 64}
        with pytest.raises(vr.RunError, match="commit"):
            vr.project(
                [report], {"f": {"f#x": ("test", "a" * 64)}}, vr.check_facts(**FACTS), record
            )

    def test_the_reasons_are_a_closed_set_the_schema_shares(self):
        schema = json.loads(
            (paths.GOVERNANCE_DIR / "schemas" / "verification-run.schema.json").read_text(
                encoding="utf-8"
            )
        )
        assert tuple(schema["$defs"]["reason"]["enum"]) == vr.CODES
        reasons = schema["properties"]["summary"]["properties"]["reasons"]
        assert tuple(reasons["required"]) == tuple(reasons["properties"]) == vr.CODES
        states = schema["properties"]["features"]["items"]["properties"]["evidence"]["enum"]
        assert tuple(states) == evidence_record.STATES
        request = schema["$defs"]["request"]["properties"]
        assert tuple(request["results"]["items"]["properties"]["result"]["enum"]) == vr.OUTCOMES
        assert request["results"]["maxItems"] == vr.RESULT_BUDGET
        assert request["run_reference"]["pattern"] == f"^{vr.RUN_REFERENCE.pattern}$"
        assert request["build"]["properties"]["commit"]["pattern"] == f"^{vr.COMMIT.pattern}$"


class TestBundledExample:
    def test_the_example_is_the_real_output_for_its_own_inputs(self, tmp_path):
        directory = tmp_path / "features" / FEATURE
        directory.mkdir(parents=True)
        shutil.copy(EXAMPLE / "acceptance.feature", directory)
        shutil.copy(EXAMPLE / "eval_criteria.yaml", directory)
        shutil.copy(EXAMPLE / "evaluation-run.json", tmp_path / "govkit-eval-results.json")
        shutil.copy(EXAMPLE / "test-run.xml", tmp_path / "junit.xml")

        def tree(target, exclude=()):
            return tree_identity.Identity("c" * 40, "d" * 64, True)

        evidence_record.write_record(
            tmp_path, observe=tree, now=datetime(2026, 11, 24, 12, 0, 0, tzinfo=timezone.utc)
        )
        baseline = {
            f"features/{FEATURE}/acceptance.feature": (
                BUNDLED / "acceptance.baseline.feature"
            ).read_bytes(),
            f"features/{FEATURE}/eval_criteria.yaml": (EXAMPLE / "eval_criteria.yaml").read_bytes(),
        }
        document = vr.build(tmp_path, vr.check_facts(**FACTS), observe=tree, read=baseline.get)
        example = json.loads((BUNDLED / "verification-run.json").read_text(encoding="utf-8"))
        validate_document(example, vr.SCHEMA)
        assert document == example
        # The example shows each of the common reasons beside results that are sent.
        assert {e["reason"] for e in example["left_out"]} == {
            vr.NO_RESULT, vr.NOT_IN_BASELINE, vr.REVISION_CHANGED,
        }  # fmt: skip
        assert example["request"]["results"]


def _run(monkeypatch, capsys, repo: Path, *extra: str, **facts) -> tuple[int, str, str]:
    from cli import govkit

    stated = {**FACTS, **facts}
    monkeypatch.setattr(
        "sys.argv",
        [
            "govkit", "verification-run", "build", "--target", str(repo),
            "--baseline", stated["baseline_tag"],
            "--repository", stated["repository"],
            "--run-reference", stated["run_reference"],
            "--build-ref", stated["build_reference"],
            "--artifact", stated["artifact_reference"],
            *extra,
        ],
    )  # fmt: skip
    with pytest.raises(SystemExit) as stopped:
        govkit.main()
    captured = capsys.readouterr()
    return stopped.value.code, captured.out, captured.err


class TestCommand:
    def test_the_document_is_printed_and_the_account_goes_to_standard_error(
        self, repo, monkeypatch, capsys
    ):
        _results(repo)
        code, out, err = _run(monkeypatch, capsys, repo)
        assert code == 0
        assert json.loads(out) == _build(repo)
        assert "5 result(s) to send from 1 feature(s); 3 left out." in err
        assert "3 left out: no-result" in err

    def test_nothing_to_send_exits_1_and_still_prints_the_document(self, repo, monkeypatch, capsys):
        code, out, err = _run(monkeypatch, capsys, repo)
        assert code == 1
        assert json.loads(out)["request"] is None
        assert "Nothing can be sent." in err

    def test_a_run_that_cannot_start_exits_2_and_prints_no_document(
        self, repo, monkeypatch, capsys
    ):
        code, out, err = _run(monkeypatch, capsys, repo, baseline_tag="v9")
        assert (code, out) == (2, "")
        assert "no tag named" in err
        code, out, _ = _run(monkeypatch, capsys, repo, repository="invoices")
        assert (code, out) == (2, "")

    def test_the_document_is_written_to_a_new_file_outside_the_target(
        self, repo, tmp_path, monkeypatch, capsys
    ):
        _results(repo)
        output = tmp_path / "run.json"
        code, out, _ = _run(monkeypatch, capsys, repo, "--output", str(output))
        assert (code, out) == (0, "")
        assert json.loads(output.read_text(encoding="utf-8")) == _build(repo)

    def test_an_existing_file_is_never_replaced(self, repo, tmp_path, monkeypatch, capsys):
        _results(repo)
        output = tmp_path / "run.json"
        output.write_text("mine", encoding="utf-8")
        code, _, err = _run(monkeypatch, capsys, repo, "--output", str(output))
        assert code == 2 and "never replaced" in err
        assert output.read_text(encoding="utf-8") == "mine"

    def test_a_file_inside_the_target_is_refused(self, repo, monkeypatch, capsys):
        # A new file in the tree would make the recorded results stale.
        _results(repo)
        code, _, _ = _run(monkeypatch, capsys, repo, "--output", str(repo / "run.json"))
        assert code == 2
        assert not (repo / "run.json").exists()

    def test_the_command_writes_nothing_in_the_target(self, repo, monkeypatch, capsys):
        _results(repo)
        before = sorted(p.as_posix() for p in repo.rglob("*") if ".git/" not in p.as_posix())
        _run(monkeypatch, capsys, repo)
        after = sorted(p.as_posix() for p in repo.rglob("*") if ".git/" not in p.as_posix())
        assert before == after
        assert _build(repo)["features"][0]["evidence"] == "current"
