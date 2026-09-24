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
