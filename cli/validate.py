#!/usr/bin/env python3
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
"""
govkit validate — governance compliance checker

Checks that all features in a target project have the required governance
artifacts and that those artifacts meet minimum quality thresholds.

Level-aware: Level 3 checks fewer artifacts and skips evaluation scoring.
Level 4 checks all 5 artifacts with full evaluation enforcement.

Depends only on the standard library plus pyyaml, a declared runtime dependency
(see `pyproject.toml`). Full JSON Schema validation of eval_criteria.yaml is
deferred to CI or `check-jsonschema` if installed.
"""

import re
import subprocess
from enum import Enum
from pathlib import Path

import yaml

from .features import list_user_features
from .marker import TYPE_AREA, read_govkit_marker

# ---------------------------------------------------------------------------
# Artifact file name constants
# ---------------------------------------------------------------------------

_ACCEPTANCE_FEATURE = "acceptance.feature"
_NFRS_MD = "nfrs.md"
_PLAN_MD = "plan.md"
_EVAL_CRITERIA_YAML = "eval_criteria.yaml"
_ARCH_PREFLIGHT_MD = "architecture_preflight.md"

_RE_MODE_LLM = r"^\s*mode:\s*llm\b"
_RE_MULTI_AGENT = r"^\s*multi_agent:\s*true\b"
_AGENT_TOPOLOGY_MD = "agent_topology.md"

# nfrs.md section contract — see docs/{backend,ui}/architecture/NFRS_CONVENTIONS.md.
# Required sections are hard-gated by repo-scope-check CI and the Architecture Preflight,
# so check_nfrs_sections surfaces deviations as WARN rather than duplicating those gates.
NFRS_REQUIRED_SECTIONS = ("Repository Scope",)
NFRS_RECOMMENDED_SECTIONS = ("Out of scope",)

# L3 (Foundations) has no per-feature artifacts; validation short-circuits
# at L3 in run_validation(). The 5-artifact contract starts at L4.
L4_REQUIRED_ARTIFACTS = [
    _ACCEPTANCE_FEATURE,
    _NFRS_MD,
    _EVAL_CRITERIA_YAML,
    _ARCH_PREFLIGHT_MD,
    _PLAN_MD,
]

# Default for backward compatibility
REQUIRED_ARTIFACTS = L4_REQUIRED_ARTIFACTS

PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"
WARN = "\033[33mWARN\033[0m"


class CheckStatus(Enum):
    """Outcome of one governance check on a feature. WARN surfaces a visible
    gap without failing the run."""

    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"


_STATUS_LABEL = {
    CheckStatus.PASS: PASS,
    CheckStatus.FAIL: FAIL,
    CheckStatus.WARN: WARN,
}


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def check_completeness(feature_dir: Path, artifacts: list[str] | None = None) -> tuple[CheckStatus, str]:
    """Check that all required artifacts exist and are non-empty."""
    if artifacts is None:
        artifacts = L4_REQUIRED_ARTIFACTS
    missing = []
    empty = []
    for artifact in artifacts:
        path = feature_dir / artifact
        if not path.exists():
            missing.append(artifact)
        elif path.stat().st_size == 0:
            empty.append(artifact)
    if missing or empty:
        parts = []
        if missing:
            parts.append(f"missing: {', '.join(missing)}")
        if empty:
            parts.append(f"empty: {', '.join(empty)}")
        present = len(artifacts) - len(missing)
        return CheckStatus.FAIL, f"{present}/{len(artifacts)} artifacts — {'; '.join(parts)}"
    return CheckStatus.PASS, f"{len(artifacts)}/{len(artifacts)} required artifacts present"


