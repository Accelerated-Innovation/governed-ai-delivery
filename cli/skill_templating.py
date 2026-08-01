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

import re
from pathlib import Path

from .agent_layout import AGENT_LAYOUTS
from .fs import read_text_or_none

_DOCS_AREA_TOKEN = "{{docs_area}}"
_PII_KEYWORDS_TOKEN = "{{pii_keywords}}"


def expand_skill_tokens(text: str, docs_area: str) -> str:
    """Expand skill tokens in `text` for the install's docs area.

    Empty `docs_area` leaves the token in place (unknown context must stay
    visible, not be guessed away). Tokens other than `{{docs_area}}` are not
    recognized and pass through untouched.
    """
    if not docs_area:
        return text
    return text.replace(_DOCS_AREA_TOKEN, docs_area)


def render_pii_keywords(keywords: list[str]) -> str:
    """Render the PII keyword list for prose insertion: `email`, `phone`, ..."""
    return ", ".join(f"`{k}`" for k in keywords)


# The rendered list is fenced so a later pass can find and replace it.
# `pii.keyword_list` is team-tunable, and substituting the token in place
# left nothing to re-render from: `apply`/`upgrade` recovered because they
# re-copy each rule from the bundle, but `calibrate` does not, so a tuned
# list never reached the rule bodies. Same marker idiom as the managed
# AGENTS.md block and the `govkit:editable` header.
_PII_OPEN = "<!-- govkit:pii_keywords -->"
_PII_CLOSE = "<!-- /govkit:pii_keywords -->"
_PII_SPAN = re.compile(
    re.escape(_PII_OPEN) + r".*?" + re.escape(_PII_CLOSE), re.DOTALL,
)


def expand_pii_keywords(text: str, keywords: list[str]) -> str:
    """Render `keywords` into `text`, replacing either the source token or a
    previously rendered span.

    Idempotent: rendering the same list twice is a no-op. An empty list
    leaves the text untouched, matching the docs_area rule that unknown
    context stays visible rather than being guessed away.
    """
    if not keywords:
        return text
    fenced = f"{_PII_OPEN}{render_pii_keywords(keywords)}{_PII_CLOSE}"
    if _PII_SPAN.search(text):
        return _PII_SPAN.sub(lambda _m: fenced, text)
    return text.replace(_PII_KEYWORDS_TOKEN, fenced)


def template_installed_rule_bodies(target: Path, agent: str, pii_keywords: list[str]) -> int:
    """Expand `{{pii_keywords}}` in installed rule bodies.

    Rule bodies embed no team-tunable literals — the tunables live in
    skill_context (`pii.keyword_list`) and are rendered in at install time,
    so the rules and the CI gate's PII check share one source. Walks the
    agent's rules dir; codex additionally gets `.agents/rules` plus any
    AGENTS.md carrying the token (its dbt layer rules install as nested
    managed blocks). An empty list leaves tokens in place (doctor's skill
    token check pattern: unknown context stays visible).
    """
    if not pii_keywords:
        return 0
    layout = AGENT_LAYOUTS.get(agent)
    if layout is None:
        return 0
    candidates: list[Path] = []
    if layout.rules_dir and (target / layout.rules_dir).is_dir():
        candidates.extend(sorted((target / layout.rules_dir).rglob("*.md")))
    if agent == "codex":
        agents_rules = target / ".agents" / "rules"
        if agents_rules.is_dir():
            candidates.extend(sorted(agents_rules.rglob("*.md")))
        candidates.extend(sorted(target.rglob("AGENTS.md")))

    modified = 0
    for path in candidates:
        text = read_text_or_none(path)
        if text is None:
            continue
        # Either an unrendered token (fresh copy from the bundle) or a span
        # rendered by an earlier run whose list has since been tuned.
        if _PII_KEYWORDS_TOKEN not in text and not _PII_SPAN.search(text):
            continue
        new_text = expand_pii_keywords(text, pii_keywords)
        if new_text == text:
            continue
        path.write_text(new_text, encoding="utf-8")
        modified += 1
    return modified


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
        text = read_text_or_none(path)
        if text is None:
            continue
        expanded = expand_skill_tokens(text, docs_area)
        if expanded != text:
            path.write_text(expanded, encoding="utf-8")
            modified += 1
    return modified
