#!/usr/bin/env python3
# Copyright 2026 Accelerated Innovation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
"""Shared install helpers used by both `govkit apply` and `govkit upgrade`.

The governed/shared copy loop, the L5-only governed-doc exclusion, and the
post-install finalization (derived files + rule re-templating + checklist) are
common to apply and upgrade. They live here so both command modules import
them inward without duplicating logic or reaching back into cli/govkit.py.
"""

from __future__ import annotations

import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from . import paths
from .fs import copy_entry
from .headers import GOVKIT_BLOCK_BEGIN, upsert_govkit_block
from .marker import _compare_version, read_govkit_marker

if TYPE_CHECKING:
    from .detect import RepoProfile


# A6: govkit used to install its agent instructions at these top-level paths.
# They now live in the auto-loaded rules namespace, so on upgrade an existing
# install carries an orphaned copy. This maps each new governance dest back to
# the legacy path it superseded, so upgrade can retire the orphan.
_LEGACY_INSTRUCTION_DEST = {
    ".claude/rules/govkit/governance.md": "CLAUDE.md",
    ".claude/rules/govkit/governance-src.md": "src/CLAUDE.md",
    ".github/instructions/govkit/governance.instructions.md": ".github/copilot-instructions.md",
}


def _unmodified_since(path: Path, applied_at: str | None) -> bool:
    """True when `path` has not been modified since the marker's `applied_at`.

    govkit wrote the legacy instruction file at apply time, so a file still at
    (or before) that timestamp is govkit's own untouched copy — regardless of
    which govkit version's text it carries. Returns False when `applied_at` is
    missing/unparseable, so an unknown history never authorizes a delete.

    A timezone-naive `applied_at` (no offset on disk — markers aren't schema-
    validated) is likewise treated as unknown history: it cannot be compared
    to the timezone-aware UTC mtime without raising TypeError, so it returns
    False rather than crash the caller. The comparison is also wrapped as a
    final safety net.
    """
    if not applied_at:
        return False
    try:
        applied_dt = datetime.fromisoformat(applied_at)
    except (ValueError, TypeError):
        return False
    if applied_dt.tzinfo is None:
        return False
    mtime_dt = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    try:
        return mtime_dt <= applied_dt
    except TypeError:
        return False


def write_managed_agent_block(dest: Path, body: str, applied_at: str | None = None) -> None:
    """Install govkit's governance into `dest` as a managed block.

    For an agent (codex) whose only mechanism is a shared AGENTS.md, govkit
    cannot move its governance elsewhere, so it fences it between markers and
    preserves the team's own content in the same file. When the file already
    exists without a block, it is replaced wholesale only if it is provably
    govkit's own pre-block copy (byte-identical to the governance body, or
    untouched since the marker's `applied_at`); otherwise it is treated as the
    team's and the block is appended below their content.
    """
    existing: str | None = None
    if dest.exists():
        try:
            existing = dest.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            existing = None
    replace_unblocked = False
    if existing is not None and GOVKIT_BLOCK_BEGIN not in existing:
        replace_unblocked = existing == body or _unmodified_since(dest, applied_at)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        upsert_govkit_block(existing, body, replace_unblocked=replace_unblocked),
        encoding="utf-8",
    )
    print(f"  wrote   {dest}  (govkit governance block)")


def install_agent_file(
    agent_dir: Path, entry: dict, target: Path, applied_at: str | None = None,
) -> None:
    """Install one agent-file manifest entry: a managed block when the entry
    opts in (`managed_block`), otherwise a plain overwrite copy."""
    src = agent_dir / entry["src"]
    dest = target / entry["dest"]
    if entry.get("managed_block"):
        write_managed_agent_block(dest, src.read_text(encoding="utf-8"), applied_at)
    else:
        copy_entry(src, dest)


