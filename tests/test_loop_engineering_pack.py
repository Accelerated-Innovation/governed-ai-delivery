"""The opt-in `loop-engineering` pack and its feature loop skill (L11a).

The skill is prose an agent follows, so these tests pin the parts of it that
restate GovKit's own contract: the exit statuses, the reason codes and their
groups, and the stop rules the maintainer decided. They do not show that an
agent follows the skill.
"""

import re

import pytest
import yaml

from cli import feature_verdict, paths
from cli.agent_layout import AGENT_LAYOUTS
from cli.pack_loading import bundled_catalog
from cli.pack_resolution import resolve_packs
from cli.pack_store import apply_install, preview_install, verify_lock
from cli.version import GOVKIT_VERSION
from tests.test_capability_packs import profile
from tests.test_pack_store import snapshot, write_profile

PACK = "loop-engineering"
SKILL = "govkit-loop-engineering-feature"
ROOT = paths.EXTENSION_PACKS_DIR / PACK
SOURCE = ROOT / "skills" / SKILL


def _text(*parts: str) -> str:
    return SOURCE.joinpath(*parts).read_text(encoding="utf-8")


def _pack():
    return next(pack for pack in bundled_catalog() if pack.id == PACK)


def _codes(section: str) -> set[str]:
    return set(re.findall(r"`([a-z]+(?:-[a-z]+)+)`", section))


class TestPack:
    def test_it_provides_one_capability_and_requires_nothing(self):
        pack = _pack()
        assert pack.provides == ("loop-engineering",)
        assert not pack.requires and not pack.conflicts
        result = resolve_packs(profile([PACK]), bundled_catalog(), govkit_version=GOVKIT_VERSION)
        assert result.ready, result.decisions
        assert {p.id for p in result.packs} == {PACK}

    def test_it_adds_no_check(self):
        manifest = yaml.safe_load((ROOT / "manifest.yaml").read_text(encoding="utf-8"))
        assert "checks" not in manifest["capability_pack"]
        assert not list(ROOT.rglob("*.py"))

    def test_the_skill_source_name_and_install_name_are_the_same(self):
        (skill,) = _pack().skills
        frontmatter = yaml.safe_load(_text("SKILL.md").split("---", 2)[1])
        assert SOURCE.name == frontmatter["name"] == skill.install_as == SKILL
        assert set(frontmatter) == {"name", "description"}

    @pytest.mark.parametrize("agent", AGENT_LAYOUTS)
    def test_it_installs_and_verifies_for_every_agent(self, tmp_path, agent):
        target = tmp_path / "consumer"
        source = write_profile(target, profile([PACK], agent=agent))
        apply_install(
            preview_install(source, target, bundled_catalog(), govkit_version=GOVKIT_VERSION)
        )
        assert verify_lock(target).ready
        native = target / AGENT_LAYOUTS[agent].skills_dir / SKILL
        assert (native / "SKILL.md").is_file()
        # The same skill for every agent, with the Claude Code guidance inside it.
        for reference in ("feature-loop.md", "claude-code.md"):
            assert (native / "references" / reference).read_text(encoding="utf-8") == _text(
                "references", reference
            )
        assert not (target / ".govkit" / "marker.json").exists()
        before = snapshot(target)
        apply_install(
            preview_install(source, target, bundled_catalog(), govkit_version=GOVKIT_VERSION)
        )
        assert snapshot(target) == before

    def test_every_reference_the_skill_links_exists(self):
        for link in re.findall(r"\]\((references/[^)]+)\)", _text("SKILL.md")):
            assert SOURCE.joinpath(link).is_file(), link


