"""One answer per feature: done, continue or escalate (L07a).

The module under test is pure: a feature evidence report and the results of the
checks that ran beside it.
"""

import pytest

from cli import feature_verdict as fv

FEATURE = "order_routing"
EVIDENCE_CHECK = "evidence:feature"


def _result(slug, outcome, kind="test", execution_class=None):
    result = {
        "requirement_id": f"{FEATURE}#{'scenario' if kind == 'test' else 'evaluation'}:{slug}",
        "kind": kind,
        "outcome": outcome,
    }
    if execution_class:
        result["execution_class"] = execution_class
    return result


def _evidence(*results, outcome=None, provenance="current", form="absent", sources=(), detail="d"):
    results = list(results) or [_result("routes-large-orders", "passed")]
    outcomes = {r["outcome"] for r in results}
    if outcome is None:
        if "error" in outcomes:
            outcome = "ERROR"
        elif "failed" in outcomes:
            outcome = "FAIL"
        elif outcomes != {"passed"} or provenance != "current" or form == "data":
            outcome = "INCONCLUSIVE"
        else:
            outcome = "PASS"
    return {
        "feature": {"name": FEATURE, "criteria": {"form": form}},
        "outcome": outcome,
        "detail": detail,
        "summary": {"scenarios": sum(r["kind"] == "test" for r in results)},
        "sources": list(sources),
        "results": results,
        "provenance": {"state": provenance, "detail": "why"},
    }


def _checks(evidence, **states):
    listed = {
        "change:scope": "pass",
        EVIDENCE_CHECK: {"PASS": "pass", "FAIL": "fail"}.get(evidence["outcome"], "unknown"),
    }
    listed.update({name.replace("__", ":"): state for name, state in states.items()})
    return [fv.Check(name, True, state) for name, state in sorted(listed.items())]


def _decide(evidence=None, **states):
    evidence = evidence or _evidence()
    return fv.decide(evidence, _checks(evidence, **states))


def _codes(verdict):
    return [(reason["state"], reason["code"]) for reason in verdict["reasons"]]


class TestDone:
    def test_done_when_every_check_and_result_passed(self):
        verdict = _decide()
        assert verdict["state"] == "done" and verdict["reasons"] == []
        assert verdict["feature"] == FEATURE and verdict["exit_code"] == 0

    def test_an_advisory_check_that_is_not_satisfied_does_not_prevent_done(self):
        evidence = _evidence()
        checks = _checks(evidence) + [fv.Check("legacy:doctor", False, "not-applicable")]
        assert fv.decide(evidence, checks)["state"] == "done"

    def test_a_check_that_is_not_applicable_and_required_is_not_done(self):
        verdict = _decide(artifact__spec="not-applicable")
        assert verdict["state"] == "escalate"


class TestContinue:
    def test_a_failed_scenario(self):
        verdict = _decide(_evidence(_result("a", "failed"), _result("b", "passed")))
        assert verdict["state"] == "continue" and verdict["exit_code"] == 1
        assert _codes(verdict) == [("continue", "result-failed")]
        assert verdict["reasons"][0]["requirements"] == [f"{FEATURE}#scenario:a"]
        assert verdict["reasons"][0]["check"] == EVIDENCE_CHECK

    def test_a_missing_result(self):
        verdict = _decide(_evidence(_result("a", "missing")))
        assert _codes(verdict) == [("continue", "result-missing")]

    def test_a_missing_free_criterion(self):
        evidence = _evidence(
            _result("a", "passed"), _result("latency", "missing", "evaluation", "free")
        )
        assert _decide(evidence)["state"] == "continue"

    @pytest.mark.parametrize(
        "provenance, code",
        [
            ("stale", "results-stale"),
            ("unrecorded", "results-unrecorded"),
            ("unavailable", "record-unusable"),
        ],
    )
    def test_results_that_are_not_tied_to_the_tree(self, provenance, code):
        verdict = _decide(_evidence(provenance=provenance))
        assert verdict["state"] == "continue" and _codes(verdict) == [("continue", code)]

    def test_another_required_check_that_failed(self):
        verdict = _decide(change__architecture="fail")
        assert _codes(verdict) == [("continue", "check-failed")]
        assert verdict["reasons"][0]["check"] == "change:architecture"

    def test_an_advisory_check_that_failed(self):
        evidence = _evidence()
        checks = _checks(evidence) + [fv.Check("legacy:doctor", False, "fail")]
        assert fv.decide(evidence, checks)["state"] == "continue"

    def test_work_the_agent_can_do_comes_before_waiting_for_a_person(self):
        evidence = _evidence(
            _result("a", "failed"),
            _result("b", "skipped"),
            _result("judge", "owed", "evaluation", "paid"),
        )
        verdict = _decide(evidence, approval__architecture="unknown")
        assert verdict["state"] == "continue"
        assert _codes(verdict) == [
            ("continue", "result-failed"),
            ("escalate", "result-skipped"),
            ("escalate", "result-owed"),
            ("escalate", "check-not-satisfied"),
        ]


