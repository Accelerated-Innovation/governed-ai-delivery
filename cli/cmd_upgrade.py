#!/usr/bin/env python3
# Copyright 2026 Accelerated Innovation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
"""govkit upgrade — refresh agent config + governed contracts to the current version.

With --migrate-levels, runs the v0.6.x → v0.7.0 maturity-model migration flow
(the L3/L4 swap) instead of the standard refresh.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from . import paths, version
from .install_common import (
    copy_governed_or_shared,
    install_agent_file,
    post_install_finalize,
    reconcile_legacy_instruction_files,
)
from .manifest import load_manifest, resolve_variant_files
from .marker import _compare_version, read_govkit_marker, write_govkit_marker


def _validate_stored_options(manifest: dict, stored_options: dict) -> None:
    """Fail fast when marker options cannot safely resolve manifest variants."""
    if not isinstance(stored_options, dict):
        print(
            "Error: .govkit marker 'options' must be an object. "
            "Re-run `govkit apply` to refresh the marker before upgrading.",
            file=sys.stderr,
        )
        sys.exit(1)

    options_spec = manifest.get("options", {})
    variants = manifest.get("variants", {})
    required_dimensions = [
        key for key in options_spec
        if key != "level" and key in variants
    ]

    for key in required_dimensions:
        spec = options_spec.get(key, {})
        choices = spec.get("choices") or []
        if key not in stored_options or stored_options.get(key) in (None, ""):
            print(
                f"Error: .govkit marker missing required option '{key}'. "
                "Re-run `govkit apply` to refresh the marker before upgrading.",
                file=sys.stderr,
            )
            sys.exit(1)

        value = stored_options[key]
        if choices and value not in choices:
            print(
                f"Error: .govkit marker has invalid value {value!r} for option "
                f"'{key}'. Expected one of: {', '.join(choices)}. "
                "Re-run `govkit apply` to refresh the marker before upgrading.",
                file=sys.stderr,
            )
            sys.exit(1)


def cmd_upgrade(args: argparse.Namespace) -> None:
    """Refresh agent config and governed contracts to the current govkit version.

    With --migrate-levels, run the v0.6→v0.7 maturity-model migration flow
    instead of the standard refresh.
    """
    target = Path(args.target).resolve()
    if not target.exists():
        print(f"Error: target directory '{target}' does not exist.")
        sys.exit(1)

    stored = read_govkit_marker(target)
    if not stored:
        print("Error: no .govkit marker found. Run 'govkit apply' first.")
        sys.exit(1)

    stored_version = stored.get("version", "unknown")
    agent = stored.get("agent")
    stored_level = stored.get("level", "3")
    stored_options = stored.get("options", {})

    if not agent:
        print("Error: .govkit marker missing 'agent' field. Run 'govkit apply' to reinitialise.")
        sys.exit(1)

    if getattr(args, "migrate_levels", False):
        sys.exit(_cmd_upgrade_migrate_levels(target, stored_version, stored_level, agent, stored_options))

    if stored_version == version.GOVKIT_VERSION and not args.force:
        print(f"\nAlready at govkit {version.GOVKIT_VERSION}. Nothing to upgrade.")
        print("Use --force to re-apply even when the version is current.")
        return

    print(f"\nUpgrading govkit {stored_version} → {version.GOVKIT_VERSION}")
    print(f"  Agent: {agent}  Level: {stored_level}\n")

    manifest = load_manifest(agent)
    _validate_stored_options(manifest, stored_options)
    agent_dir = paths.AGENTS_DIR / agent
    options = {**stored_options, "level": stored_level}
    files, shared, governed = resolve_variant_files(manifest, options)

    # Edit-protection (A2): governed/shared overwrites consult applied_at and
    # respect --force. Agent files (the `files` category) are unconditionally
    # refreshed because they are govkit-managed and don't carry editable
    # headers.
    prior_applied_at = stored.get("applied_at")
    baseline = f"govkit@{version.GOVKIT_VERSION}"

    # A6: retire any pre-namespace top-level instruction file (CLAUDE.md etc.)
    # before installing governance into the rules namespace.
    files = reconcile_legacy_instruction_files(target, agent_dir, files, prior_applied_at)

    print("Agent files (refreshed):")
    for entry in files:
        install_agent_file(agent_dir, entry, target, prior_applied_at)

    print("\nGoverned contracts (refreshed, edit-protected):")
    copy_governed_or_shared(
        governed, target, prior_applied_at, args.force, baseline,
        skip_existing=False,
    )
    print("\nShared governance (skip if present):")
    copy_governed_or_shared(
        shared, target, prior_applied_at, args.force, baseline,
    )

    # Upgrade re-installs govkit's own files; it does not re-decide anything the
    # team decided. Carry stack/assumptions/calibration across or they reset to
    # empty — which also blanks the stack facts skill_context.yaml derives below.
    # applied_at still defaults to now: upgrade IS a re-install.
    marker = write_govkit_marker(
        target, agent, stored_level, options,
        stack=stored.get("stack"),
        assumptions=stored.get("assumptions") or [],
        calibration=stored.get("calibration"),
    )
    post_install_finalize(target, agent, marker=marker)

    print(f"\nDone. '{agent}' upgraded to govkit {version.GOVKIT_VERSION} at {target}")
    print("\nReview changes with: git diff")


# ---------------------------------------------------------------------------
# Migrate-levels command (v0.6.x → v0.7.0 maturity-model swap)
# ---------------------------------------------------------------------------

_EVAL_CRITERIA_STUB = """\
# Auto-generated stub by `govkit upgrade --migrate-levels`.
# Complete this file before running `govkit validate`.
# Replace TBD placeholders with values appropriate for your feature.
version: "1"
mode: TBD  # one of: deterministic | llm | none
criteria: []
"""

_ARCH_PREFLIGHT_STUB = """\
# Architecture Preflight (auto-generated stub)

