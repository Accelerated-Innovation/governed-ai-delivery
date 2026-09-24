# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Actual-change conformance assembled from trusted policy and independent checks."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path

from . import check_adapters as adapters
from .change_architecture import assess_architecture
from .change_defects import defect_check
from .change_policy import load_change_policy
from .change_scope import capture_change
from .check_models import (
    CheckContext,
    CheckOutcome,
    CheckSpec,
    Evidence,
    Execution,
    Finding,
    Identity,
    State,
)
from .check_runner import CheckRegistry, CheckReport, parse_report, run_checks
from .pack_loading import contained_file
from .pack_store import locked_check_requirements
from .profiles import load_profile
from .schema_validation import (
    DocumentError,
    canonical_json,
    content_digest,
    read_document,
    validate_document,
)
from .workflow_store import parse_workflow_plan, plan_request
from .workflows import SENSITIVE, NormalizedRequest, RequestPlan, _covers


@dataclass(frozen=True)
class ChangeReport:
    change: dict
    plan: RequestPlan
    checks: CheckReport

    @property
    def exit_code(self):
        return self.checks.exit_code

    @property
    def state(self):
        return self.checks.state

    @property
    def document(self):
        return {
            "schema_version": 1,
            "kind": "change-results",
            "change": self.change,
            "plan": self.plan.document,
            "checks": self.checks.to_document(),
            "state": self.state.value,
            "exit_code": self.exit_code,
            "limitations": [
                "Policy checkout, accepted intent and Git base must be selected by a trusted caller; local records are not authenticated approval.",
                "Git-visible working-tree observations are bounded and are not a filesystem transaction. Ignored untracked files and unconfigured semantic controls are unmeasured.",
                "I04 engine limitations apply to the nested check execution; this outer record adds actual-change routing. No consolidated maintenance assessment is performed.",
            ],
        }

    def to_json(self):
        return canonical_json(self.document)


def load_change_report(path: Path) -> ChangeReport:
    document = read_document(path)
    validate_document(document, "change-results")
    result = ChangeReport(
        document["change"], parse_workflow_plan(document["plan"]), parse_report(document["checks"])
    )
    if (
        result.checks.identity.change_digest
        != content_digest(canonical_json(result.change).encode())
        or result.checks.identity.profile_digest
        != result.plan.document["identity"]["profile_digest"]
        or result.checks.identity.resolution_digest != result.plan.identity
        or result.checks.identity.pack_lock_digest
        != result.plan.document["identity"]["lock_digest"]
        or result.checks.identity.revision != result.change["revision"]
        or result.checks.identity.dirty_digest != result.change["tree_digest"]
        or result.document != document
    ):
        raise DocumentError("Change report identities/outcomes do not match their recorded inputs")
    return result


def _outcome(state, summary, proof, *, code=None, location=None):
    findings = (
        ()
        if code is None
        else (
            Finding(
                code,
                "error" if state is State.FAIL else "info" if state is State.PASS else "warning",
                "change",
                summary,
                "Resolve the decision/evidence and rerun conformance.",
                location,
                proof,
            ),
        )
    )
    return CheckOutcome(state, Execution.EXECUTED, summary, findings, proof)


def _command_check(command, selected):
    cached = []

    def check(context):
        if cached:
            return cached[0]
        if command["id"] not in selected:
            return CheckOutcome(
                State.SKIPPED,
                Execution.NOT_RUN,
                "Configured command needs explicit execution opt-in",
            )
        argv = [sys.executable if a == "{python}" else a for a in command["argv"]]
        try:
            result = subprocess.run(
                argv,
                cwd=context.target,
                capture_output=True,
                check=False,
                timeout=command["timeout_seconds"],
                env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
            )
        except (OSError, subprocess.SubprocessError):
            outcome = CheckOutcome(
                State.UNKNOWN,
                Execution.ERROR,
                "Configured command was unavailable or did not complete; no test verdict is known",
            )
            cached.append(outcome)
            return outcome
        proof = Evidence(
            "command:" + command["id"],
            (".",),
            "trusted-command-exit",
            "tool-execution",
            content_digest(
                canonical_json(
                    {
                        "argv": command["argv"],
                        "exit_code": result.returncode,
                        "stdout": content_digest(result.stdout),
                        "stderr": content_digest(result.stderr),
                    }
                ).encode()
            ),
            (
                "Explicitly opted-in trusted command; not sandboxed. Only its measured behavior is evidenced.",
            ),
        )
        outcome = _outcome(
            State.UNKNOWN
            if result.returncode < 0
            else State.PASS
            if result.returncode == 0
            else State.FAIL,
            f"Configured command exited {result.returncode}",
            (proof,),
        )
        cached.append(outcome)
        return outcome

    return check


