#!/usr/bin/env python3
# Copyright 2026 Accelerated Innovation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
"""govkit calibrate — guided review of installed governance.

PR 5. Walks the 9-step checklist from plan Section 7. Two modes:

  - interactive (default): prompts the user per step, accepts a decision
  - --non-interactive: emits the checklist as a markdown todo file (for
    CI bootstraps and new repos where the team fills it in later)

Decisions land in `.govkit/marker.json` under `calibration.decisions[]`,
and per-assumption `calibrated_at` / `calibrated_against_overlay_version`
fields are set so doctor's D010 can age them out properly.

Monorepo behavior matches doctor (per A9): when --target is omitted and
cwd contains multiple `.govkit/` installs, calibrate processes each.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .agent_layout import AGENT_LAYOUTS
from .marker import read_govkit_marker, write_govkit_marker
from .stack_select import STACK_ID_ASSUMPTION

# ---------------------------------------------------------------------------
# Step + decision model
# ---------------------------------------------------------------------------


@dataclass
class CalibrationStep:
    """One reviewable item in the checklist.

    `assumption_id` links the step to a marker.assumptions[] entry so the
    decision flow can flip review_required + stamp calibrated_at for the
    right assumption when the user confirms.
    """
    id: str
    title: str
    description: str
    file_path: str | None
    installed_summary: str
    detected_value: str | None
    suggestion: str
    assumption_id: str | None = None


@dataclass
class CalibrationDecision:
    step_id: str
    decided_at: str
    decision: str  # "confirm" | "modify" | "skip" | "needs-review"
    note: str = ""


@dataclass
class CalibrationResult:
    target: Path
    steps: list[CalibrationStep]
    decisions: list[CalibrationDecision] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Type helpers (mirror cli/setup_review.py conventions)
# ---------------------------------------------------------------------------


def _architecture_root(type_value: str) -> str:
    if type_value in ("ui-react", "ui-angular"):
        return "docs/ui/architecture"
    if type_value == "data":
        return "docs/data/architecture"
    return "docs/backend/architecture"


# ---------------------------------------------------------------------------
# Checklist builder
# ---------------------------------------------------------------------------


def build_checklist(target: Path, marker: dict) -> list[CalibrationStep]:
    """Build the 9-step calibration checklist for an install.

    Steps are agent- and type-aware: backend installs get docs/backend/...,
    UI installs get docs/ui/..., and agent paths follow each agent's
    convention. Detection seeds detected_value where applicable so the user
    sees what govkit inferred about their repo.
    """
    from .detect import build_profile, infer_stack

    agent = marker.get("agent", "claude-code")
    options = marker.get("options", {})
    type_value = options.get("type", "api")
    arch = _architecture_root(type_value)
    layout = AGENT_LAYOUTS.get(agent, AGENT_LAYOUTS["claude-code"])
    # Codex has no glob-scoped rules dir; its nested AGENTS.md files are the
    # reviewable rules surface, so the step points there instead.
    rules_path = layout.rules_dir or layout.instruction_file
    stack = marker.get("stack") or {}

    profile = build_profile(target)
    inferred_stack, inferred_conf = infer_stack(profile)

    steps: list[CalibrationStep] = []

    # 1. Marker — confirm agent/level/type/stack/ci
    steps.append(CalibrationStep(
        id="step.marker",
        title="Installed configuration",
        description="Confirm agent, level, type, stack, and CI selection.",
        file_path=".govkit/marker.json",
        installed_summary=(
            f"agent={agent} level={marker.get('level')} "
            f"type={type_value} ci={options.get('ci')} "
            f"stack={(stack or {}).get('id', '(none)')}"
        ),
        detected_value=(
            f"inferred_stack={inferred_stack} ({inferred_conf})"
            if inferred_stack else None
        ),
        suggestion=(
            "If the values above don't match your repo, re-run `govkit apply` "
            "with the right flags. The stack can be swapped with "
            "`govkit stack apply <id>` without a full re-apply."
        ),
        assumption_id=STACK_ID_ASSUMPTION,
    ))

    # 2. TECH_STACK.md
    steps.append(CalibrationStep(
        id="step.tech_stack",
        title="Tech stack",
        description="Language version, frameworks, persistence, messaging, observability.",
        file_path=f"{arch}/TECH_STACK.md",
        installed_summary=(
            f"baseline {stack.get('id', '(none)')}@{stack.get('version', '?')}"
        ),
        detected_value=(
            ", ".join(profile.detected_languages + profile.detected_frameworks)
            or None
        ),
        suggestion=(
            "Confirm the language version, framework choice, and approved "
            "library versions match your repo. If level < 5, strip any "
            "LLM-specific sections (LiteLLM, DeepEval, NeMo Guardrails)."
        ),
        assumption_id=STACK_ID_ASSUMPTION,
    ))

    # 3. BOUNDARIES.md
    if type_value == "data":
        boundaries_suggestion = (
            "Confirm the layering matches your dbt project. The dbt-layered "
            "default is staging → intermediate → marts. Teams using medallion "
            "(bronze/silver/gold) edit layer names in BOUNDARIES.md and "
            "skill_context.yaml. Source freshness contracts live in "
            "PIPELINE_CONTRACT.md."
        )
    else:
        boundaries_suggestion = (
            "Confirm the architecture style matches your folder layout. "
            "If your repo uses clean (Application/Domain/Infrastructure) or "
            "layered (Controllers/Services/Repositories), update layer names "
            "and folder mappings in BOUNDARIES.md."
        )
    steps.append(CalibrationStep(
        id="step.boundaries",
        title="Architecture boundaries",
        description="Architecture style (hexagonal/clean/layered/dbt-layered/...) and folder mappings.",
        file_path=f"{arch}/BOUNDARIES.md",
        installed_summary="hexagonal (default for the python-fastapi baseline)",
        detected_value=(
            ", ".join(profile.detected_architecture_signals) or None
        ),
        suggestion=boundaries_suggestion,
        assumption_id="architecture.style",
    ))

    # 4. API / query conventions
    if type_value == "data":
        steps.append(CalibrationStep(
            id="step.query_conventions",
            title="Query conventions",
            description="SQL style, CTE skeleton, model naming, source freshness policy.",
            file_path=f"{arch}/QUERY_CONVENTIONS.md",
            installed_summary="dbt CTE skeleton + `stg_<source>__<table>` naming (overlay default)",
            detected_value=None,
            suggestion=(
                "Confirm SQL style (CTE skeleton vs flat), naming pattern, "
                "source freshness thresholds, and incremental materialization "
                "policy. Edit QUERY_CONVENTIONS.md to match the team's house style."
            ),
            assumption_id=None,
        ))
    else:
        steps.append(CalibrationStep(
            id="step.api_conventions",
            title="API conventions",
            description="Route style (REST/GraphQL/gRPC), versioning, error envelope.",
            file_path=f"{arch}/API_CONVENTIONS.md",
            installed_summary="REST + JSON (baseline default)",
            detected_value=profile.detected_api_style,
            suggestion=(
                "Confirm route style, versioning policy (URI vs header), and "
                "error envelope format. Adjust API_CONVENTIONS.md if your repo "
                "differs from the baseline."
            ),
            assumption_id=None,
        ))

    # 5. TESTING.md
    if type_value == "data":
        testing_suggestion = (
            "Confirm dbt schema tests (unique / not_null / relationships), "
            "custom singular tests, and source freshness thresholds. If your "
            "team does not write BDD scenarios for data freshness/quality, set "
            "the BDD policy to 'none' in TESTING.md."
        )
    else:
        testing_suggestion = (
            "Confirm unit / mocking / BDD frameworks. If your team does not "
            "practise BDD, set the BDD framework to 'none' in TESTING.md "
            "and add `bdd: none` to .govkit/marker.json's options when "
            "L4 validation arrives."
        )
    steps.append(CalibrationStep(
        id="step.testing",
        title="Testing framework + BDD policy",
        description="Unit framework, mocking, BDD framework (or 'none' to disable L4 BDD gate).",
        file_path=f"{arch}/TESTING.md",
        installed_summary=(
            f"per stack overlay {stack.get('id', '(none)')}"
        ),
        detected_value=(
            ", ".join(profile.detected_test_packages) or None
        ),
        suggestion=testing_suggestion,
        assumption_id="testing.bdd",
    ))

    # 6. Top-level agent guidance
    steps.append(CalibrationStep(
        id="step.agent_instructions",
        title=f"Top-level agent guidance ({layout.instruction_file})",
        description="Confirm references to architecture docs are accurate.",
        file_path=layout.instruction_file,
        installed_summary=f"agent={agent} baseline govkit@{marker.get('version', '?')}",
        detected_value=None,
        suggestion=(
            "Skim this file end-to-end. Verify the citations to architecture "
            "docs (TECH_STACK.md, BOUNDARIES.md, ...) point at files that "
            "actually exist and reflect your project."
        ),
        assumption_id=None,
    ))

    # 7. Rules / instructions tree
    steps.append(CalibrationStep(
        id="step.rules",
        title=f"Agent rules ({rules_path})",
        description="Per-rule globs/applyTo patterns must match your folder layout.",
        file_path=rules_path,
        installed_summary=(
            f"agent={agent} — rules ship with the baseline; "
            "`govkit doctor` D001 flags rules whose globs resolve to zero files"
        ),
        detected_value=(
            ", ".join(profile.detected_architecture_signals) or None
        ),
        suggestion=(
            "Run `govkit doctor --target <this install>` to see any D001 "
            "findings. Fix or remove rules whose globs don't match your repo."
        ),
        assumption_id=None,
    ))

    # 8. CI gates
    steps.append(CalibrationStep(
        id="step.ci",
        title="CI quality gates",
        description="Confirm gate selection matches team practice.",
        file_path=f"ci/{options.get('ci', 'github')}",
        installed_summary=f"ci={options.get('ci')}",
        detected_value=(
            ", ".join(profile.detected_ci) or None
        ),
        suggestion=(
            "Confirm the marker's `ci` value matches the CI platform actually "
            "running in this repo. `govkit doctor` D003/D004 surface mismatches."
        ),
        assumption_id="ci.platform",
    ))

    # 9. Skill context
    steps.append(CalibrationStep(
        id="step.skill_context",
        title="Skill context",
        description="Facts skills will read (architecture style, stack, layer mappings).",
        file_path=".govkit/skill_context.yaml",
        installed_summary="regenerated when calibration completes",
        detected_value=None,
        suggestion=(
            "Final review — these are the facts skills (architecture-preflight, "
            "spec-planning, implementation-plan) consult when generating "
            "guidance. Confirm they reflect the decisions you made above."
        ),
        assumption_id=None,
    ))

    return steps


# ---------------------------------------------------------------------------
# Non-interactive renderer (markdown checklist file)
# ---------------------------------------------------------------------------


def render_checklist_markdown(steps: list[CalibrationStep]) -> str:
    """Render the checklist as a standalone markdown file (non-interactive mode).

    Output is plain markdown so it can live alongside GOVKIT_SETUP_REVIEW.md
    or be pasted into an issue/PR for team review.
    """
    now = datetime.now(timezone.utc).isoformat()
    lines = [
        "# GovKit Calibration Checklist",
        "",
        f"_Generated by `govkit calibrate --non-interactive` on {now}._",
        "",
        "Walk this list with the team. For each step, confirm or modify the "
        "installed value to match your repo. When done, set "
        "`review_required: false` on the matching assumption in "
        "`.govkit/marker.json` and add a calibration decision under "
        "`calibration.decisions[]`.",
        "",
    ]
    for i, step in enumerate(steps, start=1):
        lines.append(f"## {i}. {step.title}")
        lines.append("")
        if step.file_path:
            lines.append(f"**File:** `{step.file_path}`")
            lines.append("")
        lines.append(f"_{step.description}_")
        lines.append("")
        lines.append(f"- **Installed:** {step.installed_summary}")
        if step.detected_value:
            lines.append(f"- **Detected:** {step.detected_value}")
        if step.assumption_id:
            lines.append(f"- **Assumption id:** `{step.assumption_id}`")
        lines.append("")
        lines.append(f"**Action:** {step.suggestion}")
        lines.append("")
        lines.append("- [ ] Reviewed")
        lines.append("- [ ] Updated (if needed)")
        lines.append("- [ ] Confirmed `assumption.review_required = false` (if applicable)")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI dispatch (mirrors doctor's monorepo handling per A9)
# ---------------------------------------------------------------------------


def _resolve_targets(args: argparse.Namespace) -> list[Path]:
    """Return the list of install targets to calibrate.

    Mirrors doctor's A9 monorepo behavior — explicit --target wins, else
    auto-discover under cwd. Exits 1 with a helpful message when nothing is
    found.
    """
    from .doctor import discover_install_targets

    target_arg = getattr(args, "target", None)
    if target_arg:
        return [Path(target_arg).resolve()]
    targets = discover_install_targets(Path.cwd())
    if not targets:
        print(
            "Error: no .govkit marker found under the current directory. "
            "Run `govkit apply` first, or pass `--target <path>` to scope "
            "to a specific install.",
            file=sys.stderr,
        )
        sys.exit(1)
    return targets


def _filter_steps_by_only(
    steps: list[CalibrationStep], only: str | None,
) -> list[CalibrationStep]:
    """Apply --only filter (matches either full step id or the trailing
    component after the dot)."""
    if not only:
        return steps
    return [s for s in steps if s.id == only or s.id.endswith("." + only)]


def _calibrate_one(target: Path, args: argparse.Namespace, multi: bool) -> None:
    """Calibrate a single target. Returns early on missing marker / empty
    --only filter without raising so the monorepo loop can continue."""
    marker = read_govkit_marker(target)
    if marker is None:
        print(f"Error: no .govkit/marker.json at {target}", file=sys.stderr)
        if not multi:
            sys.exit(1)
        return

    if multi:
        try:
            rel = target.relative_to(Path.cwd())
        except ValueError:
            rel = target
        print(f"\n=== {rel} ===")

    steps = _filter_steps_by_only(
        build_checklist(target, marker),
        getattr(args, "only", None),
    )
    if not steps:
        print(
            f"  no step matching --only={getattr(args, 'only', None)!r}; skipping",
            file=sys.stderr,
        )
        return

    if getattr(args, "non_interactive", False):
        _run_non_interactive(target, steps)
    else:
        _run_interactive(target, marker, steps)


def cmd_calibrate(args: argparse.Namespace) -> None:
    """`govkit calibrate` — guided review of installed governance.

    Monorepo behavior matches doctor: with no --target, auto-discover all
    `.govkit/` installs under cwd and process each one.
    """
    targets = _resolve_targets(args)
    multi = len(targets) > 1
    for target in targets:
        _calibrate_one(target, args, multi)


def register(subparsers) -> None:
    """Register the `calibrate` subcommand and its arguments."""
    p = subparsers.add_parser(
        "calibrate",
        help="Guided review of installed governance. Walks the team "
             "through the 9-step checklist from plan Section 7.",
    )
    p.add_argument(
        "--target", default=None,
        help="Path to the install root (defaults to scanning cwd for .govkit/ "
             "markers; finds nested installs in monorepos)",
    )
    p.add_argument(
        "--non-interactive", action="store_true", dest="non_interactive",
        help="Skip prompts and write GOVKIT_CALIBRATION_CHECKLIST.md as a "
             "todo file. Useful in CI bootstraps and for new repos the team "
             "will calibrate later.",
    )
    p.add_argument(
        "--only", default=None,
        help="Run only the named step (e.g. 'tech_stack', 'rules'). Useful "
             "for revisiting a single decision without walking the whole list.",
    )
    p.set_defaults(func=cmd_calibrate)


def _run_non_interactive(target: Path, steps: list[CalibrationStep]) -> None:
    """Write the checklist as a markdown todo file at the target root."""
    body = render_checklist_markdown(steps)
    out_path = target / "GOVKIT_CALIBRATION_CHECKLIST.md"
    out_path.write_text(body, encoding="utf-8")
    print(f"  calibration checklist written: {out_path}")
    print(f"  {len(steps)} step(s) — walk this with the team, then update "
          ".govkit/marker.json with calibration decisions.")
    # Refresh derived files. No marker mutation in non-interactive mode —
    # these are pure re-derivations from the existing marker + repo state.
    from .setup_review import write_setup_review
    from .skill_context import write_skill_context
    refreshed = read_govkit_marker(target)
    if refreshed is not None:
        write_setup_review(target, refreshed)
        write_skill_context(target, refreshed)


_PROMPT_HELP = (
    "  [enter/y]=confirm  [n]=needs-review  [s]=skip  [q]=quit without saving"
)


def _prompt_step(step: CalibrationStep, index: int, total: int) -> str:
    """Render one step and read the user's decision letter from stdin.

    Returns one of "confirm", "needs-review", "skip", "quit".
    """
    print("")
    print(f"  [{index}/{total}] {step.title}")
    if step.file_path:
        print(f"        file:      {step.file_path}")
    print(f"        installed: {step.installed_summary}")
    if step.detected_value:
        print(f"        detected:  {step.detected_value}")
    print(f"        suggest:   {step.suggestion}")
    print(_PROMPT_HELP)
    raw = input("  decision: ").strip().lower()
    if raw in ("", "y", "yes"):
        return "confirm"
    if raw in ("n", "no", "needs-review"):
        return "needs-review"
    if raw == "s" or raw == "skip":
        return "skip"
    if raw == "q" or raw == "quit":
        return "quit"
    print("  unrecognised — treating as needs-review.")
    return "needs-review"


def _decisions_resolve_assumption(
    decisions: list[CalibrationDecision],
    assumption_id: str,
    steps_by_id: dict[str, CalibrationStep],
) -> bool:
    """True if calibration decisions collectively resolve an assumption.

    Several steps may link to the same assumption_id (e.g. both step.marker
    and step.tech_stack reference `stack.id`). The team must confirm on
    every linked step *and* never flag needs-review on any of them; one
    needs-review keeps the assumption open even if other linked steps were
    confirmed. Skips are neutral (don't resolve, don't block).
    """
    linked = [
        d for d in decisions
        if (s := steps_by_id.get(d.step_id)) and s.assumption_id == assumption_id
    ]
    if not linked:
        return False
    if any(d.decision == "needs-review" for d in linked):
        return False
    return any(d.decision == "confirm" for d in linked)


def _apply_decisions(
    marker: dict,
    decisions: list[CalibrationDecision],
    steps_by_id: dict[str, CalibrationStep],
    now_iso: str,
) -> dict:
    """Fold decisions into a copy of the marker.

    For each assumption referenced by any step, apply the aggregate decision
    (per `_decisions_resolve_assumption`): stamp calibrated_at +
    calibrated_against_overlay_version and clear review_required if and
    only if the team confirmed without any needs-review flags.
    """
    overlay_version = (marker.get("stack") or {}).get("version")
    updated = dict(marker)

    # Collect every assumption_id referenced by the walked steps.
    touched_assumption_ids = {
        s.assumption_id for s in steps_by_id.values() if s.assumption_id
    }

    assumptions = [dict(a) for a in marker.get("assumptions") or []]
    for assumption in assumptions:
        aid = assumption.get("id")
        if aid not in touched_assumption_ids:
            continue
        if _decisions_resolve_assumption(decisions, aid, steps_by_id):
            assumption["review_required"] = False
            assumption["calibrated_at"] = now_iso
            if overlay_version is not None:
                assumption["calibrated_against_overlay_version"] = overlay_version
    updated["assumptions"] = assumptions

    cal = dict(marker.get("calibration") or {})
    cal_decisions = list(cal.get("decisions") or [])
    cal_decisions.extend([
        {
            "step_id": d.step_id,
            "decided_at": d.decided_at,
            "decision": d.decision,
            "note": d.note,
        }
        for d in decisions
    ])
    cal["decisions"] = cal_decisions
    cal["completed_at"] = now_iso
    updated["calibration"] = cal
    return updated


def _run_interactive(target: Path, marker: dict, steps: list[CalibrationStep]) -> None:
    """Walk each step, collect a decision, then persist."""
    print(f"\nCalibrating {target}")
    print(f"  {len(steps)} step(s) to walk. {_PROMPT_HELP.strip()}\n")

    decisions: list[CalibrationDecision] = []
    quit_early = False
    for i, step in enumerate(steps, start=1):
        choice = _prompt_step(step, i, len(steps))
        if choice == "quit":
            print("  quit — no marker update.")
            quit_early = True
            break
        decisions.append(CalibrationDecision(
            step_id=step.id,
            decided_at=datetime.now(timezone.utc).isoformat(),
            decision=choice,
        ))

    if quit_early or not decisions:
        return

    now_iso = datetime.now(timezone.utc).isoformat()
    steps_by_id = {s.id: s for s in steps}
    updated = _apply_decisions(marker, decisions, steps_by_id, now_iso)

    write_govkit_marker(
        target,
        agent=updated.get("agent", "claude-code"),
        level=updated.get("level", "4"),
        options=updated.get("options", {}),
        stack=updated.get("stack"),
        assumptions=updated.get("assumptions") or [],
        calibration=updated.get("calibration"),
        # Preserve the original applied_at — calibrate is not a re-install.
        # Bumping it would silently un-protect files edited before calibration.
        applied_at=updated.get("applied_at"),
    )

    # Regenerate skill_context.yaml so skills (PR 6b/c) see fresh facts.
    from .skill_context import write_skill_context
    write_skill_context(target, updated)

    # Refresh GOVKIT_SETUP_REVIEW.md so the calibration completion + decision
    # tally are visible alongside the assumptions block.
    from .setup_review import write_setup_review
    write_setup_review(target, updated)

    summary = {"confirm": 0, "needs-review": 0, "skip": 0}
    for d in decisions:
        summary[d.decision] = summary.get(d.decision, 0) + 1
    print(
        f"\n  calibration recorded: "
        f"{summary['confirm']} confirmed, "
        f"{summary['needs-review']} needs-review, "
        f"{summary['skip']} skipped."
    )
