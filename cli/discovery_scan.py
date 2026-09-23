# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Bounded offline observations, with no inference promoted to project policy."""

from __future__ import annotations

import ast
import json
import os
import re
import stat
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath

from .schema_validation import DocumentError, content_digest

_EXCLUDED = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "vendor",
        "dist",
        "build",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        ".govkit",
        ".agents",
        ".claude",
        "skills",
    }
)
_MANIFESTS = frozenset(
    {"pyproject.toml", "requirements.txt", "package.json", "go.mod", "Cargo.toml", "pom.xml"}
)
_CODE = frozenset({".py", ".js", ".ts", ".tsx", ".go", ".rs", ".java", ".cs"})
_DEPENDENCIES = {
    "fastapi": "framework:fastapi",
    "django": "framework:django",
    "flask": "framework:flask",
    "react": "framework:react",
    "next": "framework:nextjs",
    "mcp": "tool:mcp",
    "fastmcp": "tool:mcp",
    "openai": "model:openai",
    "anthropic": "model:anthropic",
    "langchain": "model:langchain",
    "pytest": "test:pytest",
    "vitest": "test:vitest",
    "jest": "test:jest",
}


@dataclass(frozen=True)
class DiscoveryLimits:
    max_entries: int = 2048
    max_files: int = 128
    max_bytes: int = 65536
    max_total_bytes: int = 1048576
    max_depth: int = 6

    def __post_init__(self):
        for value in asdict(self).values():
            if type(value) is not int or value < 1:
                raise DocumentError("Discovery limits must be positive integers")


@dataclass(frozen=True)
class Observation:
    source: str
    category: str
    scope: str
    status: str
    digest: str | None
    confidence: str
    signals: tuple[str, ...] = ()

    def document(self):
        return {**asdict(self), "signals": list(self.signals)}


@dataclass(frozen=True)
class Scan:
    observations: tuple[Observation, ...]
    boundaries: tuple[str, ...]
    complete: bool
    limitations: tuple[str, ...]
    limits: DiscoveryLimits
    references: tuple[str, ...]


def _category(relative: str) -> str | None:
    path = PurePosixPath(relative)
    name = path.name.lower()
    parts = {p.lower() for p in path.parts}
    if path.name in _MANIFESTS or name.endswith(".csproj"):
        return "manifest"
    if (
        "workflows" in parts
        and ".github" in parts
        or name
        in {"azure-pipelines.yml", "azure-pipelines.yaml", "jenkinsfile", "makefile", "tox.ini"}
    ):
        return "ci"
    if name in {"agents.md", "claude.md", "copilot-instructions.md"}:
        return "guidance"
    if path.suffix.lower() in {".md", ".rst"}:
        if parts & {"adr", "adrs", "decisions"}:
            return "decision"
        if "arch" in name or "convention" in name or parts & {"architecture", "design"}:
            return "architecture"
        return "documentation"
    if path.suffix in _CODE:
        return (
            "test"
            if parts & {"test", "tests", "spec", "specs"}
            or name.startswith("test_")
            or ".test." in name
            else "code"
        )
    if path.suffix == ".feature":
        return "test"
    return None


def _dependency_signals(names):
    signals = set()
    for name in names:
        root = re.split(r"[\s\[<>=!~;./]", name.strip().lower())[0]
        if root in _DEPENDENCIES:
            signals.add(_DEPENDENCIES[root])
    return signals


def _signals(relative, category, content):
    """Recognize narrow syntactic indicators; never execute manifests or source."""
    name = PurePosixPath(relative).name
    text = content.decode("utf-8")
    signals = set()
    if category == "manifest":
        signals.add("boundary:manifest")
        if name == "pyproject.toml":
            data = tomllib.loads(text)
            project = data.get("project", {})
            dependencies = list(project.get("dependencies", []))
            for group in project.get("optional-dependencies", {}).values():
                dependencies.extend(group)
            dependencies.extend(data.get("tool", {}).get("poetry", {}).get("dependencies", {}))
            signals.add("language:python")
            signals.update(_dependency_signals(dependencies))
        elif name == "package.json":
            data = json.loads(text)
            dependencies = [*data.get("dependencies", {}), *data.get("devDependencies", {})]
            signals.update(_dependency_signals(dependencies))
            signals.add("language:javascript")
            if data.get("workspaces"):
                signals.add("boundary:workspace")
            if "test" in data.get("scripts", {}):
                signals.add("test:package-script")
        elif name == "requirements.txt":
            signals.add("language:python")
            signals.update(_dependency_signals(text.splitlines()))
    if category in {"code", "test"}:
        if relative.endswith(".py"):
            tree = ast.parse(text)
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.append(node.module)
            signals.update(_dependency_signals(imports))
            signals.add("language:python")
        else:
            imports = re.findall(r"""(?:from\s+|require\(|import\s*)["']([^"']+)["']""", text)
            signals.update(_dependency_signals(imports))
    if category in {"architecture", "documentation", "guidance", "decision"}:
        for style in ("hexagonal", "layered", "clean"):
            if re.search(rf"\b{style}\s+architecture\b", text, re.IGNORECASE):
                signals.add(f"architecture:{style}")
    if category == "test":
        signals.add("check:test-source")
    if category == "ci":
        signals.add("check:ci-definition")
    return tuple(sorted(signals))


