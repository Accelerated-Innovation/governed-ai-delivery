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

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from importlib.metadata import version as _pkg_version
    _GOVKIT_VERSION = _pkg_version("govkit")
except Exception:
    _GOVKIT_VERSION = "dev"


# ---------------------------------------------------------------------------
# Version comparison + one-time migration warning (Increment 9 — v0.7.0 swap)
# ---------------------------------------------------------------------------

# Set once per process. Reset by tests via _reset_migration_warning().
_MIGRATION_WARNING_PRINTED = False


def _compare_version(v1: str, v2: str) -> int:
    """Compare dotted version strings. Returns -1, 0, or 1.

    Non-parseable versions (e.g. 'dev', 'unknown') compare equal to anything,
    so development builds and corrupt markers don't trigger the migration
    warning.
    """
    try:
        t1 = tuple(int(p) for p in v1.split("."))
        t2 = tuple(int(p) for p in v2.split("."))
    except (ValueError, AttributeError):
        return 0
    if t1 < t2:
        return -1
    if t1 > t2:
        return 1
    return 0


def _maybe_warn_migration(stored_version: str | None) -> None:
    """Print one-time migration warning if marker version is pre-0.7.0.

    Suppressed by env var GOVKIT_NO_MIGRATION_WARNING=1 (for CI / scripts).
    Auto-suppressed once the marker is rewritten with version >= 0.7.0
    (because the version comparison stops triggering).
    """
    global _MIGRATION_WARNING_PRINTED
    if _MIGRATION_WARNING_PRINTED:
        return
    if not stored_version:
        return
    if os.environ.get("GOVKIT_NO_MIGRATION_WARNING") == "1":
        return
    if _compare_version(stored_version, "0.7.0") < 0:
        print(
            f"warning: .govkit marker version {stored_version} detected. "
            "The L3/L4 maturity model changed in 0.7.0. "
            "Run 'govkit upgrade --migrate-levels' to migrate. "
            "(Set GOVKIT_NO_MIGRATION_WARNING=1 to suppress.)",
            file=sys.stderr,
        )
        _MIGRATION_WARNING_PRINTED = True


def _reset_migration_warning() -> None:
    """Test helper: reset the one-time warning flag between test cases."""
    global _MIGRATION_WARNING_PRINTED
    _MIGRATION_WARNING_PRINTED = False


_SHAPE_MIGRATION_WARNING_PRINTED = False


def _maybe_warn_shape_migration(options: dict | None) -> None:
    """Print one-time warning when the marker carries the dropped `ui` option.

    The 0.7→0.8 project-shape refactor removed the `ui` dimension; the marker
    is read tolerantly so existing installs keep working, but the user is
    informed once per process. Suppressible via
    GOVKIT_NO_SHAPE_MIGRATION_WARNING=1.
    """
    global _SHAPE_MIGRATION_WARNING_PRINTED
    if _SHAPE_MIGRATION_WARNING_PRINTED:
        return
    if not options or "ui" not in options:
        return
    if os.environ.get("GOVKIT_NO_SHAPE_MIGRATION_WARNING") == "1":
        return
    print(
        "warning: .govkit marker carries the legacy 'ui' option. "
        "The project-shape model changed in 0.8.0. The `ui` option is no "
        "longer supported. Re-run 'govkit apply --type ui-react' (or "
        "'ui-angular') to switch to a UI shape, or 'govkit apply --type api' "
        "to keep the current backend shape. "
        "(Set GOVKIT_NO_SHAPE_MIGRATION_WARNING=1 to suppress.)",
        file=sys.stderr,
    )
    _SHAPE_MIGRATION_WARNING_PRINTED = True


def _reset_shape_migration_warning() -> None:
    """Test helper: reset the one-time shape-migration warning flag."""
    global _SHAPE_MIGRATION_WARNING_PRINTED
    _SHAPE_MIGRATION_WARNING_PRINTED = False

_HERE = Path(__file__).parent
# When installed via pip, agents/ is bundled inside the cli package.
# When running from the repo directly, fall back to the repo root.
AGENTS_DIR = _HERE / "agents" if (_HERE / "agents").exists() else _HERE.parent / "agents"
REPO_ROOT = AGENTS_DIR.parent


