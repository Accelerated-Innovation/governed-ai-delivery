#!/usr/bin/env python3
# Copyright 2026 Accelerated Innovation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
"""Agent manifest loading + variant resolution.

Loads agents/<agent>/manifest.json and resolves the effective install set
(files / shared / governed) for a chosen set of options (level, type, ci, ...).
The merge/replace, by_type, and by_stack dispatch rules that turn the
manifest's variant declarations into a concrete file list live here. Depends
only on the path kernel (cli/paths.py), so commands import it inward without a
cycle.
"""

from __future__ import annotations

import argparse
import json
import sys

from . import paths


def load_manifest(agent: str) -> dict:
    manifest_path = paths.AGENTS_DIR / agent / "manifest.json"
    if not manifest_path.exists():
        print(f"Error: no agent '{agent}' found. Run 'govkit list' to see available agents.")
        sys.exit(1)
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"Error: invalid JSON in {manifest_path}: {e}")
        sys.exit(1)
    # A manifest must name its agent and declare an install set in one of the
    # two supported formats: `variants` (the post-v0.6 variant format used by
    # the production agents) or `files` (the legacy flat format still honored by
    # cmd_apply's _apply_legacy_install path for custom/older agents).
    if "agent" not in manifest or not ({"variants", "files"} & manifest.keys()):
        print(
            f"Error: manifest for '{agent}' must define 'agent' and either "
            f"'variants' (variant format) or 'files' (legacy flat format)."
        )
        sys.exit(1)
    return manifest


def resolve_options(manifest: dict, args: argparse.Namespace) -> dict:
    """Resolve variant options from CLI flags or interactive prompts.

    Options without a `prompt` key are silently filled from `default` when no
    CLI flag is supplied. This is how the `stack` option (PR 2) avoids
    interrupting users who want the default — it has flag + default but no
    interactive prompt.
    """
    options_spec = manifest.get("options", {})
    resolved = {}
    for key, spec in options_spec.items():
        # Check CLI flag first
        cli_value = getattr(args, key, None)
        if cli_value is not None:
            resolved[key] = cli_value
            continue
        # No CLI value — if the option declares no prompt, silently default.
        if "prompt" not in spec:
            choices = spec.get("choices") or []
            resolved[key] = spec.get("default", choices[0] if choices else None)
            continue
        # Interactive prompt
        choices = spec["choices"]
        default = spec.get("default", choices[0])
        prompt_text = f"  {spec['prompt']} [{' / '.join(choices)}] (default: {default}): "
        answer = input(prompt_text).strip().lower()
        if answer == "":
            answer = default
        if answer not in choices:
            print(f"Error: invalid choice '{answer}'. Must be one of: {', '.join(choices)}")
            sys.exit(1)
        resolved[key] = answer
    return resolved


def _select_variant(
    variants: dict, dimension: str, value: str, level: str,
) -> tuple[dict, dict | None, str]:
    """Select (base, override, mode) for a (dimension, value) at a given level.

    Level handling:
      L3 (default): no override key — returns the dimension's base entries.
      L4: if `level_4` exists, default mode = "merge" (Spec-Driven Add-On).
      L5: if `level_5` exists, default mode = "replace" (current behavior).
      Any level with no matching override key falls back to base only.

    The override's optional `mode` field (per the v0.7 schema) takes precedence over
    the level-specific default.
    """
    variant_group = variants.get(dimension, {})
    base = variant_group.get(value, {})
    level_defaults = {"4": ("level_4", "merge"), "5": ("level_5", "replace")}
    if level in level_defaults:
        key, default_mode = level_defaults[level]
        if key in base:
            override = base[key]
            return base, override, override.get("mode", default_mode)
    return base, None, "merge"


_ENTRY_KEYS = ("files", "shared", "governed")


def _merge_dispatch_blocks(block: dict, *dispatch_blocks: dict) -> dict:
    """Merge a base block with one or more dispatch blocks."""
    merged: dict = {
        k: v for k, v in block.items()
        if k not in (*_ENTRY_KEYS, "by_type", "by_stack")
    }
    for key in _ENTRY_KEYS:
        entries = list(block.get(key, []))
        for dispatch_block in dispatch_blocks:
            entries.extend(dispatch_block.get(key, []))
        merged[key] = entries
    return merged


def _apply_by_type(block: dict, type_value: str | None, stack_value: str | None) -> dict:
    """Merge block + type/stack dispatch entries into one effective block.

    The `by_type` sub-block was added in v0.8 to let one dimension (currently `ci`)
    dispatch its entries based on another dimension's value (currently `type`).
    Example: ci.github.by_type["ui-react"] yields UI-specific CI gates; the
    backend types fall through to ci.github's own files/shared/governed.

    The optional `by_stack` sub-block, nested inside a `by_type` entry, lets data
    CI dispatch stack-specific static gates after `type=data` is selected.

    If the block has no `by_type` key, or no entry for type_value, the block
    is returned unchanged. If `by_stack` has no entry for stack_value, only the
    parent type entry is folded in. Non-list keys (like `mode`) are preserved.
    """
    if not block:
        return {}
    by_type = block.get("by_type") or {}
    type_block = by_type.get(type_value, {}) if type_value else {}
    if not type_block:
        return block
    by_stack = type_block.get("by_stack") or {}
    stack_block = by_stack.get(stack_value, {}) if stack_value else {}
    dispatch_blocks = (type_block, stack_block) if stack_block else (type_block,)
    return _merge_dispatch_blocks(block, *dispatch_blocks)


