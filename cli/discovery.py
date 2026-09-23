# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Focused discovery and maintenance observations, separate from policy acceptance.

Reports and explicit baselines are local assertions, not authenticated approvals.
Only the existing accepted-profile format feeds protected installer previews.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from pathlib import Path

from .check_models import CheckOutcome, Evidence, Execution, Finding, State
from .discovery_scan import DiscoveryLimits, scan_repository
from .pack_loading import bundled_catalog
from .pack_store import preview_install
from .profile_store import preview_materialization
from .profiles import load_profile, parse_profile
from .schema_validation import DocumentError, canonical_json, read_document, validate_document
from .version import GOVKIT_VERSION


@dataclass(frozen=True)
class DiscoveryReport:
    _document: dict

    @property
    def document(self):
        return deepcopy(self._document)

    def to_json(self):
        return canonical_json(self._document)

    def maintenance_outcome(self) -> CheckOutcome:
        """I04-compatible facts for later maintenance composition, never certification."""
        doc = self._document
        observed = {o["source"]: o for o in doc["observations"]}
        findings = []
        for change in doc["changes"]:
            current = observed.get(change["source"])
            evidence = Evidence(
                change["source"],
                (change["scope"],),
                "bounded-discovery",
                "local-check" if current and current["digest"] else "unverified",
                current["digest"] if current else None,
                ("Observation is not a policy violation or approval; checks were not executed.",),
            )
            findings.append(
                Finding(
                    f"observation-{change['kind']}",
                    "warning",
                    "maintenance",
                    f"{change['category']} evidence {change['kind']}: {change['source']}",
                    "Review affected decisions and capability fit; preserve accepted policy until explicitly revised.",
                    change["source"],
                    (evidence,),
                )
            )
        for decision in doc["review"]:
            evidence = tuple(
                Evidence(
                    source,
                    (decision["scope"],),
                    "bounded-discovery",
                    "local-check",
                    observed[source]["digest"],
                    ("Observation does not authenticate approval.",),
                )
                for source in decision["sources"]
                if source in observed and observed[source]["digest"]
            )
            findings.append(
                Finding(
                    decision["id"],
                    "warning",
                    "maintenance",
                    decision["reason"],
                    "Review only the named affected scope; accept changes explicitly.",
                    evidence=evidence,
                )
            )
        if not doc["coverage"]["complete"]:
            findings.append(
                Finding(
                    "incomplete-discovery",
                    "warning",
                    "maintenance",
                    "Bounded evidence is incomplete: " + ", ".join(doc["coverage"]["limitations"]),
                    "Inspect relevant unavailable evidence or rerun with explicit references/limits.",
                )
            )
        state = (
            State.UNKNOWN
            if not doc["coverage"]["complete"]
            else State.WARN
            if doc["review"]
            else State.NOT_APPLICABLE
        )
        return CheckOutcome(
            state,
            Execution.EXECUTED,
            "Repository fit observations only; no conformance controls executed.",
            tuple(findings),
        )


def _validate_baseline(document):
    validate_document(document, "discovery")
    if document["accepted_profile"] is not None:
        profile = parse_profile(document["accepted_profile"])
        if profile.digest != document["profile_digest"]:
            raise DocumentError("Baseline profile digest does not match accepted profile")
    elif document["profile_digest"] is not None:
        raise DocumentError("Baseline profile digest requires an accepted profile")
    if document["accepted_profile"] is None and (
        document["install_ready"] or document["operations"]
    ):
        raise DocumentError("Installation preview requires an explicit accepted profile")
    if document["coverage"]["complete"] and document["coverage"]["limitations"]:
        raise DocumentError("Complete discovery cannot contain coverage limitations")
    for observation in document["observations"]:
        if observation["status"] == "observed" and not observation["digest"]:
            raise DocumentError("Observed evidence requires a digest")
    sources = [o["source"] for o in document["observations"]]
    if len(sources) != len(set(sources)):
        raise DocumentError("Baseline contains duplicate observation sources")


