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
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree as ET

from .fs import read_text_or_none
from .headers import GOVKIT_BLOCK_BEGIN, GOVKIT_BLOCK_END

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
# Substrings that mark an LLM dependency, matched case-insensitively against
# the text of a dependency file. Chosen to cover each ecosystem's spelling of
# the same SDK — `anthropic` catches both `@anthropic-ai/sdk` and
# `Anthropic.SDK`, `openai` catches `Azure.AI.OpenAI` and `go-openai` — so
# the list stays shorter than the set of packages it recognises.
#
# `claude-agent-sdk` needs its own entry: it drives the Claude Code CLI and
# never pulls in `anthropic`, which is how a Claude-based service could look
# like it had no LLM dependency at all.
_LLM_MARKERS = (
    # Anthropic
    "anthropic", "claude-agent-sdk", "claude-code-sdk",
    # OpenAI (also matches azure.ai.openai, go-openai, openai-agents)
    "openai",
    # Google
    "genai", "generativeai", "vertexai", "vertex-ai",
    # AWS / local runtimes
    "bedrock", "ollama",
    # Orchestration frameworks
    "langchain", "langgraph", "llama", "haystack", "dspy",
    "semantic-kernel", "semantickernel", "spring-ai",
    # Multi-agent frameworks
    "crewai", "autogen", "pydantic-ai",
    # Gateways and other providers
    "litellm", "mistralai", "cohere", "instructor",
)

# Dependency manifests scanned for those markers, as fnmatch patterns.
# Covers every stack govkit ships an overlay for — omitting .csproj, go.mod
# and build.gradle meant D008 false-negatived on dotnet-aspnet, go-gin and
# java-spring-boot no matter which SDK the project used.
_DEP_FILE_PATTERNS = (
    "pyproject.toml", "requirements*.txt",   # python
    "package.json",                          # node
    "pom.xml", "build.gradle", "build.gradle.kts",  # java (maven + gradle)
    "*.csproj",                              # .net
    "go.mod",                                # go
)

# Architecture style markers — folder names (any depth under target).
_HEXAGONAL_FOLDERS = {"ports", "adapters"}
_LAYERED_FOLDERS = {"Controllers", "Services", "Repositories"}
_CLEAN_FOLDERS = {"Application", "Domain", "Infrastructure", "Presentation"}
_DBT_FOLDERS = {"staging", "intermediate", "marts"}

# The fingerprints source-root detection matches against, and how many of a
# fingerprint's folders a package must hold to be recognised. `detect_services`
# and `detect_near_miss_packages` read both from here so "one below
# recognised" cannot drift away from what recognised means.
_LAYER_FINGERPRINTS = (_HEXAGONAL_FOLDERS, _LAYERED_FOLDERS, _CLEAN_FOLDERS)
_FINGERPRINT_THRESHOLD = 2


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
    # Where the layers live, observed at the same moment as the signals
    # above. Callers that write these into a file must use the profile
    # rather than re-deriving from the target: `apply` modifies the tree it
    # is describing (codex creates a layer folder per path-scoped rule), so
    # a second reading afterwards is a reading of govkit's own output.
    detected_source_root: str = ""
    detected_services: list[tuple[str, str]] = field(default_factory=list)
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


def _find_recursive(
    target: Path, pattern: str | tuple[str, ...], max_depth: int = 4,
) -> list[Path]:
    """Recursive search bounded by depth, pruning noise dirs during traversal.

    Uses os.walk with in-place `dirnames[:]` mutation so node_modules / .venv /
    etc. are never entered — important for large repos where rglob's
    walk-then-filter approach dominated build_profile() runtime.

    `pattern` may be a tuple, in which case a file matching any of them is
    returned from a single walk. Callers needing several manifests should
    pass them together rather than calling once per pattern — the walk, not
    the matching, is what costs.

    Depth is counted as path segments from target: a file at target/a/b/c.txt
    is depth 3. With max_depth=4, files up to four segments deep are returned.
    """
    patterns = (pattern,) if isinstance(pattern, str) else tuple(pattern)
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
                if any(fnmatch.fnmatch(fname, p) for p in patterns):
                    matches.append(current / fname)
            if depth + 1 >= max_depth:
                # Next level's files would exceed max_depth; stop descent.
                dirnames[:] = []
    except OSError:
        pass
    return matches


