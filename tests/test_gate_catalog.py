"""Provider-neutral declarations cannot replace runtime policy/change resolution."""

from copy import deepcopy

import pytest

from cli.gate_catalog import compose_catalog, parse_catalog
from cli.pack_loading import bundled_catalog, load_pack
from cli.profiles import parse_profile
from cli.schema_validation import canonical_json, content_digest, validate_document
from tests.test_capability_packs import make_pack, profile


def compose(project, packs=None):
    return compose_catalog(
        project, bundled_catalog() if packs is None else packs, govkit_version="0.21.1"
    )


@pytest.mark.parametrize("agent", ["codex", "claude-code", "copilot"])
def test_equivalent_provider_profiles_have_the_same_gate_contract(agent):
    project = profile(["application-governance", "llm-evaluation"], agent=agent)
    github = compose(project).document
    other = project.document
    other["integrations"]["ci"] = "azure"
    azure = compose(parse_profile(other)).document
    assert github["gates"] == azure["gates"]
    assert {g["id"] for g in github["gates"]} >= {"govkit:change-conformance", "llm-exact-match"}
    assert github["execution"] == "not-run"
    assert github["enforcement"] == "unknown"
    assert github["pins"]["govkit"] == "0.21.1"
    assert {p["id"] for p in github["pins"]["packs"]} == {
        "application-governance",
        "llm-evaluation",
    }
    assert all(g["path_filters"] == [] for g in github["gates"])
    assert "level" not in github
    validate_document(github, "gate-catalog")


def test_policy_requirements_cannot_be_demoted_by_advisory_pack_or_workflow(tmp_path):
    pack = load_pack(
        make_pack(
            tmp_path / "control",
            checks=[{"id": "security-scan", "path": "checks/scan.py", "required": False}],
        )
    )
    document = profile(["sample"], checks=["security-scan"]).document
    document["policy"]["workflows"] = [
        {
            "id": "bounded",
            "source": {"reference": "team.md", "authority": "accepted"},
            "when": ["small-change"],
            "additional_checks": ["security-scan", "review:owner"],
        }
    ]
    catalog = compose(parse_profile(document), (pack,)).document
    gate = next(g for g in catalog["gates"] if g["id"] == "security-scan")
    assert gate["blocking"]
    assert any(r["kind"] == "repository" and r["blocking"] for r in gate["requirements"])
    assert any(
        r["kind"] == "workflow" and r["selectors"] == ["small-change"] for r in gate["requirements"]
    )
    assert any(r["kind"] == "capability" and not r["blocking"] for r in gate["requirements"])
    assert gate["path_filters"] == []
    assert (
        next(g for g in catalog["gates"] if g["id"] == "review:owner")["requirements"][0]["kind"]
        == "workflow"
    )


def test_unknown_capability_is_an_explicit_unresolved_catalog():
    catalog = compose(profile(["missing-capability"]))
    assert not catalog.ready
    assert catalog.document["decisions"]
    assert catalog.document["execution"] == "not-run"
    assert any(g["id"] == "govkit:change-conformance" for g in catalog.document["gates"])


def test_catalog_is_deterministic_detached_and_replayable():
    project = profile(["llm-evaluation", "application-governance"])
    packs = bundled_catalog()
    catalog = compose(project, packs)
    assert catalog.to_json() == compose(project, tuple(reversed(packs))).to_json()
    document = catalog.document
    assert parse_catalog(document).to_json() == catalog.to_json()
    document["gates"].clear()
    assert catalog.document["gates"]


