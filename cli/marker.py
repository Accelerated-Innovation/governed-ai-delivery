#!/usr/bin/env python3
# Copyright 2026 Accelerated Innovation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
"""The .govkit marker — read/write/migrate plus one-time migration warnings.

The marker (`.govkit/marker.json`) is the source of truth for the applied
agent, level, options, stack, assumptions, and calibration state. This module
owns its on-disk format and the version/layout-migration warnings that fire
when an older marker is read. It depends only on the version kernel
(cli/version.py) so commands and sibling modules can import it inward without
cycles.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from . import version

MARKER_DIRNAME = ".govkit"
MARKER_FILENAME = "marker.json"


# ---------------------------------------------------------------------------
# Version comparison + one-time migration warnings (v0.7.0 swap onward)
# ---------------------------------------------------------------------------

@dataclass
class _OneTimeWarning:
    """A stderr warning that fires at most once per process, suppressible
    via an env var (checked at warn time, so module-level instances respect
    env changes made after import). An env-suppressed call leaves the
    warning armed. Each migration warning declares one instance; tests
    re-arm between cases via reset().
    """
    env_var: str
    printed: bool = False

    def warn(self, message: str) -> None:
        if self.printed or os.environ.get(self.env_var) == "1":
            return
        print(message, file=sys.stderr)
        self.printed = True

    def reset(self) -> None:
        self.printed = False


_VERSION_MIGRATION_WARNING = _OneTimeWarning("GOVKIT_NO_MIGRATION_WARNING")
_SHAPE_MIGRATION_WARNING = _OneTimeWarning("GOVKIT_NO_SHAPE_MIGRATION_WARNING")
_DIRECTORY_MIGRATION_WARNING = _OneTimeWarning("GOVKIT_NO_DIRECTORY_MIGRATION_WARNING")


def _compare_version(v1: str, v2: str) -> int:
    """Compare dotted version strings. Returns -1, 0, or 1.

    Non-parseable versions (e.g. 'dev', 'unknown') compare equal to anything,
    so development builds and corrupt markers don't trigger the migration
    warning.
    """
    try:
        t1 = tuple(int(p) for p in v1.split("."))
        t2 = tuple(int(p) for p in v2.split("."))
    except (ValueError, AttributeError):
        return 0
    if t1 < t2:
        return -1
    if t1 > t2:
        return 1
    return 0


def _maybe_warn_migration(stored_version: str | None) -> None:
    """Print one-time migration warning if marker version is pre-0.7.0.

    Suppressed by env var GOVKIT_NO_MIGRATION_WARNING=1 (for CI / scripts).
    Auto-suppressed once the marker is rewritten with version >= 0.7.0
    (because the version comparison stops triggering).
    """
    if not stored_version:
        return
    if _compare_version(stored_version, "0.7.0") < 0:
        _VERSION_MIGRATION_WARNING.warn(
            f"warning: .govkit marker version {stored_version} detected. "
            "The L3/L4 maturity model changed in 0.7.0. "
            "Run 'govkit upgrade --migrate-levels' to migrate. "
            "(Set GOVKIT_NO_MIGRATION_WARNING=1 to suppress.)"
        )


def _reset_migration_warning() -> None:
    """Test helper: re-arm the one-time warning between test cases."""
    _VERSION_MIGRATION_WARNING.reset()


def _maybe_warn_shape_migration(options: dict | None) -> None:
    """Print one-time warning when the marker carries the dropped `ui` option.

    The 0.7→0.8 project-shape refactor removed the `ui` dimension; the marker
    is read tolerantly so existing installs keep working, but the user is
    informed once per process. Suppressible via
    GOVKIT_NO_SHAPE_MIGRATION_WARNING=1.
    """
    if not options or "ui" not in options:
        return
    _SHAPE_MIGRATION_WARNING.warn(
        "warning: .govkit marker carries the legacy 'ui' option. "
        "The project-shape model changed in 0.8.0. The `ui` option is no "
        "longer supported. Re-run 'govkit apply --type ui-react' (or "
        "'ui-angular') to switch to a UI shape, or 'govkit apply --type api' "
        "to keep the current backend shape. "
        "(Set GOVKIT_NO_SHAPE_MIGRATION_WARNING=1 to suppress.)"
    )


def _reset_shape_migration_warning() -> None:
    """Test helper: re-arm the one-time shape-migration warning."""
    _SHAPE_MIGRATION_WARNING.reset()


def _maybe_warn_directory_migration() -> None:
    """Print one-time warning when a legacy single-file .govkit marker is
    detected and auto-migrated to the new .govkit/ directory layout.

    The 0.9→0.10 layout refactor turns .govkit (file) into .govkit/
    (directory) holding marker.json + skill_context.yaml. Legacy markers
    are read tolerantly and migrated on first read. Suppressible via
    GOVKIT_NO_DIRECTORY_MIGRATION_WARNING=1.
    """
    _DIRECTORY_MIGRATION_WARNING.warn(
        "warning: legacy single-file .govkit marker detected — "
        "the layout changed in 0.10.0 and is now .govkit/ (directory) "
        "containing marker.json. Govkit auto-migrated this marker; no "
        "action required. "
        "(Set GOVKIT_NO_DIRECTORY_MIGRATION_WARNING=1 to suppress.)"
    )


def _reset_directory_migration_warning() -> None:
    """Test helper: re-arm the one-time directory-migration warning."""
    _DIRECTORY_MIGRATION_WARNING.reset()


# ---------------------------------------------------------------------------
# .govkit marker read / write / migrate
# ---------------------------------------------------------------------------

def read_govkit_level(target: Path) -> str | None:
    """Read the maturity level from the .govkit marker file, or None if not found.

    Delegates to read_govkit_marker so the one-time migration warning fires
    from any command that reads the level (cmd_init, cmd_validate, etc.).
    """
    data = read_govkit_marker(target)
    return data.get("level") if data else None


def read_govkit_marker(target: Path) -> dict | None:
    """Read the full .govkit marker dict, or None if missing or unreadable.

    Layout: .govkit/marker.json (current) OR a legacy single .govkit file
    (pre-0.10). Legacy files are read tolerantly and migrated to the new
    directory layout in-place on first read.

    Side effects: emits one-time stderr warnings for
      - pre-0.10 layout (file → directory migration)
      - pre-0.7 maturity-model marker (L3/L4 swap)
      - legacy `ui` option (0.7 → 0.8 shape refactor)
    Each warning is independently suppressible via env var.
    """
    marker_node = target / MARKER_DIRNAME
    # Recovery: if a prior migration crashed after backing up the legacy file
    # but before renaming the new dir into place, restore the backup as the
    # legacy file so the normal legacy-read branch below picks it up.
    backup_node = target / ".govkit.legacy.bak"
    if backup_node.is_file() and not marker_node.exists():
        try:
            backup_node.rename(marker_node)
        except OSError:
            pass

    if not marker_node.exists():
        return None

    # New layout: .govkit/ directory containing marker.json
    if marker_node.is_dir():
        marker_path = marker_node / MARKER_FILENAME
        if not marker_path.is_file():
            return None
        try:
            data = json.loads(marker_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        _maybe_warn_migration(data.get("version"))
        _maybe_warn_shape_migration(data.get("options"))
        return data

    # Legacy layout: .govkit is a single file. Read, then migrate.
    if marker_node.is_file():
        try:
            data = json.loads(marker_node.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        _maybe_warn_directory_migration()
        _migrate_legacy_marker_to_directory(target, marker_node, data)
        _maybe_warn_migration(data.get("version"))
        _maybe_warn_shape_migration(data.get("options"))
        return data

    return None


def _migrate_legacy_marker_to_directory(target: Path, marker_node: Path, data: dict) -> None:
    """Best-effort, durable migration from legacy single-file .govkit to
    .govkit/marker.json. Sequence is ordered so a crash at any step leaves
    the repo with a recoverable marker (legacy file OR backup), never nothing.

    Sequence:
      1. Remove any stale .govkit.migrate.tmp/ from a prior failed attempt.
      2. Write new marker.json into .govkit.migrate.tmp/.
      3. Move the legacy file to .govkit.legacy.bak (atomic on POSIX/NTFS).
      4. Move .govkit.migrate.tmp/ into .govkit/ (the now-vacant slot).
      5. Delete .govkit.legacy.bak (best-effort; harmless leftover if it stays).

    A failure between (3) and (4) leaves the backup on disk; the recovery
    branch at the top of read_govkit_marker restores it on the next read.
    Failures elsewhere leave the legacy file intact.
    """
    tmp_dir = target / ".govkit.migrate.tmp"
    backup = target / ".govkit.legacy.bak"
    try:
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)
        tmp_dir.mkdir(parents=True)
        (tmp_dir / MARKER_FILENAME).write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8",
        )
        # Drop any orphan backup from a prior crash before we create a new one.
        if backup.exists():
            try:
                backup.unlink()
            except OSError:
                pass
        marker_node.rename(backup)        # legacy file → backup
        tmp_dir.rename(marker_node)       # tmp dir   → final .govkit/
        try:
            backup.unlink()               # cleanup; safe to leave if this fails
        except OSError:
            pass
    except OSError:
        # Best-effort cleanup so we don't accrue migrate.tmp dirs on retry.
        if tmp_dir.exists():
            try:
                shutil.rmtree(tmp_dir)
            except OSError:
                pass
        return


def write_govkit_marker(
    target: Path,
    agent: str,
    level: str,
    options: dict,
    stack: dict | None = None,
    assumptions: list | None = None,
    calibration: dict | None = None,
    applied_at: str | None = None,
) -> dict:
    """Write the .govkit/marker.json file to track the applied configuration.

    The marker is the source of truth for `agent`, `level`, `options`, the
    selected `stack`, declared `assumptions`, and `calibration` state.
    PR 1 exposes the slots; PR 2 (stack), PR 3 (assumptions), and PR 5
    (calibration) populate them.

    `applied_at` defaults to now — that's what `apply`, `upgrade`, and
    `stack apply` want. Calibrate (PR 5) passes the original applied_at so
    edit-protection isn't silently weakened by every calibration pass.

    If a legacy single-file .govkit marker exists at the target, it is
    removed first so the directory can take its place.

    Returns the marker dict that was just written so callers can hand it to
    `_post_install_finalize` instead of re-reading + re-parsing it from disk.
    """
    marker_dir = target / MARKER_DIRNAME
    # Replace any legacy single-file marker.
    if marker_dir.is_file():
        marker_dir.unlink()
    marker_dir.mkdir(parents=True, exist_ok=True)

    data = {
        "version": version.GOVKIT_VERSION,
        "level": level,
        "agent": agent,
        "options": {k: v for k, v in options.items() if k != "level"},
        "applied_at": applied_at or datetime.now(timezone.utc).isoformat(),
        "stack": stack,
        "assumptions": assumptions if assumptions is not None else [],
        "calibration": calibration if calibration is not None else {
            "completed_at": None,
            "decisions": [],
        },
    }
    (marker_dir / MARKER_FILENAME).write_text(
        json.dumps(data, indent=2) + "\n", encoding="utf-8"
    )
    print(f"\n  .govkit/marker.json written (level {level}, govkit {version.GOVKIT_VERSION})")
    return data
