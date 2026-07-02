#!/usr/bin/env python3
# Copyright 2026 Accelerated Innovation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
"""Per-agent on-disk layout — the single owner of where each agent's files land.

Kernel leaf module (imports nothing internal, like cli/paths.py) so commands
and domain modules depend on it inward without cycles.

Boundary: agents/<agent>/manifest.json owns *what installs*. This table owns
the derived facts commands need *after* install — where the instruction file
and rules live, and how rule frontmatter scopes globs. Consumers: doctor
(D001 glob resolution), calibrate + setup_review (review paths), and
rule_templating (template expansion).

Codex has no glob-scoped rules dir (placement of nested AGENTS.md files IS its
rule scope), so its rules/glob fields are None — consumers skip on that rather
than dispatching on the agent name.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class AgentLayout:
    """One agent's file-layout facts. All paths are target-relative strings."""

    instruction_file: str
    rules_dir: str | None
    rules_glob: str | None
    frontmatter_glob_key: str | None
    glob_value_shape: Literal["list", "comma-string"] | None


AGENT_LAYOUTS: dict[str, AgentLayout] = {
    "claude-code": AgentLayout(
        instruction_file="CLAUDE.md",
        rules_dir=".claude/rules",
        rules_glob=".claude/rules/*.md",
        frontmatter_glob_key="paths",
        glob_value_shape="list",
    ),
    "copilot": AgentLayout(
        instruction_file=".github/copilot-instructions.md",
        rules_dir=".github/instructions",
        rules_glob=".github/instructions/*.instructions.md",
        frontmatter_glob_key="applyTo",
        glob_value_shape="comma-string",
    ),
    "codex": AgentLayout(
        instruction_file="AGENTS.md",
        rules_dir=None,
        rules_glob=None,
        frontmatter_glob_key=None,
        glob_value_shape=None,
    ),
}
