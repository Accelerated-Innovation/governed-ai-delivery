#!/usr/bin/env python3
# Copyright 2026 Accelerated Innovation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
govkit extensions — discovery of self-describing extension packs.

Extensions live in-place under <target>/extensions/<id>/ in a consuming
project. Govkit discovers them by scanning for manifest.yaml files and
surfaces them to agents and validation. Extensions are not installed by
the CLI; the in-repo folder *is* the install.

This module owns Increment 1 of the extension feature: discovery only.
Validation (validate_extension) and overlap detection arrive in later
increments.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml


EXTENSIONS_DIR = "extensions"
MANIFEST_FILE = "manifest.yaml"

_REQUIRED_FIELDS = ("id", "name", "version", "extension_type", "contract_sets")
_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")


@dataclass
class Extension:
    """A discovered extension. Errors collected during discovery/parse are
    held in .errors so callers can decide warn-vs-fail policy."""

    id: str
    root: Path
    manifest: dict = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    @property
    def name(self) -> str:
        return self.manifest.get("name", self.id)

    @property
    def version(self) -> str:
        return self.manifest.get("version", "0.0.0")


def load_manifest(manifest_path: Path) -> tuple[dict | None, str | None]:
    """Safe-load a YAML manifest. Returns (data, None) on success or
    (None, error_message) on failure. Never raises."""
    try:
        text = manifest_path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, f"could not read manifest: {exc}"
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        return None, f"invalid YAML: {exc}"
    if data is None:
        return None, "manifest is empty"
    if not isinstance(data, dict):
        return None, "manifest must be a YAML mapping"
    return data, None


def discover_extensions(target: Path) -> list[Extension]:
    """Scan <target>/extensions/*/manifest.yaml. Returns [] when the
    extensions directory does not exist — preserves original govkit
    behavior for projects that don't use extensions.

    For each subdirectory of extensions/, an Extension is returned. If the
    subdirectory has no manifest.yaml or the manifest fails to parse, the
    Extension carries an error in .errors and a minimal id derived from
    the folder name. Discovery never raises.
    """
    ext_root = target / EXTENSIONS_DIR
    if not ext_root.is_dir():
        return []

    results: list[Extension] = []
    for entry in sorted(ext_root.iterdir()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        manifest_path = entry / MANIFEST_FILE
        if not manifest_path.exists():
            results.append(Extension(
                id=entry.name,
                root=entry,
                errors=[f"missing {MANIFEST_FILE}"],
            ))
            continue
        data, err = load_manifest(manifest_path)
        if err is not None:
            results.append(Extension(
                id=entry.name,
                root=entry,
                errors=[err],
            ))
            continue
        ext_id = data.get("id") if isinstance(data.get("id"), str) else entry.name
        results.append(Extension(id=ext_id, root=entry, manifest=data))
    return results


def _check_required_fields(manifest: dict) -> list[str]:
    return [f"missing required field: {fld}" for fld in _REQUIRED_FIELDS if fld not in manifest]


def _check_id(manifest: dict, ext: Extension) -> list[str]:
    ext_id = manifest.get("id")
    if not isinstance(ext_id, str):
        return []
    issues: list[str] = []
    if not _ID_PATTERN.match(ext_id):
        issues.append(f"invalid id format: {ext_id!r} (must match ^[a-z0-9][a-z0-9-]*$)")
    if ext_id != ext.root.name:
        issues.append(f"id {ext_id!r} does not match folder name {ext.root.name!r}")
    return issues


def _check_path_entry(label: str, path: object, ext: Extension) -> list[str]:
    if not isinstance(path, str):
        return [f"{label} must be a string"]
    if not (ext.root / path).exists():
        return [f"{label}: {path!r} does not exist under {EXTENSIONS_DIR}/{ext.id}/"]
    return []


def _check_contract_sets(manifest: dict, ext: Extension) -> list[str]:
    contract_sets = manifest.get("contract_sets")
    if not isinstance(contract_sets, list):
        return []
    issues: list[str] = []
    for i, cs in enumerate(contract_sets):
        if not isinstance(cs, dict):
            issues.append(f"contract_sets[{i}] must be a mapping")
            continue
        paths = cs.get("paths") or []
        if not isinstance(paths, list):
            issues.append(f"contract_sets[{i}].paths must be a list")
            continue
        for path in paths:
            issues.extend(_check_path_entry(f"contract_sets[{i}].paths", path, ext))
    return issues


def _check_templates(manifest: dict, ext: Extension) -> list[str]:
    templates = manifest.get("templates")
    if not isinstance(templates, list):
        return []
    issues: list[str] = []
    for i, tpl in enumerate(templates):
        if not isinstance(tpl, dict):
            issues.append(f"templates[{i}] must be a mapping")
            continue
        path = tpl.get("path")
        if path is None:
            continue
        issues.extend(_check_path_entry(f"templates[{i}].path", path, ext))
    return issues


def validate_extension(ext: Extension, target: Path) -> list[str]:
    """Return a list of human-readable validation issues for one extension.

    Increment 2 checks:
      - discovery errors (missing/invalid manifest) — passed through
      - required top-level fields present
      - id format and folder-name match
      - contract_sets[].paths exist under ext.root
      - templates[].path exist under ext.root

    Returns [] when fully valid. The `target` parameter is reserved for
    project-root-relative checks added in Increment 3 (relates_to.extends,
    relates_to.supersedes, undeclared overlap detection)."""
    del target  # reserved for Increment 3
    if ext.errors:
        return list(ext.errors)
    m = ext.manifest
    return [
        *_check_required_fields(m),
        *_check_id(m, ext),
        *_check_contract_sets(m, ext),
        *_check_templates(m, ext),
    ]


def report_extensions(target: Path) -> int:
    """Print discovered extensions. Called from cmd_apply for visibility.
    Silent when no extensions are present. Returns the count discovered."""
    extensions = discover_extensions(target)
    if not extensions:
        return 0
    print("\nExtensions detected:")
    for ext in extensions:
        if ext.errors:
            print(f"  {ext.id} — WARN: {ext.errors[0]}")
        else:
            desc = ext.manifest.get("description", "").strip()
            suffix = f" — {ext.name}" if ext.name != ext.id else ""
            print(f"  {ext.id} v{ext.version}{suffix}")
            if desc:
                print(f"    {desc}")
    return len(extensions)
