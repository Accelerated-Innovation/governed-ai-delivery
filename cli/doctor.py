#!/usr/bin/env python3
# Copyright 2026 Accelerated Innovation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
"""govkit doctor — read-only governance fit validator.

PR 4. Loads .govkit/marker.json, builds a RepoProfile, runs checks
D001-D014, emits ValidationFindings, exits non-zero on errors. Designed
to run in CI alongside `govkit validate` (which covers per-feature
compliance; doctor covers governance fit).

Per A9: when --target is omitted, doctor auto-discovers all .govkit/
directories under cwd so monorepos get checked per-app.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

# ---------------------------------------------------------------------------
# Finding model
# ---------------------------------------------------------------------------
from .agent_layout import AGENT_LAYOUTS
from .marker import MARKER_DIRNAME, MARKER_FILENAME, read_govkit_marker

Severity = Literal["error", "warning", "info"]


@dataclass
class ValidationFinding:
    """A single doctor finding. `id` is the check id (e.g. "D001") so users
    can grep, suppress, or cite a specific check."""
    id: str
    severity: Severity
    category: str
    message: str
    suggested_action: str
    file: str | None = None


# Registry of checks. Each entry is (id, callable). Callables take
# (target, marker) and return list[ValidationFinding].
# Populated by subsequent chunks (PR4-B+); the skeleton ships empty so the
# pristine-install test verifies "no checks fire" cleanly.
_CHECKS: list[tuple[str, callable]] = []


def _register_check(check_id: str):
    """Decorator to register a check function.

    Each check takes (target: Path, marker: dict) and returns a list of
    ValidationFinding. Checks must not raise — return empty list on
    indeterminate state.
    """
    def decorator(fn):
        _CHECKS.append((check_id, fn))
        return fn
    return decorator


# ---------------------------------------------------------------------------
# Rule-tree resolution (agent-aware)
# ---------------------------------------------------------------------------


def _parse_frontmatter(text: str) -> dict | None:
    """Extract YAML frontmatter from a markdown file. Returns None if absent."""
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    import yaml
    try:
        return yaml.safe_load(text[3:end])
    except yaml.YAMLError:
        return None


def _iter_rule_files(target: Path, rules_dir: Path) -> list[Path]:
    """Find every rule file at target/<rules_dir>.

    `*.instructions.md` (copilot) is a subset of `*.md`, so glob both then
    dedupe — keeps the helper agent-agnostic.
    """
    full = target / rules_dir
    if not full.is_dir():
        return []
    seen: set[Path] = set()
    out: list[Path] = []
    for p in sorted(full.glob("*.md")) + sorted(full.glob("*.instructions.md")):
        if p in seen:
            continue
        seen.add(p)
        out.append(p)
    return out


def _extract_globs(frontmatter: dict, key: str) -> list[str]:
    """Read the glob list/string from a frontmatter dict.

    `paths:` (claude-code) is a list of strings; `applyTo:` (copilot) is a
    single string (or, less commonly, a list).
    """
    value = frontmatter.get(key)
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [v for v in value if isinstance(v, str)]
    return []


def _glob_resolves_in(target: Path, glob_pattern: str) -> bool:
    """Does `glob_pattern` match at least one path under `target`?

    Patterns from rule files look like `**/adapters/**`. Path.glob handles
    these natively. We accept matches on either files or directories.
    """
    # Normalize: rule globs use `**/x/**` to mean "x as a directory anywhere".
    # Path.glob requires that pattern syntax (also).
    try:
        for _ in target.glob(glob_pattern):
            return True
    except (ValueError, OSError):
        return False
    return False


# ---------------------------------------------------------------------------
# Checks (D001 onward)
# ---------------------------------------------------------------------------


@_register_check("D001")
def _check_rule_globs_resolve(target: Path, marker: dict) -> list[ValidationFinding]:
    """D001 — every glob in installed rule files must match ≥1 path in the repo.

    Agent-aware: claude-code uses `paths:` lists, copilot uses `applyTo:`
    strings, codex skips (no glob frontmatter; placement IS the rule scope).
    """
    agent = marker.get("agent", "claude-code")
    layout = AGENT_LAYOUTS.get(agent)
    if layout is None or layout.frontmatter_glob_key is None:
        return []
    rules_dir = Path(layout.rules_dir)
    key = layout.frontmatter_glob_key

    findings: list[ValidationFinding] = []
    for rule_file in _iter_rule_files(target, rules_dir):
        try:
            text = rule_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        fm = _parse_frontmatter(text)
        if not isinstance(fm, dict):
            continue
        for glob_pattern in _extract_globs(fm, key):
            if _glob_resolves_in(target, glob_pattern):
                continue
            try:
                rel_file = rule_file.relative_to(target)
            except ValueError:
                rel_file = rule_file
            findings.append(ValidationFinding(
                id="D001",
                severity="error",
                category="rule-glob",
                file=str(rel_file).replace("\\", "/"),
                message=f"glob `{glob_pattern}` resolves to 0 files under {target}",
                suggested_action=(
                    f"edit {rel_file} to match a folder that exists in this repo, "
                    "or delete the rule if it doesn't apply"
                ),
            ))
    return findings


@_register_check("D003")
def _check_ci_mismatch(target: Path, marker: dict) -> list[ValidationFinding]:
    """D003 — marker.options.ci disagrees with the CI files actually in the repo.

    Per A7: severity is `warning`, not error. Legitimate repos may have a
    secondary CI alongside the primary (e.g. dependabot.yml in a repo that
    runs builds on Azure Pipelines).
    """
    from .detect import build_profile
    declared = marker.get("options", {}).get("ci")
    if not declared:
        return []
    profile = build_profile(target)
    detected_pair = {"github": "github-actions", "azure": "azure-pipelines"}
    declared_signal = detected_pair.get(declared)
    if declared_signal is None:
        return []
    # Find the other-platform signal present in the repo
    other_signals = [s for s in profile.detected_ci if s != declared_signal]
    if not other_signals:
        return []
    return [ValidationFinding(
        id="D003",
        severity="warning",
        category="ci-mismatch",
        file=None,
        message=(
            f"marker declares ci={declared!r} ({declared_signal}), but this repo "
            f"contains files for: {', '.join(other_signals)}"
        ),
        suggested_action=(
            f"if you intend to use {declared!r}, remove or relocate the "
            f"{other_signals[0]} files; otherwise re-run `govkit apply --ci <platform>` "
            f"with the correct platform"
        ),
    )]


@_register_check("D004")
def _check_ci_ambiguous(target: Path, marker: dict) -> list[ValidationFinding]:
    """D004 — both CI platforms have files present; govkit's gates can't be
    in two places. Symmetrically ambiguous (regardless of marker)."""
    from .detect import build_profile
    profile = build_profile(target)
    if "github-actions" in profile.detected_ci and "azure-pipelines" in profile.detected_ci:
        return [ValidationFinding(
            id="D004",
            severity="warning",
            category="ci-mismatch",
            file=None,
            message=(
                "both `.github/workflows/` and `azure-pipelines.yml` (or .azure/) "
                "exist — govkit's quality gates can't be in two CI systems"
            ),
            suggested_action=(
                "pick one platform and remove the other set, or use the secondary "
                "system for build-only and keep govkit gates on the declared platform"
            ),
        )]
    return []


@_register_check("D005")
def _check_stack_language_mismatch(target: Path, marker: dict) -> list[ValidationFinding]:
    """D005 — marker.stack.id implies a language; detected languages disagree.

    The expected language comes from the bundled overlay's
    skill_context.language (the overlay owns per-stack facts; a guard test
    keeps every bundled overlay declaring one).

    Silent when:
      - marker has no stack block (legacy)
      - stack.id doesn't resolve to a bundled overlay declaring a language
      - no language detected in repo (nothing to disagree with)
      - detected languages include the expected one
    """
    from .overlay import load_overlay

    stack = marker.get("stack")
    if not stack:
        return []
    stack_id = stack.get("id")
    overlay = load_overlay(stack_id) if stack_id else None
    expected_lang = (overlay.skill_context or {}).get("language") if overlay else None
    if not expected_lang:
        return []

    from .detect import build_profile
    profile = build_profile(target)
    if not profile.detected_languages:
        return []
    if expected_lang in profile.detected_languages:
        return []

    return [ValidationFinding(
        id="D005",
        severity="warning",
        category="stack-mismatch",
        file=None,
        message=(
            f"marker stack {stack_id!r} expects {expected_lang!r} but detected "
            f"{', '.join(profile.detected_languages)} in this repo"
        ),
        suggested_action=(
            f"if your repo is {profile.detected_languages[0]}, run "
            f"`govkit stack apply <id>` with the matching stack id "
            "(see `govkit stack list`); otherwise update the repo or accept "
            "the assumption via `govkit calibrate` when it ships"
        ),
    )]


def _scan_baseline_headers(target: Path) -> list[tuple[Path, str, str]]:
    """Find every govkit-managed .md file under target/docs/ and return
    (path, baseline_id, baseline_version) tuples parsed from each header.

    Files without an editable header are skipped — D006 only fires on docs
    that are still govkit-managed.
    """
    from .headers import parse_editable_header
    docs_root = target / "docs"
    if not docs_root.is_dir():
        return []
    out: list[tuple[Path, str, str]] = []
    for md in docs_root.rglob("*.md"):
        try:
            text = md.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        fm = parse_editable_header(text)
        if not fm:
            continue
        baseline = fm.get("baseline", "")
        if "@" not in baseline:
            continue
        ident, _, version = baseline.partition("@")
        out.append((md, ident.strip(), version.strip()))
    return out


@_register_check("D006")
def _check_baseline_staleness(target: Path, marker: dict) -> list[ValidationFinding]:
    """D006 — an installed doc's `baseline: <id>@<version>` header lists a
    version older than the bundled overlay. User should refresh.
    """
    from .overlay import load_overlay

    findings: list[ValidationFinding] = []
    for path, ident, version in _scan_baseline_headers(target):
        # Only check stack-overlay-managed baselines (skip govkit@<ver>
        # baselines which track the govkit version, not an overlay version).
        if ident == "govkit":
            continue
        overlay = load_overlay(ident)
        if overlay is None:
            continue  # the overlay was renamed/removed; not D006's job
        if version == overlay.version:
            continue
        try:
            rel = path.relative_to(target)
        except ValueError:
            rel = path
        findings.append(ValidationFinding(
            id="D006",
            severity="warning",
            category="stack-mismatch",
            file=str(rel).replace("\\", "/"),
            message=(
                f"baseline header is {ident}@{version} but the bundled overlay is "
                f"{ident}@{overlay.version}"
            ),
            suggested_action=(
                f"run `govkit stack apply {ident} --target {target}` to refresh "
                "(edit-protected files will be preserved without --force)"
            ),
        ))
    return findings


# LLM-specific section keywords. Matching any of these in an installed
# architecture doc at level < 5 indicates leakage from L5 content.
_LLM_LEAKAGE_KEYWORDS = (
    "LiteLLM", "LangChain", "LangGraph",
    "DeepEval", "Promptfoo", "RAGAS",
    "NeMo Guardrails", "Guardrails AI",
    "OpenLLMetry", "Langfuse",
)


@_register_check("D007")
def _check_llm_leakage_in_non_l5(target: Path, marker: dict) -> list[ValidationFinding]:
    """D007 — L5-only LLM tooling (LiteLLM, DeepEval, NeMo Guardrails, etc.)
    is named in an installed architecture doc but the install is L<5.
    Indicates the wrong baseline shipped or leakage from L5 templates.
    """
    if marker.get("level") == "5":
        return []
    arch_dir = target / "docs" / "backend" / "architecture"
    if not arch_dir.is_dir():
        return []
    findings: list[ValidationFinding] = []
    for md in sorted(arch_dir.glob("*.md")):
        try:
            text = md.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        hits = [kw for kw in _LLM_LEAKAGE_KEYWORDS if kw in text]
        if not hits:
            continue
        try:
            rel = md.relative_to(target)
        except ValueError:
            rel = md
        findings.append(ValidationFinding(
            id="D007",
            severity="warning",
            category="level-leakage",
            file=str(rel).replace("\\", "/"),
            message=(
                f"L5-only keywords found in non-L5 install ({', '.join(hits)})"
            ),
            suggested_action=(
                "either upgrade to L5 (`govkit apply --level 5`) or remove these "
                "sections from the installed doc"
            ),
        ))
    return findings


@_register_check("D008")
def _check_l5_without_llm_deps(target: Path, marker: dict) -> list[ValidationFinding]:
    """D008 — install is L5 (GenAI Operations) but no LLM SDK appears in
    repo dependencies. Likely a mis-configured level.
    """
    if marker.get("level") != "5":
        return []
    from .detect import build_profile
    profile = build_profile(target)
    if profile.detected_llm_signals:
        return []
    return [ValidationFinding(
        id="D008",
        severity="info",
        category="level-leakage",
        file=None,
        message=(
            "level is 5 (GenAI Operations) but no LLM SDK detected in repo "
            "(checked pyproject.toml / requirements / package.json / pom.xml "
            "for langchain, litellm, openai, anthropic, semantic-kernel, langgraph)"
        ),
        suggested_action=(
            "if this is not actually an LLM service, downgrade with "
            "`govkit apply --level 4`; otherwise add the LLM SDK dependency or "
            "ignore this finding (it is info-only)"
        ),
    )]


_TESTING_FRAMEWORK_KEYWORDS = (
    "pytest", "pytest-bdd",
    "xunit", "nunit", "mstest", "specflow", "reqnroll", "moq", "nsubstitute",
    "junit", "junit5", "mockito", "cucumber",
    "vitest", "jest", "cucumber-js",
    "godog", "testify",
)

_DEP_MANIFESTS = (
    "pyproject.toml", "requirements.txt", "requirements-dev.txt",
    "package.json",
    "pom.xml", "build.gradle", "build.gradle.kts",
    "Directory.Packages.props",
)


def _read_lower(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").lower()
    except (OSError, UnicodeDecodeError):
        return ""


def _collect_dep_text(target: Path) -> str:
    """Concatenate every dep-manifest text we find under target's root."""
    chunks: list[str] = []
    for name in _DEP_MANIFESTS:
        for path in list(target.glob(name)) + list(target.rglob(name)):
            if path.is_file():
                chunks.append(_read_lower(path))
    for csproj in target.rglob("*.csproj"):
        if csproj.is_file():
            chunks.append(_read_lower(csproj))
    return "\n".join(c for c in chunks if c)


