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
