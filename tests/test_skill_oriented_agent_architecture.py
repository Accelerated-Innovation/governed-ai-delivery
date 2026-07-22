"""Tests for the bundled Skill-Oriented Agent Architecture extension."""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from cli.cmd_extension import cmd_extension_add
from cli.extensions import discover_extensions, validate_extension

REPO_ROOT = Path(__file__).resolve().parent.parent
EXT_DIR = REPO_ROOT / "extensions" / "skill-oriented-agent-architecture"
MANIFEST_PATH = EXT_DIR / "manifest.yaml"
SCHEMA_PATH = REPO_ROOT / "governance" / "schemas" / "extension-manifest.schema.json"

REQUIRED_CONTRACT_SETS = {
    "soaa_core",
    "soaa_selection_authority",
    "soaa_context_resilience",
    "soaa_assurance",
    "soaa_ecosystem",
}

REQUIRED_CONTRACTS = {
    "docs/backend/architecture/SKILL_ORIENTED_AGENT_ARCHITECTURE.md",
    "docs/backend/architecture/SKILL_CONTRACT.md",
    "docs/backend/architecture/RUNTIME_STATE_AND_EXECUTION_CONTRACT.md",
    "docs/backend/architecture/SKILL_SELECTION_AND_ACTIVATION_CONTRACT.md",
    "docs/backend/architecture/AUTHORITY_AND_APPROVAL_CONTRACT.md",
    "docs/backend/architecture/CONTEXT_MEMORY_AND_RESOURCE_CONTRACT.md",
    "docs/backend/architecture/RESILIENCE_AND_RECOVERY_CONTRACT.md",
    "docs/backend/architecture/EVALUATION_EVIDENCE_AND_COMPLETION_CONTRACT.md",
    "docs/backend/architecture/SKILL_LIFECYCLE_AND_INTEROPERABILITY_CONTRACT.md",
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


def test_extension_is_discovered():
    extensions = discover_extensions(REPO_ROOT)
    assert any(
        extension.id == "skill-oriented-agent-architecture"
        for extension in extensions
    )


def test_extension_validates_cleanly_against_repo():
    extension = next(
        (
            item
            for item in discover_extensions(REPO_ROOT)
            if item.id == "skill-oriented-agent-architecture"
        ),
        None,
    )
    assert extension is not None
    assert validate_extension(extension, REPO_ROOT) == []


def test_manifest_matches_extension_schema():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(schema).iter_errors(_manifest()))
    assert errors == []


def test_manifest_targets_level_5_backend_shapes():
    manifest = _manifest()
    assert manifest["supported_levels"] == [5]
    assert set(manifest["supported_project_types"]) == {"api", "cli"}


def test_manifest_declares_all_soaa_contract_sets():
    ids = {contract_set["id"] for contract_set in _manifest()["contract_sets"]}
    assert ids == REQUIRED_CONTRACT_SETS


def test_every_required_contract_is_declared_once_and_exists():
    paths = _declared_paths()
    assert set(paths) == REQUIRED_CONTRACTS
    assert len(paths) == len(set(paths))
    for path in paths:
        assert (EXT_DIR / path).is_file(), f"missing declared contract: {path}"


def test_core_profile_has_no_removed_core_supersession():
    core = next(
        item for item in _manifest()["contract_sets"] if item["id"] == "soaa_core"
    )
    assert core["relates_to"]["supersedes"] == []
    assert not (
        REPO_ROOT / "docs" / "backend" / "architecture" / "AGENT_ARCHITECTURE.md"
    ).exists()


def test_all_core_relationship_paths_exist():
    for contract_set in _manifest()["contract_sets"]:
        relationships = contract_set.get("relates_to", {})
        for kind in ("extends", "supersedes"):
            for path in relationships.get(kind, []):
                assert (REPO_ROOT / path).is_file(), (
                    f"{contract_set['id']} declares missing {kind} path: {path}"
                )


def test_architecture_contract_preserves_control_boundary():
    text = (
        EXT_DIR
        / "docs"
        / "backend"
        / "architecture"
        / "SKILL_ORIENTED_AGENT_ARCHITECTURE.md"
    ).read_text(encoding="utf-8")
    required_phrases = [
        "exactly one runtime owner",
        "Model output is a proposal",
        "Fresh authorization before each external operation",
        "Skill versus application code",
        "Eighteen",
    ]
    for phrase in required_phrases:
        assert phrase.casefold() in text.casefold()


def test_selection_contract_preserves_four_stage_pipeline_and_null_option():
    text = (
        EXT_DIR
        / "docs"
        / "backend"
        / "architecture"
        / "SKILL_SELECTION_AND_ACTIVATION_CONTRACT.md"
    ).read_text(encoding="utf-8")
    for phrase in (
        "Candidate retrieval",
        "Deterministic admission",
        "Agent ranking",
        "Atomic activation",
        "Null selection is always present",
    ):
        assert phrase in text


def test_completion_contract_rejects_self_asserted_success():
    text = (
        EXT_DIR
        / "docs"
        / "backend"
        / "architecture"
        / "EVALUATION_EVIDENCE_AND_COMPLETION_CONTRACT.md"
    ).read_text(encoding="utf-8")
    folded = text.casefold()
    assert "agent confidence" in folded
    assert "skill success" in folded
    assert "verifying" in folded
    assert "task controller transition" in folded


