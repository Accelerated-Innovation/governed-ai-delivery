# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Render native SKILL.md identities without changing pack source/provenance.

Versioned rendering contracts stay stable for offline lock replay. V3 carries
explicit invocation policy and native prompt aliases; v1/v2 retain old bytes.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

import yaml

SKILL_RENDERING = "install-as-v3"
_FRONTMATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|\Z)", re.DOTALL)
_IDENTIFIER = re.compile(r"[a-z0-9][a-z0-9-]*\Z")
_REFERENCE_DESTINATION = re.compile(
    r"^[ \t]*(?:(?:>|[-+*]|\d{1,9}[.)])[ \t]*)*"
    r"\[(?:\\[^\r\n]|[^\[\]\\]){1,999}\]:[ \t]*"
    r"(?:\r?\n[ \t]*(?:>[ \t]*)*)?"
    r"(?P<destination><(?:\\[^\r\n]|[^<>\\\r\n])*>|(?:\\[^\r\n]|[^\s<>\\])+)",
    re.MULTILINE,
)


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
    """Original v1 substitution, retained byte-for-byte for locked resources."""
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


def _references_v2(text: str, aliases: dict[str, str]) -> str:
    """Leave reference-definition destinations literal, including shown examples.

    This conservatively recognizes resource syntax in block containers without
    parsing or reserializing Markdown. Surrounding instruction text and visible
    labels still use the original alias substitution.
    """
    parts = []
    previous = 0
    for match in _REFERENCE_DESTINATION.finditer(text):
        start, end = match.span("destination")
        parts.append(_references(text[previous:start], aliases))
        parts.append(text[start:end])
        previous = end
    parts.append(_references(text[previous:], aliases))
    return "".join(parts)


def render_skill(
    content: bytes,
    install_as: str,
    aliases: dict[str, str],
    *,
    rendering: str = SKILL_RENDERING,
    explicit_only: bool = False,
) -> bytes:
    """Render only native metadata/instructions; callers retain raw pinned bytes."""
    document = _document(content)
    if document is None:
        return content
    references = {
        "install-as-v1": _references,
        "install-as-v2": _references_v2,
        "install-as-v3": _references_v2,
    }[rendering]
    text, match, metadata = document
    names = {**aliases, metadata["name"]: install_as}
    updated = {**metadata, "name": install_as}
    if explicit_only and rendering == "install-as-v3":
        updated["disable-model-invocation"] = True
    if isinstance(metadata.get("description"), str):
        updated["description"] = references(metadata["description"], names)
    body = references(text[match.end() :], names)
    if updated == metadata and body == text[match.end() :]:
        return content
    header = yaml.safe_dump(updated, allow_unicode=True, sort_keys=False).rstrip()
    return f"---\n{header}\n---\n{body}".encode("utf-8")


def render_native_skill(
    files: dict[str, bytes],
    install_as: str,
    aliases: dict[str, str],
    agent: str,
    *,
    rendering: str = SKILL_RENDERING,
) -> dict[str, bytes]:
    """Render native entrypoints only; supporting files and pinned sources stay raw.

    Read the documented Codex policy, never infer it from prose, names or truthy
    values. Older contracts ignore the sidecar entirely for exact lock replay.
    """
    output = dict(files)
    config_path = "agents/openai.yaml"
    config = None
    if rendering == "install-as-v3" and config_path in files:
        try:
            config = yaml.safe_load(files[config_path].decode("utf-8"))
        except (UnicodeError, yaml.YAMLError):
            pass  # Preserve unrecognized historical metadata byte-for-byte.
    policy = config.get("policy") if isinstance(config, dict) else None
    explicit_only = isinstance(policy, dict) and policy.get("allow_implicit_invocation") is False
    output["SKILL.md"] = render_skill(
        files["SKILL.md"],
        install_as,
        aliases,
        rendering=rendering,
        explicit_only=explicit_only and agent in {"claude-code", "copilot"},
    )
    interface = config.get("interface") if isinstance(config, dict) else None
    if isinstance(interface, dict) and isinstance(interface.get("default_prompt"), str):
        names = {**aliases, **skill_aliases([(install_as, files["SKILL.md"])])}
        prompt = _references_v2(interface["default_prompt"], names)
        if prompt != interface["default_prompt"]:
            updated = {**config, "interface": {**interface, "default_prompt": prompt}}
            output[config_path] = yaml.safe_dump(
                updated, allow_unicode=True, sort_keys=False
            ).encode("utf-8")
    return output
