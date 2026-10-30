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
