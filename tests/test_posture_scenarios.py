"""Real maintenance paths back the fleet examples and overlapping action counts."""

import json

import pytest

from cli import paths
from cli.posture import export_posture, parse_posture, render_posture
from cli.posture_aggregate import aggregate_posture
from tests.posture_scenarios import AS_OF, make_scenario
from tests.test_pack_store import snapshot

SCENARIOS = (
    "current",
    "optional-update",
    "resource-drift",
    "changed-needs",
    "incompatible",
    "unavailable",
    "stale",
    "intentional-pin",
    "required-upgrade",
    "overlap",
)


@pytest.mark.parametrize("name", SCENARIOS)
def test_live_scenario_projects_canonical_actions_versions_and_protected_files(tmp_path, name):
    target, assessment = make_scenario(tmp_path, name)
    before = snapshot(target)

    report = export_posture(assessment.document)

    doc = report.document
    assert parse_posture(doc).document == doc
    assert doc["as_of"] and doc["repository_ref"] and doc["identity"]["inventory_digest_ref"]
    assert doc["versions"]["metadata"]
    assert doc["versions"]["candidates"]
    for projected, source in zip(
        doc["maintenance"]["recommendations"], assessment.document["recommendations"], strict=True
    ):
        assert (projected["id"], projected["action"], projected["required"]) == (
            source["id"],
            source["action"],
            source["required"],
        )
        assert len(projected["customization_refs"]) == len(source["customizations"])
        assert projected["id"] in render_posture(report)
    counts = aggregate_posture(
        [doc], repository_refs=[doc["repository_ref"]], as_of=AS_OF
    ).document["summary"]["maintenance"]["categories"]
    dimensions = {d["id"]: d["state"] for d in doc["maintenance"]["dimensions"]}
    if name == "current":
        assert set(dimensions.values()) == {"pass"}
        assert not any(counts[k] for k in ("compatible_updates", "resource_drift", "ci_repairs"))
    elif name == "optional-update":
        assert counts["compatible_updates"] == 1 and counts["required_upgrades"] == 0
    elif name == "resource-drift":
        assert counts["resource_drift"] == 1 and counts["compatible_updates"] == 0
    elif name == "changed-needs":
        assert counts["governance_reviews"] == 1 and counts["compatible_updates"] == 0
    elif name == "incompatible":
        assert doc["versions"]["candidates"][0]["excluded"]
        assert counts["compatible_updates"] == counts["required_upgrades"] == 0
    elif name == "unavailable":
        assert counts["unknown_metadata"] == 1
    elif name == "stale":
        assert counts["stale_metadata"] == 1 and counts["fresh_metadata"] == 0
    elif name == "intentional-pin":
        assert counts["compliant_pins"] == 1 and counts["required_upgrades"] == 0
        assert dimensions["maintenance:releases"] == "pass"
    elif name == "required-upgrade":
        assert counts["required_upgrades"] == 1
        assert dimensions["maintenance:releases"] == "fail"
    else:
        assert (
            counts["compatible_updates"]
            == counts["resource_drift"]
            == counts["governance_reviews"]
            == counts["ci_repairs"]
            == 1
        )
    assert snapshot(target) == before


def test_bundled_scenarios_and_aggregate_replay_without_a_collector():
    from cli.posture_aggregate import parse_aggregate

    root = paths.GOVERNANCE_DIR / "examples/posture"
    docs = [json.loads((root / "scenarios" / f"{name}.json").read_text()) for name in SCENARIOS]
    for d in docs:
        assert parse_posture(d).document == d
    aggregate = json.loads((root / "fleet.json").read_text())
    assert parse_aggregate(aggregate).document == aggregate
    assert len(aggregate["cohort"]) == len(SCENARIOS) + 2  # change-only and unassessed repositories
    assert aggregate["summary"]["maintenance"]["missing_repositories"] == 2
    assert aggregate["summary"]["changes"]["evaluations"]["execution"]["executed"] == 1


def test_aggregate_embedded_schemas_match_current_source_contracts():
    s = json.loads((paths.GOVERNANCE_DIR / "schemas/posture-aggregate.schema.json").read_text())
    for name in ("posture-export", "change-posture"):
        original = json.loads((paths.GOVERNANCE_DIR / f"schemas/{name}.schema.json").read_text())
        original.pop("$id", None)
        original.pop("$schema", None)
        restored = json.loads(
            json.dumps(s["$defs"][name]).replace(f"#/$defs/{name}/$defs/", "#/$defs/")
        )
        assert restored == original
