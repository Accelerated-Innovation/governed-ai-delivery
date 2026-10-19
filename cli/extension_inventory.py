# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Read-only inventory of installed extensions in a target project.

Legacy installs live under `extensions/<id>/`; declarative packs live under
`.govkit/packs/<id>/<digest>/` and are trusted only through the verified pack
lock. The inventory lists both with repository-relative resource paths and
reports copies that conflict. It never migrates, deletes or rewrites anything,
and an installed resource is guidance, not accepted project policy.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .extensions import discover_extensions, load_manifest, validate_extension
from .pack_loading import PackError
from .pack_store import verified_lock_document
from .schema_validation import DocumentError, read_document

_LOCK = Path(".govkit") / "pack-lock.json"
_PACKS = Path(".govkit") / "packs"

LIMITATIONS = (
    "Installed guidance is not accepted project policy.",
    "Lock verification shows pinned bytes are unchanged; it does not authenticate a publisher.",
)


@dataclass(frozen=True)
class InstalledExtension:
    id: str
    version: str | None
    source: str
    root: str
    status: str
    contract_sets: tuple[dict, ...]
    resources: tuple[str, ...]
    issues: tuple[str, ...] = ()

    @property
    def usable(self) -> bool:
        return self.status in ("valid", "verified")

    def to_document(self) -> dict:
        return {
            "id": self.id,
            "version": self.version,
            "source": self.source,
            "root": self.root,
            "status": self.status,
            "contract_sets": [dict(cs) for cs in self.contract_sets],
            "resources": list(self.resources),
            "issues": list(self.issues),
        }


@dataclass(frozen=True)
class Conflict:
    kind: str
    extension: str
    roots: tuple[str, ...]
    message: str

    def to_document(self) -> dict:
        return {
            "kind": self.kind,
            "extension": self.extension,
            "roots": list(self.roots),
            "message": self.message,
        }


@dataclass(frozen=True)
class Inventory:
    extensions: tuple[InstalledExtension, ...]
    conflicts: tuple[Conflict, ...]
    lock: str

    @property
    def ready(self) -> bool:
        return not self.conflicts and all(e.usable for e in self.extensions)

    def conflicts_for(self, extension_id: str) -> list[str]:
        return sorted({c.kind for c in self.conflicts if c.extension == extension_id})

    def to_document(self) -> dict:
        return {
            "schema_version": 1,
            "kind": "extension-inventory",
            "lock": self.lock,
            "ready": self.ready,
            "extensions": [e.to_document() for e in self.extensions],
            "conflicts": [c.to_document() for c in self.conflicts],
            "limitations": list(LIMITATIONS),
        }


def installed_extensions(target: Path) -> Inventory:
    """Observe legacy and declarative installs under `target` without writing."""
    target = target.absolute()
    legacy = [_legacy_entry(target, ext) for ext in discover_extensions(target)]
    lock_state, declarative, pinned_roots = _declarative_entries(target)
    conflicts = []
    legacy_ids = {e.id: e for e in legacy}
    for entry in declarative:
        other = legacy_ids.get(entry.id)
        if other is not None:
            conflicts.append(
                Conflict(
                    "legacy-and-declarative",
                    entry.id,
                    (other.root, entry.root),
                    f"{entry.id} is installed at {other.root} (version {other.version}) and at "
                    f"{entry.root} (version {entry.version}); keep one copy",
                )
            )
    for orphan in _pack_directories(target) - pinned_roots:
        extension = orphan.split("/")[2]
        conflicts.append(
            Conflict(
                "orphan-pack-directory",
                extension,
                (orphan,),
                f"{orphan} is not recorded in the pack lock",
            )
        )
    extensions = sorted([*legacy, *declarative], key=lambda e: (e.id, e.source))
    conflicts.sort(key=lambda c: (c.extension, c.kind, c.roots))
    return Inventory(tuple(extensions), tuple(conflicts), lock_state)


def _manifest_view(manifest: dict, root: str, folder: Path) -> tuple[tuple, tuple]:
    contract_sets, resources = [], []
    for contract_set in manifest.get("contract_sets") or []:
        paths = [f"{root}/{p}" for p in contract_set.get("paths") or []]
        contract_sets.append(
            {
                "id": contract_set["id"],
                "capabilities": list(contract_set.get("capabilities") or []),
                "applies_to": list(contract_set.get("applies_to") or []),
                "paths": paths,
            }
        )
        resources.extend(paths)
    for profile in manifest.get("implementation_profiles") or []:
        resources.append(f"{root}/{profile['path']}")
    readme = folder / "README.md"
    if readme.is_file() and not readme.is_symlink():
        resources.append(f"{root}/README.md")
    return tuple(contract_sets), tuple(dict.fromkeys(resources))


def _legacy_entry(target: Path, ext) -> InstalledExtension:
    root = ext.root.relative_to(target).as_posix()
    issues = tuple(validate_extension(ext, target))
    # As in doctor (D014), relationships to project documents are warnings:
    # the extension's own contracts remain readable before core docs exist.
    if any("relates_to" not in issue for issue in issues):
        return InstalledExtension(
            ext.id, ext.version or None, "legacy", root, "invalid", (), (), issues
        )
    contract_sets, resources = _manifest_view(ext.manifest, root, ext.root)
    return InstalledExtension(
        ext.id, ext.version, "legacy", root, "valid", contract_sets, resources, issues
    )


def _declarative_entries(target: Path) -> tuple[str, list[InstalledExtension], set[str]]:
    if not (target / _LOCK).exists():
        return "absent", [], set()
    try:
        lock = verified_lock_document(target)
        verified = True
    except (PackError, OSError, ValueError):
        verified = False
        try:
            lock = read_document(target / _LOCK)
        except DocumentError:
            return "unverified", [], set()
    entries, roots = [], set()
    for pack in lock.get("packs") or []:
        if not isinstance(pack, dict) or not {"id", "digest"} <= pack.keys():
            continue
        root = f"{_PACKS.as_posix()}/{pack['id']}/{pack['digest']}"
        roots.add(root)
        version = pack.get("version")
        if not verified:
            entries.append(
                InstalledExtension(pack["id"], version, "declarative", root, "unverified", (), ())
            )
            continue
        folder = target / root
        manifest, error = load_manifest(folder / "manifest.yaml")
        if manifest is None:
            entries.append(
                InstalledExtension(
                    pack["id"], version, "declarative", root, "unverified", (), (), (error or "",)
                )
            )
            continue
        contract_sets, resources = _manifest_view(manifest, root, folder)
        entries.append(
            InstalledExtension(
                pack["id"], version, "declarative", root, "verified", contract_sets, resources
            )
        )
    return ("verified" if verified else "unverified"), entries, roots


def _pack_directories(target: Path) -> set[str]:
    base = target / _PACKS
    if not base.is_dir() or base.is_symlink():
        return set()
    found = set()
    for pack in base.iterdir():
        if not pack.is_dir() or pack.is_symlink():
            continue
        for version in pack.iterdir():
            if version.is_dir() and not version.is_symlink():
                found.add(f"{_PACKS.as_posix()}/{pack.name}/{version.name}")
    return found