@_register_check("D009")
def _check_testing_framework_mismatch(target: Path, marker: dict) -> list[ValidationFinding]:
    """D009 — TESTING.md names a framework that is not present in any
    dep manifest. Helpful for catching stack overlays that don't match
    what the repo actually depends on.

    Silent when:
      - TESTING.md is absent
      - no dep manifest exists at all (nothing to compare against)
      - all named frameworks are present in deps
    """
    testing_md = target / "docs" / "backend" / "architecture" / "TESTING.md"
    if not testing_md.is_file():
        return []
    try:
        testing_text = testing_md.read_text(encoding="utf-8").lower()
    except (OSError, UnicodeDecodeError):
        return []

    dep_text = _collect_dep_text(target)
    if not dep_text.strip():
        return []  # nothing to compare against

    findings: list[ValidationFinding] = []
    for fw in _TESTING_FRAMEWORK_KEYWORDS:
        if fw in testing_text and fw not in dep_text:
            findings.append(ValidationFinding(
                id="D009",
                severity="warning",
                category="testing",
                file="docs/backend/architecture/TESTING.md",
                message=(
                    f"TESTING.md names framework {fw!r} but no dep manifest "
                    "includes it"
                ),
                suggested_action=(
                    f"either add {fw} to your dep manifest, edit TESTING.md to "
                    "match what you actually use, or `govkit stack apply <id>` "
                    "with a stack that matches"
                ),
            ))
    return findings


