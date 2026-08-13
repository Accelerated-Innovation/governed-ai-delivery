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
"""`govkit fix` — scaffold a defect-lane fix record.

A defect that restores already-established behavior carries one schema-backed
record instead of the five-artifact feature contract. This writes the skeleton;
`govkit validate` then checks the eligibility conditions.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from . import paths
from .fixes import FIX_RECORD_FILE, FIX_RECORD_SKELETON, FIXES_DIR
from .marker import read_govkit_marker

# Mirrors the schema's `id` pattern. Checked here so a bad id fails at creation
# rather than producing a record that can never validate.
_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


def cmd_fix_init(args: argparse.Namespace) -> None:
    """Create `fixes/<id>/fix.yaml` from the skeleton."""
    target = Path(args.target).resolve()
    stored = read_govkit_marker(target) or {}

    # Level gate first, before any other check — mirrors cmd_init.
    level = args.level or stored.get("level") or "3"
    if level == "3":
        print(
            "Error: 'govkit fix init' requires Level 4 (Spec-Driven Add-On) or higher.\n"
            "  Level 3 (Foundations) ships agent rules and architecture contracts only;\n"
            "  it has no per-change artifact model, so there is nothing for a fix\n"
            "  record to sit alongside.\n"
            "  Run 'govkit apply --level 4 --target <path>' first."
        )
        sys.exit(1)

    fix_id = args.fix_id
    if not _ID_PATTERN.match(fix_id):
        print(
            f"Error: '{fix_id}' is not a valid fix id.\n"
            "  Use lowercase letters, digits, and . _ - (starting with a letter\n"
            "  or digit) — e.g. 'task-filter-reset'. The id is also the directory\n"
            "  name, and govkit validate requires the two to match."
        )
        sys.exit(1)

    record_dir = target / FIXES_DIR / fix_id
    record_path = record_dir / FIX_RECORD_FILE
    if record_path.exists():
        print(f"Error: fix record '{fix_id}' already exists at {record_path}")
        sys.exit(1)

    record_dir.mkdir(parents=True, exist_ok=True)
    record_path.write_text(FIX_RECORD_SKELETON.format(id=fix_id), encoding="utf-8")

    print(f"Created {record_path}\n")
    print("Next steps:")
    print(f"  1. Replace every TODO in {record_path}")
    print("  2. `expectation.source` must point at the requirement, contract, or ADR")
    print("     that established the behavior — a fix with no source is new behavior,")
    print("     and belongs in the feature lane instead")
    print("  3. `reproduction.test` must point at a test that fails before the fix")
    print("  4. Run `govkit validate --target .` to check eligibility")


def register(subparsers) -> None:
    """Register the `fix` subcommand tree (`fix init`)."""
    fix_parser = subparsers.add_parser(
        "fix",
        help="Scaffold a defect-lane fix record",
    )
    fix_sub = fix_parser.add_subparsers(dest="fix_command", required=True)

    init_parser = fix_sub.add_parser(
        "init", help="Create fixes/<id>/fix.yaml from the skeleton"
    )
    init_parser.add_argument(
        "fix_id",
        help="Fix id, also the directory name (e.g. task-filter-reset)",
    )
    init_parser.add_argument("--target", default=".", help=paths.TARGET_HELP)
    init_parser.add_argument(
        "--level", choices=["3", "4", "5"], default=None,
        help="Maturity level (default: read from .govkit)",
    )
    init_parser.set_defaults(func=cmd_fix_init)
