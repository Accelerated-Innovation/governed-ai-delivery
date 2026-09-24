# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Explicit legacy migration composed from discovery, profiles, packs and checks."""

from __future__ import annotations

import base64
import tempfile
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

from packaging.version import InvalidVersion, Version

from . import migration_store as store
from .check_adapters import read_marker_snapshot
from .check_models import Identity, State
from .conformance import inspect_repository
from .discovery_scan import scan_repository
from .legacy_resolution import adapt_legacy_manifest
from .manifest import load_manifest
from .pack_loading import bundled_catalog
from .pack_store import apply_install, preview_install, verified_lock_document
from .profile_store import apply_profile, preview_materialization
from .profiles import load_profile, parse_profile
from .schema_validation import (
    DocumentError,
    canonical_json,
    content_digest,
    parse_document,
    read_document,
    validate_document,
)
from .version import GOVKIT_VERSION

SOURCE = ".govkit/migration-source.json"
RECEIPT = ".govkit/migration.json"
METADATA = {SOURCE, ".govkit/profile.yaml", ".govkit/resolution.json", ".govkit/pack-lock.json"}


@dataclass(frozen=True)
class MigrationPreview:
    target: Path
    profile_path: Path | None
    snapshot: store.Snapshot
    additions: dict[str, store.FileState]
    _document: dict

    @property
    def document(self):
        return deepcopy(self._document)

    @property
    def digest(self):
        return self._document["digest"]

    def to_json(self):
        return canonical_json(self._document)


def _draft(target, snapshot, marker):
    decisions = []
    try:
        if Version(marker.get("version", "")) < Version("0.7.0"):
            decisions.append(
                "Run the existing upgrade --migrate-levels flow before translating pre-0.7 level meanings."
            )
    except InvalidVersion:
        decisions.append("Reconcile the unknown legacy version before migration.")
    options = {**marker.get("options", {}), "level": marker["level"]}
    for option in sorted(options.keys() - {"type", "ci", "level", "stack", "ui"}):
        decisions.append(f"Reconcile unsupported legacy option {option} before migration.")
    stack = marker.get("stack") or {}
    if not isinstance(stack, dict):
        raise DocumentError("Unsupported legacy stack metadata")
    if stack.get("id"):
        options["stack"] = stack["id"]
    if "ui" in options:
        decisions.append(
            "Reconcile the obsolete ui option with the existing legacy shape migration."
        )
    agent = marker.get("agent")
    if agent not in {"codex", "claude-code", "copilot"}:
        raise DocumentError("Reconcile the unsupported legacy agent before migration")
    legacy = adapt_legacy_manifest(load_manifest(agent), options)
    checks = ["legacy:doctor", "legacy:approval-policy", "migration:legacy-controls"]
    if marker["level"] != "3":
        checks.append("legacy:features")
    if any(p.startswith("extensions/") for p in snapshot.files):
        checks.extend(("legacy:extensions", "migration:custom-controls"))
    if options.get("ci") not in (None, "none") or any(
        p.startswith(".github/workflows/") or p.startswith("ci/") or p.startswith("azure-pipelines")
        for p in snapshot.files
    ):
        checks.append("migration:ci-enforcement")
    if marker.get("authority"):
        checks.append("migration:authority")
    contracts = sorted(
        p
        for p in snapshot.files
        if p.endswith(".md") and ("/architecture/" in p or p.startswith("architecture/"))
    )
    source = {"reference": SOURCE, "authority": "accepted"}
    profile = {
        "schema_version": 1,
        "source": source,
        "repository": {
            "id": target.name,
            "project_type": options.get("type"),
            "stack": options.get("stack"),
        },
        "integrations": {"agent": agent, "ci": options.get("ci")},
        "capabilities": [{"id": c.id} for c in legacy.capabilities],
        "policy": {
            "source": source,
            "workflows": [
                {
                    "id": "legacy-migration",
                    "source": source,
                    "when": ["*"],
                    "additional_checks": checks,
                }
            ],
            "contracts": [
                {"source": {"reference": p, "authority": "accepted"}, "scope": ["."]}
                for p in contracts
            ],
        },
    }
    parse_profile(profile)
    selection = [{"path": a.destination, "ownership": a.ownership.value} for a in legacy.artifacts]
    return profile, decisions, selection


