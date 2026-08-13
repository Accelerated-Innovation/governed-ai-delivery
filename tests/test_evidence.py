"""Measured evidence: read what CI actually produced, and say what it did not.

Two dimensions have unambiguous criteria today and are gated: Working (the test
run had no failures) and Accessibility (axe reported no critical or serious
violations). Everything else reports INCONCLUSIVE.

That is deliberate, not a shortfall to be papered over. Turning a 1-5 rubric
band into a pass/fail threshold is a calibration decision, and
`docs/data/architecture/ADR/0001-...` already warns that inventing a rubric
nobody has calibrated "recreates the ceremony this ADR removes". Fast therefore
reports its *observed* durations while staying INCONCLUSIVE until a team sets a
threshold — the measurement is real, the policy is theirs.
"""

from pathlib import Path

import pytest

from cli.evidence import (
    DIMENSIONS,
    Outcome,
    collect_evidence,
    summarize,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


def _junit(tmp_path: Path, cases: list[tuple[str, float, bool]], name: str = "junit.xml") -> Path:
    """cases = [(test name, seconds, passed)]"""
    failures = sum(1 for _, _, ok in cases if not ok)
    body = "".join(
        f'<testcase classname="suite" name="{n}" time="{t}">'
        + ("" if ok else '<failure message="boom">trace</failure>')
        + "</testcase>"
        for n, t, ok in cases
    )
    path = tmp_path / name
    path.write_text(
        f'<?xml version="1.0"?><testsuites><testsuite name="suite" '
        f'tests="{len(cases)}" failures="{failures}" errors="0">{body}</testsuite></testsuites>',
        encoding="utf-8",
    )
    return path


def _axe(tmp_path: Path, impacts: list[str], name: str = "axe.json") -> Path:
    import json

    path = tmp_path / name
    path.write_text(
        json.dumps({"violations": [{"id": f"r{i}", "impact": imp, "nodes": [{}]}
                                   for i, imp in enumerate(impacts)]}),
        encoding="utf-8",
    )
    return path


def _by_dimension(verdicts) -> dict:
    return {v.dimension: v for v in verdicts}


class TestNoEvidence:
    def test_every_dimension_reported(self, tmp_path):
        """Silence about a dimension is how an unmeasured one reads as green."""
        verdicts = collect_evidence(tmp_path)
        assert {v.dimension for v in verdicts} == set(DIMENSIONS)

    def test_all_inconclusive_when_nothing_produced(self, tmp_path):
        verdicts = collect_evidence(tmp_path)
        assert all(v.outcome is Outcome.INCONCLUSIVE for v in verdicts), [
            (v.dimension, v.outcome) for v in verdicts if v.outcome is not Outcome.INCONCLUSIVE
        ]

    def test_empty_analysis_fails(self, tmp_path):
        """ci/README: every tool reports success on an empty analysis, so a
        misconfigured contract looks exactly like a clean repo."""
        exit_code, summary = summarize(collect_evidence(tmp_path))
        assert exit_code == 1
        assert "analysed nothing" in summary.lower()


class TestWorking:
    def test_passing_suite(self, tmp_path):
        _junit(tmp_path, [("t1", 0.01, True), ("t2", 0.02, True)])
        v = _by_dimension(collect_evidence(tmp_path))["Working"]
        assert v.outcome is Outcome.PASS, v.detail

    def test_failing_suite(self, tmp_path):
        _junit(tmp_path, [("t1", 0.01, True), ("t2", 0.02, False)])
        v = _by_dimension(collect_evidence(tmp_path))["Working"]
        assert v.outcome is Outcome.FAIL
        assert "1" in v.detail

    def test_failure_makes_the_run_fail(self, tmp_path):
        _junit(tmp_path, [("t1", 0.01, False)])
        exit_code, _ = summarize(collect_evidence(tmp_path))
        assert exit_code == 1

    def test_zero_test_suite_is_inconclusive_not_pass(self, tmp_path):
        """A JUnit file reporting no tests is an empty analysis, not a clean one."""
        _junit(tmp_path, [])
        v = _by_dimension(collect_evidence(tmp_path))["Working"]
        assert v.outcome is Outcome.INCONCLUSIVE, v.detail

    def test_unreadable_artifact_is_error_not_pass(self, tmp_path):
        (tmp_path / "junit.xml").write_text("<not-xml", encoding="utf-8")
        v = _by_dimension(collect_evidence(tmp_path))["Working"]
        assert v.outcome is Outcome.ERROR, v.detail

    def test_error_makes_the_run_fail(self, tmp_path):
        (tmp_path / "junit.xml").write_text("<not-xml", encoding="utf-8")
        exit_code, _ = summarize(collect_evidence(tmp_path))
        assert exit_code == 1


class TestAccessibility:
    def test_no_violations(self, tmp_path):
        _axe(tmp_path, [])
        v = _by_dimension(collect_evidence(tmp_path))["Accessibility"]
        assert v.outcome is Outcome.PASS, v.detail

    @pytest.mark.parametrize("impact", ["critical", "serious"])
    def test_blocking_impacts_fail(self, tmp_path, impact):
        _axe(tmp_path, [impact])
        v = _by_dimension(collect_evidence(tmp_path))["Accessibility"]
        assert v.outcome is Outcome.FAIL
        assert impact in v.detail

    @pytest.mark.parametrize("impact", ["moderate", "minor"])
    def test_non_blocking_impacts_pass_but_are_reported(self, tmp_path, impact):
        """The UI rubric bands minor violations at 3, not 1 — they are not a
        merge blocker, but they must not vanish either."""
        _axe(tmp_path, [impact])
        v = _by_dimension(collect_evidence(tmp_path))["Accessibility"]
        assert v.outcome is Outcome.PASS
        assert impact in v.detail

    def test_playwright_array_shape_is_read(self, tmp_path):
        """Playwright axe runs commonly write an array of results."""
        import json

        (tmp_path / "axe.json").write_text(
            json.dumps([{"violations": [{"id": "x", "impact": "critical", "nodes": [{}]}]}]),
            encoding="utf-8",
        )
        v = _by_dimension(collect_evidence(tmp_path))["Accessibility"]
        assert v.outcome is Outcome.FAIL


class TestFastReportsWithoutJudging:
    def test_durations_observed_but_outcome_stays_inconclusive(self, tmp_path):
        """The measurement is real; the threshold is the team's calibration to
        make. Inventing one here would recreate the ceremony being removed."""
        _junit(tmp_path, [("t1", 0.001, True), ("t2", 1.5, True)])
        v = _by_dimension(collect_evidence(tmp_path))["Fast"]
        assert v.outcome is Outcome.INCONCLUSIVE
        assert "1.5" in v.detail or "1500" in v.detail

    def test_no_junit_means_no_observation(self, tmp_path):
        v = _by_dimension(collect_evidence(tmp_path))["Fast"]
        assert v.outcome is Outcome.INCONCLUSIVE
        assert "no" in v.detail.lower()


class TestSummary:
    def test_partial_coverage_passes_but_names_the_gap(self, tmp_path):
        """Some measured, none failing: not a blocker, but the summary must say
        how much went unmeasured rather than printing a bare green."""
        _junit(tmp_path, [("t1", 0.01, True)])
        _axe(tmp_path, [])
        exit_code, summary = summarize(collect_evidence(tmp_path))
        assert exit_code == 0
        assert "2 measured" in summary
        assert "unmeasured" in summary.lower()

    def test_summary_never_claims_a_dimension_it_did_not_measure(self, tmp_path):
        _junit(tmp_path, [("t1", 0.01, True)])
        _, summary = summarize(collect_evidence(tmp_path))
        assert "Clear" not in summary.split("unmeasured")[0]


def test_clear_is_never_measurable(tmp_path):
    """Its only proxies reward verbosity over clarity. The contract says it must
    stay advisory; this pins that it can never report PASS."""
    _junit(tmp_path, [("t1", 0.01, True)])
    _axe(tmp_path, [])
    v = _by_dimension(collect_evidence(tmp_path))["Clear"]
    assert v.outcome is Outcome.INCONCLUSIVE
    assert "judgement" in v.detail.lower()


def test_dimensions_match_the_shipped_rubrics():
    """Non-vacuous guard: the dimension list must be the rubrics' own, or this
    module is measuring something govkit never asked for."""
    first = (REPO_ROOT / "docs" / "backend" / "evaluation" / "FIRST_SCORING_RUBRIC.md").read_text(
        encoding="utf-8"
    )
    virtues = (REPO_ROOT / "docs" / "backend" / "evaluation" / "VIRTUE_SCORING_RUBRIC.md").read_text(
        encoding="utf-8"
    )
    for dim in ("Fast", "Isolated", "Repeatable", "Self-Verifying", "Timely"):
        assert dim in first, dim
    for dim in ("Working", "Unique", "Simple", "Clear", "Easy", "Developed", "Brief"):
        assert dim in virtues, dim


class TestFastThreshold:
    """A team can make Fast blocking by declaring the threshold they calibrated.

    The threshold is a flag rather than an eval_criteria.yaml field on purpose:
    it is repo-wide policy, and eval_criteria.yaml is per-feature. Putting it
    there would have meant one feature's file silently deciding the gate for the
    whole repo, and a closed-schema edit for a field nothing else reads.
    """

    def test_under_threshold_passes(self, tmp_path):
        _junit(tmp_path, [("t1", 0.01, True), ("t2", 0.05, True)])
        v = _by_dimension(collect_evidence(tmp_path, fast_max_seconds=0.2))["Fast"]
        assert v.outcome is Outcome.PASS, v.detail

    def test_over_threshold_fails_and_names_the_test(self, tmp_path):
        _junit(tmp_path, [("quick", 0.01, True), ("crawler", 1.4, True)])
        v = _by_dimension(collect_evidence(tmp_path, fast_max_seconds=0.2))["Fast"]
        assert v.outcome is Outcome.FAIL
        assert "crawler" in v.detail, v.detail

    def test_threshold_without_durations_is_still_inconclusive(self, tmp_path):
        """A declared threshold does not conjure evidence."""
        v = _by_dimension(collect_evidence(tmp_path, fast_max_seconds=0.2))["Fast"]
        assert v.outcome is Outcome.INCONCLUSIVE

    def test_no_threshold_keeps_the_observation_advisory(self, tmp_path):
        _junit(tmp_path, [("t1", 5.0, True)])
        v = _by_dimension(collect_evidence(tmp_path))["Fast"]
        assert v.outcome is Outcome.INCONCLUSIVE
