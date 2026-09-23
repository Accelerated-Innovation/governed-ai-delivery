"""Brownfield facts, explicit acceptance and focused rediscovery (test first)."""

import json
from pathlib import Path

import pytest

from cli.discovery import discover, load_baseline
from cli.discovery_scan import DiscoveryLimits
from cli.pack_loading import bundled_catalog
from cli.pack_store import apply_install, preview_install
from cli.profile_store import apply_profile, preview_materialization
from cli.schema_validation import DocumentError
from cli.version import GOVKIT_VERSION
from tests.test_pack_store import snapshot


def write(root, relative, content):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def accepted_profile(root, *, agent="codex", capabilities=("llm-evaluation",)):
    source = {"reference": "decisions/governance.md", "authority": "accepted"}
    document = {
        "schema_version": 1,
        "source": source,
        "repository": {"id": "brownfield"},
        "integrations": {"agent": agent},
        "capabilities": [{"id": c} for c in capabilities],
        "policy": {
            "source": source,
            "contracts": [
                {
                    "source": {"reference": "design/architecture.md", "authority": "accepted"},
                    "scope": ["src"],
                }
            ],
        },
    }
    write(root, "decisions/governance.md", "# Team decision\nAdopt evaluation only.\n")
    write(root, "design/architecture.md", "# Existing architecture\nHexagonal architecture.\n")
    return write(root, "desired.json", json.dumps(document))


def observations(report):
    return {o["source"]: o for o in report.document["observations"]}


def baseline(tmp_path, report):
    path = tmp_path / "reviewed.json"
    path.write_text(report.to_json())
    return load_baseline(path)


def test_documented_service_is_read_only_and_no_rule_is_silently_accepted(tmp_path):
    write(
        tmp_path,
        "pyproject.toml",
        '[project]\nname="service"\ndependencies=["fastapi>=0.100", "pytest"]\n',
    )
    write(tmp_path, "docs/architecture.md", "# Service design\nLayered architecture.\n")
    write(tmp_path, "docs/adr/001.md", "# Keep SQL\n")
    write(tmp_path, "AGENTS.md", "# Team conventions\n")
    write(tmp_path, "tests/test_service.py", "def test_health(): pass\n")
    write(tmp_path, ".github/workflows/tests.yml", "name: Tests\n")
    before = snapshot(tmp_path)
    report = discover(tmp_path, capabilities=("llm-evaluation",))
    facts = observations(report)
    assert {"manifest", "architecture", "decision", "guidance", "test", "ci"} <= {
        o["category"] for o in facts.values()
    }
    assert "framework:fastapi" in facts["pyproject.toml"]["signals"]
    assert all(o["digest"] and o["confidence"] for o in facts.values())
    assert report.document["accepted_profile"] is None
    assert report.document["proposed_profile"]["source"]["authority"] == "proposed"
    assert all(d["status"] == "pending" for d in report.document["decisions"])
    assert not report.document["operations"]
    assert report.to_json() == discover(tmp_path, capabilities=("llm-evaluation",)).to_json()
    assert snapshot(tmp_path) == before


def test_unknown_mcp_does_not_install_fastapi_and_missing_docs_are_not_global_blockers(tmp_path):
    write(tmp_path, "pyproject.toml", '[project]\ndependencies=["mcp>=1"]\n')
    write(tmp_path, "server.py", "from mcp.server.fastmcp import FastMCP\n")
    report = discover(tmp_path)
    raw = report.to_json()
    assert "tool:mcp" in raw
    assert "fastapi" not in raw.lower()
    assert report.document["proposed_profile"]["repository"] == {"id": tmp_path.name}
    assert not report.document["operations"]
    assert any(d["id"] == "architecture:." for d in report.document["decisions"])