def test_agent_skills_profile_defines_standard_compatibility_boundary():
    contract = (
        EXT_DIR
        / "docs"
        / "backend"
        / "architecture"
        / "SKILL_CONTRACT.md"
    ).read_text(encoding="utf-8")
    lifecycle = (
        EXT_DIR
        / "docs"
        / "backend"
        / "architecture"
        / "SKILL_LIFECYCLE_AND_INTEROPERABILITY_CONTRACT.md"
    ).read_text(encoding="utf-8")

    for phrase in (
        "SOAA profile for Agent Skills packages",
        "string keys mapped to string values",
        "soaa-profile",
        "soaa-manifest",
        "soaa-manifest-digest",
        "soaa-release-id",
        "Generic-client behavior",
        "must not claim SOAA package-profile or runtime conformance",
        "skills-ref validate <skill-root>",
        "Two-stage validation",
        "intersect runtime_policy",
        "intersect task_authority",
        "intersect approval_scope",
    ):
        assert phrase in contract

    for phrase in (
        "Flat string metadata keys",
        "may ignore `soaa/`",
        "must not claim SOAA conformance",
        "intersection of that ceiling, runtime policy, task authority, and approval scope",
    ):
        assert phrase in lifecycle


def test_contracts_are_provider_and_framework_neutral():
    prohibited_product_names = {
        "langgraph",
        "langchain",
        "litellm",
        "langfuse",
        "deepeval",
        "promptfoo",
        "ragas",
        "nemo guardrails",
        "guardrails ai",
    }
    for path in REQUIRED_CONTRACTS:
        text = (EXT_DIR / path).read_text(encoding="utf-8").casefold()
        found = sorted(name for name in prohibited_product_names if name in text)
        assert found == [], f"{path} contains product-specific architecture: {found}"


def test_bundled_extension_add_copies_profile(tmp_path, capsys):
    args = type(
        "Args",
        (),
        {
            "extension_id": "skill-oriented-agent-architecture",
            "target": str(tmp_path),
            "force": False,
        },
    )()
    cmd_extension_add(args)
    capsys.readouterr()

    installed = tmp_path / "extensions" / "skill-oriented-agent-architecture"
    assert (installed / "manifest.yaml").is_file()
    for path in REQUIRED_CONTRACTS:
        assert (installed / path).is_file()


# ---------------------------------------------------------------------------
# AGENT_RUNTIME_STACK implementation profile — product-naming default bindings
# for the SOAA runtime. Advisory; RUNTIME_STATE_AND_EXECUTION_CONTRACT stays
# authoritative. Names concrete products (LangGraph, …) that teams may swap
# via ADR, so it lives under implementation_profiles, NOT contract_sets.
# ---------------------------------------------------------------------------

RUNTIME_PROFILE_PATH = "docs/backend/architecture/AGENT_RUNTIME_STACK.md"


def test_manifest_declares_agent_runtime_profile():
    profiles = _manifest().get("implementation_profiles", [])
    profile = next((p for p in profiles if p["id"] == "agent_runtime_profile"), None)
    assert profile is not None, "agent_runtime_profile not declared"
    assert profile["path"] == RUNTIME_PROFILE_PATH
    assert profile["authority"] == "defaults"
    assert profile["product_selection_requires_adr"] is True
    assert "soaa_core" in profile["profiles_for"]


def test_agent_runtime_profile_file_exists():
    assert (EXT_DIR / RUNTIME_PROFILE_PATH).is_file()


def test_agent_runtime_profile_is_not_a_neutral_contract():
    """The profile names products, so it must stay out of contract_sets (the
    neutral surface) and out of the product-neutrality assertion set."""
    assert RUNTIME_PROFILE_PATH not in _declared_paths()
    assert RUNTIME_PROFILE_PATH not in REQUIRED_CONTRACTS


def test_agent_runtime_profile_names_a_default_runtime_product():
    text = (EXT_DIR / RUNTIME_PROFILE_PATH).read_text(encoding="utf-8").casefold()
    assert "langgraph" in text, "profile should name a concrete default runtime"


def test_agent_runtime_profile_defers_to_the_authoritative_contract():
    text = (EXT_DIR / RUNTIME_PROFILE_PATH).read_text(encoding="utf-8")
    folded = text.casefold()
    # It supplies defaults, not law: the runtime contract wins on conflict.
    assert "RUNTIME_STATE_AND_EXECUTION_CONTRACT" in text
    assert "advisory" in folded or "authoritative" in folded
    # No blocking CI conformance gate ships this round.
    assert "adr" in folded


def test_bundled_extension_add_copies_agent_runtime_profile(tmp_path, capsys):
    args = type(
        "Args",
        (),
        {
            "extension_id": "skill-oriented-agent-architecture",
            "target": str(tmp_path),
            "force": False,
        },
    )()
    cmd_extension_add(args)
    capsys.readouterr()
    installed = tmp_path / "extensions" / "skill-oriented-agent-architecture"
    assert (installed / RUNTIME_PROFILE_PATH).is_file()
