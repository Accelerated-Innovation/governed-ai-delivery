# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""A verification run for the Product Definition Graph, built offline.

The graph records what one build's tests and evaluations found, each result
bound to the exact revision it ran. `govkit evidence --feature` already holds
the same identifiers, digests and outcomes. This module projects those reports
into the request the graph accepts, and says what it left out and why.

Nothing here sends anything. The document's `request` is the only part that a
later step may send, and it holds identifiers, digests, kinds, outcomes and
the run's facts. It holds no title, path, message or score.

The graph refuses a whole run when one result names a requirement its tagged
baseline does not hold, or holds at another revision. So each result is
compared with the baseline tag in this checkout first, and one that would be
refused is left out and listed. The graph still decides: what it indexed is
its own record, and this comparison is not that record.

The constants below are copied from `discovery-engine`
(`src/engine/domain/verification.py`). They are the contract the engine runs
today, version 1: outcomes only.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from . import evidence_record, evidence_report, scenario_identity, tree_identity
from .evidence import Outcome
from .features import list_user_features
from .schema_validation import validate_document

KIND = "govkit.verification-run"
SCHEMA = "verification-run"
CONTRACT_VERSION = 1
RESULT_BUDGET = 5000
ARTIFACT_REFERENCE_MAX = 2048
BUILD_REFERENCE_MAX = 2048
TAG_MAX = 255
RUN_REFERENCE = re.compile(r"[a-z][a-z0-9-]{0,31}:[A-Za-z0-9][A-Za-z0-9._/-]{0,127}")
COMMIT = re.compile(r"[0-9a-f]{40}")
REPOSITORY = re.compile(r"[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}")
OUTCOMES = ("passed", "failed", "skipped", "error")
KINDS = ("test", "evaluation")

NOT_IN_BASELINE = "not-in-baseline"
REVISION_CHANGED = "revision-changed"
NO_RESULT = "no-result"
RESULTS_NOT_CURRENT = "results-not-current"
TREE_NOT_CLEAN = "tree-not-clean"
FEATURE_UNREADABLE = "feature-unreadable"
BASELINE_UNREADABLE = "baseline-unreadable"
SKIPS_UNMARKED = "skips-unmarked"
# A public contract: add, never rename.
CODES = (
    NOT_IN_BASELINE,
    REVISION_CHANGED,
    NO_RESULT,
    RESULTS_NOT_CURRENT,
    TREE_NOT_CLEAN,
    FEATURE_UNREADABLE,
    BASELINE_UNREADABLE,
    SKIPS_UNMARKED,
)
EXIT_BUILT, EXIT_NOTHING, EXIT_REFUSED = 0, 1, 2

LIMITATIONS = (
    "The request is a projection of local result files. It is not proof that tests ran.",
    "The baseline was read from the tag in this checkout. The graph decides what it "
    "indexed and may still refuse the run.",
    "Scores are not included. The verification run contract version 1 holds outcomes only.",
)


class RunError(ValueError):
    """The run could not be built at all. The message holds no file content."""


@dataclass(frozen=True)
class Facts:
    """What the caller states about the run. GovKit cannot observe any of it."""

    run_reference: str
    repository: str
    baseline_tag: str
    build_reference: str
    artifact_reference: str


def check_facts(
    *,
    run_reference: str,
    repository: str,
    baseline_tag: str,
    build_reference: str,
    artifact_reference: str,
) -> Facts:
    """The caller's facts, held to the rules the graph applies. Raises `RunError`."""
    build_reference = (build_reference or "").strip()
    artifact_reference = (artifact_reference or "").strip()
    if not RUN_REFERENCE.fullmatch(run_reference or ""):
        raise RunError(
            "the run reference must be `<system>:<run-id>`, such as `github:1234567890-1`"
        )
    if not REPOSITORY.fullmatch(repository or ""):
        raise RunError("the repository must be `owner/name`")
    if not baseline_tag or len(baseline_tag) > TAG_MAX:
        raise RunError("the baseline must be a tag name")
    if not build_reference or len(build_reference) > BUILD_REFERENCE_MAX:
        raise RunError("the build reference must name the CI run, by identifier or address")
    if not artifact_reference.startswith("https://") or (
        len(artifact_reference) > ARTIFACT_REFERENCE_MAX
        or any(c.isspace() for c in artifact_reference)
    ):
        raise RunError(
            f"the artifact link must be an https:// address of at most "
            f"{ARTIFACT_REFERENCE_MAX} characters"
        )
    return Facts(run_reference, repository, baseline_tag, build_reference, artifact_reference)