@pytest.mark.parametrize("agent", ["codex", "copilot", "claude-code"])
def test_existing_docs_support_selected_capability_without_calibration_and_idempotent_install(
    tmp_path, agent
):
    target = tmp_path / "consumer"
    target.mkdir()
    source = accepted_profile(target, agent=agent)
    before = snapshot(target)
    report = discover(target, profile_path=source)
    assert report.document["install_ready"]
    assert report.document["accepted_profile"]["repository"]["id"] == "brownfield"
    assert any(
        d["status"] == "accepted" and "design/architecture.md" in d["sources"]
        for d in report.document["decisions"]
    )
    assert {op["path"] for op in report.document["operations"]} >= {
        ".govkit/profile.yaml",
        ".govkit/resolution.json",
        ".govkit/pack-lock.json",
    }
    assert snapshot(target) == before
    apply_profile(preview_materialization(source, target))
    apply_install(preview_install(source, target, bundled_catalog(), govkit_version=GOVKIT_VERSION))
    after = snapshot(target)
    assert all(after[p] == value for p, value in before.items())
    assert not (target / "features").exists()
    assert not (target / ".govkit/marker.json").exists()
    again = discover(target)
    assert again.document["install_ready"]
    assert all(op["action"] == "preserve" for op in again.document["operations"])
    apply_profile(preview_materialization(source, target))
    apply_install(preview_install(source, target, bundled_catalog(), govkit_version=GOVKIT_VERSION))
    assert snapshot(target) == after


def test_repeat_review_only_changed_sources_and_retains_policy(tmp_path):
    target = tmp_path / "consumer"
    target.mkdir()
    source = accepted_profile(target)
    write(target, "pyproject.toml", "[project]\ndependencies=[]\n")
    write(target, "src/main.py", "print('hello')\n")
    first = discover(target, profile_path=source)
    prior = baseline(tmp_path, first)
    assert discover(target, profile_path=source, baseline=prior).document["review"] == []
    write(target, "pyproject.toml", '[project]\ndependencies=["openai"]\n')
    before = snapshot(target)
    report = discover(target, profile_path=source, baseline=prior)
    assert [c["source"] for c in report.document["changes"]] == ["pyproject.toml"]
    assert report.document["accepted_profile"] == first.document["accepted_profile"]
    assert all(d["id"] != "architecture:src" for d in report.document["review"])
    outcome = report.maintenance_outcome()
    assert outcome.state.value == "warn"
    assert all(f.category == "maintenance" for f in outcome.findings)
    assert outcome.findings[0].evidence[0].digest
    assert snapshot(target) == before


@pytest.mark.parametrize(
    "relative,new_content",
    [
        ("pyproject.toml", '[project]\ndependencies=["mcp"]\n'),
        ("docs/architecture.md", "# New architecture\n"),
        ("src/model.py", "import openai\n"),
        ("tests/test_check.py", "def test_more(): pass\n"),
        (".github/workflows/test.yml", "name: Updated\n"),
        ("services/new/package.json", '{"dependencies":{"react":"19"}}'),
    ],
)
def test_maintenance_observes_each_relevant_change_without_policy_violation(
    tmp_path, relative, new_content
):
    target = tmp_path / "consumer"
    target.mkdir()
    prior = baseline(tmp_path, discover(target))
    write(target, relative, new_content)
    report = discover(target, baseline=prior)
    assert relative in {c["source"] for c in report.document["changes"]}
    assert report.document["review"]
    assert report.maintenance_outcome().state.value != "fail"
    assert report.document["accepted_profile"] is None


def test_scoped_monorepo_conventions_and_conflict_not_global_rewrite(tmp_path):
    for component, style in [("api", "Layered"), ("worker", "Hexagonal")]:
        write(tmp_path, f"services/{component}/pyproject.toml", "[project]\ndependencies=[]\n")
        write(
            tmp_path,
            f"services/{component}/docs/architecture.md",
            f"# Architecture\n{style} architecture.\n",
        )
    report = discover(tmp_path)
    architecture = [d for d in report.document["decisions"] if d["id"].startswith("architecture:")]
    assert {d["scope"] for d in architecture} >= {"services/api", "services/worker"}
    assert all(d["choices"] == ["retain", "improve", "migrate"] for d in architecture)
    assert "scoped-conventions" in {d["id"] for d in report.document["decisions"]}
    assert not report.document["operations"]