def load_baseline(path: Path) -> dict:
    """Validate supplied last-reviewed evidence; no claim that its author is trusted."""
    document = read_document(path)
    _validate_baseline(document)
    return document


def _references(document):
    """All accepted authority references, including workflow/transition exceptions."""
    references = set()
    if isinstance(document, dict):
        if document.get("authority") == "accepted" and isinstance(document.get("reference"), str):
            references.add(document["reference"])
        for value in document.values():
            references.update(_references(value))
    elif isinstance(document, list):
        for value in document:
            references.update(_references(value))
    return references


def _decision(identifier, scope, reason, sources=(), *, status="pending", choices=(), affects=()):
    return {
        "id": identifier,
        "scope": scope,
        "status": status,
        "reason": reason,
        "sources": sorted(set(sources)),
        "choices": list(choices),
        "affects": list(affects),
    }


def _decisions(scan, profile, capabilities):
    decisions = []
    selected = {c["id"] for c in profile.document["capabilities"]} if profile else set()
    contracts = profile.document["policy"].get("contracts", []) if profile else []
    transitions = profile.document["policy"].get("transitions", []) if profile else []
    covered = set()
    by_source = {o.source: o for o in scan.observations}
    for contract in contracts:
        source = contract["source"]["reference"]
        for scope in contract["scope"]:
            covered.add(scope)
            available = source in by_source and by_source[source].status == "observed"
            decisions.append(
                _decision(
                    f"architecture:{scope}:{source}",
                    scope,
                    "Retain the accepted contract; evidence is observational."
                    if available
                    else "Accepted contract evidence is unavailable; review dependent architecture work.",
                    (source,),
                    status="accepted" if available else "review-required",
                    affects=(f"architecture:{scope}",),
                )
            )
    for transition in transitions:
        sources = _references(transition)
        covered.update(transition["scope"])
        for scope in transition["scope"]:
            available = all(s in by_source and by_source[s].status == "observed" for s in sources)
            decisions.append(
                _decision(
                    f"transition:{transition['id']}:{scope}",
                    scope,
                    f"Accepted {transition['mode']} for {transition['applies_to']}; current/target references and scoped exceptions remain in the profile. Execution/exit evidence must be checked separately.",
                    sources,
                    status="accepted" if available else "review-required",
                    affects=(f"architecture:{scope}",),
                )
            )
    for boundary in scan.boundaries:
        sources = [
            o.source
            for o in scan.observations
            if o.scope == boundary and o.category in {"architecture", "decision", "guidance"}
        ]
        # A root contract also covers contained components. Component contracts do not
        # imply a root-wide commitment; the root question stays optional.
        if any(
            c == "." or boundary == c or boundary.startswith(c.rstrip("/") + "/") for c in covered
        ):
            continue
        decisions.append(
            _decision(
                f"architecture:{boundary}",
                boundary,
                "Review existing sources and choose only when architecture work needs a commitment; no default stack is accepted.",
                sources,
                choices=("retain", "improve", "migrate"),
                affects=(f"architecture:{boundary}",),
            )
        )
    styles = {s for o in scan.observations for s in o.signals if s.startswith("architecture:")}
    if len(styles) > 1:
        decisions.append(
            _decision(
                "scoped-conventions",
                ".",
                "Different documented architecture indicators may be intentional by component or conflict within a scope; review only affected scopes. Accepted policy takes precedence over observation.",
                [o.source for o in scan.observations if any(s in styles for s in o.signals)],
                choices=("retain-scoped-conventions", "resolve-affected-conflict"),
                affects=("architecture",),
            )
        )
    recommended = set(capabilities)
    model_sources = [
        o.source for o in scan.observations if any(s.startswith("model:") for s in o.signals)
    ]
    if model_sources:
        recommended.add("llm-evaluation")
    for capability in sorted(recommended - selected):
        decisions.append(
            _decision(
                f"capability:{capability}",
                ".",
                "Review this capability before adding it to an accepted profile; observation is not selection.",
                model_sources if capability == "llm-evaluation" else (),
                choices=("adopt", "defer"),
                affects=(capability,),
            )
        )
    return decisions


