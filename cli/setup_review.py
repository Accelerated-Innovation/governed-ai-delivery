#!/usr/bin/env python3
# Copyright 2026 Accelerated Innovation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
"""GOVKIT_SETUP_REVIEW.md writer + post-install Review Checklist printer.

PR 1 / Chunk E. The setup review file is the team's starting point for
adapting the installed governance to their repo. PR 3 (detectors) and
PR 5 (calibrate) enrich the per-assumption details; PR 1 ships the file
shape and a generic checklist so the discipline starts on day one.
"""

from pathlib import Path


def _agent_doc_paths(agent: str) -> dict[str, str]:
    """Return the (label, path) pairs an agent installs at the top level.

    Path conventions differ per agent (CLAUDE.md vs .github/copilot-instructions.md
    vs AGENTS.md). This keeps the review file's references accurate per install.
    """
    if agent == "copilot":
        return {
            "agent_instruction_file": ".github/copilot-instructions.md",
            "rules_dir": ".github/instructions/",
            "rules_glob": ".github/instructions/*.instructions.md",
        }
    if agent == "codex":
        return {
            "agent_instruction_file": "AGENTS.md",
            "rules_dir": "(nested AGENTS.md per layer)",
            "rules_glob": "AGENTS.md",
        }
    # claude-code (default)
    return {
        "agent_instruction_file": "CLAUDE.md",
        "rules_dir": ".claude/rules/",
        "rules_glob": ".claude/rules/*.md",
    }


def _architecture_root(type_value: str) -> str:
    """Map project type to its docs architecture root."""
    if type_value in ("ui-react", "ui-angular"):
        return "docs/ui/architecture"
    return "docs/backend/architecture"


def _format_assumption_block(assumptions: list) -> str:
    """Format the Assumptions section. Splits into 'needs review' vs 'declared'
    so the review file surfaces blockers first.
    """
    if not assumptions:
        return (
            "_No assumptions have been recorded yet. Future releases ship a "
            "`govkit doctor` command that detects repo signals and a "
            "`govkit calibrate` command that walks you through the review._\n"
        )

    needs_review = [a for a in assumptions if a.get("review_required")]
    declared = [a for a in assumptions if not a.get("review_required")]

    lines: list[str] = []
    if needs_review:
        lines.append("### Needs your attention\n")
        for a in needs_review:
            warning = a.get("warning_message") or ""
            files = ", ".join(a.get("files_affected") or []) or "(none)"
            lines.append(f"- **{a['id']}** = `{a['value']}` (source: {a.get('source', 'unknown')})")
            if warning:
                lines.append(f"  - {warning}")
            lines.append(f"  - Files affected: {files}")
        lines.append("")
    if declared:
        lines.append("### Declared (no action required)\n")
        for a in declared:
            evidence = ", ".join(a.get("evidence") or []) or "(none)"
            lines.append(
                f"- **{a['id']}** = `{a['value']}` "
                f"(source: {a.get('source', 'unknown')}, evidence: {evidence})"
            )
        lines.append("")
    return "\n".join(lines)


def _format_review_checklist(agent: str, type_value: str) -> str:
    """Generic per-install review checklist. Path conventions vary by
    agent/type; the items themselves are stable for PR 1."""
    arch = _architecture_root(type_value)
    paths = _agent_doc_paths(agent)
    items = [
        (f"{arch}/TECH_STACK.md",
         "Confirm the language, framework, persistence, messaging, observability, "
         "and approved library versions match your repo."),
        (f"{arch}/BOUNDARIES.md",
         "Confirm the architecture style (hexagonal / clean / layered / vertical-slice) "
         "and the folder mappings (which folders are inbound, outbound, domain)."),
        (f"{arch}/API_CONVENTIONS.md",
         "Confirm REST/GraphQL/gRPC conventions, versioning policy, and error envelope."),
        (f"{arch}/TESTING.md",
         "Confirm the unit/BDD framework, mocking library, and any framework-as-L4-gate "
         "decisions (set BDD to 'none' if your team does not practise BDD)."),
        (paths["agent_instruction_file"],
         "Top-level agent guidance. Confirm references to architecture docs are accurate."),
        (paths["rules_dir"],
         f"Agent rules ({paths['rules_glob']}). Confirm globs/applyTo patterns match your "
         "folder layout — rules that don't match anything provide no guidance."),
    ]
    lines = ["Please read these files before relying on the installed governance:\n"]
    for i, (path, note) in enumerate(items, start=1):
        lines.append(f"{i}. **{path}**\n   {note}")
    return "\n".join(lines) + "\n"


