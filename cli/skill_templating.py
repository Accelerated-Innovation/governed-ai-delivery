#!/usr/bin/env python3
# Copyright 2026 Accelerated Innovation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
"""Install-time token expansion for installed skill files.

Skill sources reference the type's docs tree as `docs/{{docs_area}}/...`
instead of hardcoding `docs/backend/`. Agents cannot resolve skill_context at
runtime, so — like rule glob templating (cli/rule_templating.py) — the token
is expanded once at install time, in `post_install_finalize`, after
skill_context.yaml is written.

Unlike rule templating (a frontmatter directive), this is inline body
substitution: skills cite doc paths in prose. Degradation matches the rule
pass: an unresolvable token (empty docs_area from a missing/unknown marker
type) is left in the text — doctor flags it — never guessed.

Installed skills are govkit-owned (no editable header, unconditionally
refreshed on apply/upgrade), so rewriting them in place clobbers nothing.
"""

from __future__ import annotations

from pathlib import Path

from .agent_layout import AGENT_LAYOUTS

_DOCS_AREA_TOKEN = "{{docs_area}}"


def expand_skill_tokens(text: str, docs_area: str) -> str:
    """Expand skill tokens in `text` for the install's docs area.

    Empty `docs_area` leaves the token in place (unknown context must stay
    visible, not be guessed away). Tokens other than `{{docs_area}}` are not
    recognized and pass through untouched.
    """
    if not docs_area:
        return text
    return text.replace(_DOCS_AREA_TOKEN, docs_area)


def template_installed_skills(target: Path, agent: str, docs_area: str) -> int:
    """Expand tokens in every installed skill file for `agent` under `target`.

    Walks the agent's skills dir (AGENT_LAYOUTS), rewrites files in place,
    and returns the number of files modified. No-op (0) for unknown agents,
    layouts without a skills dir, a missing directory, or empty docs_area.
    """
    layout = AGENT_LAYOUTS.get(agent)
    if layout is None or layout.skills_dir is None or not docs_area:
        return 0
    skills_root = target / layout.skills_dir
    if not skills_root.is_dir():
        return 0

    modified = 0
    for path in sorted(skills_root.rglob("*.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        expanded = expand_skill_tokens(text, docs_area)
        if expanded != text:
            path.write_text(expanded, encoding="utf-8")
            modified += 1
    return modified