@pytest.mark.parametrize(
    "mutation", ["duplicate", "missing-dependency", "cycle", "filter", "unblock", "unsafe-scope"]
)
def test_malformed_gate_contract_is_rejected_even_with_recomputed_digest(mutation):
    document = compose(profile(["llm-evaluation"])).document
    first = document["gates"][0]
    if mutation == "duplicate":
        document["gates"].append(deepcopy(first))
    elif mutation == "missing-dependency":
        first["dependencies"] = ["missing"]
    elif mutation == "cycle":
        first["dependencies"] = [first["id"]]
    elif mutation == "filter":
        first["path_filters"] = ["docs/**"]
    elif mutation == "unblock":
        first["blocking"] = False
    else:
        first["requirements"][0]["scope"] = ["../outside"]
    document["digest"] = content_digest(
        canonical_json({k: v for k, v in document.items() if k != "digest"}).encode()
    )
    with pytest.raises(ValueError):
        parse_catalog(document)


def test_catalog_commands_use_the_shared_engine_with_explicit_trusted_inputs():
    document = compose(profile(["application-governance"])).document
    runner = next(g for g in document["gates"] if g["id"] == "govkit:change-conformance")
    assert runner["commands"] == [
        [
            "govkit",
            "conform",
            "--target",
            "{target}",
            "--request",
            "{request}",
            "--base",
            "{base}",
            "--policy-target",
            "{policy_target}",
            "--json",
        ]
    ]
    assert runner["blocking"]
    assert "trusted-policy-checkout" in runner["configuration"]
    assert runner["triggers"] == ["pull-request", "push", "manual"]
    assert runner["evidence"] == ["change-results/v1"]


def test_architecture_scope_is_retained_without_becoming_a_pipeline_path_filter():
    document = profile(["application-governance"]).document
    document["policy"]["transitions"] = [
        {
            "id": "service-boundary",
            "source": {"reference": "adr.md", "authority": "accepted"},
            "scope": ["services/core/"],
            "mode": "retain",
            "current": [
                {
                    "source": {"reference": "current.md", "authority": "accepted"},
                    "scope": ["services/core/"],
                }
            ],
            "target": [],
            "applies_to": "new-and-changed",
            "exceptions": [],
        }
    ]
    catalog = compose(parse_profile(document)).document
    gate = next(g for g in catalog["gates"] if g["id"] == "change:architecture")
    assert gate["requirements"] == [
        {
            "kind": "architecture",
            "selectors": ["service-boundary"],
            "scope": ["services/core"],
            "source": "adr.md",
            "blocking": True,
        }
    ]
    assert gate["path_filters"] == []
    assert gate["dependencies"] == ["govkit:change-conformance"]


@pytest.mark.parametrize("agent", ["codex", "claude-code", "copilot"])
def test_runtime_gate_catalog_pilot(tmp_path, agent):
    from tests.wheel_gate_catalog_smoke import run_pilot

    run_pilot(tmp_path, agent)


def test_deep_acyclic_dependencies_do_not_exhaust_the_python_stack():
    document = compose(profile(["llm-evaluation"])).document
    engine, logical = document["gates"]
    document["gates"] = [engine]
    for index in range(1020):
        gate = deepcopy(logical)
        gate["id"] = f"control-{index}"
        gate["dependencies"] = ["govkit:change-conformance"]
        if index < 1019:
            gate["dependencies"].append(f"control-{index + 1}")
        document["gates"].append(gate)
    document["digest"] = content_digest(
        canonical_json({k: v for k, v in document.items() if k != "digest"}).encode()
    )
    assert len(parse_catalog(document).document["gates"]) == 1021


@pytest.mark.parametrize("change", ["range-pin", "duplicate-pack"])
def test_catalog_pins_are_exact_and_unambiguous(change):
    document = compose(profile(["llm-evaluation"])).document
    if change == "range-pin":
        document["pins"]["govkit"] = ">=0.21.1"
    else:
        duplicate = deepcopy(document["pins"]["packs"][0])
        duplicate["version"] = "2.0.0"
        document["pins"]["packs"].append(duplicate)
    document["digest"] = content_digest(
        canonical_json({k: v for k, v in document.items() if k != "digest"}).encode()
    )
    with pytest.raises(ValueError, match="[Vv]ersion|[Pp]in|[Dd]uplicate"):
        parse_catalog(document)
