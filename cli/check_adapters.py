# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Non-printing adapters over existing checks, with explicit coverage limits."""

from __future__ import annotations

import stat
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError

from . import approval, doctor, extensions, validate
from .check_models import CheckContext, CheckOutcome, Evidence, Execution, Finding, State
from .features import list_user_features
from .pack_store import execute_check, verify_lock
from .profiles import load_profile, load_resolution, resolve_profile
from .schema_validation import DocumentError, canonical_json, content_digest, read_document


def read_marker_snapshot(target: Path) -> dict | None:
    """Read legacy/current state without the legacy reader's migration writes."""
    node = target / ".govkit"
    path = node / "marker.json" if node.is_dir() else node
    if not path.exists():
        return None
    data = read_document(path)
    if (
        not isinstance(data, dict)
        or data.get("level") not in ("3", "4", "5")
        or not isinstance(data.get("options", {}), dict)
    ):
        raise DocumentError("Marker is unreadable or lacks supported legacy context")
    return data


def evidence(
    target: Path, source: str, method: str, limitation: str, *, origin="local-check"
) -> Evidence:
    path = target / source
    digest = content_digest(path.read_bytes()) if path.is_file() else None
    return Evidence(source, (source,), method, origin, digest, (limitation,))


def absent(summary: str, *, state=State.NOT_APPLICABLE) -> CheckOutcome:
    return CheckOutcome(state, Execution.NOT_RUN, summary)


def profile_check(context: CheckContext) -> CheckOutcome:
    profile = load_profile(context.target / ".govkit/profile.yaml")
    resolution = resolve_profile(profile)
    proof = evidence(
        context.target,
        ".govkit/profile.yaml",
        "profile-validation",
        "Accepted authority is the author's assertion; referenced policy content is not authenticated or enforced here.",
    )
    findings = [
        Finding(
            d.code,
            "error",
            "policy",
            d.message,
            "Reconcile the accepted profile.",
            ".govkit/profile.yaml",
            (proof,),
        )
        for d in resolution.plan.selections.unresolved
    ]
    record = context.target / ".govkit/resolution.json"
    if record.exists():
        resolved = load_resolution(record)
        if resolved.profile_digest != profile.digest:
            findings.append(
                Finding(
                    "stale-resolution",
                    "error",
                    "policy",
                    "Resolution record belongs to a different profile",
                    "Regenerate the profile resolution.",
                    ".govkit/resolution.json",
                    (proof,),
                )
            )
    return CheckOutcome(
        State.FAIL if findings else State.PASS,
        Execution.EXECUTED,
        "Profile and available resolution metadata checked",
        tuple(findings),
        (proof,),
    )


def pack_lock_check(context: CheckContext) -> CheckOutcome:
    if not (context.target / ".govkit/pack-lock.json").exists():
        return absent("No pinned pack resources are installed", state=State.UNKNOWN)
    verification = verify_lock(context.target)
    proof = evidence(
        context.target,
        ".govkit/pack-lock.json",
        "pack-lock-replay",
        "Resource consistency is not source authenticity or proof that a control ran.",
    )
    findings = tuple(
        Finding(
            d.code,
            "error",
            "installed-resources",
            d.message,
            "Preview and reconcile the pack installation.",
            d.subjects[0],
            (proof,),
        )
        for d in verification.decisions
    )
    return CheckOutcome(
        State.PASS if verification.ready else State.FAIL,
        Execution.EXECUTED,
        "Pinned resources and native skills verified",
        findings,
        (proof,),
    )


def doctor_check(context: CheckContext) -> CheckOutcome:
    marker = read_marker_snapshot(context.target)
    if marker is None:
        return absent("Legacy doctor requires an installation marker")
    source = ".govkit/marker.json" if (context.target / ".govkit").is_dir() else ".govkit"
    proof = evidence(
        context.target,
        source,
        "legacy-doctor",
        "Legacy heuristics can return no finding for indeterminate inputs; silence does not establish complete coverage.",
    )
    findings = []
    for finding in doctor.inspect_doctor(context.target, marker):
        message, action = finding.message, finding.suggested_action
        if finding.category == "internal":
            message = f"Legacy check {finding.id} could not complete; exception details omitted"
            action = "Inspect local inputs/dependencies and rerun the check."
        findings.append(
            Finding(
                finding.id,
                finding.severity,
                finding.category,
                message,
                action,
                finding.file,
                (proof,),
            )
        )
    state = State.FAIL if any(f.severity == "error" for f in findings) else State.UNKNOWN
    return CheckOutcome(
        state,
        Execution.EXECUTED,
        "Legacy doctor findings collected; heuristic coverage remains unknown",
        tuple(findings),
        (proof,),
    )


