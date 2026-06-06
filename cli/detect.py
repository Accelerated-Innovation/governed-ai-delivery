#!/usr/bin/env python3
# Copyright 2026 Accelerated Innovation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
"""Repo-fit detection.

PR 3. Pure read-only inspection of a target repo to surface signals about
the language, framework, CI platform, testing tools, LLM dependencies, and
architecture style. The output (a `RepoProfile`) is consumed by:

  - `govkit apply`: print detected facts, override the default stack when
    confidence is high, record an `assumption.source="detected"` entry
  - `govkit doctor` (future): cross-check installed governance vs. signals
  - `govkit calibrate` (future): pre-fill the review checklist

Per the plan's A10: `build_profile` always takes an explicit `target: Path`
so monorepos don't cross-contaminate detection.
"""

import fnmatch
import os
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree as ET


# ---------------------------------------------------------------------------
# Signal definitions
# ---------------------------------------------------------------------------

# Filename-based language signals. Each tuple = (language, glob).
_LANG_FILE_SIGNALS: list[tuple[str, str]] = [
    ("csharp", "*.csproj"),
    ("csharp", "*.sln"),
    ("csharp", "global.json"),
    ("csharp", "Directory.Packages.props"),
    ("python", "pyproject.toml"),
    ("python", "setup.py"),
    ("python", "requirements*.txt"),
    ("typescript", "tsconfig.json"),
    ("go", "go.mod"),
    ("java", "pom.xml"),
    ("java", "build.gradle"),
    ("java", "build.gradle.kts"),
]

# LLM SDK / framework markers — substring searches in dep manifests.
_LLM_MARKERS = ("langchain", "litellm", "openai", "anthropic", "semantic-kernel", "langgraph")

# Architecture style markers — folder names (any depth under target).
_HEXAGONAL_FOLDERS = {"ports", "adapters"}
_LAYERED_FOLDERS = {"Controllers", "Services", "Repositories"}
_CLEAN_FOLDERS = {"Application", "Domain", "Infrastructure", "Presentation"}
_DBT_FOLDERS = {"staging", "intermediate", "marts"}


# ---------------------------------------------------------------------------
# RepoProfile
# ---------------------------------------------------------------------------

@dataclass
class RepoProfile:
    target: Path
    detected_languages: list[str] = field(default_factory=list)
    detected_frameworks: list[str] = field(default_factory=list)
    detected_ci: list[str] = field(default_factory=list)
    detected_test_packages: list[str] = field(default_factory=list)
    detected_project_paths: list[Path] = field(default_factory=list)
    detected_api_style: str | None = None
    detected_llm_signals: list[str] = field(default_factory=list)
    detected_architecture_signals: list[str] = field(default_factory=list)
    # Internal: how many signals matched per language (drives confidence).
    _language_signal_counts: dict[str, int] = field(default_factory=dict)

    def language_confidence(self, language: str) -> str:
        """Report confidence in a detected language.

        - "high": ≥2 distinct signals matched (e.g. *.csproj + global.json)
        - "medium": exactly 1 signal matched
        - "none": no signals (language not in detected_languages)
        """
        count = self._language_signal_counts.get(language, 0)
        if count >= 2:
            return "high"
        if count == 1:
            return "medium"
        return "none"


# ---------------------------------------------------------------------------
# File-scan helpers
# ---------------------------------------------------------------------------

def _find_one(target: Path, pattern: str) -> list[Path]:
    """Find files matching pattern at the target root only (not recursive).

    Some signals (global.json, pyproject.toml, tsconfig.json) are conventionally
    at the repo root; others (*.csproj, *.sln) may live in subdirs. The caller
    chooses the right helper.
    """
    try:
        return [p for p in target.glob(pattern) if p.is_file()]
    except OSError:
        return []


_SKIP_DIRS = frozenset({
    ".git", "node_modules", ".venv", "venv", "__pycache__", "dist",
    "build", "target", "bin", "obj", ".tox", ".pytest_cache",
})


