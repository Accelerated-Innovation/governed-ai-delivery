"""Tests for cli/experiments.py — experiment records and preflight outcomes.

These are tooling tests over synthetic records. They establish how GovKit
assesses supplied records; they say nothing about any application runtime.
"""

from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone

import pytest

from cli.experiments import (
    assess,
    criteria_digest,
    inputs_digest,
    parse_experiment_set,
    parse_preflight_outcome,
    result_digest,
)
from cli.schema_validation import DocumentError, content_digest

RECORD = "features/discovery/experiments.yaml"
NOW = datetime(2026, 11, 10, tzinfo=timezone.utc)

FILES = {
    "features/discovery/acceptance.feature": b"Feature: discovery\n",
    "skills/interview/SKILL.md": b"---\nname: interview\n---\n",
    "src/runtime/selection.py": b"def select(): ...\n",
    "build/eval/ac1.json": b'{"cases": 50, "violations": 0}\n',
    "build/eval/ac2.json": b'{"null_choice": true}\n',
}


def digest_of(files):
    return lambda path: content_digest(files[path]) if path in files else None


def experiment(**overrides):
    base = {
        "id": "EXP-001",
        "title": "Single-agent discovery skill selection",
        "uncertainty": "Can trusted code admit and select among three skills?",
        "hypothesis": "Admission before ranking plus a null option preserves activation controls.",
        "decisions_affected": [
            {
                "kind": "preflight-section",
                "reference": "features/discovery/architecture_preflight.md",
            }
        ],
        "requirements": [
            {
                "path": "features/discovery/acceptance.feature",
                "digest": content_digest(FILES["features/discovery/acceptance.feature"]),
            }
        ],
        "scope": {"paths": ["src/runtime"], "permitted_effects": "none", "excluded": []},
        "conditions": ["synthetic catalog"],
        "oracle": "deterministic-test",
        "required_evidence_class": "synthetic-fixture",
        "acceptance_criteria": [
            {"id": "AC-1", "statement": "Revoked release never activates", "threshold": "0 of 50"},
            {"id": "AC-2", "statement": "Null choice is offered", "threshold": "always"},
        ],
        "limits": {"budget": "2 days", "stop_when": ["authority counterexample"]},
        "depends_on": [
            {
                "kind": "skill",
                "path": "skills/interview/SKILL.md",
                "digest": content_digest(FILES["skills/interview/SKILL.md"]),
            },
            {
                "kind": "implementation",
                "path": "src/runtime/selection.py",
                "digest": content_digest(FILES["src/runtime/selection.py"]),
            },
        ],
        "status": "planned",
    }
    base.update(overrides)
    return base


def with_result(
    exp,
    *,
    outcomes=("pass", "pass"),
    status=None,
    evidence_class=None,
    observed_at="2026-11-01T10:00:00Z",
    decision="adopt",
    decided_at="2026-11-01T12:00:00Z",
):
    """Complete an experiment with a result whose digests match current inputs."""
    exp = copy.deepcopy(exp)
    criteria = []
    for criterion, outcome in zip(exp["acceptance_criteria"], outcomes, strict=False):
        evidence_path = f"build/eval/{criterion['id'].lower().replace('-', '')}.json"
        criteria.append(
            {
                "id": criterion["id"],
                "outcome": outcome,
                "evidence": [
                    {
                        "path": evidence_path,
                        "digest": content_digest(FILES[evidence_path]),
                        "producer": "test-run",
                    }
                ],
            }
        )
    exp["result"] = {
        "observed_at": observed_at,
        "evidence_class": evidence_class or exp["required_evidence_class"],
        "criteria_digest": criteria_digest(exp["acceptance_criteria"]),
        "inputs_digest": inputs_digest(exp["depends_on"]),
        "criteria": criteria,
        "summary": "Synthetic fixture run.",
        "limitations": ["Synthetic fixture only."],
    }
    if status is None:
        status = (
            "passed"
            if all(o == "pass" for o in outcomes)
            else ("failed" if "fail" in outcomes else "inconclusive")
        )
    exp["status"] = status
    if decision:
        exp["decision"] = {
            "outcome": decision,
            "reference": "features/discovery/architecture_preflight.md",
            "recorded_at": decided_at,
        }
    return exp


