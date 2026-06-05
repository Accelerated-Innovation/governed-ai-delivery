#!/usr/bin/env python3
# Copyright 2026 Accelerated Innovation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
"""govkit extension — list bundled extension packs and add one to a project.

Extension packs ship with the wheel (cli/extension_packs/, force-included from
the repo's extensions/). `extension add` copies a pack into the target's
extensions/<id>/ folder, where govkit's existing discovery/validate already
operates. Mirrors the shape of `cmd_stack` (list + apply over a bundled set).
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from . import paths
from .extensions import (
    EXTENSIONS_DIR,
    discover_extensions,
    discover_in,
    is_valid_extension_id,
    validate_extension,
)
from .marker import read_govkit_marker


def _bundled_packs() -> list:
    """Discover the bundled extension packs, skipping any with parse errors."""
    return [e for e in discover_in(paths.EXTENSION_PACKS_DIR) if not e.errors]


def _compat_warnings(manifest: dict, marker: dict) -> list[str]:
    """Return warn-and-proceed messages when the target's marker level/type is
    not covered by the pack's supported_levels / supported_project_types.
    Empty when compatible or when the pack declares no constraint."""
    warnings: list[str] = []
    level = marker.get("level")
    levels = manifest.get("supported_levels") or []
    if levels and level is not None:
        try:
            if int(level) not in [int(x) for x in levels]:
                warnings.append(
                    f"project level {level} is not in supported_levels {levels} "
                    "— installing anyway"
                )
        except (TypeError, ValueError):
            pass
    ptype = (marker.get("options") or {}).get("type")
    types = manifest.get("supported_project_types") or []
    if types and ptype is not None and ptype not in types:
        warnings.append(
            f"project type {ptype!r} is not in supported_project_types {types} "
            "— installing anyway"
        )
    return warnings


def cmd_extension_list(_args: argparse.Namespace) -> None:
    """Print every bundled extension pack (id, name, description, supported
    levels/types). Source of truth for what `govkit extension add` can install.
    """
    packs = _bundled_packs()
    if not packs:
        print("No bundled extension packs found.")
        return
    print("\nAvailable extension packs:\n")
    for ext in packs:
        m = ext.manifest
        print(f"  {ext.id:20s} {m.get('name', ext.id)}")
        desc = (m.get("description") or "").strip()
        if desc:
            print(f"  {'':20s}   {desc}")
        meta: list[str] = []
        levels = m.get("supported_levels") or []
        types = m.get("supported_project_types") or []
        if levels:
            meta.append("levels " + ",".join(str(x) for x in levels))
        if types:
            meta.append("types " + ",".join(types))
        if meta:
            print(f"  {'':20s}   ({'; '.join(meta)})")
    print(
        "\nAdd one to your project:\n"
        "  govkit extension add <id> --target <path>\n"
    )


def _resolve_dest(target: Path, pack) -> Path:
    """Return the safe install destination for a pack, or exit non-zero.

    Guards against a malformed manifest id (path separators, '..') escaping
    <target>/extensions/ before any rmtree/copytree.
    """
    if not is_valid_extension_id(pack.id):
        print(
            f"Error: extension id {pack.id!r} is not a valid identifier "
            "(must match ^[a-z0-9][a-z0-9-]*$); refusing to install.",
            file=sys.stderr,
        )
        sys.exit(1)
    ext_root = (target / EXTENSIONS_DIR).resolve()
    dest = target / EXTENSIONS_DIR / pack.id
    if not dest.resolve().is_relative_to(ext_root):
        print(
            f"Error: destination for '{pack.id}' resolves outside {ext_root}; refusing.",
            file=sys.stderr,
        )
        sys.exit(1)
    return dest


def _print_validation_notes(target: Path, ext_id: str) -> None:
    """Validate the just-installed pack in place; print any issues as non-fatal
    notes (warn and proceed)."""
    added = next((e for e in discover_extensions(target) if e.id == ext_id), None)
    if added is None:
        return
    issues = validate_extension(added, target)
    if not issues:
        return
    print(
        f"\nValidation notes ({len(issues)}) — "
        f"run `govkit doctor --target {target}` for detail:"
    )
    for issue in issues:
        print(f"  - {issue}")


def cmd_extension_add(args: argparse.Namespace) -> None:
    """Copy a bundled extension pack into <target>/extensions/<id>/.

    Refuses to clobber an existing folder without --force. After copying,
    validates the pack in place and surfaces any issues as non-fatal notes
    (e.g. a generative pack's L5 `relates_to.extends` paths missing in a
    non-L5 project) — warn and proceed.
    """
    target = Path(args.target).resolve()
    if not target.is_dir():
        print(f"Error: target directory '{target}' does not exist.", file=sys.stderr)
        sys.exit(1)

    pack = next((e for e in _bundled_packs() if e.id == args.extension_id), None)
    if pack is None:
        print(
            f"Error: extension '{args.extension_id}' not found. "
            f"Run `govkit extension list` to see available packs.",
            file=sys.stderr,
        )
        sys.exit(1)

    dest = _resolve_dest(target, pack)

    if dest.exists() and not args.force:
        print(
            f"Error: '{dest}' already exists. Re-run with --force to overwrite.",
            file=sys.stderr,
        )
        sys.exit(1)

    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(pack.root, dest)

    print(f"\nAdding extension '{pack.id}' to {target}")
    name = pack.manifest.get("name", pack.id)
    if name != pack.id:
        print(f"  {name}")

    marker = read_govkit_marker(target)
    if marker:
        for warning in _compat_warnings(pack.manifest, marker):
            print(f"  WARN: {warning}")

    print(f"Done. Extension '{pack.id}' added to {dest}")
    _print_validation_notes(target, pack.id)


def register(subparsers) -> None:
    """Register the `extension` subcommand tree (`extension list`, `extension add`)."""
    ext_parser = subparsers.add_parser(
        "extension",
        help="List or add bundled extension packs",
    )
    ext_sub = ext_parser.add_subparsers(dest="extension_command", required=True)

    list_parser = ext_sub.add_parser("list", help="List bundled extension packs")
    list_parser.set_defaults(func=cmd_extension_list)

    add_parser = ext_sub.add_parser(
        "add", help="Add a bundled extension pack to a project"
    )
    add_parser.add_argument(
        "extension_id",
        help="Extension pack id (e.g. vision-inference). See `govkit extension list`.",
    )
    add_parser.add_argument("--target", required=True, help=paths.TARGET_HELP)
    add_parser.add_argument(
        "--force", action="store_true",
        help="Overwrite an existing extensions/<id>/ folder",
    )
    add_parser.set_defaults(func=cmd_extension_add)