def _find_recursive(target: Path, pattern: str, max_depth: int = 4) -> list[Path]:
    """Recursive search bounded by depth, pruning noise dirs during traversal.

    Uses os.walk with in-place `dirnames[:]` mutation so node_modules / .venv /
    etc. are never entered — important for large repos where rglob's
    walk-then-filter approach dominated build_profile() runtime.

    Depth is counted as path segments from target: a file at target/a/b/c.txt
    is depth 3. With max_depth=4, files up to four segments deep are returned.
    """
    matches: list[Path] = []
    if not target.is_dir():
        return matches
    target_depth = len(target.parts)
    try:
        for dirpath, dirnames, filenames in os.walk(target):
            # Prune noise dirs in place — os.walk respects this and won't recurse.
            dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
            current = Path(dirpath)
            depth = len(current.parts) - target_depth  # 0 at target, +1 per descent
            if depth + 1 > max_depth:
                # Files here would be at file_depth > max_depth; bail without descent.
                dirnames[:] = []
                continue
            for fname in filenames:
                if fnmatch.fnmatch(fname, pattern):
                    matches.append(current / fname)
            if depth + 1 >= max_depth:
                # Next level's files would exceed max_depth; stop descent.
                dirnames[:] = []
    except OSError:
        pass
    return matches


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------

def _detect_languages(target: Path, prof: RepoProfile) -> None:
    counts: dict[str, int] = {}
    paths: list[Path] = []
    for language, pattern in _LANG_FILE_SIGNALS:
        # Conventional root-level files: glob at target root.
        # Project files (*.csproj, *.sln) may live under subdirs.
        if any(c in pattern for c in "*?"):
            matches = _find_recursive(target, pattern)
        else:
            matches = _find_one(target, pattern)
        if matches:
            counts[language] = counts.get(language, 0) + 1
            paths.extend(matches)

    # Special case: typescript also detected when package.json declares
    # typescript in deps/devDeps.
    pkg_json = target / "package.json"
    if pkg_json.is_file():
        text = _read_text(pkg_json)
        if "typescript" in text:
            counts["typescript"] = counts.get("typescript", 0) + 1
            paths.append(pkg_json)

    prof._language_signal_counts = counts
    prof.detected_languages = sorted(counts.keys())
    prof.detected_project_paths = sorted(set(paths))


# ---------------------------------------------------------------------------
# Framework detection (refines language)
# ---------------------------------------------------------------------------

def _csproj_indicates_aspnet_core(csproj_path: Path) -> bool:
    """Robust XML parsing per R3 — checks Project.Sdk and FrameworkReference
    rather than substring-matching package names (which would false-positive
    on `Microsoft.AspNetCore.AuthenticationCore` etc.)."""
    try:
        tree = ET.parse(csproj_path)
    except (ET.ParseError, OSError):
        return False
    root = tree.getroot()
    sdk = root.attrib.get("Sdk", "")
    if sdk == "Microsoft.NET.Sdk.Web":
        return True
    # Look for <FrameworkReference Include="Microsoft.AspNetCore.App" />
    for fr in root.iter("FrameworkReference"):
        if fr.attrib.get("Include") == "Microsoft.AspNetCore.App":
            return True
    return False


def _detect_aspnet_core(target: Path) -> bool:
    for csproj in _find_recursive(target, "*.csproj"):
        if _csproj_indicates_aspnet_core(csproj):
            return True
    return False


def _detect_fastapi(target: Path) -> bool:
    """Substring search across pyproject.toml + requirements*.txt."""
    py_files = _find_recursive(target, "pyproject.toml") + _find_recursive(target, "requirements*.txt")
    for path in py_files:
        text = _read_text(path)
        if "fastapi" in text.lower():
            return True
    return False


def _detect_fastify(target: Path) -> bool:
    """Check package.json dependencies / devDependencies for 'fastify'."""
    pkg = target / "package.json"
    if not pkg.is_file():
        return False
    text = _read_text(pkg)
    return '"fastify"' in text