def _legacy_checks(profile):
    checks = {c["id"] for c in profile["policy"].get("required_checks", [])}
    for rule in profile["policy"].get("workflows", []):
        if "*" in rule["when"]:
            checks.update(rule.get("additional_checks", []))
    return sorted(checks)


def _control_inventory(identifiers, report):
    states = {r.spec.id: r.outcome.state.value for r in report.results}
    return [
        {"id": c, "configured": True, "active": "unknown", "local_state": states.get(c, "unknown")}
        for c in sorted(set(identifiers))
    ]


def _retained(draft, profile):
    decisions = []
    if not {c["id"] for c in draft["capabilities"]} <= {c["id"] for c in profile["capabilities"]}:
        decisions.append(
            "Retain all configured legacy capabilities; migration cannot remove requirements."
        )
    if not set(_legacy_checks(draft)) <= set(_legacy_checks(profile)):
        decisions.append("Retain all legacy control obligations, including unverified enforcement.")
    actual = profile["policy"].get("contracts", [])
    if any(c not in actual for c in draft["policy"]["contracts"]):
        decisions.append(
            "Retain existing contract references and scopes; architecture changes need a separate decision."
        )
    if (
        profile.get("integrations") != draft["integrations"]
        or profile["repository"] != draft["repository"]
    ):
        decisions.append("Retain legacy repository/agent/CI/stack identity during migration.")
    return decisions


def _finish(document):
    document["digest"] = content_digest(canonical_json(document).encode())
    validate_document(document, "migration-preview")
    return document


def _receipt(target, snapshot):
    record = read_document(target / RECEIPT)
    validate_document(record, "migration-receipt")
    lock = verified_lock_document(target)
    expected = set(lock["files"]) | METADATA
    if set(record["created"]) != expected or set(record["preserved"]) & expected:
        raise DocumentError("Migration ownership differs from verified pack/profile resources")
    if load_profile(target / ".govkit/profile.yaml").digest != record["profile_digest"]:
        raise DocumentError("Migrated profile changed; reconcile before rollback")
    for name, value in record["created"].items():
        if (
            name not in snapshot.files
            or {
                "digest": content_digest(snapshot.files[name].content),
                "mode": snapshot.files[name].mode,
            }
            != value
        ):
            raise DocumentError("Migrated resources were changed; reconcile before rollback")
    original = record["original_marker"]
    if original["path"] not in {".govkit", ".govkit/marker.json"}:
        raise DocumentError("Invalid original marker path")
    return record


