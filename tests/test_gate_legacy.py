"""One shared legacy CI selection preserves custom manifests and ordering."""

import json
from copy import deepcopy

import pytest

from cli import paths
from cli.gate_legacy import expand_legacy_ci
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