@_register_check("D010")
def _check_stale_review_required_assumptions(target: Path, marker: dict) -> list[ValidationFinding]:
    """D010 — review_required: true assumptions are still in the marker
    after 30 days without a calibration entry. Reminds the team to run
    `govkit calibrate` (PR 5) — or to manually flip review_required after
    confirming the assumption is correct.
    """
    from datetime import datetime, timedelta, timezone

    applied_at = marker.get("applied_at")
    if not applied_at:
        return []
    try:
        applied_dt = datetime.fromisoformat(applied_at)
    except (ValueError, TypeError):
        return []
    now = datetime.now(timezone.utc)
    if now - applied_dt < timedelta(days=30):
        return []

    findings: list[ValidationFinding] = []
    for assumption in marker.get("assumptions") or []:
        if not assumption.get("review_required"):
            continue
        if assumption.get("calibrated_at"):
            continue
        findings.append(ValidationFinding(
            id="D010",
            severity="warning",
            category="assumption",
            file=None,
            message=(
                f"assumption {assumption.get('id')!r} = "
                f"{assumption.get('value')!r} still marked review_required "
                f"after 30+ days"
            ),
            suggested_action=(
                "run `govkit calibrate` (when it ships) to confirm the "
                "assumption, or set review_required=false directly if the "
                "default is correct for this repo"
            ),
        ))
    return findings


