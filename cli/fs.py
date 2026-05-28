#!/usr/bin/env python3
# Copyright 2026 Accelerated Innovation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
"""Filesystem copy with govkit edit-protection + header injection.

The low-level file/dir copier used by apply, upgrade, stack apply, and init.
It honors the govkit:editable header contract (A2): files a team edited since
the last apply are not clobbered unless force=True. Depends only on the header
helpers (cli/headers.py), so commands and overlays import it inward without a
cycle back through cli/govkit.py.
"""

from __future__ import annotations

import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from .headers import has_editable_header, prepend_header_to_file


def is_user_edited(dest: Path, applied_at: str | None) -> bool:
    """True if `dest` carries a govkit:editable header and was modified after
    the recorded apply time. Used by edit-protection (A2) to avoid clobbering
    team edits during `apply` / `upgrade` / `stack apply`.

    Returns False (no protection triggered) when:
      - applied_at is None or unparseable (no prior install to compare to)
      - dest doesn't exist or isn't a regular file
      - dest has no editable header (was never govkit-managed)
      - dest's mtime is at or before applied_at (no edit since)
    """
    if applied_at is None:
        return False
    if not dest.is_file():
        return False
    try:
        content = dest.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    if not has_editable_header(content):
        return False
    try:
        applied_dt = datetime.fromisoformat(applied_at)
    except (ValueError, TypeError):
        return False
    mtime_dt = datetime.fromtimestamp(dest.stat().st_mtime, tz=timezone.utc)
    return mtime_dt > applied_dt


def _copy_entry_should_refuse(
    dest: Path, applied_at: str | None, force: bool,
) -> bool:
    """Decide whether edit-protection should block overwriting `dest`.

    True ⇒ caller skips. False ⇒ caller proceeds; if force=True and the
    file IS user-edited, a warning is emitted as a side effect.
    """
    if applied_at is None or not dest.is_file() or not is_user_edited(dest, applied_at):
        return False
    if not force:
        print(
            f"  refused {dest}  (user-edited since last apply; "
            "re-run with --force to overwrite)",
            file=sys.stderr,
        )
        return True
    print(
        f"  warning: overwriting user edits at {dest} (--force set)",
        file=sys.stderr,
    )
    return False


def _copy_file(
    src: Path, dest: Path,
    skip_existing: bool, applied_at: str | None, force: bool,
    header_baseline: str | None, header_see: str,
) -> None:
    """Copy a single file with edit-protection + header injection applied."""
    if skip_existing and dest.exists():
        print(f"  skipped {dest}  (already exists)")
        return
    if _copy_entry_should_refuse(dest, applied_at, force):
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    print(f"  copied  {dest}")
    if header_baseline is not None:
        prepend_header_to_file(dest, baseline=header_baseline, see=header_see)


def copy_entry(
    src: Path,
    dest: Path,
    skip_existing: bool = False,
    applied_at: str | None = None,
    force: bool = False,
    header_baseline: str | None = None,
    header_see: str = "GOVKIT_SETUP_REVIEW.md",
    exclude_basenames: set[str] | None = None,
) -> None:
    """Copy a file or directory tree.

    Edit-protection: when `applied_at` is supplied, files at `dest` that
    carry a govkit:editable header and were modified after `applied_at` are
    skipped with a warning unless `force=True`. Pass `applied_at=None` (the
    default) to preserve pre-PR-1 behavior for callers that don't manage
    editable docs.

    Header injection: when `header_baseline` is supplied, every .md file
    successfully copied gets the govkit:editable header prepended (or
    refreshed) afterwards. Used by governed/shared paths in apply/upgrade so
    doc baselines stay in sync. Files skipped (existed when skip_existing was
    set, or refused by edit-protection) do not get the header touched.

    Exclusion (PR 6c): when `exclude_basenames` is supplied, files whose
    basename matches are silently skipped. Used by L5-only governed docs
    (AGENT_ARCHITECTURE.md, LLM_GATEWAY_CONTRACT.md, etc.) to keep them
    out of L3/L4 installs without restructuring the source tree.
    """
    if not src.exists():
        print(f"Error: source path does not exist: {src}")
        sys.exit(1)
    if exclude_basenames and src.name in exclude_basenames and src.is_file():
        return
    if src.is_dir():
        dest.mkdir(parents=True, exist_ok=True)
        for item in src.iterdir():
            copy_entry(
                item, dest / item.name,
                skip_existing=skip_existing,
                applied_at=applied_at,
                force=force,
                header_baseline=header_baseline,
                header_see=header_see,
                exclude_basenames=exclude_basenames,
            )
        return
    _copy_file(src, dest, skip_existing, applied_at, force, header_baseline, header_see)
