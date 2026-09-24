# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Read-only version/resource facts and previews using existing pack operations."""

from __future__ import annotations

import platform
import stat
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

from packaging.version import Version

from . import version
from .change_scope import capture_change
from .pack_loading import contained_file, load_pack, safe_relative
from .pack_store import preview_install, verify_lock
from .profiles import load_resolution, parse_profile
from .release_metadata import parse_metadata, select_candidates, timestamp, validate_source_url
from .schema_validation import (
    DocumentError,
    canonical_json,
    content_digest,
    parse_document,
    validate_document,
)

MAX_FILE_BYTES = 2 * 1024 * 1024


def read_bounded(path: Path):
    with path.open("rb") as stream:
        content = stream.read(MAX_FILE_BYTES + 1)
    if len(content) > MAX_FILE_BYTES:
        raise DocumentError("Metadata/resource exceeds size limit")
    return content


def _observe(target, relative):
    safe_relative(relative)
    current = target
    for part in relative.split("/"):
        current /= part
        if current.is_symlink():
            return None, {"state": "unavailable", "digest": None, "mode": None, "mtime_ns": None}
    try:
        info = current.stat()
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("Not a regular file")
        data = read_bounded(current)
        return data, {
            "state": "present",
            "digest": content_digest(data),
            "mode": stat.S_IMODE(info.st_mode),
            "mtime_ns": info.st_mtime_ns,
        }
    except (FileNotFoundError, NotADirectoryError):
        return None, {"state": "missing", "digest": None, "mode": None, "mtime_ns": None}
    except (OSError, ValueError):
        return None, {"state": "unavailable", "digest": None, "mode": None, "mtime_ns": None}


@dataclass(frozen=True)
class InventoryReport:
    _document: dict

    @property
    def document(self):
        return deepcopy(self._document)

    @property
    def digest(self):
        return self._document["digest"]

    def to_json(self):
        return canonical_json(self._document)


def inventory_repository(target: Path, *, as_of=None, metadata=()):
    target = target.absolute()
    if not target.is_dir() or target.is_symlink():
        raise DocumentError("Inventory target must be a real directory")
    if as_of is not None:
        timestamp(as_of)
    inputs, problems = {}, []
    profile, lock, marker, resolution_digest = None, None, None, None
    profile_resolution = None
    marker_name = ".govkit" if (target / ".govkit").is_file() else ".govkit/marker.json"
    for name, kind in (
        (marker_name, "marker"),
        (".govkit/profile.yaml", "profile"),
        (".govkit/pack-lock.json", "lock"),
        (".govkit/resolution.json", "resolution"),
    ):
        content, observation = _observe(target, name)
        inputs[name] = observation
        if content is None:
            problems.append(f"{kind}:{observation['state']}")
            continue
        try:
            data = parse_document(content)
            if kind == "profile":
                profile = parse_profile(data)
            elif kind == "marker":
                if not isinstance(data, dict) or not isinstance(data.get("version"), str):
                    raise ValueError("Invalid marker version")
                Version(data["version"])
                marker = data["version"]
            elif kind == "lock":
                validate_document(data, "pack-lock")
                if len(data["files"]) > 4096:
                    raise ValueError("Lock resource limit")
                lock = data
            else:
                record = load_resolution(contained_file(target, name))
                if profile and record.profile.digest != profile.digest:
                    raise ValueError("Resolution profile drift")
                if read_bounded(target / name) != content:
                    raise ValueError("Resolution changed while reading")
                resolution_digest = observation["digest"]
                profile_resolution = {
                    "govkit_version": record.govkit_version,
                    "capabilities": [c.id for c in record.plan.selections.capabilities],
                }
        except ValueError:
            problems.append(f"{kind}:invalid")
    resources, total = [], 0
    if lock:
        for name, expected in sorted(lock["files"].items()):
            try:
                if total > 64 * 1024 * 1024:
                    raise ValueError("Inventory byte limit")
                content, observed = _observe(target, name)
                total += len(content) if content else 0
                if total > 64 * 1024 * 1024:
                    raise ValueError("Inventory byte limit")
                inputs[name] = observed
                actual = observed["digest"]
                state = (
                    "matching"
                    if actual == expected
                    else "modified"
                    if actual
                    else observed["state"]
                )
            except ValueError:
                actual, state = None, "unavailable"
                problems.append("resources:incomplete")
            resources.append(
                {
                    "path": name,
                    "owner": lock["owners"].get(name),
                    "expected_digest": expected,
                    "actual_digest": actual,
                    "state": state,
                    "action": {
                        "matching": "none",
                        "missing": "refresh-resources",
                        "modified": "reconcile-customizations",
                        "unavailable": "inspect-resources",
                    }[state],
                }
            )
    verified = verify_lock(target) if lock else None
    lock_status = "verified" if verified and verified.ready else "unverified" if lock else "unknown"
    if lock and lock_status != "verified":
        problems.append("lock:replay-or-resource-verification-failed")
    installed = {p["id"]: p["version"] for p in lock["packs"]} if lock else {}
    installed["govkit"] = version.GOVKIT_VERSION
    supplied, candidates, accepted_metadata = {}, [], []
    if profile:
        for raw in metadata:
            try:
                doc = parse_metadata(raw, profile)
                if doc["source_id"] in supplied:
                    raise DocumentError("Duplicate metadata source")
                supplied[doc["source_id"]] = doc
            except ValueError:
                raise DocumentError("Invalid, duplicated or unapproved release metadata") from None
        for source in profile.maintenance.sources:
            try:
                validate_source_url(source.url)
            except ValueError:
                problems.append(f"metadata:{source.id}:unsupported-source-url")
                continue
            doc = supplied.get(
                source.id,
                {
                    "schema_version": 1,
                    "kind": "release-metadata",
                    "source_id": source.id,
                    "source_url": source.url,
                    "as_of": None,
                    "retrieved_at": None,
                    "lookup_status": "unavailable",
                    "releases": [],
                },
            )
            accepted_metadata.append(doc)
            try:
                candidates.extend(
                    select_candidates(
                        profile,
                        doc,
                        installed=installed,
                        running_govkit=version.GOVKIT_VERSION,
                        python_version=platform.python_version(),
                        as_of=as_of,
                    )
                )
            except ValueError:
                problems.append(f"candidates:{source.id}:invalid-version-policy")
    elif metadata:
        problems.append("metadata:profile-required")
    git = capture_change(target, "HEAD")
    identity = {
        "revision": git.revision,
        "dirty_digest": git.digest if git.complete else None,
        "git_complete": git.complete,
        "profile_digest": profile.digest if profile else None,
        "resolution_digest": resolution_digest,
        "pack_lock_digest": inputs[".govkit/pack-lock.json"]["digest"],
        "input_digest": content_digest(canonical_json(inputs).encode()),
    }
    document = {
        "schema_version": 1,
        "kind": "maintenance-inventory",
        "target": str(target),
        "repository": profile.repository.id if profile else target.name,
        "as_of": as_of,
        "identity": identity,
        "running_cli": version.GOVKIT_VERSION,
        "python_version": platform.python_version(),
        "recorded_install": marker,
        "profile_resolution": profile_resolution,
        "resolved_govkit": lock["govkit_version"] if lock else None,
        "locked_packs": lock["packs"] if lock else [],
        "lock_verification": lock_status,
        "resources": resources,
        "candidates": sorted(candidates, key=lambda c: c["component"]),
        "metadata": accepted_metadata,
        "problems": sorted(set(problems)),
        "limitations": [
            "Inventory is not a consolidated maintenance assessment or enforcement evidence.",
            "Lock ownership/digests remain recorded claims until replay verification succeeds.",
            "Cached/bundled metadata does not prove the latest published release; source records are not authenticated.",
            "Legacy resources without a declarative lock are not measured by this inventory.",
            "Git coverage excludes ignored untracked files and may be incomplete; file reads are not a concurrent transaction.",
        ],
    }
    document["digest"] = content_digest(canonical_json(document).encode())
    validate_document(document, "maintenance-inventory")
    return InventoryReport(document)


