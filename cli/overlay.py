#!/usr/bin/env python3
# Copyright 2026 Accelerated Innovation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
"""Stack overlay loader.

PR 2 / Chunk D. Stacks live at cli/stacks/<id>/overlay.yaml + the docs that
overlay declares. This module is the single source of truth for resolving
stacks; `govkit apply --stack`, `govkit stack list`, and `govkit stack
apply` all consume it.
"""

from dataclasses import dataclass, field
from pathlib import Path

import yaml


# STACKS_DIR resolves to the bundled cli/stacks/ directory, mirroring how
# AGENTS_DIR resolves AGENTS in cli/govkit.py. The repo-checkout vs
# pip-install fallback handles both layouts.
_HERE = Path(__file__).parent
STACKS_DIR = _HERE / "stacks" if (_HERE / "stacks").exists() else _HERE.parent / "cli" / "stacks"

_OVERLAY_FILE = "overlay.yaml"


@dataclass
class Overlay:
    """A loaded stack overlay.

    `root` points at the cli/stacks/<id>/ directory so callers can resolve
    `docs[].src` relative to it.
    """
    id: str
    root: Path
    version: str
    display_name: str
    summary: str
    default_assumptions: list = field(default_factory=list)
    docs: list = field(default_factory=list)
    skill_context: dict = field(default_factory=dict)
    review_checklist: list = field(default_factory=list)


def _parse_overlay_yaml(overlay_path: Path) -> dict | None:
    try:
        text = overlay_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError:
        return None
    if not isinstance(data, dict):
        return None
    return data


def _build_overlay(stack_dir: Path) -> Overlay | None:
    overlay_path = stack_dir / _OVERLAY_FILE
    if not overlay_path.is_file():
        return None
    data = _parse_overlay_yaml(overlay_path)
    if data is None:
        return None
    # Required fields:
    ov_id = data.get("id")
    version = data.get("version")
    display_name = data.get("display_name")
    if not (isinstance(ov_id, str) and isinstance(version, str) and isinstance(display_name, str)):
        return None
    return Overlay(
        id=ov_id,
        root=stack_dir,
        version=version,
        display_name=display_name,
        summary=data.get("summary", ""),
        default_assumptions=data.get("default_assumptions") or [],
        docs=data.get("docs") or [],
        skill_context=data.get("skill_context") or {},
        review_checklist=data.get("review_checklist") or [],
    )


def load_overlay(stack_id: str) -> Overlay | None:
    """Load a single overlay by id. Returns None if absent or malformed."""
    if not stack_id:
        return None
    stack_dir = STACKS_DIR / stack_id
    if not stack_dir.is_dir():
        return None
    return _build_overlay(stack_dir)


def list_overlays() -> list[Overlay]:
    """Enumerate every bundled overlay, sorted by id."""
    if not STACKS_DIR.is_dir():
        return []
    overlays: list[Overlay] = []
    for entry in sorted(STACKS_DIR.iterdir()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        ov = _build_overlay(entry)
        if ov is not None:
            overlays.append(ov)
    return overlays


def apply_overlay(
    overlay: Overlay,
    target: Path,
    applied_at: str | None = None,
    force: bool = False,
) -> list[Path]:
    """Copy an overlay's docs into the target repo.

    Each doc in `overlay.docs` is read from `overlay.root / src` and written
    to `target / dest`. Stack docs carry a baseline header of
    `<overlay.id>@<overlay.version>` so doctor's D006 (stale baseline) can
    detect when an overlay has been updated since the team last applied.

    Edit-protection (A2) is honored: if a target doc is user-edited since
    `applied_at`, the copy is refused unless `force=True`.

    Returns the list of destination paths that were copied.
    """
    from .govkit import copy_entry  # local import to avoid cycle

    baseline = f"{overlay.id}@{overlay.version}"
    copied: list[Path] = []
    for doc in overlay.docs:
        src = overlay.root / doc["src"]
        dest = target / doc["dest"]
        if not src.is_file():
            # Overlay metadata claims a file that isn't present in the
            # bundle. Skip silently so a missing file in one stack doesn't
            # break the whole apply. doctor (PR 4) will surface it.
            continue
        before = dest.exists() and dest.stat().st_mtime
        copy_entry(
            src, dest,
            applied_at=applied_at,
            force=force,
            header_baseline=baseline,
        )
        after = dest.exists() and dest.stat().st_mtime
        # The file was copied if it didn't exist before OR mtime advanced.
        if not before or (after and after != before):
            copied.append(dest)
    return copied