> Generated by `govkit upgrade --migrate-levels`.
> Replace TBD placeholders with the architecture preflight findings for this
> feature. See `governance/backend/templates/architecture_preflight.md` for the
> canonical template and section guidance.

## 1. Artifact Review

TBD

## 2. Standards Referenced

TBD

## 3. Boundary Analysis

TBD

## 4. API Impact

TBD

## 5. Security Impact

TBD

## 6. Evaluation Impact

TBD

## 7. ADR Determination

TBD

## 8. Shared Contract Analysis

TBD

## 9. Preflight Conclusion

TBD
"""


def _list_user_features(features_dir: Path) -> list[Path]:
    """Return sorted feature directories, excluding starters and dotfiles."""
    if not features_dir.exists():
        return []
    return sorted(
        d for d in features_dir.iterdir()
        if d.is_dir()
        and not d.name.startswith("starter_")
        and not d.name.startswith(".")
    )


def _cmd_upgrade_migrate_levels(
    target: Path, stored_version: str, stored_level: str,
    agent: str, stored_options: dict,
) -> int:
    """Execute the v0.6→v0.7 maturity-model migration flow.

    Returns an exit code (0 = success / no-op, 1 = aborted or invalid input).
    See plans/MATURITY_MODEL_L3_L4_SWAP_PLAN.md §7.2 for the state matrix.
    """
    if _compare_version(stored_version, "0.7.0") >= 0:
        print(f"\nMarker is already at version {stored_version} (>= 0.7.0). No migration needed.")
        return 0

    options = {k: v for k, v in stored_options.items() if k != "level"}

    if stored_level == "5":
        print(f"\nDetected .govkit marker: version={stored_version}  level=5")
        print("L5 (GenAI Operations) content is unchanged in v0.7.0; updating version only.")
        write_govkit_marker(target, agent, "5", options)
        return 0

    if stored_level == "4":
        print(f"\nDetected .govkit marker: version={stored_version}  level=4")
        print("Your project shape is correct under v0.7.0; the level label flips")
        print('from "Governed AI Delivery" to "Spec-Driven Add-On" but no data migration is needed.')
        write_govkit_marker(target, agent, "4", options)
        return 0

    if stored_level == "3":
        return _migrate_l3_interactive(target, stored_version, agent, options)

    print(f"\nUnknown stored level {stored_level!r}. Aborting without changes.")
    return 1


def _print_l3_migration_menu(stored_version: str, feature_dirs: list) -> None:
    """Display the 4-option migration menu for v0.6 L3 → v0.7+ migration."""
    print(f"\nDetected .govkit marker: version={stored_version}  level=3")
    print(
        f"Project has {len(feature_dirs)} feature director(ies) under features/, "
        "each with 3 artifacts.\n"
    )
    print(
        "Under govkit v0.7.0, your project's shape (features/ + 3-artifact dirs) maps\n"
        "to Level 4 (Spec-Driven Add-On). L4 requires 5 artifacts per feature.\n"
    )
    print("How would you like to migrate?")
    print("  [1] Migrate to L4 — generate stub eval_criteria.yaml and")
    print("      architecture_preflight.md in each feature dir (you fill them in later).")
    print(f"      Marker becomes level=4, version={version.GOVKIT_VERSION}.")
    print("  [2] Migrate to L4 — do NOT generate stubs. You will author the two new")
    print("      artifacts per feature manually. Validation will fail until you do.")
    print(f"      Marker becomes level=4, version={version.GOVKIT_VERSION}.")
    print("  [3] Adopt new-L3 (Foundations) — you confirm we should DELETE features/")
    print("      and switch to architecture-only governance.")
    print(f"      Marker becomes level=3, version={version.GOVKIT_VERSION}.")
    print("  [4] Abort — make no changes. Pin govkit==0.6.* in your project.\n")


def _migrate_choice_l4_with_stubs(
    target: Path, agent: str, options: dict, feature_dirs: list,
) -> int:
    """Choice 1: write the marker as L4 and stub the two new L4 artifacts in
    every feature dir that lacks them."""
    for fd in feature_dirs:
        eval_path = fd / "eval_criteria.yaml"
        if not eval_path.exists():
            eval_path.write_text(_EVAL_CRITERIA_STUB, encoding="utf-8")
        preflight_path = fd / "architecture_preflight.md"
        if not preflight_path.exists():
            preflight_path.write_text(_ARCH_PREFLIGHT_STUB, encoding="utf-8")
    write_govkit_marker(target, agent, "4", options)
    print(f"\n  Generated stubs in {len(feature_dirs)} feature director(ies).")
    print("\n  Next: edit each feature's eval_criteria.yaml and architecture_preflight.md")
    print("  to replace TBD placeholders. Then run `govkit validate`.")
    return 0


def _migrate_choice_l4_no_stubs(target: Path, agent: str, options: dict) -> int:
    """Choice 2: write the marker as L4 without generating stubs."""
    write_govkit_marker(target, agent, "4", options)
    print("\n  Marker rewritten without stub generation.")
    print("  Next: author eval_criteria.yaml and architecture_preflight.md per")
    print("  feature manually. `govkit validate` will fail until you do.")
    return 0


def _migrate_choice_delete_features(
    target: Path, agent: str, options: dict, features_dir: Path,
) -> int:
    """Choice 3: confirm + delete features/, write marker as L3 (Foundations)."""
    confirm = input(
        f"\n  This will DELETE {features_dir} and all its contents. "
        "Type 'yes' to confirm: "
    ).strip().lower()
    if confirm != "yes":
        print("  Cancelled.")
        return 1
    if features_dir.exists():
        shutil.rmtree(features_dir)
    write_govkit_marker(target, agent, "3", options)
    print(f"\n  Removed {features_dir}.")
    return 0


def _migrate_choice_abort() -> int:
    """Choice 4: no changes, advise pinning the legacy govkit version."""
    print("\n  No changes made.")
    print("  Pin `govkit==0.6.*` in your project until you're ready to migrate.")
    return 0


def _migrate_l3_interactive(
    target: Path, stored_version: str, agent: str, options: dict,
) -> int:
    """Interactive 4-option prompt for v0.6 L3 (3-artifact) projects."""
    features_dir = target / "features"
    feature_dirs = _list_user_features(features_dir)

    _print_l3_migration_menu(stored_version, feature_dirs)
    choice = input("  Choice [1-4]: ").strip()

    if choice == "1":
        return _migrate_choice_l4_with_stubs(target, agent, options, feature_dirs)
    if choice == "2":
        return _migrate_choice_l4_no_stubs(target, agent, options)
    if choice == "3":
        return _migrate_choice_delete_features(target, agent, options, features_dir)
    if choice == "4":
        return _migrate_choice_abort()

    print(f"\n  Invalid choice: {choice!r}. Aborting without changes.")
    return 1


def register(subparsers) -> None:
    """Register the `upgrade` subcommand and its arguments."""
    p = subparsers.add_parser(
        "upgrade",
        help="Refresh agent config and governed contracts to the current govkit version",
    )
    p.add_argument("--target", required=True, help=paths.TARGET_HELP)
    p.add_argument(
        "--force", action="store_true",
        help="Re-apply even when the project is already at the current govkit version",
    )
    p.add_argument(
        "--migrate-levels", action="store_true", dest="migrate_levels",
        help="Run the v0.6.x → v0.7.0 maturity-model migration "
             "(L3/L4 swap; interactive for legacy L3 projects)",
    )
    p.set_defaults(func=cmd_upgrade)
