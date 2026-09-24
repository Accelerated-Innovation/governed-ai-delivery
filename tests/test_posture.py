"""Maintenance posture exports disclose descriptors, not their local evidence payloads."""

import json
import socket
from copy import deepcopy

import pytest

from cli import paths
from cli.maintenance import assess_repository
from cli.posture import export_posture, parse_posture, render_posture
from cli.schema_validation import canonical_json, parse_document, validate_document
from tests.test_maintenance import redigest_assessment
from tests.test_maintenance_inventory import installed
from tests.test_pack_store import snapshot
from tests.test_release_metadata import AS_OF, metadata, release


def assessed(tmp_path, *, releases=None):
    target, _ = installed(tmp_path)
    return target, assess_repository(
        target, as_of=AS_OF, metadata=(metadata(*(releases or [release("1.0"), release("1.1")])),)
    ).document


def test_projection_preserves_canonical_dimensions_and_actions_without_writes(tmp_path):
    target, source = assessed(tmp_path)
    before = snapshot(target)
    report = export_posture(source)
    document = report.document
    assert document["kind"] == "posture-export"
    assert {
        r["id"]: (r["state"], r["required"]) for r in document["maintenance"]["dimensions"]
    } == {r["id"]: (r["state"], r["required"]) for r in source["checks"]["results"]}
    assert [
        (r["id"], r["action"], r["required"]) for r in document["maintenance"]["recommendations"]
    ] == [(r["id"], r["action"], r["required"]) for r in source["recommendations"]]
    assert document["versions"]["running_cli"]["display"] == source["inventory"]["running_cli"]
    assert document["coverage"]["change_results"] == "not-supplied"
    assert document["maintenance"]["exit_code"] == source["checks"]["exit_code"]
    assert document["repository_ref"] != source["repository"]
    assert snapshot(target) == before
    validate_document(document, "posture-export")


def test_repeat_export_is_byte_deterministic_for_a_saved_assessment(tmp_path):
    _, source = assessed(tmp_path)
    expected = export_posture(source).to_json()
    result = export_posture(deepcopy(source)).to_json()
    assert result == expected


def test_projection_excludes_local_paths_raw_ids_urls_and_free_text(tmp_path):
    target, _ = installed(tmp_path)
    source_path = target / ".govkit/profile.yaml"
    profile = parse_document(source_path.read_text())
    sentinel = "private-person-prompt-source-secret"
    profile["repository"]["id"] = sentinel
    profile["source"]["reference"] = sentinel + ".md"
    profile["policy"]["source"]["reference"] = sentinel + ".md"
    profile["policy"]["required_checks"] = [{"id": "project:" + sentinel}]
    source_path.write_text(json.dumps(profile))
    (target / (sentinel + ".md")).write_text(sentinel)
    source = assess_repository(target, as_of=AS_OF, metadata=(metadata(),)).document
    source["limitations"] = [sentinel]
    source = redigest_assessment(source)
    assert sentinel in canonical_json(source)
    result = export_posture(source).to_json()
    assert sentinel not in result
    assert str(target) not in result
    assert "example.invalid" not in result and "policy.md" not in result
    assert "local_ref" in result and "component_ref" in result
    assert "L3" not in result and '"level"' not in result


@pytest.mark.parametrize("tamper", ["digest", "state", "action"])
def test_projection_rejects_inconsistent_canonical_assessments(tmp_path, tamper):
    _, source = assessed(tmp_path)
    if tamper == "digest":
        source["digest"] = "0" * 64
    elif tamper == "state":
        source["checks"]["results"][0]["state"] = (
            "pass" if source["checks"]["results"][0]["state"] != "pass" else "fail"
        )
        source = redigest_assessment(source)
    else:
        source["recommendations"][0]["required"] = not source["recommendations"][0]["required"]
        source = redigest_assessment(source)
    with pytest.raises(ValueError):
        export_posture(source)


def test_unknown_ci_and_stale_metadata_are_not_promoted_to_healthy(tmp_path):
    target, _ = installed(tmp_path)
    source = assess_repository(
        target, as_of=AS_OF, metadata=(metadata(as_of="2026-09-20T00:00:00Z"),)
    ).document
    report = export_posture(source).document
    dims = {d["id"]: d for d in report["maintenance"]["dimensions"]}
    assert dims["maintenance:ci"]["state"] == "unknown"
    assert dims["maintenance:releases"]["state"] == "unknown"
    assert report["versions"]["candidates"][0]["freshness"] == "stale"
    assert report["versions"]["candidates"][0]["selected_target"] is None
    assert report["coverage"]["change_results"] == "not-supplied"


def test_export_is_offline_and_does_not_reinspect_the_repository(tmp_path, monkeypatch):
    _, source = assessed(tmp_path)

    def blocked(*args, **kwargs):
        raise AssertionError("Projection must not read the repository or connect to a service")

    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr("cli.maintenance.inventory_repository", blocked)
    result = export_posture(source)
    assert result.document["assessment_ref"] == "ref:" + source["digest"]


def test_human_output_exposes_every_canonical_action_and_dimension(tmp_path):
    _, source = assessed(tmp_path)
    report = export_posture(source)
    result = render_posture(report)
    for d in report.document["maintenance"]["dimensions"]:
        assert d["id"] in result and d["state"] in result
    for r in source["recommendations"]:
        assert r["id"] in result and r["action"] in result
    assert "1.1" in result and "Preview" in result
    assert source["target"] not in result and "example.invalid" not in result


