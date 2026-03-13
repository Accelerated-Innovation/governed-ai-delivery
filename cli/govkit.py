#!/usr/bin/env python3
"""
govkit — governed AI delivery kit installer

Usage:
    python cli/govkit.py apply --agent copilot --target /path/to/project
    python cli/govkit.py list
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
    return json.loads(manifest_path.read_text())


def copy_entry(src: Path, dest: Path, skip_existing: bool = False) -> None:
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


def cmd_apply(args: argparse.Namespace) -> None:
    target = Path(args.target).resolve()
    if not target.exists():
        print(f"Error: target directory '{target}' does not exist.")
        sys.exit(1)

    manifest = load_manifest(args.agent)
    agent_dir = AGENTS_DIR / args.agent

    print(f"\nApplying govkit agent '{args.agent}' to {target}\n")

    print("Agent files:")
    for entry in manifest["files"]:
        src = agent_dir / entry["src"]
        dest = target / entry["dest"]
        copy_entry(src, dest)

    print("\nShared governance:")
    for shared in manifest.get("shared", []):
        src = REPO_ROOT / shared
        dest = target / shared
        copy_entry(src, dest, skip_existing=True)

    print(f"\nDone. '{args.agent}' spec kit applied to {target}")


def cmd_list(_args: argparse.Namespace) -> None:
    print("\nAvailable agents:\n")
    for agent_dir in sorted(AGENTS_DIR.iterdir()):
        manifest_path = agent_dir / "manifest.json"
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text())
            print(f"  {manifest['agent']:<20} {manifest.get('description', '')}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="govkit",
        description="governed AI delivery kit — apply spec scaffolding to a project",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    apply_parser = subparsers.add_parser("apply", help="Apply an agent spec kit to a target project")
    apply_parser.add_argument("--agent", required=True, help="Agent name (e.g. copilot)")
    apply_parser.add_argument("--target", required=True, help="Path to the target project root")

    list_parser = subparsers.add_parser("list", help="List available agents")

    args = parser.parse_args()

    if args.command == "apply":
        cmd_apply(args)
    elif args.command == "list":
        cmd_list(args)


if __name__ == "__main__":
    main()
