"""The planning skills consult the contract — increment 12B.

12A installed the rule and the fact it keys on. A rule is read once, at the
start of a session, and then competes with everything else in the context
window; the moments that matter — deciding what to build, checking the
architecture, ordering the work — come later and each has its own skill.

So the precondition is repeated where it is acted on. Three properties:

- **It is the same precondition**, not a second policy. Skills point at the
  rule; they do not restate what it permits.
- **It names no path.** The three agents install the rule to three different
  places and the UI skills must be byte-identical across all three, so any
  path the block named would be wrong for two agents out of three.
- **It skips loudly when the project has no PDG.** Most do not, and a skill
  that lectures every user about a contract they never adopted is a skill
  teams strip out.
"""

from __future__ import annotations

import itertools
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

AGENTS = ("claude-code", "codex", "copilot")
AREAS = ("backend", "ui")
SKILLS = ("spec-planning", "architecture-preflight", "implementation-plan")

RULE_PATH = {
    "claude-code": ".claude/rules/govkit/behavior-contract.md",
    "codex": ".agents/rules/behavior-contract.md",
    "copilot": ".github/instructions/govkit/behavior-contract.instructions.md",
}

MARKER = "Behavior contract"


def _skill(agent: str, area: str, skill: str) -> Path:
    return REPO / "agents" / agent / "skills" / area / skill / "SKILL.md"


CASES = [
    pytest.param(a, area, s, id=f"{a}-{area}-{s}")
    for a, area, s in itertools.product(AGENTS, AREAS, SKILLS)
]


@pytest.mark.parametrize("agent,area,skill", CASES)
def test_every_planning_skill_exists(agent, area, skill):
    """The parametrisation is the claim: eighteen files, and if one of them
    is missing the coverage below is quietly smaller than it looks."""
    assert _skill(agent, area, skill).is_file()


@pytest.mark.parametrize("agent,area,skill", CASES)
def test_every_planning_skill_carries_the_precondition(agent, area, skill):
    text = _skill(agent, area, skill).read_text(encoding="utf-8")

    assert MARKER in text
    assert "skill_context.yaml" in text
    assert "authority" in text


@pytest.mark.parametrize("agent,area,skill", CASES)
def test_the_precondition_tells_the_agent_to_skip_when_there_is_no_contract(agent, area, skill):
    """`none` is the default and the common case. Without an explicit skip
    the agent works through a section that does not apply and may report on
    it, which is how a governance feature becomes noise."""
    text = _skill(agent, area, skill).read_text(encoding="utf-8").lower()

    assert "skip" in text
    assert "none" in text


@pytest.mark.parametrize("agent,area,skill", CASES)
def test_the_precondition_names_the_rule_without_hard_coding_a_path(agent, area, skill):
    """The three agents install the rule to three different places, and the
    UI skills are required to be **byte-identical** across all three
    (`test_ui_nextjs_skill_content_parity`). Those two facts cannot both
    hold if the block names a path: whichever one it names is wrong for two
    agents out of three, and a dead path in a governance instruction reads
    as governance that does not exist.

    It does not need one. Each agent auto-loads its own rules, so the rule
    is already in context by the time a skill runs; codex, which does not,
    is pointed at the file from its `AGENTS.md` where a path belongs.
    """
    text = _skill(agent, area, skill).read_text(encoding="utf-8")

    assert "behavior-contract" in text
    for owner, path in RULE_PATH.items():
        assert path not in text, f"{agent} skill hard-codes {owner}'s rule path"


@pytest.mark.parametrize(
    "flag",
    ["--target", "--baseline", "--commitment", "--source"],
)
@pytest.mark.parametrize("agent,area,skill", CASES)
def test_the_block_names_every_argument_the_checks_depend_on(agent, area, skill, flag):
    """Asserted on the prose, not on command lines.

    An earlier version of this test only inspected lines *starting with* a
    full `govkit` invocation — and the block deliberately has none, because
    it defers the exact command to the rule. So the loop ran zero
    assertions and every piece of this guidance could have been deleted
    with the suite still green.

    Each flag is load-bearing in a different way: `--target` and
    `--baseline` are required and undefaulted; `--commitment` is optional to
    argparse and decides the answer; `--source` is what a baseline spanning
    more than one repository cannot be checked without.
    """
    assert flag in _skill(agent, area, skill).read_text(encoding="utf-8")


@pytest.mark.parametrize("agent,area,skill", CASES)
def test_no_bare_invocation_creeps_in_later(agent, area, skill):
    """The block should show no runnable command at all — but if someone
    later pastes one in, it must carry the arguments that make it work."""
    for line in _skill(agent, area, skill).read_text(encoding="utf-8").splitlines():
        stripped = line.strip().lstrip("`$ ")
        if stripped.startswith(("govkit validate-baseline", "govkit verify-authority")):
            assert "--target" in line, line
            assert "--baseline" in line, line


@pytest.mark.parametrize("agent,area,skill", CASES)
def test_no_planning_skill_tells_an_agent_to_run_the_enforcing_check(agent, area, skill):
    """The enforcing form needs a credential the agent does not have and
    should not be given. It belongs to CI."""
    assert "--enforce" not in _skill(agent, area, skill).read_text(encoding="utf-8")


@pytest.mark.parametrize("agent,area,skill", CASES)
def test_the_precondition_sits_after_the_frontmatter_not_inside_it(agent, area, skill):
    """Skill frontmatter must stay byte-identical across the three agents —
    the repository's parity rule — and it carries only `name` and
    `description`. A block inserted into it would break discovery for every
    agent at once."""
    text = _skill(agent, area, skill).read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        pytest.skip("this skill has no frontmatter")

    _, frontmatter, body = text.split("---", 2)

    assert MARKER not in frontmatter
    assert MARKER in body


@pytest.mark.parametrize("area,skill", [(a, s) for a in AREAS for s in SKILLS])
def test_the_three_agents_say_the_same_thing_apart_from_their_own_path(area, skill):
    """A policy one agent states more strictly than another is a policy the
    team cannot rely on. Bodies differ between agents by design, so this
    compares only the inserted block, with each agent's path normalised out.
    """
    blocks = {}
    for agent in AGENTS:
        text = _skill(agent, area, skill).read_text(encoding="utf-8")
        start = text.index(f"## {MARKER}")
        rest = text[start + 3:]
        end = rest.find("\n## ")
        blocks[agent] = rest if end == -1 else rest[:end]

    distinct = set(blocks.values())
    assert len(distinct) == 1, f"{area}/{skill}: the three agents disagree"