def load_manifest(agent: str) -> dict:
    manifest_path = AGENTS_DIR / agent / "manifest.json"
    if not manifest_path.exists():
        print(f"Error: no agent '{agent}' found. Run 'govkit list' to see available agents.")
        sys.exit(1)
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"Error: invalid JSON in {manifest_path}: {e}")
        sys.exit(1)
    required_keys = {"agent", "variants"}
    missing = required_keys - manifest.keys()
    if missing:
        print(f"Error: manifest for '{agent}' missing required keys: {', '.join(sorted(missing))}")
        sys.exit(1)
    return manifest


def copy_entry(src: Path, dest: Path, skip_existing: bool = False) -> None:
    if not src.exists():
        print(f"Error: source path does not exist: {src}")
        sys.exit(1)
    if src.is_dir():
        dest.mkdir(parents=True, exist_ok=True)
        for item in src.iterdir():
            copy_entry(item, dest / item.name, skip_existing=skip_existing)
    else:
        if skip_existing and dest.exists():
            print(f"  skipped {dest}  (already exists)")
            return
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        print(f"  copied  {dest}")


# ---------------------------------------------------------------------------
# .govkit marker
# ---------------------------------------------------------------------------

def read_govkit_level(target: Path) -> str | None:
    """Read the maturity level from the .govkit marker file, or None if not found.

    Delegates to read_govkit_marker so the one-time migration warning fires
    from any command that reads the level (cmd_init, cmd_validate, etc.).
    """
    data = read_govkit_marker(target)
    return data.get("level") if data else None


def read_govkit_marker(target: Path) -> dict | None:
    """Read the full .govkit marker dict, or None if missing or unreadable.

    Side effect: emits a one-time stderr warning when the stored version is
    pre-0.7.0 (the L3/L4 maturity-model swap). Suppressible via
    GOVKIT_NO_MIGRATION_WARNING=1.
    """
    marker = target / ".govkit"
    if not marker.exists():
        return None
    try:
        data = json.loads(marker.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    _maybe_warn_migration(data.get("version"))
    _maybe_warn_shape_migration(data.get("options"))
    return data


def write_govkit_marker(target: Path, agent: str, level: str, options: dict) -> None:
    """Write the .govkit marker file to track the applied configuration."""
    marker = target / ".govkit"
    data = {
        "version": _GOVKIT_VERSION,
        "level": level,
        "agent": agent,
        "options": {k: v for k, v in options.items() if k != "level"},
        "applied_at": datetime.now(timezone.utc).isoformat(),
    }
    marker.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"\n  .govkit marker written (level {level}, govkit {_GOVKIT_VERSION})")


# ---------------------------------------------------------------------------
# Variant resolution
# ---------------------------------------------------------------------------

def resolve_options(manifest: dict, args: argparse.Namespace) -> dict:
    """Resolve variant options from CLI flags or interactive prompts."""
    options_spec = manifest.get("options", {})
    resolved = {}
    for key, spec in options_spec.items():
        # Check CLI flag first
        cli_value = getattr(args, key, None)
        if cli_value is not None:
            resolved[key] = cli_value
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


