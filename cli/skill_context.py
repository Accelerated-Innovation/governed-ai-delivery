#!/usr/bin/env python3
# Copyright 2026 Accelerated Innovation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
"""Skill context — what skills read to adapt to the team's repo.

PR 5 shipped the writer. PR 6a adds the typed loader and wires apply /
stack apply / calibrate to all keep the file fresh. Skill consumers
(PR 6b/c) read via `load_skill_context(target) -> SkillContext`.

The file lives at .govkit/skill_context.yaml alongside marker.json.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from .detect import RepoProfile


# Architecture-signal → style id mapping. Order matters when multiple signals
# fire (a mixed repo); first match wins.
_STYLE_PRIORITY = ("dbt-shape", "hexagonal-shape", "clean-shape", "layered-shape")
_STYLE_NAME = {
    "hexagonal-shape": "hexagonal",
    "clean-shape": "clean",
    "layered-shape": "layered",
    "dbt-shape": "dbt-layered",
}

# Default layer-name hints per style. Skills read this to scope guidance to
# the right folders without hardcoding architecture vocabulary themselves.
#
# For data types (dbt-layered), the inbound/outbound/domain mapping is:
#   inbound  = source-shaped layer (staging — where data enters cleaned)
#   domain   = business-logic layer (intermediate — transformations live here)
#   outbound = serving layer        (marts — what downstream consumers read)
# Teams using medallion (bronze/silver/gold) edit `architecture.layers` in
# skill_context.yaml directly during calibrate.
_STYLE_LAYERS = {
    "hexagonal": {
        "inbound":  ["api/", "ports/inbound/"],
        "outbound": ["adapters/", "ports/outbound/"],
        "domain":   ["services/"],
    },
    "clean": {
        "inbound":  ["Presentation/", "Api/"],
        "outbound": ["Infrastructure/"],
        "domain":   ["Application/", "Domain/"],
    },
    "layered": {
        "inbound":  ["Controllers/"],
        "outbound": ["Repositories/"],
        "domain":   ["Services/"],
    },
    "dbt-layered": {
        "inbound":  ["models/staging/", "staging/"],
        "outbound": ["models/marts/", "marts/"],
        "domain":   ["models/intermediate/", "intermediate/"],
    },
    "unknown": {"inbound": [], "outbound": [], "domain": []},
}

# CI option in marker → friendlier CI id used in skill_context.
_CI_NAME = {"github": "github-actions", "azure": "azure-pipelines"}


@dataclass
class SkillContext:
    """Typed view of .govkit/skill_context.yaml for skill consumers (PR 6b/c).

    Flat field shape (rather than nested dicts) so skill code that reads it
    can stay short and obvious. `layers` and `extensions` keep their dict /
    list shape because consumers need to iterate them.
    """
    architecture_style: str
    source_root: str
    detected_signals: list[str]
    layers: dict[str, list[str]]
    stack_id: str | None
    stack_version: str | None
    language: str | None
    api_framework: str | None
    unit_test: str | None
    bdd_test: str | None
    ci: str | None
    llm: bool
    extensions: list[dict] = field(default_factory=list)


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


def _extract_contract_paths(manifest: dict) -> list[str]:
    """Flatten every contract_sets[].paths[] string from an extension manifest."""
    paths: list[str] = []
    for cs in manifest.get("contract_sets") or []:
        if not isinstance(cs, dict):
            continue
        for p in cs.get("paths") or []:
            if isinstance(p, str):
                paths.append(p)
    return paths


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
        out.append({
            "id": ext.id,
            "version": ext.version,
            "capabilities": list(manifest.get("capabilities") or []),
            "contract_paths": _extract_contract_paths(manifest),
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


def build_skill_context(target: Path, marker: dict, profile: RepoProfile | None = None) -> dict:
    """Build the skill-context dict that gets serialized to YAML.

    Pure function — does no I/O beyond build_profile (which reads the
    target tree) and discover_extensions (which reads target/extensions/).

    Callers that already built a `RepoProfile` for this target (cmd_apply
    builds one during stack-overlay selection) can pass it in to skip a
    second walk of the target tree.
    """
    from .detect import build_profile

    if profile is None:
        profile = build_profile(target)
    options = marker.get("options") or {}
    level = marker.get("level")

    style = _infer_architecture_style(profile)
    return {
        "architecture": {
            "style": style,
            "source_root": "src/",  # caller may edit post-write
            "detected_signals": list(profile.detected_architecture_signals),
            "layers": _STYLE_LAYERS.get(style, _STYLE_LAYERS["unknown"]),
        },
        "stack": _stack_facts(marker),
        "ci": _CI_NAME.get(options.get("ci"), options.get("ci")),
        "llm": level == "5",
        "extensions": _extension_facts(target),
    }


def write_skill_context(target: Path, marker: dict, profile: RepoProfile | None = None) -> Path:
    """Write .govkit/skill_context.yaml under target.

    Returns the path written. The .govkit directory must already exist (it
    is created by write_govkit_marker before any skill_context write).

    Optional `profile` is forwarded to `build_skill_context` so cmd_apply
    can avoid a second filesystem walk per install.
    """
    data = build_skill_context(target, marker, profile=profile)
    out_path = target / ".govkit" / "skill_context.yaml"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        yaml.safe_dump(data, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )
    return out_path


def _safe_dict(value: object) -> dict:
    """Return value if it's a dict, else an empty dict. Used so a hand-edit
    that accidentally flattens `architecture:` or `stack:` to a scalar
    doesn't crash the loader on a downstream `.get(...)` call."""
    return value if isinstance(value, dict) else {}


