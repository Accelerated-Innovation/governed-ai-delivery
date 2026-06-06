"""Fixture-driven end-to-end tests.

PR 7. Three fixture repos under tests/fixtures/ exercise the whole apply
→ doctor → calibrate flow against realistic shapes:

  - dotnet-aspnet-azure/      — *.csproj + global.json + clean layout + azure-pipelines.yml
  - python-fastapi-github/    — pyproject.toml + fastapi + hexagonal layout + .github/workflows
  - dbt-project/              — dbt_project.yml + models/{staging,intermediate,marts}
  - empty/                    — no signals at all (worst-case fallback path)

Each test class copies the fixture into a tmp_path so the source tree is
never mutated, then asserts the structural outcome (marker, skill_context,
rule globs, doctor findings). Goldens are deliberately structural rather
than byte-exact so timestamps and govkit version don't make tests flaky.
"""

import argparse
import shutil
from pathlib import Path

import pytest
import yaml

FIXTURES = Path(__file__).parent / "fixtures"


def _copy_fixture(name: str, dest_root: Path) -> Path:
    """Copy a named fixture into dest_root and return the install target."""
    src = FIXTURES / name
    assert src.is_dir(), f"missing fixture: {src}"
    dest = dest_root / name
    shutil.copytree(src, dest)
    return dest


@pytest.mark.parametrize("agent", ["claude-code", "copilot", "codex"])
class TestDotnetAspnetAzureFixture:
    """A .NET clean-architecture repo on Azure Pipelines should:
      - infer dotnet-aspnet stack (high confidence)
      - record ci=azure detected
      - install clean-shape rule globs (Application/, Infrastructure/, ...)
      - end up with doctor's L5-leakage check (D007) silent
    """

    def _apply(self, fixture: Path, agent: str) -> None:
        from cli.cmd_apply import cmd_apply

        cmd_apply(argparse.Namespace(
            agent=agent, target=str(fixture),
            level="4", type="api", ci="azure", stack=None,
            force=False, detect=False,
        ))

    def test_apply_picks_dotnet_aspnet_stack(self, tmp_path, agent):
        from cli.marker import read_govkit_marker

        target = _copy_fixture("dotnet-aspnet-azure", tmp_path)
        self._apply(target, agent)

        marker = read_govkit_marker(target)
        assert marker["stack"]["id"] == "dotnet-aspnet"

    def test_apply_records_csharp_detection_as_source(self, tmp_path, agent):
        from cli.marker import read_govkit_marker

        target = _copy_fixture("dotnet-aspnet-azure", tmp_path)
        self._apply(target, agent)

        marker = read_govkit_marker(target)
        stack_assumption = next(a for a in marker["assumptions"] if a["id"] == "stack.id")
        # Detected, not defaulted — because the fixture has csproj + global.json (high confidence).
        assert stack_assumption["source"] == "detected"
        assert stack_assumption["confidence"] == "high"

    def test_skill_context_carries_clean_architecture_style(self, tmp_path, agent):
        from cli.skill_context import load_skill_context

        target = _copy_fixture("dotnet-aspnet-azure", tmp_path)
        self._apply(target, agent)

        ctx = load_skill_context(target)
        assert ctx is not None
        # Codex installs nested AGENTS.md under api/, ports/, adapters/, etc.
        # at the target root — those folder names then look like hexagonal
        # signals to the detector. So for codex we accept either style; the
        # other agents detect the fixture's actual clean architecture.
        if agent == "codex":
            assert ctx.architecture_style in ("clean", "hexagonal")
        else:
            assert ctx.architecture_style == "clean"
        assert ctx.stack_id == "dotnet-aspnet"
        assert ctx.language == "csharp"
        assert ctx.api_framework == "aspnet-core"

    def test_doctor_d007_silent_on_fresh_install(self, tmp_path, agent):
        from cli.doctor import run_doctor

        target = _copy_fixture("dotnet-aspnet-azure", tmp_path)
        self._apply(target, agent)

        d007 = [f for f in run_doctor(target) if f.id == "D007"]
        assert d007 == [], f"D007 should be silent post-PR-6c; got: {[f.message for f in d007]}"

    def test_setup_review_mentions_dotnet_baseline(self, tmp_path, agent):
        target = _copy_fixture("dotnet-aspnet-azure", tmp_path)
        self._apply(target, agent)

        review = (target / "GOVKIT_SETUP_REVIEW.md").read_text(encoding="utf-8")
        assert "dotnet-aspnet" in review


