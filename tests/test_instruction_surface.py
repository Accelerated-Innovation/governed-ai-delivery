"""Issue #188: instructions in a real install must describe what it installs."""

import argparse
import json
import re
from pathlib import Path

import pytest
import yaml

from cli.agent_layout import AGENT_LAYOUTS
from cli.cmd_apply import cmd_apply
from cli.cmd_upgrade import cmd_upgrade
from cli.skill_templating import expand_skill_tokens

AGENTS = ("claude-code", "copilot", "codex")
UI_TYPES = ("ui-react", "ui-angular", "ui-nextjs")
COMMON_ARTIFACTS = {
    "acceptance.feature",
    "nfrs.md",
    "eval_criteria.yaml",
    "architecture_preflight.md",
    "plan.md",
}
SCOPES = {
    "ports": ["**/ports/**"],
    "llm-gateway": ["**/adapters/llm/**"],
    "guardrails": ["**/adapters/guardrails/**", "**/rails/**"],
    "llm-evaluation": ["**/tests/eval/**", "**/eval_sets/**"],
    "llm-observability": ["**/adapters/observability/**"],
    "multi-agent": ["**/services/graphs/**"],
}


def apply(target: Path, agent: str, kind: str, level: str = "4") -> None:
    target.mkdir(parents=True, exist_ok=True)
    cmd_apply(
        argparse.Namespace(
            agent=agent,
            target=str(target),
            type=kind,
            level=level,
            ci="github",
            stack=None,
            force=False,
            detect=False,
        )
    )


def rule(target: Path, agent: str, name: str) -> Path:
    if agent == "codex":
        return target / ".agents/rules" / f"{name}.md"
    suffix = ".instructions.md" if agent == "copilot" else ".md"
    return target / AGENT_LAYOUTS[agent].rules_dir / "govkit" / f"{name}{suffix}"


def globs(path: Path, agent: str) -> list[str]:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{path.name} is an unscoped global rule"
    metadata = yaml.safe_load(text.split("---", 2)[1])
    value = metadata.get(AGENT_LAYOUTS[agent].frontmatter_glob_key)
    assert value, f"{path.name} has no native scope"
    return value if isinstance(value, list) else value.split(",")


@pytest.mark.parametrize("agent", ["claude-code", "copilot"])
@pytest.mark.parametrize("kind", ["api", "cli"])
def test_backend_rules_have_narrow_default_scopes(tmp_path, agent, kind):
    # Trigger the real hexagonal inference: the old ports template then replaces
    # its correct fallback with api/ + ports/inbound/, dropping outbound ports.
    for layer in ("api", "ports", "services", "models", "adapters", "common"):
        (tmp_path / "src/service" / layer).mkdir(parents=True)
    apply(tmp_path, agent, kind, "5")
    expected = {name: paths for name, paths in SCOPES.items() if name != "ports"}
    actual = {name: globs(rule(tmp_path, agent, name), agent) for name in expected}
    assert actual == expected


@pytest.mark.parametrize("agent", ["claude-code", "copilot"])
def test_ports_scope_includes_outbound_without_loading_on_api_edits(tmp_path, agent):
    for layer in ("api", "ports", "services", "models", "adapters", "common"):
        (tmp_path / "src/service" / layer).mkdir(parents=True)
    apply(tmp_path, agent, "api", "5")
    assert globs(rule(tmp_path, agent, "ports"), agent) == ["**/ports/**"]


