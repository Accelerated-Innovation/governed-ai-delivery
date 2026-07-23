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

from .headers import (
    compute_body_hash,
    has_editable_header,
    parse_editable_header,
    prepend_header_to_file,
)


def is_user_edited(dest: Path, applied_at: str | None) -> bool:
    """True if `dest` carries a govkit:editable header and its body no longer
    matches the content govkit installed. Used by edit-protection (A2) to
    avoid clobbering team edits during `apply` / `upgrade` / `stack apply`.

    Headers written since the hash field exists record the installed body's
    SHA-256; the file is user-edited iff the current body hash differs.
    Timestamps play no part — a re-stamped applied_at (upgrade, stack apply)
    or a fresh clone's new mtimes cannot flip the answer. Headers without a
    `hash:` field (pre-hash installs, or a header the user broke) fall back
    to the mtime-vs-applied_at comparison.

    Returns False (no protection triggered) when:
      - applied_at is None (no prior install; protection is off) — for the
        hash path this is purely an enable flag, not a timestamp
      - dest doesn't exist or isn't a regular file
      - dest has no editable header (was never govkit-managed)
      - the recorded hash matches the current body, or on the fallback path
        the mtime is at or before applied_at / applied_at is unparseable
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
    fields = parse_editable_header(content)
    if fields is not None and "hash" in fields:
        return compute_body_hash(content) != fields["hash"]
    try:
        applied_dt = datetime.fromisoformat(applied_at)
    except (ValueError, TypeError):
        return False
    # A timezone-naive applied_at cannot be compared to the aware UTC mtime
    # without TypeError; treat it as unknown history (no protection), same as
    # install_common._unmodified_since. The comparison is also wrapped as a
    # final safety net.
    if applied_dt.tzinfo is None:
        return False
    mtime_dt = datetime.fromtimestamp(dest.stat().st_mtime, tz=timezone.utc)
    try:
        return mtime_dt > applied_dt
    except TypeError:
        return False


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
        # A refused pre-hash file keeps mtime-only protection, which a future
        # upgrade's applied_at re-stamp resets — warn about the window.
        try:
            fields = parse_editable_header(dest.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError):
            fields = None
        if not fields or "hash" not in fields:
            print(
                f"  note: {dest} predates content-hash protection; its edits "
                "stay protected only until the next upgrade or stack apply — "
                "merge them or re-run with --force before then",
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

    Exclusion: when `exclude_basenames` is supplied, files whose basename
    matches are silently skipped. This is available to callers that need to
    omit selected bundled files while preserving the source tree.
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
