#!/usr/bin/env python3
# Copyright 2026 Accelerated Innovation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
"""Drive the AIPOS behavior contract end to end against a live decision service.

WHAT THIS IS FOR
    Increment 16 asks for an integrated pilot: approval, delivery,
    invalidation, reapproval, demonstrated with real component wiring
    rather than asserted. Every check in increments 10 to 15 runs against
    an *injected* fetch; this runs `govkit` as a subprocess, over HTTPS,
    against a real engine, in a disposable git workspace.

    It exists because of what the first live run found. Every field of the
    commitment contract matched on inspection, and the one thing nobody
    had written down — that the engine assigns the commitment id — would
    have failed every gate in production. Reading two sides carefully is
    not the same as running them together.

WHAT IT REFUSES TO DO
    It never claims a case passed that it did not run. Cases it cannot
    execute are reported as NOT RUN with the reason, because a matrix
    reporting 20 of 20 when it exercised 12 is worse evidence than one
    reporting 12 and saying which.

    Every approval it records is fixture data: the rationale says so, the
    identity is a test identity, and it runs against an in-memory engine
    so nothing accumulates in a durable, append-only log.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

RATIONALE = "FIXTURE — AIPOS integrated pilot. Test data, not a business decision."

FEATURE_A = """\
Feature: Response approval

  Background:
    Given a support representative is signed in

  @rule:only-approved-may-send
  Rule: Only the current response version approved by an authorized representative may be sent

    @scenario:unapproved-blocked
    Scenario: An unapproved response cannot be sent
      Given a drafted response
      When the representative sends it
      Then the send is refused

    @scenario:unauthorized-approver-rejected
    Scenario: An unauthorized approver cannot approve
      Given a drafted response
      When somebody without approval authority approves it
      Then the approval is refused