def extension_check(context: CheckContext) -> CheckOutcome:
    root = context.target / "extensions"
    if not root.exists():
        return absent("No legacy extensions configured")
    # The legacy scanner intentionally tolerates unreadable directories. Check
    # readability first, so that its empty fallback cannot become a pass here.
    entries = list(root.iterdir())
    for entry in entries:
        if entry.is_dir() and not entry.name.startswith("."):
            list(entry.iterdir())
    installed = extensions.discover_extensions(context.target)
    if not installed:
        return absent("No legacy extensions configured")
    findings, proofs = [], []
    for extension in installed:
        source = (extension.root / "manifest.yaml").relative_to(context.target).as_posix()
        proof = evidence(
            context.target,
            source,
            "legacy-extension-validation",
            "Checks declared shape and referenced paths, not contract compliance or check execution.",
        )
        proofs.append(proof)
        try:
            issues = extensions.validate_extension(extension, context.target)
            findings.extend(
                Finding(
                    "extension-invalid",
                    "error",
                    "extension",
                    issue,
                    "Reconcile the extension manifest and resources.",
                    source,
                    (proof,),
                )
                for issue in issues
            )
        except Exception as exc:
            findings.append(
                Finding(
                    "extension-unreadable",
                    "warning",
                    "extension",
                    f"Extension check could not complete ({type(exc).__name__})",
                    "Inspect the manifest and rerun.",
                    source,
                    (proof,),
                )
            )
    state = (
        State.FAIL
        if any(f.severity == "error" for f in findings)
        else State.UNKNOWN
        if findings
        else State.PASS
    )
    return CheckOutcome(
        state,
        Execution.EXECUTED,
        f"Checked {len(installed)} legacy extension manifest(s)",
        tuple(findings),
        tuple(proofs),
    )


def _remote_reference(value) -> bool:
    if isinstance(value, dict):
        return any(
            (
                key in ("$ref", "$dynamicRef")
                and (not isinstance(item, str) or not item.startswith("#"))
            )
            or _remote_reference(item)
            for key, item in value.items()
        )
    return isinstance(value, list) and any(_remote_reference(item) for item in value)


def offline_instance(target: Path, schema: Path, instance: Path):
    """Replace the legacy optional process boundary with offline runtime validation."""
    if not instance.resolve().is_relative_to(target.resolve()):
        return validate.CheckStatus.WARN, "Instance resolves outside the assessed repository"
    if not schema.resolve().is_relative_to(target.resolve()) or not schema.is_file():
        return (
            validate.CheckStatus.WARN,
            "Required local schema is unavailable; validation is unknown",
        )
    try:
        contract = read_document(schema)
        if _remote_reference(contract):
            return (
                validate.CheckStatus.WARN,
                "Non-local schema references are not retrieved; validation is unknown",
            )
        Draft202012Validator.check_schema(contract)
    except (DocumentError, SchemaError):
        return validate.CheckStatus.WARN, "Local schema is invalid; instance validation is unknown"
    try:
        data = read_document(instance)
    except DocumentError:
        return validate.CheckStatus.FAIL, f"{instance.name} is not a readable structured document"
    errors = list(Draft202012Validator(contract, format_checker=FormatChecker()).iter_errors(data))
    if errors:
        return (
            validate.CheckStatus.FAIL,
            f"{instance.name} fails local schema validation ({len(errors)} error(s))",
        )
    return validate.CheckStatus.PASS, f"{instance.name} conforms to its local schema"


def approval_check(context: CheckContext) -> CheckOutcome:
    path = context.target / approval.POLICY_REL
    try:
        policy_mode = path.stat().st_mode
    except FileNotFoundError:
        policy_mode = 0
    if policy_mode and not stat.S_ISREG(policy_mode):
        return absent("Configured approval policy is not a readable file", state=State.UNKNOWN)
    adrs = approval.discover_adrs_strict(context.target)
    if not policy_mode and not adrs:
        return absent("No ADR approval policy or ADRs configured")

    proofs = {}
    limitation = "Local shape and attestation references cannot authenticate provider reviews or establish active CI enforcement."

    def read_text(source_path):
        # Capture precisely the bytes the legacy checker consumes, including
        # in-scope ADRs. Do not re-read a failing source just to hash it.
        source = source_path.relative_to(context.target).as_posix()
        method = "local-approval-policy" if source_path == path else "local-adr-attestation"
        problem = "could not be read as UTF-8"
        try:
            if not source_path.resolve().is_relative_to(context.target.resolve()):
                problem = "resolves outside the assessed repository"
                raise OSError(problem)
            content = source_path.read_bytes()
            text = content.decode("utf-8")
        except (OSError, UnicodeError, RuntimeError):
            proofs[source] = Evidence(
                source, (source,), method, "unverified-artifact", None, (limitation, problem)
            )
            # Preserve the source-specific legacy diagnosis without exporting
            # an arbitrary exception payload or the resolved external path.
            raise OSError(problem) from None
        proofs[source] = Evidence(
            source, (source,), method, "local-check", content_digest(content), (limitation,)
        )
        return text

    def schema_check(target):
        status, message = offline_instance(
            target, target / approval.SCHEMA_REL, target / approval.POLICY_REL
        )
        return (
            ([message], [])
            if status is validate.CheckStatus.FAIL
            else ([], [message])
            if status is validate.CheckStatus.WARN
            else ([], [])
        )

    issues, warnings = approval.check_approval_policy(
        context.target, validate_schema=schema_check, adrs=adrs, read_text=read_text
    )

    findings = []
    for messages, severity in ((issues, "error"), (warnings, "warning")):
        for message in messages:
            source = max(
                (source for source in proofs if message.startswith(source + " ")),
                key=len,
                default=approval.POLICY_REL.as_posix(),
            )
            findings.append(
                Finding(
                    "approval-invalid" if severity == "error" else "approval-unverified",
                    severity,
                    "policy",
                    message,
                    "Reconcile policy and independently verify approval in the provider.",
                    source,
                    (proofs[source],) if source in proofs else (),
                )
            )
    # A local policy check can pass its narrow structural contract; its evidence
    # explicitly does not claim that an approval happened or a gate is active.
    return CheckOutcome(
        State.FAIL if issues else State.UNKNOWN if warnings else State.PASS,
        Execution.EXECUTED,
        "Local ADR policy/attestation structure checked",
        tuple(findings),
        tuple(proofs.values()),
    )


