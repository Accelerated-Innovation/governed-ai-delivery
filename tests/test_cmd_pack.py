"""The public pack CLI must exercise real graph/install/check services."""

import json

from cli.govkit import main
from tests.test_capability_packs import make_pack, profile
from tests.test_pack_store import write_profile


def invoke(monkeypatch, arguments):
    monkeypatch.setattr("sys.argv", ["govkit", "pack", *arguments])
    try:
        main()
    except SystemExit as exc:
        return exc.code
    return 0


def test_list_and_local_source_preview_apply_verify(monkeypatch, tmp_path, capsys):
    target = tmp_path / "consumer"
    write_profile(target, profile(["sample"]))
    source = make_pack(tmp_path / "source", skills=True)
    assert invoke(monkeypatch, ["list", "--source", str(source), "--json"]) == 0
    assert "sample" in {p["id"] for p in json.loads(capsys.readouterr().out)["available"]}
    arguments = ["--target", str(target), "--source", str(source), "--json"]
    assert invoke(monkeypatch, ["preview", *arguments]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["resolution"]["execution"] == "not-run"
    assert not (target / ".govkit/pack-lock.json").exists()
    assert invoke(monkeypatch, ["apply", *arguments]) == 0
    capsys.readouterr()
    assert invoke(monkeypatch, ["verify", "--target", str(target), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["ready"] is True
    (target / ".agents/skills/sample-help/SKILL.md").write_text("custom")
    assert invoke(monkeypatch, ["verify", "--target", str(target)]) == 1
    assert "resource-drift" in capsys.readouterr().out


def test_unresolved_cli_apply_returns_failure_without_writes(monkeypatch, tmp_path, capsys):
    target = tmp_path / "consumer"
    write_profile(target, profile(["unknown"]))
    assert invoke(monkeypatch, ["preview", "--target", str(target), "--json"]) == 1
    assert (
        json.loads(capsys.readouterr().out)["resolution"]["decisions"][0]["code"]
        == "missing-capability"
    )
    assert invoke(monkeypatch, ["apply", "--target", str(target)]) == 1
    assert "unresolved" in capsys.readouterr().err
    assert not (target / ".govkit/pack-lock.json").exists()


def test_check_cli_forwards_arguments_and_exit_status(monkeypatch, tmp_path, capsys):
    target = tmp_path / "consumer"
    write_profile(target, profile(["llm-evaluation"], checks=["llm-exact-match"]))
    assert invoke(monkeypatch, ["apply", "--target", str(target)]) == 0
    capsys.readouterr()
    results = target / "results.json"
    results.write_text('{"cases":[{"id":"test","expected":"yes","actual":"no"}]}')
    assert (
        invoke(
            monkeypatch,
            [
                "check",
                "--target",
                str(target),
                "llm-exact-match",
                "--",
                "--results",
                "results.json",
            ],
        )
        == 1
    )
    assert json.loads(capsys.readouterr().out)["failed"] == ["test"]
