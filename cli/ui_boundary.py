#!/usr/bin/env python3
# Copyright 2026 Accelerated Innovation
#
# Licensed under the Apache License, Version 2.0 (the "License");
"""Static enforcement for the standalone Next.js API/database boundary."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

DISALLOWED_PACKAGES = frozenset({
    "@libsql/client",
    "@neondatabase/serverless",
    "@planetscale/database",
    "@prisma/client",
    "better-sqlite3",
    "drizzle-orm",
    "kysely",
    "knex",
    "mongodb",
    "mongoose",
    "mssql",
    "mysql",
    "mysql2",
    "oracledb",
    "pg",
    "postgres",
    "prisma",
    "sequelize",
    "sqlite",
    "sqlite3",
    "tedious",
    "typeorm",
})

_SOURCE_SUFFIXES = frozenset({".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"})
_SKIP_DIRS = frozenset({
    ".git", ".govkit", ".next", "build", "coverage", "dist", "node_modules",
    "out", "vendor",
})
_DATABASE_DIR_NAMES = frozenset({"database", "db", "migrations", "prisma"})
_CONNECTION_KEY = re.compile(
    r"\b("
    r"DATABASE_URL|DIRECT_URL|DB_CONNECTION|DB_HOST|DB_NAME|DB_PASSWORD|"
    r"DB_PORT|DB_URL|DB_USER|MONGODB_URI|MYSQL_URL|POSTGRES_URL|"
    r"POSTGRES_PRISMA_URL|SQL_CONNECTION_STRING"
    r")\b\s*[:=]",
)
_IMPORT_PACKAGE = re.compile(
    r"(?:from\s+|import\s*\(|require\s*\()\s*['\"]([^'\"]+)['\"]",
)


@dataclass(frozen=True)
class UIBoundaryViolation:
    rule: str
    file: str
    detail: str


def _relative(path: Path, target: Path) -> str:
    try:
        return str(path.relative_to(target)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _iter_project_files(target: Path):
    for path in target.rglob("*"):
        if not path.is_file():
            continue
        try:
            parts = path.relative_to(target).parts
        except ValueError:
            continue
        if any(part in _SKIP_DIRS for part in parts):
            continue
        yield path, parts


def _package_root(import_name: str) -> str:
    if import_name.startswith("@"):
        return "/".join(import_name.split("/")[:2])
    return import_name.split("/", 1)[0]


def scan_ui_boundary(target: Path) -> list[UIBoundaryViolation]:
    """Return deterministic violations without reading or printing secret values."""
    target = target.resolve()
    violations: list[UIBoundaryViolation] = []

    package_json = target / "package.json"
    if package_json.is_file():
        try:
            payload = json.loads(package_json.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            payload = {}
        for section in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
            dependencies = payload.get(section)
            if not isinstance(dependencies, dict):
                continue
            for name in sorted(set(dependencies) & DISALLOWED_PACKAGES):
                violations.append(UIBoundaryViolation(
                    rule="database-package",
                    file="package.json",
                    detail=f"{section} declares forbidden database package `{name}`",
                ))

    for path, parts in _iter_project_files(target):
        relative = _relative(path, target)

        if path.suffix.lower() == ".sql":
            violations.append(UIBoundaryViolation(
                rule="sql-file",
                file=relative,
                detail="SQL files are not allowed in a standalone UI project",
            ))

        if any(part.lower() in _DATABASE_DIR_NAMES for part in parts[:-1]):
            violations.append(UIBoundaryViolation(
                rule="database-artifact",
                file=relative,
                detail="database, migration, or ORM artifacts belong behind the backend API",
            ))

        should_scan_text = (
            path.suffix.lower() in _SOURCE_SUFFIXES
            or path.name.startswith(".env")
            or path.name in {"next.config.ts", "next.config.js", "next.config.mjs"}
        )
        if not should_scan_text:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        if path.suffix.lower() in _SOURCE_SUFFIXES:
            for imported in _IMPORT_PACKAGE.findall(text):
                package = _package_root(imported)
                if package in DISALLOWED_PACKAGES:
                    violations.append(UIBoundaryViolation(
                        rule="database-import",
                        file=relative,
                        detail=f"imports forbidden database package `{package}`",
                    ))

        for key in sorted(set(_CONNECTION_KEY.findall(text))):
            violations.append(UIBoundaryViolation(
                rule="connection-string",
                file=relative,
                detail=f"declares database connection key `{key}`",
            ))

    return sorted(violations, key=lambda item: (item.file, item.rule, item.detail))
