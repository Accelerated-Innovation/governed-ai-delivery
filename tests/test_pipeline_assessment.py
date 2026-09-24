"""Assessment/publication and candidate integration changes remain explicit."""

import json
import sys

import pytest

from cli.artifact_publication import publish_assessment
from cli.govkit import main
from cli.maintenance import assess_repository
from cli.pack_loading import load_pack
from cli.pipeline_assessment import upgrade_integration_preview
from cli.schema_validation import parse_document
from tests.test_maintenance_inventory import installed
from tests.test_pack_store import snapshot
from tests.test_pipeline_evidence import AS_OF, collect, configured
from tests.test_pipeline_render import settings
from tests.test_release_metadata import metadata


def test_pipeline_cli_uses_canonical_assessment_and_explicit_output(tmp_path, monkeypatch, capsys):
    target, config, runtime, observation = configured(tmp_path)
    runtime_path, observation_path = tmp_path / "runtime.json", tmp_path / "observation.json"
    runtime_path.write_text(json.dumps(runtime))
    observation_path.write_text(json.dumps(observation))
    expected = assess_repository(
        target, as_of=AS_OF, ci_report=collect(target, config, runtime, observation).to_document()
    ).document
    output = tmp_path / "assessment.json"
    before = snapshot(target)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "govkit",
            "pipeline",
            "assess",
            "--target",
            str(target),
            "--settings",
            str(config),
            "--change-report",
            str(runtime_path),
            "--observation",
            str(observation_path),
            "--as-of",
            AS_OF,
            "--output",
            str(output),
            "--json",
        ],
    )
    main()
    assert json.loads(capsys.readouterr().out) == expected == json.loads(output.read_text())
    assert snapshot(target) == before


@pytest.mark.parametrize("unsafe", ["target", "exists", "symlink", "symlink-parent"])
def test_publication_cannot_overwrite_or_enter_the_repository(tmp_path, unsafe):
    target = tmp_path / "consumer"
    target.mkdir()
    output = tmp_path / "assessment.json"
    if unsafe == "target":
        output = target / "new.json"
    elif unsafe == "exists":
        output.write_text("keep")
    elif unsafe == "symlink":
        victim = tmp_path / "victim"
        victim.write_text("keep")
        output.symlink_to(victim)
    else:
        parent = tmp_path / "linked"
        parent.symlink_to(target, target_is_directory=True)
        output = parent / "new.json"
    before = snapshot(target)
    with pytest.raises((OSError, ValueError)):
        publish_assessment({"test": True}, target, output)
    assert snapshot(target) == before
    if unsafe == "exists":
        assert output.read_text() == "keep"
    if unsafe == "symlink":
        assert victim.read_text() == "keep"


def candidate(tmp_path):
    target, root = installed(tmp_path)
    manifest = root / "manifest.yaml"
    manifest.write_text(manifest.read_text().replace("1.0.0", "1.1.0"))
    report = assess_repository(target, as_of=AS_OF, metadata=(metadata(),)).document
    recommendation = next(r for r in report["recommendations"] if r["action"] == "upgrade-pack")
    config = tmp_path / "settings.json"
    config.write_text(json.dumps(settings()))
    return target, load_pack(root), report, recommendation["id"], config


def test_selected_pack_upgrade_shows_minimal_configuration_and_follow_up(tmp_path):
    target, pack, report, identifier, config = candidate(tmp_path)
    before = snapshot(target)
    preview = upgrade_integration_preview(
        target, report, identifier, config, catalog=(pack,), as_of=AS_OF
    )
    assert preview["target_version"] == "1.1.0"
    integration = preview["integration"]
    assert integration["artifact"]["catalog"]["pins"]["packs"][0]["version"] == "1.1.0"
    assert {op["path"] for op in integration["operations"]} == {
        ".govkit/pipeline-lock.json",
        ".github/actions/govkit-conformance/action.yml",
    }
    assert integration["follow_up"] and integration["permissions"]
    assert integration["writes_authorized"] is False
    assert snapshot(target) == before


def test_upgrade_integration_marks_existing_team_configuration_protected(tmp_path):
    target, pack, _, _, config = candidate(tmp_path)
    existing = target / ".github/actions/govkit-conformance/action.yml"
    existing.parent.mkdir(parents=True)
    existing.write_text("# Team-owned action\n")
    report = assess_repository(target, as_of=AS_OF, metadata=(metadata(),)).document
    identifier = next(r["id"] for r in report["recommendations"] if r["action"] == "upgrade-pack")
    before = snapshot(target)
    preview = upgrade_integration_preview(
        target, report, identifier, config, catalog=(pack,), as_of=AS_OF
    )
    assert any(op["action"] == "protected" for op in preview["integration"]["operations"])
    assert snapshot(target) == before


def test_upgrade_marks_gate_affected_when_only_its_pinned_pack_changes(tmp_path):
    from cli.pipeline_store import apply_pipeline, preview_pipeline

    target, root = installed(tmp_path)
    config = tmp_path / "settings.json"
    config.write_text(json.dumps(settings()))
    initial = preview_pipeline(target / ".govkit/profile.yaml", target, config, (load_pack(root),))
    apply_pipeline(initial, initial.digest)
    manifest = root / "manifest.yaml"
    manifest.write_text(manifest.read_text().replace("1.0.0", "1.1.0"))
    report = assess_repository(target, as_of=AS_OF, metadata=(metadata(),)).document
    identifier = next(r["id"] for r in report["recommendations"] if r["action"] == "upgrade-pack")
    preview = upgrade_integration_preview(
        target, report, identifier, config, catalog=(load_pack(root),), as_of=AS_OF
    )
    assert "govkit:change-conformance" in preview["integration"]["affected_gates"]


@pytest.mark.parametrize("refresh", [False, True])
def test_assessment_only_refreshes_approved_metadata_when_explicitly_selected(
    tmp_path, monkeypatch, capsys, refresh
):
    import io

    target, root = installed(tmp_path)
    profile_path = target / ".govkit/profile.yaml"
    profile = parse_document(profile_path.read_bytes())
    profile["maintenance"]["allow_refresh"] = True
    profile_path.write_text(json.dumps(profile))
    config = tmp_path / "settings.json"
    config.write_text(json.dumps(settings()))
    requests = []

    class Transport:
        def open(self, request, timeout):
            requests.append(request)
            return io.BytesIO(json.dumps(metadata()).encode())

    monkeypatch.setattr("cli.release_metadata.build_opener", lambda *a: Transport())
    before = snapshot(target)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "govkit",
            "pipeline",
            "assess",
            "--target",
            str(target),
            "--settings",
            str(config),
            "--pack-source",
            str(root),
            "--as-of",
            AS_OF,
            "--json",
            *(["--release-source", "team"] if refresh else []),
        ],
    )
    main()
    report = json.loads(capsys.readouterr().out)
    assert report["inventory"]["metadata"][0]["lookup_status"] == (
        "refreshed" if refresh else "unavailable"
    )
    assert len(requests) == int(refresh)
    assert all(r.data is None and "Authorization" not in r.headers for r in requests)
    assert snapshot(target) == before