@_register_check("D011")
def _check_marker_references_missing_files(target: Path, marker: dict) -> list[ValidationFinding]:
    """D011 — assumption.files_affected lists a path that no longer exists.

    Indicates the user deleted a govkit-installed file without running
    calibrate or stack-apply, leaving the marker pointing at nothing.
    """
    findings: list[ValidationFinding] = []
    for assumption in marker.get("assumptions") or []:
        for rel_path in assumption.get("files_affected") or []:
            candidate = target / rel_path
            if not candidate.exists():
                findings.append(ValidationFinding(
                    id="D011",
                    severity="error",
                    category="manifest",
                    file=rel_path,
                    message=(
                        f"assumption {assumption.get('id')!r} references "
                        f"{rel_path!r} but that path does not exist in the repo"
                    ),
                    suggested_action=(
                        "either restore the file (`govkit apply` / "
                        "`govkit stack apply`) or remove the assumption from "
                        ".govkit/marker.json"
                    ),
                ))
    return findings


def _classify_extension_message(message: str) -> tuple[str, Severity]:
    """Route a validate_extension message string to (id, severity).

    `cli/extensions.py.validate_extension` returns flat strings; doctor
    translates them into ValidationFindings categorized as D014 (relates_to
    misses, soft) vs D013 (contract-path + structural errors, hard).
    """
    if "relates_to" in message:
        return "D014", "warning"
    return "D013", "error"


