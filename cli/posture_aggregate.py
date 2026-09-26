# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Offline counts of selected posture snapshots, never a new assessment engine."""

import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime

from .posture import DIMENSIONS, PostureReport, parse_posture
from .posture_change import parse_change_posture
from .release_metadata import timestamp
from .schema_validation import DocumentError, canonical_json, content_digest, validate_document

PARSERS = {"posture-export": parse_posture, "change-posture": parse_change_posture}
STATES = ("pass", "fail", "warn", "unknown", "skipped", "waived", "not-applicable")
EXECUTIONS = ("executed", "not-run", "error")
FRESHNESS = ("fresh", "stale", "unknown", "future")
CATEGORIES = (
    "compatible_updates",
    "required_upgrades",
    "resource_drift",
    "governance_reviews",
    "ci_repairs",
    "compliant_pins",
    "fresh_metadata",
    "stale_metadata",
    "unknown_metadata",
)


@dataclass(frozen=True)
class ReportingWindow:
    """An explicit reporting clock/window; never relax canonical source freshness."""

    as_of: datetime
    max_age_hours: int

    def age(self, stamp):
        if stamp is None:
            return None, "unknown"
        hours = (self.as_of - timestamp(stamp)).total_seconds() / 3600
        if hours < 0:
            return None, "future"
        return hours, "fresh" if hours <= self.max_age_hours else "stale"

    def fresh(self, document):
        return self.age(document["as_of"])[1] == "fresh"


def _select(documents, cohort):
    selected = {}
    for document in documents:
        if (
            not isinstance(document, dict)
            or not isinstance(document.get("kind"), str)
            or document["kind"] not in PARSERS
        ):
            raise DocumentError("Expected a maintenance or change posture export")
        doc = PARSERS[document["kind"]](document).document
        key = doc["kind"], doc["repository_ref"]
        if doc["repository_ref"] not in cohort:
            raise DocumentError("Snapshot repository is outside the explicit cohort")
        if key in selected and selected[key] != doc:
            raise DocumentError("Conflicting snapshots; select one per repository and kind")
        selected[key] = doc
    return [selected[k] for k in sorted(selected)]


def _categories(doc, window):
    candidates = doc["versions"]["candidates"]
    metadata = doc["versions"]["metadata"]
    recommendations = doc["maintenance"]["recommendations"]
    actions = {r["action"] for r in recommendations}
    metadata_unknown = not candidates or not metadata
    metadata_stale = False
    for record in [*candidates, *metadata]:
        freshness = window.age(record["as_of"])[1]
        lookup_age = window.age(record["retrieved_at"])[1]
        if (
            record["lookup_status"] in ("failed", "unavailable")
            or freshness
            in (
                "unknown",
                "future",
            )
            or lookup_age in ("unknown", "future")
        ):
            metadata_unknown = True
        if (
            record["as_of"]
            and record["retrieved_at"]
            and timestamp(record["as_of"]) > timestamp(record["retrieved_at"])
        ):
            metadata_unknown = True
        if record.get("freshness") == "unknown":
            metadata_unknown = True
        if freshness == "stale" or record.get("freshness") == "stale":
            metadata_stale = True
    return {
        "compatible_updates": any(c["selected_target"] is not None for c in candidates),
        "required_upgrades": any(
            r["required"] and r["action"] in ("upgrade-cli", "upgrade-pack")
            for r in recommendations
        ),
        "resource_drift": any(r["state"] in ("missing", "modified") for r in doc["resources"]),
        "governance_reviews": bool(actions & {"review-policy", "review-capability"}),
        "ci_repairs": "repair-ci" in actions,
        "compliant_pins": any(
            c["pin"] is not None and c["current_policy_state"] == "compliant" for c in candidates
        ),
        "fresh_metadata": not metadata_unknown and not metadata_stale,
        "stale_metadata": metadata_stale,
        "unknown_metadata": metadata_unknown,
    }


def _capabilities(documents):
    rows = {}
    for doc in documents:
        capabilities = doc["capabilities"]
        required_key = "required" if doc["kind"] == "posture-export" else "change_required"
        for output_key, input_key in (
            ("configured", "configured"),
            ("required", required_key),
            ("recorded", "recorded"),
        ):
            seen = set()
            for c in capabilities[input_key]:
                row = rows.setdefault(
                    c["ref"],
                    {
                        "ref": c["ref"],
                        "label": c["label"],
                        "configured": 0,
                        "required": 0,
                        "recorded": 0,
                    },
                )
                if row["label"] != c["label"]:
                    raise DocumentError("Conflicting capability labels")
                if c["ref"] not in seen:
                    row[output_key] += 1
                    seen.add(c["ref"])
    return [rows[ref] for ref in sorted(rows)]


def _control_counts(observations):
    states, execution = Counter(), Counter()
    required = passed = required_passed = total = 0
    for control, fresh in observations:
        total += 1
        states[control["state"]] += 1
        execution[control["execution"]] += 1
        required += control["required"]
        if fresh and control["state"] == "pass" and control["execution"] == "executed":
            passed += 1
            required_passed += control["required"]
    return {
        "total": total,
        "applicable": total - states["not-applicable"],
        "required": required,
        "fresh_executed_passes": passed,
        "fresh_required_passes": required_passed,
        "states": {state: states[state] for state in STATES},
        "execution": {state: execution[state] for state in EXECUTIONS},
    }


