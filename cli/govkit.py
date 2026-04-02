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
    govkit apply --agent claude-code --type api --ui react --ci github --target /path/to/project
    govkit list
    govkit init my_feature --target /path/to/project
    govkit init my_feature --starter backend --target /path/to/project
    govkit validate --target /path/to/project
"""

import argparse
import json
import shutil
import sys
from pathlib import Path


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


def resolve_variant_files(manifest: dict, options: dict) -> tuple[list, list]:
    """Collect files and shared entries from all selected variant dimensions, deduplicated."""
    all_files = list(manifest.get("base_files", []))
    all_shared: list[str] = []
    seen_files: set[tuple[str, str]] = {(f["src"], f["dest"]) for f in all_files}
    seen_shared: set[str] = set()
    variants = manifest.get("variants", {})
    for dimension, value in options.items():
        variant_group = variants.get(dimension, {})
        selected = variant_group.get(value, {})
        for f in selected.get("files", []):
            key = (f["src"], f["dest"])
            if key not in seen_files:
                all_files.append(f)
                seen_files.add(key)
        for s in selected.get("shared", []):
            if s not in seen_shared:
                all_shared.append(s)
                seen_shared.add(s)
    return all_files, all_shared


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
        print(f"\n  Configuration: {options}\n")
        files, shared = resolve_variant_files(manifest, options)

        print("Agent files:")
        for entry in files:
            src = agent_dir / entry["src"]
            dest = target / entry["dest"]
            copy_entry(src, dest)

        print("\nShared governance:")
        for shared_path in shared:
            src = REPO_ROOT / shared_path
            dest = target / shared_path
            copy_entry(src, dest, skip_existing=True)
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
            src = REPO_ROOT / shared_path
            dest = target / shared_path
            copy_entry(src, dest, skip_existing=True)

    print(f"\nDone. '{args.agent}' spec kit applied to {target}")


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


def cmd_init(args: argparse.Namespace) -> None:
    """Create a new feature folder from the appropriate starter template."""
    target = Path(args.target).resolve()
    features_dir = target / "features"
    if not features_dir.exists():
        print(f"Error: no features/ directory found in {target}. Run 'govkit apply' first.")
        sys.exit(1)

    feature_name = args.feature
    feature_dir = features_dir / feature_name
    if feature_dir.exists():
        print(f"Error: feature '{feature_name}' already exists at {feature_dir}")
        sys.exit(1)

    # Determine starter type
    starter_type = args.starter
    if starter_type is None:
        choices = ["backend", "cli", "ui"]
        prompt_text = f"  Feature type? [{' / '.join(choices)}] (default: backend): "
        answer = input(prompt_text).strip().lower()
        if answer == "":
            answer = "backend"
        if answer not in choices:
            print(f"Error: invalid choice '{answer}'. Must be one of: {', '.join(choices)}")
            sys.exit(1)
        starter_type = answer

    starter_dir = features_dir / f"starter_{starter_type}"
    if not starter_dir.exists():
        print(f"Error: starter template not found at {starter_dir}")
        sys.exit(1)

    copy_entry(starter_dir, feature_dir)
    print(f"\nCreated feature '{feature_name}' from starter_{starter_type}")
    print(f"  Location: {feature_dir}")
    print("\nNext steps:")
    print(f"  1. Edit {feature_dir / 'acceptance.feature'} — write your Gherkin scenarios")
    print(f"  2. Edit {feature_dir / 'nfrs.md'} — replace all TBD entries")
    print(f"  3. Run /architecture-preflight {feature_name}")


def cmd_validate(args: argparse.Namespace) -> None:
    from .validate import run_validation
    sys.exit(run_validation(Path(args.target).resolve()))


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
    apply_parser.add_argument("--type", choices=["api", "cli"], default=None,
                              help="Project type (default: prompted)")
    apply_parser.add_argument("--ui", choices=["none", "react", "angular"], default=None,
                              help="UI framework (default: prompted)")
    apply_parser.add_argument("--ci", choices=["github", "azure"], default=None,
                              help="CI platform (default: prompted)")

    # --- list ---
    subparsers.add_parser("list", help="List available agents and their options")

    # --- init ---
    init_parser = subparsers.add_parser("init", help="Create a new feature folder from a starter template")
    init_parser.add_argument("feature", help="Feature name (e.g. user-auth, schema-publish)")
    init_parser.add_argument("--target", default=".", help="Path to the target project root (default: current directory)")
    init_parser.add_argument("--starter", choices=["backend", "cli", "ui"], default=None,
                             help="Starter template type (default: prompted)")

    # --- validate ---
    validate_parser = subparsers.add_parser("validate", help="Check governance compliance in a project")
    validate_parser.add_argument("--target", required=True, help="Path to the target project root")

    args = parser.parse_args()

    if args.command == "apply":
        cmd_apply(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "init":
        cmd_init(args)
    elif args.command == "validate":
        cmd_validate(args)


if __name__ == "__main__":
    main()
