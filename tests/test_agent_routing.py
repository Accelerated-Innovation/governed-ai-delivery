"""LLM, SOAA and multi-agent routing in the agent payload (Phase A Increment 8).

The three layers route independently in all three hosts: LLM contracts load for
model use, SOAA guidance loads for governed runtime skills even with one agent,
and topology stays tied to `multi_agent: true`. Instructions find extension
resources in either install root (legacy `extensions/` or declarative
`.govkit/packs/`).
"""

from __future__ import annotations

import re
import textwrap
from pathlib import Path

import pytest

from cli.validate import check_agent_topology_exists, check_agent_topology_sections

REPO = Path(__file__).resolve().parents[1]
AGENTS = ("claude-code", "codex", "copilot")
ENTRY_DIRS = {"claude-code": "claude-md", "codex": "agents-md", "copilot": "copilot-instructions"}
L5_BACKEND = ("l5-backend-api", "l5-backend-cli")

ROOT_NOTE = (
    "Find installed extensions with `govkit extension list --installed --target .`, which "
    "prints each extension root: `extensions/<id>/` (legacy) or `.govkit/packs/<id>/<digest>/` "
    "(declarative). Read a path written as `extensions/<id>/<path>` under that root. Stop if "
    "the listing reports a conflict or exits non-zero"
)
LLM_TRIGGER = (
    "If the feature calls language models (`mode: llm`), confirm `llm-application` is "
    "installed. If it is missing, stop and request "
    "`govkit extension add llm-application --target .`"
)
SOAA_TRIGGER = (
    "If the feature uses governed runtime skills, an adaptive agent loop, or their control "
    "boundaries, including a single agent with fixed skills, read "
    "`extensions/skill-oriented-agent-architecture/docs/backend/architecture/"
    "SKILL_ORIENTED_AGENT_ARCHITECTURE.md` and the applicable runtime, authority, resilience, "
    "and completion contracts. Agent count does not decide this. If the extension is missing, "
    "stop and request `govkit extension add skill-oriented-agent-architecture --target .`"
)
TOPOLOGY_TRIGGER = (
    "Multi-agent topology (`agent_topology.md`) applies only when `eval_criteria.yaml` declares "
    "`multi_agent: true`; such a feature also needs the SOAA contracts above"
)
STEP_ZERO = "0. **Multi-agent features only (`multi_agent: true`):**"
HARD_CODED = re.compile(r"extensions/(?:llm-application|skill-oriented-agent-architecture|\*)/")


def entry(agent: str, doc: str) -> str:
    return (REPO / "agents" / agent / ENTRY_DIRS[agent] / f"{doc}.md").read_text(encoding="utf-8")


def section(text: str, heading: str) -> str:
    """The body under `heading` up to the next heading of the same or higher level."""
    level = len(heading) - len(heading.lstrip("#"))
    start = text.index(heading)
    rest = text[start + len(heading) :]
    stop = re.search(rf"^#{{1,{level}}} ", rest, re.MULTILINE)
    return heading + (rest[: stop.start()] if stop else rest)


@pytest.mark.parametrize("agent", AGENTS)
@pytest.mark.parametrize("doc", L5_BACKEND)
def test_l5_entry_routes_three_layers_identically(agent, doc):
    text = entry(agent, doc)
    for sentence in (ROOT_NOTE, LLM_TRIGGER, SOAA_TRIGGER, TOPOLOGY_TRIGGER, STEP_ZERO):
        assert sentence in text, (agent, doc, sentence[:50])


@pytest.mark.parametrize("agent", AGENTS)
@pytest.mark.parametrize("doc", L5_BACKEND)
def test_l5_entry_never_gates_soaa_on_multi_agent(agent, doc):
    for line in entry(agent, doc).splitlines():
        assert not ("multi_agent" in line and "skill-oriented-agent-architecture" in line), line