def _detect_spring_boot(target: Path) -> bool:
    """Substring search across pom.xml and build.gradle*."""
    candidates = (
        _find_recursive(target, "pom.xml")
        + _find_recursive(target, "build.gradle")
        + _find_recursive(target, "build.gradle.kts")
    )
    for path in candidates:
        text = _read_text(path)
        if "spring-boot" in text or "springframework.boot" in text:
            return True
    return False


def _detect_gin(target: Path) -> bool:
    """Check go.mod content for the Gin import path."""
    go_mod = target / "go.mod"
    if not go_mod.is_file():
        return False
    return "github.com/gin-gonic/gin" in _read_text(go_mod)


def _detect_dbt(target: Path) -> bool:
    """Presence of dbt_project.yml at any depth indicates a dbt project."""
    return bool(_find_recursive(target, "dbt_project.yml"))


def _detect_databricks_lakehouse(target: Path) -> bool:
    """Presence of Databricks Asset Bundle config indicates a Databricks repo."""
    return bool(_find_recursive(target, "databricks.yml") or _find_recursive(target, "databricks.yaml"))


def _detect_frameworks(target: Path, prof: RepoProfile) -> None:
    """Detect frameworks from manifest contents directly. We don't gate on
    language detection because framework presence is the more specific
    signal — if package.json has fastify, that's fastify regardless of
    whether tsconfig.json exists.
    """
    detected: list[str] = []
    if _detect_aspnet_core(target):
        detected.append("aspnet-core")
    if _detect_fastapi(target):
        detected.append("fastapi")
    if _detect_fastify(target):
        detected.append("fastify")
    if _detect_spring_boot(target):
        detected.append("spring-boot")
    if _detect_gin(target):
        detected.append("gin")
    if _detect_dbt(target):
        detected.append("dbt")
    # dbt-on-Databricks remains a dbt project shape by default. Users can still
    # opt into the native Databricks overlay with --stack databricks-lakehouse.
    if _detect_databricks_lakehouse(target):
        detected.append("databricks-lakehouse")
    prof.detected_frameworks = detected


# ---------------------------------------------------------------------------
# CI detection
# ---------------------------------------------------------------------------

def _detect_ci(target: Path, prof: RepoProfile) -> None:
    detected: list[str] = []
    gh_workflows = target / ".github" / "workflows"
    if gh_workflows.is_dir() and (
        any(gh_workflows.glob("*.yml")) or any(gh_workflows.glob("*.yaml"))
    ):
        detected.append("github-actions")
    # azure-pipelines.yml at root, or .azure/ dir, or pipelines/*.yml at root.
    pipelines_dir = target / "pipelines"
    if (
        (target / "azure-pipelines.yml").is_file()
        or (target / ".azure").is_dir()
        or (pipelines_dir.is_dir() and any(pipelines_dir.glob("*.yml")))
    ):
        detected.append("azure-pipelines")
    prof.detected_ci = detected


# ---------------------------------------------------------------------------
# Architecture signals
# ---------------------------------------------------------------------------

def _top_level_folder_names(target: Path) -> set[str]:
    """Collect the immediate-child folder names under each known source root
    (target, src/, Source/, models/). dbt's layers live under models/; the
    others live at target root or src/.
    """
    names: set[str] = set()
    for root in (target, target / "src", target / "Source", target / "models"):
        if not root.is_dir():
            continue
        try:
            for entry in root.iterdir():
                if entry.is_dir() and not entry.name.startswith("."):
                    names.add(entry.name)
        except OSError:
            continue
    return names