def _safe_path(target: Path, relative: str) -> Path:
    path = PurePosixPath(relative)
    if (
        path.is_absolute()
        or ".." in path.parts
        or "\\" in relative
        or not path.parts
        or ":" in relative
    ):
        raise DocumentError("Reference is not a repository-relative file")
    current = target
    for part in path.parts:
        current = current / part
        if current.is_symlink():
            raise DocumentError("Symlink evidence is not followed")
    if not current.resolve().is_relative_to(target.resolve()):
        raise DocumentError("Reference escapes repository")
    return current


def _bounded_references(references, limits: DiscoveryLimits) -> tuple[tuple[str, ...], bool]:
    """Bound both unique storage and iteration, including duplicate-heavy inputs."""
    selected = set()
    for index, reference in enumerate(references):
        if index >= limits.max_entries:
            return tuple(sorted(selected)), True
        if reference not in selected:
            if len(selected) >= limits.max_files:
                return tuple(sorted(selected)), True
            selected.add(reference)
    return tuple(sorted(selected)), False


def scan_repository(target: Path, *, references=(), limits: DiscoveryLimits | None = None) -> Scan:
    target = target.absolute()
    limits = limits or DiscoveryLimits()
    if target.is_symlink() or not target.is_dir():
        raise DocumentError("Discovery target must be an existing directory, not a symlink")
    references, reference_limited = _bounded_references(references, limits)
    reference_set = frozenset(references)
    candidates = {reference: _category(reference) or "reference" for reference in references}
    limitations = {"reference-limit"} if reference_limited else set()
    entries_seen = 0
    # Bounded enumeration: do not materialize/sort an unbounded directory listing.
    pending = [(target, 0)]
    while pending:
        directory, depth = pending.pop(0)
        relative_dir = directory.relative_to(target).as_posix()
        try:
            entries = []
            with os.scandir(directory) as iterator:
                for entry in iterator:
                    entries_seen += 1
                    if entries_seen > limits.max_entries:
                        limitations.add("entry-limit")
                        break
                    entries.append(entry)
            for entry in sorted(entries, key=lambda item: item.name):
                relative = (directory / entry.name).relative_to(target).as_posix()
                if entry.name in _EXCLUDED:
                    continue
                if entry.is_symlink():
                    candidates.setdefault(relative, _category(relative) or "inventory")
                elif entry.is_dir(follow_symlinks=False):
                    if depth < limits.max_depth:
                        pending.append((Path(entry.path), depth + 1))
                    else:
                        limitations.add(f"depth-limit:{relative}")
                elif category := _category(relative):
                    candidates.setdefault(relative, category)
            if entries_seen > limits.max_entries:
                break
        except OSError:
            limitations.add(f"unreadable-directory:{relative_dir}")
    boundaries = {"."}
    for relative, category in candidates.items():
        if category == "manifest":
            boundaries.add(str(PurePosixPath(relative).parent))
    observations = []
    consumed = 0
    ordered = sorted(candidates, key=lambda p: (p not in reference_set, p))
    if len(ordered) > limits.max_files:
        limitations.add("file-limit")
    for relative in ordered[: limits.max_files]:
        category = candidates[relative]
        scope = max((b for b in boundaries if b == "." or relative.startswith(b + "/")), key=len)
        status, digest, confidence, signals = "observed", None, "high", ()
        try:
            path = _safe_path(target, relative)
            if not stat.S_ISREG(path.stat().st_mode):
                raise DocumentError("Evidence is not a regular file")
            allowance = min(limits.max_bytes, max(0, limits.max_total_bytes - consumed))
            # Read at most the configured allowance plus a sentinel, never a FIFO/device.
            with path.open("rb") as stream:
                content = stream.read(allowance + 1)
            consumed += len(content)
            if len(content) > allowance:
                status, confidence = "limited", "low"
                limitations.add(f"byte-limit:{relative}")
            else:
                digest = content_digest(content)
                if category in {
                    "architecture",
                    "documentation",
                    "decision",
                    "guidance",
                    "reference",
                }:
                    confidence = "medium"
                try:
                    signals = _signals(relative, category, content)
                except (ValueError, TypeError, AttributeError, SyntaxError, RecursionError):
                    status, confidence = "unavailable", "low"
                    limitations.add(f"uninterpreted:{relative}")
        except FileNotFoundError:
            status, confidence = "missing", "low"
            limitations.add(f"missing-reference:{relative}")
        except (OSError, ValueError, RuntimeError):
            status, confidence = "unavailable", "low"
            limitations.add(f"unavailable:{relative}")
        observations.append(
            Observation(relative, category, scope, status, digest, confidence, signals)
        )
    return Scan(
        tuple(sorted(observations, key=lambda o: o.source)),
        tuple(sorted(boundaries)),
        not limitations,
        tuple(sorted(limitations)),
        limits,
        references,
    )
