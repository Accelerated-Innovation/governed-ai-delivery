# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Pure compatibility adapter for ordered legacy manifest/flag selections.

All level and merge/replace interpretation belongs here, outside the new core.
Command-boundary validation remains unchanged. In particular this adapter, like
its predecessor, does not reject unknown dimensions or unsupported CLI options.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy

from .resolution_models import (
    ArtifactRequirement,
    Authority,
    CapabilityRequirement,
    InstallationPlan,
    Integrations,
    Ownership,
    Provenance,
    Reason,
    RepositoryInput,
    SourceRef,
)


def _select_variant(
    variants: dict,
    dimension: str,
    value: str,
    level: str,
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
        k: v for k, v in block.items() if k not in (*_ENTRY_KEYS, "by_type", "by_stack")
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
    base: dict,
    override: dict | None,
    mode: str,
    type_value: str | None = None,
    stack_value: str | None = None,
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
    .github/instructions/) is handled by the adapter's collector, not here.
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


_CAPABILITIES_BY_LEVEL = {
    "3": ("application-governance",),
    "4": ("application-governance", "gherkin-delivery"),
    "5": ("application-governance", "gherkin-delivery", "llm-evaluation"),
}
_OWNERSHIP_BY_ENTRY = {
    "files": Ownership.AGENT_CONFIG,
    "shared": Ownership.PROJECT_ARTIFACT,
    "governed": Ownership.GOVERNED_CONTRACT,
}


def adapt_legacy_manifest(
    manifest: dict,
    options: dict,
    *,
    manifest_reference: str | None = None,
) -> RepositoryInput:
    """Translate already supplied legacy inputs, without approving project policy.

    Preserve option iteration order, base duplicates, cross-dimension (src,dest)
    deduplication, and every installer attribute. The manifest remains the
    authority for legacy resource selection. Flat-manifest apply remains on its
    existing separate path, and command validation continues at its boundary.
    """
    agent = manifest.get("agent")
    reference = manifest_reference or (
        f"agents/{agent}/manifest.json" if agent else "legacy-manifest"
    )
    level = options.get("level", "3")
    artifacts: list[ArtifactRequirement] = []
    seen: dict[str, set] = {key: set() for key in _ENTRY_KEYS}

    def collect(entries: tuple[list, list, list], reason: Reason, *, base: bool = False) -> None:
        for key, values in zip(_ENTRY_KEYS, entries, strict=True):
            for value in values:
                is_file = key == "files"
                identity = (value["src"], value["dest"]) if is_file else value
                if not base and identity in seen[key]:
                    continue
                seen[key].add(identity)
                source_path = value["src"] if is_file else value
                destination = value["dest"] if is_file else value
                attributes = (
                    {k: deepcopy(v) for k, v in value.items() if k not in ("src", "dest")}
                    if is_file
                    else {}
                )
                artifacts.append(
                    ArtifactRequirement(
                        f"legacy:{key}:{len(artifacts)}",
                        source_path,
                        destination,
                        _OWNERSHIP_BY_ENTRY[key],
                        (reason,),
                        attributes=attributes,
                    )
                )

    collect(
        (list(manifest.get("base_files", [])), [], []),
        Reason(
            "Unconditional legacy base resource",
            SourceRef(f"{reference}#base_files", Authority.LEGACY),
        ),
        base=True,
    )
    variants = manifest.get("variants", {})
    for dimension, value in options.items():
        if dimension == "level":
            continue
        base, override, mode = _select_variant(variants, dimension, value, level)
        entries = _dimension_entries(
            base, override, mode, options.get("type"), options.get("stack")
        )
        pointer = "/".join(
            str(part).replace("~", "~0").replace("/", "~1") for part in (dimension, value)
        )
        collect(
            entries,
            Reason(
                f"Legacy {dimension}={value}; {mode if override is not None else 'base'} selection "
                f"with type={options.get('type')} and stack={options.get('stack')}",
                SourceRef(f"{reference}#variants/{pointer}", Authority.LEGACY),
            ),
        )

    capabilities = tuple(
        CapabilityRequirement(
            identifier,
            (
                Reason(
                    "Configured by the translated legacy bundle; not evidence of execution",
                    SourceRef(f"{reference}#options/level", Authority.LEGACY),
                ),
            ),
        )
        for identifier in _CAPABILITIES_BY_LEVEL.get(level, ())
    )
    digest = hashlib.sha256(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    provenance = Provenance(
        SourceRef(reference, Authority.LEGACY),
        digest,
        {
            "options": deepcopy(options),
            "option_order": list(options),
            "effective_level": level,
        },
    )
    return RepositoryInput(
        f"legacy:{agent or 'custom'}",
        capabilities,
        tuple(artifacts),
        integrations=Integrations(
            agent, options.get("type"), options.get("ci"), options.get("stack")
        ),
        provenance=(provenance,),
    )


def legacy_file_lists(plan: InstallationPlan) -> tuple[list, list, list]:
    """Restore the legacy ABI; ownership categories do not grant overwrite rights."""
    if not plan.ready:
        raise ValueError("Cannot convert an unresolved plan into an install selection")
    files, shared, governed = [], [], []
    destinations = {
        Ownership.PROJECT_ARTIFACT: shared,
        Ownership.GOVERNED_CONTRACT: governed,
    }
    for artifact in plan.selections.artifacts:
        if artifact.ownership == Ownership.AGENT_CONFIG:
            files.append(
                {
                    "src": artifact.source_path,
                    "dest": artifact.destination,
                    **deepcopy(artifact.attributes),
                }
            )
        else:
            destinations[artifact.ownership].append(artifact.source_path)
    return files, shared, governed
