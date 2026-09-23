"""Per-request plans preserve policy and make proportional evidence explicit."""

import json

import pytest

from cli.pack_loading import bundled_catalog
from cli.pack_store import apply_install, preview_install
from cli.profiles import parse_profile
from cli.schema_validation import DocumentError
from cli.version import GOVKIT_VERSION
from cli.workflow_store import load_workflow_plan, plan_request
from cli.workflows import IMPACTS, parse_request, resolve_workflow
from tests.test_discovery import write
from tests.test_pack_store import snapshot


def request(change="enhancement", **impacts):
    return {
        "schema_version": 1,
        "id": "change-123",
        "source": "https://tracker.invalid/123",
        "summary": "Return the agreed result for this bounded request.",
        "confirmation": "confirmed",
        "change": change,
        "scope": ["src"],
        "impacts": {
            **dict.fromkeys(IMPACTS, False),
            "bounded": True,
            "within-contracts": True,
            "new-behavior": change not in {"defect", "refactor", "maintenance"},
            **impacts,
        },
        "acceptance": ["The agreed behavior is covered by tests."],
        "references": [],
        "preference": "auto",
    }


def install(
    target,
    *,
    capabilities=("application-governance", "gherkin-delivery", "llm-evaluation"),
    agent="codex",
    workflows=(),
    checks=(),
):
    source = {"reference": "policy.md", "authority": "accepted"}
    profile = parse_profile(
        {
            "schema_version": 1,
            "source": source,
            "repository": {"id": "service"},
            "integrations": {"agent": agent},
            "capabilities": [{"id": c} for c in capabilities],
            "policy": {
                "source": source,
                "workflows": list(workflows),
                "required_checks": [{"id": c} for c in checks],
                "contracts": [
                    {
                        "source": {"reference": "architecture.md", "authority": "accepted"},
                        "scope": ["src"],
                    }
                ],
            },
        }
    )
    write(target, "policy.md", "# Accepted team policy\n")
    write(target, "architecture.md", "# Accepted contracts and NFRs\n")
    write(target, "src/service.py", "def result(): return 42\n")
    write(target, "tests/test_service.py", "def test_result(): assert True\n")
    source_path = write(target, ".govkit/profile.yaml", json.dumps(profile.document))
    apply_install(
        preview_install(source_path, target, bundled_catalog(), govkit_version=GOVKIT_VERSION)
    )
    return profile


def plan(target, document, **kwargs):
    return plan_request(target, parse_request(document), **kwargs)


def ids(report, name):
    return {item["id"] for item in report.document[name]}


def test_one_profile_routes_defect_small_refactor_and_full_feature_without_writes(tmp_path):
    install(tmp_path)
    before = snapshot(tmp_path)
    cases = [
        ("defect", "defect"),
        ("enhancement", "bounded"),
        ("refactor", "bounded"),
        ("feature", "full-feature"),
    ]
    for change, workflow in cases:
        document = request(change)
        if change == "defect":
            document["references"] = [
                {
                    "kind": "established-behavior",
                    "reference": "architecture.md",
                    "authority": "accepted",
                },
                {
                    "kind": "regression-test",
                    "reference": "tests/test_service.py",
                    "authority": "observed",
                },
            ]
        report = plan(tmp_path, document)
        assert report.document["workflow"] == workflow
        assert report.ready
        assert all(check["execution"] == "not-run" for check in report.document["checks"])
        if workflow == "bounded":
            assert ids(report, "artifacts") == {"change-record", "test-evidence"}
        if workflow == "full-feature":
            assert {"spec", "plan", "architecture-preflight", "test-plan", "validation"} <= ids(
                report, "artifacts"
            )
        assert snapshot(tmp_path) == before


