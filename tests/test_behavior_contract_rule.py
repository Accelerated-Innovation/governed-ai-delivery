"""The coding-agent boundary under a behavior contract — increment 12.

Increments 01–11 made behavior a versioned commitment and gave the merge
boundary teeth. None of that reaches the agent actually writing the code:
it plans from the feature folder, and a Gherkin file in the working tree
looks the same whether or not it is the one somebody approved.

This rule is that missing half. Two properties matter more than its prose:

- **It is inert unless the project opted in.** GovKit is open source and
  most projects have no PDG. The rule ships everywhere and applies only when
  `.govkit/skill_context.yaml` records `authority.source: pdg` — so existing
  adoption at any level is not retroactively reinterpreted as having agreed
  to it.
- **It cannot be satisfied by the agent alone.** The whole point is that an
  agent cannot issue itself a product approval, so a rule an agent could
  discharge by deciding it had would be worse than none.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

# Each agent's home for a project-wide rule, and the suffix its format uses.
RULE_FILES = {
    "claude-code": REPO / "agents/claude-code/rules/generic/behavior-contract.md",
    "codex": REPO / "agents/codex/rules/generic/behavior-contract.md",
    "copilot": REPO / "agents/copilot/instructions/generic/behavior-contract.instructions.md",
}


@pytest.fixture(params=sorted(RULE_FILES), ids=sorted(RULE_FILES))
def rule(request) -> Path:
    return RULE_FILES[request.param]


def test_the_rule_ships_for_all_three_agents(rule):
    """Parity is the repository's standing rule: a policy one agent enforces
    and another does not is a policy the team cannot rely on."""
    assert rule.is_file(), f"missing {rule.relative_to(REPO)}"


def test_the_copilot_form_carries_the_frontmatter_its_format_needs(rule):
    """Copilot instructions are scoped by `applyTo`; without it the file is
    installed and never applied, which looks identical to being enforced."""
    if "copilot" not in str(rule):
        pytest.skip("only copilot's format uses applyTo")
    text = rule.read_text(encoding="utf-8")

    assert text.startswith("---\n")
    assert "applyTo:" in text.split("---")[1]


def test_the_rule_is_inert_without_an_explicit_opt_in(rule):
    """It must name the fact it keys on and say plainly that it does not
    apply otherwise. A rule that reads as unconditional turns every existing
    install into an AIPOS install by accident."""
    text = rule.read_text(encoding="utf-8")

    assert "skill_context.yaml" in text
    assert "authority" in text
    assert "pdg" in text.lower()
    assert "does not apply" in text.lower()


def test_the_rule_refuses_agent_self_approval(rule):
    """The acceptance criterion with the sharpest edge: no agent variant can
    issue itself a product approval, whatever it concludes about the code."""
    text = rule.read_text(encoding="utf-8").lower()

    assert "approval" in text
    assert "never" in text or "cannot" in text


@pytest.mark.parametrize(
    "prohibition",
    ["exclusion", "threshold", "tool authority", "helpful"],
)
def test_the_rule_names_each_prohibited_drift(rule, prohibition):
    """Four ways an agent quietly changes the product while believing it is
    implementing the spec: dropping a case it inferred was out of scope,
    adding behavior nobody asked for, relaxing an evaluation threshold to
    make a run pass, and widening its own tool authority."""
    assert prohibition in rule.read_text(encoding="utf-8").lower()


def test_the_rule_still_permits_ordinary_refactoring(rule):
    """A contract on *behavior* is not a freeze on the code. If the rule
    reads as "change nothing", teams will turn it off rather than obey it,
    and the acceptance criteria require refactoring to proceed within
    contract."""
    text = rule.read_text(encoding="utf-8").lower()

    assert "refactor" in text


def test_the_rule_routes_a_scope_change_to_a_decision_rather_than_a_judgement(rule):
    """The agent's job at a conflict is to stop and say so. It is the one
    thing it must not resolve on its own, because resolving it is what the
    commitment exists to prevent."""
    text = rule.read_text(encoding="utf-8").lower()

    assert "stop" in text or "halt" in text
    assert "decision" in text


def test_the_rule_does_not_tell_an_agent_to_run_the_enforcing_check(rule):
    """`verify-authority --enforce` belongs to CI, which holds a read-only
    credential the agent does not and should not have. An agent told to run
    the enforcing form either fails for want of a token or is handed one."""
    text = rule.read_text(encoding="utf-8")

    assert "--enforce" not in text


# ---------------------------------------------------------------------------
# Wiring: shipped is not installed
# ---------------------------------------------------------------------------

MANIFESTS = {
    "claude-code": REPO / "agents/claude-code/manifest.json",
    "codex": REPO / "agents/codex/manifest.json",
    "copilot": REPO / "agents/copilot/manifest.json",
}


@pytest.fixture(params=sorted(MANIFESTS), ids=sorted(MANIFESTS))
def manifest_text(request) -> str:
    return MANIFESTS[request.param].read_text(encoding="utf-8")


def test_every_variant_that_governs_features_also_installs_this_rule(manifest_text):
    """`spec-compliance` is the existing project-wide rule about feature
    artifacts, and it installs at L4 and L5 and never at L3 — which is the
    correct set here too, because a baseline binds scenarios and L3 has no
    `features/` at all.

    Tying the counts together rather than hard-coding eleven means a new
    project type cannot get one rule and not the other.
    """
    assert manifest_text.count("behavior-contract") == manifest_text.count("spec-compliance")


def test_the_rule_is_not_installed_at_l3(manifest_text):
    """L3 carries architecture contracts and no features. A rule about
    approved scenarios would be unreachable advice."""
    import json

    manifest = json.loads(manifest_text)
    for type_name, levels in manifest["variants"]["type"].items():
        level_3 = levels.get("level_3") or {}
        installed = json.dumps(level_3)
        assert "behavior-contract" not in installed, type_name


def test_apply_installs_the_rule_into_a_real_project(tmp_path):
    """The manifest entry and the shipped file have to agree about the
    source path, and only a real apply proves it — a wrong `src` fails at
    install time in a customer's repo, not here."""
    from cli.cmd_apply import cmd_apply

    class Args:
        agent = "claude-code"
        target = str(tmp_path)
        level = "4"
        type = "api"
        ci = "github"
        stack = None
        ui = None
        force = False
        dry_run = False
        yes = True

    cmd_apply(Args())

    assert (tmp_path / ".claude/rules/govkit/behavior-contract.md").is_file()


