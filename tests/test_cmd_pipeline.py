"""Read-only gate catalog views use the same domain contract."""

import json
import sys

import pytest

from cli.govkit import main
from tests.test_capability_packs import profile
from tests.test_pack_store import snapshot


@pytest.mark.parametrize("provider", ["github", "azure"])
def test_catalog_cli_never_writes_or_claims_execution(tmp_path, monkeypatch, capsys, provider):
    target = tmp_path / "consumer"
    (target / ".govkit").mkdir(parents=True)
    document = profile(["application-governance", "llm-evaluation"]).document
    document["integrations"]["ci"] = provider
    (target / ".govkit/profile.yaml").write_text(json.dumps(document))
    before = snapshot(target)
    monkeypatch.setattr(
        sys, "argv", ["govkit", "pipeline", "catalog", "--target", str(target), "--json"]
    )
    main()
    catalog = json.loads(capsys.readouterr().out)
    assert catalog["provider"] == provider
    assert catalog["ready"] and catalog["execution"] == "not-run"
    assert catalog["enforcement"] == "unknown"
    assert {g["id"] for g in catalog["gates"]} == {"govkit:change-conformance", "llm-exact-match"}
    assert snapshot(target) == before


def test_unresolved_catalog_is_printed_but_exits_unsuccessfully(tmp_path, monkeypatch, capsys):
    source = tmp_path / "profile.json"
    source.write_text(json.dumps(profile(["unknown-capability"]).document))
    monkeypatch.setattr(
        sys, "argv", ["govkit", "pipeline", "catalog", "--profile", str(source), "--json"]
    )
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 1
    report = json.loads(capsys.readouterr().out)
    assert not report["ready"]
    assert report["decisions"]


def test_human_catalog_names_limits_and_controls(tmp_path, monkeypatch, capsys):
    source = tmp_path / "profile.json"
    source.write_text(json.dumps(profile(["llm-evaluation"]).document))
    monkeypatch.setattr(sys, "argv", ["govkit", "pipeline", "catalog", "--profile", str(source)])
    main()
    output = capsys.readouterr().out
    assert "llm-exact-match" in output
    assert "not-run" in output and "unknown" in output


def test_pipeline_cli_requires_reviewed_digest_and_reports_configuration_only(
    tmp_path, monkeypatch, capsys
):
    from tests.test_pipeline_store import setup

    source, target, config = setup(tmp_path)
    common = [
        "--target",
        str(target),
        "--profile",
        str(source),
        "--settings",
        str(config),
        "--json",
    ]

    def invoke(action, *extra, failed=False):
        monkeypatch.setattr(sys, "argv", ["govkit", "pipeline", action, *common, *extra])
        if failed:
            with pytest.raises(SystemExit) as error:
                main()
            assert error.value.code == 1
        else:
            main()
        return capsys.readouterr()

    initial = snapshot(target)
    assert json.loads(invoke("check", failed=True).out)["configuration"] == "missing"
    preview = json.loads(invoke("preview").out)
    assert snapshot(target) == initial
    assert "digest" in invoke("generate", failed=True).err
    invoke("generate", "--accept-digest", preview["digest"])
    checked = json.loads(invoke("check").out)
    assert checked["configuration"] == "current"
    assert checked["execution"] == "unknown" and checked["enforcement"] == "unknown"
