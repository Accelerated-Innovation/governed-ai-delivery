#!/usr/bin/env python3
# Copyright 2026 Accelerated Innovation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
"""Skill context — what skills read to adapt to the team's repo.

PR 5 ships the writer; PR 6a will add the loader and refactor apply /
stack apply to also call write_skill_context so consumers (skills in
PR 6b/c) always see fresh facts.

The file lives at .govkit/skill_context.yaml alongside marker.json.
"""

from pathlib import Path

import yaml


# Architecture-signal → style id mapping.
_STYLE_PRIORITY = ("hexagonal-shape", "clean-shape", "layered-shape")
_STYLE_NAME = {
    "hexagonal-shape": "hexagonal",
    "clean-shape": "clean",
    "layered-shape": "layered",
}

# CI option in marker → friendlier CI id used in skill_context.
_CI_NAME = {"github": "github-actions", "azure": "azure-pipelines"}


def _infer_architecture_style(profile) -> str:
    """Pick the dominant architecture style from detected signals.

    If multiple signals fire (which can happen in mixed repos), prefer in
    the order: hexagonal → clean → layered. Returns "unknown" when no
    signal is present so skills know to ask the team rather than guess.
    """
    signals = set(profile.detected_architecture_signals)
    for candidate in _STYLE_PRIORITY:
        if candidate in signals:
            return _STYLE_NAME[candidate]
    return "unknown"


def _extension_facts(target: Path) -> list[dict]:
    """Discover extensions and project their manifest data into a flat list
    of (id, version, capabilities, contract_paths) dicts for skill consumers."""
    from .extensions import discover_extensions

    out: list[dict] = []
    for ext in discover_extensions(target):
        if ext.errors:
            # Skip ext with discovery errors — doctor's D013 surfaces those.
            continue
        manifest = ext.manifest or {}
        contract_paths: list[str] = []
        for cs in manifest.get("contract_sets") or []:
            if not isinstance(cs, dict):
                continue
            for p in cs.get("paths") or []:
                if isinstance(p, str):
                    contract_paths.append(p)
        out.append({
            "id": ext.id,
            "version": ext.version,
            "capabilities": list(manifest.get("capabilities") or []),
            "contract_paths": contract_paths,
        })
    return out


def _stack_facts(marker: dict) -> dict:
    """Merge marker.stack metadata with the overlay's skill_context block.

    The marker tells us which overlay is active; the overlay's own
    skill_context (cli/stacks/<id>/overlay.yaml) supplies the language,
    framework, and test-framework facts skills need.
    """
    stack = marker.get("stack") or {}
    stack_id = stack.get("id")
    facts: dict = {
        "id": stack_id,
        "version": stack.get("version"),
        "display_name": stack.get("display_name"),
    }
    if stack_id:
        from .overlay import load_overlay
        overlay = load_overlay(stack_id)
        if overlay is not None:
            for k, v in (overlay.skill_context or {}).items():
                facts.setdefault(k, v)
    return facts


def build_skill_context(target: Path, marker: dict) -> dict:
    """Build the skill-context dict that gets serialized to YAML.

    Pure function — does no I/O beyond build_profile (which reads the
    target tree) and discover_extensions (which reads target/extensions/).
    """
    from .detect import build_profile

    profile = build_profile(target)
    options = marker.get("options") or {}
    level = marker.get("level")

    return {
        "architecture": {
            "style": _infer_architecture_style(profile),
            "source_root": "src/",  # caller may edit post-write
            "detected_signals": list(profile.detected_architecture_signals),
        },
        "stack": _stack_facts(marker),
        "ci": _CI_NAME.get(options.get("ci"), options.get("ci")),
        "llm": level == "5",
        "extensions": _extension_facts(target),
    }


def write_skill_context(target: Path, marker: dict) -> Path:
    """Write .govkit/skill_context.yaml under target.

    Returns the path written. The .govkit directory must already exist (it
    is created by write_govkit_marker before any skill_context write).
    """
    data = build_skill_context(target, marker)
    out_path = target / ".govkit" / "skill_context.yaml"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        yaml.safe_dump(data, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )
    return out_path