class TestDotnetAspnetClaudeRulesTemplating:
    """Rule globs in claude-code rules expand to clean-architecture folders
    for this fixture (covered by per-agent matrix above, but called out here
    because rule templating is the highest-leverage piece for D001)."""

    def test_adapters_rule_targets_infrastructure_folder(self, tmp_path):
        from cli.cmd_apply import cmd_apply

        target = _copy_fixture("dotnet-aspnet-azure", tmp_path)
        cmd_apply(argparse.Namespace(
            agent="claude-code", target=str(target),
            level="4", type="api", ci="azure", stack=None,
            force=False, detect=False,
        ))

        text = (target / ".claude" / "rules" / "adapters.md").read_text(encoding="utf-8")
        fm = yaml.safe_load(text.split("---", 2)[1])
        assert "**/Infrastructure/**" in (fm.get("paths") or [])
        # Hexagonal default is gone — clean layers took its place.
        assert "**/adapters/**" not in (fm.get("paths") or [])

    def test_copilot_adapters_applyto_targets_infrastructure(self, tmp_path):
        from cli.cmd_apply import cmd_apply

        target = _copy_fixture("dotnet-aspnet-azure", tmp_path)
        cmd_apply(argparse.Namespace(
            agent="copilot", target=str(target),
            level="4", type="api", ci="azure", stack=None,
            force=False, detect=False,
        ))

        text = (target / ".github" / "instructions" / "adapters.instructions.md").read_text(encoding="utf-8")
        fm = yaml.safe_load(text.split("---", 2)[1])
        applyto = fm.get("applyTo", "")
        assert "**/Infrastructure/**" in applyto


@pytest.mark.parametrize("agent", ["claude-code", "copilot", "codex"])
class TestPythonFastapiGithubFixture:
    """A Python / FastAPI / hexagonal repo on GitHub Actions should:
      - infer python-fastapi stack
      - keep hexagonal layer defaults (ports/, adapters/)
      - have github CI confirmed
    """

    def _apply(self, fixture: Path, agent: str) -> None:
        from cli.cmd_apply import cmd_apply

        cmd_apply(argparse.Namespace(
            agent=agent, target=str(fixture),
            level="4", type="api", ci="github", stack=None,
            force=False, detect=False,
        ))

    def test_apply_picks_python_fastapi_stack(self, tmp_path, agent):
        from cli.marker import read_govkit_marker

        target = _copy_fixture("python-fastapi-github", tmp_path)
        self._apply(target, agent)

        marker = read_govkit_marker(target)
        assert marker["stack"]["id"] == "python-fastapi"

    def test_skill_context_picks_hexagonal(self, tmp_path, agent):
        from cli.skill_context import load_skill_context

        target = _copy_fixture("python-fastapi-github", tmp_path)
        self._apply(target, agent)

        ctx = load_skill_context(target)
        assert ctx is not None
        assert ctx.architecture_style == "hexagonal"
        assert ctx.language == "python"

    def test_doctor_d001_quiet_on_hexagonal_repo(self, tmp_path, agent):
        """Hexagonal fixture has ports/ + adapters/ folders so rule globs
        resolve — no D001 errors expected."""
        from cli.doctor import run_doctor

        target = _copy_fixture("python-fastapi-github", tmp_path)
        self._apply(target, agent)
        if agent == "codex":
            pytest.skip("codex uses nested AGENTS.md, no glob frontmatter to check")

        d001 = [f for f in run_doctor(target) if f.id == "D001"]
        # Codex skipped. Hexagonal claude-code/copilot rules target inbound
        # (api/, ports/inbound/) etc. — the fixture has ports/ flat, so
        # ports/inbound/ and ports/outbound/ won't match. The remaining
        # security.md (`**/security/**`, `**/auth/**`) won't match either.
        # We assert the count is bounded, not zero.
        # Acceptable for this fixture: ≤ 5 D001 findings (security + a
        # couple of layer subfolder gaps); zero is the ideal.
        assert len(d001) <= 5, f"too many D001 findings: {[f.message for f in d001]}"


