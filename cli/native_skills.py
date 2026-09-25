# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Render native SKILL.md identities without changing pack source/provenance.

This is the install-as-v1 lock contract. Keep it stable for offline replay;
future rendering changes need a distinct contract and the old implementation.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

import yaml

SKILL_RENDERING = "install-as-v1"
_FRONTMATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|\Z)", re.DOTALL)
_IDENTIFIER = re.compile(r"[a-z0-9][a-z0-9-]*\Z")


def _document(content: bytes) -> tuple[str, re.Match[str], dict] | None:
    """Historical packs may lack valid frontmatter; retain those bytes as-is."""
    try:
        text = content.decode("utf-8")
        match = _FRONTMATTER.match(text)
        metadata = yaml.safe_load(match[1]) if match else None
    except (UnicodeError, yaml.YAMLError):
        return None
    if not isinstance(metadata, dict) or not isinstance(metadata.get("name"), str):
        return None
    if not _IDENTIFIER.fullmatch(metadata["name"]):
        return None
    return text, match, metadata


def skill_aliases(skills: Iterable[tuple[str, bytes]]) -> dict[str, str]:
    """Map unambiguous upstream identities to the manifest's native names."""
    candidates: dict[str, set[str]] = {}
    for install_as, content in skills:
        document = _document(content)
        if document:
            candidates.setdefault(document[2]["name"], set()).add(install_as)
    return {name: next(iter(names)) for name, names in candidates.items() if len(names) == 1}


def _references(text: str, aliases: dict[str, str]) -> str:
    names = "|".join(re.escape(name) for name in sorted(aliases, key=len, reverse=True))
    if not names:
        return text
    # URLs and filesystem paths remain provenance/resource references. Only
    # standalone skill identifiers and native /name or $name invocations change.
    pattern = re.compile(
        r"(?P<protected>\]\([^\n)]*\)|(?:[a-zA-Z][a-zA-Z0-9+.-]*://|mailto:)[^\s<>]+)"
        r"|(?<![\w./\\:@%#-])(?P<sigil>[/\$]?)(?P<name>" + names + r")(?![\w/\\-]|\.[\w])"
    )

    def replace(match):
        if match["protected"]:
            return match[0]
        name, sigil = match["name"], match["sigil"]
        # A one-word name may also be ordinary prose. Require explicit native
        # invocation or code formatting for these references (e.g. `help`).
        if "-" not in name and not sigil:
            before, after = text[: match.start()], text[match.end() :]
            if not (before.endswith("`") and after.startswith("`")):
                return match[0]
        return sigil + aliases[name]

    return pattern.sub(replace, text)


def render_skill(content: bytes, install_as: str, aliases: dict[str, str]) -> bytes:
    """Render only native metadata/instructions; callers retain raw pinned bytes."""
    document = _document(content)
    if document is None:
        return content
    text, match, metadata = document
    names = {**aliases, metadata["name"]: install_as}
    updated = {**metadata, "name": install_as}
    if isinstance(metadata.get("description"), str):
        updated["description"] = _references(metadata["description"], names)
    body = _references(text[match.end() :], names)
    if updated == metadata and body == text[match.end() :]:
        return content
    header = yaml.safe_dump(updated, allow_unicode=True, sort_keys=False).rstrip()
    return f"---\n{header}\n---\n{body}".encode("utf-8")
