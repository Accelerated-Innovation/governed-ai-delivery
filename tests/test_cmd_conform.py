"""Exercise real command dispatch and JSON/human views of one result protocol."""

import json

from cli.govkit import main
from tests.test_capability_packs import profile
from tests.test_pack_store import snapshot, write_profile


def invoke(monkeypatch, args):
    monkeypatch.setattr("sys.argv", ["govkit", "conform", *args])
    try:
        main()
    except SystemExit as exc:
        return exc.code
    return 0


def test_cli_reports_missing_required_controls_without_target_writes(tmp_path, monkeypatch, capsys):
    write_profile(tmp_path, profile([], checks=["security"]))
    before = snapshot(tmp_path)
    assert invoke(monkeypatch, ["--target", str(tmp_path), "--json"]) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["kind"] == "check-results"
    assert report["summary"]["required_satisfied"] < report["summary"]["required"]
    assert report["identity"]["revision"] is None
    assert invoke(monkeypatch, ["--target", str(tmp_path)]) == 1
    output = capsys.readouterr().out
    assert "security" in output and "UNKNOWN" in output and "Required checks satisfied" in output
    assert snapshot(tmp_path) == before


def test_cli_explicit_identity_and_invalid_argument_file(tmp_path, monkeypatch, capsys):
    write_profile(tmp_path, profile([]))
    assert (
        invoke(
            monkeypatch,
            [
                "--target",
                str(tmp_path),
                "--json",
                "--revision",
                "fixture-revision",
                "--observed-at",
                "2026-09-23T12:00:00Z",
            ],
        )
        == 0
    )
    document = json.loads(capsys.readouterr().out)
    assert document["identity"]["repository"] == "service"
    assert document["identity"]["revision"] == "fixture-revision"
    assert document["identity"]["observed_at"] == "2026-09-23T12:00:00Z"
    arguments = tmp_path / "arguments.json"
    arguments.write_text('{"quality":"not-an-array"}')
    before = snapshot(tmp_path)
    assert invoke(monkeypatch, ["--target", str(tmp_path), "--pack-arguments", str(arguments)]) == 1
    assert "arrays of strings" in capsys.readouterr().err
    assert snapshot(tmp_path) == before