def baseline_of(feature: str, definition: bytes | None, criteria: bytes | None) -> dict | None:
    """One feature's requirements as its baseline files state them.

    Each identifier maps to its kind and revision digest. None when a file is
    present and cannot be identified, where the graph would not have indexed
    the feature. A feature the baseline lacks has no requirements.
    """
    index: dict[str, tuple[str, str]] = {}
    if definition is not None:
        try:
            scenarios = scenario_identity.read_scenarios(feature, definition)
        except scenario_identity.IdentityError:
            return None
        index.update({s.id: ("test", s.revision_digest) for s in scenarios})
    if criteria is not None:
        listed = evidence_report.criteria_in(criteria, feature)
        if listed is None:
            return None
        index.update({c.id: ("evaluation", c.revision_digest) for c in listed})
    return index


def _feature_reason(report: Mapping, record: Mapping | None) -> str | None:
    """Why none of a feature's results can be sent, or None when each is judged alone."""
    state = report["provenance"]["state"]
    if state == evidence_record.NOT_CHECKED:
        # The report stopped before its results were checked against the record,
        # or no result file was read and there is nothing that could be sent.
        return FEATURE_UNREADABLE if report["outcome"] == Outcome.ERROR.value else None
    if state != evidence_record.CURRENT or record is None:
        return RESULTS_NOT_CURRENT
    if not record.get("clean"):
        return TREE_NOT_CLEAN
    return None


def project(
    reports: Sequence[Mapping],
    baselines: Mapping[str, dict | None],
    facts: Facts,
    record: Mapping | None,
) -> dict:
    """The verification-run document for these evidence reports. Raises `RunError`.

    Pure. `baselines` maps a feature's name to `baseline_of` for it; `record`
    is the evidence record the reports were checked against, or None.
    """
    results: list[dict] = []
    left_out: list[dict] = []
    features: list[dict] = []

    def leave(feature: str, reason: str, result: Mapping | None = None) -> None:
        left_out.append(
            {
                "feature": feature,
                "requirement_id": result["requirement_id"] if result else None,
                "kind": result["kind"] if result else None,
                "reason": reason,
            }
        )

    for report in sorted(reports, key=lambda r: r["feature"]["name"]):
        name = report["feature"]["name"]
        before = len(results), len(left_out)
        reason = _feature_reason(report, record)
        if reason is not None:
            leave(name, reason)
        else:
            for result in report["results"]:
                found = _judge(result, report, baselines.get(name, {}))
                if found is None:
                    results.append(
                        {
                            "requirement_id": result["requirement_id"],
                            "revision_digest": result["revision_digest"],
                            "kind": result["kind"],
                            "result": result["outcome"],
                        }
                    )
                else:
                    leave(name, found, result)
        features.append(
            {
                "name": name,
                "evidence": report["provenance"]["state"],
                "sent": len(results) - before[0],
                "left_out": len(left_out) - before[1],
            }
        )

    identifiers = [result["requirement_id"] for result in results]
    if len(set(identifiers)) != len(identifiers):
        raise RunError("two results name the same requirement; a run names each once")
    if len(results) > RESULT_BUDGET:
        raise RunError(
            f"the run would hold {len(results)} results; the graph accepts at most "
            f"{RESULT_BUDGET} in one run"
        )
    request = None
    if results:
        # Results are only sent from features whose record holds, so there is one.
        if record is None or not COMMIT.fullmatch(str(record.get("commit", ""))):
            raise RunError("the recorded commit is not a 40-character commit the graph accepts")
        request = {
            "run_reference": facts.run_reference,
            "repository": facts.repository,
            "baseline_tag": facts.baseline_tag,
            "build": {"commit": record["commit"], "ref": facts.build_reference},
            "executed_at": record["recorded_at"],
            "artifact_reference": facts.artifact_reference,
            "results": sorted(results, key=lambda result: result["requirement_id"]),
        }
    left_out.sort(key=lambda entry: (entry["feature"], entry["requirement_id"] or ""))
    reasons = {code: sum(1 for entry in left_out if entry["reason"] == code) for code in CODES}
    document = {
        "schema_version": 1,
        "kind": KIND,
        "contract_version": CONTRACT_VERSION,
        "request": request,
        "features": features,
        "left_out": left_out,
        "summary": {
            "features": len(features),
            "sent": len(results),
            "left_out": len(left_out),
            "reasons": reasons,
        },
        "limitations": list(LIMITATIONS),
    }
    validate_document(document, SCHEMA)
    return document