def test_posture_schema_rejects_unexpected_raw_payload(tmp_path):
    _, source = assessed(tmp_path)
    document = export_posture(source).document
    document["maintenance"]["recommendations"][0]["raw_reason"] = "source-secret"
    with pytest.raises(ValueError):
        parse_posture(document)


def test_posture_replay_rejects_recomputed_digest_with_forged_dimension_counts(tmp_path):
    from cli.schema_validation import content_digest

    _, source = assessed(tmp_path)
    document = export_posture(source).document
    document["maintenance"]["summary"]["pass"] = 999
    document["digest"] = content_digest(
        canonical_json({k: v for k, v in document.items() if k != "digest"}).encode()
    )
    with pytest.raises(ValueError, match="summary"):
        parse_posture(document)


def test_bundled_example_replays_with_runtime_schema():
    document = json.loads((paths.GOVERNANCE_DIR / "examples/posture/maintenance.json").read_text())
    report = parse_posture(document)
    assert report.document["kind"] == "posture-export"
    assert report.document["maintenance"]["dimensions"]


@pytest.mark.parametrize("tamper", ["state", "exit_code"])
def test_posture_replay_rejects_optimistic_aggregate_even_with_recomputed_digest(tmp_path, tamper):
    from cli.schema_validation import content_digest

    _, source = assessed(tmp_path)
    document = export_posture(source).document
    assert document["maintenance"]["state"] != "pass"
    document["maintenance"][tamper] = "pass" if tamper == "state" else 0
    document["digest"] = content_digest(
        canonical_json({k: v for k, v in document.items() if k != "digest"}).encode()
    )
    with pytest.raises(ValueError, match="aggregate"):
        parse_posture(document)


@pytest.mark.parametrize("applies_to", ["new", "new-and-changed", "all"])
def test_accepted_transitions_keep_scope_mode_and_exception_expiry(tmp_path, applies_to):
    target, _ = installed(tmp_path)
    path = target / ".govkit/profile.yaml"
    profile = parse_document(path.read_text())
    accepted = {"reference": "private-architecture.md", "authority": "accepted"}
    profile["policy"]["transitions"] = [
        {
            "id": "private-transition",
            "source": accepted,
            "scope": ["private-scope"],
            "mode": "improve",
            "applies_to": applies_to,
            "current": [{"source": accepted, "scope": ["private-scope"]}],
            "target": [{"source": accepted, "scope": ["private-scope"]}],
            "exceptions": [
                {
                    "id": "private-exception",
                    "source": accepted,
                    "scope": ["private-scope"],
                    "expires_at": "2026-12-31",
                }
            ],
        }
    ]
    path.write_text(json.dumps(profile))
    source = assess_repository(target, as_of=AS_OF).document
    report = export_posture(source).document
    transition = report["architecture"]["transitions"][0]
    assert transition["mode"] == "improve" and transition["applies_to"] == applies_to
    assert transition["exceptions"][0]["expires_at"] == "2026-12-31"
    assert "private-" not in canonical_json(report)


def test_local_version_labels_are_referenced_without_disclosing_them(tmp_path):
    _, source = assessed(tmp_path, releases=[release("1.0"), release("1.1+privateperson")])
    document = export_posture(source).document
    candidate = document["versions"]["candidates"][0]
    assert candidate["selected_target"]["display"] == "1.1"
    assert candidate["selected_target"]["ref"].startswith("ref:")
    assert "privateperson" not in canonical_json(document)


def test_missing_profile_remains_explicit_in_posture(tmp_path):
    source = assess_repository(tmp_path, as_of=AS_OF).document
    document = export_posture(source).document
    assert document["coverage"]["profile"] == "missing"
    assert document["capabilities"]["configured"] == []
    assert document["coverage"]["change_results"] == "not-supplied"
    assert document["maintenance"]["state"] != "pass"


def test_human_report_keeps_metadata_sources_without_release_constraints(tmp_path):
    target, _ = installed(tmp_path)
    path = target / ".govkit/profile.yaml"
    profile = parse_document(path.read_text())
    profile["maintenance"]["constraints"] = []
    path.write_text(json.dumps(profile))
    report = export_posture(assess_repository(target, as_of=AS_OF, metadata=(metadata(),)).document)
    rendered = render_posture(report)
    source = report.document["versions"]["metadata"][0]
    assert source["source_ref"] in rendered
    assert source["lookup_status"] in rendered and source["as_of"] in rendered


@pytest.mark.parametrize("execution", ["not-run", "error"])
def test_posture_replay_cannot_count_unexecuted_maintenance_as_pass(tmp_path, execution):
    from cli.schema_validation import content_digest

    _, source = assessed(tmp_path)
    document = export_posture(source).document
    dimension = next(d for d in document["maintenance"]["dimensions"] if d["state"] == "pass")
    dimension["execution"] = execution
    document["maintenance"]["summary"]["executed"] -= 1
    document["digest"] = content_digest(
        canonical_json({k: v for k, v in document.items() if k != "digest"}).encode()
    )
    with pytest.raises(ValueError, match="execution"):
        parse_posture(document)