def preview_migration(target: Path, *, profile_path: Path | None = None) -> MigrationPreview:
    target = target.absolute()
    profile_path = profile_path.absolute() if profile_path else None
    snapshot = store.capture(target)
    if RECEIPT in snapshot.files:
        record = _receipt(target, snapshot)
        profile = load_profile(target / ".govkit/profile.yaml")
        if profile_path and load_profile(profile_path).digest != profile.digest:
            raise DocumentError("Migration already applied with a different profile")
        verification = inspect_repository(target)
        document = _finish(
            {
                "schema_version": 1,
                "kind": "migration-preview",
                "target": str(target),
                "migration_id": record["migration_id"],
                "input_digest": snapshot.digest,
                "acceptance": "supplied",
                "proposed_profile": profile.document,
                "ready": True,
                "decisions": [],
                "operations": [],
                "controls": _control_inventory(_legacy_checks(profile.document), verification),
                "enforcement_parity": False,
                "discovery": [],
                "discovery_coverage": {
                    "complete": False,
                    "limitations": ["Already migrated; run discover for fresh evidence."],
                },
                "local_verification": verification.to_document(),
                "profile_source_digest": content_digest(profile_path.read_bytes())
                if profile_path
                else None,
            }
        )
        return MigrationPreview(target, profile_path, snapshot, {}, document)
    if any(p in snapshot.files for p in METADATA):
        raise DocumentError("Existing declarative metadata is protected; reconcile separately")
    marker = read_marker_snapshot(target)
    if marker is None:
        raise DocumentError("Migration requires an existing legacy marker")
    draft, decisions, selection = _draft(target, snapshot, marker)
    profile_bytes = (
        profile_path.read_bytes() if profile_path else (canonical_json(draft) + "\n").encode()
    )
    profile = parse_profile(parse_document(profile_bytes))
    decisions.extend(_retained(draft, profile.document))
    if profile_path is None:
        decisions.append(
            "Review proposed_profile and supply an explicit accepted --profile before applying."
        )
    additions, operations = {}, []
    with tempfile.TemporaryDirectory(prefix="govkit-migration-preview-") as directory:
        shadow = Path(directory) / target.name
        store.materialize(shadow, snapshot)
        scan = scan_repository(shadow)
        before = inspect_repository(target, identity=Identity(draft["repository"]["id"]))
        if (shadow / ".govkit").is_file():
            original = snapshot.files[".govkit"]
            (shadow / ".govkit").unlink()
            (shadow / ".govkit").mkdir()
            (shadow / ".govkit/marker.json").write_bytes(original.content)
            additions[".govkit/marker.json"] = original
            operations.append(
                {"path": ".govkit/marker.json", "action": "relocate", "from": ".govkit"}
            )
        source = {
            "schema_version": 1,
            "kind": "legacy-migration-source",
            "marker": marker,
            "current_manifest_selection": selection,
            "input_digest": snapshot.digest,
            "preserved_paths": sorted(snapshot.files),
            "limitations": "Accepted migration retains configured obligations; installation and local checks are not enforcement parity.",
        }
        (shadow / SOURCE).write_text(canonical_json(source) + "\n")
        accepted = Path(directory) / "profile.json"
        accepted.write_bytes(profile_bytes)
        metadata = preview_materialization(accepted, shadow)
        packs = preview_install(accepted, shadow, bundled_catalog(), govkit_version=GOVKIT_VERSION)
        operations.extend({"path": op.path, "action": op.action} for op in metadata.operations)
        operations.extend(op.summary() for op in packs.operations)
        decisions.extend(d.message for d in metadata.resolution.plan.selections.unresolved)
        decisions.extend(d.message for d in packs.resolution.decisions)
        if any(o["action"] == "protected" for o in operations):
            decisions.append("Existing user-owned skill or pack destination is protected.")
        if (
            metadata.resolution.ready
            and packs.resolution.ready
            and not any(o["action"] == "protected" for o in operations)
        ):
            apply_profile(metadata)
            apply_install(packs)
            staged = store.capture(shadow)
            for name, file in staged.files.items():
                if name not in snapshot.files:
                    additions[name] = store.FileState(file.content, file.mode, 0)
            if ".govkit" in snapshot.files:
                additions[".govkit/marker.json"] = snapshot.files[".govkit"]
    controls = _control_inventory(
        set(_legacy_checks(draft)) | set(_legacy_checks(profile.document)), before
    )
    operations.append({"path": SOURCE, "action": "create"})
    operations.append({"path": RECEIPT, "action": "create"})
    document = _finish(
        {
            "schema_version": 1,
            "kind": "migration-preview",
            "target": str(target),
            "migration_id": None,
            "input_digest": snapshot.digest,
            "acceptance": "supplied" if profile_path else "proposed",
            "proposed_profile": profile.document,
            "profile_source_digest": content_digest(profile_bytes) if profile_path else None,
            "ready": not decisions,
            "decisions": decisions,
            "operations": operations,
            "controls": controls,
            "enforcement_parity": False,
            "discovery": [o.document() for o in scan.observations],
            "discovery_coverage": {
                "complete": scan.complete,
                "limitations": list(scan.limitations),
            },
            "local_verification": before.to_document(),
        }
    )
    return MigrationPreview(target, profile_path, snapshot, additions, document)


