# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Repository check assembly; policy requirements cannot be filtered by a caller."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from . import check_adapters as adapters
from .check_models import CheckContext, CheckSpec, Identity, State
from .check_runner import CheckRegistry, CheckReport, run_checks
from .pack_loading import PackError
from .pack_store import locked_check_requirements
from .profiles import load_profile
from .schema_validation import DocumentError, content_digest


def _digest(path: Path) -> str | None:
    try:
        return content_digest(path.read_bytes()) if path.is_file() else None
    except OSError:
        return None  # The owning check reports the unreadable input separately.


def inspect_repository(
    target: Path,
    *,
    identity: Identity | None = None,
    execute_pack_checks: tuple[str, ...] = (),
    pack_arguments: dict[str, tuple[str, ...]] | None = None,
) -> CheckReport:
    """Default inspection is read-only and offline; pack code requires explicit opt-in.

    Identity/time values are explicit caller inputs. Missing revision/change
    identity stays null; this foundation does not infer or route an actual diff.
    """
    target = target.absolute()
    if not target.is_dir() or target.is_symlink():
        raise ValueError("Target must be an existing directory, not a symlink")
    profile_path = target / ".govkit/profile.yaml"
    profile_present = profile_path.exists()
    marker_present = (target / ".govkit/marker.json").exists() or (target / ".govkit").is_file()
    lock_present = (target / ".govkit/pack-lock.json").exists()
    profile = None
    if profile_present:
        try:
            profile = load_profile(profile_path)
        except DocumentError:
            pass  # Still run the profile check and unrelated controls.
    identity = identity or Identity(profile.repository.id if profile else target.name)
    identity = replace(
        identity,
        repository=profile.repository.id if profile else identity.repository,
        profile_digest=profile.digest if profile else None,
        resolution_digest=_digest(target / ".govkit/resolution.json"),
        pack_lock_digest=_digest(target / ".govkit/pack-lock.json"),
    )
    arguments = pack_arguments or {}
    if any(
        not isinstance(key, str)
        or not isinstance(values, (tuple, list))
        or not all(isinstance(v, str) for v in values)
        for key, values in arguments.items()
    ):
        raise ValueError("Pack arguments must map check IDs to arrays of strings")
    context = CheckContext(
        target,
        identity,
        tuple(sorted(set(execute_pack_checks))),
        {key: tuple(values) for key, values in arguments.items()},
    )
    registry, specifications = CheckRegistry(), []

    def add(identifier, check, required, reason, source, scope=(".",)):
        registry.register(identifier, check)
        specifications.append(CheckSpec(identifier, required, reason, source, scope))

    needs_packs = bool(profile and profile.repository.capabilities)
    add(
        "govkit:profile",
        adapters.profile_check
        if profile_present
        else lambda _: adapters.absent(
            "No declarative profile is configured",
            state=State.NOT_APPLICABLE if marker_present else State.UNKNOWN,
        ),
        profile_present or not marker_present,
        "Validate the accepted declarative configuration",
        ".govkit/profile.yaml",
    )
    add(
        "govkit:pack-lock",
        adapters.pack_lock_check
        if lock_present or needs_packs
        else lambda _: adapters.absent("No pack installation is selected"),
        lock_present or needs_packs,
        "Verify selected installed resources without executing controls",
        ".govkit/profile.yaml",
    )
    legacy = (
        ("legacy:doctor", adapters.doctor_check),
        ("legacy:features", adapters.feature_check),
        ("legacy:extensions", adapters.extension_check),
        ("legacy:approval-policy", adapters.approval_check),
    )
    for identifier, check in legacy:
        add(
            identifier,
            check,
            False,
            "Inspect existing legacy artifacts without adopting a workflow",
            ".govkit/marker.json",
        )
    controls = ()
    if lock_present:
        try:
            controls = locked_check_requirements(target)
        except (PackError, DocumentError, OSError):
            controls = ()  # Lock verification remains required and reports the failure.
        for identifier, required in controls:
            add(
                identifier,
                adapters.pack_check(identifier),
                required,
                "Control contributed by the selected pinned pack",
                ".govkit/pack-lock.json",
            )
    if profile:
        # Accepted requirements precede default/pack selections so the merge
        # retains their authority when several sources select the same check.
        specifications = [
            CheckSpec(
                check.id,
                True,
                "Required by accepted project policy",
                profile.repository.policy.source.reference,
                (".",),
            )
            for check in profile.repository.policy.required_checks
        ] + specifications
    unknown = set(context.execute_pack_checks) - {identifier for identifier, _ in controls}
    if unknown:
        raise ValueError("Not a selected pinned pack check: " + ", ".join(sorted(unknown)))
    for identifier in context.execute_pack_checks:
        specifications.append(
            CheckSpec(
                identifier, True, "Explicit control execution requested", "command-line", (".",)
            )
        )
    return run_checks(context, tuple(specifications), registry)


def render_report(report: CheckReport) -> str:
    lines = [f"Conformance checks: {report.state.value.upper()} — {report.identity.repository}"]
    for result in report.results:
        outcome = result.outcome
        required = "required" if result.spec.required else "advisory"
        lines.append(
            f"  {outcome.state.value.upper():14} {result.spec.id} ({required}; {outcome.execution.value})"
        )
        for finding in outcome.findings:
            if finding.severity != "info":
                location = f" [{finding.location}]" if finding.location else ""
                lines.append(f"    {finding.code}{location}: {finding.message}")
    counts = report.summary
    lines.append(
        f"Required checks satisfied: {counts['required_satisfied']}/{counts['required']}; {counts['executed']} checks executed."
    )
    lines.append(
        "Only the named checks and scopes were assessed. Use --json for provenance and limitations."
    )
    return "\n".join(lines)
