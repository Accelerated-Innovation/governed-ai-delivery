# Copyright 2026 Accelerated Innovation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""`govkit evidence --feature`: each scenario and criterion with its result.

The report starts from the feature's own definition: the scenarios in
`features/<name>/acceptance.feature` and the criteria in its
`eval_criteria.yaml`. It looks for a result for each one, so a scenario nobody
ran or a criterion nobody measured is reported instead of going unnoticed.
Identity comes from `scenario_identity` and `criterion_identity`, which mirror
the Product Definition Graph.

The dictionary `build_report` returns is the canonical report. The text output
is a rendering of it, and so is every later export. It is read-only and
offline: it reads the feature file and the JUnit XML under the target and
writes nothing, and starts no test run or evaluation. A `PASS` shows that every
scenario has a passing test result and every criterion a passing score in the
files found, and that an evidence record ties those files to the current
commit and working tree. It does not show that the tests ran when the record
says, or that a test asserts what its scenario says. See docs/EVIDENCE_REPORT.md.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from . import criterion_identity, evaluation_results, evidence_record, scenario_identity
from .evidence import SCENARIO_PROPERTY, CaseResult, Outcome, read_test_reports
from .features import list_user_features
from .schema_validation import DocumentError, parse_document

SCHEMA = "evidence-report"
KIND = "govkit.evidence-report"
DEFINITION = "acceptance.feature"
CRITERIA = "eval_criteria.yaml"
MAX_DEFINITION_BYTES = 1024 * 1024
STATES = ("passed", "failed", "error", "skipped", "missing", "owed")
# The worst of a scenario's test cases decides its state.
_SEVERITY = {"passed": 0, "skipped": 1, "failed": 2, "error": 3}
_NAMED_IN_DETAIL = 5
_OWED_NOTE = (
    "An owed criterion costs money or needs a person. GovKit does not start it; "
    "the feature is not done until its result exists."
)
_DATA_FORM = (
    f"{CRITERIA} lists criteria in the data form (an id and a predicate in words), "
    "which is not compared yet"
)
_PROVENANCE = {
    evidence_record.STALE: "stale",
    evidence_record.UNRECORDED: "unrecorded",
    evidence_record.UNAVAILABLE: "of unknown origin",
}
_NFR_NOTE = (
    "A passing @nfr scenario shows that its test passed. "
    "It does not show that the test asserts the value written in the scenario."
)


class SelectionError(ValueError):
    """`--feature` named no feature directory."""


def build_report(target: Path, feature: str, *, observe=None) -> dict:
    """The canonical report for one feature. Raises `SelectionError`.

    `observe` identifies the working tree; it defaults to Git.
    """
    directory = _select(target, feature)
    definition = directory / DEFINITION
    report = {
        "schema_version": 1,
        "kind": KIND,
        "feature": {
            "name": feature,
            "definition": definition.relative_to(target).as_posix(),
            "content_digest": None,
            "criteria": {
                "definition": (directory / CRITERIA).relative_to(target).as_posix(),
                "content_digest": None,
                "form": "absent",
            },
        },
        "outcome": Outcome.INCONCLUSIVE.value,
        "detail": "",
        "summary": {"scenarios": 0, "criteria": 0, **{state: 0 for state in STATES}},
        "sources": [],
        "results": [],
        "provenance": evidence_record.provenance(target, []),
    }

    def finish(outcome: Outcome, detail: str) -> dict:
        report["outcome"], report["detail"] = outcome.value, detail
        return report

    if directory.is_symlink() or definition.is_symlink():
        return finish(Outcome.ERROR, f"{DEFINITION} is behind a symbolic link and was not read")
    try:
        criteria = _read_criteria(directory / CRITERIA, feature, report["feature"]["criteria"])
    except _Unusable as unusable:
        return finish(Outcome.ERROR, str(unusable))
    if not definition.is_file():
        return finish(Outcome.INCONCLUSIVE, f"the feature has no {DEFINITION}")
    try:
        if definition.stat().st_size > MAX_DEFINITION_BYTES:
            return finish(Outcome.ERROR, f"{DEFINITION} is larger than 1 MiB and was not read")
        data = definition.read_bytes()
    except OSError as exc:
        return finish(Outcome.ERROR, f"{DEFINITION} could not be read: {exc}")
    report["feature"]["content_digest"] = hashlib.sha256(data).hexdigest()
    try:
        scenarios = scenario_identity.read_scenarios(feature, data)
    except scenario_identity.IdentityError as refused:
        return finish(Outcome.ERROR, f"{DEFINITION} cannot be identified: {refused.reason}")

    loaded = evidence_record.load(target)
    reports, error = read_test_reports(target, evidence_record.junit_patterns(target, loaded))
    if error:
        return finish(Outcome.ERROR, error)
    report["sources"] = [
        {
            "tool": "junit",
            "path": source.path,
            "content_digest": source.content_digest,
            "unidentified_skipped": source.unidentified_skipped,
        }
        for source in reports
    ]
    cases = [case for source in reports for case in source.cases]
    report["results"] = _bind(scenarios, cases)
    report["summary"]["scenarios"] = len(scenarios)
    report["summary"]["criteria"] = len(criteria)

    def count() -> None:
        for result in report["results"]:
            report["summary"][result["outcome"]] += 1

    if criteria:
        files, error = evaluation_results.read_results(target)
        if error:
            # The scenarios were judged; only the criteria could not be.
            count()
            return finish(Outcome.ERROR, error)
        report["sources"] += [
            {"tool": "evaluation-results", "path": f.path, "content_digest": f.content_digest}
            for f in files
        ]
        measurements = [m for f in files for m in f.results]
        report["results"] += [_judge(criterion, measurements) for criterion in criteria]
    count()
    outcome, detail = _outcome(report)
    report["provenance"] = evidence_record.provenance(
        target, report["sources"], observe=observe, loaded=loaded
    )
    state = report["provenance"]["state"]
    if outcome is not Outcome.ERROR and state not in (
        evidence_record.CURRENT,
        evidence_record.NOT_CHECKED,
    ):
        # The results may describe another commit or an earlier edit, so they
        # do not count. What they said stays in the detail and in each result.
        return finish(
            Outcome.INCONCLUSIVE,
            f"the results are {_PROVENANCE[state]}: {report['provenance']['detail']}. "
            f"As found: {detail}",
        )
    return finish(outcome, detail)