class TestEscalateNow:
    @pytest.mark.parametrize(
        "check, code",
        [("change:definition", "definition-changed"), ("change:protected", "protected-changed")],
    )
    def test_a_weakened_definition_or_test_escalates_ahead_of_a_failure(self, check, code):
        evidence = _evidence(_result("a", "failed"))
        verdict = fv.decide(evidence, _checks(evidence) + [fv.Check(check, True, "fail")])
        assert verdict["state"] == "escalate" and verdict["exit_code"] == 3
        assert _codes(verdict)[0] == ("escalate", code)
        assert ("continue", "result-failed") in _codes(verdict)

    def test_a_change_check_that_could_not_compare_escalates_after_agent_work(self):
        verdict = _decide(change__definition="unknown")
        assert verdict["state"] == "escalate"
        assert _codes(verdict) == [("escalate", "check-not-satisfied")]

    def test_an_errored_test(self):
        verdict = _decide(_evidence(_result("a", "error"), _result("b", "failed")))
        assert verdict["state"] == "escalate"
        assert _codes(verdict) == [("escalate", "result-error"), ("continue", "result-failed")]

    def test_evidence_that_could_not_be_read(self):
        evidence = _evidence(outcome="ERROR", detail="junit.xml could not be parsed")
        verdict = _decide(evidence)
        assert verdict["state"] == "escalate"
        assert _codes(verdict) == [("escalate", "evidence-unreadable")]
        assert "junit.xml" in verdict["reasons"][0]["message"]

    def test_unreadable_criteria_results_are_listed_beside_an_errored_test(self):
        evidence = _evidence(_result("a", "error"), detail="govkit-eval-results.json is not JSON")
        evidence["summary"]["criteria"] = 1
        assert _codes(_decide(evidence)) == [
            ("escalate", "result-error"),
            ("escalate", "evidence-unreadable"),
        ]

    def test_an_errored_test_with_judged_criteria_is_reported_once(self):
        evidence = _evidence(_result("a", "error"), _result("latency", "passed", "evaluation"))
        evidence["summary"]["criteria"] = 1
        assert _codes(_decide(evidence)) == [("escalate", "result-error")]

    def test_a_required_check_that_did_not_complete_escalates_ahead_of_a_failure(self):
        evidence = _evidence(_result("a", "failed"))
        checks = _checks(evidence) + [fv.Check("project:tests", True, "unknown", errored=True)]
        verdict = fv.decide(evidence, checks)
        assert verdict["state"] == "escalate"
        assert _codes(verdict) == [("escalate", "check-error"), ("continue", "result-failed")]

    def test_an_advisory_check_that_did_not_complete_changes_nothing(self):
        evidence = _evidence(_result("a", "failed"))
        checks = _checks(evidence) + [fv.Check("legacy:doctor", False, "unknown", errored=True)]
        assert fv.decide(evidence, checks)["state"] == "continue"

    def test_unreadable_evidence_does_not_also_report_its_record(self):
        evidence = _evidence(outcome="ERROR", provenance="not-checked")
        assert _codes(_decide(evidence)) == [("escalate", "evidence-unreadable")]


class TestEscalateWhenNothingIsLeftForTheAgent:
    def test_a_skipped_test(self):
        verdict = _decide(_evidence(_result("a", "skipped")))
        assert verdict["state"] == "escalate" and verdict["exit_code"] == 3
        assert _codes(verdict) == [("escalate", "result-skipped")]

    @pytest.mark.parametrize("execution_class", ["paid", "human"])
    def test_an_owed_evaluation(self, execution_class):
        evidence = _evidence(
            _result("a", "passed"), _result("judge", "owed", "evaluation", execution_class)
        )
        assert _codes(_decide(evidence)) == [("escalate", "result-owed")]

    def test_skips_that_are_not_marked(self):
        evidence = _evidence(
            outcome="INCONCLUSIVE", sources=[{"path": "junit.xml", "unidentified_skipped": 2}]
        )
        assert _codes(_decide(evidence)) == [("escalate", "skips-unmarked")]

    def test_criteria_in_a_form_that_is_not_compared(self):
        assert _codes(_decide(_evidence(form="data"))) == [("escalate", "criteria-not-compared")]

    def test_a_feature_with_no_scenarios(self):
        evidence = _evidence(outcome="INCONCLUSIVE")
        evidence["results"], evidence["summary"]["scenarios"] = [], 0
        assert _codes(_decide(evidence)) == [("escalate", "no-scenarios")]

    @pytest.mark.parametrize("state", ["unknown", "skipped", "warn", "waived"])
    def test_a_required_check_without_a_pass(self, state):
        verdict = _decide(approval__architecture=state)
        assert _codes(verdict) == [("escalate", "check-not-satisfied")]
        assert verdict["reasons"][0]["check"] == "approval:architecture"

    def test_evidence_that_is_not_a_pass_is_never_done(self):
        # A report this module does not recognise still cannot be read as done.
        evidence = _evidence(outcome="INCONCLUSIVE")
        assert _codes(_decide(evidence)) == [("escalate", "evidence-inconclusive")]


class TestContract:
    def test_every_reason_code_is_declared(self):
        assert fv.CODES == (
            "definition-changed",
            "protected-changed",
            "result-error",
            "evidence-unreadable",
            "check-error",
            "result-failed",
            "result-missing",
            "results-stale",
            "results-unrecorded",
            "record-unusable",
            "check-failed",
            "result-skipped",
            "result-owed",
            "skips-unmarked",
            "criteria-not-compared",
            "no-scenarios",
            "check-not-satisfied",
            "evidence-inconclusive",
        )

    def test_states_and_exit_codes(self):
        assert fv.EXIT_CODES == {"done": 0, "continue": 1, "escalate": 3}

    def test_every_reason_says_what_to_do(self):
        evidence = _evidence(_result("a", "failed"), _result("b", "skipped"))
        for reason in _decide(evidence, change__protected="fail")["reasons"]:
            assert reason["action"] and reason["message"] and reason["code"] in fv.CODES

    def test_the_evidence_check_is_reported_through_the_evidence_not_twice(self):
        verdict = _decide(_evidence(_result("a", "failed")))
        assert all(reason["code"] != "check-failed" for reason in verdict["reasons"])

    def test_the_same_inputs_give_the_same_answer(self):
        evidence = _evidence(_result("a", "failed"), _result("b", "skipped"))
        assert _decide(evidence) == _decide(evidence)