@pytest.mark.parametrize("agent", ["claude-code", "copilot"])
def test_upgrade_preserves_and_renders_explicit_role_overrides(tmp_path, agent):
    apply(tmp_path, agent, "api", "5")
    context = tmp_path / ".govkit/skill_context.yaml"
    document = yaml.safe_load(context.read_text())
    roles = {name.replace("-", "_"): [f"custom/{name}/"] for name in SCOPES}
    document["architecture"]["layers"].update(roles)
    context.write_text(yaml.safe_dump(document))
    notes = tmp_path / "team-notes.md"
    notes.write_text("Team decisions must survive.\n")
    marker = tmp_path / ".govkit/marker.json"
    stored = json.loads(marker.read_text())
    stored["version"] = "0.20.0"
    marker.write_text(json.dumps(stored))
    cmd_upgrade(argparse.Namespace(target=str(tmp_path), force=False))
    assert (
        yaml.safe_load(context.read_text())["architecture"]["layers"]
        == document["architecture"]["layers"]
    )
    assert notes.read_text() == "Team decisions must survive.\n"
    assert {name: globs(rule(tmp_path, agent, name), agent) for name in SCOPES} == {
        name: [f"**/custom/{name}/**"] for name in SCOPES
    }


def assert_ui_guidance(target: Path, agent: str) -> None:
    governance = target / "AGENTS.md" if agent == "codex" else rule(target, agent, "governance")
    skill_root = target / AGENT_LAYOUTS[agent].skills_dir
    fix = skill_root / "govkit-fix-record/SKILL.md"
    problems = []
    for path in (governance, fix):
        text = path.read_text(encoding="utf-8")
        names = set(re.findall(r"(?:/|\$)(govkit-[a-z-]+)", text))
        if path == fix:
            assert "govkit-ui-architecture-preflight" in names
            prefix = "$" if agent == "codex" else "/"
            assert f"`{prefix}govkit-ui-architecture-preflight`" in text
        for name in names:
            if not (skill_root / name / "SKILL.md").is_file():
                problems.append(f"{path.name} invokes missing {name}")
        for reference in re.findall(
            r"`((?:\.claude/rules|\.github/instructions|\.agents/rules)/[^`]+\.md)`", text
        ):
            if not any(target.glob(reference)):
                problems.append(f"{path.name} references missing {reference}")
        if "{{" in text:
            problems.append(f"{path.name} contains unexpanded tokens")
    compliance = rule(target, agent, "spec-compliance").read_text(encoding="utf-8")
    prechecks = compliance.split("## Pre-Implementation Checks", 1)[1].split(
        "## Plan Discipline", 1
    )[0]
    assert re.search(r"Verify.*Repository Scope.*`nfrs.md`.*complete", prechecks), (
        "UI scope check must gate implementation"
    )
    section = compliance.split("## Feature Artifacts", 1)[1].split("## Defect fixes", 1)[0]
    listed = set(re.findall(r"^[-*] `([^`]+)`", section, re.MULTILINE))
    if listed != COMMON_ARTIFACTS | {"design.md"}:
        problems.append(
            f"UI compliance requires {listed}, expected six artifacts including design.md"
        )
    if "five artifacts" in compliance or "five-artifact" in fix.read_text():
        problems.append("UI guidance still describes a five-artifact contract")
    assert not problems, "\n".join(problems)


@pytest.mark.parametrize("agent", AGENTS)
@pytest.mark.parametrize("kind", UI_TYPES)
@pytest.mark.parametrize("level", ["4", "5"])
def test_ui_guidance_matches_native_skills_rules_and_design_contract(tmp_path, agent, kind, level):
    apply(tmp_path, agent, kind, level)
    assert_ui_guidance(tmp_path, agent)


@pytest.mark.parametrize("agent", AGENTS)
def test_ui_upgrade_replaces_stale_owned_guidance_and_preserves_team_files(tmp_path, agent):
    apply(tmp_path, agent, "ui-react")
    rule(tmp_path, agent, "spec-compliance").write_text("# Old five-artifact guidance\n")
    notes = tmp_path / "team-notes.md"
    notes.write_text("Keep the team's accepted UI decisions.\n")
    marker = tmp_path / ".govkit/marker.json"
    stored = json.loads(marker.read_text())
    stored["version"] = "0.20.0"
    marker.write_text(json.dumps(stored))
    cmd_upgrade(argparse.Namespace(target=str(tmp_path), force=False))
    assert_ui_guidance(tmp_path, agent)
    assert notes.read_text() == "Keep the team's accepted UI decisions.\n"


