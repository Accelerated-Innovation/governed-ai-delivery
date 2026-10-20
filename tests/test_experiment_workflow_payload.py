"""Agent payload for the experiment-aware feature workflow (Phase A Increment 4).

Templates, starters, skills, rules and entry instructions must guide all
three agents through: preflight → experiment only when needed → reassessment
→ strict completion, with an explicit `experiment-required` outcome and a short
path for established boundaries. Backend API/CLI (L4/L5) and data only; UI is
a separate increment.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest

from cli.experiment_store import assess_feature
from cli.experiments import parse_preflight_outcome

REPO = Path(__file__).resolve().parents[1]
AGENTS = ("claude-code", "codex", "copilot")
ENTRY_DIRS = {"claude-code": "claude-md", "codex": "agents-md", "copilot": "copilot-instructions"}
ENTRY_DOCS = ("l4-backend-api", "l4-backend-cli", "l4-data", "l5-backend-api", "l5-backend-cli")
SPEC_COMPLIANCE = {
    "claude-code": "rules/generic/spec-compliance.md",
    "codex": "rules/generic/spec-compliance.md",
    "copilot": "instructions/generic/spec-compliance.instructions.md",
}
STRICT = "govkit validate --target . --strict"


def skill(agent: str, name: str) -> str:
    return (REPO / "agents" / agent / "skills" / "backend" / name / "SKILL.md").read_text(
        encoding="utf-8"
    )


def section(text: str, heading: str) -> str:
    """The body under `heading` up to the next heading of the same or higher level."""
    level = len(heading) - len(heading.lstrip("#"))
    start = text.index(heading)
    rest = text[start + len(heading):]
    stop = re.search(rf"^#{{1,{level}}} ", rest, re.MULTILINE)
    return heading + (rest[: stop.start()] if stop else rest)


def normalized(text: str) -> str:
    return re.sub(r"[/$](govkit-)", r"@\1", text)


@pytest.mark.parametrize(
    ("name", "heading"),
    [
        ("govkit-architecture-preflight", "## 6.5 Uncertainty Classification and Outcome"),
        ("govkit-spec-planning", "## Preflight outcome"),
        ("govkit-implementation-plan", "### Experiments, Reassessment and Completion"),
    ],
)
def test_new_skill_sections_are_identical_across_agents(name, heading):
    bodies = {agent: normalized(section(skill(agent, name), heading)) for agent in AGENTS}
    assert len(set(bodies.values())) == 1, sorted(bodies)


def test_preflight_skill_classifies_uncertainty_and_records_one_outcome():
    body = section(
        skill("claude-code", "govkit-architecture-preflight"),
        "## 6.5 Uncertainty Classification and Outcome",
    )
    for phrase in (
        "experiment-required",
        "approved-for-planning",
        "preflight_outcome:",
        "governance/schemas/experiment-set.schema.json",
        "needs no experiment",
        "cannot excuse",
        "Do not label an untested design approved",
        "experiments do not change accepted requirements",
        "relies_on",
        STRICT,
    ):
        assert phrase in body, phrase
    assert parse_preflight_outcome(body)["status"] == "experiment-required"


def test_preflight_skill_still_writes_the_report_after_the_outcome():
    text = skill("claude-code", "govkit-architecture-preflight")
    assert text.index("## 6.5 Uncertainty") < text.index("Write this report to")


def test_genai_preflight_uses_the_shared_outcome_vocabulary():
    for agent in AGENTS:
        output = section(skill(agent, "govkit-genai-preflight"), "## Output")
        assert "experiment-required" in output and "preflight_outcome" in output, agent


def test_spec_planning_plans_only_experiments_while_required():
    body = section(skill("claude-code", "govkit-spec-planning"), "## Preflight outcome")
    for phrase in ("experiment-required", "only the experiment increments", "adr-required",
                   "blocked", "Do not reverse"):
        assert phrase in body, phrase


def test_implementation_plan_reassesses_and_completes_strictly():
    body = section(
        skill("claude-code", "govkit-implementation-plan"),
        "### Experiments, Reassessment and Completion",
    )
    for phrase in ("EXP-", "permitted effects", "reassess", "narrow-supported-behavior", STRICT):
        assert phrase in body, phrase


@pytest.mark.parametrize("agent", AGENTS)
def test_spec_compliance_blocks_completion_on_unresolved_outcomes(agent):
    text = (REPO / "agents" / agent / SPEC_COMPLIANCE[agent]).read_text(encoding="utf-8")
    assert "preflight_outcome" in text and "experiment-required" in text and STRICT in text


@pytest.mark.parametrize("agent", AGENTS)
@pytest.mark.parametrize("doc", ENTRY_DOCS)
def test_entry_instructions_route_experiments_and_strict_completion(agent, doc):
    text = (REPO / "agents" / agent / ENTRY_DIRS[agent] / f"{doc}.md").read_text(encoding="utf-8")
    assert "experiment-required" in text, (agent, doc)
    assert STRICT in text, (agent, doc)


@pytest.mark.parametrize(
    "template", ["architecture_preflight.md", "l5-architecture-preflight.md"]
)
def test_preflight_templates_record_uncertainty_and_outcome(template):
    text = (REPO / "governance" / "backend" / "templates" / template).read_text(encoding="utf-8")
    assert "## 8.5 Architecture Uncertainty and Experiments" in text
    outcome = parse_preflight_outcome(text)
    assert outcome == {"status": "blocked", "reason": "Preflight not yet completed."}
    assert "Experiment required" in text


@pytest.mark.parametrize("template", ["plan.md", "l5-plan.md"])
def test_plan_templates_cover_experiments_and_reassessment(template):
    text = (REPO / "governance" / "backend" / "templates" / template).read_text(encoding="utf-8")
    assert "## Reassessment and Completion" in text
    assert "experiment-required" in text and STRICT in text


STARTERS = ("starter_backend", "starter_backend_l5", "starter_cli", "starter_cli_l5",
            "starter_data")


@pytest.mark.parametrize("starter", STARTERS)
def test_starters_ship_an_honest_unfinished_outcome(tmp_path, starter):
    """A copied starter blocks completion until its preflight is done: valid,
    so CI's non-strict check passes, but outstanding under --strict."""
    source = REPO / "features" / starter
    assert parse_preflight_outcome(
        (source / "architecture_preflight.md").read_text(encoding="utf-8")
    ) == {"status": "blocked", "reason": "Preflight not yet completed."}
    shutil.copytree(source, tmp_path / "features" / "new-feature")
    result = assess_feature(tmp_path, tmp_path / "features" / "new-feature")
    assert [(f.code, f.severity) for f in result.assessment.findings] == [
        ("preflight-blocked", "outstanding")
    ]


def test_data_starter_mirrors_the_new_skill_section():
    text = (REPO / "features" / "starter_data" / "architecture_preflight.md").read_text(
        encoding="utf-8"
    )
    assert "## 6.5 Uncertainty Classification and Outcome" in text