def feature_check(context: CheckContext) -> CheckOutcome:
    marker = read_marker_snapshot(context.target)
    if marker is None:
        return absent("Legacy feature checks require explicit legacy configuration")
    if marker["level"] == "3":
        return absent("Legacy level 3 has no feature artifact contract")
    features = list_user_features(context.target / "features")
    if not features:
        return absent("No user feature artifacts were evaluated", state=State.UNKNOWN)
    _, checks = validate._build_checks(
        marker["level"],
        marker.get("options", {}).get("type"),
        marker_reader=lambda path: marker if path == context.target else None,
        validate_instance=lambda schema, instance: offline_instance(
            context.target, schema, instance
        ),
    )
    findings, proofs, states = [], [], []
    for feature in features:
        location = feature.relative_to(context.target).as_posix()
        proof = Evidence(
            location,
            (location,),
            "legacy-feature-checks",
            "local-check",
            None,
            (
                "Artifact consistency does not execute tests or verify agent predictions; missing schema/tool coverage stays unknown.",
            ),
        )
        proofs.append(proof)
        for index, check in enumerate(checks):
            code = f"feature-{index:02d}"
            try:
                status, message = check(feature)
                finding_proof = proof
                state = {
                    validate.CheckStatus.PASS: State.PASS,
                    validate.CheckStatus.FAIL: State.FAIL,
                    validate.CheckStatus.WARN: State.UNKNOWN,
                }[status]
                if check is validate.check_plan_eval_prediction:
                    finding_proof = evidence(
                        context.target,
                        f"{location}/plan.md",
                        "prediction-structure",
                        "Self-predictions are producer assertions, not independent test or evaluation results.",
                        origin="agent-assertion",
                    )
                    if state is State.PASS:
                        state = State.UNKNOWN
                        message = "Agent prediction structure is valid; independent execution evidence is unavailable"
                states.append(state)
                severity = (
                    "error" if state is State.FAIL else "info" if state is State.PASS else "warning"
                )
                findings.append(
                    Finding(
                        code,
                        severity,
                        "feature",
                        message,
                        "Reconcile the feature artifacts and supply independent evidence.",
                        location,
                        (finding_proof,),
                    )
                )
            except Exception as exc:
                states.append(State.UNKNOWN)
                findings.append(
                    Finding(
                        code,
                        "warning",
                        "feature",
                        f"Check could not complete ({type(exc).__name__})",
                        "Inspect the input and rerun; other checks were retained.",
                        location,
                        (proof,),
                    )
                )
    state = (
        State.FAIL
        if State.FAIL in states
        else State.UNKNOWN
        if State.UNKNOWN in states
        else State.PASS
    )
    return CheckOutcome(
        state,
        Execution.EXECUTED,
        f"Checked artifacts in {len(features)} feature(s)",
        tuple(findings),
        tuple(proofs),
    )


def pack_check(identifier: str):
    def run(context: CheckContext) -> CheckOutcome:
        if identifier not in context.execute_pack_checks:
            return absent(
                f"Control {identifier} is configured but was not executed; request execution explicitly",
                state=State.SKIPPED,
            )
        arguments = context.pack_arguments.get(identifier, ())
        result = execute_check(context.target, identifier, arguments)
        digest = content_digest(
            canonical_json(
                {
                    "exit_code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "arguments": arguments,
                }
            ).encode()
        )
        proof = Evidence(
            f"pack-check:{identifier}",
            (".",),
            "pinned-python-exit",
            "tool-execution",
            digest,
            (
                "Executes explicitly trusted code, not a sandbox; an exit status does not authenticate the supplied evidence's origin, freshness or completeness.",
            ),
        )
        return CheckOutcome(
            State.PASS if result.returncode == 0 else State.FAIL,
            Execution.EXECUTED,
            f"Pinned control exited {result.returncode}",
            evidence=(proof,),
        )

    return run
