"""Explicit offline posture publication preserves source and destination ownership."""

import json
import sys

import pytest

from cli.govkit import main
from cli.posture import export_posture
from tests.test_pack_store import snapshot
from tests.test_posture import assessed, assessed_with_missing_owners


def saved(tmp_path):
    target, source = assessed(tmp_path)
    path = tmp_path / "assessment.json"
    path.write_text(json.dumps(source))
    return target, source, path


@pytest.mark.parametrize("json_output", [False, True])
def test_cli_exports_and_publishes_assessment_with_unknown_resource_owner(
    tmp_path, monkeypatch, capsys, json_output
):
    target, source, _ = assessed_with_missing_owners(tmp_path)
    path = tmp_path / "assessment.json"
    path.write_text(json.dumps(source))
    output = tmp_path / "posture.json"
    before = snapshot(target)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "govkit",
            "posture",
            "export",
            "--assessment",
            str(path),
            "--output",
            str(output),
            *(["--json"] if json_output else []),
        ],
    )

    with pytest.raises(SystemExit) as error:
        main()

    result = capsys.readouterr()
    assert error.value.code == 0
    assert result.err == ""
    document = json.loads(output.read_text())
    assert document["resources"][0]["component_ref"] is None
    assert document["capabilities"]["lock_verification"] == "unverified"
    if json_output:
        assert json.loads(result.out) == document
    else:
        for item in source["recommendations"]:
            assert item["id"] in result.out and item["action"] in result.out
    assert output.stat().st_mode & 0o777 == 0o600
    assert snapshot(target) == before


@pytest.mark.parametrize("json_output", [False, True])
def test_cli_reports_saved_canonical_facts_without_modifying_target(
    tmp_path, monkeypatch, capsys, json_output
):
    target, source, path = saved(tmp_path)
    before = snapshot(target)
    expected = export_posture(source).document
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "govkit",
            "posture",
            "export",
            "--assessment",
            str(path),
            *(["--json"] if json_output else []),
        ],
    )
    with pytest.raises(SystemExit) as error:
        main()
    result = capsys.readouterr()
    assert error.value.code == 0  # Export success is not a conformance gate.
    assert result.err == ""
    if json_output:
        assert json.loads(result.out) == expected
    else:
        for item in expected["maintenance"]["recommendations"]:
            assert item["id"] in result.out and item["action"] in result.out
    assert snapshot(target) == before


def test_cli_publication_creates_private_json_outside_assessed_repository(
    tmp_path, monkeypatch, capsys
):
    target, source, path = saved(tmp_path)
    output = tmp_path / "posture.json"
    before = snapshot(target)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "govkit",
            "posture",
            "export",
            "--assessment",
            str(path),
            "--output",
            str(output),
            "--json",
        ],
    )
    with pytest.raises(SystemExit) as error:
        main()
    result = capsys.readouterr()
    assert error.value.code == 0
    assert (
        json.loads(result.out) == json.loads(output.read_text()) == export_posture(source).document
    )
    assert output.stat().st_mode & 0o777 == 0o600
    assert snapshot(target) == before


@pytest.mark.parametrize("destination", ["inside", "existing", "symlink"])
def test_cli_unsafe_publication_is_rejected_without_replacing_files(
    tmp_path, monkeypatch, capsys, destination
):
    target, _, path = saved(tmp_path)
    output = target / "posture.json" if destination == "inside" else tmp_path / "posture.json"
    protected = tmp_path / "owner.json"
    protected.write_text("owner bytes")
    if destination == "existing":
        output.write_text("original")
    elif destination == "symlink":
        output.symlink_to(protected)
    before = snapshot(target)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "govkit",
            "posture",
            "export",
            "--assessment",
            str(path),
            "--output",
            str(output),
            "--json",
        ],
    )
    with pytest.raises(SystemExit) as error:
        main()
    result = capsys.readouterr()
    assert error.value.code == 1 and not result.out
    assert "Unable to export posture" in result.err
    assert protected.read_text() == "owner bytes"
    assert snapshot(target) == before
    if destination == "existing":
        assert output.read_text() == "original"
    if destination == "symlink":
        assert output.is_symlink()


def test_cli_invalid_input_diagnostic_does_not_echo_sensitive_payload(
    tmp_path, monkeypatch, capsys
):
    path = tmp_path / "assessment.json"
    path.write_text('{"raw_secret":"private-secret-prompt"}')
    monkeypatch.setattr(
        sys, "argv", ["govkit", "posture", "export", "--assessment", str(path), "--json"]
    )
    with pytest.raises(SystemExit) as error:
        main()
    result = capsys.readouterr()
    assert error.value.code == 1
    assert "private-secret-prompt" not in result.err + result.out
    assert "Unable to export posture" in result.err
