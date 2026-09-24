"""Fleet summaries count explicit evidence without joining independent snapshots."""

import json
import socket
from copy import deepcopy

import pytest

from cli import paths
from cli.posture import reference
from cli.posture_aggregate import aggregate_posture, parse_aggregate, render_aggregate
from cli.schema_validation import canonical_json, content_digest, validate_document

AS_OF = "2026-09-24T12:00:00Z"
MISSING = reference("repository", "not-assessed")


def example(name="maintenance"):
    return json.loads((paths.GOVERNANCE_DIR / f"examples/posture/{name}.json").read_text())


def redigest(document):
    document["digest"] = content_digest(
        canonical_json({k: v for k, v in document.items() if k != "digest"}).encode()
    )
    return document


def aggregate(*documents, **kwargs):
    return aggregate_posture(
        documents,
        repository_refs=kwargs.pop(
            "repository_refs", sorted({d["repository_ref"] for d in documents})
        ),
        as_of=kwargs.pop("as_of", AS_OF),
        **kwargs,
    )


def test_explicit_cohort_counts_missing_assessments_and_separate_change_coverage():
    maintenance, change = example(), example("change")
    cohort = sorted({maintenance["repository_ref"], change["repository_ref"], MISSING})

    report = aggregate(maintenance, change, repository_refs=cohort)

    s = report.document["summary"]
    assert s["repositories"] == len(cohort)
    assert s["maintenance"]["assessed_repositories"] == 1
    assert s["maintenance"]["missing_repositories"] == len(cohort) - 1
    assert s["changes"]["assessed_repositories"] == 1
    assert s["changes"]["missing_repositories"] == len(cohort) - 1
    assert s["maintenance"]["categories"]["compatible_updates"] == 1
    assert s["maintenance"]["categories"]["required_upgrades"] == 0
    assert s["changes"]["evaluations"]["total"] == 1
    assert s["changes"]["evaluations"]["execution"]["executed"] == 1
    assert s["changes"]["evaluations"]["fresh_executed_passes"] == 1
    assert parse_aggregate(json.loads(report.to_json())).document == report.document
    validate_document(report.document, "posture-aggregate")


def test_empty_observations_keep_the_whole_cohort_missing_without_inventing_passes():
    d = aggregate(repository_refs=[MISSING]).document["summary"]
    for key in ("maintenance", "changes"):
        assert d[key]["assessed_repositories"] == 0
        assert d[key]["missing_repositories"] == 1
    assert d["changes"]["controls"]["fresh_executed_passes"] == 0
    assert d["changes"]["controls"]["applicable"] == 0
    assert not d["maintenance"]["capabilities"]


def test_input_order_and_identical_duplicates_do_not_change_counts_or_bytes(monkeypatch):
    a, b = example(), example("change")
    original = deepcopy([a, b])
    monkeypatch.setattr(socket, "socket", lambda *a, **k: pytest.fail("Aggregation used network"))
    first = aggregate(a, b).to_json()
    assert aggregate(b, a, deepcopy(a), deepcopy(b)).to_json() == first
    assert [a, b] == original


@pytest.mark.parametrize("kind", ["maintenance", "change"])
def test_conflicting_snapshots_require_explicit_selection_instead_of_latest_wins(kind):
    a = example(kind)
    b = redigest({**deepcopy(a), "as_of": "2026-09-24T13:00:00+00:00"})
    with pytest.raises(ValueError, match="Conflicting"):
        aggregate(a, b)


@pytest.mark.parametrize("cohort", [[], [MISSING, MISSING], ["private/repo"], [None]])
def test_invalid_or_duplicate_cohort_is_rejected(cohort):
    with pytest.raises(ValueError):
        aggregate(repository_refs=cohort)


def test_unlisted_repository_cannot_silently_expand_the_denominator():
    with pytest.raises(ValueError, match="cohort"):
        aggregate(example(), repository_refs=[MISSING])


