#!/usr/bin/env python3
# Copyright 2026 Accelerated Innovation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
"""govkit verify-contract — every commitment in this repository, one command.

The seam both CI providers call. `verify-authority` answers one question
about one baseline a human pointed it at; this answers both questions about
every commitment package in the tree, which is what a protected boundary
needs: the acceptance criterion is that *spec drift, invalidation, missing
evidence, changed enforcement policy, or an untrusted checker* cannot get
past it, and four of those five are invisible to a single-baseline check.

Exit codes are the contract, because a shell step reads nothing else:

  0  everything checked passed, or the project has no PDG and the caller
     did not assert that it should
  1  a check failed, or could not be completed, under `--enforce`
  2  the gate itself is misconfigured — no endpoint, unreadable marker

`1` and `2` are kept apart on purpose. A failing gate means look at the
change; a misconfigured gate means look at the pipeline, and conflating them
sends people to re-approve baselines that are fine.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from . import contract_gate, paths, pdg_client
from .authority_check import PdgUnreachable
from .cmd_verify_authority import TOKEN_ENV, URL_ENV, MarkerUnreadable, _authority


def _fetch_via(base_url: str, token: str):
    def fetch(commitment_id: str) -> dict:
        status = pdg_client.fetch_status(base_url, commitment_id, token=token)
        if status is None:
            # The PDG looked and found nothing — a definite answer about
            # this commitment, not a failure to ask.
            raise _NoSuchCommitment(commitment_id)
        return status
    return fetch


class _NoSuchCommitment(PdgUnreachable):
    """Raised where `fetch` must answer, translated by the caller below.

    Subclasses `PdgUnreachable` so a caller that forgets to translate it
    degrades to *undetermined* rather than crashing the gate — the safe
    direction when enforced, since undetermined fails closed.
    """

    def __init__(self, commitment_id: str) -> None:
        super().__init__(f"the PDG has no commitment {commitment_id!r}")
        self.commitment_id = commitment_id


def cmd_verify_contract(args: argparse.Namespace) -> None:
    target = Path(args.target).resolve()
    enforced = bool(getattr(args, "enforce", False))
    require = bool(getattr(args, "require_authority", False))

    try:
        authority = _authority(target)
    except MarkerUnreadable as unreadable:
        print(f"cannot determine this project's authority configuration: {unreadable}",
              file=sys.stderr)
        sys.exit(2)

    if (authority.get("source") or "none") != "pdg":
        if require:
            print(
                "expected this project to verify against a PDG "
                "(--require-authority), but .govkit/marker.json does not set "
                "authority.source = pdg",
                file=sys.stderr,
            )
            sys.exit(1)
        print(
            "not applicable: this project does not verify against a PDG.\n"
            "`govkit validate-baseline` still checks each spec against its approved "
            "revision, which needs no PDG."
        )
        sys.exit(0)

    base_url = os.environ.get(URL_ENV)
    if not base_url:
        print(
            f"set {URL_ENV} to the PDG endpoint. It is deliberately not read from "
            f"the repository: an endpoint from the working tree plus a credential "
            f"from the environment would let a pull request collect the token.",
            file=sys.stderr,
        )
        sys.exit(2)

    token = os.environ.get(TOKEN_ENV)
    if token:
        fetch = _fetch_via(base_url, token)
    else:
        # No credential means the question could not be asked. Undetermined,
        # which fails an enforced gate and advises an unenforced one — never
        # "not authorized", which would send someone to re-approve a
        # baseline whose only problem is a missing token.
        def fetch(commitment_id: str) -> dict:
            raise PdgUnreachable(
                f"no verification credential: set {TOKEN_ENV} to a read-only PDG token"
            )

    report = contract_gate.run(target, fetch=fetch, require_commitments=require)
    _report(report, enforced=enforced)
    sys.exit(contract_gate.exit_status(report, enforced=enforced))


def _report(report: contract_gate.GateReport, *, enforced: bool) -> None:
    for problem in report.problems:
        print(f"  {problem}")

    for package in report.packages:
        if package.error:
            print(f"  {package.key}: REFUSED — {package.error}")
            continue
        drift = package.drift
        if drift is not None and not drift.ok:
            for difference in drift.differences:
                print(f"  {package.key}: drift — {difference.ref}: {difference.detail}")
            for refusal in drift.refusals:
                print(f"  {package.key}: could not check — {refusal}")
        authority = {True: "authorized", False: "NOT authorized", None: "unverified"}[
            package.authorized
        ]
        print(f"  {package.key}: {authority} — {package.authority_detail}")

    if report.ok:
        print(f"  contract: {len(report.packages)} commitment(s) current and undrifted")
    elif not enforced:
        # Advisory. Saying so matters: an exit code of zero beside a list of
        # failures otherwise reads as a bug in the gate.
        print("  advisory only — this run does not block. The gate at merge does.")


def register(subparsers) -> None:
    """Register the `verify-contract` subcommand."""
    p = subparsers.add_parser(
        "verify-contract",
        help="Check every commitment in this repository for drift and current authority",
    )
    p.add_argument("--target", required=True, help=paths.TARGET_HELP)
    p.add_argument("--require-authority", action="store_true",
                   help="Fail if this project is not configured to verify against a "
                        "PDG, or declares no commitments. For a protected boundary, "
                        "so a change to the repository cannot disable the gate.")
    p.add_argument("--enforce", action="store_true",
                   help="Fail closed: exit non-zero unless every commitment is "
                        "undrifted and currently authorized. For the protected "
                        "boundary; omit for advisory local checks.")
    p.set_defaults(func=cmd_verify_contract)
