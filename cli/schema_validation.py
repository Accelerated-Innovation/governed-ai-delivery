# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Strict local schema loading shared by profile and capability-pack adapters."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker

from . import paths


class DocumentError(ValueError):
    """Invalid, conflicting or unsafe profile/record input."""


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def content_digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


class _StrictLoader(yaml.SafeLoader):
    """JSON-shaped YAML only: no aliases, duplicate keys or implicit dates."""

    yaml_implicit_resolvers = {
        key: [(tag, regex) for tag, regex in values if tag != "tag:yaml.org,2002:timestamp"]
        for key, values in yaml.SafeLoader.yaml_implicit_resolvers.items()
    }

    def compose_node(self, parent, index):
        if self.check_event(yaml.AliasEvent):
            raise DocumentError("YAML aliases are not allowed in a governance document")
        return super().compose_node(parent, index)

    def construct_mapping(self, node, deep=False):
        result = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str):
                raise DocumentError("Object keys must be strings")
            if key in result:
                raise DocumentError(f"Duplicate YAML/JSON key: {key}")
            result[key] = self.construct_object(value_node, deep=deep)
        return result


def parse_document(content: str | bytes) -> dict:
    """Parse one captured document without rereading its backing file."""
    try:
        value = yaml.load(content, Loader=_StrictLoader)
        canonical_json(value)
        return value
    except (UnicodeError, yaml.YAMLError, TypeError, ValueError, RecursionError) as exc:
        raise DocumentError(str(exc)) from exc


def read_document(path: Path) -> dict:
    try:
        return parse_document(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise DocumentError(f"{path}: {exc}") from exc


def validate_document(document: dict, schema_name: str) -> None:
    try:
        canonical_json(document)
        schema = json.loads(
            (paths.GOVERNANCE_DIR / "schemas" / f"{schema_name}.schema.json").read_text(
                encoding="utf-8"
            )
        )
    except (OSError, UnicodeError, TypeError, ValueError, RecursionError) as exc:
        raise DocumentError(f"Cannot validate {schema_name}: {exc}") from exc
    # Bundled schemas use local $defs only; validation never retrieves schemas.
    errors = list(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(document)
    )
    if errors:
        details = []
        for error in errors:
            location = "/" + "/".join(str(part) for part in error.absolute_path)
            details.append(f"{location}: {error.message}")
        raise DocumentError(f"Invalid {schema_name}: " + "; ".join(details))