def _dimension_entries(
    base: dict, override: dict | None, mode: str,
) -> tuple[list, list, list]:
    """Compute one dimension's effective (files, shared, governed) after applying override.

    merge mode (L4 default):
      - files: base entries whose `dest` collides with an override entry are dropped;
        override entries are appended after the surviving base entries (later wins on dest).
      - shared, governed: append override entries to base, dedup by string equality.

    replace mode (L5 default):
      - files, shared, governed: take only the override block's entries; ignore base.

    Cross-dimension accumulation (e.g. type.api + ui.react both contributing to
    .github/instructions/) is handled by `_collect_entries`, not here.
    """
    if override is None:
        return (
            list(base.get("files", [])),
            list(base.get("shared", [])),
            list(base.get("governed", [])),
        )
    if mode == "replace":
        return (
            list(override.get("files", [])),
            list(override.get("shared", [])),
            list(override.get("governed", [])),
        )
    # merge mode
    override_dests = {f["dest"] for f in override.get("files", [])}
    files = [f for f in base.get("files", []) if f["dest"] not in override_dests]
    files.extend(override.get("files", []))

    shared = list(base.get("shared", []))
    for s in override.get("shared", []):
        if s not in shared:
            shared.append(s)

    governed = list(base.get("governed", []))
    for g in override.get("governed", []):
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
    for dimension, value in options.items():
        if dimension == "level":
            continue
        base, override, mode = _select_variant(variants, dimension, value, level)
        files, shared, governed = _dimension_entries(base, override, mode)
        _collect_entries(
            files, shared, governed,
            all_files, seen_files,
            all_shared, seen_shared,
            all_governed, seen_governed,
        )
    return all_files, all_shared, all_governed


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_apply(args: argparse.Namespace) -> None:
    target = Path(args.target).resolve()
    if not target.exists():
        print(f"Error: target directory '{target}' does not exist.")
        sys.exit(1)

    manifest = load_manifest(args.agent)
    agent_dir = AGENTS_DIR / args.agent

    # Detect manifest format: variant-based (new) or flat (legacy)
    if "variants" in manifest:
        print(f"\nApplying govkit agent '{args.agent}' to {target}\n")
        options = resolve_options(manifest, args)
        level = options.get("level", "3")
        print(f"\n  Configuration: {options}\n")
        files, shared, governed = resolve_variant_files(manifest, options)

        print("Agent files:")
        for entry in files:
            src = agent_dir / entry["src"]
            dest = target / entry["dest"]
            copy_entry(src, dest)

        print("\nGoverned contracts (skip if present):")
        for governed_path in governed:
            if governed_path.startswith("features/"):
                continue
            src = REPO_ROOT / governed_path
            dest = target / governed_path
            copy_entry(src, dest, skip_existing=True)

        print("\nShared governance:")
        for shared_path in shared:
            if shared_path.startswith("features/"):
                continue
            src = REPO_ROOT / shared_path
            dest = target / shared_path
            copy_entry(src, dest, skip_existing=True)

        # L3 (Foundations) ships agent rules + architecture contracts only.
        # The features/ directory model is part of the L4 Spec-Driven Add-On.
        if level != "3":
            features_dir = target / "features"
            if not features_dir.exists():
                features_dir.mkdir(parents=True)
                print(f"  Created {features_dir} (empty)")

        write_govkit_marker(target, args.agent, level, options)
    else:
        # Legacy flat manifest — backward compatibility
        print(f"\nApplying govkit agent '{args.agent}' to {target}\n")
        print("Agent files:")
        for entry in manifest["files"]:
            src = agent_dir / entry["src"]
            dest = target / entry["dest"]
            copy_entry(src, dest)

        print("\nShared governance:")
        for shared_path in manifest.get("shared", []):
            if shared_path.startswith("features/"):
                continue
            src = REPO_ROOT / shared_path
            dest = target / shared_path
            copy_entry(src, dest, skip_existing=True)

        features_dir = target / "features"
        if not features_dir.exists():
            features_dir.mkdir(parents=True)
            print(f"  Created {features_dir} (empty)")

    print(f"\nDone. '{args.agent}' spec kit applied to {target}")
    print("\nNext step: add your first feature package.")
    print("  govkit init <feature-name> --target <target>   # scaffold from a starter template")
    print("  or drop a feature folder manually into features/")


def cmd_list(_args: argparse.Namespace) -> None:
    print("\nAvailable agents:\n")
    for agent_dir in sorted(AGENTS_DIR.iterdir()):
        if not agent_dir.is_dir():
            continue
        manifest_path = agent_dir / "manifest.json"
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as e:
                print(f"  Warning: failed to read {manifest_path}: {e}")
                continue
            name = manifest["agent"]
            desc = manifest.get("description", "")
            options = manifest.get("options", {})
            if options:
                opts_summary = " | ".join(
                    f"{k}: {', '.join(v['choices'])}" for k, v in options.items()
                )
                print(f"  {name:<20} {desc}")
                print(f"  {'':20} options: {opts_summary}")
            else:
                print(f"  {name:<20} {desc}")
    print()