@pytest.mark.parametrize("agent", AGENTS)
@pytest.mark.parametrize("doc", L5_BACKEND)
def test_l5_entry_conditions_llm_contracts_on_model_use(agent, doc):
    text = entry(agent, doc)
    assert "Confirm `extensions/llm-application/manifest.yaml` exists" not in text
    for line in text.splitlines():
        if "llm-application" in line and ("read" in line.lower() or "contract sets" in line):
            assert "language models" in line or "mode: llm" in line, line


def _payload_files():
    for agent in AGENTS:
        base = REPO / "agents" / agent
        for sub in ("skills", "rules", "instructions", ENTRY_DIRS[agent]):
            yield from sorted((base / sub).rglob("*.md"))


@pytest.mark.parametrize(
    "path", list(_payload_files()), ids=lambda p: p.relative_to(REPO).as_posix()
)
def test_extension_paths_name_the_declarative_root(path):
    text = path.read_text(encoding="utf-8")
    if HARD_CODED.search(text):
        assert ".govkit/packs/" in text, path.relative_to(REPO)


def test_genai_preflight_states_the_three_layers_identically():
    bodies = {
        agent: section(
            (REPO / "agents" / agent / "skills/backend/govkit-genai-preflight/SKILL.md").read_text(
                encoding="utf-8"
            ),
            "## Applicability layers",
        )
        for agent in AGENTS
    }
    assert len(set(bodies.values())) == 1
    body = bodies["claude-code"]
    for phrase in (
        "LLM application",
        "SOAA",
        "Multi-agent topology",
        "multi_agent: true",
        "Agent count does not decide",
    ):
        assert phrase in body, phrase


PREFLIGHTS = (
    "governance/backend/templates/l5-architecture-preflight.md",
    "features/starter_backend_l5/architecture_preflight.md",
    "features/starter_cli_l5/architecture_preflight.md",
)


@pytest.mark.parametrize("path", PREFLIGHTS)
def test_l5_preflight_separates_soaa_from_topology(path):
    text = (REPO / path).read_text(encoding="utf-8")
    body = section(text, "## 15. Agent Architecture")
    soaa = section(body, "### 15a. SOAA applicability")
    topology = section(body, "### 15b. Agent topology")
    assert "single agent with fixed skills" in soaa
    assert "multi_agent" not in soaa
    assert "Check `eval_criteria.yaml` for `multi_agent: true`." in topology
    assert "- SOAA status (if applicable): approved | blocked | n/a" in text


def test_l5_starters_copy_the_template_section_15():
    template = (REPO / PREFLIGHTS[0]).read_text(encoding="utf-8")
    expected = section(template, "## 15. Agent Architecture")
    for path in PREFLIGHTS[1:]:
        assert section((REPO / path).read_text(encoding="utf-8"), "## 15. Agent Architecture") == (
            expected
        ), path


SOAA_ONLY_PREFLIGHT = """\
    ## 15. Agent Architecture

    ### 15a. SOAA applicability (one or more agents)

    Applicable: one agent selects fixed governed runtime skills.
"""


@pytest.mark.parametrize("topology_present", [False, True])
def test_soaa_only_feature_never_requires_or_passes_topology(tmp_path, topology_present):
    """Review 3.6: SOAA applicability without `multi_agent` leaves topology inapplicable."""
    (tmp_path / "eval_criteria.yaml").write_text("version: 1\nmode: llm\n", encoding="utf-8")
    (tmp_path / "architecture_preflight.md").write_text(
        textwrap.dedent(SOAA_ONLY_PREFLIGHT), encoding="utf-8"
    )
    if topology_present:
        (tmp_path / "agent_topology.md").write_text("# Agent Topology\n", encoding="utf-8")
    for check in (check_agent_topology_exists, check_agent_topology_sections):
        status, message = check(tmp_path)
        assert status.name == "PASS" and "not applicable" in message, message


# --- PR #237 review findings -------------------------------------------------