@_register_check("D013")
def _check_extension_contracts(target: Path, marker: dict) -> list[ValidationFinding]:
    """D013/D014 — extension manifest issues. Delegates to
    cli/extensions.py's validate_extension() and routes each issue to the
    appropriate finding id by message content.

    Note: registered under D013 but emits both D013 and D014 findings.
    """
    from .extensions import discover_extensions, validate_extension

    findings: list[ValidationFinding] = []
    for ext in discover_extensions(target):
        issues = validate_extension(ext, target)
        for issue in issues:
            check_id, severity = _classify_extension_message(issue)
            findings.append(ValidationFinding(
                id=check_id,
                severity=severity,
                category="extension",
                file=f"extensions/{ext.id}/manifest.yaml",
                message=f"extension {ext.id!r}: {issue}",
                suggested_action=(
                    f"edit extensions/{ext.id}/manifest.yaml or the referenced "
                    "files; see plans/GOVERNANCE_ACCELERATOR_PLAN.md "
                    "(Extensions Compatibility) for the contract"
                ),
            ))
    return findings


# D002 (rule body mentions an absent folder name) is intentionally deferred.
# The body of most rule files contains explanatory text that references
# architecture concepts ("adapters implement outbound port contracts...")
# whether or not the team's repo uses that exact folder name. A naive scan
# produces near-constant warnings; a precise version would need to correlate
# with D001's resolved globs. Revisit once real user feedback indicates a
# false-positive rate worth tuning.


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


def discover_install_targets(cwd: Path) -> list[Path]:
    """Find every .govkit/ directory under `cwd` (A9).

    If `cwd` itself is a govkit install (has .govkit/), returns [cwd] and
    does NOT recurse — apps/ subdirs of a single install don't get
    double-counted.

    Otherwise walks under cwd looking for .govkit/ markers. Skips
    `.git`, `node_modules`, `.venv`, etc. so the walk is bounded.
    """
    cwd_marker = cwd / MARKER_DIRNAME
    if cwd_marker.is_dir() or cwd_marker.is_file():
        return [cwd]

    skip_dirs = {".git", "node_modules", ".venv", "venv", "__pycache__",
                 "dist", "build", "target", "bin", "obj"}
    targets: list[Path] = []
    for marker in cwd.rglob(MARKER_DIRNAME):
        # Skip if any parent in the chain is a skip-dir
        try:
            rel_parts = marker.relative_to(cwd).parts
        except ValueError:
            continue
        if any(p in skip_dirs for p in rel_parts):
            continue
        if not (marker.is_dir() or marker.is_file()):
            continue
        targets.append(marker.parent)
    return sorted(set(targets))


