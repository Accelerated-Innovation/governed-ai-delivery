"""Exercise the actual CLI dispatcher and profile service without a consumer install."""

import json

import yaml

from cli.govkit import main
from tests.test_profiles import profile_document


def invoke(monkeypatch, args):
    monkeypatch.setattr("sys.argv", ["govkit", "profile", *args])
    try:
        main()
    except SystemExit as exc:
        return exc.code
    return 0


def test_cli_preview_and_explicit_apply(monkeypatch, tmp_path, capsys):
    source = tmp_path / "input.yaml"
    source.write_text(yaml.safe_dump(profile_document()))
    target = tmp_path / "consumer"
    target.mkdir()
    args = ["--profile", str(source), "--target", str(target), "--json"]
    assert invoke(monkeypatch, ["preview", *args]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["resolution"]["plan"]["integrations"]["stack"] is None
    assert report["operations"][0]["action"] == "create"
    assert list(target.iterdir()) == []
    assert invoke(monkeypatch, ["apply", *args]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["applied"] is True
    assert (target / ".govkit/resolution.json").is_file()
    assert not (target / ".govkit/marker.json").exists()


def test_cli_invalid_input_is_actionable_and_writes_nothing(monkeypatch, tmp_path, capsys):
    source = tmp_path / "input.yaml"
    source.write_text("schema_version: 99\n")
    assert invoke(monkeypatch, ["apply", "--profile", str(source), "--target", str(tmp_path)]) == 1
    out = capsys.readouterr()
    assert "Error:" in out.err and "schema_version" in out.err
    assert not (tmp_path / ".govkit").exists()


def test_cli_default_profile_path_and_readable_unknowns(monkeypatch, tmp_path, capsys):
    (tmp_path / ".govkit").mkdir()
    (tmp_path / ".govkit/profile.yaml").write_text(yaml.safe_dump(profile_document()))
    assert invoke(monkeypatch, ["preview", "--target", str(tmp_path)]) == 0
    output = capsys.readouterr().out
    assert "stack" in output and "unknown" in output.lower()
    assert "security" in output and "small-change" in output
    assert not (tmp_path / ".govkit/resolution.json").exists()