def preview_candidate(target: Path, inventory: dict, component: str, *, catalog=()):
    """Re-observe inputs and compose a protected preview, never execute a saved action."""
    validate_document(inventory, "maintenance-inventory")
    recorded = {key: value for key, value in inventory.items() if key != "digest"}
    if content_digest(canonical_json(recorded).encode()) != inventory["digest"]:
        raise DocumentError("Invalid inventory digest; regenerate the record")
    current = inventory_repository(target, as_of=inventory["as_of"], metadata=inventory["metadata"])
    if current.digest != inventory["digest"]:
        raise DocumentError("Stale inventory; refresh it before previewing an operation")
    selection = next(
        (c for c in current.document["candidates"] if c["component"] == component), None
    )
    if selection is None or selection["selected_target"] is None:
        raise DocumentError("No fresh compatible upgrade candidate is selected")
    result = {
        "schema_version": 1,
        "kind": "maintenance-candidate-preview",
        "inventory_digest": current.digest,
        "component": component,
        "target_version": selection["selected_target"],
        "ready": False,
        "operations": [],
        "affected_controls": [],
        "protected_customizations": [],
        "decisions": [],
    }
    if component == "govkit":
        result["decisions"] = [
            "Update the developer CLI through its existing package manager, then rerun inventory; repository resources require separate reviewed pack operations."
        ]
        return result
    chosen = [
        p
        for p in catalog
        if p.id == component and Version(p.version) == Version(selection["selected_target"])
    ]
    if len(chosen) != 1:
        result["decisions"] = [
            "Supply exactly one explicit local candidate pack snapshot; metadata never downloads code."
        ]
        return result
    try:
        target = target.absolute()
        profile_path = contained_file(target, ".govkit/profile.yaml")
        lock_path = contained_file(target, ".govkit/pack-lock.json")
        lock = parse_document(read_bounded(lock_path))
        validate_document(lock, "pack-lock")
        packs = list(chosen)
        for entry in lock["packs"]:
            if entry["id"] != component:
                packs.append(
                    load_pack(
                        target / f".govkit/packs/{entry['id']}/{entry['digest']}",
                        source_kind=entry["source"],
                    )
                )
        preview = preview_install(
            profile_path, target, tuple(packs), govkit_version=version.GOVKIT_VERSION
        )
        result["operations"] = [op.summary() for op in preview.operations]
        result["affected_controls"] = sorted(
            set(lock["checks"])
            | set(preview.resolution.required_checks)
            | {c.id for p in preview.resolution.packs for c in p.checks}
        )
        result["protected_customizations"] = [
            op.path for op in preview.operations if op.action == "protected"
        ]
        result["decisions"] = [d.message for d in preview.resolution.decisions]
        if result["protected_customizations"]:
            result["decisions"].append(
                "Reconcile protected customizations before applying pack operations"
            )
        result["ready"] = preview.resolution.ready and not result["protected_customizations"]
    except (OSError, ValueError):
        result["decisions"] = [
            "Pinned resources cannot be replayed; reconcile them before previewing a replacement."
        ]
    return result