# ---------------------------------------------------------------------------
# Core run loop
# ---------------------------------------------------------------------------


def run_doctor(target: Path) -> list[ValidationFinding]:
    """Run every registered check against `target` and aggregate findings.

    Returns a list of ValidationFinding. Empty if everything is clean.
    Always includes at minimum a marker-missing error if .govkit isn't
    present, so callers know the install can't be validated.
    """
    findings: list[ValidationFinding] = []

    marker = read_govkit_marker(target)
    if marker is None:
        findings.append(ValidationFinding(
            id="D000",
            severity="error",
            category="manifest",
            message="No .govkit/marker.json found at target — nothing to validate.",
            suggested_action="Run `govkit apply` to install governance before running doctor.",
            file=None,
        ))
        return findings

    for check_id, fn in _CHECKS:
        try:
            results = fn(target, marker) or []
        except Exception as e:  # noqa: BLE001
            # A failing check should not break the whole run — report it.
            findings.append(ValidationFinding(
                id=check_id,
                severity="warning",
                category="internal",
                message=f"check {check_id} raised: {e!r}",
                suggested_action="File a govkit issue with the marker contents.",
            ))
            continue
        findings.extend(results)

    return findings


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------


_SEVERITY_RANK = {"error": 0, "warning": 1, "info": 2}


def _print_findings(target: Path, findings: list[ValidationFinding]) -> None:
    """Print a grouped, color-free summary to stdout. Designed for CI logs."""
    by_sev: dict[Severity, list[ValidationFinding]] = {"error": [], "warning": [], "info": []}
    for f in findings:
        by_sev[f.severity].append(f)

    if not findings:
        print(f"  doctor: clean — no findings for {target}")
        return

    for sev in ("error", "warning", "info"):
        bucket = by_sev[sev]  # type: ignore[index]
        if not bucket:
            continue
        print(f"\n  {sev.upper()}S ({len(bucket)}):")
        for f in bucket:
            file_part = f"  {f.file}" if f.file else ""
            print(f"    {f.id}{file_part}")
            print(f"          {f.message}")
            print(f"          fix: {f.suggested_action}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def cmd_doctor(args: argparse.Namespace) -> None:
    """`govkit doctor` — validate governance fit. Exit 1 on errors."""
    target_arg = getattr(args, "target", None)
    if target_arg:
        targets = [Path(target_arg).resolve()]
    else:
        targets = discover_install_targets(Path.cwd())
        if not targets:
            print(
                "Error: no .govkit marker found under the current directory. "
                "Run `govkit apply` first, or pass `--target <path>` to scope "
                "to a specific install.",
                file=sys.stderr,
            )
            sys.exit(1)

    overall_exit = 0
    multi = len(targets) > 1
    for target in targets:
        if multi:
            try:
                rel = target.relative_to(Path.cwd())
            except ValueError:
                rel = target
            print(f"\n=== {rel} ===")
        print(f"  reading {target / MARKER_DIRNAME / MARKER_FILENAME}")
        findings = run_doctor(target)
        _print_findings(target, findings)
        if any(f.severity == "error" for f in findings):
            overall_exit = 1

    if overall_exit == 0:
        # Friendly closer — the pristine-install test asserts on one of these phrases.
        print("\n  doctor: ok — no errors.")
    else:
        print("\n  doctor: errors present (see above).")

    sys.exit(overall_exit)


def register(subparsers) -> None:
    """Register the `doctor` subcommand and its arguments."""
    p = subparsers.add_parser(
        "doctor",
        help="Read-only governance fit validator. Run in CI to surface "
             "mismatches between installed governance and the actual repo.",
    )
    p.add_argument(
        "--target", default=None,
        help="Path to the install root (defaults to scanning cwd for .govkit/ "
             "markers; finds nested installs in monorepos)",
    )
    p.set_defaults(func=cmd_doctor)