def test_llm_and_gherkin_are_independent(tmp_path):
    install(tmp_path, capabilities=("application-governance", "llm-evaluation"))
    report = plan(tmp_path, request(llm=True))
    assert report.ready and report.document["workflow"] == "bounded"
    assert "llm-exact-match" in ids(report, "checks")
    assert "spec" not in ids(report, "artifacts")
    assert "gherkin-delivery" not in report.document["required_capabilities"]
    other = tmp_path / "other"
    other.mkdir()
    install(other, capabilities=("gherkin-delivery",))
    feature = plan(other, request("feature"))
    assert feature.ready
    assert "llm-exact-match" not in ids(feature, "checks")


@pytest.mark.parametrize(
    "impact",
    [
        "security",
        "auth",
        "data",
        "public-contract",
        "nfr",
        "ownership",
        "architecture",
        "cross-service",
    ],
)
def test_small_sensitive_changes_keep_controls_even_with_bounded_preference(tmp_path, impact):
    install(tmp_path)
    doc = request(**{impact: True})
    doc["preference"] = "bounded"
    report = plan(tmp_path, doc)
    assert f"review:{impact}" in ids(report, "checks")
    assert report.document["workflow"] in {"full-feature", "architecture"}
    assert any(d["code"] == "preference-escalated" for d in report.document["decisions"])


@pytest.mark.parametrize("missing", ["established-behavior", "regression-test"])
def test_defect_requires_existing_expectation_and_regression_source(tmp_path, missing):
    install(tmp_path)
    doc = request("defect")
    doc["references"] = [
        {"kind": "established-behavior", "reference": "architecture.md", "authority": "accepted"},
        {"kind": "regression-test", "reference": "tests/test_service.py", "authority": "observed"},
    ]
    doc["references"] = [r for r in doc["references"] if r["kind"] != missing]
    report = plan(tmp_path, doc)
    assert not report.ready
    assert report.document["workflow"] != "defect"
    assert any(d["code"] == "defect-ineligible" for d in report.document["decisions"])


def test_unknowns_and_agent_proposals_cannot_silently_qualify_small_work(tmp_path):
    install(tmp_path)
    doc = request(security=None)
    doc["confirmation"] = "proposed"
    report = plan(tmp_path, doc)
    assert not report.ready
    assert {"unconfirmed-intent", "unknown-impact"} <= {
        d["code"] for d in report.document["decisions"]
    }
    assert "review:security" in ids(report, "checks")


def test_profile_rules_add_requirements_and_unknown_selectors_fail_closed(tmp_path):
    source = {"reference": "policy.md", "authority": "accepted"}
    install(
        tmp_path,
        workflows=[
            {
                "id": "sensitive",
                "source": source,
                "when": ["public-contract"],
                "required_capabilities": ["gherkin-delivery"],
                "additional_checks": ["contract"],
            }
        ],
    )
    report = plan(tmp_path, request(**{"public-contract": True}))
    assert "contract" in ids(report, "checks")
    assert "gherkin-delivery" in report.document["required_capabilities"]
    assert (
        next(c for c in report.document["checks"] if c["id"] == "contract")["source_policy"]
        == "policy.md"
    )
    source_path = tmp_path / ".govkit/profile.yaml"
    profile = json.loads(json.dumps(report.document["inputs"]["profile"]))
    profile["policy"]["workflows"][0]["when"] = ["unknown-future-selector"]
    source_path.write_text(json.dumps(profile))
    result = plan(tmp_path, request())
    assert not result.ready
    assert any(d["code"] == "unknown-policy-selector" for d in result.document["decisions"])