@pytest.mark.parametrize("agent", AGENTS)
@pytest.mark.parametrize("doc", L5_BACKEND)
def test_l5_lifecycle_runs_llm_only_skills_for_model_use(agent, doc):
    """A deterministic L5 feature must not be sent to skills that require llm-application."""
    for line in entry(agent, doc).splitlines():
        if re.match(r"\d+\. (GenAI Preflight|Evaluation Suite Planning)", line):
            assert "mode: llm" in line or "uses LLM" in line, line


@pytest.mark.parametrize("agent", AGENTS)
def test_architecture_preflight_skill_splits_section_15(agent):
    text = (
        REPO / "agents" / agent / "skills/backend/govkit-architecture-preflight/SKILL.md"
    ).read_text(encoding="utf-8")
    assert "Section 15: Not applicable" not in text
    body = section(text, "## 15. Agent Architecture")
    soaa = section(body, "### 15a. SOAA applicability")
    topology = section(body, "### 15b. Agent topology")
    assert "single agent with fixed skills" in soaa and "multi_agent" not in soaa
    assert "multi_agent: true" in topology and "agent_topology.md" in topology


def test_genai_preflight_applies_only_to_model_use():
    for agent in AGENTS:
        text = (
            REPO / "agents" / agent / "skills/backend/govkit-genai-preflight/SKILL.md"
        ).read_text(encoding="utf-8")
        assert "Run this skill only when the feature calls language models" in text, agent


@pytest.mark.parametrize(
    "path", list(_payload_files()), ids=lambda p: p.relative_to(REPO).as_posix()
)
def test_extension_listing_stops_on_nonzero_and_never_reads_unverified_packs(path):
    text = path.read_text(encoding="utf-8")
    if "govkit extension list --installed" in text:
        assert "non-zero" in text, path.relative_to(REPO)
    # Without the lock-verifying listing, pack manifests are unverified.
    assert not re.search(r"look for [^.]*`\.govkit/packs/", text), path.relative_to(REPO)
    assert ".govkit/packs/*/*/manifest.yaml" not in text, path.relative_to(REPO)


@pytest.mark.parametrize("doc", L5_BACKEND)
def test_copilot_reads_llm_contract_sets_under_the_installed_root(doc):
    text = entry("copilot", doc)
    assert "declared by `extensions/llm-application/manifest.yaml`" not in text


@pytest.mark.parametrize("agent", AGENTS)
def test_extension_discovery_resolves_relationships_from_project_root(agent):
    text = (
        REPO / "agents" / agent / "skills/backend/govkit-architecture-preflight/SKILL.md"
    ).read_text(encoding="utf-8")
    body = section(text, "## 2.6 Extension Discovery")
    assert "Resolve every path under that extension's root" not in body
    assert "project-root-relative" in body
    assert "unverified" in body


# --- Increment 9: glob matches prompt a domain check; §15a records applicability


@pytest.mark.parametrize("agent", AGENTS)
@pytest.mark.parametrize(
    "skill", ("backend/govkit-architecture-preflight", "ui/govkit-ui-architecture-preflight")
)
def test_applies_to_glob_alone_never_makes_an_extension_applicable(agent, skill):
    text = (REPO / "agents" / agent / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
    body = section(text, "## 2.6 Extension Discovery")
    assert "A touched file matching a `contract_sets[].applies_to` glob is not enough" in body


@pytest.mark.parametrize("agent", AGENTS)
def test_section_15a_records_applicability_with_the_soaa_template(agent):
    text = (
        REPO / "agents" / agent / "skills/backend/govkit-architecture-preflight/SKILL.md"
    ).read_text(encoding="utf-8")
    soaa = section(section(text, "## 15. Agent Architecture"), "### 15a. SOAA applicability")
    assert "templates/preflight-soaa.md" in soaa
    assert "unknown" in soaa and "change trigger" in soaa
