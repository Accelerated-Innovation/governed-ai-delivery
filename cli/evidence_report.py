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
"""`govkit evidence --feature`: each scenario bound to a test result.

The report starts from the scenarios in `features/<name>/acceptance.feature`
and looks for a result for each one, so a scenario nobody ran is reported as
missing instead of going unnoticed. Identity comes from `scenario_identity`,
which mirrors the Product Definition Graph.

The dictionary `build_report` returns is the canonical report. The text output
is a rendering of it, and so is every later export. It is read-only and
offline: it reads the feature file and the JUnit XML under the target and
writes nothing. A `PASS` shows that every scenario has a passing test result
in the files found. It does not show which commit produced those files, or
that a test asserts what its scenario says. See docs/EVIDENCE_REPORT.md.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from . import scenario_identity
from .evidence import SCENARIO_PROPERTY, CaseResult, Outcome, read_test_reports
from .features import list_user_features

SCHEMA = "evidence-report"
KIND = "govkit.evidence-report"
DEFINITION = "acceptance.feature"
MAX_DEFINITION_BYTES = 1024 * 1024
STATES = ("passed", "failed", "error", "skipped", "missing")
# The worst of a scenario's test cases decides its state.
_SEVERITY = {"passed": 0, "skipped": 1, "failed": 2, "error": 3}
_NAMED_IN_DETAIL = 5
_NFR_NOTE = (
    "A passing @nfr scenario shows that its test passed. "
    "It does not show that the test asserts the value written in the scenario."
)


class SelectionError(ValueError):
    """`--feature` named no feature directory."""


def build_report(target: Path, feature: str) -> dict:
    """The canonical report for one feature. Raises `SelectionError`."""
    directory = _select(target, feature)
    definition = directory / DEFINITION
    report = {
        "schema_version": 1,
        "kind": KIND,
        "feature": {
            "name": feature,
            "definition": definition.relative_to(target).as_posix(),
            "content_digest": None,
        },
        "outcome": Outcome.INCONCLUSIVE.value,
        "detail": "",
        "summary": {"scenarios": 0, **{state: 0 for state in STATES}},
        "sources": [],
        "results": [],
    }

    def finish(outcome: Outcome, detail: str) -> dict:
        report["outcome"], report["detail"] = outcome.value, detail
        return report

    if directory.is_symlink() or definition.is_symlink():
        return finish(Outcome.ERROR, f"{DEFINITION} is behind a symbolic link and was not read")
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

    reports, error = read_test_reports(target)
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
    for result in report["results"]:
        report["summary"][result["outcome"]] += 1
    report["summary"]["scenarios"] = len(scenarios)
    return finish(*_outcome(report))


def exit_code(report: dict) -> int:
    """Zero only when every scenario passed. Anything else is not done."""
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
    total = summary["scenarios"]
    if total == 0:
        return Outcome.INCONCLUSIVE, f"{DEFINITION} has no scenarios"
    counts = ", ".join(f"{summary[state]} {state}" for state in STATES[1:] if summary[state])
    named = [
        f"{_slug(result)} ({result['outcome']})"
        for result in report["results"]
        if result["outcome"] != "passed"
    ]
    more = len(named) - _NAMED_IN_DETAIL
    listed = ", ".join(named[:_NAMED_IN_DETAIL]) + (f" and {more} more" if more > 0 else "")
    detail = f"{counts} of {total} scenarios: {listed}"
    if summary["error"]:
        return Outcome.ERROR, detail
    if summary["failed"]:
        return Outcome.FAIL, detail
    if summary["skipped"] or summary["missing"]:
        return Outcome.INCONCLUSIVE, detail
    unmarked = [source for source in report["sources"] if source["unidentified_skipped"]]
    if unmarked:
        return Outcome.INCONCLUSIVE, (
            f"{total} of {total} scenarios have a passing result, but {unmarked[0]['path']} "
            f"counts {unmarked[0]['unidentified_skipped']} skipped tests that are not marked, "
            "so a passed test cannot be told from a skipped one"
        )
    return Outcome.PASS, f"{total} of {total} scenarios passed"


def _slug(result: dict) -> str:
    return result["requirement_id"].partition("#scenario:")[2]


_LABEL = {
    "passed": "\033[32mpassed \033[0m",
    "failed": "\033[31mfailed \033[0m",
    "error": "\033[31merror  \033[0m",
    "skipped": "\033[33mskipped\033[0m",
    "missing": "\033[33mmissing\033[0m",
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


def render_text(report: dict) -> str:
    lines = [f"\ngovkit evidence — feature {report['feature']['name']}\n"]
    width = max((len(_slug(result)) for result in report["results"]), default=0)
    for result in report["results"]:
        tests = len(result["tests"])
        how = _BOUND_BY[result["binding"]]
        if tests:
            how = f"{tests} test{'s' if tests != 1 else ''}, {how}"
        nfr = [tag for tag in result["tags"] if tag.startswith("@nfr")]
        tags = f"  {' '.join(nfr)}" if nfr else ""
        lines.append(f"  {_LABEL[result['outcome']]}  {_slug(result).ljust(width)}  ({how}){tags}")
        if "note" in result:
            lines.append(f"           {result['note']}")
    if report["results"]:
        lines.append("")
    lines.append(f"  Working  {_LABEL[report['outcome']]}  {report['detail']}")
    if any(tag.startswith("@nfr") for result in report["results"] for tag in result["tags"]):
        lines.append(f"\n{_NFR_NOTE}")
    lines.append(
        "\nThis reports the test results found under the target. "
        "Which commit produced them is not checked.\n"
    )
    return "\n".join(lines)