def _dimension_entries(
    base: dict, override: dict | None, mode: str,
    type_value: str | None = None, stack_value: str | None = None,
) -> tuple[list, list, list]:
    """Compute one dimension's effective (files, shared, governed) after applying override.

    merge mode (L4 default):
      - files: base entries whose `dest` collides with an override entry are dropped;
        override entries are appended after the surviving base entries (later wins on dest).
      - shared, governed: append override entries to base, dedup by string equality.

    replace mode (L5 default):
      - files, shared, governed: take only the override block's entries; ignore base.

    The optional `type_value` enables `by_type` dispatch (v0.8): each block's
    `by_type[type_value]` entries are folded into the block before the merge/
    replace logic runs. Used by the `ci` dimension to ship type-specific gates.
    The optional `stack_value` enables nested `by_stack` dispatch (v0.12+) under
    those type entries for data-stack-specific CI gates.

    Cross-dimension accumulation (e.g. type.api + ci.github both contributing to
    .github/instructions/) is handled by `_collect_entries`, not here.
    """
    eff_base = _apply_by_type(base, type_value, stack_value)
    eff_override = _apply_by_type(override, type_value, stack_value) if override else None

    if eff_override is None:
        return (
            list(eff_base.get("files", [])),
            list(eff_base.get("shared", [])),
            list(eff_base.get("governed", [])),
        )
    if mode == "replace":
        return (
            list(eff_override.get("files", [])),
            list(eff_override.get("shared", [])),
            list(eff_override.get("governed", [])),
        )
    # merge mode
    override_dests = {f["dest"] for f in eff_override.get("files", [])}
    files = [f for f in eff_base.get("files", []) if f["dest"] not in override_dests]
    files.extend(eff_override.get("files", []))

    shared = list(eff_base.get("shared", []))
    for s in eff_override.get("shared", []):
        if s not in shared:
            shared.append(s)

    governed = list(eff_base.get("governed", []))
    for g in eff_override.get("governed", []):
        if g not in governed:
            governed.append(g)
    return files, shared, governed


def _collect_entries(
    files_to_add: list,
    shared_to_add: list,
    governed_to_add: list,
    all_files: list, seen_files: set,
    all_shared: list, seen_shared: set,
    all_governed: list, seen_governed: set,
) -> None:
    """Append a dimension's effective entries to running collections, deduplicated.

    Cross-dimension dedup:
      files: by `(src, dest)` tuple — preserves the legitimate case where multiple
             source directories install at the same destination (e.g. copilot's
             `instructions/backend/` and `instructions/ui-react/` both targeting
             `.github/instructions/`).
      shared, governed: by string equality.

    Within-dimension override-vs-base collisions on `dest` are resolved upstream
    by `_dimension_entries` before this function is called.
    """
    for f in files_to_add:
        key = (f["src"], f["dest"])
        if key not in seen_files:
            all_files.append(f)
            seen_files.add(key)
    for s in shared_to_add:
        if s not in seen_shared:
            all_shared.append(s)
            seen_shared.add(s)
    for g in governed_to_add:
        if g not in seen_governed:
            all_governed.append(g)
            seen_governed.add(g)


def resolve_variant_files(manifest: dict, options: dict) -> tuple[list, list, list]:
    """Collect files, shared, and governed entries from all selected variant dimensions, deduplicated.

    Returns (files, shared, governed):
      files   — agent config files; always overwritten on apply and upgrade
      shared  — project-owned paths; written once (skip_existing), never overwritten
      governed — govkit-owned contracts; written once on apply, refreshed on upgrade
    """
    all_files = list(manifest.get("base_files", []))
    all_shared: list[str] = []
    all_governed: list[str] = []
    seen_files: set[tuple[str, str]] = {(f["src"], f["dest"]) for f in all_files}
    seen_shared: set[str] = set()
    seen_governed: set[str] = set()
    variants = manifest.get("variants", {})
    level = options.get("level", "3")
    type_value = options.get("type")
    stack_value = options.get("stack")
    for dimension, value in options.items():
        if dimension == "level":
            continue
        base, override, mode = _select_variant(variants, dimension, value, level)
        files, shared, governed = _dimension_entries(
            base, override, mode,
            type_value=type_value, stack_value=stack_value,
        )
        _collect_entries(
            files, shared, governed,
            all_files, seen_files,
            all_shared, seen_shared,
            all_governed, seen_governed,
        )
    return all_files, all_shared, all_governed