def check_gherkin_syntax(feature_dir: Path) -> tuple[CheckStatus, str]:
    """Basic Gherkin structure validation using text matching."""
    path = feature_dir / _ACCEPTANCE_FEATURE
    if not path.exists():
        return CheckStatus.FAIL, f"{_ACCEPTANCE_FEATURE} not found"
    text = path.read_text(encoding="utf-8")
    issues = []
    if not re.search(r"^Feature:", text, re.MULTILINE):
        issues.append("missing 'Feature:' keyword")
    if not re.search(r"^\s*Scenario:", text, re.MULTILINE):
        issues.append("no 'Scenario:' found")
    active_lines = [ln for ln in text.splitlines() if not ln.strip().startswith("#")]
    active_text = "\n".join(active_lines)
    if not re.search(r"^\s*(Given|When|Then)", active_text, re.MULTILINE):
        issues.append("no Given/When/Then steps found")
    if issues:
        return CheckStatus.FAIL, f"{_ACCEPTANCE_FEATURE}: {'; '.join(issues)}"
    return CheckStatus.PASS, f"{_ACCEPTANCE_FEATURE} has valid Gherkin structure"


# A line that *talks about* TBD rather than leaving one. `**TBD**` is the
# emphasised form starters use ("Replace every **TBD** with a real value");
# "TBD entries" is how the govkit rule itself is phrased. Both are documentation,
# not placeholders — the bare \bTBD\b scan matched govkit's own worked example,
# failing `govkit validate` on a file govkit ships.
_RE_TBD_SELF_REFERENCE = re.compile(r"\*\*TBD\*\*|\bTBD entries\b")


def check_nfrs_no_tbd(feature_dir: Path) -> tuple[CheckStatus, str]:
    """Check that nfrs.md has no remaining TBD placeholders.

    Placeholders occur in several real shapes across `features/*/nfrs.md` — a bare
    list item, a value after a colon, a table cell, and mid-sentence ("Baseline TBD
    after 2 weeks") — so the scan stays deliberately broad. Only the two
    self-referential forms above are exempt.
    """
    path = feature_dir / _NFRS_MD
    if not path.exists():
        return CheckStatus.FAIL, f"{_NFRS_MD} not found"
    lines = path.read_text(encoding="utf-8").splitlines()
    tbd_lines = [
        i + 1
        for i, ln in enumerate(lines)
        if re.search(r"\bTBD\b", ln) and not _RE_TBD_SELF_REFERENCE.search(ln)
    ]
    if tbd_lines:
        return CheckStatus.FAIL, f"{_NFRS_MD} contains TBD entries (lines {', '.join(map(str, tbd_lines))})"
    return CheckStatus.PASS, f"{_NFRS_MD} has no TBD entries"


def check_nfrs_sections(feature_dir: Path) -> tuple[CheckStatus, str]:
    """Advisory check of the nfrs.md section contract (see NFRS_CONVENTIONS.md).

    Required sections (Repository Scope) are hard-gated elsewhere — repo-scope-check CI
    and the Architecture Preflight — so a deviation surfaces here as WARN rather than FAIL,
    keeping the local validate run informative without duplicating those gates. Recommended
    sections (Out of scope) also WARN when absent; spec planning then infers and labels them.

    A section counts only when it is *populated*: its body must hold real content after
    whitespace-only lines and HTML comments are stripped. An empty `## Out of scope` — header
    only, or header plus a placeholder comment — is treated as missing, matching
    spec-planning's "missing or empty -> infer and label" behaviour (otherwise the validator
    would say OK while the plan still inserts an INFERRED marker). Returns PASS when the full
    contract is met.
    """
    path = feature_dir / _NFRS_MD
    if not path.exists():
        return CheckStatus.FAIL, f"{_NFRS_MD} not found"
    text = path.read_text(encoding="utf-8")

    def _populated(section: str) -> bool:
        """True only when the section header exists AND its body is non-empty after
        stripping whitespace-only lines and HTML comments."""
        header = re.search(rf"^##\s+{re.escape(section)}\b.*$", text,
                           re.MULTILINE | re.IGNORECASE)
        if not header:
            return False
        nxt = re.search(r"^##\s", text[header.end():], re.MULTILINE)
        body = text[header.end():header.end() + nxt.start()] if nxt else text[header.end():]
        body = re.sub(r"<!--.*?-->", "", body, flags=re.DOTALL)
        return bool(body.strip())

    missing_required = [s for s in NFRS_REQUIRED_SECTIONS if not _populated(s)]
    if missing_required:
        sections = ", ".join(f"## {s}" for s in missing_required)
        return CheckStatus.WARN, (f"{_NFRS_MD} missing or empty required section(s) {sections} "
                      f"(NFRS_CONVENTIONS.md) — hard-gated by repo-scope-check/preflight")

    missing_recommended = [s for s in NFRS_RECOMMENDED_SECTIONS if not _populated(s)]
    if missing_recommended:
        sections = ", ".join(f"## {s}" for s in missing_recommended)
        return CheckStatus.WARN, (f"{_NFRS_MD} {sections} missing or empty — "
                      f"spec planning will infer deferrals (NFRS_CONVENTIONS.md)")

    return CheckStatus.PASS, f"{_NFRS_MD} section contract OK (Repository Scope + Out of scope populated)"


