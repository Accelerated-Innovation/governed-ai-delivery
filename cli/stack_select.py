#!/usr/bin/env python3
# Copyright 2026 Accelerated Innovation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
"""Stack selection — stage 2 of the stack pipeline.

Sits between detection (cli/detect.py: build_profile, infer_stack) and overlay
loading (cli/overlay.py: load_overlay, apply_overlay). Given the inferred
stack, the user's explicit --stack flag, and the requested --type, this module
decides which bundled overlay an install actually uses, prints the detection
summary, and applies the chosen overlay (recording the marker assumption).

Selection is decoupled from argparse on purpose: callers pass the raw --stack
value and the resolved --type, not a Namespace. This keeps the per-type default
authoritative — the manifest's silent `stack` default flows through
`options['stack']`, which must NOT shadow `--type data -> python-dbt`.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

from .detect import RepoProfile

# The marker assumption id under which the chosen stack is recorded. Consumed
# by doctor and `govkit stack apply` to find/replace the prior stack choice.
STACK_ID_ASSUMPTION = "stack.id"


# Per-type default stack when nothing is detected and no --stack is passed.
# Picked to match the most common starting point for that shape.
_DEFAULT_STACK_BY_TYPE = {
    "api":  "python-fastapi",
    "cli":  "python-fastapi",
    "data": "python-dbt",
}

def _stack_supports_type(stack_id: str | None, type_value: str) -> bool:
    """True when `stack_id` is a sensible overlay for `type_value`.

    An inferred stack that doesn't support the user's chosen --type is
    treated as an ambient signal from a different shape (e.g. fastapi in
    pyproject.toml of a dbt workshop dir) and does NOT override the
    type-default. The user's explicit --type intent wins.

    Reads the overlay's declared supported_types. Unknown stack ids and
    overlays declaring no restriction return True so future-added stacks
    aren't accidentally rejected — the type-default is a safety net, not a
    gatekeeper.
    """
    if not stack_id:
        return False
    from .overlay import load_overlay

    overlay = load_overlay(stack_id)
    if overlay is None or not overlay.supported_types:
        return True
    return type_value in overlay.supported_types


def resolve_stack_choice(
    cli_stack: str | None,
    type_value: str,
    profile: RepoProfile,
    inferred_stack: str | None,
    inferred_confidence: str,
    target: Path,
) -> tuple[str, str, str, list[str]]:
    """Return (requested_stack, source, confidence, evidence).

    Precedence: explicit --stack > type-compatible high-confidence inference >
    per-type default. An inferred stack that does not match the requested
    --type is ignored — the user's explicit shape intent (--type data) outranks
    an incidental framework signal from a different shape (fastapi pyproject).

    `cli_stack` is the raw --stack flag value (None when the user didn't pass
    it). The manifest's silent `stack` default is deliberately NOT consulted
    here so it can't shadow the per-type default.
    """
    if cli_stack:
        return cli_stack, "flag", "high", []
    if (inferred_stack
            and inferred_confidence == "high"
            and _stack_supports_type(inferred_stack, type_value)):
        evidence = list(
            profile.detected_frameworks
            + [str(p.relative_to(target)) for p in profile.detected_project_paths[:3]]
        )
        return inferred_stack, "detected", "high", evidence
    default_stack = _DEFAULT_STACK_BY_TYPE.get(type_value, "python-fastapi")
    return default_stack, "default", "low", []


def _print_detected_signals(profile: RepoProfile) -> None:
    """Emit the per-category `[confidence] kind value` lines."""
    for lang in profile.detected_languages:
        conf = profile.language_confidence(lang)
        print(f"  [{conf:6s}] language       {lang}")
    for fw in profile.detected_frameworks:
        print(f"  [high  ] framework      {fw}")
    for ci_name in profile.detected_ci:
        print(f"  [high  ] ci             {ci_name}")
    for sig in profile.detected_architecture_signals:
        print(f"  [medium] architecture   {sig}")
    if profile.detected_llm_signals:
        print(f"  [high  ] llm            {', '.join(profile.detected_llm_signals)}")


def _print_chosen_stack_line(
    inferred_stack: str | None, inferred_confidence: str,
    chosen_stack: str, stack_source: str,
) -> None:
    """Trailing one-liner that names the stack the install will use."""
    if inferred_stack and stack_source == "detected":
        print(f"\n  → using detected stack: {chosen_stack} (confidence: {inferred_confidence})")
    elif stack_source == "flag":
        print(f"\n  → using explicit --stack: {chosen_stack}")
    else:
        print(f"\n  → using default stack: {chosen_stack} (no high-confidence match)")


def print_detection_summary(
    profile: RepoProfile,
    inferred_stack: str | None,
    inferred_confidence: str,
    chosen_stack: str,
    stack_source: str,
) -> None:
    """Print a one-block detection summary before installing.

    Format mirrors the plan's Section 5 example: a 'detecting repo profile'
    header with [confidence] tagged lines per category. Skipped quietly for
    repos with no detectable signals.
    """
    if not (profile.detected_languages or profile.detected_frameworks
            or profile.detected_ci or profile.detected_architecture_signals):
        return
    print("\nDetecting repo profile...")
    _print_detected_signals(profile)
    _print_chosen_stack_line(inferred_stack, inferred_confidence, chosen_stack, stack_source)


def _build_stack_assumption(
    overlay, source: str, confidence: str, evidence: list[str],
) -> dict:
    """Construct the `stack.id` assumption block to write into the marker."""
    return {
        "id": STACK_ID_ASSUMPTION,
        "value": overlay.id,
        "source": source,
        "confidence": confidence,
        "evidence": evidence,
        "files_affected": [d["dest"] for d in overlay.docs],
        "review_required": source == "default",
        "warning_message": (
            f"Defaulted to {overlay.id}. If your repo uses a different stack, "
            f"re-run `govkit stack apply <id>` or pass `--stack <id>` to apply."
        ) if source == "default" else None,
        "calibrated_at": None,
        "calibrated_against_overlay_version": None,
    }


def apply_stack_overlay(
    target: Path, cli_stack: str | None, options: dict,
    prior_applied_at: str | None, force: bool,
) -> tuple[dict | None, dict | None, dict, RepoProfile | None]:
    """Run detection, apply the chosen stack overlay, return
    (stack_meta, stack_assumption, updated_options, profile).

    `profile` is threaded back to the caller so `_post_install_finalize` can
    pass it to `write_skill_context` without re-walking the target tree.

    No-op for UI types (returns Nones + original options + None profile).
    """
    type_value = options.get("type", "")
    if type_value not in ("api", "cli", "data"):
        return None, None, options, None

    from .detect import build_profile, infer_stack
    from .overlay import apply_overlay, load_overlay

    profile = build_profile(target)
    inferred_stack, inferred_confidence = infer_stack(profile)
    requested_stack, source, confidence, evidence = resolve_stack_choice(
        cli_stack, type_value, profile, inferred_stack, inferred_confidence, target,
    )

    print_detection_summary(
        profile, inferred_stack, inferred_confidence, requested_stack, source,
    )

    overlay = load_overlay(requested_stack)
    if overlay is None:
        print(
            f"Error: stack '{requested_stack}' not found. "
            f"Run `govkit stack list` to see available stacks.",
            file=sys.stderr,
        )
        sys.exit(1)
    print(f"\nStack overlay: {overlay.id} ({overlay.display_name})")
    apply_overlay(overlay, target, applied_at=prior_applied_at, force=force)

    stack_meta = {
        "id": overlay.id,
        "version": overlay.version,
        "display_name": overlay.display_name,
        "applied_at": datetime.now(timezone.utc).isoformat(),
    }
    stack_assumption = _build_stack_assumption(overlay, source, confidence, evidence)
    # Persist the chosen stack in marker.options so future commands
    # (upgrade, stack apply, doctor) know what was selected.
    return stack_meta, stack_assumption, {**options, "stack": overlay.id}, profile
