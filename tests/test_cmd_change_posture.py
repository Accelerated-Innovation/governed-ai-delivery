"""Saved change facts use explicit private publication and safe diagnostics."""

import json
import sys

import pytest

from cli.govkit import main
from tests.test_change_conformance import inspect, setup
from tests.test_discovery import write
from tests.test_pack_store import snapshot


def saved_change(tmp_path):
    target, trusted, base = setup(tmp_path)
    write(target, "src/service.py", "# good updated\n")
    source = inspect(target, trusted, base).document
    path = tmp_path / "change-results.json"
    path.write_text(json.dumps(source))
    return target, trusted, source, path


@pytest.mark.parametrize("json_output", [False, True])
def test_cli_projects_saved_change_and_publishes_without_changing_either_checkout(
    tmp_path, monkeypatch, capsys, json_output
):
    target, trusted, source, path = saved_change(tmp_path)
    output = tmp_path / "posture.json"
    before = snapshot(target), snapshot(trusted)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "govkit",
            "posture",
            "change",
            "--results",
            str(path),
            "--target",
            str(target),
            "--output",
            str(output),
            *(["--json"] if json_output else []),
        ],
    )

    with pytest.raises(SystemExit) as error:
        main()

    captured = capsys.readouterr()
    assert error.value.code == 0 and not captured.err
    document = json.loads(output.read_text())
    assert document["results"]["exit_code"] == source["exit_code"] == 1
    assert document["results"]["summary"] == source["checks"]["summary"]
    if json_output:
        assert json.loads(captured.out) == document
    else:
        for control in document["results"]["controls"]:
            assert control["ref"] in captured.out and control["state"] in captured.out
    assert output.stat().st_mode & 0o777 == 0o600
    assert (snapshot(target), snapshot(trusted)) == before


@pytest.mark.parametrize(
    "destination", ["inside", "existing", "symlink", "no-target", "unused-target"]
)
def test_cli_refuses_unsafe_or_incomplete_change_publication(
    tmp_path, monkeypatch, capsys, destination
):
    target, trusted, _, path = saved_change(tmp_path)
    output = target / "posture.json" if destination == "inside" else tmp_path / "posture.json"
    owner = tmp_path / "owner"
    owner.write_text("owner bytes")
    if destination == "existing":
        output.write_text("original")
    elif destination == "symlink":
        output.symlink_to(owner)
    before = snapshot(target), snapshot(trusted)
    args = ["govkit", "posture", "change", "--results", str(path)]
    if destination != "no-target":
        args += ["--target", str(target)]
    if destination != "unused-target":
        args += ["--output", str(output)]
    monkeypatch.setattr(sys, "argv", args)

    with pytest.raises(SystemExit) as error:
        main()

    captured = capsys.readouterr()
    assert error.value.code == 1 and not captured.out
    assert "Unable to export change posture" in captured.err
    assert (snapshot(target), snapshot(trusted)) == before
    assert owner.read_text() == "owner bytes"
    if destination == "existing":
        assert output.read_text() == "original"
    elif destination == "symlink":
        assert output.is_symlink()
    else:
        assert not output.exists()


def test_cli_change_validation_diagnostic_does_not_echo_source_payload(
    tmp_path, monkeypatch, capsys
):
    path = tmp_path / "secret.json"
    path.write_text('{"private-request-secret":"private-person"}')
    monkeypatch.setattr(sys, "argv", ["govkit", "posture", "change", "--results", str(path)])

    with pytest.raises(SystemExit) as error:
        main()

    captured = capsys.readouterr()
    assert error.value.code == 1 and not captured.out
    assert "private" not in captured.err
    assert "Unable to export change posture" in captured.err