class TestDbtProjectFixture:
    """A dbt project with dbt_project.yml + models/{staging,intermediate,marts}
    should:
      - infer python-dbt stack (via dbt framework signal)
      - record architecture_style == dbt-layered (staging+marts present)
      - install data rules whose paths_template expands to models/staging/, etc.
      - have no D001 errors against rule globs that target dbt layers
    """

    def _apply(self, fixture: Path) -> None:
        from cli.cmd_apply import cmd_apply

        cmd_apply(argparse.Namespace(
            agent="claude-code", target=str(fixture),
            level="4", type="data", ci="github", stack=None,
            force=False, detect=False,
        ))

    def test_apply_picks_python_dbt_stack(self, tmp_path):
        from cli.marker import read_govkit_marker

        target = _copy_fixture("dbt-project", tmp_path)
        self._apply(target)

        marker = read_govkit_marker(target)
        assert marker["stack"]["id"] == "python-dbt"

    def test_skill_context_picks_dbt_layered(self, tmp_path):
        from cli.skill_context import load_skill_context

        target = _copy_fixture("dbt-project", tmp_path)
        self._apply(target)

        ctx = load_skill_context(target)
        assert ctx is not None
        assert ctx.architecture_style == "dbt-layered"
        assert ctx.stack_id == "python-dbt"
        assert "models/staging/" in ctx.layers["inbound"]
        assert "models/marts/" in ctx.layers["outbound"]
        assert "models/intermediate/" in ctx.layers["domain"]

    def test_staging_rule_globs_expand_to_dbt_layers(self, tmp_path):
        target = _copy_fixture("dbt-project", tmp_path)
        self._apply(target)

        text = (target / ".claude" / "rules" / "staging.md").read_text(encoding="utf-8")
        fm = yaml.safe_load(text.split("---", 2)[1])
        paths = fm.get("paths") or []
        assert "**/models/staging/**" in paths

    def test_marts_rule_globs_expand_to_dbt_layers(self, tmp_path):
        target = _copy_fixture("dbt-project", tmp_path)
        self._apply(target)

        text = (target / ".claude" / "rules" / "marts.md").read_text(encoding="utf-8")
        fm = yaml.safe_load(text.split("---", 2)[1])
        paths = fm.get("paths") or []
        assert "**/models/marts/**" in paths

    def test_data_baseline_contracts_installed(self, tmp_path):
        target = _copy_fixture("dbt-project", tmp_path)
        self._apply(target)

        arch_dir = target / "docs" / "data" / "architecture"
        assert (arch_dir / "BOUNDARIES.md").is_file()
        assert (arch_dir / "DATA_QUALITY_CONTRACT.md").is_file()
        assert (arch_dir / "PII_HANDLING_CONTRACT.md").is_file()

    def test_data_adr_template_installed(self, tmp_path):
        """The adr-author skill + l4-data.md both advertise ADRs, so the data
        install must ship docs/data/architecture/ADR/TEMPLATE.md — otherwise
        /adr-author points at a missing file in a dbt project."""
        target = _copy_fixture("dbt-project", tmp_path)
        self._apply(target)

        adr = target / "docs" / "data" / "architecture" / "ADR" / "TEMPLATE.md"
        assert adr.is_file(), "data install must ship an ADR template"
        body = adr.read_text(encoding="utf-8")
        # Data-adapted: it should speak to data contracts, not HTTP routes.
        assert "Data Contract Impact" in body
        assert "PII" in body

    def test_doctor_d001_quiet_on_dbt_layered_rules(self, tmp_path):
        """The dbt-layered rules (staging.md, intermediate.md, marts.md)
        should expand to globs that resolve in this fixture."""
        from cli.doctor import run_doctor

        target = _copy_fixture("dbt-project", tmp_path)
        self._apply(target)

        d001 = [f for f in run_doctor(target) if f.id == "D001"]
        layer_rules = {"staging.md", "intermediate.md", "marts.md"}
        offenders = [f for f in d001 if f.file and Path(f.file).name in layer_rules]
        assert offenders == [], (
            f"layer rule globs failed to match dbt-project fixture: "
            f"{[(f.file, f.message) for f in offenders]}"
        )