# marker.TYPE_AREA maps options.type to its governance area. data maps to its
# own area, which ships no schema yet — the resolver then reports the gap
# instead of consulting another type's (possibly stale) governance tree.
_NO_SCHEMA_REASON = "no eval_criteria schema installed for this project type"


def _resolve_eval_schema(feature_dir: Path) -> tuple[Path | None, str]:
    """Resolve the installed eval_criteria schema governing this feature.

    Returns (schema, "") when resolved, or (None, reason) when instance
    validation must be skipped. The marker's options.type decides the
    governance area — a stale tree left by a previous `apply --type` must
    not be validated against. Scanning is the fallback for markerless or
    unknown-type layouts, and it refuses to guess when more than one area
    ships a schema.

    Standard layout: feature_dir is <target>/features/<name>; the marker and
    governance/ live at <target>. A few ancestors are walked so a
    non-standard nesting still resolves.
    """
    ancestors = list(feature_dir.parents)[:3]
    for ancestor in ancestors:
        marker = read_govkit_marker(ancestor)
        if not marker:
            continue
        area = TYPE_AREA.get((marker.get("options") or {}).get("type"))
        if area is None:
            break  # marker present but type unknown — fall back to scanning
        schema = ancestor / "governance" / area / "schemas" / "eval_criteria.schema.json"
        if schema.is_file():
            return schema, ""
        return None, _NO_SCHEMA_REASON

    matches: list[Path] = []
    for ancestor in ancestors:
        matches = sorted(ancestor.glob("governance/*/schemas/eval_criteria.schema.json"))
        if matches:
            break
    if len(matches) > 1:
        areas = ", ".join(sorted(p.parent.parent.name for p in matches))
        return None, (
            f"ambiguous eval_criteria schemas installed ({areas}) "
            "and no marker type to choose by"
        )
    if matches:
        return matches[0], ""
    return None, _NO_SCHEMA_REASON


