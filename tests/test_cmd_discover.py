"""Real discover dispatch is read-only; report output is not acceptance."""

import json

import pytest

from cli.govkit import main
from cli.profiles import parse_profile
from cli.schema_validation import DocumentError
from tests.test_discovery import accepted_profile, write
from tests.test_pack_store import snapshot


def invoke(monkeypatch, args):
    monkeypatch.setattr("sys.argv", ["govkit", "discover", *args])
    try:
        main()
    except SystemExit as exc:
        return exc.code
    return 0


def test_cli_json_human_and_repeat_do_not_write(tmp_path, monkeypatch, capsys):
    target = tmp_path / "repo"
    target.mkdir()
    write(target, "server.py", "import mcp\n")
    args = ["--target", str(target)]
    before = snapshot(target)
    assert invoke(monkeypatch, [*args, "--json", "--capability", "llm-evaluation"]) == 0
    document = json.loads(capsys.readouterr().out)
    assert document["review"]
    with pytest.raises(DocumentError):
        parse_profile(document["proposed_profile"])
    record = write(tmp_path, "reviewed.json", json.dumps(document))
    assert (
        invoke(monkeypatch, [*args, "--baseline", str(record), "--capability", "llm-evaluation"])
        == 0
    )
    text = capsys.readouterr().out
    assert "Focused review: 0" in text
    assert "tool:mcp" in text and "checks were not executed" in text
    assert snapshot(target) == before


def test_cli_explicit_profile_prints_protected_operations(tmp_path, monkeypatch, capsys):
    source = accepted_profile(tmp_path)
    write(tmp_path, ".agents/skills/llm-evaluation/SKILL.md", "user-edited content")
    assert invoke(monkeypatch, ["--target", str(tmp_path), "--profile", str(source), "--json"]) == 0
    doc = json.loads(capsys.readouterr().out)
    assert not doc["install_ready"]
    assert any(o["action"] == "protected" for o in doc["operations"])


def test_cli_invalid_baseline_and_limits_fail_without_traceback(tmp_path, monkeypatch, capsys):
    path = write(tmp_path, "bad.json", '{"schema_version":1}')
    assert invoke(monkeypatch, ["--target", str(tmp_path), "--baseline", str(path)]) == 1
    assert "Error:" in capsys.readouterr().err
    assert invoke(monkeypatch, ["--target", str(tmp_path), "--max-files", "0"]) == 1
    assert "positive integers" in capsys.readouterr().err


def test_cli_legacy_single_file_marker_is_not_migrated(tmp_path, monkeypatch, capsys):
    write(tmp_path, ".govkit", '{"version":"0.1.0","level":4}')
    before = snapshot(tmp_path)
    assert invoke(monkeypatch, ["--target", str(tmp_path), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["accepted_profile"] is None
    assert snapshot(tmp_path) == before
