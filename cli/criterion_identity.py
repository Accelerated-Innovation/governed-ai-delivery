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
"""Criterion identity, targets and comparison, as the Product Definition Graph has them.

A criterion in `eval_criteria.yaml` is identified, and its `target` is read
and compared, the way `discovery-engine` does it (`requirements.py`:
`criteria_from`, `_meets`). A copied fixture pins this module to the engine.
Do not improve those rules here: a criterion GovKit reports as met must be one
the graph reports as met.

The reading is lenient where the engine's is. Unknown keys are ignored, and
checking the file against its schema stays with `govkit validate`. The target
is read strictly, because it is compared.

Two things are GovKit's own and the graph ignores them:

- `execution_class` says who may run a criterion: `free`, `paid` or `human`.
- A criterion without a target is compared with `threshold` and `fail_on`.

It is pure: a parsed document in, criteria out.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from .scenario_identity import TITLE_MAX, IdentityError

COMPARATORS = (">=", "<=", "==", "between")
# The engine's MeasurementUnit, a closed set.
UNITS = ("seconds", "minutes", "hours", "days", "percent", "ratio", "count", "currency")
# Who may run a criterion. `free` is the default; GovKit starts none of them.
EXECUTION_CLASSES = ("free", "paid", "human")
_DEFAULT_CLASS = "free"


class CriteriaError(ValueError):
    """A GovKit rule about a criterion was broken; the graph has no such rule."""


@dataclass(frozen=True)
class Target:
    metric: str
    comparator: str
    value: float
    value_high: float | None
    unit: str


@dataclass(frozen=True)
class Criterion:
    id: str
    name: str
    threshold: float | None
    fail_on: str | None
    target: Target | None
    execution_class: str
    tags: tuple[str, ...]
    revision_digest: str  # SHA-256 of the criteria file's bytes


def criterion_id(package: str, name: str) -> str:
    return f"{package}#evaluation:{name}"


def read_criteria(package: str, document: Mapping, digest: str) -> tuple[Criterion, ...]:
    """The criteria of one parsed `eval_criteria.yaml`, in source order.

    Raises `IdentityError` where the graph would refuse the file, and
    `CriteriaError` for an unknown `execution_class`.
    """
    llm = document.get("llm_evaluation", {})
    if not isinstance(llm, Mapping):
        raise IdentityError("parse_error")
    criteria: list[Criterion] = []
    seen: set[str] = set()
    for source in (llm.get("criteria", []), document.get("criteria", [])):
        if not isinstance(source, list):
            raise IdentityError("parse_error")
        for item in source:
            criterion = _criterion(package, item, digest)
            if criterion.id in seen:
                raise IdentityError("slug_collision")
            seen.add(criterion.id)
            criteria.append(criterion)
    return tuple(criteria)


def meets(target: Target, value: float) -> bool:
    if target.comparator == ">=":
        return value >= target.value
    if target.comparator == "<=":
        return value <= target.value
    if target.comparator == "==":
        return value == target.value
    return target.value <= value <= target.value_high


def compare(criterion: Criterion, value: float) -> bool | None:
    """Whether `value` satisfies the criterion, or None when it declares nothing to compare.

    A target is used ahead of the threshold. `fail_on: error` and
    `fail_on: missing_signal` ask only that a result exists.
    """
    if criterion.target is not None:
        return meets(criterion.target, value)
    if criterion.threshold is None:
        return None
    if criterion.fail_on == "below_threshold":
        return value >= criterion.threshold
    if criterion.fail_on == "above_threshold":
        return value <= criterion.threshold
    return None


def _criterion(package: str, item: object, digest: str) -> Criterion:
    if not isinstance(item, Mapping):
        raise IdentityError("parse_error")
    name = item.get("name")
    if not isinstance(name, str) or not name:
        raise IdentityError("parse_error")
    if len(name) > TITLE_MAX:
        raise IdentityError("title_too_long")
    fail_on = item.get("fail_on")
    execution_class = item.get("execution_class", _DEFAULT_CLASS)
    if execution_class not in EXECUTION_CLASSES:
        raise CriteriaError(
            f"criterion {name!r} has an unknown execution_class; "
            f"use one of {', '.join(EXECUTION_CLASSES)}"
        )
    tags = item.get("tags")
    return Criterion(
        id=criterion_id(package, name),
        name=name,
        threshold=_number(item.get("threshold")),
        fail_on=fail_on if isinstance(fail_on, str) else None,
        target=_target(item.get("target")),
        execution_class=execution_class,
        tags=tuple(tag for tag in tags if isinstance(tag, str)) if isinstance(tags, list) else (),
        revision_digest=digest,
    )


def _target(target: object) -> Target | None:
    if target is None:
        return None
    if not isinstance(target, Mapping):
        raise IdentityError("parse_error")
    metric = target.get("metric")
    comparator = target.get("comparator")
    unit = target.get("unit")
    value, high = _number(target.get("value")), _number(target.get("value_high"))
    if not (
        isinstance(metric, str)
        and metric
        and isinstance(comparator, str)
        and comparator in COMPARATORS
        and isinstance(unit, str)
        and unit in UNITS
        and value is not None
    ):
        raise IdentityError("parse_error")
    if comparator == "between" and high is None:
        raise IdentityError("parse_error")
    return Target(metric, comparator, value, high if comparator == "between" else None, unit)


def _number(value: object) -> float | None:
    if isinstance(value, int | float) and not isinstance(value, bool):
        try:
            return float(value)
        except OverflowError:
            # An integer no float can hold. Refused, so it is reported and not raised.
            raise IdentityError("parse_error") from None
    return None
