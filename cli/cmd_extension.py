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

from . import paths
from .extensions import discover_in


def _bundled_packs() -> list:
    """Discover the bundled extension packs, skipping any with parse errors."""
    return [e for e in discover_in(paths.EXTENSION_PACKS_DIR) if not e.errors]


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


def register(subparsers) -> None:
    """Register the `extension` subcommand tree (`extension list`)."""
    ext_parser = subparsers.add_parser(
        "extension",
        help="List or add bundled extension packs",
    )
    ext_sub = ext_parser.add_subparsers(dest="extension_command", required=True)

    list_parser = ext_sub.add_parser("list", help="List bundled extension packs")
    list_parser.set_defaults(func=cmd_extension_list)