def test_missing_capability_is_setup_action_without_network_or_install(tmp_path, monkeypatch):
    import socket
    import subprocess

    install(tmp_path, capabilities=("application-governance",))
    before = snapshot(tmp_path)

    def deny(*args, **kwargs):
        raise AssertionError("Unexpected network/process")

    monkeypatch.setattr(socket, "create_connection", deny)
    monkeypatch.setattr(subprocess, "run", deny)
    report = plan(tmp_path, request(llm=True))
    assert not report.ready
    assert any(
        d["code"] == "missing-capability" and "llm-evaluation" in d["affected"]
        for d in report.document["decisions"]
    )
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("agent", ["codex", "claude-code", "copilot"])
def test_guidance_names_only_verified_installed_skills(tmp_path, agent):
    install(tmp_path, agent=agent)
    report = plan(tmp_path, request())
    assert report.document["guidance"]
    assert all((tmp_path / g["path"]).is_file() for g in report.document["guidance"])
    assert any(g["id"] == "request-planning" for g in report.document["guidance"])
    (tmp_path / report.document["guidance"][0]["path"]).write_text("local edit")
    drifted = plan(tmp_path, request())
    assert not drifted.ready and not drifted.document["guidance"]


def test_replay_detects_edited_workflow_and_actual_scope_widens_controls(tmp_path):
    install(tmp_path)
    original = plan(tmp_path, request())
    path = write(tmp_path, "request-plan.json", original.to_json())
    assert load_workflow_plan(path).to_json() == original.to_json()
    doc = json.loads(path.read_text())
    doc["checks"] = []
    path.write_text(json.dumps(doc))
    with pytest.raises(DocumentError, match="replay"):
        load_workflow_plan(path)
    expanded = plan(
        tmp_path,
        request(),
        observed_scope={
            "schema_version": 1,
            "paths": ["src/service.py", "auth/login.py"],
            "impacts": {"auth": True},
        },
        previous=original,
    )
    assert expanded.document["reassessment"]["required"]
    assert "review:auth" in ids(expanded, "checks")
    assert expanded.document["workflow"] != "bounded"
    assert (
        expanded.document["identity"]["request_digest"]
        == original.document["identity"]["request_digest"]
    )
    assert (
        expanded.document["identity"]["scope_digest"]
        != original.document["identity"]["scope_digest"]
    )


def test_normalized_requests_reject_waivers_and_scope_escape(tmp_path):
    for field, value in [("waive_checks", ["security"]), ("authority", "accepted")]:
        doc = request()
        doc[field] = value
        with pytest.raises(DocumentError):
            parse_request(doc)
    doc = request()
    doc["scope"] = ["../outside"]
    with pytest.raises(DocumentError):
        parse_request(doc)


def test_plan_is_deterministic_and_reuses_locally_snapshotted_contracts(tmp_path):
    install(tmp_path)
    first = plan(tmp_path, request())
    assert first.to_json() == plan(tmp_path, request()).to_json()
    assert first.document["inputs"]["request"]["summary"]
    assert any(e["source"] == "architecture.md" and e["digest"] for e in first.document["evidence"])
    before = snapshot(tmp_path)
    again = plan(tmp_path, request(), previous=first)
    assert not again.document["reassessment"]["required"]
    assert snapshot(tmp_path) == before


def test_required_policy_escalates_workflow_and_then_applies_feature_rules(tmp_path):
    source = {"reference": "policy.md", "authority": "accepted"}
    install(
        tmp_path,
        workflows=[
            {
                "id": "feature-extra",
                "source": source,
                "when": ["full-feature"],
                "additional_checks": ["feature-review"],
            },
            {
                "id": "force-spec",
                "source": source,
                "when": ["small-change"],
                "required_capabilities": ["gherkin-delivery"],
            },
        ],
        checks=["llm-exact-match"],
    )
    report = plan(tmp_path, request())
    assert report.document["workflow"] == "full-feature"
    assert "spec" in ids(report, "artifacts")
    assert {"feature-review", "llm-exact-match"} <= ids(report, "checks")


def test_bounded_request_requires_contract_coverage_of_every_path(tmp_path):
    install(tmp_path)
    doc = request()
    doc["scope"] = ["src", "other"]
    report = plan(tmp_path, doc)
    assert not report.ready
    assert any(
        d["code"] == "missing-contract" and "other" in d["affected"]
        for d in report.document["decisions"]
    )