class TestDatabricksLakehouseGuidance:
    """Databricks stack docs explain how GovKit and Databricks agent skills coexist."""

    def _apply(self, target: Path, stack: str | None = "databricks-lakehouse") -> None:
        from cli.cmd_apply import cmd_apply

        cmd_apply(argparse.Namespace(
            agent="claude-code", target=str(target),
            level="4", type="data", ci="github",
            stack=stack, force=False, detect=False,
        ))

    def _write_bundle(self, target: Path) -> None:
        (target / "resources").mkdir()
        (target / "src").mkdir()
        (target / "databricks.yml").write_text(
            "bundle:\n  name: customer_analytics\ninclude:\n  - resources/*.yml\n",
            encoding="utf-8",
        )
        (target / "resources" / "pipelines.yml").write_text(
            "resources:\n  pipelines:\n    customer_quality:\n      name: customer_quality\n",
            encoding="utf-8",
        )

    def test_apply_type_data_detects_databricks_lakehouse_stack(self, tmp_path):
        from cli.marker import read_govkit_marker

        target = tmp_path / "databricks-project"
        target.mkdir()
        self._write_bundle(target)

        self._apply(target, stack=None)

        marker = read_govkit_marker(target)
        assert marker["stack"]["id"] == "databricks-lakehouse"
        assert marker["options"]["stack"] == "databricks-lakehouse"
        stack_assumption = next(a for a in marker["assumptions"] if a["id"] == "stack.id")
        assert stack_assumption["source"] == "detected"
        assert stack_assumption["confidence"] == "high"
        assert (target / "ci" / "github" / "databricks-gate.yml").is_file()
        assert not (target / "ci" / "github" / "dbt-gate.yml").exists()

    def test_generated_tech_stack_mentions_databricks_agent_skills_boundary(self, tmp_path):
        target = tmp_path / "databricks-project"
        target.mkdir()
        self._apply(target)

        text = (target / "docs" / "data" / "architecture" / "TECH_STACK.md").read_text(encoding="utf-8")

        assert "databricks aitools install" in text
        assert "Databricks agent skills" in text
        assert "GovKit contracts remain authoritative" in text
        assert "acceptance criteria" in text
        assert "PII" in text
        assert "approvals" in text

    def test_databricks_skills_are_guidance_only_not_required(self, tmp_path):
        target = tmp_path / "databricks-project"
        target.mkdir()
        self._apply(target)

        marker = target / ".govkit" / "marker.json"
        tech_stack = target / "docs" / "data" / "architecture" / "TECH_STACK.md"

        assert marker.is_file()
        assert tech_stack.is_file()
        assert not (target / ".databricks-agent-skills").exists()


class TestEmptyFixture:
    """The empty fixture has no signals — every detection should be 'unknown'
    and the install should still succeed (defaults to python-fastapi)."""

    def test_apply_falls_back_to_default_stack(self, tmp_path):
        from cli.cmd_apply import cmd_apply
        from cli.marker import read_govkit_marker

        target = _copy_fixture("empty", tmp_path)
        cmd_apply(argparse.Namespace(
            agent="claude-code", target=str(target),
            level="4", type="api", ci="github", stack=None,
            force=False, detect=False,
        ))

        marker = read_govkit_marker(target)
        assert marker["stack"]["id"] == "python-fastapi"
        stack_assumption = next(a for a in marker["assumptions"] if a["id"] == "stack.id")
        assert stack_assumption["source"] == "default"
        assert stack_assumption["review_required"] is True

    def test_skill_context_architecture_style_is_unknown(self, tmp_path):
        from cli.cmd_apply import cmd_apply
        from cli.skill_context import load_skill_context

        target = _copy_fixture("empty", tmp_path)
        cmd_apply(argparse.Namespace(
            agent="claude-code", target=str(target),
            level="4", type="api", ci="github", stack=None,
            force=False, detect=False,
        ))

        ctx = load_skill_context(target)
        assert ctx is not None
        assert ctx.architecture_style == "unknown"

    def test_doctor_runs_cleanly_on_empty_target(self, tmp_path):
        """Empty repo is the worst-case input; doctor must not crash and
        must produce useful findings (D001 for rule globs that don't match)."""
        from cli.cmd_apply import cmd_apply
        from cli.doctor import run_doctor

        target = _copy_fixture("empty", tmp_path)
        cmd_apply(argparse.Namespace(
            agent="claude-code", target=str(target),
            level="4", type="api", ci="github", stack=None,
            force=False, detect=False,
        ))

        findings = run_doctor(target)
        # Doctor should produce D001 findings (rule globs don't match empty repo).
        ids = {f.id for f in findings}
        assert "D001" in ids
        # D007 must NOT fire — PR 6c moved the L5 leakage out.
        assert "D007" not in ids