def reconcile_legacy_instruction_files(
    target: Path, agent_dir: Path, files: list, applied_at: str | None = None,
) -> list:
    """Retire a pre-namespace govkit instruction file before writing governance.

    For each governance entry, if the legacy top-level file it superseded is
    present, it is treated as govkit's own untouched orphan — and removed — when
    EITHER:
      - it is byte-identical to govkit's current governance body, or
      - it has not been modified since the marker's `applied_at` (so it is
        govkit's file from an earlier version, untouched by the team).
    Otherwise it is treated as the team's file: kept, and the governance entry
    is dropped so upgrade does not install duplicate governance alongside it. A
    warning tells the team how to adopt the managed layout.

    Returns the files list to actually write. Upgrade-only: on a fresh apply a
    top-level CLAUDE.md is the team's, and governance is expected to coexist.
    """
    keep = []
    for entry in files:
        legacy_rel = _LEGACY_INSTRUCTION_DEST.get(entry["dest"])
        if legacy_rel is None:
            keep.append(entry)
            continue
        legacy = target / legacy_rel
        if not legacy.exists():
            keep.append(entry)
            continue
        govkit_body = (agent_dir / entry["src"]).read_text(encoding="utf-8")
        try:
            legacy_body = legacy.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            legacy_body = None
        is_govkit_orphan = legacy_body == govkit_body or _unmodified_since(legacy, applied_at)
        if is_govkit_orphan:
            try:
                legacy.unlink()
            except OSError as exc:
                # Deletion can fail (permissions, a Windows sharing violation, a
                # read-only mount). Don't crash the upgrade — and don't install
                # the namespaced governance while the legacy copy is still on
                # disk, or the agent would load governance twice.
                print(
                    f"  warning: could not remove legacy {legacy_rel} ({exc}); "
                    f"skipping {entry['dest']} to avoid loading governance twice. "
                    f"Remove {legacy_rel} manually and re-run upgrade to adopt the "
                    "managed governance.",
                    file=sys.stderr,
                )
                continue
            print(f"  migrated {legacy_rel} -> {entry['dest']}  (removed govkit-authored orphan)")
            keep.append(entry)
        else:
            print(
                f"  warning: {legacy_rel} exists and is not govkit's governance; "
                f"leaving it and skipping {entry['dest']} to avoid duplicate governance. "
                f"If it is no longer needed, delete {legacy_rel} and re-run upgrade to "
                "adopt the managed governance.",
                file=sys.stderr,
            )
    return keep


# 0.14.0 moved govkit's own agent files into a namespace govkit owns, so a
# team's same-named rules and skills survive alongside them:
#   .claude/rules/X.md          -> .claude/rules/govkit/X.md
#   .github/instructions/X      -> .github/instructions/govkit/X
#   .claude|.agents/skills/Y/   -> .../skills/govkit-Y/
# Upgrading a pre-0.14 install writes the new paths but leaves govkit's old
# copy behind, and the agent auto-loads both — duplicated and, once the two
# drift, contradictory governance. Both moves are mechanical, so the superseded
# path is derived rather than enumerated per agent.
_NAMESPACE_MIGRATION_VERSION = "0.14.0"


def _superseded_agent_path(dest: str) -> str | None:
    """The pre-namespace path `dest` superseded, or None when `dest` is not a
    namespaced (or `govkit-` prefixed) govkit agent file."""
    if "/govkit/" in dest:
        return dest.replace("/govkit/", "/", 1)
    if "/skills/govkit-" in dest:
        return dest.replace("/skills/govkit-", "/skills/", 1)
    return None


def _tree_unmodified_since(root: Path, applied_at: str | None) -> bool:
    """True when every file under `root` is unmodified since `applied_at`.

    One user-touched file protects the whole directory: a skill the team
    edited is theirs even if they changed only part of it. An empty tree
    returns False — there is nothing to prove ownership with, so it stays.
    """
    contents = [p for p in root.rglob("*") if p.is_file()]
    return bool(contents) and all(_unmodified_since(p, applied_at) for p in contents)


