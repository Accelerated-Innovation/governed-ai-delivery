"""
Schema validation for agents/*/manifest.json files.

Originally added in Increment 1 of the L3/L4 maturity-model swap (plan §6.3).

These tests catch manifest/schema drift that previously slipped through:
the v0.6.x schema set additionalProperties: false on variant_config but
omitted the `governed` key, while every live manifest used `governed`.

The v0.7.0 schema:
  - Adds `governed` to variant_config and level_override (fixes the drift).
  - Replaces the transitional `level_3` property with `level_4`.
  - Adds an optional `mode` field on level_override ("merge" | "replace").

The transitional `level_3` key was removed in Increment 11; the schema now
rejects manifests that use it (locked in by test_schema_rejects_level_3).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

jsonschema = pytest.importorskip("jsonschema")
from jsonschema import Draft202012Validator  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "governance" / "schemas" / "agent-manifest.schema.json"
AGENTS_DIR = REPO_ROOT / "agents"


def _load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _load_manifest(agent: str) -> dict:
    return json.loads((AGENTS_DIR / agent / "manifest.json").read_text(encoding="utf-8"))


def _all_agents() -> list[str]:
    return sorted(
        d.name for d in AGENTS_DIR.iterdir()
        if d.is_dir() and (d / "manifest.json").exists()
    )


# ---------------------------------------------------------------------------
# Schema is itself a valid JSON Schema
# ---------------------------------------------------------------------------


def test_schema_is_a_valid_json_schema():
    """The manifest schema must itself conform to the meta-schema."""
    schema = _load_schema()
    Draft202012Validator.check_schema(schema)


# ---------------------------------------------------------------------------
# Every live agent manifest validates against the schema
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("agent", _all_agents())
def test_live_manifest_validates(agent: str):
    """Every agents/<agent>/manifest.json must validate against the v0.7.0 schema."""
    schema = _load_schema()
    manifest = _load_manifest(agent)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(manifest), key=lambda e: e.path)
    assert not errors, (
        f"{agent}/manifest.json failed schema validation:\n"
        + "\n".join(f"  - at {list(e.absolute_path)}: {e.message}" for e in errors)
    )


# ---------------------------------------------------------------------------
# Structural assertions on the schema itself
# ---------------------------------------------------------------------------


class TestSchemaShape:
    """Lock in the v0.7.0 schema surface so accidental edits are caught."""

    def test_variant_config_allows_governed(self):
        schema = _load_schema()
        props = schema["$defs"]["variant_config"]["properties"]
        assert "governed" in props, (
            "variant_config must allow `governed` (was missing in v0.6.x — schema/manifest drift bug)"
        )

    def test_level_override_allows_governed(self):
        schema = _load_schema()
        props = schema["$defs"]["level_override"]["properties"]
        assert "governed" in props, "level_override must allow `governed`"

    def test_variant_config_has_level_4(self):
        schema = _load_schema()
        props = schema["$defs"]["variant_config"]["properties"]
        assert "level_4" in props, "v0.7.0 schema must define level_4 for the Spec-Driven Add-On"

    def test_schema_no_longer_allows_level_3(self):
        # Increment 11 cleanup: the transitional level_3 key is gone.
        schema = _load_schema()
        props = schema["$defs"]["variant_config"]["properties"]
        assert "level_3" not in props, (
            "level_3 must be removed from the schema in v0.7.0+ "
            "(L3 is now the default top-level base; no override key is used)"
        )

    def test_variant_config_has_level_5(self):
        schema = _load_schema()
        props = schema["$defs"]["variant_config"]["properties"]
        assert "level_5" in props

    def test_level_override_has_optional_mode(self):
        schema = _load_schema()
        props = schema["$defs"]["level_override"]["properties"]
        assert "mode" in props, "level_override must accept an optional `mode` field"
        required = schema["$defs"]["level_override"].get("required", [])
        assert "mode" not in required, "`mode` must be optional"
        assert set(props["mode"]["enum"]) == {"merge", "replace"}


# ---------------------------------------------------------------------------
# Negative tests — schema rejects what it should reject
# ---------------------------------------------------------------------------


class TestSchemaRejects:
    """Confirm the schema still enforces guardrails after the v0.7.0 changes."""

    def test_rejects_unknown_top_level_key(self):
        schema = _load_schema()
        manifest = {
            "agent": "x",
            "description": "y",
            "variants": {},
            "rogue_top_level": True,  # additionalProperties: false should reject this
        }
        validator = Draft202012Validator(schema)
        errors = list(validator.iter_errors(manifest))
        assert errors, "Unknown top-level keys must be rejected"

    def test_rejects_unknown_variant_config_key(self):
        schema = _load_schema()
        manifest = {
            "agent": "x",
            "description": "y",
            "variants": {
                "type": {
                    "api": {
                        "files": [],
                        "rogue_field": True,  # not allowed
                    }
                }
            },
        }
        validator = Draft202012Validator(schema)
        errors = list(validator.iter_errors(manifest))
        assert errors, "Unknown variant_config keys must be rejected"

    def test_rejects_invalid_mode_value(self):
        schema = _load_schema()
        manifest = {
            "agent": "x",
            "description": "y",
            "variants": {
                "type": {
                    "api": {
                        "level_4": {"mode": "additive"}  # only "merge" or "replace" allowed
                    }
                }
            },
        }
        validator = Draft202012Validator(schema)
        errors = list(validator.iter_errors(manifest))
        assert errors, "Invalid `mode` enum values must be rejected"

    def test_rejects_file_entry_missing_dest(self):
        schema = _load_schema()
        manifest = {
            "agent": "x",
            "description": "y",
            "variants": {
                "type": {
                    "api": {
                        "files": [{"src": "only-src.md"}]  # missing dest
                    }
                }
            },
        }
        validator = Draft202012Validator(schema)
        errors = list(validator.iter_errors(manifest))
        assert errors, "file_entry must require both src and dest"

    def test_rejects_level_3_property(self):
        # Increment 11 cleanup: a manifest carrying a legacy `level_3` block
        # must fail schema validation under v0.7.0.
        schema = _load_schema()
        manifest = {
            "agent": "x",
            "description": "y",
            "variants": {
                "type": {
                    "api": {
                        "level_3": {"files": []}  # legacy v0.6 key — no longer allowed
                    }
                }
            },
        }
        validator = Draft202012Validator(schema)
        errors = list(validator.iter_errors(manifest))
        assert errors, "Manifest with level_3 block must be rejected post-v0.7.0"

    def test_rejects_options_ui(self):
        # v0.8 project-shape refactor: the legacy `ui` option dimension was
        # removed. The schema must reject manifests that still declare it.
        schema = _load_schema()
        manifest = {
            "agent": "x",
            "description": "y",
            "options": {
                "type": {"prompt": "Type?", "choices": ["api"]},
                "ui": {"prompt": "UI?", "choices": ["none", "react", "angular"]},
            },
            "variants": {"type": {"api": {"files": []}}},
        }
        validator = Draft202012Validator(schema)
        errors = list(validator.iter_errors(manifest))
        assert errors, "Manifest with options.ui must be rejected after v0.8 shape refactor"
        assert any("ui" in str(e.message) or "propertyNames" in e.message for e in errors), (
            f"At least one error must reference the rejected `ui` key; got: {[e.message for e in errors]}"
        )

    def test_rejects_variants_ui(self):
        # Same v0.8 cleanup at the variants layer.
        schema = _load_schema()
        manifest = {
            "agent": "x",
            "description": "y",
            "variants": {
                "type": {"api": {"files": []}},
                "ui": {"react": {"files": []}},
            },
        }
        validator = Draft202012Validator(schema)
        errors = list(validator.iter_errors(manifest))
        assert errors, "Manifest with variants.ui must be rejected after v0.8 shape refactor"


# ---------------------------------------------------------------------------
# Positive: example manifests showing the new shapes
# ---------------------------------------------------------------------------


class TestSchemaAcceptsNewShapes:
    """Confirm the v0.7.0 additions are accepted, not just permitted by accident."""

    def test_accepts_level_4_with_explicit_merge_mode(self):
        schema = _load_schema()
        manifest = {
            "agent": "x",
            "description": "y",
            "variants": {
                "type": {
                    "api": {
                        "files": [{"src": "base.md", "dest": "BASE.md"}],
                        "governed": ["docs/architecture/"],
                        "level_4": {
                            "mode": "merge",
                            "files": [{"src": "addon.md", "dest": "ADDON.md"}],
                            "shared": ["features/starter_backend/"],
                            "governed": ["governance/backend/"]
                        }
                    }
                }
            },
        }
        validator = Draft202012Validator(schema)
        errors = list(validator.iter_errors(manifest))
        assert not errors, f"Should accept level_4 with mode=merge; got: {errors}"

    def test_accepts_level_5_with_explicit_replace_mode(self):
        schema = _load_schema()
        manifest = {
            "agent": "x",
            "description": "y",
            "variants": {
                "type": {
                    "api": {
                        "files": [{"src": "base.md", "dest": "BASE.md"}],
                        "level_5": {
                            "mode": "replace",
                            "files": [{"src": "l5.md", "dest": "L5.md"}]
                        }
                    }
                }
            },
        }
        validator = Draft202012Validator(schema)
        errors = list(validator.iter_errors(manifest))
        assert not errors, f"Should accept level_5 with mode=replace; got: {errors}"

    def test_accepts_level_4_without_mode_field(self):
        # mode is optional — default semantics handled by the CLI, not the schema.
        schema = _load_schema()
        manifest = {
            "agent": "x",
            "description": "y",
            "variants": {
                "type": {
                    "api": {
                        "level_4": {
                            "files": [{"src": "addon.md", "dest": "ADDON.md"}]
                        }
                    }
                }
            },
        }
        validator = Draft202012Validator(schema)
        errors = list(validator.iter_errors(manifest))
        assert not errors, f"mode must be optional on level_4; got: {errors}"

    def test_accepts_by_type_at_base_and_levels(self):
        # v0.8 by_type CI dispatch: schema must accept the by_type sub-block
        # in both base variant_config and level_override.
        schema = _load_schema()
        manifest = {
            "agent": "x",
            "description": "y",
            "variants": {
                "ci": {
                    "github": {
                        "governed": ["common.yml"],
                        "by_type": {
                            "api":      {"governed": ["api.yml"]},
                            "ui-react": {"governed": ["ui.yml"]},
                        },
                        "level_4": {
                            "mode": "merge",
                            "governed": [],
                            "by_type": {
                                "api":      {"governed": ["api-l4.yml"]},
                                "ui-react": {"governed": ["ui-l4.yml"]},
                            },
                        },
                    }
                }
            },
        }
        validator = Draft202012Validator(schema)
        errors = list(validator.iter_errors(manifest))
        assert not errors, f"Schema must accept by_type sub-block; got: {errors}"

    def test_accepts_by_stack_inside_by_type_entries(self):
        # Data CI can dispatch first by type, then by stack, so stack-specific
        # gates stay scoped to data stacks.
        schema = _load_schema()
        manifest = {
            "agent": "x",
            "description": "y",
            "options": {
                "type": {"prompt": "Type?", "choices": ["data"]},
                "ci": {"prompt": "CI?", "choices": ["github"]},
                "stack": {
                    "choices": ["python-dbt", "databricks-lakehouse"],
                    "default": "python-dbt",
                },
            },
            "variants": {
                "ci": {
                    "github": {
                        "governed": [],
                        "by_type": {
                            "data": {
                                "governed": ["ci/github/data-common-gate.yml"],
                                "by_stack": {
                                    "python-dbt": {"governed": ["ci/github/dbt-gate.yml"]},
                                    "databricks-lakehouse": {
                                        "governed": ["ci/github/databricks-gate.yml"],
                                    },
                                },
                            }
                        },
                        "level_4": {
                            "mode": "merge",
                            "by_type": {
                                "data": {
                                    "by_stack": {
                                        "python-dbt": {"governed": ["ci/github/dbt-gate.yml"]},
                                    }
                                }
                            },
                        },
                    }
                }
            },
        }
        validator = Draft202012Validator(schema)
        errors = list(validator.iter_errors(manifest))
        assert not errors, f"Schema must accept by_stack under by_type; got: {errors}"

    def test_rejects_unknown_key_in_by_type_entry(self):
        # by_type_entry has additionalProperties: false; rogue keys must error.
        schema = _load_schema()
        manifest = {
            "agent": "x",
            "description": "y",
            "variants": {
                "ci": {
                    "github": {
                        "by_type": {
                            "api": {"governed": [], "rogue_field": True}
                        }
                    }
                }
            },
        }
        validator = Draft202012Validator(schema)
        errors = list(validator.iter_errors(manifest))
        assert errors, "Unknown keys inside by_type_entry must be rejected"

    def test_rejects_unknown_key_in_by_stack_entry(self):
        schema = _load_schema()
        manifest = {
            "agent": "x",
            "description": "y",
            "variants": {
                "ci": {
                    "github": {
                        "by_type": {
                            "data": {
                                "by_stack": {
                                    "python-dbt": {
                                        "governed": [],
                                        "rogue_field": True,
                                    }
                                }
                            }
                        }
                    }
                }
            },
        }
        validator = Draft202012Validator(schema)
        errors = list(validator.iter_errors(manifest))
        assert errors, "Unknown keys inside by_stack_entry must be rejected"

    @pytest.mark.parametrize("ui_type", ["ui-react", "ui-angular"])
    def test_accepts_new_ui_type_in_choices_and_variants(self, ui_type):
        # v0.8 introduces the flat ui-react / ui-angular type values. The
        # schema must accept them in type.choices and as variants.type keys.
        schema = _load_schema()
        manifest = {
            "agent": "x",
            "description": "y",
            "options": {
                "type": {"prompt": "Type?", "choices": ["api", "cli", "ui-react", "ui-angular"]},
            },
            "variants": {
                "type": {
                    ui_type: {
                        "files": [{"src": f"claude-md/{ui_type}.md", "dest": "CLAUDE.md"}],
                    }
                }
            },
        }
        validator = Draft202012Validator(schema)
        errors = list(validator.iter_errors(manifest))
        assert not errors, f"Schema must accept --type {ui_type}; got: {errors}"


# ---------------------------------------------------------------------------
# Extension manifest schema (Increment 2)
# ---------------------------------------------------------------------------


EXT_DIR = REPO_ROOT / "extensions" / "agentic-skills"
EXT_SCHEMA_PATH = EXT_DIR / "schemas" / "extension-manifest.schema.json"
EXT_MANIFEST_PATH = EXT_DIR / "manifest.yaml"


def test_extension_manifest_schema_is_valid_json_schema():
    schema = json.loads(EXT_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)


def test_agentic_skills_manifest_matches_schema():
    yaml = pytest.importorskip("yaml")
    schema = json.loads(EXT_SCHEMA_PATH.read_text(encoding="utf-8"))
    manifest = yaml.safe_load(EXT_MANIFEST_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    errors = list(validator.iter_errors(manifest))
    assert not errors, f"agentic-skills manifest must validate; got: {errors}"


# ---------------------------------------------------------------------------
# Extension manifest schema — relates_to (Increment 3)
# ---------------------------------------------------------------------------


def _minimal_ext_manifest(**overrides) -> dict:
    base = {
        "id": "sample-ext",
        "name": "Sample",
        "version": "0.1.0",
        "extension_type": "architecture",
        "contract_sets": [
            {"id": "sample", "description": "x", "paths": ["docs/X.md"]}
        ],
    }
    base.update(overrides)
    return base


class TestSchemaRelatesTo:
    def _validate(self, manifest: dict) -> list:
        schema = json.loads(EXT_SCHEMA_PATH.read_text(encoding="utf-8"))
        return list(Draft202012Validator(schema).iter_errors(manifest))

    def test_schema_accepts_relates_to_with_extends(self):
        m = _minimal_ext_manifest()
        m["contract_sets"][0]["relates_to"] = {
            "extends": ["docs/backend/architecture/CORE.md"],
        }
        assert self._validate(m) == []

    def test_schema_accepts_relates_to_with_supersedes(self):
        m = _minimal_ext_manifest()
        m["contract_sets"][0]["relates_to"] = {
            "supersedes": ["docs/backend/architecture/CORE.md"],
        }
        assert self._validate(m) == []

    def test_schema_accepts_relates_to_with_both(self):
        m = _minimal_ext_manifest()
        m["contract_sets"][0]["relates_to"] = {
            "extends": ["docs/backend/architecture/A.md"],
            "supersedes": ["docs/backend/architecture/B.md"],
        }
        assert self._validate(m) == []

    def test_schema_accepts_omitted_relates_to(self):
        # relates_to is optional — existing manifests without it must still validate
        assert self._validate(_minimal_ext_manifest()) == []

    def test_schema_rejects_relates_to_as_string(self):
        m = _minimal_ext_manifest()
        m["contract_sets"][0]["relates_to"] = "not an object"
        assert self._validate(m) != []

    def test_schema_rejects_relates_to_extends_as_string(self):
        m = _minimal_ext_manifest()
        m["contract_sets"][0]["relates_to"] = {"extends": "should be array"}
        assert self._validate(m) != []


class TestAgenticSkillsLiveRelatesTo:
    """Pin the live agentic-skills manifest's relates_to claims so they don't
    silently drift away from the real core L5 contracts they overlap with."""

    @staticmethod
    def _live_manifest() -> dict:
        yaml = pytest.importorskip("yaml")
        return yaml.safe_load(EXT_MANIFEST_PATH.read_text(encoding="utf-8"))

    def test_agentic_skills_declares_relates_to_extends(self):
        m = self._live_manifest()
        cs = m["contract_sets"][0]
        assert "relates_to" in cs, "agentic-skills should declare relates_to"
        assert "extends" in cs["relates_to"]
        assert isinstance(cs["relates_to"]["extends"], list)
        assert len(cs["relates_to"]["extends"]) > 0

    def test_agentic_skills_extends_known_core_l5_contracts(self):
        m = self._live_manifest()
        extends = set(m["contract_sets"][0].get("relates_to", {}).get("extends", []))
        expected = {
            "docs/backend/architecture/EVALUATION_LLM_CONTRACT.md",
            "docs/backend/architecture/OBSERVABILITY_LLM_CONTRACT.md",
            "docs/backend/architecture/GUARDRAILS_CONTRACT.md",
        }
        missing = expected - extends
        assert not missing, f"agentic-skills must extend {missing}"

    def test_agentic_skills_extends_paths_exist_in_repo(self):
        m = self._live_manifest()
        extends = m["contract_sets"][0].get("relates_to", {}).get("extends", [])
        for path in extends:
            full = REPO_ROOT / path
            assert full.exists(), f"declared extends path {path!r} not found in repo"

    def test_agentic_skills_extension_validates_cleanly_against_repo(self):
        """The reference extension must be WARN-free when validated against the
        canonical repo. Any new core contract that overlaps an extension contract
        topic must be declared in relates_to before merging."""
        from cli.extensions import discover_extensions, validate_extension

        extensions = discover_extensions(REPO_ROOT)
        agentic = next((e for e in extensions if e.id == "agentic-skills"), None)
        assert agentic is not None, "agentic-skills extension not discovered in repo"
        issues = validate_extension(agentic, REPO_ROOT)
        assert issues == [], f"reference extension must validate cleanly; got: {issues}"

    def test_no_templates_block_in_manifest(self):
        """Increment 4 — the `templates:` block was removed because those
        artifacts ship with skill packages, not the platform repo."""
        m = self._live_manifest()
        assert "templates" not in m, (
            "manifest should not declare a templates block; skill-package artifact "
            "shapes are defined by the architecture contracts instead"
        )

    def test_templates_dir_absent(self):
        """Increment 4 — the templates/ folder is gone; nothing in the platform
        repo should still scaffold per-skill artifacts."""
        templates_dir = REPO_ROOT / "extensions" / "agentic-skills" / "governance" / "backend" / "templates"
        assert not templates_dir.exists(), (
            f"{templates_dir} should not exist; templates moved to skill-author scope"
        )


class TestInc5InboundContracts:
    """Increment 5 — inbound contracts for the skill family / phase / handoff
    layer and their JSON Schemas. Tests written before implementation."""

    ARCH_DIR = EXT_DIR / "docs" / "backend" / "architecture"

    @staticmethod
    def _live_manifest() -> dict:
        yaml = pytest.importorskip("yaml")
        return yaml.safe_load(EXT_MANIFEST_PATH.read_text(encoding="utf-8"))

    # --- file existence ---

    def test_skill_family_manifest_contract_file_exists(self):
        assert (self.ARCH_DIR / "SKILL_FAMILY_MANIFEST_CONTRACT.md").exists()

    def test_handoff_contract_file_exists(self):
        assert (self.ARCH_DIR / "HANDOFF_CONTRACT.md").exists()

    # --- manifest declares them ---

    def test_manifest_declares_skill_family_manifest_contract(self):
        m = self._live_manifest()
        paths = m["contract_sets"][0]["paths"]
        assert "docs/backend/architecture/SKILL_FAMILY_MANIFEST_CONTRACT.md" in paths

    def test_manifest_declares_handoff_contract(self):
        m = self._live_manifest()
        paths = m["contract_sets"][0]["paths"]
        assert "docs/backend/architecture/HANDOFF_CONTRACT.md" in paths


class TestInc5JsonSchemas:
    """Increment 5 — machine-validatable schemas for the 3 inbound payload
    shapes. Each schema is tested three ways: it's a valid schema, it accepts
    a minimal valid payload, and it rejects a specific bad case."""

    SCHEMAS_DIR = EXT_DIR / "schemas"

    @staticmethod
    def _load(path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _errors(schema: dict, payload: dict) -> list:
        return list(Draft202012Validator(schema).iter_errors(payload))

    # --- csp-family-manifest.schema.json ---

    def test_csp_family_manifest_schema_is_valid_json_schema(self):
        schema = self._load(self.SCHEMAS_DIR / "csp-family-manifest.schema.json")
        Draft202012Validator.check_schema(schema)

    def test_csp_family_manifest_schema_accepts_minimal_valid_payload(self):
        schema = self._load(self.SCHEMAS_DIR / "csp-family-manifest.schema.json")
        payload = {
            "family_id": "lean-coe",
            "version": "0.1.0",
            "name": "Lean CoE CSP",
            "description": "A test family",
            "owner": "team-csp@example.com",
            "phases": [
                {
                    "id": "phase00-configuration",
                    "order": 0,
                    "skill_ref": "phase00-configuration@0.1.0",
                    "depends_on": [],
                },
            ],
        }
        assert self._errors(schema, payload) == []

    def test_csp_family_manifest_schema_rejects_missing_phases(self):
        schema = self._load(self.SCHEMAS_DIR / "csp-family-manifest.schema.json")
        payload = {
            "family_id": "lean-coe",
            "version": "0.1.0",
            "name": "Lean CoE CSP",
            "description": "missing phases",
            "owner": "team-csp@example.com",
        }
        assert self._errors(schema, payload) != []

    # --- skill-package.schema.json ---

    def test_skill_package_schema_is_valid_json_schema(self):
        schema = self._load(self.SCHEMAS_DIR / "skill-package.schema.json")
        Draft202012Validator.check_schema(schema)

    def test_skill_package_schema_accepts_minimal_valid_payload(self):
        schema = self._load(self.SCHEMAS_DIR / "skill-package.schema.json")
        payload = {
            "skill_id": "phase00-configuration",
            "name": "Phase 00 Configuration",
            "version": "0.1.0",
            "supported_modes": ["interactive"],
            "allowed_actions": ["read_config"],
            "disallowed_actions": ["write_external_system"],
        }
        assert self._errors(schema, payload) == []

    def test_skill_package_schema_rejects_invalid_skill_id_format(self):
        schema = self._load(self.SCHEMAS_DIR / "skill-package.schema.json")
        payload = {
            "skill_id": "Phase_00_Configuration",   # uppercase + underscores: invalid
            "name": "Phase 00",
            "version": "0.1.0",
            "supported_modes": ["interactive"],
            "allowed_actions": [],
            "disallowed_actions": [],
        }
        assert self._errors(schema, payload) != []

    # --- handoff-payload.schema.json ---

    def test_handoff_payload_schema_is_valid_json_schema(self):
        schema = self._load(self.SCHEMAS_DIR / "handoff-payload.schema.json")
        Draft202012Validator.check_schema(schema)

    def test_handoff_payload_schema_accepts_minimal_valid_payload(self):
        schema = self._load(self.SCHEMAS_DIR / "handoff-payload.schema.json")
        payload = {
            "from_phase": "phase00-configuration",
            "to_phase": "phase01-discovery-readiness",
            "family_id": "lean-coe",
            "run_id": "run-2026-05-24-001",
            "artifacts": [
                {
                    "type": "evidence_bundle",
                    "schema_ref": "evidence-bundle@1.0.0",
                    "content_ref": "sha256:abc123",
                },
            ],
            "state": {
                "phase_outputs": {"phase00-configuration": {"status": "ok"}},
                "accumulated_context": {"tenant": "acme"},
            },
            "trace": {
                "events": [
                    {
                        "timestamp": "2026-05-24T12:00:00Z",
                        "event_type": "PHASE_COMPLETED",
                        "detail": "phase00 finished",
                    },
                ],
                "decisions": [],
                "approvals_taken": [],
            },
        }
        assert self._errors(schema, payload) == []

    def test_handoff_payload_schema_rejects_artifact_missing_content_ref(self):
        schema = self._load(self.SCHEMAS_DIR / "handoff-payload.schema.json")
        payload = {
            "from_phase": "p1",
            "to_phase": "p2",
            "family_id": "lean-coe",
            "run_id": "r1",
            "artifacts": [
                {"type": "x", "schema_ref": "s@1.0.0"},  # missing content_ref
            ],
            "state": {"phase_outputs": {}, "accumulated_context": {}},
            "trace": {"events": [], "decisions": [], "approvals_taken": []},
        }
        assert self._errors(schema, payload) != []


class TestInc6RuntimeContracts:
    """Increment 6 — runtime-behavior contracts for the phase state machine
    and the three registries. Markdown-only (no schemas; these describe
    platform behavior, not payload shapes)."""

    ARCH_DIR = EXT_DIR / "docs" / "backend" / "architecture"

    @staticmethod
    def _live_manifest() -> dict:
        yaml = pytest.importorskip("yaml")
        return yaml.safe_load(EXT_MANIFEST_PATH.read_text(encoding="utf-8"))

    def test_phase_state_machine_contract_file_exists(self):
        assert (self.ARCH_DIR / "PHASE_STATE_MACHINE_CONTRACT.md").exists()

    def test_registry_contract_file_exists(self):
        assert (self.ARCH_DIR / "REGISTRY_CONTRACT.md").exists()

    def test_manifest_declares_phase_state_machine_contract(self):
        m = self._live_manifest()
        paths = m["contract_sets"][0]["paths"]
        assert "docs/backend/architecture/PHASE_STATE_MACHINE_CONTRACT.md" in paths

    def test_manifest_declares_registry_contract(self):
        m = self._live_manifest()
        paths = m["contract_sets"][0]["paths"]
        assert "docs/backend/architecture/REGISTRY_CONTRACT.md" in paths


# ---------------------------------------------------------------------------
# .govkit/marker.json schema (PR 1 / A11)
# ---------------------------------------------------------------------------


MARKER_SCHEMA_PATH = REPO_ROOT / "governance" / "schemas" / "govkit-marker.schema.json"


def _load_marker_schema() -> dict:
    return json.loads(MARKER_SCHEMA_PATH.read_text(encoding="utf-8"))


def test_marker_schema_is_a_valid_json_schema():
    """The marker schema must itself conform to the meta-schema."""
    Draft202012Validator.check_schema(_load_marker_schema())


class TestMarkerSchemaAcceptsFreshlyWrittenMarkers:
    """A marker written by write_govkit_marker() must validate against the
    shipped schema. Otherwise the schema and the writer have drifted."""

    def test_minimal_apply_marker_validates(self, tmp_path):
        from cli.marker import write_govkit_marker

        write_govkit_marker(tmp_path, "claude-code", "4", {"type": "api", "ci": "github", "level": "4"})
        marker = json.loads((tmp_path / ".govkit" / "marker.json").read_text(encoding="utf-8"))

        validator = Draft202012Validator(_load_marker_schema())
        errors = list(validator.iter_errors(marker))
        assert not errors, "freshly written marker failed schema validation: " + "; ".join(e.message for e in errors)

    def test_marker_with_populated_stack_validates(self, tmp_path):
        from cli.marker import write_govkit_marker

        stack = {
            "id": "dotnet-aspnet",
            "version": "0.10.0",
            "display_name": "C# 12 / .NET 8 / ASP.NET Core",
            "applied_at": "2026-05-27T15:00:00+00:00",
        }
        write_govkit_marker(
            tmp_path, "claude-code", "4",
            {"type": "api", "ci": "azure", "level": "4"},
            stack=stack,
        )
        marker = json.loads((tmp_path / ".govkit" / "marker.json").read_text(encoding="utf-8"))

        validator = Draft202012Validator(_load_marker_schema())
        errors = list(validator.iter_errors(marker))
        assert not errors, "; ".join(e.message for e in errors)

    def test_marker_with_assumptions_validates(self, tmp_path):
        from cli.marker import write_govkit_marker

        assumptions = [{
            "id": "architecture.style",
            "value": "hexagonal",
            "source": "default",
            "confidence": "low",
            "evidence": [],
            "files_affected": ["docs/backend/architecture/BOUNDARIES.md"],
            "review_required": True,
            "warning_message": "Hexagonal layout assumed; no ports/ or adapters/ folder detected.",
            "calibrated_at": None,
            "calibrated_against_overlay_version": None,
        }]
        write_govkit_marker(
            tmp_path, "claude-code", "4",
            {"type": "api", "ci": "github", "level": "4"},
            assumptions=assumptions,
        )
        marker = json.loads((tmp_path / ".govkit" / "marker.json").read_text(encoding="utf-8"))

        validator = Draft202012Validator(_load_marker_schema())
        errors = list(validator.iter_errors(marker))
        assert not errors, "; ".join(e.message for e in errors)


class TestMarkerSchemaRejectsInvalid:
    def _valid_marker(self) -> dict:
        return {
            "version": "0.10.0",
            "level": "4",
            "agent": "claude-code",
            "options": {"type": "api", "ci": "github"},
            "applied_at": "2026-05-27T15:00:00+00:00",
            "stack": None,
            "assumptions": [],
            "calibration": {"completed_at": None, "decisions": []},
        }

    def test_rejects_missing_agent(self):
        marker = self._valid_marker()
        del marker["agent"]
        errors = list(Draft202012Validator(_load_marker_schema()).iter_errors(marker))
        assert errors and any("agent" in e.message for e in errors)

    def test_rejects_unknown_level(self):
        marker = self._valid_marker()
        marker["level"] = "6"
        errors = list(Draft202012Validator(_load_marker_schema()).iter_errors(marker))
        assert errors

    def test_rejects_unknown_type(self):
        marker = self._valid_marker()
        marker["options"]["type"] = "fullstack"
        errors = list(Draft202012Validator(_load_marker_schema()).iter_errors(marker))
        assert errors

    def test_rejects_unknown_assumption_source(self):
        marker = self._valid_marker()
        marker["assumptions"] = [{
            "id": "stack.language", "value": "python",
            "source": "wishful-thinking",  # not in enum
            "confidence": "low", "evidence": [], "files_affected": [],
            "review_required": False,
        }]
        errors = list(Draft202012Validator(_load_marker_schema()).iter_errors(marker))
        assert errors

    def test_rejects_unknown_top_level_key(self):
        marker = self._valid_marker()
        marker["extra_field"] = "nope"
        errors = list(Draft202012Validator(_load_marker_schema()).iter_errors(marker))
        assert errors

    def test_accepts_marker_with_extension_sourced_assumption(self):
        """source='extension' is one of the new sources added per the
        Extensions Compatibility section."""
        marker = self._valid_marker()
        marker["assumptions"] = [{
            "id": "extension.agentic-skills.agent-runtime",
            "value": "true",
            "source": "extension",
            "confidence": "high",
            "evidence": ["extensions/agentic-skills/manifest.yaml"],
            "files_affected": [],
            "review_required": False,
            "warning_message": None,
            "calibrated_at": None,
            "calibrated_against_overlay_version": None,
        }]
        errors = list(Draft202012Validator(_load_marker_schema()).iter_errors(marker))
        assert not errors


# ---------------------------------------------------------------------------
# cli/stacks/<id>/overlay.yaml schema
# ---------------------------------------------------------------------------


STACK_OVERLAY_SCHEMA_PATH = REPO_ROOT / "governance" / "schemas" / "stack-overlay.schema.json"
STACKS_DIR = REPO_ROOT / "cli" / "stacks"


def _bundled_stack_ids() -> list[str]:
    return sorted(
        d.name for d in STACKS_DIR.iterdir()
        if d.is_dir() and (d / "overlay.yaml").is_file()
    )


def test_stack_overlay_schema_is_a_valid_json_schema():
    schema = json.loads(STACK_OVERLAY_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)


@pytest.mark.parametrize("stack_id", _bundled_stack_ids())
def test_bundled_overlay_validates_against_schema(stack_id):
    """Every cli/stacks/<id>/overlay.yaml must validate against the shipped
    schema. Catches drift between an overlay author and the schema authors."""
    yaml_mod = pytest.importorskip("yaml")
    schema = json.loads(STACK_OVERLAY_SCHEMA_PATH.read_text(encoding="utf-8"))
    overlay_path = STACKS_DIR / stack_id / "overlay.yaml"
    overlay = yaml_mod.safe_load(overlay_path.read_text(encoding="utf-8"))

    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(overlay), key=lambda e: list(e.path))
    assert not errors, (
        f"{stack_id}/overlay.yaml failed schema validation:\n"
        + "\n".join(f"  - at {list(e.absolute_path)}: {e.message}" for e in errors)
    )


@pytest.mark.parametrize("stack_id", _bundled_stack_ids())
def test_overlay_has_yaml_language_server_modeline(stack_id):
    """The first line of every overlay.yaml must point VS Code's YAML
    extension at the right schema — otherwise it tries to validate against
    unrelated public schemas (e.g. the JSON Schema Overlay spec) and floods
    the Problems panel with false errors."""
    overlay_path = STACKS_DIR / stack_id / "overlay.yaml"
    first_line = overlay_path.read_text(encoding="utf-8").splitlines()[0]
    assert first_line.startswith("# yaml-language-server: $schema=")
    assert "stack-overlay.schema.json" in first_line