def _changes(scan, baseline):
    if baseline is None:
        return []
    old = {o["source"]: o for o in baseline["observations"]}
    current = {o.source: o.document() for o in scan.observations}
    changes = []
    for source in sorted(old.keys() | current.keys()):
        before, after = old.get(source), current.get(source)
        if before == after:
            continue
        if after is None:
            same_coverage = (
                asdict(scan.limits) == baseline["coverage"]["limits"]
                and list(scan.references) == baseline["references"]
            )
            kind = "removed" if scan.complete and same_coverage else "unavailable"
        elif after["status"] != "observed":
            kind = "unavailable"
        else:
            kind = "added" if before is None else "changed"
        fact = after or before
        changes.append(
            {
                "source": source,
                "scope": fact["scope"],
                "category": fact["category"],
                "kind": kind,
                "before_digest": before["digest"] if before else None,
                "after_digest": after["digest"] if after else None,
            }
        )
    return changes


def _review(decisions, changes, baseline, scan, profile_digest):
    if baseline is None:
        review = [d for d in decisions if d["status"] != "accepted"]
    else:
        old = {d["id"]: d for d in baseline["decisions"]}
        changed_sources = {c["source"] for c in changes}
        review = []
        for decision in decisions:
            affected = changed_sources.intersection(decision["sources"])
            if decision != old.get(decision["id"]) or affected:
                review.append(
                    {
                        **decision,
                        "status": "review-required"
                        if decision["status"] == "accepted"
                        else decision["status"],
                    }
                )
        for change in changes:
            review.append(
                _decision(
                    f"fit:{change['source']}",
                    change["scope"],
                    f"Review changed {change['category']} evidence and affected assumptions; no automatic policy or capability change.",
                    (change["source"],),
                    status="review-required",
                    affects=(change["category"],),
                )
            )
        if profile_digest != baseline["profile_digest"]:
            review.append(
                _decision(
                    "accepted-profile-changed",
                    ".",
                    "Explicit accepted profile changed; review affected commitments.",
                    status="review-required",
                    affects=("policy",),
                )
            )
        if (
            asdict(scan.limits) != baseline["coverage"]["limits"]
            or list(scan.references) != baseline["references"]
        ):
            review.append(
                _decision(
                    "observation-coverage-changed",
                    ".",
                    "Discovery coverage changed; compare within the shared observation scope.",
                    status="review-required",
                    affects=("evidence",),
                )
            )
    if not scan.complete:
        review.append(
            _decision(
                "incomplete-evidence",
                ".",
                "Relevant evidence is unavailable or outside the bounded sample; only dependent decisions remain unresolved.",
                status="review-required",
                affects=("evidence",),
            )
        )
    return sorted(review, key=lambda d: d["id"])


def _install_preview(profile_path, target):
    try:
        metadata = preview_materialization(profile_path, target)
        packs = preview_install(
            profile_path, target, bundled_catalog(), govkit_version=GOVKIT_VERSION
        )
        operations = [op.summary() for op in (*metadata.operations, *packs.operations)]
        ready = (
            metadata.resolution.ready
            and packs.resolution.ready
            and all(op["action"] != "protected" for op in operations)
        )
        pending = [
            _decision(
                f"install:{d.code}:{','.join(d.subjects)}", ".", d.message, affects=d.subjects
            )
            for d in packs.resolution.decisions
        ]
        for d in metadata.resolution.plan.selections.unresolved:
            pending.append(_decision(f"profile:{d.id}", ".", d.message, affects=d.affected))
        for operation in operations:
            if operation["action"] == "protected":
                pending.append(
                    _decision(
                        f"protected:{operation['path']}",
                        ".",
                        "Preserve this existing customization; reconcile it explicitly before installation.",
                        (operation["path"],),
                        affects=("installation",),
                    )
                )
        return operations, ready, pending
    except (OSError, DocumentError):
        return (
            [],
            False,
            [
                _decision(
                    "install:preview-unavailable",
                    ".",
                    "Existing metadata/resources cannot be previewed safely; use profile/pack preview to diagnose and reconcile the installation. Discovery facts remain available.",
                    affects=("installation",),
                )
            ],
        )


