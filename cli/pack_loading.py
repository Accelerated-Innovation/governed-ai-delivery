# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Read bounded, declared pack content from existing extension distribution."""

from __future__ import annotations

from pathlib import Path, PurePosixPath, PureWindowsPath

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version

from . import paths
from .agent_layout import AGENT_LAYOUTS
from .pack_models import PackCheck, PackDependency, PackFile, PackSkill, PackSnapshot
from .schema_validation import (
    DocumentError,
    canonical_json,
    content_digest,
    read_document,
    validate_document,
)


class PackError(ValueError):
    """Invalid, unsafe or inconsistent pack input/operation."""


def safe_relative(value: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise PackError(f"Unsafe relative resource path: {value!r}")
    parts = value.split("/")
    if (
        PurePosixPath(value).is_absolute()
        or PureWindowsPath(value).is_absolute()
        or any(p in ("", ".", "..") for p in parts)
    ):
        raise PackError(f"Unsafe relative resource path: {value!r}")
    return value


def contained_file(root: Path, relative: str) -> Path:
    relative = safe_relative(relative)
    current = root
    if root.is_symlink():
        raise PackError(f"Pack root is a symlink: {root}")
    for part in relative.split("/"):
        current = current / part
        if current.is_symlink():
            raise PackError(f"Refusing symlink resource: {relative}")
    if not current.is_file():
        raise PackError(f"Missing required resource: {relative}")
    return current


def _legacy_contract(manifest: dict) -> dict:
    """Levels survive only as provenance; actual references create dependencies."""
    provides = [manifest["id"]]
    dependencies = {}
    resources = []
    for contract in manifest.get("contract_sets", []):
        provides.extend(contract.get("capabilities", []))
        resources.extend({"path": p, "kind": "contract"} for p in contract.get("paths", []))
        for reference in contract.get("relates_to", {}).get("extends", []):
            parts = reference.split("/")
            if len(parts) > 2 and parts[0] == "extensions" and parts[1] != manifest["id"]:
                dependencies[parts[1]] = {
                    "capability": parts[1],
                    "version": "*",
                    "reason": f"Referenced contract {reference}",
                }
    resources.extend(
        {"path": p["path"], "kind": "defaults"} for p in manifest.get("implementation_profiles", [])
    )
    resources.extend({"path": p["path"], "kind": "example"} for p in manifest.get("templates", []))
    return {
        "schema_version": 1,
        "provides": list(dict.fromkeys(provides)),
        "requires": list(dependencies.values()),
        "resources": resources,
    }


def load_pack(root: Path, *, source_kind: str = "local") -> PackSnapshot:
    root = root.absolute()
    try:
        if source_kind not in ("bundled", "local"):
            raise PackError("Pack source must be bundled or local")
        manifest_path = contained_file(root, "manifest.yaml")
        manifest = read_document(manifest_path)
        validate_document(manifest, "extension-manifest")
        block = (
            manifest["capability_pack"]
            if "capability_pack" in manifest
            else _legacy_contract(manifest)
        )
        validate_document(block, "capability-pack")
        identifier = manifest["id"]
        package_version = str(Version(manifest["version"]))
        minimum = str(Version(manifest.get("govkit_min_version", "0.0.0")))
        requires = tuple(
            PackDependency(d["capability"], d["version"], d["reason"])
            for d in block.get("requires", [])
        )
        for dependency in requires:
            SpecifierSet("" if dependency.version == "*" else dependency.version)
        skills = tuple(PackSkill(s["path"], s["install_as"]) for s in manifest.get("skills", []))
        checks = tuple(
            PackCheck(c["id"], c["path"], c.get("required", False)) for c in block.get("checks", [])
        )
        for kind, identifiers in (
            ("skill", [s.install_as for s in skills]),
            ("check", [c.id for c in checks]),
        ):
            if len(set(identifiers)) != len(identifiers):
                raise PackError(f"Duplicate {kind} identifier in {identifier}")
        files = {}

        def include(relative: str, kind: str) -> None:
            path = contained_file(root, relative)
            files[relative] = PackFile(relative, path.read_bytes(), kind)

        include("manifest.yaml", "manifest")
        for resource in block.get("resources", []):
            include(resource["path"], resource["kind"])
        for skill in skills:
            skill_path = safe_relative(skill.path)
            include(f"{skill_path}/SKILL.md", "skill")
            for path in sorted((root / skill_path).rglob("*")):
                if path.is_symlink():
                    raise PackError(f"Refusing symlink skill resource: {path.relative_to(root)}")
                if path.is_file():
                    include(path.relative_to(root).as_posix(), "skill")
        for check in checks:
            if not check.path.endswith(".py"):
                raise PackError(f"Check {check.id} must name a Python entrypoint")
            include(check.path, "check")
        for license_file in manifest.get("origin", {}).get("license_files", []):
            include(license_file, "license")
        ordered = tuple(files[key] for key in sorted(files))
        digest = content_digest(
            canonical_json({f.path: content_digest(f.content) for f in ordered}).encode()
        )
        legacy = (
            {"supported_levels": manifest["supported_levels"]}
            if "supported_levels" in manifest
            else {}
        )
        return PackSnapshot(
            identifier,
            package_version,
            minimum,
            tuple(dict.fromkeys((identifier, *block["provides"]))),
            requires,
            tuple(block.get("conflicts", [])),
            tuple(manifest.get("supported_project_types", [])),
            tuple(block.get("agents", sorted(AGENT_LAYOUTS))),
            skills,
            checks,
            ordered,
            digest,
            source_kind,
            root,
            legacy,
        )
    except (DocumentError, OSError, InvalidVersion, InvalidSpecifier, TypeError, KeyError) as exc:
        raise PackError(f"Invalid pack {root.name}: {exc}") from exc


def bundled_catalog() -> tuple[PackSnapshot, ...]:
    return tuple(
        load_pack(p.parent, source_kind="bundled")
        for p in sorted(paths.EXTENSION_PACKS_DIR.glob("*/manifest.yaml"))
    )
