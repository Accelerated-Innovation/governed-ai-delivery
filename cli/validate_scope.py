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
"""Feature-scoped `govkit validate` with a known-failures record.

Runs the same checks as `validate.run_validation`, narrowed to selected
features, and reports each failure as new or known against an explicit
caller-reviewed record. It changes no check and no threshold. A passing run
shows artifact consistency for the selection; it is not review, approval or
evidence that a control ran. See ADR 0021 and docs/KNOWN_FAILURES.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from . import known_failures as kf
from . import validate
from .features import list_user_features
from .marker import read_govkit_marker
from .validate import CheckStatus

KNOWN = "\033[33mKNOWN\033[0m"
RESOLVED = "\033[32mRESOLVED\033[0m"


@dataclass(frozen=True)
class Result:
    key: kf.Key
    status: CheckStatus
    message: str


def _feature_results(target, feature_dir, artifacts, named, only_experiments, strict, now):
    name = feature_dir.name
    results = []
    for check, function in [] if only_experiments else named:
        if check == validate.CHECK_COMPLETENESS:
            problems = validate.completeness_problems(feature_dir, artifacts)
            if problems:
                results.extend(
                    Result(
                        ("feature", name, check, artifact),
                        CheckStatus.FAIL,
                        f"{artifact} is {state}",
                    )
                    for artifact, state in problems
                )
                continue
        outcome = function(feature_dir)
        for status, message in outcome if isinstance(outcome, list) else [outcome]:
            results.append(Result(("feature", name, check, None), status, message))
    for status, message, finding in validate.experiment_results(
        target, feature_dir, strict=strict, now=now
    ):
        key = ("feature", name, validate.CHECK_EXPERIMENTS, finding)
        results.append(Result(key, status, message))
    return results


def _repository_results(target, strict, level):
    """Extension, fix-record and approval results as `(kind, title, results)`."""
    from .fixes import FIXES_DIR

    sections = []
    extensions = [
        Result(("extension", name, kf.CHECK_EXTENSION, None), status, message)
        for name, status, message in validate.extension_results(target, strict)
    ]
    sections.append(("extension", "extensions", extensions))
    if level != "3":
        fixes = [
            Result(
                ("fix", rel, kf.CHECK_FIX, None),
                status,
                message if rel in message else f"{rel}: {message}",
            )
            for rel, status, message in validate.fix_results(target)
        ]
        sections.append(("fix", f"{FIXES_DIR}/", fixes))
        approvals = [
            Result(("approval", None, kf.CHECK_APPROVAL, None), status, message)
            for status, message in validate.approval_results(target)
        ]
        sections.append(("approval", "ADR approval attestation", approvals))
    return sections


def _line(result: Result, known: frozenset) -> str:
    label = validate._STATUS_LABEL[result.status]
    if result.status is CheckStatus.FAIL and result.key in known:
        label = KNOWN
    return f"  {label}  [{kf.identifier(result.key[2], result.key[3])}] {result.message}"


def _error(message: str) -> int:
    print(f"Error: {message}")
    return 1


def run_scoped_validation(
    target: Path,
    *,
    level: str | None = None,
    strict: bool = False,
    only: str | None = None,
    features=(),
    known_failures: Path | None = None,
    expected_digest: str | None = None,
    print_record: bool = False,
    now: datetime | None = None,
) -> int:
    """Run validate for a selection and classify failures. Returns the exit code.

    `print_record` prints the current failures in the record format in place of
    the report and returns 0; the caller reviews and saves that text.
    """
    if not target.exists():
        return _error(f"target directory '{target}' does not exist.")
    if expected_digest is not None and known_failures is None:
        return _error("--known-failures-digest requires --known-failures.")
    now = now or datetime.now(timezone.utc)

    record = None
    if known_failures is not None:
        try:
            record = kf.load(Path(known_failures))
        except kf.RecordError as exc:
            return _error(f"known-failures record {known_failures}: {exc}")
        if expected_digest is not None:
            expected = expected_digest.strip().lower().removeprefix("sha256:")
            if expected != record.digest:
                return _error(
                    f"known-failures record {known_failures}: digest sha256:{record.digest} "
                    f"does not match the expected sha256:{expected}"
                )
    known = record.entries if record else frozenset()

    only_experiments = only == "experiments"
    marker = {} if only_experiments else (read_govkit_marker(target) or {})
    if not only_experiments and level is None:
        level = marker.get("level") or "3"
    has_features = only_experiments or level != "3"

    names = list(dict.fromkeys(features))
    feature_dirs: list[Path] = []
    artifacts, named = [], []
    if has_features:
        features_dir = target / "features"
        # Both legacy runners refuse a target without features/; a scoped
        # option must not turn a mistargeted checkout into an empty pass.
        if not features_dir.exists():
            return _error(f"no features/ directory found in '{target}'.")
        available = {d.name: d for d in list_user_features(features_dir)}
        unknown = [name for name in names if name not in available]
        if unknown:
            return _error(
                "--feature matched no feature directory: "
                + ", ".join(repr(name) for name in unknown)
                + f". Available: {', '.join(available) or 'none'}."
            )
        feature_dirs = [available[name] for name in names] if names else list(available.values())
        if not only_experiments:
            artifacts, named = validate._named_checks(
                level, (marker.get("options") or {}).get("type")
            )

    sections = [] if only_experiments else _repository_results(target, strict, level)
    blocks = [
        (
            feature_dir,
            _feature_results(target, feature_dir, artifacts, named, only_experiments, strict, now),
        )
        for feature_dir in feature_dirs
    ]
    results = [r for _kind, _title, items in sections for r in items]
    results += [r for _dir, items in blocks for r in items]
    failures = [r for r in results if r.status is CheckStatus.FAIL]

    if print_record:
        try:
            text = kf.render(r.key for r in failures)
        except kf.RecordError as exc:
            return _error(f"cannot print a known-failures record: {exc}.")
        print(text, end="")
        return 0

    # A record entry applies to this run when its check was evaluated for its
    # scope. Entries that do not apply are ignored, never reported as resolved.
    feature_checks = {validate.CHECK_EXPERIMENTS} | {check for check, _fn in named}
    evaluated_kinds = {kind for kind, _title, _items in sections}
    present = {r.key for r in results if r.status is not CheckStatus.PASS}
    failing = {r.key for r in failures}
    resolved, ignored = [], 0
    for key in sorted(known - failing, key=lambda k: tuple(p or "" for p in k)):
        kind, name, check, _finding = key
        if kind == "feature":
            applies = has_features and check in feature_checks and (not names or name in names)
        else:
            applies = kind in evaluated_kinds
        if applies and key not in present:
            resolved.append(key)
        else:
            ignored += 1

    if record:
        inside = record.path.resolve().is_relative_to(target.resolve())
        place = "inside" if inside else "outside"
        print(f"\nKnown-failures record: {record.path} ({place} the inspected tree)")
        print(f"  digest: sha256:{record.digest}")

    for _kind, title, items in sections:
        if items:
            print(f"\ngovkit validate — {title}\n")
            for result in items:
                print(_line(result, known))
            print()

    if only_experiments:
        print("\ngovkit validate — architecture experiments\n")
    elif level == "3":
        print(validate.LEVEL_3_NOTICE)
    else:
        label = validate.LEVEL_LABELS.get(level, f"L{level}")
        print(f"\ngovkit validate — governance compliance check ({label})\n")
    reported = 0
    for feature_dir, items in blocks:
        if not items:
            continue
        reported += 1
        print(f"features/{feature_dir.name}/")
        for result in items:
            print(_line(result, known))
        print()
    if only_experiments and not reported:
        print("No architecture experiment records or preflight outcomes found.")
    elif has_features and not feature_dirs:
        print("No feature directories found to validate.")

    if resolved:
        print("Resolved known failures — remove them from the record:")
        for key in resolved:
            print(f"  {RESOLVED}  {kf.describe(key)}")
        print()

    new = sum(1 for r in failures if r.key not in known)
    print(
        f"{len(feature_dirs)} feature(s) selected: {new} new failure(s), "
        f"{len(failures) - new} known, {len(resolved)} resolved"
    )
    if ignored:
        print(
            f"{ignored} record entr{'y' if ignored == 1 else 'ies'} not applicable to this run "
            "ignored (outside the selection, or not failing without --strict)"
        )
    return 1 if new or (strict and resolved) else 0