def _safe_str_list(value: object) -> list[str]:
    """Coerce value to a list[str] without splatting a scalar string into
    characters. `list("hexagonal-shape")` would give `['h','e','x',...]` —
    almost never what the user meant. Scalars become empty lists; only
    iterables-of-strings are preserved."""
    if isinstance(value, list):
        return [v for v in value if isinstance(v, str)]
    return []


def _safe_layers(value: object) -> dict[str, list[str]]:
    """Normalize layers to dict[str, list[str]] so downstream consumers
    (rule_templating) can iterate hints without worrying about scalar
    values being splatted into characters.

    Fallback: the unknown-style skeleton (empty list per inbound/outbound/domain)
    so consumers always see the expected keys."""
    if not isinstance(value, dict):
        return dict(_STYLE_LAYERS["unknown"])
    normalized: dict[str, list[str]] = {}
    for key, hints in value.items():
        if not isinstance(key, str):
            continue
        if isinstance(hints, list):
            normalized[key] = [h for h in hints if isinstance(h, str)]
        elif isinstance(hints, str):
            # `inbound: api/` (forgot the list dashes) → `["api/"]`.
            normalized[key] = [hints]
        else:
            normalized[key] = []
    return normalized


def load_skill_context(target: Path) -> SkillContext | None:
    """Read .govkit/skill_context.yaml and return a typed SkillContext.

    Returns None when the file is missing or unparseable so skills can
    degrade gracefully at agent runtime (no exceptions propagating into
    user-facing skill output).

    Hand-edits that flatten `architecture:` / `stack:` / `layers:` to a
    scalar or wrong-typed value are absorbed silently — the loader returns
    a SkillContext with safe defaults rather than crashing _post_install_finalize.
    """
    path = target / ".govkit" / "skill_context.yaml"
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8")
        data = yaml.safe_load(text)
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return None
    if not isinstance(data, dict):
        return None

    arch = _safe_dict(data.get("architecture"))
    stack = _safe_dict(data.get("stack"))
    extensions = data.get("extensions")
    return SkillContext(
        architecture_style=arch.get("style", "unknown") if isinstance(arch.get("style"), str) else "unknown",
        source_root=arch.get("source_root", "src/") if isinstance(arch.get("source_root"), str) else "src/",
        detected_signals=_safe_str_list(arch.get("detected_signals")),
        layers=_safe_layers(arch.get("layers")),
        stack_id=stack.get("id") if isinstance(stack.get("id"), str) else None,
        stack_version=stack.get("version") if isinstance(stack.get("version"), str) else None,
        language=stack.get("language") if isinstance(stack.get("language"), str) else None,
        api_framework=stack.get("api_framework") if isinstance(stack.get("api_framework"), str) else None,
        unit_test=stack.get("unit_test") if isinstance(stack.get("unit_test"), str) else None,
        bdd_test=stack.get("bdd_test") if isinstance(stack.get("bdd_test"), str) else None,
        ci=data.get("ci") if isinstance(data.get("ci"), str) else None,
        llm=bool(data.get("llm")),
        extensions=[e for e in extensions if isinstance(e, dict)] if isinstance(extensions, list) else [],
    )
