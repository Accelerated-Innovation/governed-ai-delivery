"""Public inventory, candidate preview and isolated release-cache refresh."""

import json
import sys

import pytest

from cli.govkit import main
from tests.test_maintenance_inventory import installed
from tests.test_pack_store import snapshot
from tests.test_release_metadata import AS_OF, metadata


def invoke(monkeypatch, *arguments):
    monkeypatch.setattr(sys, "argv", ["govkit", "maintain", *map(str, arguments)])
    main()


@pytest.mark.parametrize("action", ["verify", "preview"])
def test_missing_candidate_source_is_a_controlled_validation_error(
    tmp_path, monkeypatch, capsys, action
):
    from cli.maintenance import assess_repository
    from tests.test_maintenance import redigest_assessment

    target, _ = installed(tmp_path)
    document = assess_repository(target, as_of=AS_OF, metadata=(metadata(),)).document
    selected = next(r["id"] for r in document["recommendations"] if r["action"] == "upgrade-pack")
    document["inventory"]["candidates"][0]["source_id"] = "missing-source"
    record = tmp_path / "assessment.json"
    record.write_text(json.dumps(redigest_assessment(document)))
    before = snapshot(target)
    arguments = [action, "--target", target, "--assessment", record, "--as-of", AS_OF]
    if action == "preview":
        arguments.extend(["--recommendation", selected])
    with pytest.raises(SystemExit) as error:
        invoke(monkeypatch, *arguments)
    assert error.value.code == 1
    output = capsys.readouterr()
    assert "Error:" in output.err
    assert "Traceback" not in output.err
    assert not output.out
    assert snapshot(target) == before


def test_cli_inventory_is_read_only_and_has_human_and_json_views(tmp_path, monkeypatch, capsys):
    target, _ = installed(tmp_path)
    cache = tmp_path / "releases.json"
    cache.write_text(json.dumps(metadata()))
    before = snapshot(target)
    invoke(
        monkeypatch,
        "inventory",
        "--target",
        target,
        "--metadata",
        cache,
        "--as-of",
        AS_OF,
        "--json",
    )
    doc = json.loads(capsys.readouterr().out)
    assert doc["kind"] == "maintenance-inventory"
    assert doc["candidates"][0]["selected_target"] == "1.1.0"
    invoke(monkeypatch, "inventory", "--target", target, "--metadata", cache, "--as-of", AS_OF)
    text = capsys.readouterr().out
    assert "sample" in text and "1.1.0" in text and "read-only" in text
    assert snapshot(target) == before


def test_cli_refresh_cannot_write_inside_repository(tmp_path, monkeypatch, capsys):
    target, _ = installed(tmp_path)
    before = snapshot(target)
    with pytest.raises(SystemExit) as exit_info:
        invoke(
            monkeypatch,
            "refresh",
            "--target",
            target,
            "--release-source",
            "team",
            "--output",
            target / "cache.json",
            "--as-of",
            AS_OF,
        )
    assert exit_info.value.code == 1
    assert "outside" in capsys.readouterr().err
    assert snapshot(target) == before


def test_explicit_refresh_writes_only_named_external_cache(tmp_path, monkeypatch, capsys):
    import stat

    from cli import release_metadata
    from tests.test_release_metadata import project

    target, _ = installed(tmp_path)
    (target / ".govkit/profile.yaml").write_text(json.dumps(project(allow_refresh=True).document))
    before = snapshot(target)

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, count):
            return json.dumps(metadata()).encode()

    class Transport:
        def open(self, request, timeout):
            assert request.data is None
            return Response()

    monkeypatch.setattr(release_metadata, "build_opener", lambda handler: Transport())
    cache = tmp_path / "external-cache.json"
    invoke(
        monkeypatch,
        "refresh",
        "--target",
        target,
        "--release-source",
        "team",
        "--output",
        cache,
        "--as-of",
        AS_OF,
        "--json",
    )
    report = json.loads(capsys.readouterr().out)
    assert report == json.loads(cache.read_text())
    assert report["lookup_status"] == "refreshed"
    assert stat.S_IMODE(cache.stat().st_mode) == 0o600
    assert snapshot(target) == before


def test_cli_assess_prints_canonical_dimensions_without_writes(tmp_path, monkeypatch, capsys):
    target, _ = installed(tmp_path)
    before = snapshot(target)
    invoke(monkeypatch, "assess", "--target", target, "--as-of", AS_OF, "--json")
    report = json.loads(capsys.readouterr().out)
    assert report["kind"] == "maintenance-assessment"
    assert len(report["checks"]["results"]) == 4
    assert snapshot(target) == before


def test_cli_assessment_preview_requires_recommendation(tmp_path, monkeypatch, capsys):
    from cli.maintenance import assess_repository

    target, _ = installed(tmp_path)
    report = tmp_path / "assessment.json"
    report.write_text(assess_repository(target, as_of=AS_OF).to_json())
    with pytest.raises(SystemExit) as error:
        invoke(monkeypatch, "preview", "--target", target, "--assessment", report)
    assert error.value.code == 1
    assert "recommendation" in capsys.readouterr().err


def test_cli_verify_reports_remaining_findings(tmp_path, monkeypatch, capsys):
    from cli.maintenance import assess_repository

    target, _ = installed(tmp_path)
    (target / ".agents/skills/sample-help/SKILL.md").unlink()
    report = tmp_path / "assessment.json"
    report.write_text(assess_repository(target, as_of=AS_OF).to_json())
    invoke(
        monkeypatch,
        "verify",
        "--target",
        target,
        "--assessment",
        report,
        "--as-of",
        AS_OF,
        "--json",
    )
    result = json.loads(capsys.readouterr().out)
    assert result["remaining"]
    assert not result["resolved"]


def test_cli_verify_consumes_fresh_provider_results(tmp_path, monkeypatch, capsys):
    from cli.check_models import State
    from cli.maintenance import assess_repository
    from tests.test_maintenance import ci_evidence, ci_repository

    target = ci_repository(tmp_path)
    before = assess_repository(target, as_of=AS_OF, ci_report=ci_evidence(target, state=State.FAIL))
    record = tmp_path / "before.json"
    record.write_text(before.to_json())
    fresh = tmp_path / "ci.json"
    fresh.write_text(json.dumps(ci_evidence(target)))
    invoke(
        monkeypatch,
        "verify",
        "--target",
        target,
        "--assessment",
        record,
        "--ci-report",
        fresh,
        "--as-of",
        AS_OF,
        "--json",
    )
    result = json.loads(capsys.readouterr().out)
    original = next(r for r in before.document["recommendations"] if r["dimension"] == "ci")
    assert original["id"] in result["resolved"]
