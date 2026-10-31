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


# ---------------------------------------------------------------------------
# SOAA 0.2.0 (Phase A Increment 9): proportional applicability, an explicit
# capability_pack, advisory docs, a local case catalog and bounded source
# discrepancies. Identities, tokens and contract paths stay unchanged.
# ---------------------------------------------------------------------------

ARCH = "docs/backend/architecture"
APPLICABILITY_DOC = f"{ARCH}/SOAA_APPLICABILITY.md"
EXPERIMENTS_DOC = f"{ARCH}/SOAA_EXPERIMENTS.md"
TEMPLATE = "templates/preflight-soaa.md"
CATALOG = "catalog/gk-soaa-cases.yaml"
NEW_FILES = (APPLICABILITY_DOC, EXPERIMENTS_DOC, TEMPLATE, CATALOG)
EXPECTED_KINDS = {
    **{path: "contract" for path in REQUIRED_CONTRACTS},
    RUNTIME_PROFILE_PATH: "defaults",
    "README.md": "advisory",
    APPLICABILITY_DOC: "advisory",
    EXPERIMENTS_DOC: "advisory",
    TEMPLATE: "example",
    CATALOG: "reference",
}
CONDITIONS = {
    "adaptive-run",
    "skill-activation",
    "untrusted-input",
    "external-read",
    "external-mutation",
    "multi-tenant-data",
    "model-selection",
    "workflow-switching",
    "persistent-memory",
    "human-takeover",
    "delegation",
    "executable-assets",
}
PRODUCT_NAMES = {
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


def _text(relative: str) -> str:
    return (EXT_DIR / relative).read_text(encoding="utf-8")


def _yaml(text: str):
    return pytest.importorskip("yaml").safe_load(text)


def _fenced_block(text: str, key: str) -> dict:
    """The one fenced YAML block whose top-level key is `key`."""
    import re

    blocks = [
        _yaml(body)
        for body in re.findall(r"```yaml\n(.*?)```", text, re.DOTALL)
        if body.startswith(f"{key}:")
    ]
    assert len(blocks) == 1, f"expected one {key} block, found {len(blocks)}"
    return blocks[0][key]


def catalog_errors(catalog: dict) -> list[str]:
    """Structural errors in a GK-SOAA case catalog (empty when well formed)."""
    errors = []
    known = [c["id"] for c in catalog.get("conditions", [])]
    if len(known) != len(set(known)):
        errors.append("duplicate condition id")
    cases = catalog.get("cases", []) + catalog.get("conditional_cases", [])
    ids = [case["id"] for case in cases]
    if len(ids) != len(set(ids)):
        errors.append("duplicate case id")
    for case in cases:
        if not case.get("applies_when"):
            errors.append(f"{case['id']}: no applies_when")
        errors.extend(
            f"{case['id']}: unknown condition {cid}"
            for cid in case.get("applies_when", [])
            if cid not in known
        )
        for field in ("trigger", "observation"):
            if not str(case.get(field, "")).strip():
                errors.append(f"{case['id']}: missing {field}")
    return errors


def test_manifest_is_version_0_2_0():
    assert _manifest()["version"] == "0.2.0"


def test_capability_pack_provides_the_pack_id_and_every_contract_token():
    manifest = _manifest()
    tokens = [
        token
        for contract_set in manifest["contract_sets"]
        for token in contract_set["capabilities"]
    ]
    assert len(tokens) == 32
    assert manifest["capability_pack"]["provides"] == [manifest["id"], *tokens]


def test_capability_pack_resources_declare_every_shipped_file_with_its_kind():
    block = _manifest()["capability_pack"]
    declared = {r["path"]: r["kind"] for r in block["resources"]}
    assert declared == EXPECTED_KINDS
    assert sorted(block["agents"]) == ["claude-code", "codex", "copilot"]
    assert "checks" not in block  # Increment 10 adds the applicability check


def test_load_pack_includes_readme_and_new_resources_with_declared_kinds():
    from cli.pack_loading import load_pack

    snapshot = load_pack(EXT_DIR, source_kind="bundled")
    kinds = {f.path: f.kind for f in snapshot.files}
    assert kinds.pop("manifest.yaml") == "manifest"
    assert kinds == EXPECTED_KINDS
    assert snapshot.version == "0.2.0"
    assert set(snapshot.provides) == set(_manifest()["capability_pack"]["provides"])


def test_template_is_declared_in_manifest_templates():
    assert {"id": "preflight_soaa", "path": TEMPLATE} in _manifest()["templates"]


def test_new_files_exist_and_are_not_contract_sets():
    for path in NEW_FILES:
        assert (EXT_DIR / path).is_file(), path
        assert path not in _declared_paths()


def test_catalog_has_sixteen_base_cases_and_known_conditions():
    catalog = _yaml(_text(CATALOG))
    assert catalog_errors(catalog) == []
    assert [c["id"] for c in catalog["cases"]] == [f"GK-SOAA-{n:02d}" for n in range(1, 17)]
    assert {c["id"] for c in catalog["conditions"]} == CONDITIONS
    assert catalog["conditional_cases"], "conditional cases missing"
    assert "not normative" in catalog["status"].casefold()


def test_catalog_validation_rejects_unknown_and_duplicate_ids():
    catalog = _yaml(_text(CATALOG))
    broken = {**catalog, "cases": [*catalog["cases"]]}
    broken["cases"][0] = {**broken["cases"][0], "applies_when": ["no-such-condition"]}
    assert any("unknown condition" in e for e in catalog_errors(broken))
    duplicated = {**catalog, "cases": [*catalog["cases"], catalog["cases"][0]]}
    assert "duplicate case id" in catalog_errors(duplicated)


def test_applicability_doc_matrix_matches_catalog_conditions():
    import re

    text = _text(APPLICABILITY_DOC)
    rows = set(re.findall(r"^\| `([a-z-]+)` \|", text, re.MULTILINE))
    assert rows == CONDITIONS
    folded = text.casefold()
    for phrase in (
        "unknown applicability stays unresolved",
        "verified absent or disabled interface",
        "owner",
        "change trigger",
        "system level",
        "per-feature",
    ):
        assert phrase in folded, phrase


def test_preflight_template_block_covers_every_condition():
    block = _fenced_block(_text(TEMPLATE), "soaa_applicability")
    assert block["version"] == 1
    assert {c["id"] for c in block["conditions"]} == CONDITIONS
    for condition in block["conditions"]:
        assert condition["status"] == "unknown"
        assert {"reason", "evidence", "owner", "change_trigger"} <= set(condition)
    assert "Writer map" in _text(TEMPLATE)


def test_readme_starts_with_the_single_agent_path_and_three_layers():
    text = _text("README.md")
    assert "## Start here: one agent with fixed skills" in text
    assert text.index("## Start here") < text.index("## Contract loading")
    folded = text.casefold()
    assert "`multi_agent: true` is only for topology" in text
    for phrase in (
        "experiment-required",
        "report validation",
        "observed execution",
        "formal soaa conformance",
        ".govkit/packs/skill-oriented-agent-architecture/<digest>/",
        "govkit pack",
    ):
        assert phrase in folded, phrase


def test_experiments_doc_defines_e1_to_e5_and_maps_to_experiment_records():
    text = _text(EXPERIMENTS_DOC)
    for experiment in ("E1", "E1b", "E2", "E3", "E4", "E5"):
        assert f"| {experiment} " in text, experiment
    folded = text.casefold()
    for phrase in ("stopping conditions", "experiments.yaml", "illustrative", "unverified"):
        assert phrase in folded, phrase


def test_no_rung_or_ladder_vocabulary_in_the_extension():
    import re

    for path in sorted(EXT_DIR.rglob("*")):
        if path.is_file():
            folded = path.read_text(encoding="utf-8").casefold()
            assert "agent_skills_rung" not in folded, path
            assert not re.search(r"\brungs?\b", folded), path
            assert "maturity ladder" not in folded, path


def test_new_docs_are_provider_and_framework_neutral():
    for path in NEW_FILES:
        folded = _text(path).casefold()
        found = sorted(name for name in PRODUCT_NAMES if name in folded)
        assert found == [], f"{path} names products: {found}"


def test_authority_contract_subtracts_prohibited_access_explicitly():
    text = _text(f"{ARCH}/AUTHORITY_AND_APPROVAL_CONTRACT.md")
    assert "MINUS ProhibitedAccess(skill)" in text
    assert "Overlap example" in text
    assert "MINUS ExplicitDenies" in text  # existing term is kept


def test_core_contract_maps_roles_at_system_level_and_records_applicability():
    text = _text(f"{ARCH}/SKILL_ORIENTED_AGENT_ARCHITECTURE.md")
    assert "all eighteen soaa logical roles" in text.casefold()
    assert "once at system level" in text
    assert "changed rows" in text
    assert "SOAA applicability decision" in text
    assert "omission needs evidence" in text.casefold()


def test_binding_modes_distinguish_fixed_binding_from_fixed_menu_selection():
    text = _text(f"{ARCH}/SKILL_SELECTION_AND_ACTIVATION_CONTRACT.md")
    section = text[text.index("## Binding modes") : text.index("## Conflict and composition")]
    assert "Fixed binding" in section and "revocation" in section
    assert "Fixed menu" in section and "null selection" in section


def test_skill_contract_records_metadata_discrepancy_without_renaming_keys():
    text = _text(f"{ARCH}/SKILL_CONTRACT.md")
    assert "soaa-profile" in text  # keys are not renamed
    assert "urn:soaa:agent-skills:1" in text
    assert "blocked pending source" in text


def test_instruction_precedence_discrepancy_is_recorded():
    text = _text(f"{ARCH}/AUTHORITY_AND_APPROVAL_CONTRACT.md")
    section = text[text.index("## Instruction precedence") : text.index("## Tool and side-effect")]
    assert "Appendix G" in section and "no enforcement change" in section


def test_every_contract_source_alignment_lists_open_discrepancies():
    for path in sorted(REQUIRED_CONTRACTS - {f"{ARCH}/SKILL_ORIENTED_AGENT_ARCHITECTURE.md"}):
        text = _text(path)
        alignment = text[text.index("## Source alignment") : text.index("## Purpose")]
        assert "| Open discrepancies |" in alignment, path
    core = _text(f"{ARCH}/SKILL_ORIENTED_AGENT_ARCHITECTURE.md")
    assert "| Open discrepancies |" in core[: core.index("## Purpose")]


def test_agent_guidance_covers_applicability_experiments_and_layers():
    guidance = " ".join(_manifest()["agent_guidance"]["architecture_preflight"])
    for phrase in (
        "templates/preflight-soaa.md",
        "experiment-required",
        "multi_agent: true",
        "one agent with fixed skills",
        "applies_to",
    ):
        assert phrase in guidance, phrase


def test_minimum_govkit_version_resolves_in_the_editable_install():
    from packaging.version import Version

    from cli import version

    minimum = Version(_manifest()["govkit_min_version"])
    assert minimum >= Version("0.21.1")  # first release with explicit capability_pack blocks
    assert Version(version.GOVKIT_VERSION) >= minimum