def _read_text(path: Path) -> str:
    """read_text_or_none with detection's empty-string default: an unreadable
    file simply contributes no signals."""
    return read_text_or_none(path) or ""


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
    py_files = _find_recursive(target, ("pyproject.toml", "requirements*.txt"))
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


def _package_dependencies(target: Path) -> set[str]:
    """Return package.json dependency names, tolerating absent/invalid JSON."""
    pkg = target / "package.json"
    if not pkg.is_file():
        return set()
    try:
        payload = json.loads(_read_text(pkg))
    except (json.JSONDecodeError, OSError):
        return set()
    names: set[str] = set()
    for section in ("dependencies", "devDependencies", "peerDependencies"):
        dependencies = payload.get(section)
        if isinstance(dependencies, dict):
            names.update(str(name) for name in dependencies)
    return names


def _detect_nextjs(target: Path) -> bool:
    return "next" in _package_dependencies(target)


def _detect_react_vite(target: Path) -> bool:
    dependencies = _package_dependencies(target)
    return "react" in dependencies and "vite" in dependencies


def _detect_angular(target: Path) -> bool:
    return (
        "@angular/core" in _package_dependencies(target)
        or (target / "angular.json").is_file()
    )


def _detect_tailwindcss(target: Path) -> bool:
    return "tailwindcss" in _package_dependencies(target)


def _detect_spring_boot(target: Path) -> bool:
    """Substring search across pom.xml and build.gradle*."""
    candidates = _find_recursive(target, ("pom.xml", "build.gradle", "build.gradle.kts"))
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
    if _detect_nextjs(target):
        detected.append("nextjs")
    if _detect_react_vite(target):
        detected.append("react-vite")
    if _detect_angular(target):
        detected.append("angular")
    if _detect_tailwindcss(target):
        detected.append("tailwindcss")
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

def _child_dir_names(root: Path) -> set[str]:
    """Immediate-child directory names of `root`, ignoring dot-dirs and the
    usual noise directories. Empty set when root is missing or unreadable."""
    names: set[str] = set()
    if not root.is_dir():
        return names
    try:
        for entry in root.iterdir():
            if entry.is_dir() and not entry.name.startswith(".") and entry.name not in _SKIP_DIRS:
                names.add(entry.name)
    except OSError:
        pass
    return names


def _top_level_folder_names(target: Path) -> set[str]:
    """Collect the immediate-child folder names under each known source root
    (target, src/, Source/, models/). dbt's layers live under models/; the
    others live at target root or src/.
    """
    names: set[str] = set()
    for root in (target, target / "src", target / "Source", target / "models"):
        names |= _child_dir_names(root)
    return names


def _source_folder_sets(target: Path) -> list[set[str]]:
    """Candidate folder-name sets to match architecture fingerprints against.

    The first set is the historical union of the known source roots, which
    covers the flat `src/{api,ports,...}` shape. Each remaining set is one
    direct child package of `src/` or `Source/` — the layout
    REPO_STRUCTURE_README.md actually documents (`src/<package>/api/...`),
    and the multi-service `src/{orders,billing}/` form.

    Kept per-package rather than unioned so two unrelated packages each
    holding one matching folder cannot combine into a false signal. The walk
    stops at direct children, so cost stays fixed regardless of repo size.
    """
    sets = [_top_level_folder_names(target)]
    for root in (target / "src", target / "Source"):
        if not root.is_dir():
            continue
        try:
            packages = sorted(p for p in root.iterdir() if p.is_dir())
        except OSError:
            continue
        for pkg in packages:
            if pkg.name.startswith(".") or pkg.name in _SKIP_DIRS:
                continue
            sets.append(_child_dir_names(pkg))
    return sets


_PACKAGE_ROOTS = ("src", "Source")