class TestTheSkillRestatesTheContract:
    def test_the_exit_statuses_are_the_answers(self):
        table = _text("SKILL.md").split("| Exit | State |")[1].split("\n\n")[0]
        rows = {
            int(exit_code): state
            for exit_code, state in re.findall(r"^\| (\d) \| `(\w+)` \|", table, re.MULTILINE)
        }
        assert rows == {code: state for state, code in feature_verdict.EXIT_CODES.items()}
        assert "| 2 | The run could not start |" in table

    def test_every_reason_code_is_in_the_group_the_code_gives_it(self):
        guide = _text("references", "feature-loop.md")
        act = guide.split("### Reasons you can act on")[1].split("###")[0]
        now = guide.split("### Reasons that need a person now")[1].split("###")[0]
        later = guide.split("### Reasons that need a person once")[1].split("## The stop rules")[0]
        assert _codes(act) >= set(feature_verdict._AGENT)
        assert _codes(now) == set(feature_verdict._NOW)
        assert _codes(later) == set(feature_verdict._PERSON)
        named = (
            set(feature_verdict._AGENT) | set(feature_verdict._NOW) | set(feature_verdict._PERSON)
        )
        assert named == set(feature_verdict.CODES)
        # Nothing that needs a person is listed as something the agent can act on.
        assert not _codes(act) & (set(feature_verdict._NOW) | set(feature_verdict._PERSON))

    def test_the_order_of_the_states_is_the_codes_order(self):
        guide = _text("references", "feature-loop.md")
        order = re.findall(r"^\d\. `(\w+)`", guide, re.MULTILINE)
        assert order == [state for state, _ in feature_verdict._GROUPS] + [feature_verdict.DONE]

    def test_the_round_runs_tests_then_record_then_the_answer(self):
        round_steps = _text("SKILL.md").split("## One round")[1].split("| Exit |")[0]
        commands = _text("references", "feature-loop.md").split("```")[1]
        for text in (round_steps, commands):
            record = text.index("govkit evidence --target . --record")
            assert text.index("test") < record < text.index("govkit conform")
        assert "--feature <name>" in _text("references", "feature-loop.md")


class TestTheStopRules:
    """The maintainer's decision of 2026-11-27."""

    def test_the_three_rules_are_stated_with_the_default_limit(self):
        rules = _text("SKILL.md").split("## Stop rules")[1].split("##")[0]
        assert "The state is `escalate`." in rules
        assert "Two rounds in a row give the same set of reason codes." in rules
        assert "round limit" in rules
        assert "It is 10 unless the person states another number." in _text("SKILL.md")

    def test_no_progress_compares_codes_and_every_conform_run_counts(self):
        guide = _text("references", "feature-loop.md")
        assert "Compare the codes, not the messages." in guide
        assert "Count a round each time you run `govkit conform --feature`." in guide

    def test_the_report_gives_the_reasons_as_printed(self):
        report = _text("SKILL.md").split("## What you report when you stop")[1]
        assert "as GovKit printed them" in report and "Which stop rule applied." in report

    def test_done_may_not_be_reached_by_weakening_and_is_not_approval(self):
        forbidden = _text("SKILL.md").split("## What you must not do")[1].split("##")[0]
        for phrase in (
            "`acceptance.feature`", "`eval_criteria.yaml`", "an existing test",
            "skip a test", "paid evaluation", "approved, reviewed or ready to merge",
        ):  # fmt: skip
            assert phrase in forbidden, phrase
        assert "It is not review, approval or a gate." in (ROOT / "README.md").read_text(
            encoding="utf-8"
        )


class TestClaudeCodeGuidance:
    def test_the_goal_condition_names_every_stop_rule(self):
        guide = _text("references", "claude-code.md")
        condition = guide.split("```")[1]
        for phrase in ("exited 0", "exited 3", "exited 2", "same reason codes", "10 rounds"):
            assert phrase in condition, phrase
        assert SKILL in condition

    def test_it_says_what_was_checked_and_when(self):
        guide = _text("references", "claude-code.md")
        assert "checked against the Claude Code documentation on 2026-11-27" in guide
        assert "This file applies to Claude Code only." in guide

    def test_a_stop_hook_may_block_only_on_continue(self):
        guide = _text("references", "claude-code.md")
        assert "it must block only on exit status 1" in guide

    def test_govkit_does_not_run_the_loop(self):
        for text in (_text("SKILL.md"), (ROOT / "README.md").read_text(encoding="utf-8")):
            assert "GovKit does not run th" in text
