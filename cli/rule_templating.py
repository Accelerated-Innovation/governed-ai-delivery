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

from .agent_layout import AGENT_LAYOUTS

# Each agent uses its own frontmatter shape:
#   claude-code → paths_template: layers.<k>  →  paths: [<globs>]      (list)
#   copilot     → applyTo_template: layers.<k>→  applyTo: "<glob,...>" (string)
# The per-key (template_key, output_key, list_vs_string) schemas derive from
# AGENT_LAYOUTS; expansion stays agent-agnostic — every schema is tried against
# every file so the helper handles both shapes from one entry point.
_TEMPLATE_SCHEMAS: list[tuple[str, str, str]] = [
    (f"{layout.frontmatter_glob_key}_template",
     layout.frontmatter_glob_key, layout.glob_value_shape)
    for layout in AGENT_LAYOUTS.values()
    if layout.frontmatter_glob_key
]


def expand_rule_template(text: str, layers: dict[str, list[str]]) -> str:
    """Expand any `<key>_template: layers.<k>` directive in a rule file's
    frontmatter.

    Handles both supported schemas:
      - `paths_template:`   → writes `paths:`   (list)        — claude-code
      - `applyTo_template:` → writes `applyTo:` (comma-string) — copilot

    Files with no template directive come through unchanged. Files where
    the template resolves to non-empty layer hints get the output key
    replaced; empty layer hints leave any existing fallback intact.
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

    changed = False
    for template_key, output_key, kind in _TEMPLATE_SCHEMAS:
        ref = fm.get(template_key)
        if not isinstance(ref, str):
            continue
        globs = _expand_template_ref(ref, layers)
        fm.pop(template_key, None)
        changed = True
        if not globs:
            continue  # fallback (existing `paths:` / `applyTo:`) survives
        if kind == "list":
            fm[output_key] = globs
        else:  # "comma-string"
            fm[output_key] = ",".join(globs)

    if not changed:
        return text

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
    layout = AGENT_LAYOUTS.get(agent)
    if layout is None or layout.rules_dir is None:
        return 0
    rules_root = target / layout.rules_dir
    if not rules_root.is_dir():
        return 0
    modified = 0
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
