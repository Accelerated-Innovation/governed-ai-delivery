#!/usr/bin/env python3
# Copyright 2026 Accelerated Innovation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
"""Agent manifest loading + variant resolution.

Loads agents/<agent>/manifest.json and resolves the effective install set
(files / shared / governed) for a chosen set of options (level, type, ci, ...).
Legacy selection semantics live in cli/legacy_resolution.py. This module keeps
the public loading/prompt surface and selection facade, depending inward on the
path kernel, compatibility adapter, and pure resolution core.
"""

from __future__ import annotations

import argparse
import json
import sys

from . import paths
from .gate_legacy import expand_legacy_ci
from .legacy_resolution import adapt_legacy_manifest, legacy_file_lists
from .resolution import resolve_repository


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
    try:
        return expand_legacy_ci(manifest)
    except ValueError as exc:
        print(f"Error: invalid shared CI catalog: {exc}")
        sys.exit(1)


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


def resolve_variant_files(manifest: dict, options: dict) -> tuple[list, list, list]:
    """Compatibility facade preserving the ordered (files, shared, governed) ABI.

    Loading/prompts and command validation retain their legacy behavior. Pure
    manifest interpretation is isolated in the adapter; explicit requirements
    pass through the same core as future declarative consumers.
    """
    return legacy_file_lists(
        resolve_repository(adapt_legacy_manifest(expand_legacy_ci(manifest), options))
    )