def _verification(target):
    report = inspect_repository(target)
    obligations = _legacy_checks(load_profile(target / ".govkit/profile.yaml").document)
    states = {r.spec.id: r.outcome.state for r in report.results}
    return {
        "schema_version": 1,
        "kind": "migration-result",
        "applied": True,
        "enforcement_parity": False,
        "verification": report.to_document(),
        "controls": _control_inventory(obligations, report),
        "remaining": sorted(
            c
            for c in states.keys() | set(obligations)
            if states.get(c, State.UNKNOWN) not in {State.PASS, State.NOT_APPLICABLE, State.WAIVED}
        ),
    }


def apply_migration(preview: MigrationPreview):
    try:
        current = preview_migration(preview.target, profile_path=preview.profile_path)
    except (OSError, ValueError) as exc:
        raise DocumentError("Stale or invalid migration inputs; preview again") from exc
    if current.document["migration_id"] == preview.digest and not current.additions:
        return _verification(preview.target)
    if current.digest != preview.digest:
        raise DocumentError("Stale migration preview; inputs or profile changed")
    if not current.document["ready"]:
        raise DocumentError("Migration has unresolved decisions or protected content")
    if not current.additions:
        return _verification(preview.target)
    original_path = ".govkit" if ".govkit" in current.snapshot.files else ".govkit/marker.json"
    original = current.snapshot.files[original_path]
    owned = {p: f for p, f in current.additions.items() if p != ".govkit/marker.json"}
    receipt = {
        "schema_version": 1,
        "kind": "migration-receipt",
        "migration_id": current.digest,
        "profile_digest": parse_profile(current.document["proposed_profile"]).digest,
        "created": {
            p: {"digest": content_digest(f.content), "mode": f.mode} for p, f in owned.items()
        },
        "original_marker": {
            "path": original_path,
            "content": base64.b64encode(original.content).decode(),
            "mode": original.mode,
            "mtime_ns": original.mtime_ns,
        },
        "original_directories": list(current.snapshot.directories),
        "preserved": {p: f.summary() for p, f in current.snapshot.files.items()},
    }
    validate_document(receipt, "migration-receipt")
    additions = {
        **current.additions,
        RECEIPT: store.FileState((canonical_json(receipt) + "\n").encode(), 0o600, 0),
    }
    if (
        current.profile_path
        and content_digest(current.profile_path.read_bytes())
        != current.document["profile_source_digest"]
    ):
        raise DocumentError("Stale accepted profile; preview again")
    store.write_changes(
        preview.target,
        current.snapshot,
        additions,
        removals=(".govkit",) if original_path == ".govkit" else (),
    )
    return _verification(preview.target)


def rollback_migration(target: Path, *, expected_digest: str):
    target = target.absolute()
    snapshot = store.capture(target)
    record = _receipt(target, snapshot)
    if record["migration_id"] != expected_digest:
        raise DocumentError("Rollback requires the exact migration digest")
    removals = list(record["created"]) + [RECEIPT]
    additions = {}
    marker = record["original_marker"]
    if marker["path"] == ".govkit":
        content = base64.b64decode(marker["content"], validate=True)
        if snapshot.files[".govkit/marker.json"].content != content:
            raise DocumentError("Legacy marker was changed; reconcile before rollback")
        removals.append(".govkit/marker.json")
        if any(p.startswith(".govkit/") and p not in removals for p in snapshot.files):
            raise DocumentError("New metadata must be reconciled before restoring a flat marker")
        additions[".govkit"] = store.FileState(content, marker["mode"], marker["mtime_ns"])
    ancestors = {
        p.as_posix() for name in removals for p in Path(name).parents if p.as_posix() != "."
    }
    directories = ancestors - set(record["original_directories"])
    store.write_changes(
        target, snapshot, additions, removals=removals, prune_directories=directories
    )
    return {
        "schema_version": 1,
        "kind": "migration-rollback",
        "migration_id": expected_digest,
        "rolled_back": True,
    }