def test_unrelated_missing_contract_does_not_block_covered_work(tmp_path):
    install(tmp_path)
    path = tmp_path / ".govkit/profile.yaml"
    profile = json.loads(path.read_text())
    profile["policy"]["contracts"].append(
        {"source": {"reference": "other/missing.md", "authority": "accepted"}, "scope": ["other"]}
    )
    path.write_text(json.dumps(profile))
    apply_install(preview_install(path, tmp_path, bundled_catalog(), govkit_version=GOVKIT_VERSION))
    report = plan(tmp_path, request())
    assert report.ready
    outside = request()
    outside["scope"] = ["other"]
    assert not plan(tmp_path, outside).ready


def test_pure_replay_has_no_external_reads(tmp_path, monkeypatch):
    from pathlib import Path

    install(tmp_path)
    original = plan(tmp_path, request())
    from cli.workflows import parse_context

    inputs = original.document["inputs"]
    profile, normalized, context = (
        parse_profile(inputs["profile"]),
        parse_request(inputs["request"]),
        parse_context(inputs["context"]),
    )

    def deny(*args, **kwargs):
        raise AssertionError("Resolver read external state")

    monkeypatch.setattr(Path, "open", deny)
    monkeypatch.setattr(Path, "read_text", deny)
    assert resolve_workflow(profile, normalized, context).document == original.document


def test_changed_pinned_reference_requires_reassessment(tmp_path):
    from cli.schema_validation import content_digest

    install(tmp_path)
    doc = request()
    doc["references"] = [
        {
            "kind": "nfr",
            "reference": "architecture.md",
            "authority": "accepted",
            "digest": content_digest((tmp_path / "architecture.md").read_bytes()),
        }
    ]
    first = plan(tmp_path, doc)
    (tmp_path / "architecture.md").write_text("changed NFR")
    second = plan(tmp_path, doc, previous=first)
    assert not second.ready and second.document["reassessment"]["required"]
    assert any(d["code"] == "changed-reference" for d in second.document["decisions"])


def test_request_cli_template_plan_explain_reassess_and_errors(tmp_path, monkeypatch, capsys):
    import sys

    from cli.govkit import main

    def run(*args):
        monkeypatch.setattr(sys, "argv", ["govkit", "request", *args])
        main()
        return capsys.readouterr().out

    template = json.loads(run("template"))
    assert template["confirmation"] == "proposed" and template["impacts"]["auth"] is None
    install(tmp_path)
    path = write(tmp_path, "request.json", json.dumps(request()))
    before = snapshot(tmp_path)
    raw = run("plan", str(path), "--target", str(tmp_path), "--json")
    prior = write(tmp_path, "prior.json", raw)
    assert json.loads(raw)["workflow"] == "bounded"
    assert "project:tests" in run("plan", str(path), "--target", str(tmp_path), "--explain")
    scope = write(
        tmp_path,
        "scope.json",
        json.dumps({"schema_version": 1, "paths": ["auth"], "impacts": {"auth": True}}),
    )
    assert json.loads(
        run(
            "plan",
            str(path),
            "--target",
            str(tmp_path),
            "--previous",
            str(prior),
            "--scope",
            str(scope),
            "--json",
        )
    )["reassessment"]["required"]
    assert all(snapshot(tmp_path)[p] == content for p, content in before.items())
    path.write_text('{"schema_version": 500}')
    with pytest.raises(SystemExit) as exc:
        run("plan", str(path), "--target", str(tmp_path))
    assert exc.value.code == 1
    assert "Error:" in capsys.readouterr().err


def test_plan_exposes_i04_contracts_without_execution(tmp_path):
    from cli.check_models import CheckSpec, Evidence

    install(tmp_path)
    report = plan(tmp_path, request())
    assert report.check_specs() and all(isinstance(c, CheckSpec) for c in report.check_specs())
    assert report.evidence() and all(isinstance(e, Evidence) for e in report.evidence())