def _judge(result: Mapping, report: Mapping, baseline: dict | None) -> str | None:
    """Why one result is left out, or None when it is sent."""
    if result["outcome"] not in OUTCOMES:
        return NO_RESULT
    if report["provenance"]["state"] != evidence_record.CURRENT:
        return RESULTS_NOT_CURRENT
    if (
        result["kind"] == "test"
        and result["outcome"] == "passed"
        and any(source.get("unidentified_skipped") for source in report["sources"])
    ):
        # A result file counts skipped tests it does not mark, so a test that
        # looks passed may have been skipped. That is not sent as a pass.
        return SKIPS_UNMARKED
    if baseline is None:
        return BASELINE_UNREADABLE
    held = baseline.get(result["requirement_id"])
    if held is None or held[0] != result["kind"]:
        return NOT_IN_BASELINE
    if held[1] != result["revision_digest"]:
        return REVISION_CHANGED
    return None


def exit_code(document: Mapping) -> int:
    """0 when a request was built, 1 when there is nothing that can be sent."""
    return EXIT_BUILT if document["request"] is not None else EXIT_NOTHING


def build(
    target: Path,
    facts: Facts,
    *,
    observe=None,
    read: Callable[[str], bytes | None] | None = None,
) -> dict:
    """Read the target's features and its baseline tag, and project them. Raises `RunError`.

    `observe` identifies the working tree, and `read(path)` returns the bytes
    a path under the target has at the baseline, or None. Both default to Git.
    """
    target = Path(target).resolve()
    if read is None:
        try:
            commit = tree_identity.tag_commit(target, facts.baseline_tag)
        except tree_identity.Unavailable as exc:
            raise RunError(f"the baseline cannot be read: {exc}") from None

        def read(path: str) -> bytes | None:
            return tree_identity.file_at(target, commit, path, evidence_report.MAX_DEFINITION_BYTES)

    record, _ = evidence_record.load(target)
    names = [path.name for path in list_user_features(target / "features")]
    reports = [evidence_report.build_report(target, name, observe=observe) for name in names]
    for report in reports:
        held = report["provenance"]
        if held["state"] == evidence_record.CURRENT and (
            record is None
            or (held["commit"], held["recorded_at"]) != (record["commit"], record["recorded_at"])
        ):
            raise RunError("the evidence record changed while it was read; build the run again")
    baselines: dict[str, dict | None] = {}
    for report in reports:
        name = report["feature"]["name"]
        if not any(result["outcome"] in OUTCOMES for result in report["results"]):
            continue
        try:
            baselines[name] = baseline_of(
                name,
                read(f"features/{name}/{evidence_report.DEFINITION}"),
                read(f"features/{name}/{evidence_report.CRITERIA}"),
            )
        except tree_identity.Unavailable:
            baselines[name] = None
    return project(reports, baselines, facts, record)


def render(document: Mapping) -> str:
    """A short account for a person. Lists counts, never a title or a path."""
    summary = document["summary"]
    lines = [
        f"Verification run: {summary['sent']} result(s) to send from "
        f"{summary['features']} feature(s); {summary['left_out']} left out."
    ]
    lines += [f"  {count} left out: {code}" for code, count in summary["reasons"].items() if count]
    if document["request"] is None:
        lines.append("  Nothing can be sent.")
    return "\n".join(lines)