def record(*experiments):
    return {
        "schema_version": 1,
        "kind": "experiment-set",
        "feature": "discovery",
        "experiments": list(experiments),
    }


def run(document=None, outcome=None, *, files=FILES, now=NOW, extra=None):
    records = {} if document is None else {RECORD: document}
    records.update(extra or {})
    return assess(outcome, records, default_record=RECORD, read_digest=digest_of(files), now=now)


def codes(assessment, severity=None):
    return sorted(f.code for f in assessment.findings if severity is None or f.severity == severity)


def state(assessment, experiment_id="EXP-001"):
    return next(s for s in assessment.experiments if s.id == experiment_id)


def outcome_block(status, **fields):
    return {"status": status, "reason": "Recorded in preflight", **fields}


# ---------------------------------------------------------------------------
# Record parsing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", ["experiment-set", "preflight-outcome"])
def test_schemas_are_valid_json_schema(name):
    import json

    from jsonschema import Draft202012Validator

    from cli import paths

    schema = json.loads(
        (paths.GOVERNANCE_DIR / "schemas" / f"{name}.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    assert schema["$id"] == f"urn:governed-ai-delivery:schemas:{name}"


class TestParseExperimentSet:
    def test_valid_record_parses(self):
        document = record(with_result(experiment()))
        assert parse_experiment_set(document) == document

    @pytest.mark.parametrize(
        "mutate",
        [
            lambda d: d.update(schema_version=2),
            lambda d: d.update(unexpected=True),
            lambda d: d["experiments"][0].update(id="EXP-1"),
            lambda d: d["experiments"][0].update(status="done"),
            lambda d: d["experiments"][0]["scope"].update(paths=["/abs/path"]),
            lambda d: d["experiments"][0]["scope"].update(paths=["src/../secrets"]),
            lambda d: d["experiments"][0]["scope"].update(paths=["src/**/*.py"]),
            lambda d: d["experiments"][0]["requirements"][0].update(digest="sha256:" + "a" * 64),
            lambda d: d["experiments"][0].update(acceptance_criteria=[]),
            lambda d: d["experiments"][0].update(waiver="accepted risk"),
            lambda d: d["experiments"][0]["result"].update(observed_at="2026-11-01"),
            lambda d: d["experiments"][0]["result"].update(observed_at="2026-11-01T10:00:00"),
        ],
        ids=[
            "version",
            "top-level-key",
            "id-pattern",
            "status",
            "absolute-path",
            "parent-path",
            "glob-path",
            "prefixed-digest",
            "no-criteria",
            "waiver-field",
            "date-only",
            "naive-timestamp",
        ],
    )
    def test_rejects_invalid_records(self, mutate):
        document = record(with_result(experiment()))
        mutate(document)
        with pytest.raises(DocumentError):
            parse_experiment_set(document)

    def test_rejects_duplicate_experiment_ids(self):
        with pytest.raises(DocumentError, match="Duplicate experiment"):
            parse_experiment_set(record(experiment(), experiment()))

    def test_rejects_duplicate_criterion_ids(self):
        exp = experiment()
        exp["acceptance_criteria"][1]["id"] = "AC-1"
        with pytest.raises(DocumentError, match="Duplicate acceptance criterion"):
            parse_experiment_set(record(exp))

    def test_planned_experiment_cannot_carry_result(self):
        exp = with_result(experiment(), status="planned", decision=None)
        with pytest.raises(DocumentError):
            parse_experiment_set(record(exp))

    def test_narrowing_requires_requirement_change(self):
        exp = with_result(
            experiment(), outcomes=("fail", "pass"), decision="narrow-supported-behavior"
        )
        with pytest.raises(DocumentError):
            parse_experiment_set(record(exp))
        exp["decision"]["requirement_change"] = "adr/0004-narrow-discovery.md"
        parse_experiment_set(record(exp))


# ---------------------------------------------------------------------------
# Preflight outcome block
# ---------------------------------------------------------------------------


class TestParsePreflightOutcome:
    def test_absent_block_returns_none(self):
        assert parse_preflight_outcome("# Preflight\n\n```yaml\nother: 1\n```\n") is None

    def test_parses_single_block(self):
        text = (
            "# Preflight\n\n## 9. Conclusion\n\n```yaml\npreflight_outcome:\n"
            "  status: experiment-required\n  reason: Untested selection boundary\n"
            "  experiments: [EXP-001]\n```\n"
        )
        assert parse_preflight_outcome(text) == {
            "status": "experiment-required",
            "reason": "Untested selection boundary",
            "experiments": ["EXP-001"],
        }

    @pytest.mark.parametrize(
        "body",
        [
            "preflight_outcome:\n  status: aligned\n  reason: x\n",
            "preflight_outcome:\n  status: experiment-required\n  reason: x\n",
            "preflight_outcome:\n  status: approved-for-planning\n  reason: x\n"
            "  experiments: [EXP-001]\n",
            "preflight_outcome:\n  status: blocked\n  reason: x\n  status: approved-for-planning\n",
            "preflight_outcome:\n  status: &s blocked\n  reason: *s\n",
        ],
        ids=[
            "unknown-status",
            "missing-experiments",
            "experiments-when-approved",
            "duplicate-key",
            "alias",
        ],
    )
    def test_rejects_invalid_blocks(self, body):
        with pytest.raises(DocumentError):
            parse_preflight_outcome(f"```yaml\n{body}```\n")

    def test_rejects_more_than_one_block(self):
        block = "```yaml\npreflight_outcome:\n  status: blocked\n  reason: x\n```\n"
        with pytest.raises(DocumentError, match="exactly one"):
            parse_preflight_outcome(block + "\n" + block)


# ---------------------------------------------------------------------------
# Assessment: established boundaries need nothing
# ---------------------------------------------------------------------------


class TestShortPath:
    def test_approved_outcome_without_experiments_is_ready(self):
        assessment = run(outcome=outcome_block("approved-for-planning"))
        assert assessment.findings == ()
        assert assessment.ready_for_completion

    def test_nothing_declared_is_ready(self):
        assessment = run()
        assert assessment.findings == () and assessment.experiments == ()


# ---------------------------------------------------------------------------
# Outstanding work
# ---------------------------------------------------------------------------


class TestOutstanding:
    @pytest.mark.parametrize("status", ["planned", "running"])
    def test_in_progress_experiment_is_outstanding(self, status):
        assessment = run(record(experiment(status=status)))
        assert codes(assessment) == ["experiment-outstanding"]
        assert state(assessment).effective == status
        assert not assessment.ready_for_completion

    def test_experiment_required_outcome_is_outstanding(self):
        assessment = run(
            record(experiment()),
            outcome_block("experiment-required", experiments=["EXP-001"]),
        )
        assert codes(assessment, "outstanding") == ["experiment-outstanding", "experiment-required"]
        assert codes(assessment, "error") == []

    @pytest.mark.parametrize(
        ("status", "code"), [("adr-required", "adr-required"), ("blocked", "preflight-blocked")]
    )
    def test_unresolved_outcomes_are_outstanding(self, status, code):
        assert codes(run(outcome=outcome_block(status))) == [code]

    def test_result_without_decision_requires_decision(self):
        assessment = run(record(with_result(experiment(), decision=None)))
        assert codes(assessment) == ["decision-required"]
        assert state(assessment).effective == "passed"

    def test_rerun_decision_stays_outstanding(self):
        exp = with_result(experiment(), outcomes=("pass", "unknown"), decision="rerun")
        assert codes(run(record(exp))) == ["rerun-pending"]

    def test_withdrawn_experiment_needs_nothing(self):
        assessment = run(record(experiment(status="withdrawn")))
        assert assessment.findings == ()
        assert state(assessment).effective == "withdrawn"


# ---------------------------------------------------------------------------
# Results and decisions
# ---------------------------------------------------------------------------


class TestResults:
    def test_passed_and_adopted_is_ready(self):
        assessment = run(record(with_result(experiment())))
        assert assessment.findings == ()
        assert state(assessment).effective == "passed"
        assert state(assessment).decision == "adopt"

    def test_failed_experiment_closed_by_revision(self):
        exp = with_result(experiment(), outcomes=("fail", "pass"), decision="revise-design")
        assessment = run(record(exp))
        assert assessment.findings == ()
        assert state(assessment).effective == "failed"

    def test_adopting_a_failed_experiment_is_an_error(self):
        exp = with_result(experiment(), outcomes=("fail", "pass"), decision="adopt")
        assert "adopt-without-pass" in codes(run(record(exp)), "error")

    @pytest.mark.parametrize(
        ("outcomes", "declared"),
        [
            (("fail", "pass"), "passed"),
            (("pass", "pass"), "failed"),
            (("pass", "unknown"), "passed"),
            (("fail", "pass"), "inconclusive"),
        ],
    )
    def test_declared_status_must_match_criteria(self, outcomes, declared):
        exp = with_result(experiment(), outcomes=outcomes, status=declared, decision=None)
        assert "status-contradiction" in codes(run(record(exp)), "error")

    def test_unknown_criterion_result_is_invalid(self):
        exp = with_result(experiment())
        exp["result"]["criteria"][1]["id"] = "AC-9"
        assessment = run(record(exp))
        assert {"unknown-criterion", "missing-criterion-result"} <= set(codes(assessment, "error"))
        assert state(assessment).effective == "invalid"

    def test_duplicate_criterion_result_is_invalid(self):
        exp = with_result(experiment())
        exp["result"]["criteria"][1]["id"] = "AC-1"
        assert "duplicate-criterion-result" in codes(run(record(exp)), "error")

    def test_decision_cannot_precede_result(self):
        exp = with_result(experiment(), decided_at="2026-10-31T09:00:00Z")
        assert "decision-precedes-result" in codes(run(record(exp)), "error")

    def test_synthetic_evidence_cannot_satisfy_application_requirement(self):
        exp = with_result(
            experiment(required_evidence_class="application"),
            evidence_class="synthetic-fixture",
        )
        assessment = run(record(exp))
        assert "insufficient-evidence-class" in codes(assessment, "outstanding")
        assert "status-contradiction" in codes(assessment, "error")
        assert "adopt-without-pass" in codes(assessment, "error")
        assert state(assessment).effective == "inconclusive"

    def test_application_evidence_satisfies_synthetic_requirement(self):
        exp = with_result(experiment(), evidence_class="application")
        assert run(record(exp)).findings == ()

    def test_evidence_changed_after_result_is_an_error(self):
        files = dict(FILES, **{"build/eval/ac1.json": b'{"cases": 50, "violations": 3}\n'})
        assessment = run(record(with_result(experiment())), files=files)
        assert codes(assessment) == ["evidence-digest-mismatch"]

    def test_missing_evidence_is_unverifiable(self):
        files = {k: v for k, v in FILES.items() if k != "build/eval/ac2.json"}
        assessment = run(record(with_result(experiment())), files=files)
        assert codes(assessment) == ["unverifiable-evidence"]
        assert not assessment.ready_for_completion


# ---------------------------------------------------------------------------
# Invalidation
# ---------------------------------------------------------------------------


class TestInvalidation:
    @pytest.mark.parametrize(
        ("path", "code"),
        [
            ("features/discovery/acceptance.feature", "stale-requirement"),
            ("skills/interview/SKILL.md", "stale-dependency"),
            ("src/runtime/selection.py", "stale-dependency"),
        ],
    )
    def test_changed_inputs_make_results_stale(self, path, code):
        files = dict(FILES, **{path: FILES[path] + b"# changed\n"})
        assessment = run(record(with_result(experiment())), files=files)
        assert codes(assessment) == [code]
        assert state(assessment).effective == "stale"
        assert not assessment.ready_for_completion

    @pytest.mark.parametrize(
        "kind",
        ["requirement", "skill", "policy", "interface", "runtime", "implementation", "catalog"],
    )
    def test_every_dependency_kind_invalidates(self, kind):
        exp = experiment()
        exp["depends_on"] = [
            {
                "kind": kind,
                "path": "src/runtime/selection.py",
                "digest": content_digest(FILES["src/runtime/selection.py"]),
            }
        ]
        files = dict(FILES, **{"src/runtime/selection.py": b"changed\n"})
        assessment = run(record(with_result(exp)), files=files)
        assert codes(assessment) == ["stale-dependency"]
        assert kind in assessment.findings[0].message

    def test_editing_criteria_after_result_is_stale(self):
        exp = with_result(experiment())
        exp["acceptance_criteria"][0]["threshold"] = "at most 5 of 50"
        assert codes(run(record(exp))) == ["criteria-changed-after-result"]

    def test_repinning_dependencies_without_rerun_is_stale(self):
        exp = with_result(experiment())
        changed = dict(FILES, **{"src/runtime/selection.py": b"changed\n"})
        exp["depends_on"][1]["digest"] = content_digest(changed["src/runtime/selection.py"])
        assert codes(run(record(exp), files=changed)) == ["inputs-changed-after-result"]

    def test_unverifiable_dependency_is_unknown(self):
        files = {k: v for k, v in FILES.items() if k != "skills/interview/SKILL.md"}
        assessment = run(record(with_result(experiment())), files=files)
        assert codes(assessment) == ["unverifiable-dependency"]
        assert codes(assessment, "unknown") == ["unverifiable-dependency"]

    def test_unverifiable_requirement_is_unknown(self):
        files = {k: v for k, v in FILES.items() if k != "features/discovery/acceptance.feature"}
        assert codes(run(record(with_result(experiment())), files=files)) == [
            "unverifiable-requirement"
        ]

    def test_expired_result_is_stale(self):
        exp = experiment()
        exp["limits"]["expires_after_days"] = 5
        assessment = run(record(with_result(exp)))
        assert codes(assessment) == ["expired"]
        assert state(assessment).effective == "stale"

    def test_unexpired_result_is_current(self):
        exp = experiment()
        exp["limits"]["expires_after_days"] = 30
        assert run(record(with_result(exp))).findings == ()

    def test_expiry_without_clock_is_unknown(self):
        exp = experiment()
        exp["limits"]["expires_after_days"] = 30
        assert codes(run(record(with_result(exp)), now=None)) == ["expiry-unverifiable"]

    def test_result_after_clock_is_unknown(self):
        exp = experiment()
        exp["limits"]["expires_after_days"] = 30
        assessment = run(record(with_result(exp)), now=NOW - timedelta(days=30))
        assert codes(assessment) == ["result-in-future"]

    def test_closed_experiment_ignores_later_file_changes(self):
        exp = with_result(experiment(), outcomes=("fail", "pass"), decision="reject-approach")
        files = dict(FILES, **{"src/runtime/selection.py": b"rewritten\n"})
        files.pop("build/eval/ac1.json")
        assert run(record(exp), files=files).findings == ()


# ---------------------------------------------------------------------------
# Reliance and reuse
# ---------------------------------------------------------------------------


class TestReliance:
    def _relied(self, exp=None, **entry):
        exp = exp or with_result(experiment())
        reliance = {"experiment": exp["id"], "result_digest": result_digest(exp["result"])}
        reliance.update(entry)
        return exp, outcome_block("approved-for-planning", relies_on=[reliance])

    def test_current_reliance_is_ready(self):
        exp, outcome = self._relied()
        assessment = run(record(exp), outcome)
        assert assessment.findings == ()
        assert assessment.ready_for_completion

    def test_stale_reliance_is_an_error(self):
        exp, outcome = self._relied()
        files = dict(FILES, **{"features/discovery/acceptance.feature": b"Feature: changed\n"})
        assessment = run(record(exp), outcome, files=files)
        assert codes(assessment, "error") == ["stale-reliance"]
        assert codes(assessment, "outstanding") == ["stale-requirement"]

    def test_changed_result_breaks_reliance(self):
        exp, outcome = self._relied()
        exp["result"]["summary"] = "Rewritten after the reliance was recorded."
        assert codes(run(record(exp), outcome)) == ["stale-reliance"]

    def test_relying_on_unadopted_experiment_is_invalid(self):
        exp, outcome = self._relied(with_result(experiment(), decision=None))
        assert codes(run(record(exp), outcome), "error") == ["invalid-reliance"]

    def test_relying_on_failed_experiment_is_invalid(self):
        exp, outcome = self._relied(
            with_result(experiment(), outcomes=("fail", "pass"), decision="revise-design")
        )
        assert codes(run(record(exp), outcome)) == ["invalid-reliance"]

    def test_relying_on_unverifiable_experiment_is_unknown(self):
        exp, outcome = self._relied()
        files = {k: v for k, v in FILES.items() if k != "build/eval/ac1.json"}
        assessment = run(record(exp), outcome, files=files)
        assert "reliance-unverifiable" in codes(assessment, "unknown")
        assert codes(assessment, "error") == []

    def test_unknown_experiment_is_an_error(self):
        outcome = outcome_block("experiment-required", experiments=["EXP-404"])
        assert "unknown-experiment" in codes(run(record(experiment()), outcome), "error")

    def test_reliance_without_record_is_an_error(self):
        _, outcome = self._relied()
        assert codes(run(None, outcome)) == ["missing-record"]

    def test_reuses_another_features_passed_experiment(self):
        other = "features/onboarding/experiments.yaml"
        exp = with_result(experiment())
        other_record = dict(record(exp), feature="onboarding")
        _, outcome = self._relied(exp, record=other)
        assessment = run(None, outcome, extra={other: other_record})
        assert assessment.findings == ()

    def test_other_features_outstanding_work_does_not_leak(self):
        other = "features/onboarding/experiments.yaml"
        exp = with_result(experiment())
        pending = experiment(id="EXP-002", status="running")
        other_record = dict(record(exp, pending), feature="onboarding")
        _, outcome = self._relied(exp, record=other)
        assert run(None, outcome, extra={other: other_record}).findings == ()


# ---------------------------------------------------------------------------
# Invalid inputs surface as findings, not exceptions
# ---------------------------------------------------------------------------


class TestInvalidInputs:
    def test_unparseable_record_is_an_error(self):
        assessment = assess(
            None,
            {RECORD: "invalid YAML: duplicate key"},
            default_record=RECORD,
            read_digest=digest_of(FILES),
            now=NOW,
        )
        assert codes(assessment) == ["invalid-record"]

    def test_unparseable_outcome_is_an_error(self):
        assessment = assess(
            "invalid preflight_outcome",
            {},
            default_record=RECORD,
            read_digest=digest_of(FILES),
            now=NOW,
        )
        assert codes(assessment) == ["invalid-outcome"]

    def test_record_feature_must_match_its_folder(self):
        document = dict(record(experiment()), feature="elsewhere")
        assert "feature-mismatch" in codes(run(document))

    def test_assessment_is_deterministic(self):
        exp, outcome = TestReliance()._relied()
        files = dict(FILES, **{"src/runtime/selection.py": b"changed\n"})
        first = run(record(exp, experiment(id="EXP-002", status="running")), outcome, files=files)
        second = run(record(exp, experiment(id="EXP-002", status="running")), outcome, files=files)
        assert first == second