def discover(
    target: Path,
    *,
    profile_path: Path | None = None,
    baseline: dict | None = None,
    references=(),
    capabilities=(),
    limits: DiscoveryLimits | None = None,
) -> DiscoveryReport:
    """Inspect and preview only. Never migrate markers, run checks or write files."""
    target = target.absolute()
    limits = limits or DiscoveryLimits()
    if profile_path is None:
        candidate = target / ".govkit/profile.yaml"
        if candidate.is_symlink() or (target / ".govkit").is_symlink():
            raise DocumentError("Refusing symlink profile metadata")
        # Explicit stat avoids treating permission failures as an ungoverned repo.
        try:
            candidate.stat()
            profile_path = candidate
        except (FileNotFoundError, NotADirectoryError):
            pass  # Includes the old single-file marker; do not migrate it.
    profile = load_profile(profile_path) if profile_path else None
    identifier = profile.repository.id if profile else target.name
    if baseline is not None:
        _validate_baseline(baseline)
        if baseline["repository"] != identifier:
            raise DocumentError("Baseline repository identity does not match current repository")
    accepted = profile.document if profile else None
    scan = scan_repository(
        target, references=tuple(sorted(set(references) | _references(accepted))), limits=limits
    )
    decisions = _decisions(scan, profile, capabilities)
    changes = _changes(scan, baseline)
    profile_digest = profile.digest if profile else None
    review = _review(decisions, changes, baseline, scan, profile_digest)
    operations, ready, pending = (
        _install_preview(profile_path, target) if profile else ([], False, [])
    )
    decisions.extend(pending)
    review.extend(d for d in pending if baseline is None or d not in baseline["decisions"])
    proposed = None
    if not profile:
        source = {"reference": "pending-team-decision", "authority": "proposed"}
        proposed = {
            "schema_version": 1,
            "source": source,
            "repository": {"id": identifier},
            "capabilities": [{"id": c} for c in sorted(set(capabilities))],
            "policy": {"source": source},
        }
    document = {
        "kind": "discovery",
        "schema_version": 1,
        "scanner_version": 1,
        "repository": identifier,
        "profile_digest": profile_digest,
        "accepted_profile": accepted,
        "proposed_profile": proposed,
        "observations": [o.document() for o in scan.observations],
        "boundaries": list(scan.boundaries),
        "references": list(scan.references),
        "coverage": {
            "complete": scan.complete,
            "limitations": list(scan.limitations),
            "limits": asdict(limits),
        },
        "decisions": sorted(decisions, key=lambda d: d["id"]),
        "changes": changes,
        "review": sorted(review, key=lambda d: d["id"]),
        "operations": operations,
        "install_ready": ready,
    }
    _validate_baseline(document)
    return DiscoveryReport(document)


def render_discovery(report: DiscoveryReport) -> str:
    doc = report.document
    lines = [
        f"Discovery: {doc['repository']} (read-only)",
        "Evidence is observational; proposals are pending; accepted profile policy takes precedence.",
        f"Boundaries: {', '.join(doc['boundaries'])}",
        f"Coverage: {'bounded sample complete' if doc['coverage']['complete'] else 'incomplete'}; checks were not executed.",
    ]
    for observation in doc["observations"]:
        signals = ", ".join(observation["signals"]) or "source available for focused review"
        lines.append(
            f"{observation['category']} [{observation['confidence']}/{observation['status']}] {observation['source']} ({observation['scope']}): {signals}"
        )
    lines.append(f"Focused review: {len(doc['review'])} items")
    for decision in doc["review"]:
        lines.append(f"{decision['id']} [{decision['status']}]: {decision['reason']}")
    lines.append(
        f"Install preview: {len(doc['operations'])} operations; ready={doc['install_ready']}"
    )
    for operation in doc["operations"]:
        lines.append(f"{operation['action']}: {operation['path']}")
    return "\n".join(lines)