def check_eval_criteria(feature_dir: Path) -> tuple[CheckStatus, str]:
    """Check eval_criteria.yaml required keys, then validate the instance
    against the installed schema via check-jsonschema.

    WARN when no schema is installed for this project type or the binary is
    unavailable — visible gaps, not silent green.
    """
    path = feature_dir / _EVAL_CRITERIA_YAML
    if not path.exists():
        return CheckStatus.FAIL, f"{_EVAL_CRITERIA_YAML} not found"
    text = path.read_text(encoding="utf-8")
    issues = []
    if not re.search(r"^version:", text, re.MULTILINE):
        issues.append("missing 'version' key")
    if not re.search(r"^mode:", text, re.MULTILINE):
        issues.append("missing 'mode' key")
    if issues:
        return CheckStatus.FAIL, f"{_EVAL_CRITERIA_YAML}: {'; '.join(issues)}"

    schema, skip_reason = _resolve_eval_schema(feature_dir)
    if schema is None:
        return CheckStatus.WARN, f"{_EVAL_CRITERIA_YAML} structure OK — {skip_reason}; instance validation skipped"
    try:
        result = subprocess.run(
            ["check-jsonschema", "--schemafile", str(schema), str(path)],
            capture_output=True, text=True, timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return CheckStatus.WARN, f"{_EVAL_CRITERIA_YAML} structure OK — install check-jsonschema for full validation"
    if result.returncode != 0:
        detail = (result.stdout or result.stderr or "").strip().splitlines()
        snippet = detail[-1] if detail else "schema validation failed"
        return CheckStatus.FAIL, f"{_EVAL_CRITERIA_YAML} fails {schema.name}: {snippet}"
    return CheckStatus.PASS, f"{_EVAL_CRITERIA_YAML} valid against {schema.name}"


# One fenced YAML block. Non-greedy *within* a block so an earlier fence cannot
# absorb a later one — the prediction block is then selected by content, not by
# being first. A single `.*?evaluation_prediction:.*?` pattern anchored on the
# first fence in the file and ran straight past intervening fences, so an
# unrelated earlier block's `: null` was reported as a prediction null.
_RE_YAML_BLOCK = re.compile(r"```ya?ml\s*\n(.*?)```", re.DOTALL)

# A score group declares its mean under one of these keys. Backend plans use
# `first:`/`virtues:` with `average:`; the UI template nests scores under
# `component_tests.FIRST_scores` and declares `predicted_average`.
_AVERAGE_KEYS = ("average", "predicted_average")

# Declared averages are recorded to one or two decimals, so 31/7 = 4.4285… is
# legitimately written 4.4. Tolerate rounding; catch a fabricated figure.
_AVERAGE_TOLERANCE = 0.05

# FIRST_SCORING_RUBRIC.md and VIRTUE_SCORING_RUBRIC.md both say:
# "Fail: average < 4.0 OR any individual score below 3". Only the average half
# was ever enforced.
_MIN_INDIVIDUAL_SCORE = 3


def _as_number(value: object) -> float | None:
    """Numeric value, excluding bool (which is an int subclass in Python)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _declared_average(node: dict) -> float | None:
    for key in _AVERAGE_KEYS:
        number = _as_number(node.get(key))
        if number is not None:
            return number
    return None


def _subtree_scores(node: dict) -> list[float]:
    """Every `score:` beneath this node, not descending into a nested group that
    declares its own average — so `first` and `virtues` stay separate."""
    scores = []
    for key, value in node.items():
        if key == "score":
            number = _as_number(value)
            if number is not None:
                scores.append(number)
        elif isinstance(value, dict) and _declared_average(value) is None:
            scores.extend(_subtree_scores(value))
    return scores


def _score_groups(node: object, label: str = "evaluation_prediction") -> list[tuple]:
    """(label, scores, declared_average) for every subtree declaring an average."""
    groups: list[tuple] = []
    if not isinstance(node, dict):
        return groups
    declared = _declared_average(node)
    if declared is not None:
        groups.append((label, _subtree_scores(node), declared))
    for key, value in node.items():
        if isinstance(value, dict):
            groups.extend(_score_groups(value, key))
    return groups


def _prediction_score_problems(block: str) -> tuple[list[str], list[str]]:
    """Cross-check each declared average against the scores beside it.

    The declared `average:` was previously read and never verified, so a plan
    could claim 4.5 over scores averaging 3.1. Groups that declare an average
    without individual scores are left alone — those plans stay valid.
    """
    try:
        parsed = yaml.safe_load(block)
    except yaml.YAMLError:
        return [], []  # eval-gate reports unparseable blocks; don't double-fail here
    prediction = parsed.get("evaluation_prediction") if isinstance(parsed, dict) else None

    inconsistent, low_scores = [], []
    for label, scores, declared in _score_groups(prediction):
        if not scores:
            continue
        computed = sum(scores) / len(scores)
        if abs(computed - declared) > _AVERAGE_TOLERANCE:
            inconsistent.append(
                f"{label} declares {declared:g} but its scores average {computed:.2f}"
            )
        low_scores.extend(
            f"{label}={score:g}" for score in scores if score < _MIN_INDIVIDUAL_SCORE
        )
    return inconsistent, low_scores


def check_plan_eval_prediction(feature_dir: Path) -> tuple[CheckStatus, str]:
    """Check that plan.md has an evaluation_prediction block with averages >= 4.0."""
    path = feature_dir / _PLAN_MD
    if not path.exists():
        return CheckStatus.FAIL, f"{_PLAN_MD} not found"
    text = path.read_text(encoding="utf-8")

    block = next(
        (b for b in _RE_YAML_BLOCK.findall(text) if "evaluation_prediction:" in b),
        None,
    )
    if block is None:
        return CheckStatus.FAIL, f"{_PLAN_MD} missing evaluation_prediction block"

    null_matches = re.findall(r":\s*null\b", block)
    if null_matches:
        return CheckStatus.FAIL, f"{_PLAN_MD} evaluation_prediction has {len(null_matches)} null value(s) — all must be populated"

    averages = re.findall(r"average:\s*([\d.]+)", block)
    if not averages:
        return CheckStatus.FAIL, f"{_PLAN_MD} evaluation_prediction missing average values"

    below_threshold = []
    for avg_str in averages:
        avg = float(avg_str)
        if avg < 4.0:
            below_threshold.append(avg_str)

    if below_threshold:
        return CheckStatus.FAIL, f"{_PLAN_MD} evaluation_prediction average(s) below 4.0: {', '.join(below_threshold)}"

    inconsistent, low_scores = _prediction_score_problems(block)
    if inconsistent:
        return CheckStatus.FAIL, (
            f"{_PLAN_MD} evaluation_prediction is internally inconsistent — "
            + "; ".join(inconsistent)
        )
    if low_scores:
        return CheckStatus.FAIL, (
            f"{_PLAN_MD} evaluation_prediction has individual score(s) below 3: "
            + ", ".join(low_scores)
        )
    return CheckStatus.PASS, f"{_PLAN_MD} evaluation_prediction averages OK ({', '.join(averages)})"


# A markdown table's delimiter row (`|---|:---:|`). Rows before it are the
# header; rows after it are data. Only data rows prove a section is populated.
_RE_TABLE_DELIMITER = re.compile(r"^\|(?:\s*:?-+:?\s*\|)+$")


def check_gherkin_nfr_coverage(feature_dir: Path) -> tuple[CheckStatus, str]:
    """Cross-reference populated NFR categories vs @nfr-* tags in acceptance.feature.

    A section heading may be either the plain category (`## Freshness`) or the
    tag form the data starter uses (`## @nfr-freshness`); both normalize to the
    same category. A section counts as populated when it has a non-TBD bullet
    (checkbox lines included) or a non-TBD table data row — a header-and-
    delimiter-only table is scaffolding, like a lone TBD bullet.
    """
    nfrs_path = feature_dir / _NFRS_MD
    feature_path = feature_dir / _ACCEPTANCE_FEATURE
    if not nfrs_path.exists() or not feature_path.exists():
        return CheckStatus.FAIL, f"cannot check NFR coverage — missing {_NFRS_MD} or {_ACCEPTANCE_FEATURE}"

    nfrs_text = nfrs_path.read_text(encoding="utf-8")
    feature_text = feature_path.read_text(encoding="utf-8")

    populated = []
    current_heading = None
    in_table = False
    for line in nfrs_text.splitlines():
        heading_match = re.match(r"^##\s+(.+)", line)
        if heading_match:
            current_heading = heading_match.group(1).strip().lower()
            current_heading = current_heading.removeprefix("@nfr-")
            in_table = False
            continue
        if current_heading is None:
            continue
        stripped = line.strip()
        if _RE_TABLE_DELIMITER.match(stripped):
            in_table = True
            continue
        is_bullet = stripped.startswith("- ")
        is_table_row = in_table and stripped.startswith("|")
        if (is_bullet or is_table_row) and "TBD" not in line:
            populated.append(current_heading)
            current_heading = None

    if not populated:
        return CheckStatus.PASS, "no populated NFR categories — tag coverage not required"

    tags_found = set(re.findall(r"@nfr-(\w+)", feature_text))

    # NFR categories whose population demands a matching @nfr-<category> tag.
    known_categories = frozenset({
        "performance", "availability", "security", "compliance",
        "scalability", "observability", "reliability", "compatibility",
        "freshness", "quality", "pii", "lineage", "cost",
    })

    missing_tags = [
        f"@nfr-{category}"
        for category in populated
        if category in known_categories and category not in tags_found
    ]

    if missing_tags:
        return CheckStatus.FAIL, f"Gherkin missing NFR tags: {', '.join(missing_tags)}"
    return CheckStatus.PASS, "Gherkin @nfr-* tag coverage matches populated NFR categories"


# ---------------------------------------------------------------------------
# L5-specific checks
# ---------------------------------------------------------------------------

LLM_NFR_CATEGORIES = {"llm latency", "llm cost", "llm fallback", "llm safety"}


def _is_multi_agent(feature_dir: Path) -> bool | None:
    """Returns True if eval_criteria.yaml declares multi_agent: true, None if file missing."""
    eval_path = feature_dir / _EVAL_CRITERIA_YAML
    if not eval_path.exists():
        return None
    return bool(re.search(_RE_MULTI_AGENT, eval_path.read_text(encoding="utf-8"), re.MULTILINE))


def check_agent_topology_exists(feature_dir: Path) -> tuple[CheckStatus, str]:
    """When multi_agent: true, agent_topology.md must exist and be non-empty."""
    is_ma = _is_multi_agent(feature_dir)
    if not is_ma:
        return CheckStatus.PASS, "multi_agent not declared — agent topology check not applicable"
    path = feature_dir / _AGENT_TOPOLOGY_MD
    if not path.exists():
        return CheckStatus.FAIL, f"{_AGENT_TOPOLOGY_MD} missing — required when multi_agent: true"
    if path.stat().st_size == 0:
        return CheckStatus.FAIL, f"{_AGENT_TOPOLOGY_MD} is empty"
    return CheckStatus.PASS, f"{_AGENT_TOPOLOGY_MD} present"


def check_agent_topology_sections(feature_dir: Path) -> tuple[CheckStatus, str]:
    """When multi_agent: true, agent_topology.md must have all required sections."""
    is_ma = _is_multi_agent(feature_dir)
    if not is_ma:
        return CheckStatus.PASS, "multi_agent not declared — agent topology sections check not applicable"
    path = feature_dir / _AGENT_TOPOLOGY_MD
    if not path.exists():
        return CheckStatus.FAIL, f"{_AGENT_TOPOLOGY_MD} not found"
    text = path.read_text(encoding="utf-8")
    required = [
        (r"^##\s+Orchestrator", "Orchestrator"),
        (r"^##\s+Specialist Agents", "Specialist Agents"),
        (r"^##\s+Routing Logic", "Routing Logic"),
        (r"^##\s+Failure Modes", "Failure Modes"),
    ]
    missing = [name for pattern, name in required
               if not re.search(pattern, text, re.MULTILINE)]
    if missing:
        return CheckStatus.FAIL, f"{_AGENT_TOPOLOGY_MD} missing sections: {', '.join(missing)}"
    return CheckStatus.PASS, f"{_AGENT_TOPOLOGY_MD} has all required sections"


def _is_mode_llm(feature_dir: Path) -> bool | None:
    """Check if eval_criteria.yaml exists and has mode: llm. Returns None if file missing."""
    eval_path = feature_dir / _EVAL_CRITERIA_YAML
    if not eval_path.exists():
        return None
    text = eval_path.read_text(encoding="utf-8")
    return bool(re.search(_RE_MODE_LLM, text, re.MULTILINE))


def check_llm_nfrs(feature_dir: Path) -> tuple[CheckStatus, str]:
    """Check that nfrs.md has populated LLM-specific NFR categories when mode is llm."""
    mode_llm = _is_mode_llm(feature_dir)
    if mode_llm is None:
        return CheckStatus.FAIL, f"{_EVAL_CRITERIA_YAML} not found — cannot check LLM NFRs"
    if not mode_llm:
        return CheckStatus.PASS, "mode is not llm — LLM NFR check not applicable"

    nfrs_path = feature_dir / _NFRS_MD
    if not nfrs_path.exists():
        return CheckStatus.FAIL, f"{_NFRS_MD} not found"
    nfrs_text = nfrs_path.read_text(encoding="utf-8")

    missing = []
    for category in sorted(LLM_NFR_CATEGORIES):
        pattern = rf"^##\s+{re.escape(category)}"
        heading_match = re.search(pattern, nfrs_text, re.MULTILINE | re.IGNORECASE)
        if not heading_match:
            missing.append(category)
            continue
        start = heading_match.end()
        next_heading = re.search(r"^##\s+", nfrs_text[start:], re.MULTILINE)
        section = nfrs_text[start:start + next_heading.start()] if next_heading else nfrs_text[start:]
        if re.search(r"\bTBD\b", section):
            missing.append(f"{category} (TBD)")

    if missing:
        return CheckStatus.FAIL, f"LLM NFR categories incomplete: {', '.join(missing)}"
    return CheckStatus.PASS, "LLM NFR categories populated (latency, cost, fallback, safety)"


def check_l5_eval_criteria(feature_dir: Path) -> tuple[CheckStatus, str]:
    """Check that mode:llm declares at least one model evaluation criterion.

    Evaluator products are selected by an implementation profile or ADR, so
    validation intentionally does not require a product-specific eval_class.
    """
    mode_llm = _is_mode_llm(feature_dir)
    if mode_llm is None:
        return CheckStatus.FAIL, f"{_EVAL_CRITERIA_YAML} not found"
    if not mode_llm:
        return CheckStatus.PASS, "mode is not llm — L5 eval criteria check not applicable"

    text = (feature_dir / _EVAL_CRITERIA_YAML).read_text(encoding="utf-8")
    has_llm_section = bool(re.search(r"^\s*llm_evaluation:\s*$", text, re.MULTILINE))
    criterion_count = len(re.findall(r"^\s*eval_class:\s*\S+", text, re.MULTILINE))
    if not has_llm_section or criterion_count == 0:
        return CheckStatus.FAIL, (
            f"{_EVAL_CRITERIA_YAML} mode is llm but llm_evaluation has no criteria"
        )
    return CheckStatus.PASS, f"L5 eval criteria present ({criterion_count} declared)"


def check_l5_preflight_sections(feature_dir: Path) -> tuple[CheckStatus, str]:
    """Check that architecture_preflight.md has L5 sections (10-14) when mode is llm."""
    mode_llm = _is_mode_llm(feature_dir)
    if mode_llm is not None and not mode_llm:
        return CheckStatus.PASS, "mode is not llm — L5 preflight sections not required"

    path = feature_dir / _ARCH_PREFLIGHT_MD
    if not path.exists():
        return CheckStatus.FAIL, f"{_ARCH_PREFLIGHT_MD} not found"
    text = path.read_text(encoding="utf-8")

    required_sections = [
        (r"##\s+10\.", "LLM Gateway Configuration"),
        (r"##\s+11\.", "Observability Configuration"),
        (r"##\s+12\.", "Guardrails Configuration"),
        (r"##\s+13\.", "Evaluation Strategy"),
        (r"##\s+14\.", "LLM NFR Validation"),
    ]
    missing = []
    for pattern, name in required_sections:
        if not re.search(pattern, text, re.MULTILINE):
            missing.append(name)

    if missing:
        return CheckStatus.FAIL, f"{_ARCH_PREFLIGHT_MD} missing L5 sections: {', '.join(missing)}"
    return CheckStatus.PASS, f"{_ARCH_PREFLIGHT_MD} has all L5 sections (10-14)"


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def _data_prediction_not_required(feature_dir: Path) -> tuple[CheckStatus, str]:
    """Data features carry no FIRST/Virtue self-prediction (ADR-0001 under
    docs/data/architecture/ADR/): enforcement is artifact completeness, the
    data eval-criteria schema, NFR tag coverage, and the mart-contract gate."""
    return CheckStatus.PASS, (
        "evaluation prediction not required for data features "
        "(docs/data/architecture/ADR/0001-data-features-skip-prediction-gate.md)"
    )


def _build_checks(level: str, marker_type: str | None = None) -> tuple[list[str], list]:
    """Return the artifact list and check functions for a given level.

    L3 is handled by an early no-op return in run_validation() and never reaches
    this function. L4 enforces the 5-artifact governed contract; L5 layers in
    LLM-specific checks on top. `marker_type` swaps the type-specific checks —
    data features skip the evaluation-prediction gate (ADR-0001).
    """
    prediction_check = (
        _data_prediction_not_required if marker_type == "data" else check_plan_eval_prediction
    )
    artifacts = L4_REQUIRED_ARTIFACTS
    if level == "5":
        checks = [
            lambda fd: check_completeness(fd, artifacts),
            check_gherkin_syntax,
            check_nfrs_no_tbd,
            check_nfrs_sections,
            check_eval_criteria,
            prediction_check,
            check_gherkin_nfr_coverage,
            check_llm_nfrs,
            check_l5_eval_criteria,
            check_l5_preflight_sections,
            check_agent_topology_exists,
            check_agent_topology_sections,
        ]
    else:
        # L4 (Spec-Driven Add-On) — full 5-artifact governed contract.
        checks = [
            lambda fd: check_completeness(fd, artifacts),
            check_gherkin_syntax,
            check_nfrs_no_tbd,
            check_nfrs_sections,
            check_eval_criteria,
            prediction_check,
            check_gherkin_nfr_coverage,
        ]
    return artifacts, checks


def _run_feature_checks(feature_dir: Path, checks: list) -> bool:
    """Run all checks on a single feature directory. Returns True if all pass."""
    feature_ok = True
    print(f"features/{feature_dir.name}/")
    for check_fn in checks:
        status, message = check_fn(feature_dir)
        print(f"  {_STATUS_LABEL[status]}  {message}")
        if status is CheckStatus.FAIL:
            feature_ok = False
    print()
    return feature_ok


def _run_extension_checks(target: Path, strict: bool) -> int:
    """Validate all discovered extensions. Silent when no extensions are
    present — preserves today's behavior for projects that don't use them.
    Returns 1 only when strict and at least one extension has issues."""
    from .extensions import discover_extensions, validate_extension

    extensions = discover_extensions(target)
    if not extensions:
        return 0

    print("\ngovkit validate — extensions\n")
    any_fail = False
    for ext in extensions:
        issues = validate_extension(ext, target)
        if not issues:
            print(f"  {PASS}  {ext.id} v{ext.version}")
            continue
        tag = FAIL if strict else WARN
        for msg in issues:
            print(f"  {tag}  {ext.id}: {msg}")
        if strict:
            any_fail = True
    print()
    return 1 if any_fail else 0


def run_validation(target: Path, level: str | None = None, strict: bool = False) -> int:
    """Run all governance checks on the target project. Returns exit code."""
    if not target.exists():
        print(f"Error: target directory '{target}' does not exist.")
        return 1

    marker = read_govkit_marker(target) or {}
    if level is None:
        level = marker.get("level") or "3"

    ext_exit = _run_extension_checks(target, strict)

    # L3 (Foundations) ships agent rules + architecture contracts only — there
    # are no per-feature artifacts to validate. The CI quality-gate is the L3
    # compliance surface (lint, tests, import-linter, optional sonar/snyk).
    if level == "3":
        print(
            "\ngovkit validate — Level 3 (Governed AI Delivery (Foundations))\n"
            "\nLevel 3 ships agent rules and architecture contracts only;\n"
            "there are no per-feature artifacts to check at this level.\n"
            "CI quality-gate is the compliance surface for L3.\n"
        )
        return ext_exit

    features_dir = target / "features"
    if not features_dir.exists():
        print(f"Error: no features/ directory found in '{target}'.")
        return 1

    _, checks = _build_checks(level, (marker.get("options") or {}).get("type"))

    feature_dirs = list_user_features(features_dir)

    if not feature_dirs:
        print("No feature directories found to validate.")
        return ext_exit

    level_labels = {
        "3": "L3 Governed AI Delivery (Foundations)",
        "4": "L4 Spec-Driven Add-On",
        "5": "L5 GenAI Operations",
    }
    level_label = level_labels.get(level, f"L{level}")
    print(f"\ngovkit validate — governance compliance check ({level_label})\n")

    passed = sum(1 for fd in feature_dirs if _run_feature_checks(fd, checks))
    failed = len(feature_dirs) - passed
    print(f"{len(feature_dirs)} feature(s) checked, {passed} passed, {failed} failed")
    feature_exit = 0 if failed == 0 else 1
    return max(feature_exit, ext_exit)