def _artifact_check(identifier, references, request, proof, test_check):
    def check(context):
        if identifier == "change-record":
            return _outcome(
                State.PASS,
                "Normalized local intent retains summary, acceptance, scope and sources",
                proof,
            )
        if identifier == "test-evidence":
            return (
                test_check(context)
                if test_check
                else CheckOutcome(
                    State.UNKNOWN,
                    Execution.NOT_RUN,
                    "No independent project-test provider is configured",
                )
            )
        if not references:
            return _outcome(
                State.UNKNOWN,
                f"No accepted references configured for {identifier}",
                proof,
                code="unconfigured-artifact",
            )
        evidence, missing = [], []
        for reference in references:
            try:
                path = contained_file(context.target, reference)
                with path.open("rb") as stream:
                    content = stream.read(65537)
                if not content.strip() or len(content) > 65536:
                    raise ValueError("Unavailable artifact")
                evidence.append(
                    Evidence(
                        reference,
                        (reference,),
                        "nonempty-artifact",
                        "local-check",
                        content_digest(content),
                        ("Presence and bytes only; semantic acceptance/approval is not inferred.",),
                    )
                )
            except (OSError, ValueError):
                missing.append(reference)
        return _outcome(
            State.FAIL if missing else State.PASS,
            f"{identifier}: "
            + (
                "missing/unreadable/unsafe references: " + ", ".join(missing)
                if missing
                else "configured local references present"
            ),
            tuple(evidence) or proof,
            code="missing-artifact" if missing else None,
        )

    return check


