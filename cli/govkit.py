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
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .detect import RepoProfile

from . import paths, version
from .cmd_list import cmd_list
from .cmd_stack import cmd_stack_apply, cmd_stack_list
from .fs import copy_entry
from .fs import is_user_edited as is_user_edited
from .manifest import load_manifest, resolve_options, resolve_variant_files
from .marker import (
    _compare_version,
    read_govkit_level,
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
from .stack_select import (
    apply_stack_overlay,
    print_detection_summary,
    resolve_stack_choice,
)

# PR 6c: L5-only architecture docs. These live in docs/backend/architecture/
# alongside the universal baseline files for repo-self-governance purposes,
# but they must NOT install at L3/L4 — doctor D007 (LLM-leakage in non-L5)
# is the canary. Future PR may relocate these into a separate dir and drop
# the exclusion machinery.
_L5_ONLY_GOVERNED_BASENAMES: set[str] = {
    "AGENT_ARCHITECTURE.md",
    "LLM_GATEWAY_CONTRACT.md",
    "GUARDRAILS_CONTRACT.md",
    "OBSERVABILITY_LLM_CONTRACT.md",
    "EVALUATION_LLM_CONTRACT.md",
}


def _exclude_for_level(level: str) -> set[str] | None:
    """Return basenames to exclude from governed copy at this level.

    None at L5 (everything ships); the L5-only set at L3/L4.
    """
    if level == "5":
        return None
    return _L5_ONLY_GOVERNED_BASENAMES


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def _cmd_apply_detect_dry_run(target: Path, args: argparse.Namespace) -> None:
    """`govkit apply --detect`: print the inferred configuration and exit
    without writing anything to the target.

    Useful before a real apply so the user can confirm the inferred stack
    matches their expectations, and for CI scripts that want to log what
    govkit would do without committing to a write.
    """
    from .detect import build_profile, infer_stack

    profile = build_profile(target)
    inferred_stack, inferred_confidence = infer_stack(profile)

    # Delegate to resolve_stack_choice so the dry-run reports the same stack
    # real apply would pick — including the type-compatibility check that
    # rejects e.g. python-fastapi inference when --type data is requested.
    type_value = getattr(args, "type", None) or "api"
    chosen_stack, stack_source, _, _ = resolve_stack_choice(
        getattr(args, "stack", None), type_value,
        profile, inferred_stack, inferred_confidence, target,
    )

    print(f"\n[dry-run --detect] govkit apply would target: {target}\n")
    print_detection_summary(
        profile, inferred_stack, inferred_confidence,
        chosen_stack, stack_source,
    )
    print("\nProposed configuration:")
    print(f"  agent:  {getattr(args, 'agent', '(none)')}")
    print(f"  level:  {getattr(args, 'level', '(prompted)')}")
    print(f"  type:   {getattr(args, 'type', '(prompted)')}")
    print(f"  ci:     {getattr(args, 'ci', '(prompted)')}")
    print(f"  stack:  {chosen_stack}  (source: {stack_source})")
    print("\nNo files written. Re-run without --detect to apply.")


def _copy_governed_or_shared(
    rel_paths: list, target: Path, prior_applied_at: str | None,
    force: bool, baseline: str, exclude: set[str] | None,
    skip_existing: bool = True,
) -> None:
    """Copy each governed/shared dir from the bundle (REPO_ROOT) to target.

    `features/` entries are deferred — those land via `govkit init`, not
    apply/upgrade. `skip_existing=True` (the default) is correct for `apply`
    governed/shared and for `upgrade` shared. `upgrade` governed passes
    `skip_existing=False` because upgrade re-installs governed contracts.
    """
    for rel in rel_paths:
        if rel.startswith(paths.FEATURES_PREFIX):
            continue
        copy_entry(
            paths.REPO_ROOT / rel, target / rel,
            skip_existing=skip_existing,
            applied_at=prior_applied_at,
            force=force,
            header_baseline=baseline,
            exclude_basenames=exclude,
        )


def _create_features_dir_if_missing(target: Path) -> None:
    """Create `features/` under target if absent. Idempotent."""
    features_dir = target / "features"
    if not features_dir.exists():
        features_dir.mkdir(parents=True)
        print(f"  Created {features_dir} (empty)")


def _ensure_features_dir(target: Path, level: str) -> None:
    """L3 ships agent rules + architecture contracts only. L4/L5 also get an
    empty `features/` so `govkit init <feature>` has somewhere to scaffold."""
    if level == "3":
        return
    _create_features_dir_if_missing(target)


def _apply_variant_install(
    target: Path, args: argparse.Namespace, manifest: dict, agent_dir: Path,
    prior_applied_at: str | None, force: bool, baseline: str,
) -> tuple[dict, RepoProfile | None]:
    """Variant-based manifest path (new format used by all 3 production agents).

    Returns `(marker, profile)` so the caller can thread both into
    `_post_install_finalize` and skip one marker read + one repo-tree walk.
    """
    print(f"\nApplying govkit agent '{args.agent}' to {target}\n")
    options = resolve_options(manifest, args)
    level = options.get("level", "3")
    print(f"\n  Configuration: {options}\n")
    files, shared, governed = resolve_variant_files(manifest, options)

    print("Agent files:")
    for entry in files:
        copy_entry(agent_dir / entry["src"], target / entry["dest"])

    l5_exclude = _exclude_for_level(level)
    print("\nGoverned contracts (skip if present):")
    _copy_governed_or_shared(governed, target, prior_applied_at, force, baseline, l5_exclude)
    print("\nShared governance:")
    _copy_governed_or_shared(shared, target, prior_applied_at, force, baseline, l5_exclude)

    _ensure_features_dir(target, level)

    stack_meta, stack_assumption, options, profile = apply_stack_overlay(
        target, getattr(args, "stack", None), options, prior_applied_at, force,
    )

    marker = write_govkit_marker(
        target, args.agent, level, options,
        stack=stack_meta,
        assumptions=[stack_assumption] if stack_assumption else [],
    )
    return marker, profile


def _apply_legacy_install(
    target: Path, args: argparse.Namespace, manifest: dict, agent_dir: Path,
    prior_applied_at: str | None, force: bool, baseline: str,
) -> tuple[dict | None, None]:
    """Pre-variant flat-manifest path; retained for back-compat with custom agents.

    Returns `(None, None)` — legacy manifests don't write a govkit marker,
    so `_post_install_finalize` will read from disk if needed (it'll find
    nothing and no-op cleanly).
    """
    print(f"\nApplying govkit agent '{args.agent}' to {target}\n")
    print("Agent files:")
    for entry in manifest["files"]:
        copy_entry(agent_dir / entry["src"], target / entry["dest"])

    print("\nShared governance:")
    _copy_governed_or_shared(
        manifest.get("shared", []), target, prior_applied_at, force, baseline, None,
    )

    _create_features_dir_if_missing(target)
    return None, None


def _post_install_finalize(
    target: Path, agent: str,
    marker: dict | None = None, profile: RepoProfile | None = None,
) -> None:
    """Write derived files (setup review + skill_context), re-template rule
    globs to match the team's actual layout, print the post-install checklist.

    `marker` and `profile` may be passed in by callers that already have them
    in hand (cmd_apply, cmd_upgrade) so we skip a redundant marker read +
    repo-tree walk. If omitted, both are derived from disk/target.

    No-op when no marker is available (something earlier failed)."""
    from .extensions import report_extensions
    report_extensions(target)

    if marker is None:
        marker = read_govkit_marker(target)
    if marker is None:
        return
    from .rule_templating import template_installed_rules
    from .setup_review import print_review_checklist, write_setup_review
    from .skill_context import load_skill_context, write_skill_context
    write_setup_review(target, marker)
    write_skill_context(target, marker, profile=profile)
    sc = load_skill_context(target)
    if sc is not None:
        template_installed_rules(target, agent, sc.layers)
    print_review_checklist(target, marker)


def cmd_apply(args: argparse.Namespace) -> None:
    target = Path(args.target).resolve()
    if not target.exists():
        print(f"Error: target directory '{target}' does not exist.")
        sys.exit(1)

    # PR 3 / Chunk D: --detect runs inference and exits without writing.
    if getattr(args, "detect", False):
        _cmd_apply_detect_dry_run(target, args)
        return

    manifest = load_manifest(args.agent)
    agent_dir = paths.AGENTS_DIR / args.agent

    # Edit-protection (A2): consult any prior marker for applied_at so
    # governed/shared docs the user has edited since last apply are protected.
    prior_marker = read_govkit_marker(target)
    prior_applied_at = prior_marker.get("applied_at") if prior_marker else None
    force = bool(getattr(args, "force", False))
    baseline = f"govkit@{version.GOVKIT_VERSION}"

    # Variant manifests are the post-v0.6 format used by all 3 production
    # agents; the flat path is retained for custom agents on the old layout.
    if "variants" in manifest:
        marker, profile = _apply_variant_install(
            target, args, manifest, agent_dir, prior_applied_at, force, baseline,
        )
    else:
        marker, profile = _apply_legacy_install(
            target, args, manifest, agent_dir, prior_applied_at, force, baseline,
        )

    _post_install_finalize(target, args.agent, marker=marker, profile=profile)

    print(f"\nDone. '{args.agent}' spec kit applied to {target}")
    print("\nNext step: add your first feature package.")
    print("  govkit init <feature-name> --target <target>   # scaffold from a starter template")
    print("  or drop a feature folder manually into features/")


def _prompt_starter_type() -> str:
    """Interactively prompt for the starter template type."""
    choices = ["backend", "cli", "ui-react", "ui-angular", "data"]
    prompt_text = f"  Feature type? [{' / '.join(choices)}] (default: backend): "
    answer = input(prompt_text).strip().lower()
    if answer == "":
        answer = "backend"
    if answer not in choices:
        print(f"Error: invalid choice '{answer}'. Must be one of: {', '.join(choices)}")
        sys.exit(1)
    return answer


def _starter_dir_slug(starter_type: str) -> str:
    """Map a starter_type to its bundled directory slug.

    Most types map 1:1 (backend → starter_backend). UI variants currently
    share a single framework-agnostic starter — both ui-react and ui-angular
    resolve to starter_ui. If they diverge later, separate starter_ui_react
    and starter_ui_angular dirs can be added without resolver changes (the
    1:1 path is the default).
    """
    if starter_type in ("ui-react", "ui-angular"):
        return "ui"
    return starter_type


def _resolve_starter_dir(starter_type: str, level: str) -> Path:
    """Select the level-appropriate starter directory from the bundled govkit templates.

    L3 (Foundations) has no feature starter — `govkit init` is gated to L4+.
    """
    if level == "3":
        raise ValueError(
            "L3 (Governed AI Delivery — Foundations) has no feature starter. "
            "Run 'govkit apply --level 4' first to enable the spec-driven feature workflow."
        )
    bundled = paths.REPO_ROOT / "features"
    slug = _starter_dir_slug(starter_type)
    if level == "5":
        level_dir = bundled / f"starter_{slug}_l5"
        if level_dir.exists():
            return level_dir
    return bundled / f"starter_{slug}"


def cmd_init(args: argparse.Namespace) -> None:
    """Create a new feature folder from the appropriate starter template."""
    target = Path(args.target).resolve()

    # Determine level early so we can gate L3 before any other checks.
    level = args.level or read_govkit_level(target) or "3"

    if level == "3":
        print(
            "Error: 'govkit init' requires Level 4 (Spec-Driven Add-On) or higher.\n"
            "  Level 3 (Foundations) ships agent rules and architecture contracts only;\n"
            "  it has no features/ directory model.\n"
            "  Run 'govkit apply --level 4 --target <path>' to enable the spec-driven\n"
            "  feature workflow, then re-run 'govkit init'."
        )
        sys.exit(1)

    features_dir = target / "features"
    if not features_dir.exists():
        print(f"Error: no features/ directory found in {target}. Run 'govkit apply' first.")
        sys.exit(1)

    feature_name = args.feature
    feature_dir = features_dir / feature_name
    if feature_dir.exists():
        print(f"Error: feature '{feature_name}' already exists at {feature_dir}")
        sys.exit(1)

    starter_type = args.starter or _prompt_starter_type()
    starter_dir = _resolve_starter_dir(starter_type, level)

    if not starter_dir.exists():
        print(f"Error: starter template not found at {starter_dir}")
        sys.exit(1)

    copy_entry(starter_dir, feature_dir)
    print(f"\nCreated feature '{feature_name}' from {starter_dir.name} (level {level})")
    print(f"  Location: {feature_dir}")
    print("\nNext steps:")
    print(f"  1. Edit {feature_dir / 'acceptance.feature'} — write your Gherkin scenarios")
    print(f"  2. Edit {feature_dir / 'nfrs.md'} — replace all TBD entries")
    if level == "5":
        print(f"  3. Run /architecture-preflight {feature_name}")
        print(f"  4. Run /genai-preflight {feature_name}")
    else:  # L4
        print(f"  3. Run /architecture-preflight {feature_name}")
        print(f"  4. Run /spec-planning {feature_name}")


def cmd_validate(args: argparse.Namespace) -> None:
    from .validate import run_validation
    target = Path(args.target).resolve()
    level = args.level
    strict = getattr(args, "strict", False)
    sys.exit(run_validation(target, level=level, strict=strict))


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
    l5_exclude = _exclude_for_level(stored_level)

    print("\nGoverned contracts (refreshed, edit-protected):")
    _copy_governed_or_shared(
        governed, target, prior_applied_at, args.force, baseline, l5_exclude,
        skip_existing=False,
    )
    print("\nShared governance (skip if present):")
    _copy_governed_or_shared(
        shared, target, prior_applied_at, args.force, baseline, l5_exclude,
    )

    marker = write_govkit_marker(target, agent, stored_level, options)
    _post_install_finalize(target, agent, marker=marker)

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