def _is_govkit_authored_folder(path: Path) -> bool:
    """True when `path` holds nothing but a govkit-authored `AGENTS.md`.

    govkit creates layer folders in exactly one place: the target root, when
    it could not detect a source root and codex's path-scoped destinations
    stayed root-relative. Everywhere else it writes into folders the team
    already had — that is how the source root was detected in the first
    place.

    Counting those folders as evidence of an architecture is what made a
    multi-service repo permanently unreadable: the first install wrote
    `api/AGENTS.md` and friends at the root, and every later run then saw
    layers at the root and reported a flat single-service repo. The damage
    was self-perpetuating, so neither the per-service fan-out nor doctor's
    D018 could ever fire on the installs that needed them.

    A folder the team owns is never discounted: one holding their own
    `AGENTS.md` with govkit's block appended below, or any other file
    alongside it, is theirs.
    """
    try:
        entries = list(path.iterdir())
    except OSError:
        return False
    if len(entries) != 1:
        return False
    only = entries[0]
    if not only.is_file() or only.name != "AGENTS.md":
        return False
    body = read_text_or_none(only)
    if body is None or GOVKIT_BLOCK_BEGIN not in body:
        return False
    # Govkit's block and nothing else — no content the team contributed.
    begin = body.find(GOVKIT_BLOCK_BEGIN)
    end = body.find(GOVKIT_BLOCK_END)
    if end < begin:
        return False
    return body[:begin].strip() == "" and body[end + len(GOVKIT_BLOCK_END):].strip() == ""


def _layer_root_candidates(target: Path) -> list[Path]:
    """Every directory under `target` that looks like a set of architecture
    layers.

    The single walk behind both `detect_source_root` and `detect_services`.
    They ask different questions of the same list — "is there exactly one?"
    and "which of these are service packages?" — and keeping the list in one
    place is what stops the two answers disagreeing. Splitting it would let
    a fingerprint, a skip-dir rule or the `Source/` sibling drift into one
    function and not the other, and `skill_context.yaml` would then claim a
    single source root *and* a set of services.

    Returns `[target]` when the layers sit at the target root, and stops
    there: a repo with both root-level layers and `src/<pkg>/` packages has
    no coherent answer, so the root wins and nothing further is collected.
    That is the behaviour `detect_source_root` has always had, preserved
    deliberately rather than inherited.

    Direct children only — `iterdir()` on `src/`, `Source/` and each of
    their packages. Cost is fixed regardless of repo size.
    """
    def _matches(root: Path, discount_govkit: bool = False) -> bool:
        names = _child_dir_names(root)
        if discount_govkit:
            names = {n for n in names if not _is_govkit_authored_folder(root / n)}
        return any(
            len(fp & names) >= _FINGERPRINT_THRESHOLD for fp in _LAYER_FINGERPRINTS
        )

    # Only the target root discounts govkit's own folders — see
    # `_is_govkit_authored_folder`. Applying it to `src/<pkg>/` would drop
    # the source root of a greenfield install whose layer folders are empty
    # but for the rules govkit just wrote, sending the next run's rules back
    # to the repo root.
    if _matches(target, discount_govkit=True):
        return [target]

    candidates: list[Path] = []
    for root in (target / name for name in _PACKAGE_ROOTS):
        if not root.is_dir():
            continue
        if _matches(root):
            candidates.append(root)
            continue
        try:
            packages = sorted(p for p in root.iterdir() if p.is_dir())
        except OSError:
            continue
        candidates.extend(
            p for p in packages
            if not p.name.startswith(".") and p.name not in _SKIP_DIRS and _matches(p)
        )
    return candidates


def detect_source_root(target: Path) -> str:
    """POSIX-relative directory holding the architecture layer folders.

    `""` when the layers sit at the target root, when no layout is
    recognisable, or when several sibling packages each look like a service
    — callers then fall back to root-relative destinations rather than
    guessing which service a rule belongs to.

    Used to place codex's path-scoped `AGENTS.md` rules next to the code
    they govern, and written to `skill_context.yaml` so a skill knows where
    the code lives. claude-code and copilot need no equivalent for rules:
    those carry `**/<layer>/**` globs that match at any depth.
    """
    candidates = _layer_root_candidates(target)
    # `[target]` is the layers-at-the-root case, whose relative path is "."
    # rather than "". Both mean "no prefix", and only one of them is a value
    # a caller can join onto a destination.
    if len(candidates) != 1 or candidates[0] == target:
        return ""
    return candidates[0].relative_to(target).as_posix()