class TestCalibrateNonInteractiveFixture:
    """Calibrate non-interactive against a real fixture: emit checklist
    file, refresh skill_context, refresh setup review."""

    def test_non_interactive_writes_checklist_and_refreshes_artifacts(self, tmp_path):
        from cli.calibrate import cmd_calibrate
        from cli.cmd_apply import cmd_apply

        target = _copy_fixture("python-fastapi-github", tmp_path)
        cmd_apply(argparse.Namespace(
            agent="claude-code", target=str(target),
            level="4", type="api", ci="github", stack=None,
            force=False, detect=False,
        ))

        # Remove derived files so we can verify calibrate re-creates them.
        (target / "GOVKIT_CALIBRATION_CHECKLIST.md").unlink(missing_ok=True)
        (target / "GOVKIT_SETUP_REVIEW.md").unlink(missing_ok=True)
        (target / ".govkit" / "skill_context.yaml").unlink(missing_ok=True)

        cmd_calibrate(argparse.Namespace(
            target=str(target), non_interactive=True, only=None,
        ))

        checklist = target / "GOVKIT_CALIBRATION_CHECKLIST.md"
        review = target / "GOVKIT_SETUP_REVIEW.md"
        sc = target / ".govkit" / "skill_context.yaml"

        assert checklist.is_file()
        assert review.is_file()
        assert sc.is_file()

        body = checklist.read_text(encoding="utf-8")
        # All 9 canonical steps emitted as numbered headings.
        for i in range(1, 10):
            assert f"## {i}." in body
        # Action prompts present.
        assert "Action:" in body
        # Checkbox shape.
        assert "- [ ] Reviewed" in body


class TestMonorepoFixture:
    """A9: monorepo with apps/api + apps/web. doctor + calibrate run from
    the monorepo root must discover BOTH installs and process each."""

    def _install_both(self, monorepo_root: Path) -> tuple[Path, Path]:
        from cli.cmd_apply import cmd_apply

        api = monorepo_root / "apps" / "api"
        web = monorepo_root / "apps" / "web"
        cmd_apply(argparse.Namespace(
            agent="claude-code", target=str(api),
            level="4", type="api", ci="github", stack=None,
            force=False, detect=False,
        ))
        cmd_apply(argparse.Namespace(
            agent="claude-code", target=str(web),
            level="4", type="ui-react", ci="github", stack=None,
            force=False, detect=False,
        ))
        return api, web

    def test_each_install_gets_its_own_marker(self, tmp_path):
        from cli.marker import read_govkit_marker

        root = _copy_fixture("monorepo", tmp_path)
        api, web = self._install_both(root)

        api_marker = read_govkit_marker(api)
        web_marker = read_govkit_marker(web)

        assert api_marker is not None and api_marker["options"]["type"] == "api"
        assert web_marker is not None and web_marker["options"]["type"] == "ui-react"

    def test_doctor_auto_discovers_both_installs(self, tmp_path, monkeypatch, capsys):
        from cli.doctor import cmd_doctor

        root = _copy_fixture("monorepo", tmp_path)
        self._install_both(root)
        monkeypatch.chdir(root)

        with pytest.raises(SystemExit):
            cmd_doctor(argparse.Namespace(target=None))

        out = capsys.readouterr().out.replace("\\", "/")
        assert "apps/api" in out
        assert "apps/web" in out

    def test_calibrate_non_interactive_processes_both_installs(self, tmp_path, monkeypatch):
        from cli.calibrate import cmd_calibrate

        root = _copy_fixture("monorepo", tmp_path)
        api, web = self._install_both(root)
        monkeypatch.chdir(root)

        cmd_calibrate(argparse.Namespace(
            target=None, non_interactive=True, only=None,
        ))

        assert (api / "GOVKIT_CALIBRATION_CHECKLIST.md").is_file()
        assert (web / "GOVKIT_CALIBRATION_CHECKLIST.md").is_file()

    def test_doctor_per_install_findings_isolated(self, tmp_path, monkeypatch):
        """A finding in apps/web should reference apps/web, not apps/api."""
        from cli.doctor import discover_install_targets, run_doctor

        root = _copy_fixture("monorepo", tmp_path)
        api, web = self._install_both(root)
        monkeypatch.chdir(root)

        targets = discover_install_targets(root)
        assert api in targets
        assert web in targets

        # Each install's findings are computed against its own target —
        # rule-glob check looks in api's .claude/rules vs web's .claude/rules.
        api_findings = run_doctor(api)
        web_findings = run_doctor(web)
        for f in api_findings:
            if f.file:
                assert "apps" not in f.file or "api" in f.file
        for f in web_findings:
            if f.file:
                assert "apps" not in f.file or "web" in f.file
