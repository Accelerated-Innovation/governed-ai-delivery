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


L3_REQUIRED_ARTIFACTS = [
    "acceptance.feature",
    "nfrs.md",
    "plan.md",
]

L4_REQUIRED_ARTIFACTS = [
    "acceptance.feature",
    "nfrs.md",
    "eval_criteria.yaml",
    "architecture_preflight.md",
    "plan.md",
]

# Default for backward compatibility
REQUIRED_ARTIFACTS = L4_REQUIRED_ARTIFACTS

PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"
WARN = "\033[33mWARN\033[0m"

STARTERS = {
    "starter_backend", "starter_ui", "starter_cli",
    "starter_backend_l3", "starter_ui_l3", "starter_cli_l3",
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
    path = feature_dir / "acceptance.feature"
    if not path.exists():
        return False, "acceptance.feature not found"
    text = path.read_text(encoding="utf-8")
    issues = []
    if not re.search(r"^Feature:", text, re.MULTILINE):
        issues.append("missing 'Feature:' keyword")
    if not re.search(r"^\s*Scenario:", text, re.MULTILINE):
        issues.append("no 'Scenario:' found")
    # Check for at least one Given/When/Then (ignoring comments)
    active_lines = [ln for ln in text.splitlines() if not ln.strip().startswith("#")]
    active_text = "\n".join(active_lines)
    if not re.search(r"^\s*(Given|When|Then)", active_text, re.MULTILINE):
        issues.append("no Given/When/Then steps found")
    if issues:
        return False, f"acceptance.feature: {'; '.join(issues)}"
    return True, "acceptance.feature has valid Gherkin structure"


def check_nfrs_no_tbd(feature_dir: Path) -> tuple[bool, str]:
    """Check that nfrs.md has no remaining TBD entries."""
    path = feature_dir / "nfrs.md"
    if not path.exists():
        return False, "nfrs.md not found"
    lines = path.read_text(encoding="utf-8").splitlines()
    tbd_lines = [i + 1 for i, ln in enumerate(lines) if re.search(r"\bTBD\b", ln)]
    if tbd_lines:
        return False, f"nfrs.md contains TBD entries (lines {', '.join(map(str, tbd_lines))})"
    return True, "nfrs.md has no TBD entries"


def check_eval_criteria(feature_dir: Path) -> tuple[bool | None, str]:
    """Check eval_criteria.yaml for required keys. Full schema validation via check-jsonschema if available."""
    path = feature_dir / "eval_criteria.yaml"
    if not path.exists():
        return False, "eval_criteria.yaml not found"
    text = path.read_text(encoding="utf-8")
    issues = []
    if not re.search(r"^version:", text, re.MULTILINE):
        issues.append("missing 'version' key")
    if not re.search(r"^mode:", text, re.MULTILINE):
        issues.append("missing 'mode' key")
    if issues:
        return False, f"eval_criteria.yaml: {'; '.join(issues)}"

    # Try full schema validation if check-jsonschema is installed
    try:
        result = subprocess.run(
            ["check-jsonschema", "--check-metaschema", str(path)],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return None, "eval_criteria.yaml structure OK — full schema validation requires CI"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None, "eval_criteria.yaml structure OK — install check-jsonschema for full validation"
    return True, "eval_criteria.yaml is valid"


def check_plan_eval_prediction(feature_dir: Path) -> tuple[bool, str]:
    """Check that plan.md has an evaluation_prediction block with averages >= 4.0."""
    path = feature_dir / "plan.md"
    if not path.exists():
        return False, "plan.md not found"
    text = path.read_text(encoding="utf-8")

    # Find the evaluation_prediction YAML block between triple backticks
    block_match = re.search(
        r"```ya?ml\s*\n(.*?evaluation_prediction:.*?)```",
        text, re.DOTALL,
    )
    if not block_match:
        return False, "plan.md missing evaluation_prediction block"

    block = block_match.group(1)

    # Check for null values
    null_matches = re.findall(r":\s*null\b", block)
    if null_matches:
        return False, f"plan.md evaluation_prediction has {len(null_matches)} null value(s) — all must be populated"

    # Extract average values
    averages = re.findall(r"average:\s*([\d.]+)", block)
    if not averages:
        return False, "plan.md evaluation_prediction missing average values"

    below_threshold = []
    for avg_str in averages:
        avg = float(avg_str)
        if avg < 4.0:
            below_threshold.append(avg_str)

    if below_threshold:
        return False, f"plan.md evaluation_prediction average(s) below 4.0: {', '.join(below_threshold)}"
    return True, f"plan.md evaluation_prediction averages OK ({', '.join(averages)})"


def check_gherkin_nfr_coverage(feature_dir: Path) -> tuple[bool, str]:
    """Cross-reference populated NFR categories vs @nfr-* tags in acceptance.feature."""
    nfrs_path = feature_dir / "nfrs.md"
    feature_path = feature_dir / "acceptance.feature"
    if not nfrs_path.exists() or not feature_path.exists():
        return False, "cannot check NFR coverage — missing nfrs.md or acceptance.feature"

    nfrs_text = nfrs_path.read_text(encoding="utf-8")
    feature_text = feature_path.read_text(encoding="utf-8")

    # Find populated NFR categories (heading followed by non-TBD content)
    populated = []
    current_heading = None
    for line in nfrs_text.splitlines():
        heading_match = re.match(r"^##\s+(.+)", line)
        if heading_match:
            current_heading = heading_match.group(1).strip().lower()
            continue
        if current_heading and line.strip().startswith("- ") and "TBD" not in line:
            populated.append(current_heading)
            current_heading = None  # only need one non-TBD line per category

    if not populated:
        return True, "no populated NFR categories — tag coverage not required"

    # Find @nfr-* tags in acceptance.feature
    tags_found = set(re.findall(r"@nfr-(\w+)", feature_text))

    # Map NFR category names to expected tag suffixes
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
        expected_tag = category_to_tag.get(category, category)
        if expected_tag not in tags_found:
            missing_tags.append(f"@nfr-{expected_tag}")

    if missing_tags:
        return False, f"Gherkin missing NFR tags: {', '.join(missing_tags)}"
    return True, "Gherkin @nfr-* tag coverage matches populated NFR categories"


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


def run_validation(target: Path, level: str | None = None) -> int:
    """Run all governance checks on the target project. Returns exit code."""
    if not target.exists():
        print(f"Error: target directory '{target}' does not exist.")
        return 1

    features_dir = target / "features"
    if not features_dir.exists():
        print(f"Error: no features/ directory found in '{target}'.")
        return 1

    # Determine effective level
    if level is None:
        level = _read_govkit_level(target) or "4"

    # Select artifact list and checks based on level
    if level == "3":
        artifacts = L3_REQUIRED_ARTIFACTS
        checks = [
            lambda fd: check_completeness(fd, artifacts),
            check_gherkin_syntax,
            check_nfrs_no_tbd,
            check_gherkin_nfr_coverage,
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

    # Collect feature directories (skip starters and non-directories)
    feature_dirs = sorted(
        d for d in features_dir.iterdir()
        if d.is_dir() and d.name not in STARTERS and not d.name.startswith(".")
    )

    if not feature_dirs:
        print("No feature directories found to validate.")
        return 0

    level_label = "L3 Spec-Driven" if level == "3" else "L4 Governed AI Delivery"
    print(f"\ngovkit validate — governance compliance check ({level_label})\n")

    total = 0
    passed = 0

    for feature_dir in feature_dirs:
        total += 1
        feature_ok = True
        print(f"features/{feature_dir.name}/")

        for check_fn in checks:
            result, message = check_fn(feature_dir)
            if result is True:
                print(f"  {PASS}  {message}")
            elif result is False:
                print(f"  {FAIL}  {message}")
                feature_ok = False
            else:  # None = warning
                print(f"  {WARN}  {message}")

        print()
        if feature_ok:
            passed += 1

    failed = total - passed
    print(f"{total} feature(s) checked, {passed} passed, {failed} failed")
    return 0 if failed == 0 else 1
