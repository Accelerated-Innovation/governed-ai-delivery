"""Tests for the bundled provider-neutral LLM Application extension."""

import argparse
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from cli.cmd_apply import cmd_apply
from cli.cmd_extension import cmd_extension_add
from cli.extensions import discover_extensions, validate_extension

REPO_ROOT = Path(__file__).resolve().parent.parent
EXT_DIR = REPO_ROOT / "extensions" / "llm-application"
MANIFEST_PATH = EXT_DIR / "manifest.yaml"
SCHEMA_PATH = (
    REPO_ROOT
    / "extensions"
    / "agentic-skills"
    / "schemas"
    / "extension-manifest.schema.json"
)

REQUIRED_CONTRACT_SETS = {
    "llm_gateway",
    "llm_evaluation",
    "llm_observability",
    "model_guardrails",
}

REQUIRED_CONTRACTS = {
    "docs/backend/architecture/LLM_GATEWAY_CONTRACT.md",
    "docs/backend/architecture/LLM_EVALUATION_CONTRACT.md",
    "docs/backend/architecture/LLM_OBSERVABILITY_CONTRACT.md",
    "docs/backend/architecture/MODEL_GUARDRAILS_CONTRACT.md",
}

REMOVED_CORE_CONTRACTS = {
    "AGENT_ARCHITECTURE.md",
    "LLM_GATEWAY_CONTRACT.md",
    "EVALUATION_LLM_CONTRACT.md",
    "OBSERVABILITY_LLM_CONTRACT.md",
    "GUARDRAILS_CONTRACT.md",
}


def _manifest() -> dict:
    yaml = pytest.importorskip("yaml")
    return yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))


def _declared_paths() -> list[str]:
    return [
        path
        for contract_set in _manifest()["contract_sets"]
        for path in contract_set.get("paths", [])
    ]


def test_extension_is_discovered_and_validates_cleanly():
    extension = next(
        (item for item in discover_extensions(REPO_ROOT) if item.id == "llm-application"),
        None,
    )
    assert extension is not None
    assert validate_extension(extension, REPO_ROOT) == []


def test_manifest_matches_extension_schema():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(_manifest())) == []


def test_manifest_targets_level_5_backend_shapes():
    manifest = _manifest()
    assert manifest["supported_levels"] == [5]
    assert set(manifest["supported_project_types"]) == {"api", "cli"}


def test_manifest_declares_four_progressive_contract_sets():
    ids = {contract_set["id"] for contract_set in _manifest()["contract_sets"]}
    assert ids == REQUIRED_CONTRACT_SETS


def test_every_required_contract_is_declared_once_and_exists():
    paths = _declared_paths()
    assert set(paths) == REQUIRED_CONTRACTS
    assert len(paths) == len(set(paths))
    for path in paths:
        assert (EXT_DIR / path).is_file(), f"missing declared contract: {path}"


def test_all_relationship_paths_exist():
    for contract_set in _manifest()["contract_sets"]:
        relationships = contract_set.get("relates_to", {})
        for kind in ("extends", "supersedes"):
            for path in relationships.get(kind, []):
                assert (REPO_ROOT / path).is_file(), (
                    f"{contract_set['id']} declares missing {kind} path: {path}"
                )


def test_contracts_are_provider_framework_and_product_neutral():
    prohibited_names = {
        "langgraph",
        "langchain",
        "litellm",
        "langfuse",
        "openllmetry",
        "deepeval",
        "promptfoo",
        "ragas",
        "nemo guardrails",
        "guardrails ai",
        "openai",
        "anthropic",
    }
    for path in REQUIRED_CONTRACTS:
        text = (EXT_DIR / path).read_text(encoding="utf-8").casefold()
        found = sorted(name for name in prohibited_names if name in text)
        assert found == [], f"{path} contains product-specific architecture: {found}"


def test_contracts_preserve_required_control_boundaries():
    gateway = (EXT_DIR / "docs/backend/architecture/LLM_GATEWAY_CONTRACT.md").read_text(
        encoding="utf-8"
    )
    evaluation = (
        EXT_DIR / "docs/backend/architecture/LLM_EVALUATION_CONTRACT.md"
    ).read_text(encoding="utf-8")
    observability = (
        EXT_DIR / "docs/backend/architecture/LLM_OBSERVABILITY_CONTRACT.md"
    ).read_text(encoding="utf-8")
    guardrails = (
        EXT_DIR / "docs/backend/architecture/MODEL_GUARDRAILS_CONTRACT.md"
    ).read_text(encoding="utf-8")

    assert "Model tool calls are proposals" in gateway
    assert "logical capability or model alias" in gateway
    assert "invalid, unavailable, or ambiguous judge output MUST be inconclusive" in evaluation
    assert "Raw prompt, response" in observability
    assert "A model-generated tool call is untrusted proposed data" in guardrails
    assert "MUST NOT substitute for authorization" in guardrails


def test_extension_owned_contracts_are_absent_from_core():
    core = REPO_ROOT / "docs" / "backend" / "architecture"
    for filename in REMOVED_CORE_CONTRACTS:
        assert not (core / filename).exists(), f"extension-owned core duplicate remains: {filename}"


def test_bundled_extension_add_copies_profile(tmp_path, capsys):
    args = type(
        "Args",
        (),
        {
            "extension_id": "llm-application",
            "target": str(tmp_path),
            "force": False,
        },
    )()
    cmd_extension_add(args)
    capsys.readouterr()

    installed = tmp_path / "extensions" / "llm-application"
    assert (installed / "manifest.yaml").is_file()
    for path in REQUIRED_CONTRACTS:
        assert (installed / path).is_file()


def test_extension_add_validates_cleanly_in_level_5_project(tmp_path, capsys):
    target = tmp_path / "project"
    target.mkdir()
    cmd_apply(
        argparse.Namespace(
            agent="claude-code",
            target=str(target),
            level="5",
            type="api",
            ci="github",
            stack="python-fastapi",
            force=False,
            detect=False,
        )
    )
    cmd_extension_add(
        argparse.Namespace(
            extension_id="llm-application",
            target=str(target),
            force=False,
        )
    )
    output = capsys.readouterr().out
    assert "Validation notes" not in output
