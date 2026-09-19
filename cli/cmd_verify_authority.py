#!/usr/bin/env python3
# Copyright 2026 Accelerated Innovation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
"""govkit verify-authority — is this baseline currently authorized by the PDG?

**Opt-in, and off by default.** GovKit is open source and most projects using
it have no PDG. `.govkit/marker.json` records `authority.source`, absent
meaning `none`, and a project in that state gets *not applicable* — not a
failure, not a warning, not a degraded mode. The question does not arise, and
everything local still works: `govkit validate-baseline` answers whether the
spec drifted from what was approved without touching a network.

**"No PDG" and "PDG unreachable" are different states.** Conflating them is
the defect this command is shaped around, and it fails in both directions:
spurious failures for adopters who never had a PDG, or silent passes for an
AIPOS project whose engine is down.

**Enforcement lives at the call site.** Advisory by default, `--enforce` for
the protected boundary. A marker field named `enforce` would be one line to
flip in a pull request, and it would flip a gate while reading as a setting.

The token comes from `GOVKIT_PDG_TOKEN` — a read-only verification
credential. Installing a checker must not hand anything the authority to make
an approval.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import paths, pdg_client
from .authority_check import Outcome, PdgUnreachable, Result, exit_status, verify

TOKEN_ENV = "GOVKIT_PDG_TOKEN"


def _authority(target: Path) -> dict:
    """The project's authority configuration, defaulting to none.

    An absent key means `none`, so every existing install keeps working
    untouched and AIPOS enforcement stays an explicit adoption rather than a
    reinterpretation of what someone already had.
    """
    marker = target / ".govkit" / "marker.json"
    if not marker.is_file():
        return {"source": "none"}
    try:
        data = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"source": "none"}
    return data.get("authority") or {"source": "none"}


def cmd_verify_authority(args: argparse.Namespace) -> None:
    target = Path(args.target).resolve()
    authority = _authority(target)

    if (authority.get("source") or "none") != "pdg":
        print(
            "not applicable: this project does not verify against a PDG "
            "(.govkit/marker.json has no authority.source = pdg).\n"
            "`govkit validate-baseline` still checks the spec against its approved "
            "revision, which needs no PDG."
        )
        sys.exit(0)

    baseline_path = Path(args.baseline).resolve()
    if not baseline_path.is_file():
        print(f"baseline file not found: {baseline_path}", file=sys.stderr)
        sys.exit(2)
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))

    base_url = authority.get("base_url")
    if not base_url:
        print("authority.source is pdg but no base_url is configured", file=sys.stderr)
        sys.exit(2)

    token = os.environ.get(TOKEN_ENV)
    if not token:
        # Undetermined, not rejection: no credential means the question could
        # not be asked, and answering "not authorized" would send someone to
        # re-approve a baseline that is fine.
        result = Result(
            Outcome.UNDETERMINED,
            f"no verification credential: set {TOKEN_ENV} to a read-only PDG token",
        )
    else:
        def fetch(commitment_id: str) -> dict:
            status = pdg_client.fetch_status(base_url, commitment_id, token=token)
            if status is None:
                # The PDG looked and found nothing. A definite answer.
                raise _NoSuchCommitment(commitment_id)
            return status

        try:
            result = verify(baseline, commitment_id=args.commitment, fetch=fetch)
        except _NoSuchCommitment as absent:
            result = Result(
                Outcome.NOT_AUTHORIZED,
                f"the PDG has no commitment {absent.commitment_id!r}",
            )
        except ValueError as misconfigured:
            result = Result(Outcome.UNDETERMINED, str(misconfigured))
        except PdgUnreachable as unreachable:  # pragma: no cover - fetch wraps these
            result = Result(Outcome.UNDETERMINED, str(unreachable))

    _report(result, enforced=bool(args.enforce))
    sys.exit(exit_status(result.outcome, enforced=bool(args.enforce)))


class _NoSuchCommitment(RuntimeError):
    def __init__(self, commitment_id: str) -> None:
        super().__init__(commitment_id)
        self.commitment_id = commitment_id


def _report(result: Result, *, enforced: bool) -> None:
    """Never prints the token, and never prints evidence text: the binding is
    identifiers and digests, and this output lands in CI logs."""
    if result.outcome is Outcome.AUTHORIZED:
        print(f"authorized: {result.detail}")
        return
    if result.outcome is Outcome.NOT_AUTHORIZED:
        print(f"NOT AUTHORIZED: {result.detail}", file=sys.stderr)
        return
    label = "UNKNOWN" if enforced else "authorization unverified"
    print(f"{label}: {result.detail}", file=sys.stderr)
    if not enforced:
        print(
            "Continuing: this is an advisory check. The protected boundary runs it "
            "with --enforce, where an unknown answer fails closed.",
            file=sys.stderr,
        )


def register(subparsers) -> None:
    """Register the `verify-authority` subcommand and its arguments."""
    p = subparsers.add_parser(
        "verify-authority",
        help="Check whether the PDG currently authorizes this baseline",
    )
    p.add_argument("--target", required=True, help=paths.TARGET_HELP)
    p.add_argument("--baseline", required=True, help="Path to the baseline JSON")
    p.add_argument("--commitment", default=None,
                   help="The commitment id the PDG recorded for this baseline")
    p.add_argument(
        "--enforce", action="store_true",
        help="Fail closed: exit non-zero unless the PDG confirms current authority. "
             "For the protected boundary; omit for advisory local checks.",
    )
    p.set_defaults(func=cmd_verify_authority)