class _Unusable(Exception):
    """The criteria file exists and cannot be used. The message is the report's detail."""


def _read_criteria(path: Path, feature: str, described: dict) -> tuple:
    """The feature's criteria, recording the file's digest and form in `described`."""
    if path.is_symlink():
        raise _Unusable(f"{CRITERIA} is a symbolic link and was not read")
    if not path.is_file():
        return ()
    try:
        if path.stat().st_size > MAX_DEFINITION_BYTES:
            raise _Unusable(f"{CRITERIA} is larger than 1 MiB and was not read")
        data = path.read_bytes()
        document = parse_document(data)
    except (OSError, DocumentError) as exc:
        raise _Unusable(f"{CRITERIA} could not be read: {exc}") from None
    if not isinstance(document, dict):
        raise _Unusable(f"{CRITERIA} could not be read: it is not a mapping")
    digest = hashlib.sha256(data).hexdigest()
    described["content_digest"] = digest
    listed = document.get("criteria")
    if (
        isinstance(listed, list)
        and listed
        and all(isinstance(item, dict) and "id" in item and "name" not in item for item in listed)
    ):
        described["form"] = "data"
        return ()
    described["form"] = "named"
    try:
        return criterion_identity.read_criteria(feature, document, digest)
    except scenario_identity.IdentityError as refused:
        raise _Unusable(f"{CRITERIA} cannot be identified: {refused.reason}") from None
    except criterion_identity.CriteriaError as exc:
        raise _Unusable(f"{CRITERIA}: {exc}") from None


def _judge(criterion, measurements) -> dict:
    """One criterion against the measurements that name it. The worst decides."""
    target = criterion.target
    if target is not None:
        compared_with = {
            "target": {
                "metric": target.metric,
                "comparator": target.comparator,
                "value": target.value,
                "value_high": target.value_high,
                "unit": target.unit,
            }
        }
    elif criterion.threshold is not None:
        compared_with = {"threshold": criterion.threshold, "fail_on": criterion.fail_on}
    else:
        compared_with = None
    named = [m for m in measurements if m.requirement_id == criterion.id]
    listed = []
    states = set()
    note = None
    for measurement in named:
        met = None
        if measurement.errored:
            states.add("error")
        elif target is not None and (measurement.metric, measurement.unit) != (
            target.metric,
            target.unit,
        ):
            states.add("error")
            note = (
                "a measurement does not state the target's metric and unit "
                f"({target.metric}, {target.unit}), so it was not compared"
            )
        else:
            met = criterion_identity.compare(criterion, measurement.value)
            states.add("failed" if met is False else "passed")
            if met is None:
                note = "a result exists; it was not compared with a number"
        listed.append(
            {
                "value": measurement.value,
                "unit": measurement.unit,
                "metric": measurement.metric,
                "n": measurement.n,
                "met": met,
                "source": measurement.source,
            }
        )
    if not named:
        outcome = "missing" if criterion.execution_class == "free" else "owed"
    else:
        outcome = max(states, key=_SEVERITY.get)
    result = {
        "requirement_id": criterion.id,
        "revision_digest": criterion.revision_digest,
        "kind": "evaluation",
        "title": criterion.name,
        "tags": list(criterion.tags),
        "outcome": outcome,
        "execution_class": criterion.execution_class,
        "compared_with": compared_with,
        "measurements": listed,
    }
    if note:
        result["note"] = note
    return result


