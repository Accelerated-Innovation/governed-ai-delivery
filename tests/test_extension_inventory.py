"""Read-only inventory of installed extensions across legacy and declarative installs."""

from __future__ import annotations

import argparse
import json
import shutil

import pytest

from cli import paths
from cli.extension_inventory import installed_extensions
from cli.pack_loading import load_pack
from cli.pack_store import apply_install, preview_install
from cli.schema_validation import validate_document
from tests.test_capability_packs import profile
from tests.test_pack_store import snapshot, write_profile

SOAA = "skill-oriented-agent-architecture"
LLM = "llm-application"


def legacy_install(target, pack_id=SOAA):
    shutil.copytree(paths.EXTENSION_PACKS_DIR / pack_id, target / "extensions" / pack_id)


def declarative_install(target, *pack_ids):
    catalog = tuple(
        load_pack(paths.EXTENSION_PACKS_DIR / pack_id, source_kind="bundled")
        for pack_id in pack_ids
    )
    path = write_profile(target, profile(list(pack_ids)))
    preview = preview_install(path, target, catalog, govkit_version="0.22.0")
    assert preview.resolution.ready, preview.resolution
    apply_install(preview)
    return catalog


def core_documents(target):
    """The core architecture documents SOAA's relates_to entries extend."""
    folder = target / "docs" / "backend" / "architecture"
    folder.mkdir(parents=True, exist_ok=True)
    for name in (
        "ARCH_CONTRACT",
        "BOUNDARIES",
        "SECURITY_AUTH_PATTERNS",
        "OBSERVABILITY_PORT_CONTRACT",
        "TESTING",
    ):
        (folder / f"{name}.md").write_text("x\n", encoding="utf-8")


def by_source(inventory, source):
    return {e.id: e for e in inventory.extensions if e.source == source}


def test_empty_project_has_nothing_installed(tmp_path):
    inventory = installed_extensions(tmp_path)
    assert inventory.extensions == () and inventory.conflicts == ()
    assert inventory.lock == "absent" and inventory.ready


def test_legacy_install_lists_contract_sets_with_root_prefixed_paths(tmp_path):
    legacy_install(tmp_path)
    inventory = installed_extensions(tmp_path)
    [soaa] = inventory.extensions
    assert (soaa.id, soaa.source, soaa.status) == (SOAA, "legacy", "valid")
    assert soaa.root == f"extensions/{SOAA}"
    core = next(cs for cs in soaa.contract_sets if cs["id"] == "soaa_core")
    assert "governed-agent-runtime" in core["capabilities"]
    assert "**/*agent*" in core["applies_to"]
    assert all(p.startswith(f"extensions/{SOAA}/docs/") for p in core["paths"])
    assert all((tmp_path / p).is_file() for cs in soaa.contract_sets for p in cs["paths"])
    assert f"extensions/{SOAA}/README.md" in soaa.resources
    assert inventory.ready


def test_missing_core_documents_are_listed_but_do_not_invalidate(tmp_path):
    """Before `govkit apply` installs core docs, relates_to targets are missing;
    the extension's own contracts are still usable (doctor treats this as D014)."""
    legacy_install(tmp_path)
    [soaa] = installed_extensions(tmp_path).extensions
    assert soaa.status == "valid" and soaa.contract_sets
    assert soaa.issues and all("relates_to" in issue for issue in soaa.issues)
    core_documents(tmp_path)
    [soaa] = installed_extensions(tmp_path).extensions
    assert soaa.issues == ()


def test_markerless_declarative_install_lists_pinned_contracts(tmp_path):
    [snapshot_pack] = declarative_install(tmp_path, SOAA)
    inventory = installed_extensions(tmp_path)
    [soaa] = inventory.extensions
    root = f".govkit/packs/{SOAA}/{snapshot_pack.digest}"
    assert (soaa.source, soaa.status, soaa.root) == ("declarative", "verified", root)
    assert soaa.version == snapshot_pack.version
    assert inventory.lock == "verified" and inventory.ready
    paths_listed = [p for cs in soaa.contract_sets for p in cs["paths"]]
    assert len(paths_listed) == 9
    assert all(p.startswith(root + "/") and (tmp_path / p).is_file() for p in paths_listed)
    assert not (tmp_path / ".govkit" / "marker.json").exists()


def test_mixed_install_reports_conflicting_copies(tmp_path):
    declarative_install(tmp_path, SOAA)
    legacy_install(tmp_path)
    inventory = installed_extensions(tmp_path)
    assert set(by_source(inventory, "legacy")) == set(by_source(inventory, "declarative")) == {SOAA}
    [conflict] = inventory.conflicts
    assert (conflict.kind, conflict.extension) == ("legacy-and-declarative", SOAA)
    assert f"extensions/{SOAA}" in conflict.roots
    assert not inventory.ready


def test_tampered_lock_marks_declarative_resources_unverified(tmp_path):
    declarative_install(tmp_path, SOAA)
    contract = next((tmp_path / ".govkit" / "packs").rglob("SKILL_CONTRACT.md"))
    contract.write_text("tampered", encoding="utf-8")
    inventory = installed_extensions(tmp_path)
    [soaa] = inventory.extensions
    assert soaa.status == "unverified"
    assert soaa.contract_sets == () and soaa.resources == ()
    assert inventory.lock == "unverified" and not inventory.ready