def _detect_architecture(target: Path, prof: RepoProfile) -> None:
    """Match top-level folder names against known style fingerprints."""
    folders = _top_level_folder_names(target)
    signals: list[str] = []
    if _HEXAGONAL_FOLDERS.issubset(folders) or len(_HEXAGONAL_FOLDERS & folders) >= 2:
        signals.append("hexagonal-shape")
    if len(_LAYERED_FOLDERS & folders) >= 2:
        signals.append("layered-shape")
    if len(_CLEAN_FOLDERS & folders) >= 2:
        signals.append("clean-shape")
    if len(_DBT_FOLDERS & folders) >= 2:
        signals.append("dbt-shape")
    prof.detected_architecture_signals = signals


# ---------------------------------------------------------------------------
# LLM signals
# ---------------------------------------------------------------------------

def _detect_llm_signals(target: Path, prof: RepoProfile) -> None:
    candidates = (
        _find_recursive(target, "pyproject.toml")
        + _find_recursive(target, "requirements*.txt")
        + ([target / "package.json"] if (target / "package.json").is_file() else [])
        + _find_recursive(target, "pom.xml")
    )
    found: list[str] = []
    for path in candidates:
        text = _read_text(path).lower()
        for marker in _LLM_MARKERS:
            if marker in text and marker not in found:
                found.append(marker)
    prof.detected_llm_signals = found


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Stack inference
# ---------------------------------------------------------------------------

# Framework → stack id. A high-confidence framework match overrides
# language-only inference because frameworks are the more specific signal.
_FRAMEWORK_TO_STACK = {
    "aspnet-core":  "dotnet-aspnet",
    "fastapi":      "python-fastapi",
    "fastify":      "nodejs-fastify",
    "spring-boot":  "java-spring-boot",
    "gin":          "go-gin",
    "databricks-lakehouse": "databricks-lakehouse",
    "dbt":          "python-dbt",
}

# Language → default stack id for that language. Used when no framework is
# detected but the language is clear.
_LANGUAGE_TO_STACK = {
    "csharp":     "dotnet-aspnet",
    "python":     "python-fastapi",
    "typescript": "nodejs-fastify",
    "java":       "java-spring-boot",
    "go":         "go-gin",
}


def infer_stack(profile: RepoProfile) -> tuple[str | None, str]:
    """Pick the best bundled stack for `profile`.

    Returns (stack_id, confidence). confidence is one of "high" (framework
    matched), "medium" (language matched, no framework), "low" (language
    matched with weak signals), "none" (no usable signals).

    Framework signals outrank language signals — if a repo has both Python
    indicators (pyproject) and .NET indicators (csproj + aspnet-core), the
    framework-specific match (dotnet-aspnet) wins.
    """
    # Framework match → high confidence
    for framework in profile.detected_frameworks:
        stack_id = _FRAMEWORK_TO_STACK.get(framework)
        if stack_id is not None:
            return stack_id, "high"

    # Language match → medium/low confidence based on language confidence
    if profile.detected_languages:
        # Prefer the language with highest confidence.
        ranked = sorted(
            profile.detected_languages,
            key=lambda lang: (
                {"high": 3, "medium": 2, "low": 1, "none": 0}[profile.language_confidence(lang)],
                lang,
            ),
            reverse=True,
        )
        for lang in ranked:
            stack_id = _LANGUAGE_TO_STACK.get(lang)
            if stack_id is not None:
                lang_conf = profile.language_confidence(lang)
                # Without a framework match, downgrade one level.
                if lang_conf == "high":
                    return stack_id, "medium"
                return stack_id, "low"

    return None, "none"


def build_profile(target: Path) -> RepoProfile:
    """Inspect `target` and return a RepoProfile of detected signals.

    Pure read-only. Never raises on filesystem issues — returns an empty
    profile if `target` is unreadable so callers can degrade gracefully.

    The detector is scoped strictly to `target` so monorepos don't
    cross-contaminate (per A10).
    """
    prof = RepoProfile(target=target)
    if not target.is_dir():
        return prof

    _detect_languages(target, prof)
    _detect_frameworks(target, prof)
    _detect_ci(target, prof)
    _detect_architecture(target, prof)
    _detect_llm_signals(target, prof)
    return prof
