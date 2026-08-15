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
"""`govkit verdict` — may an autonomous run open a pull request?

For the harness driving a bug-fix agent, not for a human at a keyboard. See
`cli/verdict.py` for why the answer cannot come from the agent or its exit code.
"""

from __future__ import annotations

import argparse
import json
import shlex
import sys
from pathlib import Path

from .verdict import EXIT_CODES, assess

_LABEL = {"pass": "PASS", "fail": "FAIL", "skip": "----"}

_NEXT_STEP = {
    "FIXED": "Commit and open the PR.",
    "REJECTED": "Do not open a PR, and do not retry blind — a human reads this.",
    "REFUSED": "The agent declined. This is a success: no PR, no retry.",
    "BLOCKED": "Stopped at a gate only a human can clear. Escalate; do not retry.",
}


def cmd_verdict(args: argparse.Namespace) -> None:
    target = Path(args.target).resolve()
    if not target.is_dir():
        print(f"Error: target directory '{target}' does not exist.", file=sys.stderr)
        sys.exit(1)

    roots = tuple(r.strip() for r in (args.source_roots or "").split(",") if r.strip())
    if not roots:
        print(
            "Error: --source-roots is required. govkit will not guess which "
            "paths are application source; `.govkit/skill_context.yaml` records "
            "what was detected under architecture.source_root, but an empty "
            "value there means 'no single root' and is not a value to paste in.",
            file=sys.stderr,
        )
        sys.exit(1)

    command = shlex.split(args.test_command) if args.test_command else None
    result = assess(
        target,
        base=args.base or "",
        source_roots=roots,
        test_command=command,
        run_validate=not args.no_validate,
    )

    if args.json:
        print(json.dumps({
            "verdict": result.verdict,
            "exit_code": result.exit_code,
            "target": str(target),
            "gates": [
                {"status": g.status, "gate": g.gate, "detail": g.detail}
                for g in result.gates
            ],
        }, indent=2))
        sys.exit(result.exit_code)

    print(f"\ngovkit verdict — {result.verdict}  (exit {result.exit_code})\n")
    for gate in result.gates:
        print(f"  {_LABEL.get(gate.status, gate.status):<4}  {gate.gate:<28}  {gate.detail}")
    print(f"\n{_NEXT_STEP.get(result.verdict, '')}\n")
    sys.exit(result.exit_code)


def register(subparsers) -> None:
    """Register the `verdict` subcommand and its arguments."""
    codes = ", ".join(f"{name}={code}" for name, code in EXIT_CODES.items())
    p = subparsers.add_parser(
        "verdict",
        help="Decide whether an autonomous run may open a PR. For a calling "
             f"harness: exit codes are {codes}.",
    )
    p.add_argument("--target", default=".", help="Path to the repository the agent ran in")
    p.add_argument(
        "--base", default="",
        help="Ref the run started from. Required when the agent committed its "
             "own work; omit for a run left uncommitted in the working tree.",
    )
    p.add_argument(
        "--source-roots", default="",
        help="Comma-separated application source prefixes, e.g. 'src/,lib/'. "
             "Required: govkit will not guess.",
    )
    p.add_argument(
        "--test-command", default="",
        help="Command that runs the suite, e.g. 'pytest -q' or 'go test ./...'. "
             "Without it the red-before-green gate cannot run and nothing is "
             "certified — an unverified reproduction is not a verified one.",
    )
    p.add_argument(
        "--no-validate", action="store_true",
        help="Skip the `govkit validate` gate (it is run by default)",
    )
    p.add_argument("--json", action="store_true", help="Emit machine-readable output")
    p.set_defaults(func=cmd_verdict)