def test_accepted_reference_change_reopens_only_its_scope(tmp_path):
    target = tmp_path / "consumer"
    target.mkdir()
    source = accepted_profile(target)
    prior = baseline(tmp_path, discover(target, profile_path=source))
    write(target, "design/architecture.md", "# Architecture\nLayered architecture.\n")
    report = discover(target, profile_path=source, baseline=prior)
    assert any(
        d["scope"] == "src" and d["status"] == "review-required" for d in report.document["review"]
    )
    assert report.document["accepted_profile"] == prior["accepted_profile"]
    assert report.document[
        "install_ready"
    ]  # A changed observation does not waive/reject accepted policy.


def test_symlinks_limits_and_unreadable_files_are_explicit(tmp_path, monkeypatch):
    outside = write(tmp_path, "private.txt", "SECRET_NEVER_READ")
    target = tmp_path / "consumer"
    target.mkdir()
    (target / "AGENTS.md").symlink_to(outside)
    write(target, "pyproject.toml", "x" * 100)
    report = discover(target, limits=DiscoveryLimits(max_bytes=32))
    assert "SECRET_NEVER_READ" not in report.to_json()
    assert not report.document["coverage"]["complete"]
    assert observations(report)["AGENTS.md"]["status"] == "unavailable"
    assert observations(report)["pyproject.toml"]["status"] == "limited"
    assert report.maintenance_outcome().state.value == "unknown"


def test_partial_scan_cannot_claim_missing_baseline_file_was_removed(tmp_path):
    target = tmp_path / "consumer"
    target.mkdir()
    write(target, "src/a.py", "import openai\n")
    write(target, "src/b.py", "import mcp\n")
    prior = baseline(tmp_path, discover(target))
    report = discover(target, baseline=prior, limits=DiscoveryLimits(max_files=1))
    assert not report.document["coverage"]["complete"]
    assert all(c["kind"] != "removed" for c in report.document["changes"])
    assert report.document["review"]


def test_baseline_schema_identity_and_tampering_are_rejected(tmp_path):
    target = tmp_path / "consumer"
    target.mkdir()
    report = discover(target)
    prior = baseline(tmp_path, report)
    prior["schema_version"] = 2
    with pytest.raises(DocumentError):
        discover(target, baseline=prior)
    prior = baseline(tmp_path, report)
    prior["repository"] = "other"
    with pytest.raises(DocumentError, match="repository"):
        discover(target, baseline=prior)
    raw = json.loads(report.to_json())
    raw["unexpected"] = True
    path = write(tmp_path, "bad.json", json.dumps(raw))
    with pytest.raises(DocumentError):
        load_baseline(path)


def test_invalid_existing_profile_does_not_fall_back_to_ungoverned(tmp_path):
    write(tmp_path, ".govkit/profile.yaml", "schema_version: 999\n")
    with pytest.raises(DocumentError):
        discover(tmp_path)


def test_reference_selection_change_is_not_file_removal(tmp_path):
    target = tmp_path / "consumer"
    target.mkdir()
    write(target, "policy.txt", "Project policy")
    prior = baseline(tmp_path, discover(target, references=("policy.txt",)))
    report = discover(target, baseline=prior)
    assert all(c["kind"] != "removed" for c in report.document["changes"])
    assert any(d["id"] == "observation-coverage-changed" for d in report.document["review"])


def test_reference_manifest_keeps_boundary_and_signals(tmp_path):
    write(tmp_path, "services/tools/pyproject.toml", '[project]\ndependencies=["mcp"]\n')
    report = discover(tmp_path, references=("services/tools/pyproject.toml",))
    assert "services/tools" in report.document["boundaries"]
    assert "tool:mcp" in observations(report)["services/tools/pyproject.toml"]["signals"]


def test_missing_required_context_names_only_dependent_work(tmp_path):
    source = accepted_profile(tmp_path)
    doc = json.loads(source.read_text())
    doc["capabilities"][0]["requires_context"] = ["stack"]
    source.write_text(json.dumps(doc))
    report = discover(tmp_path, profile_path=source)
    assert not report.document["install_ready"]
    assert any(
        "llm-evaluation" in d["affects"] and "stack" in d["reason"]
        for d in report.document["review"]
    )