def inspect_change(
    target: Path,
    request: NormalizedRequest,
    *,
    base: str,
    policy_target: Path,
    previous: RequestPlan | None = None,
    observed_at: str | None = None,
    execute_checks=(),
    pack_arguments=None,
) -> ChangeReport:
    """Inspect without writes by default. Execution is explicit, trusted, unsandboxed.

    Use a separately controlled policy checkout, never policy edited by the change.
    Both local and CI callers supply that checkout, accepted intent and base.
    """
    target, policy_target = target.absolute(), policy_target.absolute()
    if target.resolve().is_relative_to(
        policy_target.resolve()
    ) or policy_target.resolve().is_relative_to(target.resolve()):
        raise ValueError(
            "Policy target must be a separate trusted checkout outside the change target"
        )
    if observed_at is not None:
        try:
            if not re.fullmatch(
                r"\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[Zz]|[+-](?:[01]\d|2[0-3]):[0-5]\d)",
                observed_at,
            ):
                raise ValueError("Invalid timestamp syntax")
            observed_at = datetime.fromisoformat(
                observed_at.upper().replace("Z", "+00:00")
            ).isoformat()
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "Observation time must be an RFC 3339 timestamp with a timezone"
            ) from exc
    profile = load_profile(contained_file(policy_target, ".govkit/profile.yaml"))
    policy_error, policy_digest = False, None
    try:
        policy, policy_digest = load_change_policy(policy_target, profile)
    except (OSError, ValueError):
        policy_error = True
        policy = {"impact_rules": [], "commands": [], "artifacts": [], "constraints": []}
    change = capture_change(target, base)
    impacts, unclassified = {}, []
    for path in change.paths:
        matched = [r for r in policy["impact_rules"] if any(_covers(p, path) for p in r["paths"])]
        if not matched:
            unclassified.append(path)
        for rule in matched:
            impacts.update(rule["impacts"])
    if unclassified or not change.complete:
        impacts = {**dict.fromkeys((*SENSITIVE, "llm", "mcp")), **impacts}
    observed = {"schema_version": 1, "paths": list(change.paths[:256]), "impacts": impacts}
    plan = plan_request(policy_target, request, observed_scope=observed, previous=previous)
    config_ref = profile.document["policy"].get("conformance", {}).get("reference")
    config_evidence = next((e for e in plan.document["evidence"] if e["source"] == config_ref), {})
    policy_error = (
        policy_error
        or profile.digest != plan.document["identity"]["profile_digest"]
        or config_evidence.get("digest") != policy_digest
    )
    proof = (
        Evidence(
            "git:" + (change.base or base),
            change.paths or (".",),
            "base-to-git-visible-worktree",
            "local-check" if change.complete else "unverified",
            change.digest,
            (
                "Includes staged, unstaged and untracked nonignored files. Renames are add/delete. Bounded snapshot; concurrent edits require a rerun.",
            ),
        ),
    )
    identity = Identity(
        profile.repository.id,
        revision=change.revision,
        dirty_digest=change.document["tree_digest"],
        profile_digest=profile.digest,
        resolution_digest=plan.identity,
        pack_lock_digest=plan.document["identity"]["lock_digest"],
        change_digest=change.digest,
        observed_at=observed_at,
    )
    context = CheckContext(target, identity, tuple(execute_checks), pack_arguments or {})
    trusted_context = replace(context, target=policy_target)
    registry, specs = CheckRegistry(), list(plan.check_specs())

    def add(identifier, check, reason, source="accepted:conformance", scope=(".",)):
        registry.register(identifier, check)
        specs.append(CheckSpec(identifier, True, reason, source, scope))

    add(
        "govkit:profile",
        lambda _: adapters.profile_check(trusted_context),
        "Validate trusted accepted policy",
        ".govkit/profile.yaml",
    )
    add(
        "govkit:pack-lock",
        lambda _: adapters.pack_lock_check(trusted_context),
        "Verify trusted pinned resources",
        ".govkit/pack-lock.json",
    )
    add(
        "change:policy",
        lambda _: _outcome(
            State.UNKNOWN if policy_error else State.PASS,
            "Accepted conformance configuration is unavailable"
            if policy_error
            else "Accepted conformance configuration validated",
            proof,
        ),
        "Require explicit executable/artifact/impact mapping",
    )
    add(
        "change:scope",
        lambda _: _outcome(
            State.UNKNOWN if not change.complete else State.FAIL if unclassified else State.PASS,
            "Unclassified changed paths: " + ", ".join(unclassified)
            if unclassified
            else "Complete Git scope captured"
            if change.complete
            else change.problems[0],
            proof,
            code="unclassified-scope" if unclassified else None,
        ),
        "Do not let path filters hide changes",
    )
    expansion = [
        p for p in change.paths if not any(_covers(s, p) for s in request.document["scope"])
    ]
    stale = False
    if previous:
        old, fresh = previous.document, plan.document
        stale = (
            any(
                old["identity"][k] != fresh["identity"][k]
                for k in ("request_digest", "profile_digest", "lock_digest")
            )
            or old["workflow"] != fresh["workflow"]
            or not {c["id"] for c in fresh["checks"]} <= {c["id"] for c in old["checks"]}
            or old["evidence"] != fresh["evidence"]
        )
    add(
        "change:plan",
        lambda _: _outcome(
            State.FAIL if expansion or stale else State.UNKNOWN if not plan.ready else State.PASS,
            "Resolve changed intent/scope/policy or stale obligations"
            if expansion or stale
            else "Resolved request still has blocking decisions"
            if not plan.ready
            else "Requirements re-resolved against trusted policy and actual scope",
            proof,
            code="stale-or-expanded-plan" if expansion or stale else None,
        ),
        "Editable workflow labels cannot waive requirements",
    )
    commands = {c["id"]: c for c in policy["commands"]}
    try:
        packs = dict(locked_check_requirements(policy_target))
    except (OSError, ValueError):
        packs = {}
    if commands.keys() & packs.keys():
        raise ValueError("Duplicate command/pack providers")
    required = {s.id for s in specs}
    selected = set(execute_checks)
    executable = (
        commands.keys()
        | packs.keys()
        | ({"defect:eligibility"} if "defect:eligibility" in required else set())
    )
    if selected - executable or selected - required:
        raise ValueError("Execution is not a selected configured check")
    if any(
        k not in packs
        or k not in required
        or k not in selected
        or not isinstance(v, (tuple, list))
        or not all(isinstance(a, str) for a in v)
        for k, v in (pack_arguments or {}).items()
    ):
        raise ValueError("Pack arguments must map selected pack IDs to string arrays")

    def executable_check(check):
        if policy_error:
            return lambda _: CheckOutcome(
                State.UNKNOWN,
                Execution.NOT_RUN,
                "Accepted policy capture is invalid or changed; command execution withheld",
            )
        return check

    for identifier, command in commands.items():
        if identifier in required:
            registry.register(identifier, executable_check(_command_check(command, selected)))
    for identifier in packs:
        if identifier in required:
            registry.register(
                identifier,
                executable_check(adapters.pack_check(identifier, policy_target=policy_target)),
            )

    def architecture(_):
        return assess_architecture(profile, policy, change, observed_at, proof)

    add(
        "change:architecture",
        architecture,
        "Measure current and scoped target constraints across repository scope",
    )
    if (
        "review:architecture" in required
        and "review:architecture" not in commands
        and "review:architecture" not in packs
    ):
        registry.register("review:architecture", architecture)
    if plan.document["workflow"] == "architecture":
        add(
            "approval:architecture",
            lambda _: CheckOutcome(
                State.UNKNOWN,
                Execution.NOT_RUN,
                "Platform approval evidence is unavailable locally; an agent assertion cannot grant it",
            ),
            "Architecture approval is independent of source content",
        )
    artifacts = {a["id"]: a["references"] for a in policy["artifacts"]}
    if "defect:eligibility" in required:
        registry.register(
            "defect:eligibility",
            executable_check(
                defect_check(
                    request,
                    change,
                    artifacts.get("fix-record", []),
                    commands.get("project:tests"),
                    selected,
                    _command_check,
                )
            ),
        )
    for artifact in plan.document["artifacts"]:
        identifier = artifact["id"]
        add(
            "artifact:" + identifier,
            _artifact_check(
                identifier,
                artifacts.get(identifier, []),
                request,
                proof,
                registry.get("project:tests"),
            ),
            artifact["reason"],
            scope=tuple(plan.document["scope"]),
        )
    checks = run_checks(context, tuple(specs), registry)

    def stable_inputs(_):
        try:
            fresh_change = capture_change(target, base)
            fresh_plan = plan_request(
                policy_target, request, observed_scope=observed, previous=previous
            )
            stable = (
                fresh_change.complete
                and fresh_change.digest == change.digest
                and fresh_plan.identity == plan.identity
            )
        except (OSError, ValueError):
            stable = False
        return _outcome(
            State.PASS if stable else State.FAIL,
            "Captured Git/policy/resource/reference inputs remained stable"
            if stable
            else "Inputs changed during inspection; discard this result and rerun",
            proof,
            code=None if stable else "inputs-changed",
        )

    registry.register("change:stable-inputs", stable_inputs)
    stability = run_checks(
        context,
        (
            CheckSpec(
                "change:stable-inputs",
                True,
                "Results must match the inspected inputs",
                "accepted:conformance",
                (".",),
            ),
        ),
        registry,
    )
    checks = replace(
        checks, results=tuple(sorted(checks.results + stability.results, key=lambda r: r.spec.id))
    )
    report = ChangeReport(change.document, plan, checks)
    validate_document(report.document, "change-results")
    return report
