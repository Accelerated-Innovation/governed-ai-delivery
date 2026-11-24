"""Criterion identity, targets and comparison equal the Product Definition Graph's.

The expected values were produced by running the engine's own rules, so a
criterion GovKit reports as met is one the graph would report as met.
`execution_class` is GovKit's own field; the graph ignores it.
"""

import json
from pathlib import Path

import pytest

from cli import criterion_identity as ci
from cli.scenario_identity import IdentityError

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "scenario-identity" / "criteria_parity.json").read_text(
        encoding="utf-8"
    )
)
PACKAGE = FIXTURE["package"]
DIGEST = "a" * 64


def _read(document):
    return ci.read_criteria(PACKAGE, document, DIGEST)


@pytest.mark.parametrize(
    "case", [c for c in FIXTURE["cases"] if "criteria" in c["expected"]], ids=lambda c: c["name"]
)
def test_criteria_equal_the_engines(case):
    found = [
        {
            "id": c.id,
            "name": c.name,
            "threshold": c.threshold,
            "fail_on": c.fail_on,
            "metric": c.target.metric if c.target else None,
            "comparator": c.target.comparator if c.target else None,
            "target_value": c.target.value if c.target else None,
            "target_high": c.target.value_high if c.target else None,
            "unit": c.target.unit if c.target else None,
        }
        for c in _read(case["document"])
    ]
    assert found == case["expected"]["criteria"]


@pytest.mark.parametrize(
    "case", [c for c in FIXTURE["cases"] if "refused" in c["expected"]], ids=lambda c: c["name"]
)
def test_refusals_equal_the_engines(case):
    with pytest.raises(IdentityError) as refused:
        _read(case["document"])
    assert refused.value.reason == case["expected"]["refused"]


@pytest.mark.parametrize(
    "row", FIXTURE["meets"], ids=lambda r: f"{r['target']['comparator']}-{r['measured']}"
)
def test_a_target_is_met_when_the_engine_says_so(row):
    document = {"criteria": [{"name": "c", "target": row["target"]}]}
    target = _read(document)[0].target
    assert ci.meets(target, row["measured"]) is row["met"]


def test_every_criterion_carries_the_files_digest():
    document = {"criteria": [{"name": "a"}, {"name": "b"}]}
    assert {c.revision_digest for c in _read(document)} == {DIGEST}


class TestThreshold:
    """Without a target, a criterion is compared with `threshold` and `fail_on`."""

    @pytest.mark.parametrize(
        "fail_on, value, expected",
        [
            ("below_threshold", 0.79, False),
            ("below_threshold", 0.8, True),
            ("below_threshold", 0.9, True),
            ("above_threshold", 0.81, False),
            ("above_threshold", 0.8, True),
            ("above_threshold", 0.1, True),
        ],
    )
    def test_a_value_is_compared_with_the_threshold(self, fail_on, value, expected):
        criterion = _read({"criteria": [{"name": "c", "threshold": 0.8, "fail_on": fail_on}]})[0]
        assert ci.compare(criterion, value) is expected

    @pytest.mark.parametrize("fail_on", ["error", "missing_signal"])
    def test_a_criterion_that_only_needs_a_signal_is_not_compared(self, fail_on):
        criterion = _read({"criteria": [{"name": "c", "threshold": 0.8, "fail_on": fail_on}]})[0]
        assert ci.compare(criterion, 0.1) is None

    def test_a_criterion_with_neither_target_nor_threshold_is_not_compared(self):
        assert ci.compare(_read({"criteria": [{"name": "c"}]})[0], 0.1) is None

    def test_a_target_is_used_ahead_of_the_threshold(self):
        target = {"metric": "m", "comparator": "<=", "value": 0.2, "unit": "ratio"}
        criterion = _read(
            {
                "criteria": [
                    {"name": "c", "threshold": 0.8, "fail_on": "below_threshold", "target": target}
                ]
            }
        )[0]
        assert ci.compare(criterion, 0.1) is True
        assert ci.compare(criterion, 0.9) is False


class TestExecutionClass:
    def test_free_is_the_default(self):
        assert _read({"criteria": [{"name": "c"}]})[0].execution_class == "free"

    @pytest.mark.parametrize("value", ci.EXECUTION_CLASSES)
    def test_a_declared_class_is_read(self, value):
        document = {"criteria": [{"name": "c", "execution_class": value}]}
        assert _read(document)[0].execution_class == value

    @pytest.mark.parametrize("value", ["Paid", "expensive", 3, None, ""])
    def test_an_unknown_class_is_an_error_not_free(self, value):
        """Reading a mistyped `paid` as `free` would tell an agent to run it."""
        with pytest.raises(ci.CriteriaError) as error:
            _read({"criteria": [{"name": "c", "execution_class": value}]})
        assert "execution_class" in str(error.value)

    def test_tags_are_read_when_they_are_text(self):
        document = {"criteria": [{"name": "c", "tags": ["safety", 7, "nfr"]}]}
        assert _read(document)[0].tags == ("safety", "nfr")


@pytest.mark.parametrize("field", ["value", "value_high"])
def test_a_number_too_large_for_a_float_is_refused_not_raised(field):
    target = {"metric": "m", "comparator": ">=", "value": 1, "unit": "ratio", field: 10**400}
    with pytest.raises(IdentityError) as refused:
        _read({"criteria": [{"name": "c", "target": target}]})
    assert refused.value.reason == "parse_error"


def test_a_threshold_too_large_for_a_float_is_refused_not_raised():
    with pytest.raises(IdentityError):
        _read({"criteria": [{"name": "c", "threshold": 10**400}]})
