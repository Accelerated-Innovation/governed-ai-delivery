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

from . import paths
from .cmd_apply import cmd_apply
from .cmd_init import _resolve_starter_dir as _resolve_starter_dir
from .cmd_init import cmd_init
from .cmd_list import cmd_list
from .cmd_stack import cmd_stack_apply, cmd_stack_list
from .cmd_upgrade import cmd_upgrade
from .cmd_validate import cmd_validate
from .fs import copy_entry as copy_entry
from .fs import is_user_edited as is_user_edited
from .manifest import load_manifest as load_manifest
from .manifest import resolve_options as resolve_options
from .manifest import resolve_variant_files as resolve_variant_files
from .marker import _reset_directory_migration_warning as _reset_directory_migration_warning
from .marker import _reset_migration_warning as _reset_migration_warning
from .marker import _reset_shape_migration_warning as _reset_shape_migration_warning
from .marker import read_govkit_level as read_govkit_level
from .marker import read_govkit_marker as read_govkit_marker
from .marker import write_govkit_marker as write_govkit_marker

# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

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
