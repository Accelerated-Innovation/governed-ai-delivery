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

Uses only the Python standard library. Full JSON Schema validation of
eval_criteria.yaml is deferred to CI or `check-jsonschema` if installed.
"""

import json
import re
import subprocess
from pathlib import Path


# ---------------------------------------------------------------------------
# Artifact file name constants
# ---------------------------------------------------------------------------

_ACCEPTANCE_FEATURE = "acceptance.feature"
_NFRS_MD = "nfrs.md"
_PLAN_MD = "plan.md"
_EVAL_CRITERIA_YAML = "eval_criteria.yaml"
_ARCH_PREFLIGHT_MD = "architecture_preflight.md"

_RE_MODE_LLM = r"^mode:\s*llm"

L3_REQUIRED_ARTIFACTS = [
    _ACCEPTANCE_FEATURE,
    _NFRS_MD,
    _PLAN_MD,
]

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

STARTERS = {
    "starter_backend", "starter_ui", "starter_cli",
    "starter_backend_l3", "starter_ui_l3", "starter_cli_l3",
    "starter_backend_l5", "starter_cli_l5",
}


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def check_completeness(feature_dir: Path, artifacts: list[str] | None = None) -> tuple[bool, str]:
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
        return False, f"{present}/{len(artifacts)} artifacts — {'; '.join(parts)}"
    return True, f"{len(artifacts)}/{len(artifacts)} required artifacts present"


def check_gherkin_syntax(feature_dir: Path) -> tuple[bool, str]:
    """Basic Gherkin structure validation using text matching."""
    path = feature_dir / _ACCEPTANCE_FEATURE
    if not path.exists():
        return False, f"{_ACCEPTANCE_FEATURE} not found"
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
        return False, f"{_ACCEPTANCE_FEATURE}: {'; '.join(issues)}"
    return True, f"{_ACCEPTANCE_FEATURE} has valid Gherkin structure"


def check_nfrs_no_tbd(feature_dir: Path) -> tuple[bool, str]:
    """Check that nfrs.md has no remaining TBD entries."""
    path = feature_dir / _NFRS_MD
    if not path.exists():
        return False, f"{_NFRS_MD} not found"
    lines = path.read_text(encoding="utf-8").splitlines()
    tbd_lines = [i + 1 for i, ln in enumerate(lines) if re.search(r"\bTBD\b", ln)]
    if tbd_lines:
        return False, f"{_NFRS_MD} contains TBD entries (lines {', '.join(map(str, tbd_lines))})"
    return True, f"{_NFRS_MD} has no TBD entries"


def check_eval_criteria(feature_dir: Path) -> tuple[bool | None, str]:
    """Check eval_criteria.yaml for required keys. Full schema validation via check-jsonschema if available."""
    path = feature_dir / _EVAL_CRITERIA_YAML
    if not path.exists():
        return False, f"{_EVAL_CRITERIA_YAML} not found"
    text = path.read_text(encoding="utf-8")
    issues = []
    if not re.search(r"^version:", text, re.MULTILINE):
        issues.append("missing 'version' key")
    if not re.search(r"^mode:", text, re.MULTILINE):
        issues.append("missing 'mode' key")
    if issues:
        return False, f"{_EVAL_CRITERIA_YAML}: {'; '.join(issues)}"

    try:
        result = subprocess.run(
            ["check-jsonschema", "--check-metaschema", str(path)],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return None, f"{_EVAL_CRITERIA_YAML} structure OK — full schema validation requires CI"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None, f"{_EVAL_CRITERIA_YAML} structure OK — install check-jsonschema for full validation"
    return True, f"{_EVAL_CRITERIA_YAML} is valid"


def check_plan_eval_prediction(feature_dir: Path) -> tuple[bool, str]:
    """Check that plan.md has an evaluation_prediction block with averages >= 4.0."""
    path = feature_dir / _PLAN_MD
    if not path.exists():
        return False, f"{_PLAN_MD} not found"
    text = path.read_text(encoding="utf-8")

    block_match = re.search(
        r"```ya?ml\s*\n(.*?evaluation_prediction:.*?)```",
        text, re.DOTALL,
    )
    if not block_match:
        return False, f"{_PLAN_MD} missing evaluation_prediction block"

    block = block_match.group(1)

    null_matches = re.findall(r":\s*null\b", block)
    if null_matches:
        return False, f"{_PLAN_MD} evaluation_prediction has {len(null_matches)} null value(s) — all must be populated"

    averages = re.findall(r"average:\s*([\d.]+)", block)
    if not averages:
        return False, f"{_PLAN_MD} evaluation_prediction missing average values"

    below_threshold = []
    for avg_str in averages:
        avg = float(avg_str)
        if avg < 4.0:
            below_threshold.append(avg_str)

    if below_threshold:
        return False, f"{_PLAN_MD} evaluation_prediction average(s) below 4.0: {', '.join(below_threshold)}"
    return True, f"{_PLAN_MD} evaluation_prediction averages OK ({', '.join(averages)})"


def check_gherkin_nfr_coverage(feature_dir: Path) -> tuple[bool, str]:
    """Cross-reference populated NFR categories vs @nfr-* tags in acceptance.feature."""
    nfrs_path = feature_dir / _NFRS_MD
    feature_path = feature_dir / _ACCEPTANCE_FEATURE
    if not nfrs_path.exists() or not feature_path.exists():
        return False, f"cannot check NFR coverage — missing {_NFRS_MD} or {_ACCEPTANCE_FEATURE}"

    nfrs_text = nfrs_path.read_text(encoding="utf-8")
    feature_text = feature_path.read_text(encoding="utf-8")

    populated = []
    current_heading = None
    for line in nfrs_text.splitlines():
        heading_match = re.match(r"^##\s+(.+)", line)
        if heading_match:
            current_heading = heading_match.group(1).strip().lower()
            continue
        if current_heading and line.strip().startswith("- ") and "TBD" not in line:
            populated.append(current_heading)
            current_heading = None

    if not populated:
        return True, "no populated NFR categories — tag coverage not required"

    tags_found = set(re.findall(r"@nfr-(\w+)", feature_text))

    category_to_tag = {
        "performance": "performance",
        "availability": "availability",
        "security": "security",
        "compliance": "compliance",
        "scalability": "scalability",
        "observability": "observability",
        "reliability": "reliability",
        "compatibility": "compatibility",
    }

    missing_tags = []
    for category in populated:
        if category not in category_to_tag:
            continue
        expected_tag = category_to_tag[category]
        if expected_tag not in tags_found:
            missing_tags.append(f"@nfr-{expected_tag}")

    if missing_tags:
        return False, f"Gherkin missing NFR tags: {', '.join(missing_tags)}"
    return True, "Gherkin @nfr-* tag coverage matches populated NFR categories"


# ---------------------------------------------------------------------------
# L5-specific checks
# ---------------------------------------------------------------------------

LLM_NFR_CATEGORIES = {"llm latency", "llm cost", "llm fallback", "llm safety"}


def _is_mode_llm(feature_dir: Path) -> bool | None:
    """Check if eval_criteria.yaml exists and has mode: llm. Returns None if file missing."""
    eval_path = feature_dir / _EVAL_CRITERIA_YAML
    if not eval_path.exists():
        return None
    text = eval_path.read_text(encoding="utf-8")
    return bool(re.search(_RE_MODE_LLM, text, re.MULTILINE))


def check_llm_nfrs(feature_dir: Path) -> tuple[bool, str]:
    """Check that nfrs.md has populated LLM-specific NFR categories when mode is llm."""
    mode_llm = _is_mode_llm(feature_dir)
    if mode_llm is None:
        return False, f"{_EVAL_CRITERIA_YAML} not found — cannot check LLM NFRs"
    if not mode_llm:
        return True, "mode is not llm — LLM NFR check not applicable"

    nfrs_path = feature_dir / _NFRS_MD
    if not nfrs_path.exists():
        return False, f"{_NFRS_MD} not found"
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
        return False, f"LLM NFR categories incomplete: {', '.join(missing)}"
    return True, "LLM NFR categories populated (latency, cost, fallback, safety)"


def check_l5_eval_criteria(feature_dir: Path) -> tuple[bool, str]:
    """Check that eval_criteria.yaml has deepeval_* or promptfoo_* eval_class when mode is llm."""
    mode_llm = _is_mode_llm(feature_dir)
    if mode_llm is None:
        return False, f"{_EVAL_CRITERIA_YAML} not found"
    if not mode_llm:
        return True, "mode is not llm — L5 eval criteria check not applicable"

    text = (feature_dir / _EVAL_CRITERIA_YAML).read_text(encoding="utf-8")
    has_deepeval = bool(re.search(r"eval_class:\s*deepeval_", text))
    has_promptfoo = bool(re.search(r"eval_class:\s*promptfoo_", text))
    if not has_deepeval and not has_promptfoo:
        return False, f"{_EVAL_CRITERIA_YAML} mode is llm but has no deepeval_* or promptfoo_* eval_class"
    tools = []
    if has_deepeval:
        tools.append("deepeval")
    if has_promptfoo:
        tools.append("promptfoo")
    return True, f"L5 eval criteria present ({', '.join(tools)})"


def check_l5_preflight_sections(feature_dir: Path) -> tuple[bool, str]:
    """Check that architecture_preflight.md has L5 sections (10-14) when mode is llm."""
    mode_llm = _is_mode_llm(feature_dir)
    if mode_llm is not None and not mode_llm:
        return True, "mode is not llm — L5 preflight sections not required"

    path = feature_dir / _ARCH_PREFLIGHT_MD
    if not path.exists():
        return False, f"{_ARCH_PREFLIGHT_MD} not found"
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
        return False, f"{_ARCH_PREFLIGHT_MD} missing L5 sections: {', '.join(missing)}"
    return True, f"{_ARCH_PREFLIGHT_MD} has all L5 sections (10-14)"


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def _read_govkit_level(target: Path) -> str | None:
    """Read the maturity level from the .govkit marker file."""
    marker = target / ".govkit"
    if not marker.exists():
        return None
    try:
        data = json.loads(marker.read_text(encoding="utf-8"))
        return data.get("level")
    except (json.JSONDecodeError, OSError):
        return None


def _build_checks(level: str) -> tuple[list[str], list]:
    """Return the artifact list and check functions for a given level."""
    if level == "3":
        artifacts = L3_REQUIRED_ARTIFACTS
        checks = [
            lambda fd: check_completeness(fd, artifacts),
            check_gherkin_syntax,
            check_nfrs_no_tbd,
            check_gherkin_nfr_coverage,
        ]
    elif level == "5":
        artifacts = L4_REQUIRED_ARTIFACTS
        checks = [
            lambda fd: check_completeness(fd, artifacts),
            check_gherkin_syntax,
            check_nfrs_no_tbd,
            check_eval_criteria,
            check_plan_eval_prediction,
            check_gherkin_nfr_coverage,
            check_llm_nfrs,
            check_l5_eval_criteria,
            check_l5_preflight_sections,
        ]
    else:
        artifacts = L4_REQUIRED_ARTIFACTS
        checks = [
            lambda fd: check_completeness(fd, artifacts),
            check_gherkin_syntax,
            check_nfrs_no_tbd,
            check_eval_criteria,
            check_plan_eval_prediction,
            check_gherkin_nfr_coverage,
        ]
    return artifacts, checks


def _run_feature_checks(feature_dir: Path, checks: list) -> bool:
    """Run all checks on a single feature directory. Returns True if all pass."""
    feature_ok = True
    print(f"features/{feature_dir.name}/")
    for check_fn in checks:
        result, message = check_fn(feature_dir)
        if result is True:
            print(f"  {PASS}  {message}")
        elif result is False:
            print(f"  {FAIL}  {message}")
            feature_ok = False
        else:
            print(f"  {WARN}  {message}")
    print()
    return feature_ok


def run_validation(target: Path, level: str | None = None) -> int:
    """Run all governance checks on the target project. Returns exit code."""
    if not target.exists():
        print(f"Error: target directory '{target}' does not exist.")
        return 1

    features_dir = target / "features"
    if not features_dir.exists():
        print(f"Error: no features/ directory found in '{target}'.")
        return 1

    if level is None:
        level = _read_govkit_level(target) or "4"

    _, checks = _build_checks(level)

    feature_dirs = sorted(
        d for d in features_dir.iterdir()
        if d.is_dir() and d.name not in STARTERS and not d.name.startswith(".")
    )

    if not feature_dirs:
        print("No feature directories found to validate.")
        return 0

    level_labels = {"3": "L3 Spec-Driven", "4": "L4 Governed AI Delivery", "5": "L5 GenAI Operations"}
    level_label = level_labels.get(level, f"L{level}")
    print(f"\ngovkit validate — governance compliance check ({level_label})\n")

    passed = sum(1 for fd in feature_dirs if _run_feature_checks(fd, checks))
    failed = len(feature_dirs) - passed
    print(f"{len(feature_dirs)} feature(s) checked, {passed} passed, {failed} failed")
    return 0 if failed == 0 else 1