def detect_near_miss_packages(target: Path) -> list[tuple[str, tuple[str, ...]]]:
    """`(root, matched folders)` for packages govkit almost called services.

    `detect_services` omits any package holding too few architecture layers.
    That is right — govkit can say nothing useful about `src/legacy/` — but
    it is silent, and a team reading `services: [orders, billing]` cannot
    tell whether that is the whole repo.

    A near miss overlaps some fingerprint by **exactly one** folder: enough
    that govkit looked at it, too little to name it. Reporting every
    unlisted directory instead would fire on `src/utils/`, `src/config/` and
    every shared package in every multi-service repo, which is noise — and
    noise trains people to ignore the check.

    The fingerprints and the threshold are the ones `_layer_root_candidates`
    uses, not a second copy, so "one below recognised" cannot drift away
    from what recognised means.

    Note the fingerprints are case-sensitive: the layered one holds
    `Services`, so a package with only `src/x/services/` overlaps nothing
    and is not a near miss.
    """
    recognised = set(_layer_root_candidates(target))
    near_misses: list[tuple[str, tuple[str, ...]]] = []
    for root in (target / name for name in _PACKAGE_ROOTS):
        if not root.is_dir():
            continue
        try:
            packages = sorted(p for p in root.iterdir() if p.is_dir())
        except OSError:
            continue
        for package in packages:
            if package.name.startswith(".") or package.name in _SKIP_DIRS:
                continue
            if package in recognised:
                continue
            names = _child_dir_names(package)
            matched = max((fp & names for fp in _LAYER_FINGERPRINTS), key=len, default=set())
            if 0 < len(matched) < _FINGERPRINT_THRESHOLD:
                near_misses.append(
                    (package.relative_to(target).as_posix(), tuple(sorted(matched))),
                )
    return near_misses


def detect_services(target: Path) -> list[tuple[str, str]]:
    """`(name, root)` for each service package, or `[]` when there is one.

    A *service* is a package under `src/` or `Source/` that holds its own
    architecture layers — the `src/{orders,billing}/` shape. `src/` holding
    the layers directly is a source root, not a service, so it is never
    named; a repo whose only service is `src/mypkg` is the documented
    single-service layout and is described by `detect_source_root` alone.

    `name` is the package name: derivable, stable, and what the code
    already calls itself. Teams that want a friendlier label edit
    `architecture.services` in skill_context.yaml, which the provenance
    mechanism preserves like every other tunable.

    Packages that do not conform — `src/legacy/` next to two real services —
    are omitted. That omission is silent here by design; it is the emitted
    file, not this function, that has to make it visible.
    """
    package_roots = {target / name for name in _PACKAGE_ROOTS}
    services = [
        c for c in _layer_root_candidates(target) if c.parent in package_roots
    ]
    if len(services) < 2:
        return []
    return [(c.name, c.relative_to(target).as_posix()) for c in services]


def _detect_architecture(target: Path, prof: RepoProfile) -> None:
    """Match source folder names against known style fingerprints.

    A fingerprint fires when any single candidate source root matches it —
    the flat layout via the union set, the documented `src/<package>/`
    layout via that package's own set.
    """
    folder_sets = _source_folder_sets(target)

    def _fires(fingerprint: set[str]) -> bool:
        return any(len(fingerprint & folders) >= 2 for folders in folder_sets)

    signals: list[str] = []
    if _fires(_HEXAGONAL_FOLDERS):
        signals.append("hexagonal-shape")
    if _fires(_LAYERED_FOLDERS):
        signals.append("layered-shape")
    if _fires(_CLEAN_FOLDERS):
        signals.append("clean-shape")
    if _fires(_DBT_FOLDERS):
        signals.append("dbt-shape")
    prof.detected_architecture_signals = signals


# ---------------------------------------------------------------------------
# LLM signals
# ---------------------------------------------------------------------------

def _detect_llm_signals(target: Path, prof: RepoProfile) -> None:
    """Record which LLM SDK markers appear in the repo's dependency files.

    package.json is searched recursively like every other manifest — a JS
    monorepo keeps its dependencies in `apps/<app>/package.json`, and only
    reading the root one hid them. `_find_recursive` prunes node_modules and
    bounds depth, so this stays cheap.
    """
    candidates = _find_recursive(target, _DEP_FILE_PATTERNS)

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
    prof.detected_source_root = detect_source_root(target)
    prof.detected_services = detect_services(target)
    _detect_llm_signals(target, prof)
    return prof