# ---------------------------------------------------------------------------
# Installed is not loaded, and named is not runnable
# ---------------------------------------------------------------------------


def test_codex_points_at_the_rule_from_a_file_it_actually_loads():
    """Codex discovers instructions only through `AGENTS.md`, root or nested.
    A file dropped at `.agents/rules/behavior-contract.md` with nothing
    pointing at it is installed and never read — which looks exactly like
    being enforced. The existing rules are reachable because the AGENTS.md
    files name them; this one has to be too.

    Driven off the manifest rather than a filename convention, so a new
    project type cannot ship the rule with no pointer to it.
    """
    import json

    manifest = json.loads(MANIFESTS["codex"].read_text(encoding="utf-8"))
    checked = 0

    for type_name, levels in manifest["variants"]["type"].items():
        for level_name, block in levels.items():
            if not isinstance(block, dict):
                continue
            files = [e for e in block.get("files", []) if isinstance(e, dict)]
            if not any("behavior-contract" in e.get("src", "") for e in files):
                continue
            roots = [
                e["src"] for e in files
                if e.get("dest") == "AGENTS.md" and "agents-md" in e.get("src", "")
            ]
            assert roots, f"{type_name}/{level_name} installs the rule with no root AGENTS.md"
            for src in roots:
                text = (REPO / "agents/codex" / src).read_text(encoding="utf-8")
                assert "behavior-contract" in text, (
                    f"{src} does not point codex at the rule it installs "
                    f"({type_name}/{level_name})"
                )
                checked += 1

    assert checked == 11, f"expected every L4/L5 variant covered, saw {checked}"


def test_the_rule_shows_each_command_with_the_arguments_it_requires(rule):
    """Both commands take `--target` and `--baseline`, and neither has a
    default. A rule that names a command bare reads as runnable and exits in
    argument parsing — the mandatory pre-planning step then checks nothing.
    """
    text = rule.read_text(encoding="utf-8")

    for line in text.splitlines():
        stripped = line.strip().lstrip("`$ ")
        if stripped.startswith("govkit validate-baseline") or stripped.startswith(
            "govkit verify-authority"
        ):
            assert "--target" in line, line
            assert "--baseline" in line, line


def test_the_rule_supplies_the_commitment_id(rule):
    """`--commitment` is optional to argparse and load-bearing to the answer:
    without it `verify()` returns **not authorized** — a true statement about
    a missing pointer that reads as a verdict about the work. An agent
    following the rule literally would stop for the wrong reason."""
    text = rule.read_text(encoding="utf-8")

    assert "--commitment" in text
    assert "not authorized" in text.lower()


def test_the_rule_says_where_the_endpoint_comes_from(rule):
    """Without `GOVKIT_PDG_URL` the advisory check reports that it cannot ask
    and exits zero. That is the right behavior and the wrong thing to leave
    unexplained: an agent reading "no verdict" needs to know whether it is
    looking at an outage or an unset variable."""
    assert "GOVKIT_PDG_URL" in rule.read_text(encoding="utf-8")


@pytest.mark.parametrize("agent", ["claude-code", "copilot"])
def test_the_other_two_agents_need_no_pointer_because_of_where_it_lands(agent):
    """The codex pointer is an asymmetry, and this is why it is not an
    oversight.

    Claude Code and Copilot auto-load a directory; codex auto-loads only
    `AGENTS.md`. For those two the rule lands in the very directory their
    level-specific governance rule already occupies, so it is loaded by the
    same mechanism and a cross-reference would add nothing. Asserting it
    keeps that from silently ceasing to be true.
    """
    import json
    from posixpath import dirname

    manifest = json.loads(MANIFESTS[agent].read_text(encoding="utf-8"))

    for type_name, levels in manifest["variants"]["type"].items():
        for level_name, block in levels.items():
            if not isinstance(block, dict):
                continue
            files = [e for e in block.get("files", []) if isinstance(e, dict)]
            rule = next((e for e in files if "behavior-contract" in e.get("src", "")), None)
            if rule is None:
                continue
            governance = next(
                (e for e in files if e.get("dest", "").endswith(("govkit/governance.md",
                                                                 "govkit/governance.instructions.md"))),
                None,
            )
            assert governance, f"{agent} {type_name}/{level_name} has no governance rule"
            assert dirname(rule["dest"]) == dirname(governance["dest"]), (
                f"{agent} {type_name}/{level_name}: the rule lands in "
                f"{dirname(rule['dest'])} but governance loads from "
                f"{dirname(governance['dest'])}"
            )
