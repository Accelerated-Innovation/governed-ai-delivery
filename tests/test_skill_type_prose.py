"""Issue #188 item 3: installed skills contain only their project's guidance."""

import argparse
import json

import pytest

from cli.agent_layout import AGENT_LAYOUTS
from cli.cmd_upgrade import cmd_upgrade
from cli.doctor import run_doctor
from cli.skill_context import load_skill_context
from cli.skill_templating import expand_skill_tokens, template_installed_skills
from tests.test_instruction_surface import AGENTS, UI_TYPES, apply


def assert_guidance(target, agent, kind):
    root = target / AGENT_LAYOUTS[agent].skills_dir
    prefix = "govkit-ui-" if kind in UI_TYPES else "govkit-"
    preflight = (root / (prefix + "architecture-preflight") / "SKILL.md").read_text()
    planning = (root / (prefix + "spec-planning") / "SKILL.md").read_text()
    combined = preflight + planning
    assert "govkit:docs-area" not in combined
    assert "{{docs_area}}" not in combined
    assert "Repository Scope" in preflight and "Out of scope" in planning
    if kind == "data":
        for section in ("Pipeline Impact", "Contract Impact", "PII Impact", "Lineage Impact"):
            assert section in preflight, section
        assert "@nfr-<category>" in planning and "No LLM evaluator tools" in planning
        assert "PII_HANDLING_CONTRACT.md" in combined
        assert "API_CONVENTIONS.md" not in combined
        assert "SECURITY_AUTH_PATTERNS.md" not in combined
        assert "docs/data/architecture/" in combined
    else:
        for data_prose in ("Data Impact", "Data projects", "Pipeline Impact", "PII Impact"):
            assert data_prose not in combined, data_prose
        assert "No LLM evaluator tools" not in combined
        if kind not in UI_TYPES:
            assert "API_CONVENTIONS.md" in combined
            assert "SECURITY_AUTH_PATTERNS.md" in combined
            assert "docs/backend/architecture/" in combined


@pytest.mark.parametrize("agent", AGENTS)
@pytest.mark.parametrize("kind", ["api", "cli", "data", *UI_TYPES])
def test_apply_selects_the_installed_types_guidance(tmp_path, agent, kind):
    apply(tmp_path, agent, kind)
    assert_guidance(tmp_path, agent, kind)


@pytest.mark.parametrize("agent", AGENTS)
@pytest.mark.parametrize("kind", ["api", "cli", "data"])
def test_upgrade_refreshes_shared_skill_prose_and_preserves_team_files(tmp_path, agent, kind):
    apply(tmp_path, agent, kind)
    root = tmp_path / AGENT_LAYOUTS[agent].skills_dir
    for skill in ("govkit-architecture-preflight", "govkit-spec-planning"):
        (root / skill / "SKILL.md").write_text("Obsolete shared instructions\n")
    notes = tmp_path / "team-notes.md"
    notes.write_text("Keep the team's decisions.\n")
    before = notes.read_bytes(), notes.stat().st_mtime_ns
    marker = tmp_path / ".govkit/marker.json"
    document = json.loads(marker.read_text())
    document["version"] = "0.20.0"
    marker.write_text(json.dumps(document))

    cmd_upgrade(argparse.Namespace(target=str(tmp_path), force=False))

    assert_guidance(tmp_path, agent, kind)
    assert (notes.read_bytes(), notes.stat().st_mtime_ns) == before


SECTIONS = (
    "Shared introduction\n"
    "<!-- govkit:docs-area data -->\nData docs/{{docs_area}}/\n<!-- /govkit:docs-area -->\n"
    "<!-- govkit:docs-area backend -->\nBackend docs/{{docs_area}}/\n<!-- /govkit:docs-area -->\n"
    "Shared conclusion\n"
)


@pytest.mark.parametrize(
    "area,expected",
    [
        ("data", "Data docs/data/\n"),
        ("backend", "Backend docs/backend/\n"),
        ("ui", ""),
    ],
)
def test_type_sections_select_content_and_expand_its_paths(area, expected):
    assert (
        expand_skill_tokens(SECTIONS, area)
        == "Shared introduction\n" + expected + "Shared conclusion\n"
    )


@pytest.mark.parametrize("area", ["", "unknown"])
def test_unknown_type_does_not_discard_conditional_guidance(area):
    text = SECTIONS + "Invoke {{architecture_preflight_skill}}.\n"
    assert expand_skill_tokens(text, area) == text


def unresolved_install(target, agent, area):
    apply(target, agent, "api")
    skill = target / AGENT_LAYOUTS[agent].skills_dir / "govkit-spec-planning/SKILL.md"
    skill.write_text(SECTIONS, encoding="utf-8")
    context = target / ".govkit/skill_context.yaml"
    context.write_text(json.dumps({"docs_area": area}), encoding="utf-8")
    return skill, load_skill_context(target)


@pytest.mark.parametrize("agent", AGENTS)
@pytest.mark.parametrize("area", ["", "future-area"])
def test_unknown_loaded_context_preserves_installed_bytes_and_mtime(tmp_path, agent, area):
    skill, context = unresolved_install(tmp_path, agent, area)
    before = skill.read_bytes(), skill.stat().st_mtime_ns

    modified = template_installed_skills(tmp_path, agent, context.docs_area)

    assert modified == 0
    assert (skill.read_bytes(), skill.stat().st_mtime_ns) == before


@pytest.mark.parametrize("agent", AGENTS)
def test_doctor_still_reports_path_tokens_after_unknown_context_render(tmp_path, agent):
    skill, context = unresolved_install(tmp_path, agent, "future-area")
    template_installed_skills(tmp_path, agent, context.docs_area)

    findings = run_doctor(tmp_path)

    hits = [finding for finding in findings if finding.id == "D015"]
    assert len(hits) == 1
    assert hits[0].file == skill.relative_to(tmp_path).as_posix()
    assert hits[0].severity == "warning" and "{{docs_area}}" in hits[0].message


def test_rendered_type_guidance_is_idempotent():
    rendered = "Shared introduction\nData docs/data/\nShared conclusion\n"
    assert expand_skill_tokens(rendered, "data") == rendered


def test_type_sections_support_windows_newlines():
    text = SECTIONS.replace("\n", "\r\n")
    assert expand_skill_tokens(text, "data") == (
        "Shared introduction\r\nData docs/data/\r\nShared conclusion\r\n"
    )


@pytest.mark.parametrize(
    "text",
    [
        "<!-- govkit:docs-area future -->\nKeep future guidance\n<!-- /govkit:docs-area -->\n",
        "<!-- govkit:docs-area data -->\nUnterminated guidance\n",
        "Explain <!-- govkit:docs-area data --> inline.\n",
        "<!-- An unrelated comment -->\nKeep this content.\n",
    ],
)
def test_unrecognized_or_incomplete_sections_are_left_visible(text):
    assert expand_skill_tokens(text, "backend") == text
