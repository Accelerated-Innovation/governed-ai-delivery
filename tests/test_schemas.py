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
