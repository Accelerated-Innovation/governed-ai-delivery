#!/usr/bin/env python3
# Copyright 2026 Accelerated Innovation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
govkit — governed AI delivery kit installer

Usage:
    govkit apply --agent claude-code --target /path/to/project
    govkit apply --agent claude-code --level 3 --type api --ci github --target /path/to/project
    govkit list
    govkit init my_feature --target /path/to/project
    govkit init my_feature --starter backend --target /path/to/project
    govkit validate --target /path/to/project
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from . import paths, version
from .cmd_apply import cmd_apply
from .cmd_init import _resolve_starter_dir as _resolve_starter_dir
from .cmd_init import cmd_init
from .cmd_list import cmd_list
from .cmd_stack import cmd_stack_apply, cmd_stack_list
from .cmd_validate import cmd_validate
from .fs import copy_entry
from .fs import is_user_edited as is_user_edited
from .install_common import (
    copy_governed_or_shared,
    exclude_for_level,
    post_install_finalize,
)
from .manifest import load_manifest, resolve_variant_files
from .manifest import resolve_options as resolve_options
from .marker import (
    _compare_version,
    read_govkit_marker,
    write_govkit_marker,
)
from .marker import (
    _reset_directory_migration_warning as _reset_directory_migration_warning,
)
from .marker import (
    _reset_migration_warning as _reset_migration_warning,
)
from .marker import (
    _reset_shape_migration_warning as _reset_shape_migration_warning,
)
from .marker import read_govkit_level as read_govkit_level

# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

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
    agent_dir = paths.AGENTS_DIR / agent
    options = {**stored_options, "level": stored_level}
    files, shared, governed = resolve_variant_files(manifest, options)

    # Edit-protection (A2): governed/shared overwrites consult applied_at and
    # respect --force. Agent files (the `files` category) are unconditionally
    # refreshed because they are govkit-managed and don't carry editable
    # headers.
    prior_applied_at = stored.get("applied_at")
    baseline = f"govkit@{version.GOVKIT_VERSION}"

    print("Agent files (refreshed):")
    for entry in files:
        src = agent_dir / entry["src"]
        dest = target / entry["dest"]
        copy_entry(src, dest)

    # PR 6c: keep L5-only docs out of L3/L4 upgrades too.
    l5_exclude = exclude_for_level(stored_level)

    print("\nGoverned contracts (refreshed, edit-protected):")
    copy_governed_or_shared(
        governed, target, prior_applied_at, args.force, baseline, l5_exclude,
        skip_existing=False,
    )
    print("\nShared governance (skip if present):")
    copy_governed_or_shared(
        shared, target, prior_applied_at, args.force, baseline, l5_exclude,
    )

    marker = write_govkit_marker(target, agent, stored_level, options)
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


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="govkit",
        description="governed AI delivery kit — apply spec scaffolding to a project",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- apply ---
    apply_parser = subparsers.add_parser("apply", help="Apply an agent spec kit to a target project")
    apply_parser.add_argument("--agent", required=True, help="Agent name (e.g. claude-code, copilot)")
    apply_parser.add_argument("--target", required=True, help=paths.TARGET_HELP)
    apply_parser.add_argument("--level", choices=["3", "4", "5"], default=None,
                              help="Maturity level (default: prompted)")
    apply_parser.add_argument("--type", choices=["api", "cli", "ui-react", "ui-angular", "data"], default=None,
                              help="Project type (default: prompted)")
    apply_parser.add_argument("--ci", choices=["github", "azure"], default=None,
                              help="CI platform (default: prompted)")
    apply_parser.add_argument(
        "--stack", default=None,
        help="Stack overlay id (default: python-fastapi). Run `govkit stack list` "
             "to see available stacks.",
    )
    apply_parser.add_argument(
        "--detect", action="store_true",
        help="Dry-run: run repo inference, print the proposed config, and exit "
             "without writing anything to the target",
    )
    apply_parser.add_argument(
        "--force", action="store_true",
        help="Override edit-protection and overwrite user-edited governed/shared "
             "docs (those carrying a govkit:editable header)",
    )

    # --- list ---
    subparsers.add_parser("list", help="List available agents and their options")

    # --- stack ---
    stack_parser = subparsers.add_parser(
        "stack",
        help="List or apply bundled stack overlays",
    )
    stack_sub = stack_parser.add_subparsers(dest="stack_command", required=True)
    stack_sub.add_parser("list", help="List bundled stack overlays")
    stack_apply_parser = stack_sub.add_parser(
        "apply",
        help="Re-apply a stack overlay over an existing install",
    )
    stack_apply_parser.add_argument(
        "stack_id",
        help="Stack overlay id (e.g. dotnet-aspnet). See `govkit stack list`.",
    )
    stack_apply_parser.add_argument(
        "--target", required=True,
        help="Path to the target project root (must contain a .govkit marker)",
    )
    stack_apply_parser.add_argument(
        "--force", action="store_true",
        help="Override edit-protection and overwrite user-edited stack docs",
    )

    # --- init ---
    init_parser = subparsers.add_parser("init", help="Create a new feature folder from a starter template")
    init_parser.add_argument("feature", help="Feature name (e.g. user-auth, schema-publish)")
    init_parser.add_argument("--target", default=".", help="Path to the target project root (default: current directory)")
    init_parser.add_argument("--starter", choices=["backend", "cli", "ui-react", "ui-angular", "data"], default=None,
                             help="Starter template type (default: prompted)")
    init_parser.add_argument("--level", choices=["3", "4", "5"], default=None,
                             help="Maturity level (default: read from .govkit or 4)")

    # --- doctor ---
    doctor_parser = subparsers.add_parser(
        "doctor",
        help="Read-only governance fit validator. Run in CI to surface "
             "mismatches between installed governance and the actual repo.",
    )
    doctor_parser.add_argument(
        "--target", default=None,
        help="Path to the install root (defaults to scanning cwd for .govkit/ "
             "markers; finds nested installs in monorepos)",
    )

    # --- calibrate ---
    calibrate_parser = subparsers.add_parser(
        "calibrate",
        help="Guided review of installed governance. Walks the team "
             "through the 9-step checklist from plan Section 7.",
    )
    calibrate_parser.add_argument(
        "--target", default=None,
        help="Path to the install root (defaults to scanning cwd for .govkit/ "
             "markers; finds nested installs in monorepos)",
    )
    calibrate_parser.add_argument(
        "--non-interactive", action="store_true", dest="non_interactive",
        help="Skip prompts and write GOVKIT_CALIBRATION_CHECKLIST.md as a "
             "todo file. Useful in CI bootstraps and for new repos the team "
             "will calibrate later.",
    )
    calibrate_parser.add_argument(
        "--only", default=None,
        help="Run only the named step (e.g. 'tech_stack', 'rules'). Useful "
             "for revisiting a single decision without walking the whole list.",
    )

    # --- validate ---
    validate_parser = subparsers.add_parser("validate", help="Check governance compliance in a project")
    validate_parser.add_argument("--target", required=True, help=paths.TARGET_HELP)
    validate_parser.add_argument("--level", choices=["3", "4", "5"], default=None,
                                 help="Maturity level (default: read from .govkit or 4)")
    validate_parser.add_argument("--strict", action="store_true",
                                 help="Promote extension manifest warnings to failures")

    # --- upgrade ---
    upgrade_parser = subparsers.add_parser(
        "upgrade",
        help="Refresh agent config and governed contracts to the current govkit version",
    )
    upgrade_parser.add_argument("--target", required=True, help=paths.TARGET_HELP)
    upgrade_parser.add_argument(
        "--force", action="store_true",
        help="Re-apply even when the project is already at the current govkit version",
    )
    upgrade_parser.add_argument(
        "--migrate-levels", action="store_true", dest="migrate_levels",
        help="Run the v0.6.x → v0.7.0 maturity-model migration "
             "(L3/L4 swap; interactive for legacy L3 projects)",
    )

    args = parser.parse_args()

    if args.command == "apply":
        cmd_apply(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "stack":
        if args.stack_command == "list":
            cmd_stack_list(args)
        elif args.stack_command == "apply":
            cmd_stack_apply(args)
    elif args.command == "init":
        cmd_init(args)
    elif args.command == "doctor":
        from .doctor import cmd_doctor
        cmd_doctor(args)
    elif args.command == "calibrate":
        from .calibrate import cmd_calibrate
        cmd_calibrate(args)
    elif args.command == "validate":
        cmd_validate(args)
    elif args.command == "upgrade":
        cmd_upgrade(args)


if __name__ == "__main__":
    main()
