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

from dataclasses import dataclass, field
from pathlib import Path

import yaml


EXTENSIONS_DIR = "extensions"
MANIFEST_FILE = "manifest.yaml"


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