def _is_govkit_pre_namespace_copy(
    legacy: Path, src: Path, applied_at: str | None,
) -> bool:
    """True when `legacy` is provably govkit's own copy rather than the team's.

    A directory qualifies when nothing inside it was touched since the last
    apply. A file qualifies when it is byte-identical to what govkit installs
    today (a same-version orphan) or untouched since the last apply (an older
    govkit version's file the team never edited).
    """
    if legacy.is_dir():
        return _tree_unmodified_since(legacy, applied_at)
    if src.is_file():
        try:
            if legacy.read_text(encoding="utf-8") == src.read_text(encoding="utf-8"):
                return True
        except (OSError, UnicodeDecodeError):
            pass
    return _unmodified_since(legacy, applied_at)


def retire_pre_namespace_agent_files(
    target: Path, agent_dir: Path, files: list,
    applied_at: str | None = None, stored_version: str | None = None,
) -> None:
    """Remove the pre-namespace rules/skills an upgrade would otherwise orphan.

    Runs only while the marker predates the namespace move, so a same-named
    file the team authors at an old path *after* migrating is never a
    candidate. Inside that window a path is removed only when it is provably
    govkit's own (see `_is_govkit_pre_namespace_copy`); anything else is the
    team's and is left untouched — govkit's namespaced copy installs alongside
    it, which is the entire point of the namespace. A failed delete warns and
    never aborts the upgrade.
    """
    if _compare_version(stored_version or "", _NAMESPACE_MIGRATION_VERSION) >= 0:
        return
    for entry in files:
        legacy_rel = _superseded_agent_path(entry["dest"])
        if legacy_rel is None:
            continue
        legacy = target / legacy_rel
        if not legacy.exists():
            continue
        if not _is_govkit_pre_namespace_copy(legacy, agent_dir / entry["src"], applied_at):
            continue
        try:
            if legacy.is_dir():
                shutil.rmtree(legacy)
            else:
                legacy.unlink()
        except OSError as exc:
            print(
                f"  warning: could not remove superseded {legacy_rel} ({exc}); "
                f"it now duplicates {entry['dest']}. Delete {legacy_rel} manually "
                "so the agent does not load both copies.",
                file=sys.stderr,
            )
            continue
        print(f"  retired {legacy_rel}  (superseded by {entry['dest']})")


def copy_governed_or_shared(
    rel_paths: list, target: Path, prior_applied_at: str | None,
    force: bool, baseline: str,
    skip_existing: bool = True,
) -> None:
    """Copy each governed/shared dir from the bundle (REPO_ROOT) to target.

    `features/` entries are deferred — those land via `govkit init`, not
    apply/upgrade. `skip_existing=True` (the default) is correct for `apply`
    governed/shared and for `upgrade` shared. `upgrade` governed passes
    `skip_existing=False` because upgrade re-installs governed contracts.
    """
    for rel in rel_paths:
        if rel.startswith(paths.FEATURES_PREFIX):
            continue
        copy_entry(
            paths.REPO_ROOT / rel, target / rel,
            skip_existing=skip_existing,
            applied_at=prior_applied_at,
            force=force,
            header_baseline=baseline,
        )


def post_install_finalize(
    target: Path, agent: str,
    marker: dict | None = None, profile: RepoProfile | None = None,
) -> None:
    """Write derived files (setup review + skill_context), re-template rule
    globs to match the team's actual layout, print the post-install checklist.

    `marker` and `profile` may be passed in by callers that already have them
    in hand (cmd_apply, cmd_upgrade) so we skip a redundant marker read +
    repo-tree walk. If omitted, both are derived from disk/target.

    No-op when no marker is available (something earlier failed)."""
    from .extensions import report_extensions
    report_extensions(target)

    if marker is None:
        marker = read_govkit_marker(target)
    if marker is None:
        return
    from .rule_templating import template_installed_rules
    from .setup_review import print_review_checklist, write_setup_review
    from .skill_context import load_skill_context, write_skill_context
    write_setup_review(target, marker)
    write_skill_context(target, marker, profile=profile)
    sc = load_skill_context(target)
    if sc is not None:
        template_installed_rules(target, agent, sc.layers)
    print_review_checklist(target, marker)