@pytest.mark.parametrize("clock", ["yesterday", "2026-09-24T12:00:00", None])
def test_reporting_clock_must_be_explicit_and_timezone_aware(clock):
    with pytest.raises(ValueError):
        aggregate(example(), as_of=clock)


@pytest.mark.parametrize("hours", [0, -1, True, 1.5, float("nan")])
def test_age_window_is_a_positive_integer(hours):
    with pytest.raises(ValueError):
        aggregate(example(), max_age_hours=hours)


@pytest.mark.parametrize(
    "clock,expected",
    [
        ("2026-09-25T12:00:00Z", "fresh"),
        ("2026-09-25T12:00:01Z", "stale"),
        ("2026-09-24T11:59:59Z", "future"),
    ],
)
def test_reporting_age_boundary_never_refreshes_old_or_future_passes(clock, expected):
    source = redigest({**example("change"), "as_of": AS_OF})
    d = aggregate(source, as_of=clock).document
    assert d["observations"][0]["freshness"] == expected
    counts = d["summary"]["changes"]["evaluations"]
    assert counts["states"]["pass"] == counts["applicable"] == 1
    assert counts["fresh_executed_passes"] == (1 if expected == "fresh" else 0)


@pytest.mark.parametrize("state", ["unknown", "skipped", "waived", "not-applicable"])
def test_unknown_skipped_waived_and_not_applicable_are_never_pass_numerators(state):
    # This report remains structurally valid; canonical aggregation is rebuilt for
    # the recorded state so the test targets fleet counting, not invalid inputs.
    from cli.check_models import CheckOutcome, CheckResult, CheckSpec, Execution, Identity, State
    from cli.check_runner import CheckReport

    d = example("change")
    c = next(c for c in d["results"]["controls"] if c["label"] == "llm-exact-match")
    c.update(state=state, execution="not-run", evidence=[], findings=[])
    checks = CheckReport(
        Identity("fixture"),
        tuple(
            CheckResult(
                CheckSpec(c["ref"], c["required"], "", "", ()),
                CheckOutcome(State(c["state"]), Execution(c["execution"]), ""),
            )
            for c in d["results"]["controls"]
        ),
        "",
    )
    d["results"].update(
        summary=checks.summary, state=checks.state.value, exit_code=checks.exit_code
    )
    result = aggregate(redigest(d)).document["summary"]["changes"]["evaluations"]
    assert result["total"] == result["required"] == 1
    assert result["states"][state] == 1
    assert result["fresh_executed_passes"] == result["fresh_required_passes"] == 0
    assert result["applicable"] == (0 if state == "not-applicable" else 1)


def test_undated_snapshot_cannot_supply_fresh_passes():
    d = redigest({**example("change"), "as_of": None})
    result = aggregate(d).document
    assert result["observations"][0]["freshness"] == "unknown"
    assert result["summary"]["changes"]["evaluations"]["fresh_executed_passes"] == 0


def test_stale_metadata_remains_stale_even_under_a_longer_reporting_window():
    d = example()
    d["versions"]["candidates"][0]["freshness"] = "stale"
    result = aggregate(redigest(d), max_age_hours=72).document
    assert result["summary"]["maintenance"]["categories"]["stale_metadata"] == 1


@pytest.mark.parametrize("mutation", ["count", "snapshot", "cohort", "extra", "digest"])
def test_replay_rejects_corrupt_inputs_or_redigested_summary_lies(mutation):
    d = aggregate(example()).document
    if mutation == "count":
        d["summary"]["maintenance"]["assessed_repositories"] += 1
    elif mutation == "snapshot":
        d["snapshots"][0]["private_source"] = "secret"
    elif mutation == "cohort":
        d["cohort"].append(MISSING)
    elif mutation == "extra":
        d["raw_request"] = "secret"
    else:
        d["digest"] = "f" * 64
    if mutation != "digest":
        redigest(d)
    with pytest.raises(ValueError):
        parse_aggregate(d)


