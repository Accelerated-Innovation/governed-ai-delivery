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

from .agent_layout import AGENT_LAYOUTS, AgentLayout


def _layout_for(agent: str) -> AgentLayout:
    """Layout for `agent`, defaulting to claude-code for unknown names so a
    hand-edited marker still yields a readable review file."""
    return AGENT_LAYOUTS.get(agent, AGENT_LAYOUTS["claude-code"])


def _rules_display(layout: AgentLayout) -> tuple[str, str]:
    """Human-readable (rules_dir, rules_glob) for the review file and banner.

    Agents without a glob-scoped rules dir (codex) get descriptive text — a
    presentation concern, so it lives here rather than in the layout table."""
    if layout.rules_dir is None:
        return "(nested AGENTS.md per layer)", layout.instruction_file
    return f"{layout.rules_dir}/", layout.rules_glob


def _architecture_root(type_value: str) -> str:
    """Map project type to its docs architecture root."""
    if type_value in ("ui-react", "ui-angular"):
        return "docs/ui/architecture"
    if type_value == "data":
        return "docs/data/architecture"
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
    layout = _layout_for(agent)
    rules_dir, rules_glob = _rules_display(layout)
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
        (layout.instruction_file,
         "Top-level agent guidance. Confirm references to architecture docs are accurate."),
        (rules_dir,
         f"Agent rules ({rules_glob}). Confirm globs/applyTo patterns match your "
         "folder layout — rules that don't match anything provide no guidance."),
    ]
    lines = ["Please read these files before relying on the installed governance:\n"]
    for i, (path, note) in enumerate(items, start=1):
        lines.append(f"{i}. **{path}**\n   {note}")
    return "\n".join(lines) + "\n"


def _format_calibration_block(calibration: dict | None) -> str:
    """Render the Calibration section: completion status + decision summary."""
    cal = calibration or {}
    completed_at = cal.get("completed_at")
    decisions = cal.get("decisions") or []

    if not completed_at:
        return (
            "_Calibration has not yet been run on this install. When ready, "
            "run `govkit calibrate --target <path>` to walk the review "
            "checklist with the team (use `--non-interactive` to emit a "
            "markdown todo file instead)._\n"
        )

    counts = {"confirm": 0, "needs-review": 0, "skip": 0}
    for d in decisions:
        key = d.get("decision", "")
        counts[key] = counts.get(key, 0) + 1

    return (
        f"- **Last completed:** {completed_at}\n"
        f"- **Decisions recorded:** {len(decisions)} "
        f"({counts['confirm']} confirmed, {counts['needs-review']} needs-review, "
        f"{counts['skip']} skipped)\n"
        "- To revisit a single step, run "
        "`govkit calibrate --only <step_name> --target <path>`.\n"
    )


def write_setup_review(target: Path, marker: dict) -> None:
    """Write GOVKIT_SETUP_REVIEW.md at the target root.

    The file is regenerated on every `apply` / `upgrade` / `stack apply` /
    `calibrate` so stale review notes never bleed across runs. Team-authored
    notes belong in separate files (e.g., ADRs), not in this file.
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
    calibration = marker.get("calibration")

    stack_line = (
        f"`{stack.get('id')}@{stack.get('version', '?')}` ({stack.get('display_name', '')})"
        if stack
        else "_(not yet selected — first-class `--stack` support arrives in a later release; "
             "for now, edit installed docs to match your repo)_"
    )

    body = f"""# GovKit Setup Review

Generated by `govkit apply` / `govkit upgrade` / `govkit calibrate` on {applied_at}.

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

## Calibration

{_format_calibration_block(calibration)}

## Next steps

- After reviewing, edit any docs above to match your repo. GovKit detects your
  edits (via the `govkit:editable` header + file mtime vs. the marker's
  `applied_at`) and refuses to overwrite them on `govkit upgrade` or
  `govkit stack apply`. Use `--force` to override.
- `govkit doctor` validates fit and surfaces mismatches; run it in CI.
- `govkit calibrate` walks the review checklist with the team and records
  each decision in `.govkit/marker.json`.
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
    layout = _layout_for(agent)
    rules_dir, _ = _rules_display(layout)
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
        f"    4. {layout.instruction_file:32s} — top-level agent guidance",
        f"    5. {rules_dir:32s} — rule globs / applyTo patterns",
    ]
    if needs_review_count:
        lines.append("")
        lines.append(
            f"  {needs_review_count} assumption(s) flagged review_required — see "
            "GOVKIT_SETUP_REVIEW.md → Assumptions."
        )
    lines.append(bar)
    print("\n".join(lines))
