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
from pathlib import Path, PurePosixPath, PureWindowsPath

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
    except (OSError, UnicodeDecodeError) as exc:
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
    return discover_in(target / EXTENSIONS_DIR)


def discover_in(ext_root: Path) -> list[Extension]:
    """Scan a directory of extension folders (<ext_root>/<id>/manifest.yaml).

    The lower-level scanner behind discover_extensions. Used directly to
    enumerate bundled extension packs (paths.EXTENSION_PACKS_DIR), whose layout
    is the same <root>/<id>/manifest.yaml but not under an `extensions/` parent.
    Returns [] when ext_root does not exist. Never raises.
    """
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


def _check_safe_file_path(
    label: str, path: object, base: Path, base_label: str
) -> list[str]:
    """Resolve `path` against `base` and verify it is a relative, contained,
    existing file. Guards against absolute paths and `..` / symlink escape so
    a malicious or sloppy manifest cannot reach outside the declared root."""
    if not isinstance(path, str):
        return [f"{label} must be a string"]
    # Cross-platform: Path.is_absolute() is host-OS-specific (e.g. "/foo" is
    # not absolute on Windows because it has no drive). Check both flavors so
    # a POSIX-style abs path is rejected on Windows too, and vice versa.
    if PurePosixPath(path).is_absolute() or PureWindowsPath(path).is_absolute():
        return [f"{label}: {path!r} must be relative, not absolute"]
    base_resolved = base.resolve()
    candidate = (base / path).resolve(strict=False)
    if not candidate.is_relative_to(base_resolved):
        return [f"{label}: {path!r} resolves outside {base_label}"]
    if not candidate.is_file():
        return [f"{label}: {path!r} does not exist under {base_label} (or is not a file)"]
    return []


def _check_path_entry(label: str, path: object, ext: Extension) -> list[str]:
    return _check_safe_file_path(label, path, ext.root, f"{EXTENSIONS_DIR}/{ext.id}/")


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


def _check_relates_to_field(
    label: str, paths: object, target: Path
) -> list[str]:
    if not isinstance(paths, list):
        return []
    issues: list[str] = []
    for path in paths:
        if not isinstance(path, str):
            continue
        issues.extend(_check_safe_file_path(label, path, target, "project root"))
    return issues


def _check_relates_to(manifest: dict, target: Path) -> list[str]:
    contract_sets = manifest.get("contract_sets")
    if not isinstance(contract_sets, list):
        return []
    issues: list[str] = []
    for i, cs in enumerate(contract_sets):
        if not isinstance(cs, dict):
            continue
        relates_to = cs.get("relates_to")
        if not isinstance(relates_to, dict):
            continue
        issues.extend(_check_relates_to_field(
            f"contract_sets[{i}].relates_to.extends",
            relates_to.get("extends"),
            target,
        ))
        issues.extend(_check_relates_to_field(
            f"contract_sets[{i}].relates_to.supersedes",
            relates_to.get("supersedes"),
            target,
        ))
    return issues


_CORE_ARCHITECTURE_DIR = Path("docs/backend/architecture")
_CONTRACT_SUFFIX = "_CONTRACT.md"


def _topic_token(contract_filename: str) -> str | None:
    """Extract the topic token from a contract filename.

    AGENT_EVALUATION_CONTRACT.md -> 'EVALUATION'
    EVALUATION_LLM_CONTRACT.md   -> 'LLM'
    Files not ending in _CONTRACT.md return None.
    """
    if not contract_filename.endswith(_CONTRACT_SUFFIX):
        return None
    stem = contract_filename[: -len(_CONTRACT_SUFFIX)]
    parts = stem.split("_")
    return parts[-1] if parts and parts[-1] else None


def _declared_core_paths(contract_set: dict) -> set[str]:
    relates_to = contract_set.get("relates_to")
    if not isinstance(relates_to, dict):
        return set()
    declared: set[str] = set()
    for key in ("extends", "supersedes"):
        for path in relates_to.get(key) or []:
            if isinstance(path, str):
                declared.add(path)
    return declared


def _overlaps_for_contract(
    contract_path: str, declared: set[str], core_dir: Path
) -> list[tuple[str, str]]:
    """Return (extension_path, core_relative_path) pairs for undeclared overlaps."""
    filename = Path(contract_path).name
    ext_token = _topic_token(filename)
    if not ext_token:
        return []
    pairs: list[tuple[str, str]] = []
    for core_file in sorted(core_dir.glob(f"*{ext_token}*{_CONTRACT_SUFFIX}")):
        if core_file.name == filename:
            continue
        core_rel = (_CORE_ARCHITECTURE_DIR / core_file.name).as_posix()
        if core_rel in declared:
            continue
        pairs.append((contract_path, core_rel))
    return pairs


def _check_undeclared_overlap(manifest: dict, target: Path) -> list[str]:
    """Warn when an extension contract's topic token matches a core contract
    under <target>/docs/backend/architecture/ and the core path is not declared
    in relates_to.extends/supersedes. Pure filename heuristic — no content
    inspection."""
    core_dir = target / _CORE_ARCHITECTURE_DIR
    if not core_dir.is_dir():
        return []
    contract_sets = manifest.get("contract_sets")
    if not isinstance(contract_sets, list):
        return []
    issues: list[str] = []
    for cs in contract_sets:
        if not isinstance(cs, dict):
            continue
        declared = _declared_core_paths(cs)
        for path in cs.get("paths") or []:
            if not isinstance(path, str):
                continue
            for ext_path, core_rel in _overlaps_for_contract(path, declared, core_dir):
                issues.append(
                    f"{ext_path} overlaps core {core_rel} "
                    "— declare relates_to.extends or .supersedes"
                )
    return issues


def validate_extension(ext: Extension, target: Path) -> list[str]:
    """Return a list of human-readable validation issues for one extension.

    Increment 2 checks:
      - discovery errors (missing/invalid manifest) — passed through
      - required top-level fields present
      - id format and folder-name match
      - contract_sets[].paths exist under ext.root
      - templates[].path exist under ext.root

    Returns [] when fully valid. The `target` parameter is used for
    project-root-relative checks (relates_to.extends/supersedes paths,
    undeclared overlap with core contracts)."""
    if ext.errors:
        return list(ext.errors)
    m = ext.manifest
    return [
        *_check_required_fields(m),
        *_check_id(m, ext),
        *_check_contract_sets(m, ext),
        *_check_templates(m, ext),
        *_check_relates_to(m, target),
        *_check_undeclared_overlap(m, target),
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