def test_user_edit_protection_and_stale_preview_are_enforced_in_adoption(tmp_path):
    source = accepted_profile(tmp_path)
    preview = preview_materialization(source, tmp_path)
    source.write_text(source.read_text() + "\n")
    with pytest.raises(DocumentError, match="Stale"):
        apply_profile(preview)
    assert not (tmp_path / ".govkit").exists()


def test_permission_error_does_not_leak_content_or_look_like_success(tmp_path, monkeypatch):
    path = write(tmp_path, "docs/architecture.md", "private content")
    original = Path.open

    def deny(self, *args, **kwargs):
        if self == path:
            raise PermissionError("SECRET_DIAGNOSTIC")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", deny)
    report = discover(tmp_path)
    assert observations(report)["docs/architecture.md"]["status"] == "unavailable"
    assert "SECRET_DIAGNOSTIC" not in report.to_json()
    assert report.document["review"]


def test_new_model_needs_are_recommended_at_current_version(tmp_path):
    target = tmp_path / "consumer"
    target.mkdir()
    source = accepted_profile(target, capabilities=("application-governance",))
    write(target, ".govkit/marker.json", json.dumps({"version": GOVKIT_VERSION}))
    prior = baseline(tmp_path, discover(target, profile_path=source))
    write(target, "src/model.py", "from openai import OpenAI\n")
    report = discover(target, profile_path=source, baseline=prior)
    suggestion = next(
        d for d in report.document["review"] if d["id"] == "capability:llm-evaluation"
    )
    assert suggestion["status"] == "pending" and suggestion["sources"] == ["src/model.py"]
    assert report.document["accepted_profile"] == prior["accepted_profile"]
    assert report.maintenance_outcome().state.value == "warn"


def test_deleted_and_moved_boundaries_are_scoped_observations(tmp_path):
    target = tmp_path / "consumer"
    target.mkdir()
    source = write(target, "services/api/pyproject.toml", "[project]\ndependencies=[]\n")
    prior = baseline(tmp_path, discover(target))
    source.unlink()
    write(target, "services/gateway/pyproject.toml", "[project]\ndependencies=[]\n")
    report = discover(target, baseline=prior)
    assert {(c["kind"], c["scope"]) for c in report.document["changes"]} == {
        ("removed", "services/api"),
        ("added", "services/gateway"),
    }
    assert report.maintenance_outcome().state.value == "warn"


def test_metadata_and_source_files_are_not_executed_or_networked(tmp_path, monkeypatch):
    import socket
    import subprocess

    source = accepted_profile(tmp_path)
    write(tmp_path, "pyproject.toml", '[project]\ndependencies=["mcp"]\n')
    write(tmp_path, "server.py", "raise RuntimeError('must not run')\n")

    def deny(*args, **kwargs):
        raise AssertionError("Unexpected execution/network")

    monkeypatch.setattr(socket, "create_connection", deny)
    monkeypatch.setattr(subprocess, "run", deny)
    assert discover(tmp_path, profile_path=source).document["install_ready"]


def test_transition_modes_preserve_scoped_contracts_exceptions_and_exit_reference(tmp_path):
    source = accepted_profile(tmp_path)
    doc = json.loads(source.read_text())

    def ref(path):
        write(tmp_path, path, "# Team contract\n")
        return {"reference": path, "authority": "accepted"}

    transitions = []
    for component, mode in [("stable", "retain"), ("api", "improve"), ("worker", "migrate")]:
        transitions.append(
            {
                "id": component,
                "source": ref(f"decisions/{component}.md"),
                "scope": [component],
                "mode": mode,
                "current": [
                    {"source": ref(f"design/{component}-current.md"), "scope": [component]}
                ],
                "target": []
                if mode == "retain"
                else [
                    {"source": ref(f"design/{component}-target-and-exit.md"), "scope": [component]}
                ],
                "applies_to": "new-and-changed",
                "exceptions": [
                    {
                        "id": "existing",
                        "source": ref(f"decisions/{component}-existing.md"),
                        "scope": [f"{component}/legacy"],
                        "expires_at": None,
                    }
                ],
            }
        )
    doc["policy"]["transitions"] = transitions
    source.write_text(json.dumps(doc))
    before = snapshot(tmp_path)
    report = discover(tmp_path, profile_path=source)
    decisions = [d for d in report.document["decisions"] if d["id"].startswith("transition:")]
    assert len(decisions) == 3 and all(d["status"] == "accepted" for d in decisions)
    assert report.document["accepted_profile"]["policy"]["transitions"] == transitions
    assert snapshot(tmp_path) == before


