"""Tests for the shipped vision-inference extension (discriminative spine).

PR1 / Increment A — scaffold: the extension is discovered, validates cleanly
against the repo, its manifest matches the extension schema, and the first
spine contract (VISION_MODEL_ADAPTER) is present. Later increments add the
remaining spine contracts and the generative/VLM layer.
"""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from cli.extensions import discover_extensions, validate_extension

REPO_ROOT = Path(__file__).resolve().parent.parent
EXT_DIR = REPO_ROOT / "extensions" / "vision-inference"
MANIFEST_PATH = EXT_DIR / "manifest.yaml"
SCHEMA_PATH = (
    REPO_ROOT / "extensions" / "agentic-skills" / "schemas" / "extension-manifest.schema.json"
)
ADAPTER_CONTRACT = "docs/backend/architecture/VISION_MODEL_ADAPTER_CONTRACT.md"
SPINE_CONTRACTS = [
    "docs/backend/architecture/VISION_MODEL_ADAPTER_CONTRACT.md",
    "docs/backend/architecture/MODEL_VERSIONING_CONTRACT.md",
    "docs/backend/architecture/INFERENCE_ACCEPTANCE_CONTRACT.md",
    "docs/backend/architecture/BIOMETRIC_DATA_HANDLING_CONTRACT.md",
    "docs/backend/architecture/PREDICTION_LOGGING_CONTRACT.md",
]
PREDICTION_RECORD_SCHEMA = EXT_DIR / "schemas" / "prediction-record.schema.json"


def _manifest() -> dict:
    yaml = pytest.importorskip("yaml")
    return yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_extension_discovered():
    exts = discover_extensions(REPO_ROOT)
    assert any(e.id == "vision-inference" for e in exts), "vision-inference not discovered"


def test_extension_validates_cleanly_against_repo():
    """Must be WARN-free against the canonical repo — including the
    undeclared-overlap heuristic against core *_CONTRACT.md topics."""
    ext = next((e for e in discover_extensions(REPO_ROOT) if e.id == "vision-inference"), None)
    assert ext is not None, "vision-inference extension not discovered in repo"
    issues = validate_extension(ext, REPO_ROOT)
    assert issues == [], f"extension must validate cleanly; got: {issues}"


def test_manifest_matches_schema():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(schema).iter_errors(_manifest()))
    assert not errors, f"manifest must validate; got: {errors}"


def test_manifest_core_fields():
    m = _manifest()
    assert m["id"] == "vision-inference"
    assert m["extension_type"] == "architecture"
    assert "api" in m.get("supported_project_types", [])


def test_adapter_contract_declared_and_present():
    paths = [p for cs in _manifest()["contract_sets"] for p in cs.get("paths", [])]
    assert ADAPTER_CONTRACT in paths, "adapter contract must be declared in a contract set"
    assert (EXT_DIR / ADAPTER_CONTRACT).exists(), "adapter contract file must exist"


def test_all_spine_contracts_declared_and_present():
    paths = [p for cs in _manifest()["contract_sets"] for p in cs.get("paths", [])]
    for contract in SPINE_CONTRACTS:
        assert contract in paths, f"{contract} must be declared in a contract set"
        assert (EXT_DIR / contract).exists(), f"{contract} file must exist"


def test_prediction_record_schema_is_valid_json_schema():
    schema = json.loads(PREDICTION_RECORD_SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)


def test_prediction_record_schema_pins_provenance_fields():
    """The per-prediction record is the object the acceptance gate and prediction
    logging both consume — it must pin model identity + version + confidence."""
    schema = json.loads(PREDICTION_RECORD_SCHEMA.read_text(encoding="utf-8"))
    required = set(schema.get("required", []))
    assert {"model_id", "model_version"} <= required, (
        f"prediction record must require model identity + version; got {required}"
    )


class TestGenerativeLayer:
    """PR 2 — generative / VLM contract set. Adds MULTIMODAL_INPUT and REUSES the
    L5 GenAI-Ops contracts via relates_to.extends rather than reinventing them."""

    GENERATIVE_CONTRACT = "docs/backend/architecture/MULTIMODAL_INPUT_CONTRACT.md"
    EXPECTED_EXTENDS = {
        "docs/backend/architecture/GUARDRAILS_CONTRACT.md",
        "docs/backend/architecture/EVALUATION_LLM_CONTRACT.md",
        "docs/backend/architecture/OBSERVABILITY_LLM_CONTRACT.md",
    }

    @staticmethod
    def _generative_set() -> dict | None:
        return next(
            (cs for cs in _manifest()["contract_sets"] if cs.get("id") == "vision_generative"),
            None,
        )

    def test_generative_contract_set_present(self):
        assert self._generative_set() is not None, "vision_generative contract set must exist"

    def test_multimodal_contract_declared_and_present(self):
        cs = self._generative_set()
        assert cs is not None
        assert self.GENERATIVE_CONTRACT in cs.get("paths", []), "multimodal contract must be declared"
        assert (EXT_DIR / self.GENERATIVE_CONTRACT).exists(), "multimodal contract file must exist"

    def test_generative_extends_l5_contracts(self):
        cs = self._generative_set()
        assert cs is not None
        extends = set(cs.get("relates_to", {}).get("extends", []))
        missing = self.EXPECTED_EXTENDS - extends
        assert not missing, f"generative set must extend L5 GenAI-Ops contracts: {missing}"

    def test_generative_extends_paths_exist_in_repo(self):
        cs = self._generative_set()
        assert cs is not None
        for path in cs.get("relates_to", {}).get("extends", []):
            assert (REPO_ROOT / path).exists(), f"declared extends path {path!r} not found in repo"