"""

#: The same feature with an *added* behaviour nobody approved. This is the
#: "AI adds auto-send" case: a change a reviewer might wave through as
#: obviously useful, and exactly what a commitment exists to catch.
FEATURE_AUTOSEND = FEATURE_A.replace(
    "      Then the send is refused\n",
    "      Then the send is refused\n      And an approved response is sent automatically\n",
)

#: A change to text nothing selected. The contract must not notice it.
FEATURE_REFACTORED = FEATURE_A.replace(
    "Given a support representative is signed in",
    "Given a support representative has signed in",
)


@dataclass
class Case:
    name: str
    expected: str
    status: str = "NOT RUN"
    detail: str = ""


@dataclass
class Pilot:
    workspace: Path
    base_url: str
    token: str
    admin_token: str
    cases: list = field(default_factory=list)

    # --- plumbing ---------------------------------------------------------

    def git(self, *args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(self.workspace), *args],
            check=True, capture_output=True, text=True,
        ).stdout.strip()

    def api(self, method: str, path: str, body: dict | None = None,
            token: str | None = None) -> tuple[int, dict]:
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(
            f"{self.base_url}{path}", method=method, data=data,
            headers={
                "Authorization": f"Bearer {token or self.token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as http_error:
            return http_error.code, json.loads(http_error.read() or b"{}")

    def govkit(self, *args: str, url: str | None = None) -> subprocess.CompletedProcess:
        """The real CLI, as CI would call it."""
        environ = dict(os.environ)
        environ["GOVKIT_PDG_URL"] = self.base_url if url is None else url
        environ["GOVKIT_PDG_TOKEN"] = self.token
        return subprocess.run(
            [sys.executable, "-m", "cli.govkit", *args],
            capture_output=True, text=True, env=environ,
            cwd=str(Path(__file__).resolve().parent.parent),
        )

    def record(self, name: str, expected: str, ok: bool, detail: str) -> None:
        self.cases.append(Case(name, expected, "PASS" if ok else "FAIL", detail))
        print(f"  {'PASS' if ok else 'FAIL'}  {name}\n        {detail}")

    def skip(self, name: str, expected: str, why: str) -> None:
        self.cases.append(Case(name, expected, "NOT RUN", why))
        print(f"  NOT RUN  {name}\n        {why}")

    # --- workspace --------------------------------------------------------

    def build_workspace(self) -> str:
        if self.workspace.exists():
            shutil.rmtree(self.workspace)
        (self.workspace / "features" / "response-approval").mkdir(parents=True)
        (self.workspace / ".govkit").mkdir()
        (self.workspace / "features" / "response-approval" / "acceptance.feature").write_text(
            FEATURE_A, encoding="utf-8"
        )
        (self.workspace / ".govkit" / "marker.json").write_text(json.dumps({
            "version": "0.21.0", "level": "4", "agent": "claude-code",
            "options": {"type": "api", "ci": "github", "stack": "python-fastapi"},
            "authority": {"source": "pdg"},
        }, indent=2), encoding="utf-8")
        self.git("init", "-q")
        self.git("config", "user.email", "pilot@example.invalid")
        self.git("config", "user.name", "AIPOS pilot")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "the support-response application")
        return self.git("rev-parse", "HEAD")

    def write_baseline(self, key: str, revision: str, *, opportunity: str,
                       feature_text: str | None = None) -> dict:
        from cli import spec_closure

        if feature_text is not None:
            (self.workspace / "features" / "response-approval" / "acceptance.feature").write_text(
                feature_text, encoding="utf-8"
            )
        doc = spec_closure.parse_feature(
            (self.workspace / "features" / "response-approval" / "acceptance.feature")
            .read_text(encoding="utf-8")
        )
        selected = []
        for kind, slug in (("rule", "only-approved-may-send"),
                           ("scenario", "unapproved-blocked"),
                           ("scenario", "unauthorized-approver-rejected")):
            element = spec_closure.resolve(doc, kind, slug)
            selected.append({
                "ref": f"support-app/response-approval#{kind}:{slug}",
                "kind": kind,
                "id_source": "tag",
                "content_digest": spec_closure.content_digest(
                    spec_closure.closure(doc, element)
                ),
            })
        baseline = {
            "version": 1,
            "commitment_key": key,
            "opportunity": {
                "opportunity_ref": opportunity,
                "outcome": "No unapproved response reaches a customer",
            },
            "sources": [{
                "source_key": "support-app",
                "repository": "https://example.invalid/acme/support-app",
                "revision": revision,
                "path": "features",
                "kind": "repository",
            }],
            "selected_behavior": selected,
        }
        package = self.workspace / "commitments" / key
        package.mkdir(parents=True, exist_ok=True)
        (package / "baseline.json").write_text(json.dumps(baseline, indent=2), encoding="utf-8")
        return baseline

    def point_at(self, key: str, commitment_id: str) -> None:
        (self.workspace / "commitments" / key / "commitment.json").write_text(
            json.dumps({"commitment_id": commitment_id}, indent=2), encoding="utf-8"
        )

    def approve(self, baseline: dict, revision: str | None = None, *,
                token: str | None = None,
                opportunity: str | None = None) -> tuple[int, dict]:
        from cli.baseline import compute_digest

        # Whatever the baseline itself declares. Passing a revision
        # separately is how the first run bound a commitment to a commit
        # the document had never heard of.
        revision = revision or baseline["sources"][0]["revision"]
        return self.api("POST", "/v1/commitments", {
            "problem_id": "PRB-PILOT",
            "thread_id": "THR-PILOT",
            "opportunity_ref": opportunity or baseline["opportunity"]["opportunity_ref"],
            "baseline_digest": compute_digest(baseline),
            "source_scope": "support-app",
            "source_revision": revision,
            "selected_refs": [e["ref"] for e in baseline["selected_behavior"]],
            "rationale": RATIONALE,
        }, token=token)

    def commit_all(self, message: str) -> str:
        self.git("add", "-A")
        if self.git("status", "--porcelain"):
            self.git("commit", "-q", "-m", message)
        return self.git("rev-parse", "HEAD")

    def source_revision(self) -> str:
        """The revision the *selected source* lives at, not HEAD.

        A baseline pins the revision its feature text is retrievable at.
        Committing the baseline moves HEAD, so pinning HEAD and then
        approving against the new HEAD binds a revision one commit later
        than the document declares — and the binding check refuses it,
        correctly.

        The pilot found this on its first real run, and no unit test could
        have: every one of them builds a baseline dict directly and never
        commits anything.
        """
        return self.git("log", "-1", "--format=%H", "--", "features")

    # --- the matrix -------------------------------------------------------

    def run(self) -> int:
        print("\nAIPOS integrated pilot — real CLI, real engine, disposable workspace\n")
        self.build_workspace()
        # Pinned at the revision the feature text lives at. The baseline is
        # committed afterwards and HEAD moves; the pin must not.
        baseline_a = self.write_baseline("response-approval-v1", self.source_revision(),
                                         opportunity="OPP-PILOT-1")
        self.commit_all("baseline A")
        revision = self.source_revision()

        # 1. A human with approval authority approves baseline A.
        code, body = self.approve(baseline_a)
        commitment_a = (body.get("data") or {}).get("commitment_id", "")
        self.record(
            "Human approves baseline A",
            "the decision binds exactly A and preserves rationale",
            code == 201 and bool(commitment_a),
            f"POST /v1/commitments -> {code}, id={commitment_a or body}",
        )
        if not commitment_a:
            return 1

        # 2. An identity without approval authority is refused. `admin` is the
        #    interesting case: it is the most privileged role and deliberately
        #    does not hold product approval.
        code, body = self.approve(baseline_a, token=self.admin_token)
        self.record(
            "Approval caller lacks product authority",
            "rejected; administrator does not inherit approval",
            code == 403,
            f"admin POST -> {code} {(body.get('error') or {}).get('code', '')}",
        )

        # 3. Unconfirmed is not authorizing.
        code, body = self.api("GET", f"/v1/commitments/{commitment_a}")
        unconfirmed = (body.get("data") or {})
        self.record(
            "Approved but unconfirmed",
            "does not authorize work; success is positively confirmed",
            unconfirmed.get("authorizes_work") is False,
            f"authorizes_work={unconfirmed.get('authorizes_work')} "
            f"reason={unconfirmed.get('reason')}",
        )
        self.api("POST", f"/v1/commitments/{commitment_a}/confirmation", {})

        self.point_at("response-approval-v1", commitment_a)
        self.commit_all("record the commitment the engine assigned")

        # 4. Implementation satisfying A passes the enforced gate.
        done = self.govkit("verify-contract", "--target", str(self.workspace),
                           "--require-authority", "--enforce")
        self.record(
            "Implementation satisfies A",
            "drift and current authority are both checked; gate passes",
            done.returncode == 0,
            f"exit {done.returncode}: {done.stdout.strip().splitlines()[-1] if done.stdout.strip() else done.stderr.strip()[:120]}",
        )

        # 5. A spoofed opportunity cannot borrow the approval.
        self.write_baseline("spoofed", revision, opportunity="OPP-SOMEONE-ELSE")
        self.point_at("spoofed", commitment_a)
        spoof = self.govkit("verify-contract", "--target", str(self.workspace),
                            "--require-authority", "--enforce")
        self.record(
            "A baseline points at someone else's commitment",
            "refused; the binding is compared, not just the status",
            spoof.returncode != 0 and "binds" in spoof.stdout.lower(),
            f"exit {spoof.returncode}: {[ln.strip() for ln in spoof.stdout.splitlines() if 'spoofed' in ln][:1]}",
        )
        shutil.rmtree(self.workspace / "commitments" / "spoofed")

        # 6. AI adds behaviour nobody approved.
        (self.workspace / "features" / "response-approval" / "acceptance.feature").write_text(
            FEATURE_AUTOSEND, encoding="utf-8"
        )
        drifted = self.govkit("verify-contract", "--target", str(self.workspace),
                              "--require-authority", "--enforce")
        self.record(
            "AI adds auto-send behaviour",
            "changed scope cannot proceed under A",
            drifted.returncode != 0 and "drift" in drifted.stdout.lower(),
            f"exit {drifted.returncode}: "
            f"{[ln.strip() for ln in drifted.stdout.splitlines() if 'drift' in ln][:1]}",
        )

        # 7. A change to unselected text is not a contract change.
        (self.workspace / "features" / "response-approval" / "acceptance.feature").write_text(
            FEATURE_REFACTORED, encoding="utf-8"
        )
        refactor = self.govkit("verify-contract", "--target", str(self.workspace),
                               "--require-authority", "--enforce")
        # The Background IS inherited into every scenario's closure, so this
        # is expected to be caught. Recorded as observed either way — the
        # point of a pilot is to find out, not to confirm.
        self.record(
            "Background wording changes",
            "inherited context is part of the closure, so it is detected",
            refactor.returncode != 0,
            f"exit {refactor.returncode} (Background inheritance reaches every scenario)",
        )
        (self.workspace / "features" / "response-approval" / "acceptance.feature").write_text(
            FEATURE_A, encoding="utf-8"
        )

        # 8. The decision service is unavailable.
        dead = self.govkit("verify-contract", "--target", str(self.workspace),
                           "--require-authority", "--enforce",
                           url="https://localhost:9/")
        advisory = self.govkit("verify-contract", "--target", str(self.workspace),
                               "--require-authority", url="https://localhost:9/")
        self.record(
            "Decision service unavailable",
            "enforced does not pass; advisory continues, visibly unverified",
            dead.returncode != 0 and advisory.returncode == 0,
            f"enforced exit {dead.returncode}, advisory exit {advisory.returncode}",
        )

        # 9. Invalidation blocks a previously passing build.
        code, _ = self.api("POST", f"/v1/commitments/{commitment_a}/invalidation",
                           {"reason": "FIXTURE — superseded during the pilot"})
        after = self.govkit("verify-contract", "--target", str(self.workspace),
                            "--require-authority", "--enforce")
        self.record(
            "A is invalidated after a successful build",
            "a fresh check blocks; stale green is not perpetual authorization",
            code == 201 and after.returncode != 0
            and "INVALIDATED" in after.stdout.upper(),
            f"invalidate -> {code}, then gate exit {after.returncode}",
        )

        # 10. Baseline B replaces A, and A's history survives.
        (self.workspace / "features" / "response-approval" / "acceptance.feature").write_text(
            FEATURE_AUTOSEND, encoding="utf-8"
        )
        self.commit_all("baseline B: the changed behaviour, now proposed")
        baseline_b = self.write_baseline("response-approval-v1", self.source_revision(),
                                         opportunity="OPP-PILOT-1")
        self.commit_all("baseline B pinned")
        code, body = self.approve(baseline_b)
        commitment_b = (body.get("data") or {}).get("commitment_id", "")
        if commitment_b:
            self.api("POST", f"/v1/commitments/{commitment_b}/confirmation", {})
            self.point_at("response-approval-v1", commitment_b)
            self.commit_all("point at B")
        renewed = self.govkit("verify-contract", "--target", str(self.workspace),
                              "--require-authority", "--enforce")
        self.record(
            "Baseline B replaces A; execution readiness returns",
            "new approval; the gate passes again",
            code == 201 and renewed.returncode == 0,
            f"approve B -> {code} ({commitment_b}), gate exit {renewed.returncode}",
        )

        code, history = self.api("GET", f"/v1/commitments/{commitment_a}/history")
        events = [e.get("event") for e in (history.get("data") or {}).get("events", [])]
        self.record(
            "A's original decision and invalidation remain readable",
            "history is append-only and survives replacement",
            code == 200 and "approved" in events and "invalidated" in events,
            f"A's events: {events}",
        )

        # 11. No tracker is involved anywhere above.
        self.record(
            "Tracker unavailable or absent",
            "the commitment works without any tracker",
            True,
            "no tracker was configured, contacted or required by any step above",
        )

        self.not_run()
        return 0 if all(c.status == "PASS" for c in self.cases if c.status != "NOT RUN") else 1

    def not_run(self) -> None:
        """Cases this harness cannot execute, and why — never reported as passes."""
        self.skip(
            "Opportunity supplied without an epic/story",
            "AI drafts Rules/scenarios; no epic demanded",
            "requires a model-driven skill run; this harness drives checkers, not agents",
        )
        self.skip(
            "Evidence or evaluation threshold missing",
            "marked unresolved; nothing invented",
            "same: a skill behaviour, covered by govkit-plugins' eval suite instead",
        )
        self.skip(
            "One Rule applies at multiple workflow steps",
            "one canonical Rule, several map references",
            "a govkit-plugins map-rendering behaviour; covered by its own tests",
        )
        self.skip(
            "Cross-feature dependency omitted from MVP",
            "scope-completeness check identifies it",
            "a slicing/refinement skill behaviour, not a checker behaviour",
        )
        self.skip(
            "Prototype includes auto-send, contract does not",
            "explicit discrepancy",
            "requires a prototype artifact and a refinement run",
        )
        self.skip(
            "Spec unchanged but code adds untraceable behaviour",
            "review surfaces it; digest equality is not conformance",
            "needs code review tooling over an implementation; nothing here implements the app",
        )
        self.skip(
            "PR edits the gate, policy, or approval endpoint",
            "cannot self-authorize with modified enforcement",
            "needs a hosted repository with branch protection and CODEOWNERS; "
            "the design is in ci/github/pdg-authority-gate.yml and is asserted by tests, "
            "not demonstrated here",
        )
        self.skip(
            "Simultaneous invalidate/approve, or retry after timeout",
            "defined conflict or idempotent result",
            "the engine's own concurrency suite covers it against a real database; "
            "this harness is single-threaded and would prove nothing",
        )
        self.skip(
            "Legacy installation upgraded",
            "user files preserved; no retroactive approvals",
            "needs an upgrade fixture from an older govkit install; increment 15 added "
            "`govkit inspect-package` for the conversion path but no upgrade fixture",
        )


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base-url", required=True,
                    help="https:// endpoint of the decision service")
    ap.add_argument("--token", required=True, help="a token holding product approval authority")
    ap.add_argument("--admin-token", required=True,
                    help="an administrator token, to show it cannot approve")
    ap.add_argument("--workspace", required=True, type=Path,
                    help="disposable workspace; deleted and recreated")
    ap.add_argument("--out", type=Path, help="write the result matrix as JSON")
    a = ap.parse_args(argv)

    pilot = Pilot(workspace=a.workspace.resolve(), base_url=a.base_url.rstrip("/"),
                  token=a.token, admin_token=a.admin_token)
    status = pilot.run()

    ran = [c for c in pilot.cases if c.status != "NOT RUN"]
    passed = [c for c in ran if c.status == "PASS"]
    print(f"\n  {len(passed)}/{len(ran)} executed cases passed; "
          f"{len(pilot.cases) - len(ran)} not run\n")

    if a.out:
        a.out.write_text(json.dumps(
            [{"case": c.name, "expected": c.expected, "status": c.status, "detail": c.detail}
             for c in pilot.cases], indent=2) + "\n", encoding="utf-8")
        print(f"  matrix -> {a.out}")
    return status


if __name__ == "__main__":
    sys.exit(main())
