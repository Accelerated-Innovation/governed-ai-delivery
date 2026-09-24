"""One shared legacy CI selection preserves custom manifests and ordering."""

import json
import sys
from copy import deepcopy

import pytest

from cli import paths
from cli.gate_legacy import expand_legacy_ci
from cli.govkit import main
from cli.manifest import load_manifest, resolve_variant_files
from cli.schema_validation import validate_document


@pytest.mark.parametrize("agent", ["codex", "claude-code", "copilot"])
def test_bundled_manifests_reference_one_shared_ci_selection(agent):
    raw = json.loads((paths.AGENTS_DIR / agent / "manifest.json").read_text())
    validate_document(raw, "agent-manifest")
    assert raw["ci_catalog"] == "builtin:legacy-ci-v1"
    assert "ci" not in raw["variants"]
    resolved = load_manifest(agent)
    assert "ci" in resolved["variants"]
    assert resolve_variant_files(
        raw, {"type": "api", "level": "4", "ci": "github"}
    ) == resolve_variant_files(resolved, {"type": "api", "level": "4", "ci": "github"})


def test_custom_inline_ci_selection_is_unchanged_and_not_mutated():
    manifest = {"agent": "custom", "variants": {"ci": {"github": {"governed": ["custom.yml"]}}}}
    original = deepcopy(manifest)
    assert expand_legacy_ci(manifest) == original
    assert resolve_variant_files(manifest, {"ci": "github"})[2] == ["custom.yml"]
    assert manifest == original


@pytest.mark.parametrize("case", ["unknown", "ambiguous"])
def test_invalid_reference_cannot_silently_drop_or_override_ci(case):
    manifest = {"agent": "custom", "ci_catalog": "builtin:legacy-ci-v1", "variants": {}}
    if case == "unknown":
        manifest["ci_catalog"] = "https://example.invalid/ci.json"
    else:
        manifest["variants"]["ci"] = {}
    with pytest.raises(ValueError):
        expand_legacy_ci(manifest)


def test_shared_catalog_uses_live_bundled_paths_and_missing_payload_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "GOVERNANCE_DIR", tmp_path)
    manifest = {"agent": "custom", "ci_catalog": "builtin:legacy-ci-v1", "variants": {}}
    with pytest.raises(ValueError, match="catalog"):
        expand_legacy_ci(manifest)


@pytest.mark.parametrize("change", ["missing-providers", "boolean-version"])
def test_malformed_shared_payload_cannot_silently_disable_ci(tmp_path, monkeypatch, change):
    document = json.loads((paths.GOVERNANCE_DIR / "ci/legacy-selection.json").read_text())
    (tmp_path / "schemas").mkdir()
    (tmp_path / "schemas/agent-manifest.schema.json").write_bytes(
        (paths.GOVERNANCE_DIR / "schemas/agent-manifest.schema.json").read_bytes()
    )
    if change == "missing-providers":
        document["variants"] = {}
    else:
        document["schema_version"] = True
    (tmp_path / "ci").mkdir()
    (tmp_path / "ci/legacy-selection.json").write_text(json.dumps(document))
    monkeypatch.setattr(paths, "GOVERNANCE_DIR", tmp_path)
    with pytest.raises(ValueError, match="catalog"):
        expand_legacy_ci({"ci_catalog": "builtin:legacy-ci-v1", "variants": {}})


@pytest.mark.parametrize("variants", [None, [], {"type": {}}])
def test_shared_reference_rejects_flat_or_malformed_variant_manifests(variants):
    manifest = {
        "agent": "custom",
        "files": [{"src": "rule.md", "dest": "RULE.md"}],
        "ci_catalog": "builtin:legacy-ci-v1",
    }
    if variants is not None:
        manifest["variants"] = variants
    original = deepcopy(manifest)
    with pytest.raises(ValueError, match="variant"):
        expand_legacy_ci(manifest)
    assert manifest == original


@pytest.mark.parametrize("variants", [None, [], "invalid"])
def test_shared_reference_requires_a_variant_mapping(variants):
    with pytest.raises(ValueError, match="variant"):
        expand_legacy_ci({"ci_catalog": "builtin:legacy-ci-v1", "variants": variants})


@pytest.mark.parametrize("shared_reference", [False, True])
def test_flat_custom_apply_preserves_files_or_rejects_reference_before_writes(
    tmp_path, monkeypatch, capsys, shared_reference
):
    agent_dir = tmp_path / "agents/custom"
    agent_dir.mkdir(parents=True)
    (agent_dir / "rule.md").write_text("Custom agent instructions\n")
    manifest = {"agent": "custom", "files": [{"src": "rule.md", "dest": "RULE.md"}]}
    if shared_reference:
        manifest["ci_catalog"] = "builtin:legacy-ci-v1"
    (agent_dir / "manifest.json").write_text(json.dumps(manifest))
    monkeypatch.setattr(paths, "AGENTS_DIR", agent_dir.parent)
    target = tmp_path / "target"
    target.mkdir()
    (target / "existing.txt").write_text("Keep this file\n")
    monkeypatch.setattr(
        sys, "argv", ["govkit", "apply", "--agent", "custom", "--target", str(target)]
    )
    if shared_reference:
        with pytest.raises(SystemExit) as error:
            main()
        assert error.value.code == 1
        assert "variant" in capsys.readouterr().out
        assert sorted(p.name for p in target.iterdir()) == ["existing.txt"]
    else:
        main()
        assert "Custom agent instructions" in (target / "RULE.md").read_text()
    assert (target / "existing.txt").read_text() == "Keep this file\n"