@pytest.mark.parametrize("agent", AGENTS)
def test_backend_keeps_its_five_artifact_contract_and_native_preflight(tmp_path, agent):
    apply(tmp_path, agent, "api")
    compliance = rule(tmp_path, agent, "spec-compliance").read_text(encoding="utf-8")
    section = compliance.split("## Feature Artifacts", 1)[1].split("## Defect fixes", 1)[0]
    assert set(re.findall(r"^[-*] `([^`]+)`", section, re.MULTILINE)) == COMMON_ARTIFACTS
    fix = (tmp_path / AGENT_LAYOUTS[agent].skills_dir / "govkit-fix-record/SKILL.md").read_text()
    assert "govkit-architecture-preflight" in fix
    assert "govkit-ui-architecture-preflight" not in fix
    assert "{{" not in fix


@pytest.mark.parametrize(
    "area,expected",
    [
        ("ui", "govkit-ui-architecture-preflight"),
        ("backend", "govkit-architecture-preflight"),
        ("data", "govkit-architecture-preflight"),
        ("", "{{architecture_preflight_skill}}"),
        ("unrecognized", "{{architecture_preflight_skill}}"),
    ],
)
def test_preflight_skill_token_uses_known_context_or_stays_unresolved(area, expected):
    assert expand_skill_tokens("{{architecture_preflight_skill}}", area) == expected


@pytest.mark.parametrize("agent", AGENTS)
@pytest.mark.parametrize("level", ["3", "4", "5"])
def test_angular_api_guidance_passes_shared_client_without_ambient_injection(
    tmp_path, agent, level
):
    apply(tmp_path, agent, "ui-angular", level)
    governance = tmp_path / "AGENTS.md" if agent == "codex" else rule(tmp_path, agent, "governance")
    root_api = governance.read_text().split("### Model — API", 1)[1].split("\n---", 1)[0]
    if agent == "claude-code":
        details = (
            rule(tmp_path, agent, "governance-src")
            .read_text()
            .split("## API (Model Layer)", 1)[1]
            .split("## Accessibility", 1)[0]
        )
    elif agent == "codex":
        details = (tmp_path / "src/features/api/AGENTS.md").read_text()
    else:
        details = rule(tmp_path, agent, "ui-api").read_text()
    problems = []
    for reference in re.findall(
        r"`((?:\.claude/rules|\.github/instructions)/[^`]+\.md)`", root_api
    ):
        if not (tmp_path / reference).is_file():
            problems.append(f"Angular API summary references missing {reference}")
    for name, text in (("root API summary", root_api), ("API rules", details)):
        if not re.search(r"ApiService.*(?:parameter|argument)", text):
            problems.append(f"{name} must require an explicit shared ApiService argument")
        if re.search(r"(?:take|wrapping|services with) `HttpClient`", text):
            problems.append(f"{name} bypasses the shared client")
    for snippet in re.findall(r"```typescript\n(.*?)```", details, re.DOTALL):
        if "fetchUserProfile" in snippet:
            if re.search(r"\binject\s*\(", snippet):
                problems.append("API example depends on ambient Angular injection")
            if not re.search(r"fetchUserProfile\(\s*api: ApiService,", snippet):
                problems.append("API example must receive the shared client")
    state = (tmp_path / "docs/ui/architecture/angular/STATE_MANAGEMENT.md").read_text()
    for function, callback in (
        ("injectUserProfile", "queryFn"),
        ("injectUpdateUserProfile", "mutationFn"),
    ):
        factory = state.split(f"export function {function}", 1)[1].split("\n}", 1)[0]
        if "const api = inject(ApiService);" not in factory.split("return inject", 1)[0]:
            problems.append(f"{function} must resolve ApiService before deferred {callback}")
    if (
        "fetchUserProfile(api, userId())" not in state
        or "updateUserProfile(api, userId, payload)" not in state
    ):
        problems.append("Query/mutation examples must pass the captured client to the API")
    assert not problems, "\n".join(problems)