def test_legacy_installation_namespace_blocks_only_install_preview(tmp_path):
    source = accepted_profile(tmp_path)
    write(tmp_path, ".govkit", '{"version":"0.1.0"}')
    before = snapshot(tmp_path)
    report = discover(tmp_path, profile_path=source)
    assert not report.document["install_ready"]
    assert any(d["id"] == "install:preview-unavailable" for d in report.document["review"])
    assert observations(report)["design/architecture.md"]["digest"]
    assert snapshot(tmp_path) == before


def test_policy_only_change_has_canonical_maintenance_finding(tmp_path):
    target = tmp_path / "consumer"
    target.mkdir()
    source = accepted_profile(target)
    prior = baseline(tmp_path, discover(target, profile_path=source))
    doc = json.loads(source.read_text())
    doc["capabilities"].append({"id": "application-governance"})
    source.write_text(json.dumps(doc))
    outcome = discover(target, profile_path=source, baseline=prior).maintenance_outcome()
    assert any(
        f.code == "accepted-profile-changed" and f.category == "maintenance"
        for f in outcome.findings
    )


def test_proposed_input_cannot_be_accepted_by_baseline_roundtrip(tmp_path):
    doc = discover(tmp_path).document
    doc["install_ready"] = True
    path = write(tmp_path, "bad.json", json.dumps(doc))
    with pytest.raises(DocumentError):
        load_baseline(path)


@pytest.mark.parametrize("limit", ["max_depth", "max_entries", "max_total_bytes"])
def test_each_scan_budget_exposes_incomplete_coverage(tmp_path, limit):
    write(tmp_path, "a/b/c/architecture.md", "# architecture\n" * 10)
    write(tmp_path, "README.md", "# Read me\n" * 10)
    report = discover(tmp_path, limits=DiscoveryLimits(**{limit: 1}))
    assert not report.document["coverage"]["complete"]
    assert report.maintenance_outcome().state.value == "unknown"


def test_bundled_brownfield_examples_cover_four_scenarios(tmp_path):
    from cli import paths

    examples = sorted((paths.GOVERNANCE_DIR / "examples/discovery").glob("*.json"))
    assert {p.stem for p in examples} == {
        "documented-service",
        "sparse-repository",
        "unfamiliar-mcp",
        "monorepo",
    }
    for example in examples:
        data = json.loads(example.read_text())
        target = tmp_path / example.stem
        target.mkdir()
        for relative, content in data["files"].items():
            write(target, relative, content)
        profile_path = (
            write(target, "accepted-profile.json", json.dumps(data["profile"]))
            if data.get("profile")
            else None
        )
        before = snapshot(target)
        report = discover(target, profile_path=profile_path)
        assert report.document["observations"]
        assert snapshot(target) == before
        assert (
            discover(target, profile_path=profile_path, baseline=report.document).document["review"]
            == []
        )
        if example.stem == "unfamiliar-mcp":
            assert "fastapi" not in report.to_json().lower()


def test_discovery_maintenance_outcome_uses_the_existing_report_contract(tmp_path):
    from cli.check_models import CheckContext, CheckSpec, Identity
    from cli.check_runner import CheckRegistry, load_report, run_checks

    write(tmp_path, "server.py", "import openai\n")
    discovery = discover(tmp_path)
    registry = CheckRegistry()
    registry.register("repository-fit", lambda context: discovery.maintenance_outcome())
    spec = CheckSpec("repository-fit", False, "Review observed needs", "explicit-discovery", (".",))
    report = run_checks(CheckContext(tmp_path, Identity(tmp_path.name)), (spec,), registry)
    record = tmp_path / "checks.json"
    record.write_text(report.to_json())
    assert load_report(record).to_json() == report.to_json()
    assert report.results[0].outcome.state.value == "warn"
    assert all(f.category == "maintenance" for f in report.results[0].outcome.findings)