def test_human_output_represents_every_summary_count_and_observation():
    report = aggregate(
        example(),
        example("change"),
        repository_refs=sorted(
            {example()["repository_ref"], example("change")["repository_ref"], MISSING}
        ),
    )
    display = render_aggregate(report)

    def check(value, prefix):
        if isinstance(value, dict):
            for key, item in value.items():
                check(item, prefix + "/" + key)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                check(item, prefix + "/" + str(index))
        else:
            assert f"{prefix}: {value}" in display

    check(report.document["summary"], "summary")
    for observation in report.document["observations"]:
        assert observation["snapshot_ref"] in display
        assert observation["freshness"] in display
    assert "not a compliance or productivity score" in display


def test_old_assessment_retains_historical_actions_without_fresh_availability():
    source = example()
    result = aggregate(source, as_of="2026-09-26T12:00:00Z").document["summary"]["maintenance"]
    assert result["categories"]["compatible_updates"] == 1
    assert result["fresh_categories"]["compatible_updates"] == 0
    assert result["categories"]["stale_metadata"] == 1
    assert result["categories"]["fresh_metadata"] == 0
    assert result["freshness"]["stale"] == 1
    assert all(d["counts"]["fresh_executed_passes"] == 0 for d in result["dimensions"])


def test_shared_repository_reference_does_not_join_maintenance_and_change_identities():
    maintenance, change = example(), example("change")
    change["repository_ref"] = maintenance["repository_ref"]
    redigest(change)
    result = aggregate(maintenance, change).document
    assert result["summary"]["repositories"] == 1
    assert result["summary"]["maintenance"]["assessed_repositories"] == 1
    assert result["summary"]["changes"]["assessed_repositories"] == 1
    assert result["summary"]["changes"]["controls"]["total"] == len(change["results"]["controls"])
    assert {d["kind"]: d["identity"] for d in result["snapshots"]} == {
        "posture-export": maintenance["identity"],
        "change-posture": change["identity"],
    }


def test_real_failing_evaluation_counts_as_executed_but_not_passed(tmp_path):
    from cli.posture_change import export_change_posture
    from tests.test_change_posture import changed

    _, _, source = changed(tmp_path, llm=True, good=False)
    report = export_change_posture(source.document).document
    result = aggregate(report).document["summary"]["changes"]["evaluations"]
    assert result["total"] == result["applicable"] == result["required"] == 1
    assert result["execution"]["executed"] == result["states"]["fail"] == 1
    assert result["fresh_executed_passes"] == result["fresh_required_passes"] == 0


@pytest.mark.parametrize("retrieved", [None, "2026-09-25T12:00:00Z", "2026-09-23T12:00:00Z"])
def test_unknown_future_or_inverted_source_lookup_time_cannot_supply_fresh_metadata(retrieved):
    doc = example()
    doc["versions"]["metadata"][0]["retrieved_at"] = retrieved
    result = aggregate(redigest(doc)).document["summary"]["maintenance"]
    assert result["categories"]["unknown_metadata"] == 1
    assert result["categories"]["fresh_metadata"] == 0
    assert result["fresh_categories"]["compatible_updates"] == 0


def test_fresh_assessment_does_not_refresh_its_older_release_evidence():
    doc = example("scenarios/current")
    # The original policy can permit a longer source age than this reporting
    # window. Preserve its canonical pass, but exclude it from fresh-pass counts.
    for record in [*doc["versions"]["candidates"], *doc["versions"]["metadata"]]:
        record["as_of"] = "2026-09-22T12:00:00Z"
    result = aggregate(redigest(doc)).document["summary"]["maintenance"]
    releases = next(d["counts"] for d in result["dimensions"] if d["id"] == "maintenance:releases")
    assert result["freshness"]["fresh"] == 1
    assert releases["states"]["pass"] == 1
    assert releases["fresh_executed_passes"] == 0