def write_setup_review(target: Path, marker: dict) -> None:
    """Write GOVKIT_SETUP_REVIEW.md at the target root.

    The file is regenerated on every `apply` / `upgrade` / `stack apply` so
    stale review notes never bleed across runs. Team-authored notes belong
    in separate files (e.g., ADRs), not in this file.
    """
    agent = marker.get("agent", "claude-code")
    options = marker.get("options", {})
    type_value = options.get("type", "api")
    ci = options.get("ci", "github")
    level = marker.get("level", "?")
    govkit_version = marker.get("version", "unknown")
    applied_at = marker.get("applied_at", "unknown")
    stack = marker.get("stack")
    assumptions = marker.get("assumptions", []) or []

    stack_line = (
        f"`{stack.get('id')}@{stack.get('version', '?')}` ({stack.get('display_name', '')})"
        if stack
        else "_(not yet selected — first-class `--stack` support arrives in a later release; "
             "for now, edit installed docs to match your repo)_"
    )

    body = f"""# GovKit Setup Review

Generated by `govkit apply` / `govkit upgrade` on {applied_at}.

This file lists what was installed and what you should review before relying on
the governance for AI-agent guidance. Regenerated on every install; do not edit
this file — author your notes in ADRs or a separate doc instead.

## What was installed

- **Agent:** `{agent}`
- **Level:** {level}
- **Type:** `{type_value}`
- **CI:** `{ci}`
- **Stack:** {stack_line}
- **GovKit version:** {govkit_version}

## Review checklist

{_format_review_checklist(agent, type_value)}

## Assumptions

{_format_assumption_block(assumptions)}

## Next steps

- After reviewing, edit any docs above to match your repo. GovKit detects your
  edits (via the `govkit:editable` header + file mtime vs. the marker's
  `applied_at`) and refuses to overwrite them on `govkit upgrade` or
  `govkit stack apply`. Use `--force` to override.
- Future releases ship `govkit doctor` (validate fit, surface mismatches) and
  `govkit calibrate` (guided review). See the roadmap in
  `plans/GOVERNANCE_ACCELERATOR_PLAN.md`.
"""
    review_path = target / "GOVKIT_SETUP_REVIEW.md"
    review_path.write_text(body, encoding="utf-8")


def print_review_checklist(target: Path, marker: dict) -> None:
    """Print the post-install Review Checklist banner to stdout.

    Condensed version of the GOVKIT_SETUP_REVIEW.md file; meant to be read in
    the terminal at the end of `apply` / `upgrade`. The full review file
    lives at the target root.
    """
    agent = marker.get("agent", "claude-code")
    type_value = marker.get("options", {}).get("type", "api")
    arch = _architecture_root(type_value)
    paths = _agent_doc_paths(agent)
    needs_review_count = sum(
        1 for a in (marker.get("assumptions") or []) if a.get("review_required")
    )

    bar = "-" * 77
    lines = [
        "",
        bar,
        "REVIEW CHECKLIST — please read before relying on installed governance:",
        bar,
        "  See GOVKIT_SETUP_REVIEW.md (just written) for the full checklist.",
        "",
        "  Top items to confirm:",
        f"    1. {arch}/TECH_STACK.md      — language / framework / libraries",
        f"    2. {arch}/BOUNDARIES.md      — architecture style + folder mappings",
        f"    3. {arch}/TESTING.md         — test framework + BDD policy",
        f"    4. {paths['agent_instruction_file']:32s} — top-level agent guidance",
        f"    5. {paths['rules_dir']:32s} — rule globs / applyTo patterns",
    ]
    if needs_review_count:
        lines.append("")
        lines.append(
            f"  {needs_review_count} assumption(s) flagged review_required — see "
            "GOVKIT_SETUP_REVIEW.md → Assumptions."
        )
    lines.append(bar)
    print("\n".join(lines))