def test_repeated_source_cannot_hide_a_mismatched_digest(tmp_path):
    install(tmp_path)
    doc = request()
    doc["references"] = [
        {
            "kind": "acceptance",
            "reference": "architecture.md",
            "authority": "accepted",
            "digest": "0" * 64,
        },
        {"kind": "nfr", "reference": "architecture.md", "authority": "accepted"},
    ]
    assert not plan(tmp_path, doc).ready


def test_external_symlink_reference_is_unavailable(tmp_path):
    target = tmp_path / "consumer"
    target.mkdir()
    install(target)
    (tmp_path / "secret.md").write_text("external source")
    (target / "linked.md").symlink_to(tmp_path / "secret.md")
    doc = request()
    doc["references"] = [{"kind": "nfr", "reference": "linked.md", "authority": "accepted"}]
    report = plan(target, doc)
    assert not report.ready
    assert (
        next(e for e in report.document["evidence"] if e["source"] == "linked.md")["digest"] is None
    )


def test_existing_substantial_feature_policy_selector_is_supported(tmp_path):
    install(
        tmp_path,
        workflows=[
            {
                "id": "full",
                "source": {"reference": "policy.md", "authority": "accepted"},
                "when": ["substantial-feature"],
                "additional_checks": ["acceptance-tests"],
            }
        ],
    )
    result = plan(tmp_path, request("feature"))
    assert result.ready and "acceptance-tests" in ids(result, "checks")


def test_bundled_workflow_examples_have_replayable_plans(tmp_path):
    from cli import paths
    from cli.schema_validation import read_document

    root = paths.GOVERNANCE_DIR / "examples/workflows"
    fixture = json.loads((root / "consumer.json").read_text())
    for relative, content in fixture["files"].items():
        write(tmp_path, relative, content)
    source = write(tmp_path, ".govkit/profile.yaml", json.dumps(fixture["profile"]))
    apply_install(
        preview_install(source, tmp_path, bundled_catalog(), govkit_version=GOVKIT_VERSION)
    )
    expected = {
        "defect": "defect",
        "enhancement": "bounded",
        "refactor": "bounded",
        "mcp": "full-feature",
        "llm": "bounded",
        "feature": "full-feature",
        "architecture": "architecture",
    }
    assert {p.stem for p in (root / "requests").glob("*.json")} == set(expected)
    before = snapshot(tmp_path)
    for name, workflow in expected.items():
        report = plan(tmp_path, read_document(root / "requests" / f"{name}.json"))
        assert report.ready and report.document["workflow"] == workflow
        output = write(tmp_path.parent, f"{name}-plan.json", report.to_json())
        assert load_workflow_plan(output).identity == report.identity
        assert snapshot(tmp_path) == before


def test_applicable_transition_needs_current_and_target_sources(tmp_path):
    install(tmp_path)
    path = tmp_path / ".govkit/profile.yaml"
    profile = json.loads(path.read_text())
    profile["policy"]["transitions"] = [
        {
            "id": "migrate",
            "source": {"reference": "policy.md", "authority": "accepted"},
            "scope": ["src"],
            "mode": "improve",
            "applies_to": "new-and-changed",
            "current": [
                {
                    "source": {"reference": "architecture.md", "authority": "accepted"},
                    "scope": ["src"],
                }
            ],
            "target": [
                {
                    "source": {"reference": "missing-target.md", "authority": "accepted"},
                    "scope": ["src"],
                }
            ],
        }
    ]
    path.write_text(json.dumps(profile))
    apply_install(preview_install(path, tmp_path, bundled_catalog(), govkit_version=GOVKIT_VERSION))
    report = plan(tmp_path, request("architecture", architecture=True))
    assert not report.ready
    assert any(
        d["blocking"] and "missing-target.md" in d["affected"] for d in report.document["decisions"]
    )
