# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Offline SOAA applicability and local-case coverage check.

Validates one feature's `soaa_applicability` block and reports whether the
claimed GK-SOAA cases are covered by passed experiment criteria with
sufficient evidence. Exit 0: satisfied; 1: not satisfied; 2: invalid input.
It executes no application tests and makes no formal SOAA claim. Experiment
currency and consistency remain the core assessor's job (`govkit validate`).
"""

import argparse
import json
import re
from pathlib import Path

CHECK = "soaa-applicability"
STATUSES = ("applies", "not-applicable", "unknown")
OMISSION_FIELDS = ("reason", "evidence", "owner", "change_trigger")
# Decisions after which an experiment's evidence supports nothing.
CLOSING_DECISIONS = {"revise-design", "reject-approach", "narrow-supported-behavior"}
FENCED_YAML = re.compile(r"^```ya?ml[ \t]*\r?\n(.*?)^```[ \t]*$", re.MULTILINE | re.DOTALL)
BLOCK_KEY = re.compile(r"^soaa_applicability\s*:", re.MULTILINE)
DEFAULT_CATALOG = Path(__file__).resolve().parent.parent / "catalog/gk-soaa-cases.yaml"
LIMITATIONS = (
    "Checks recorded applicability and cited experiment results only; it executes no application tests.",
    "Coverage by a synthetic-fixture result says nothing about any application runtime.",
    "Experiment currency, digests and status consistency are assessed separately by govkit validate.",
    "GK-SOAA cases are GovKit local cases, not normative SOAA assertions; no conformance claim follows.",
)


class InvalidInput(ValueError):
    pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--experiments", type=Path)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--cases", nargs="+", metavar="CASE_ID")
    args = parser.parse_args()
    try:
        from cli.experiments import parse_experiment_set
        from cli.schema_validation import DocumentError, content_digest, parse_document
    except ImportError as exc:
        return invalid(f"Requires GovKit 0.23.0 or later (experiment records): {exc}")
    try:
        inputs, documents = {}, {}
        for name, path in (
            ("preflight", args.preflight),
            ("experiments", args.experiments),
            ("catalog", args.catalog),
        ):
            if path is None:
                inputs[name] = None
                continue
            content = path.read_bytes()
            inputs[name] = content_digest(content)
            documents[name] = content
        catalog = parse_catalog(parse_document(documents["catalog"]))
        rows = parse_block(documents["preflight"].decode("utf-8"), catalog, parse_document)
        records = {"experiments": []}
        if "experiments" in documents:
            records = parse_experiment_set(parse_document(documents["experiments"]))
            check_feature(args.preflight, args.experiments, records["feature"])
        report = assess(rows, catalog, records, args.cases)
    except (OSError, UnicodeError, DocumentError, InvalidInput) as exc:
        return invalid(str(exc))
    report = {"check": CHECK, "inputs": inputs, **report, "limitations": list(LIMITATIONS)}
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] == "pass" else 1


def invalid(message: str) -> int:
    print(json.dumps({"check": CHECK, "status": "invalid", "error": message}, sort_keys=True))
    return 2


def check_feature(preflight: Path, experiments: Path, feature: str) -> None:
    """Bind the experiment record to the preflight's feature directory."""
    directory = preflight.absolute().parent
    if experiments.absolute().parent != directory or directory.name != feature:
        raise InvalidInput(
            f"Experiment record for feature {feature!r} must sit beside the preflight "
            f"in features/{feature}/"
        )


def parse_catalog(document) -> dict:
    """Return {"conditions": [...], "cases": {case_id: applies_when}}."""
    if not isinstance(document, dict) or document.get("version") != 1:
        raise InvalidInput("Catalog must be a version 1 mapping")
    rows = document.get("conditions")
    if not isinstance(rows, list) or not rows:
        raise InvalidInput("Catalog conditions must be a nonempty list")
    conditions = [c.get("id") if isinstance(c, dict) else None for c in rows]
    if not all(isinstance(c, str) and c.strip() for c in conditions):
        raise InvalidInput("Catalog condition ids must be nonempty strings")
    if len(conditions) != len(set(conditions)):
        raise InvalidInput("Catalog condition ids must be unique")
    listed = [document.get(key, []) for key in ("cases", "conditional_cases")]
    if not all(isinstance(entries, list) for entries in listed) or not sum(listed, []):
        raise InvalidInput("Catalog must list at least one case")
    cases = {}
    for case in sum(listed, []):
        identifier = case.get("id") if isinstance(case, dict) else None
        applies_when = case.get("applies_when") if isinstance(case, dict) else None
        if not isinstance(identifier, str) or identifier in cases:
            raise InvalidInput(f"Catalog case id missing or duplicated: {identifier}")
        if (
            not isinstance(applies_when, list)
            or not applies_when
            or not all(isinstance(c, str) for c in applies_when)
            or not set(applies_when) <= set(conditions)
        ):
            raise InvalidInput(f"Catalog case {identifier} has unknown or no conditions")
        cases[identifier] = list(applies_when)
    return {"conditions": conditions, "cases": cases}


