"""Explicit offline fleet command, with diagnostics that do not leak input data."""

import json
import sys

import pytest

from cli import paths
from cli.govkit import main


def invoke(monkeypatch, capsys, args):
    monkeypatch.setattr(sys, "argv", ["govkit", "posture", "aggregate", *args])
    with pytest.raises(SystemExit) as error:
        main()
    return error.value.code, capsys.readouterr()


@pytest.mark.parametrize("json_output", [True, False])
def test_cli_aggregates_explicit_saved_exports_without_writing(
    tmp_path, monkeypatch, capsys, json_output
):
    source = paths.GOVERNANCE_DIR / "examples/posture/maintenance.json"
    doc = json.loads(source.read_text())
    saved = tmp_path / "input.json"
    saved.write_text(json.dumps(doc))
    before = saved.read_bytes(), saved.stat().st_mtime_ns
    args = [
        "--report",
        str(saved),
        "--repository-ref",
        doc["repository_ref"],
        "--as-of",
        "2026-09-24T12:00:00Z",
    ]
    if json_output:
        args.append("--json")

    code, out = invoke(monkeypatch, capsys, args)

    assert code == 0 and not out.err
    if json_output:
        result = json.loads(out.out)
        assert result["summary"]["maintenance"]["assessed_repositories"] == 1
        assert result["summary"]["changes"]["missing_repositories"] == 1
    else:
        assert "summary/maintenance/assessed_repositories: 1" in out.out
    assert (saved.read_bytes(), saved.stat().st_mtime_ns) == before
    assert list(tmp_path.iterdir()) == [saved]


@pytest.mark.parametrize(
    "content", ['{"private_key":"secret-value"}', "{bad", '{"kind":1}', '{"kind":[]}']
)
def test_cli_rejects_bad_exports_without_echoing_paths_or_payloads(
    tmp_path, monkeypatch, capsys, content
):
    saved = tmp_path / "private-ticket-secret.json"
    saved.write_text(content)
    code, out = invoke(
        monkeypatch,
        capsys,
        [
            "--report",
            str(saved),
            "--repository-ref",
            "ref:" + "a" * 64,
            "--as-of",
            "2026-09-24T12:00:00Z",
            "--json",
        ],
    )
    assert code == 1 and not out.out
    assert "Unable to aggregate posture" in out.err
    assert str(saved) not in out.err and "secret" not in out.err
    assert saved.read_text() == content