def exit_code(report: dict) -> int:
    """Zero only when every scenario and criterion passed. Anything else is not done."""
    return 0 if report["outcome"] == Outcome.PASS.value else 1


def _select(target: Path, feature: str) -> Path:
    available = {path.name: path for path in list_user_features(target / "features")}
    if feature not in available:
        raise SelectionError(
            f"--feature matched no feature directory: {feature!r}. "
            f"Available: {', '.join(available) or 'none'}."
        )
    return available[feature]


def _title_key(text: str) -> str:
    """Letters and digits, lower-cased, without a leading run of digits.

    This is how a runner such as pytest-bdd turns a scenario title into a test
    name, as far as it can be undone: punctuation and spaces are lost, and a
    name cannot start with a digit.
    """
    return "".join(ch for ch in text.lower() if ch.isalnum()).lstrip("0123456789")


def _test_key(name: str) -> str:
    if name.endswith("]") and "[" in name:
        name = name[: name.index("[")]
    if name.lower().startswith("test_"):
        name = name[5:]
    return _title_key(name)


def _bind(scenarios, cases: list[CaseResult]) -> list[dict]:
    keys = [_title_key(scenario.title) for scenario in scenarios]
    untagged: dict[str, list[CaseResult]] = {}
    for case in cases:
        if not case.scenarios:
            untagged.setdefault(_test_key(case.name), []).append(case)
    results = []
    for scenario, key in zip(scenarios, keys, strict=True):
        tag = f"@scenario:{scenario.slug}"
        # Every test that names the scenario counts, in either form. Keeping
        # only the id-bound ones would drop a failing test that used the tag.
        named = [case for case in cases if scenario.id in case.scenarios or tag in case.scenarios]
        note = None
        if named:
            by_id = any(scenario.id in case.scenarios for case in named)
            binding, bound = "id" if by_id else "tag", named
        elif key and keys.count(key) > 1:
            binding, bound = "none", []
            note = (
                "another scenario in this feature reduces to the same test name, "
                f"so it is not matched by title; name it with a {SCENARIO_PROPERTY} property"
            )
        elif key and key in untagged:
            binding, bound = "title", untagged[key]
        else:
            binding, bound = "none", []
        outcome = max((case.outcome for case in bound), key=_SEVERITY.get, default="missing")
        result = {
            "requirement_id": scenario.id,
            "revision_digest": scenario.revision_digest,
            "kind": "test",
            "title": scenario.title,
            "id_source": scenario.id_source,
            "tags": list(scenario.tags),
            "outcome": outcome,
            "binding": binding,
            "tests": [
                {
                    "name": case.name,
                    "classname": case.classname,
                    "outcome": case.outcome,
                    "source": case.source,
                }
                for case in bound
            ],
        }
        if note:
            result["note"] = note
        results.append(result)
    return results


def _outcome(report: dict) -> tuple[Outcome, str]:
    summary = report["summary"]
    scenarios, criteria = summary["scenarios"], summary["criteria"]
    # A feature with no scenarios is never done, but a criterion that errored
    # or failed is still reported as that and not hidden behind it.
    if scenarios == 0 and not (summary["error"] or summary["failed"]):
        return Outcome.INCONCLUSIVE, f"{DEFINITION} has no scenarios"
    scope = f"{scenarios} scenarios"
    if criteria:
        scope += f" and {criteria} {'criterion' if criteria == 1 else 'criteria'}"
    counts = ", ".join(f"{summary[state]} {state}" for state in STATES[1:] if summary[state])
    named = [
        f"{_name(result)} ({result['outcome']})"
        for result in report["results"]
        if result["outcome"] != "passed"
    ]
    more = len(named) - _NAMED_IN_DETAIL
    listed = ", ".join(named[:_NAMED_IN_DETAIL]) + (f" and {more} more" if more > 0 else "")
    detail = f"{counts} of {scope}: {listed}"
    if summary["error"]:
        return Outcome.ERROR, detail
    if summary["failed"]:
        return Outcome.FAIL, detail
    if summary["skipped"] or summary["missing"] or summary["owed"]:
        return Outcome.INCONCLUSIVE, detail
    unmarked = [source for source in report["sources"] if source.get("unidentified_skipped")]
    if unmarked:
        return Outcome.INCONCLUSIVE, (
            f"{scenarios} of {scenarios} scenarios have a passing result, but "
            f"{unmarked[0]['path']} counts {unmarked[0]['unidentified_skipped']} skipped tests "
            "that are not marked, so a passed test cannot be told from a skipped one"
        )
    if report["feature"]["criteria"]["form"] == "data":
        return (
            Outcome.INCONCLUSIVE,
            f"{scenarios} of {scenarios} scenarios passed, but {_DATA_FORM}",
        )
    passed = f"{scenarios} of {scenarios} scenarios"
    if criteria:
        passed += f" and {criteria} of {criteria} criteria"
    return Outcome.PASS, f"{passed} passed"