def parse_block(markdown: str, catalog: dict, parse_document) -> dict:
    """Return {condition_id: row} from the one fenced soaa_applicability block."""
    blocks = [b for b in FENCED_YAML.findall(markdown) if BLOCK_KEY.search(b)]
    if len(blocks) != 1:
        raise InvalidInput(f"Expected one soaa_applicability block, found {len(blocks)}")
    document = parse_document(blocks[0])
    block = document.get("soaa_applicability") if isinstance(document, dict) else None
    if not isinstance(block, dict) or block.get("version") != 1:
        raise InvalidInput("soaa_applicability must be a version 1 mapping")
    if not isinstance(block.get("conditions"), list):
        raise InvalidInput("soaa_applicability.conditions must be a list")
    rows = {}
    for row in block["conditions"]:
        if not isinstance(row, dict):
            raise InvalidInput("Each condition must be a mapping")
        identifier = row.get("id")
        if identifier not in catalog["conditions"]:
            raise InvalidInput(f"Unknown condition: {identifier}")
        if identifier in rows:
            raise InvalidInput(f"Duplicate condition: {identifier}")
        if row.get("status") not in STATUSES:
            raise InvalidInput(f"Condition {identifier} has an unknown status")
        for field in OMISSION_FIELDS:
            if not isinstance(row.get(field, ""), str):
                raise InvalidInput(f"Condition {identifier} field {field} must be a string")
        rows[identifier] = row
    return rows


def assess(rows: dict, catalog: dict, records: dict, cases) -> dict:
    findings = []

    def add(code, message):
        findings.append({"code": code, "message": message})

    by_status = {status: [] for status in STATUSES}
    for identifier in catalog["conditions"]:
        row = rows.get(identifier)
        if row is None:
            add("condition-undecided", f"{identifier} is missing from the block")
            continue
        by_status[row["status"]].append(identifier)
        if row["status"] == "unknown":
            add("condition-unknown", f"{identifier} is unknown; unknown stays unresolved")
        elif row["status"] == "not-applicable":
            missing = [f for f in OMISSION_FIELDS if not row.get(f, "").strip()]
            if missing:
                add("omission-incomplete", f"{identifier} omission lacks {', '.join(missing)}")

    applies = set(by_status["applies"])
    applicable = [c for c, when in catalog["cases"].items() if applies & set(when)]
    if cases is None:
        claimed = applicable
    else:
        unknown = [c for c in cases if c not in catalog["cases"]]
        if unknown or len(cases) != len(set(cases)):
            raise InvalidInput(f"Unknown or duplicate case ids: {sorted(set(cases))}")
        claimed = list(cases)

    support = coverage(records)
    covered, uncovered = [], []
    for case in claimed:
        if case not in applicable:
            add("case-not-applicable", f"{case} applies under none of the applying conditions")
        elif case in support:
            covered.append({"case": case, **support[case]})
        else:
            uncovered.append(case)
            add("case-uncovered", f"{case} has no passed criterion with sufficient evidence")
    return {
        "status": "fail" if findings else "pass",
        "conditions": {
            "applies": sorted(by_status["applies"]),
            "not_applicable": sorted(by_status["not-applicable"]),
            "unknown": sorted(by_status["unknown"]),
        },
        "claimed": claimed,
        "covered": covered,
        "uncovered": uncovered,
        "applicable_unclaimed": [c for c in applicable if c not in claimed],
        "findings": findings,
    }


def coverage(records: dict) -> dict:
    """Map each cited case to the first passed criterion with sufficient evidence."""
    support = {}
    for experiment in records["experiments"]:
        result = experiment.get("result")
        decision = experiment.get("decision", {}).get("outcome")
        if experiment["status"] != "passed" or result is None or decision in CLOSING_DECISIONS:
            continue
        evidence = result["evidence_class"]
        if evidence != experiment["required_evidence_class"] and evidence != "application":
            continue
        # A pass with no recorded evidence supports nothing.
        passed = {c["id"] for c in result["criteria"] if c["outcome"] == "pass" and c["evidence"]}
        for criterion in experiment["acceptance_criteria"]:
            if criterion["id"] not in passed:
                continue
            for case in criterion.get("refs", []):
                support.setdefault(
                    case,
                    {
                        "experiment": experiment["id"],
                        "criterion": criterion["id"],
                        "evidence_class": evidence,
                    },
                )
    return support


if __name__ == "__main__":
    raise SystemExit(main())