def _coverage(documents, cohort_size, window):
    counts = Counter(window.age(doc["as_of"])[1] for doc in documents)
    return {
        "assessed_repositories": len(documents),
        "missing_repositories": cohort_size - len(documents),
        "freshness": {state: counts[state] for state in FRESHNESS},
        "capabilities": _capabilities(documents),
    }


def _fresh_dimension(document, identifier, window):
    return window.fresh(document) and (
        identifier != "maintenance:releases" or _categories(document, window)["fresh_metadata"]
    )


def _summarize(documents, cohort_size, window):
    maintenance = [d for d in documents if d["kind"] == "posture-export"]
    changes = [d for d in documents if d["kind"] == "change-posture"]
    categories, fresh_categories = Counter(), Counter()
    for doc in maintenance:
        flags = _categories(doc, window)
        categories.update(key for key, value in flags.items() if value)
        if window.fresh(doc):
            # Retain historical canonical update recommendations, but never call
            # their availability fresh if the release evidence is stale/unknown.
            if not flags["fresh_metadata"]:
                flags["compatible_updates"] = False
            fresh_categories.update(key for key, value in flags.items() if value)
    controls = [(c, window.fresh(doc)) for doc in changes for c in doc["results"]["controls"]]
    return {
        "repositories": cohort_size,
        "maintenance": {
            **_coverage(maintenance, cohort_size, window),
            "categories": {key: categories[key] for key in CATEGORIES},
            "fresh_categories": {key: fresh_categories[key] for key in CATEGORIES},
            "dimensions": [
                {
                    "id": identifier,
                    "counts": _control_counts(
                        (c, _fresh_dimension(doc, identifier, window))
                        for doc in maintenance
                        for c in doc["maintenance"]["dimensions"]
                        if c["id"] == identifier
                    ),
                }
                for identifier in sorted(DIMENSIONS)
            ],
        },
        "changes": {
            **_coverage(changes, cohort_size, window),
            "controls": _control_counts(controls),
            "evaluations": _control_counts(
                (c, fresh) for c, fresh in controls if c["label"] == "llm-exact-match"
            ),
        },
    }


def aggregate_posture(documents, *, repository_refs, as_of, max_age_hours=24):
    """Count an explicitly selected cohort; identical duplicate exports are idempotent."""
    cohort = list(repository_refs)
    if not cohort or any(
        not isinstance(r, str) or not re.fullmatch(r"ref:[a-f0-9]{64}", r) for r in cohort
    ):
        raise DocumentError("Invalid repository cohort")
    if len(set(cohort)) != len(cohort):
        raise DocumentError("Duplicate repository in cohort")
    if type(max_age_hours) is not int or max_age_hours < 1:
        raise DocumentError("Reporting age must be a positive integer")
    if not isinstance(as_of, str):
        raise DocumentError("An explicit reporting time is required")
    window = ReportingWindow(timestamp(as_of), max_age_hours)
    snapshots = _select(documents, cohort)
    observations = []
    for doc in snapshots:
        age, freshness = window.age(doc["as_of"])
        observations.append(
            {
                "kind": doc["kind"],
                "repository_ref": doc["repository_ref"],
                "snapshot_ref": "ref:" + doc["digest"],
                "as_of": doc["as_of"],
                "age_hours": age,
                "freshness": freshness,
            }
        )
    document = {
        "schema_version": 2 if any(s["schema_version"] == 2 for s in snapshots) else 1,
        "kind": "posture-aggregate",
        "as_of": window.as_of.isoformat(),
        "max_age_hours": max_age_hours,
        "cohort": sorted(cohort),
        "snapshots": snapshots,
        "observations": observations,
        "summary": _summarize(snapshots, len(cohort), window),
    }
    document["digest"] = content_digest(canonical_json(document).encode())
    validate_document(document, "posture-aggregate")
    return PostureReport(document)


def parse_aggregate(document):
    """Replay counts from validated embedded exports; consistency is not authenticity."""
    validate_document(document, "posture-aggregate")
    replay = aggregate_posture(
        document["snapshots"],
        repository_refs=document["cohort"],
        as_of=document["as_of"],
        max_age_hours=document["max_age_hours"],
    )
    if replay.document != document:
        raise DocumentError("Aggregate does not match its selected snapshots and cohort")
    return replay


def render_aggregate(report):
    """Every summary scalar is shown with its JSON path for exact human/JSON parity."""
    doc = parse_aggregate(report.document).document
    lines = [
        f"Posture aggregate as of {doc['as_of']} (window {doc['max_age_hours']} hours)",
        "Unauthenticated selected snapshots; not a compliance or productivity score.",
        "Categories overlap. Maintenance and change evidence remain separate.",
    ]

    def render(value, path):
        if isinstance(value, dict):
            for key, item in sorted(value.items()):
                render(item, path + "/" + key)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                render(item, path + "/" + str(index))
        else:
            lines.append(f"{path}: {value}")

    render(doc["summary"], "summary")
    for row in doc["observations"]:
        lines.append(
            f"Snapshot {row['snapshot_ref']}: {row['kind']}; {row['repository_ref']}; "
            f"{row['freshness']}; age hours={row['age_hours']}"
        )
    return "\n".join(lines)