def _name(result: dict) -> str:
    """The scenario's slug, or the criterion's name."""
    if result["kind"] == "evaluation":
        return result["title"]
    return result["requirement_id"].partition("#scenario:")[2]


_LABEL = {
    "passed": "\033[32mpassed \033[0m",
    "failed": "\033[31mfailed \033[0m",
    "error": "\033[31merror  \033[0m",
    "skipped": "\033[33mskipped\033[0m",
    "missing": "\033[33mmissing\033[0m",
    "owed": "\033[33mowed   \033[0m",
    Outcome.PASS.value: "\033[32mPASS\033[0m",
    Outcome.FAIL.value: "\033[31mFAIL\033[0m",
    Outcome.INCONCLUSIVE.value: "\033[33mINCONCLUSIVE\033[0m",
    Outcome.ERROR.value: "\033[31mERROR\033[0m",
}
_BOUND_BY = {
    "id": "bound by id",
    "tag": "bound by tag",
    "title": "bound by title",
    "none": "no test result found",
}


def _bound(compared_with: dict | None) -> str:
    if compared_with is None:
        return "nothing to compare with"
    if "target" in compared_with:
        target = compared_with["target"]
        if target["comparator"] == "between":
            bound = f"between {target['value']:g} and {target['value_high']:g}"
        else:
            bound = f"{target['comparator']} {target['value']:g}"
        return f"target {bound} {target['unit']}"
    sign = {"below_threshold": ">= ", "above_threshold": "<= "}.get(compared_with["fail_on"])
    if sign is None:
        return f"threshold {compared_with['threshold']:g}, fails on {compared_with['fail_on']}"
    return f"threshold {sign}{compared_with['threshold']:g}"


def _measured(measurements: list[dict]) -> str:
    if not measurements:
        return "no result"
    first = measurements[0]
    if first["value"] is None:
        shown = "the evaluation errored"
    else:
        shown = f"{first['value']:g}" + (f" {first['unit']}" if first["unit"] else "")
    more = len(measurements) - 1
    return shown + (f" and {more} more" if more else "")


def _line(result: dict) -> str:
    if result["kind"] == "evaluation":
        return (
            f"{_measured(result['measurements'])}, {_bound(result['compared_with'])}"
            f"  [{result['execution_class']}]"
        )
    tests = len(result["tests"])
    how = _BOUND_BY[result["binding"]]
    if tests:
        how = f"{tests} test{'s' if tests != 1 else ''}, {how}"
    nfr = [tag for tag in result["tags"] if tag.startswith("@nfr")]
    return f"({how})" + (f"  {' '.join(nfr)}" if nfr else "")


def render_text(report: dict) -> str:
    lines = [f"\ngovkit evidence — feature {report['feature']['name']}\n"]
    results = report["results"]
    width = max((len(_name(result)) for result in results), default=0)
    for kind, heading in (("test", None), ("evaluation", "  Criteria")):
        of_kind = [result for result in results if result["kind"] == kind]
        if of_kind and heading:
            lines += ["", heading]
        for result in of_kind:
            label = _LABEL[result["outcome"]]
            lines.append(f"  {label}  {_name(result).ljust(width)}  {_line(result)}")
            if "note" in result:
                lines.append(f"           {result['note']}")
    if results:
        lines.append("")
    lines.append(f"  Working  {_LABEL[report['outcome']]}  {report['detail']}")
    tests = [result for result in results if result["kind"] == "test"]
    if any(tag.startswith("@nfr") for result in tests for tag in result["tags"]):
        lines.append(f"\n{_NFR_NOTE}")
    if report["summary"]["owed"]:
        lines.append(f"\n{_OWED_NOTE}")
    provenance = report["provenance"]
    if provenance["state"] == evidence_record.CURRENT:
        lines.append(
            f"\nThe results were recorded at {provenance['recorded_at']} from commit "
            f"{provenance['commit'][:12]}, and the commit and working tree have not changed "
            "since. A record can be rewritten without running the tests again; "
            "the run that counts is CI on a clean checkout.\n"
        )
    else:
        lines.append("")
    return "\n".join(lines)