def _prompt_starter_type() -> str:
    """Interactively prompt for the starter template type."""
    choices = ["backend", "cli", "ui-react", "ui-angular"]
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
    bundled = REPO_ROOT / "features"
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
    sys.exit(run_validation(target, level=level))


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

    if stored_version == _GOVKIT_VERSION and not args.force:
        print(f"\nAlready at govkit {_GOVKIT_VERSION}. Nothing to upgrade.")
        print("Use --force to re-apply even when the version is current.")
        return

    print(f"\nUpgrading govkit {stored_version} → {_GOVKIT_VERSION}")
    print(f"  Agent: {agent}  Level: {stored_level}\n")

    manifest = load_manifest(agent)
    agent_dir = AGENTS_DIR / agent
    options = {**stored_options, "level": stored_level}
    files, shared, governed = resolve_variant_files(manifest, options)

    print("Agent files (refreshed):")
    for entry in files:
        src = agent_dir / entry["src"]
        dest = target / entry["dest"]
        copy_entry(src, dest)

    print("\nGoverned contracts (refreshed):")
    for governed_path in governed:
        if governed_path.startswith("features/"):
            continue
        src = REPO_ROOT / governed_path
        dest = target / governed_path
        copy_entry(src, dest)

    print("\nShared governance (skip if present):")
    for shared_path in shared:
        if shared_path.startswith("features/"):
            continue
        src = REPO_ROOT / shared_path
        dest = target / shared_path
        copy_entry(src, dest, skip_existing=True)

    write_govkit_marker(target, agent, stored_level, options)
    print(f"\nDone. '{agent}' upgraded to govkit {_GOVKIT_VERSION} at {target}")
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


def _migrate_l3_interactive(
    target: Path, stored_version: str, agent: str, options: dict,
) -> int:
    """Interactive 4-option prompt for v0.6 L3 (3-artifact) projects."""
    features_dir = target / "features"
    feature_dirs = _list_user_features(features_dir)

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
    print(f"      Marker becomes level=4, version={_GOVKIT_VERSION}.")
    print("  [2] Migrate to L4 — do NOT generate stubs. You will author the two new")
    print("      artifacts per feature manually. Validation will fail until you do.")
    print(f"      Marker becomes level=4, version={_GOVKIT_VERSION}.")
    print("  [3] Adopt new-L3 (Foundations) — you confirm we should DELETE features/")
    print("      and switch to architecture-only governance.")
    print(f"      Marker becomes level=3, version={_GOVKIT_VERSION}.")
    print("  [4] Abort — make no changes. Pin govkit==0.6.* in your project.\n")

    choice = input("  Choice [1-4]: ").strip()

    if choice == "1":
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

    if choice == "2":
        write_govkit_marker(target, agent, "4", options)
        print("\n  Marker rewritten without stub generation.")
        print("  Next: author eval_criteria.yaml and architecture_preflight.md per")
        print("  feature manually. `govkit validate` will fail until you do.")
        return 0

    if choice == "3":
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

    if choice == "4":
        print("\n  No changes made.")
        print("  Pin `govkit==0.6.*` in your project until you're ready to migrate.")
        return 0

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
    apply_parser.add_argument("--target", required=True, help="Path to the target project root")
    apply_parser.add_argument("--level", choices=["3", "4", "5"], default=None,
                              help="Maturity level (default: prompted)")
    apply_parser.add_argument("--type", choices=["api", "cli", "ui-react", "ui-angular"], default=None,
                              help="Project type (default: prompted)")
    apply_parser.add_argument("--ci", choices=["github", "azure"], default=None,
                              help="CI platform (default: prompted)")

    # --- list ---
    subparsers.add_parser("list", help="List available agents and their options")

    # --- init ---
    init_parser = subparsers.add_parser("init", help="Create a new feature folder from a starter template")
    init_parser.add_argument("feature", help="Feature name (e.g. user-auth, schema-publish)")
    init_parser.add_argument("--target", default=".", help="Path to the target project root (default: current directory)")
    init_parser.add_argument("--starter", choices=["backend", "cli", "ui-react", "ui-angular"], default=None,
                             help="Starter template type (default: prompted)")
    init_parser.add_argument("--level", choices=["3", "4", "5"], default=None,
                             help="Maturity level (default: read from .govkit or 4)")

    # --- validate ---
    validate_parser = subparsers.add_parser("validate", help="Check governance compliance in a project")
    validate_parser.add_argument("--target", required=True, help="Path to the target project root")
    validate_parser.add_argument("--level", choices=["3", "4", "5"], default=None,
                                 help="Maturity level (default: read from .govkit or 4)")

    # --- upgrade ---
    upgrade_parser = subparsers.add_parser(
        "upgrade",
        help="Refresh agent config and governed contracts to the current govkit version",
    )
    upgrade_parser.add_argument("--target", required=True, help="Path to the target project root")
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
    elif args.command == "init":
        cmd_init(args)
    elif args.command == "validate":
        cmd_validate(args)
    elif args.command == "upgrade":
        cmd_upgrade(args)


if __name__ == "__main__":
    main()
