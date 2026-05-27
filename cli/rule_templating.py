#!/usr/bin/env python3
# Copyright 2026 Accelerated Innovation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
"""Rule-glob templating: expand `paths_template: layers.<key>` at install time.

PR 6b. The source claude-code rule files declare `paths_template:` so
that, at install time, `cmd_apply` / `cmd_stack_apply` / `cmd_upgrade`
can substitute concrete `paths:` globs based on the team's actual
architecture (carried in skill_context.layers). This avoids the D001
false-positive where a rule scoped to `**/adapters/**` produces zero
matches in a Clean Architecture repo using `Infrastructure/`.

Templating happens at install time because Claude Code can't dynamically
resolve `skill_context.layers.outbound` from a rule's frontmatter at
agent runtime — the glob list must be concrete by the time the file
lands in `.claude/rules/`.

Degradation strategy: if the template key is unknown or the layer list
is empty (e.g. style="unknown"), the source file's existing `paths:`
fallback survives unchanged. Doctor D001 then surfaces the real
mismatch — which is the right signal.
"""

from pathlib import Path

import yaml


_TEMPLATE_KEY = "paths_template"
_PATHS_KEY = "paths"

# Where each agent's rule files land. Codex uses nested AGENTS.md placement —
# no glob frontmatter, so nothing to template.
_RULES_DIRS_BY_AGENT: dict[str, list[str]] = {
    "claude-code": [".claude/rules"],
    "copilot":     [".github/instructions"],
    "codex":       [],
}


def expand_rule_template(text: str, layers: dict[str, list[str]]) -> str:
    """Expand `paths_template: layers.<key>` in a rule file's frontmatter.

    Returns the rewritten file text. Files without `paths_template:` come
    through unchanged. Files where the template resolves to non-empty
    layer hints get a `paths:` block that replaces any fallback.
    """
    if not text or not text.startswith("---"):
        return text
    end = text.find("\n---", 3)
    if end == -1:
        return text

    frontmatter_text = text[3:end]
    body = text[end + len("\n---"):]
    try:
        fm = yaml.safe_load(frontmatter_text) or {}
    except yaml.YAMLError:
        return text
    if not isinstance(fm, dict):
        return text

    template_ref = fm.get(_TEMPLATE_KEY)
    if not isinstance(template_ref, str):
        return text

    expanded = _expand_template_ref(template_ref, layers)
    # Drop the template directive so apply doesn't re-process this file.
    fm.pop(_TEMPLATE_KEY, None)
    if expanded:
        fm[_PATHS_KEY] = expanded
    # Else: leave `paths:` untouched (fallback preserved).

    new_fm_text = yaml.safe_dump(fm, sort_keys=False, default_flow_style=False).rstrip("\n")
    return f"---\n{new_fm_text}\n---{body}"


def _expand_template_ref(template_ref: str, layers: dict[str, list[str]]) -> list[str]:
    """Resolve `layers.<key>` to a list of `**/<hint>/**` globs.

    Returns [] when the key is unknown or the layer list is empty so the
    caller knows to keep any existing fallback paths.
    """
    if not template_ref.startswith("layers."):
        return []
    key = template_ref[len("layers."):]
    hints = layers.get(key) or []
    return [_hint_to_glob(h) for h in hints if isinstance(h, str) and h]


def _hint_to_glob(hint: str) -> str:
    """Normalise a layer hint like 'api/' or 'Controllers/' into a `**/<hint>/**`
    glob that matches the folder at any depth in the repo."""
    cleaned = hint.strip().strip("/")
    return f"**/{cleaned}/**"


def template_installed_rules(
    target: Path,
    agent: str,
    layers: dict[str, list[str]],
) -> int:
    """Walk the installed rules dir(s) for `agent` and expand `paths_template`
    in every rule file using the team's actual `layers` map.

    Returns the count of files modified. Silent on missing directories so
    fresh installs / agents without a rules dir (codex) are safe no-ops.

    Called from cmd_apply / cmd_upgrade after agent files are copied AND
    skill_context is available. Stack apply doesn't re-copy rules, so it
    doesn't call this — architecture style is a property of the repo, not
    the stack.
    """
    modified = 0
    for rules_rel in _RULES_DIRS_BY_AGENT.get(agent, []):
        rules_root = target / rules_rel
        if not rules_root.is_dir():
            continue
        for md in rules_root.rglob("*.md"):
            try:
                text = md.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            new_text = expand_rule_template(text, layers)
            if new_text != text:
                md.write_text(new_text, encoding="utf-8")
                modified += 1
    return modified