def test_orphan_pack_directory_is_reported(tmp_path):
    declarative_install(tmp_path, SOAA)
    orphan = tmp_path / ".govkit" / "packs" / LLM / ("0" * 64)
    orphan.mkdir(parents=True)
    (orphan / "manifest.yaml").write_text("id: llm-application\n", encoding="utf-8")
    inventory = installed_extensions(tmp_path)
    kinds = {(c.kind, c.extension) for c in inventory.conflicts}
    assert ("orphan-pack-directory", LLM) in kinds
    assert not inventory.ready


def test_invalid_legacy_manifest_carries_diagnostics(tmp_path):
    broken = tmp_path / "extensions" / "broken"
    broken.mkdir(parents=True)
    (broken / "manifest.yaml").write_text("id: broken\ncontract_sets: oops\n", encoding="utf-8")
    inventory = installed_extensions(tmp_path)
    [entry] = inventory.extensions
    assert entry.status == "invalid" and entry.issues
    assert entry.contract_sets == ()
    assert not inventory.ready


def test_inventory_is_read_only(tmp_path):
    declarative_install(tmp_path, SOAA, LLM)
    legacy_install(tmp_path, LLM)
    before = snapshot(tmp_path)
    installed_extensions(tmp_path)
    assert snapshot(tmp_path) == before


def test_inventory_document_validates_against_its_schema(tmp_path):
    declarative_install(tmp_path, SOAA)
    legacy_install(tmp_path)
    document = installed_extensions(tmp_path).to_document()
    validate_document(document, "extension-inventory")
    assert document["kind"] == "extension-inventory"
    assert document["ready"] is False
    assert any("not accepted project policy" in item for item in document["limitations"])


# ---------------------------------------------------------------------------
# `govkit extension list --installed`
# ---------------------------------------------------------------------------


def run_list(target, *extra):
    from cli.cmd_extension import register

    parser = argparse.ArgumentParser()
    register(parser.add_subparsers())
    args = parser.parse_args(["extension", "list", *extra, "--target", str(target)])
    args.func(args)


def test_list_installed_json(tmp_path, capsys):
    declarative_install(tmp_path, SOAA)
    run_list(tmp_path, "--installed", "--json")
    document = json.loads(capsys.readouterr().out)
    validate_document(document, "extension-inventory")
    assert [e["id"] for e in document["extensions"]] == [SOAA]


def test_list_installed_text_and_exit_on_conflict(tmp_path, capsys):
    declarative_install(tmp_path, SOAA)
    legacy_install(tmp_path)
    with pytest.raises(SystemExit) as exit_info:
        run_list(tmp_path, "--installed")
    assert exit_info.value.code == 1
    out = capsys.readouterr().out
    assert SOAA in out and "legacy-and-declarative" in out
    assert ".govkit/packs/" in out and f"extensions/{SOAA}" in out


def test_list_installed_requires_target(capsys):
    from cli.cmd_extension import register

    parser = argparse.ArgumentParser()
    register(parser.add_subparsers())
    args = parser.parse_args(["extension", "list", "--installed"])
    with pytest.raises(SystemExit) as exit_info:
        args.func(args)
    assert exit_info.value.code == 1
    assert "--target" in capsys.readouterr().err


def test_bundled_listing_is_unchanged(capsys):
    from cli.cmd_extension import register

    parser = argparse.ArgumentParser()
    register(parser.add_subparsers())
    args = parser.parse_args(["extension", "list"])
    args.func(args)
    out = capsys.readouterr().out
    assert "Available extension packs:" in out and SOAA in out


# ---------------------------------------------------------------------------
# Consumers: skill context and the legacy extension conformance check
# ---------------------------------------------------------------------------


def test_skill_context_lists_declarative_extensions_with_roots(tmp_path):
    from cli.skill_context import _extension_facts

    [snapshot_pack] = declarative_install(tmp_path, SOAA)
    legacy_install(tmp_path, LLM)
    facts = {(f["id"], f["source"]): f for f in _extension_facts(tmp_path)}
    soaa = facts[(SOAA, "declarative")]
    assert soaa["root"] == f".govkit/packs/{SOAA}/{snapshot_pack.digest}"
    assert soaa["status"] == "verified" and soaa["conflicts"] == []
    assert len(soaa["capabilities"]) == 32
    llm = facts[(LLM, "legacy")]
    assert llm["root"] == f"extensions/{LLM}"
    assert all(not p.startswith("extensions/") for p in llm["contract_paths"])


def test_skill_context_marks_conflicting_copies(tmp_path):
    from cli.skill_context import _extension_facts

    declarative_install(tmp_path, SOAA)
    legacy_install(tmp_path)
    facts = _extension_facts(tmp_path)
    assert {f["source"] for f in facts if f["id"] == SOAA} == {"legacy", "declarative"}
    assert all(f["conflicts"] == ["legacy-and-declarative"] for f in facts if f["id"] == SOAA)


def test_legacy_extension_check_warns_on_conflicting_copies(tmp_path):
    from cli.check_adapters import extension_check
    from cli.check_models import CheckContext, Identity, State

    declarative_install(tmp_path, SOAA)
    legacy_install(tmp_path)
    core_documents(tmp_path)
    outcome = extension_check(CheckContext(tmp_path, Identity(repository="r")))
    assert {(f.code, f.severity) for f in outcome.findings} == {("extension-conflict", "warning")}
    assert outcome.state is State.UNKNOWN
