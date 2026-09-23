"""Behavior contract for the level-free, side-effect-free resolution core."""

import ast
import builtins
import copy
import dataclasses
import json
import socket
from pathlib import Path

import pytest

from cli.legacy_resolution import adapt_legacy_manifest, legacy_file_lists
from cli.manifest import load_manifest, resolve_variant_files
from cli.resolution import resolve_repository, resolve_request
from cli.resolution_models import (
    AcceptedPolicy,
    ArchitectureTransition,
    ArtifactRequirement,
    Authority,
    CapabilityRequirement,
    CheckRequirement,
    ContractRef,
    Integrations,
    Observation,
    Ownership,
    PolicyException,
    ProposedDecision,
    Reason,
    RepositoryInput,
    RequestInput,
    SourceRef,
)


def reason(text="Explicit project selection", authority=Authority.ACCEPTED, ref="policy.yaml"):
    return Reason(text, SourceRef(ref, authority))


def capability(identifier, **kwargs):
    return CapabilityRequirement(identifier, (reason(),), **kwargs)


def artifact(identifier="guide", **kwargs):
    return ArtifactRequirement(
        identifier,
        "docs/guide.md",
        "docs/guide.md",
        Ownership.GOVERNED_CONTRACT,
        (reason("Resource from selected pack", Authority.BUNDLED, "pack.json"),),
        **kwargs,
    )


def check(identifier="architecture", **kwargs):
    return CheckRequirement(identifier, (reason(),), **kwargs)


def test_independent_capabilities_need_no_level():
    repo = RepositoryInput(
        "service",
        capabilities=(capability("application-governance"), capability("llm-evaluation")),
        artifacts=(artifact(capability_id="llm-evaluation"),),
        checks=(check("eval", capability_id="llm-evaluation"),),
        integrations=Integrations(agent="codex", stack=None),
    )
    plan = resolve_repository(repo)
    assert plan.ready
    assert [c.id for c in plan.selections.capabilities] == [
        "application-governance",
        "llm-evaluation",
    ]
    assert plan.integrations.stack is None
    assert plan.selections.artifacts[0].reasons[0].source.authority == Authority.BUNDLED
    assert all(
        item.reasons
        for items in (
            plan.selections.capabilities,
            plan.selections.artifacts,
            plan.selections.checks,
        )
        for item in items
    )
    assert "level" not in plan.to_json()


def test_request_plan_is_separate_and_cannot_drop_repository_checks():
    mandatory = check("security")
    policy = AcceptedPolicy(
        SourceRef("team-policy.yaml", Authority.ACCEPTED), required_checks=(mandatory,)
    )
    repo = RepositoryInput("service", capabilities=(capability("application"),), policy=policy)
    initial = resolve_repository(repo)
    request = RequestInput(
        "change-123",
        SourceRef("intent/change-123.json", Authority.ACCEPTED),
        required_capabilities=(capability("application"),),
        checks=(check("regression"),),
    )
    workflow = resolve_request(repo, request)
    assert workflow.ready
    assert workflow.repository_identity == initial.identity
    assert workflow.kind == "workflow"
    assert initial.kind == "installation"
    assert {c.id for c in workflow.selections.checks} == {"security", "regression"}
    assert resolve_repository(repo).to_json() == initial.to_json()
    assert repo.checks == ()
    assert any(
        r.source.reference == "team-policy.yaml" for r in workflow.selections.checks[0].reasons
    )


def test_request_missing_capability_does_not_install_or_enable_it():
    repo = RepositoryInput("service", capabilities=(capability("application"),))
    request = RequestInput(
        "change",
        SourceRef("request.json", Authority.ACCEPTED),
        required_capabilities=(capability("llm-evaluation"),),
        checks=(check("eval", capability_id="llm-evaluation"),),
    )
    plan = resolve_request(repo, request)
    assert not plan.ready
    assert [c.id for c in plan.selections.capabilities] == ["application"]
    assert {d.code for d in plan.selections.unresolved} >= {"unavailable-capability"}
    assert not plan.selections.checks
    assert repo.capabilities == (capability("application"),)


def test_request_keeps_existing_dependencies_when_it_only_names_a_capability():
    repo = RepositoryInput(
        "service",
        capabilities=(
            capability("application"),
            capability("eval", requires=("application",)),
        ),
    )
    request = RequestInput(
        "change",
        SourceRef("intent.json", Authority.ACCEPTED),
        required_capabilities=(capability("eval"),),
    )
    plan = resolve_request(repo, request)
    assert plan.ready
    assert plan.selections.capabilities[1].requires == ("application",)


def test_request_can_add_requirements_but_cannot_waive_existing_ones():
    repo = RepositoryInput("service", capabilities=(capability("eval", requires=("runtime",)),))
    request = RequestInput(
        "change",
        SourceRef("intent.json", Authority.ACCEPTED),
        required_capabilities=(capability("eval", requires=("dataset",)),),
    )
    plan = resolve_request(repo, request)
    assert not plan.ready
    assert plan.selections.capabilities[0].requires == ("runtime", "dataset")
    assert {d.affected for d in plan.selections.unresolved if d.code == "missing-capability"} == {
        ("eval", "runtime"),
        ("eval", "dataset"),
    }


def test_request_conflict_does_not_remove_a_mandatory_check():
    mandatory = check("security")
    repo = RepositoryInput(
        "service",
        policy=AcceptedPolicy(
            SourceRef("team-policy.yaml", Authority.ACCEPTED),
            required_checks=(mandatory,),
        ),
    )
    request = RequestInput(
        "change",
        SourceRef("intent.json", Authority.ACCEPTED),
        checks=(check("security", capability_id="unavailable"),),
    )
    plan = resolve_request(repo, request)
    assert not plan.ready
    assert plan.selections.checks[0].id == "security"
    assert plan.selections.checks[0].capability_id is None
    assert any(d.code == "conflicting-declaration" for d in plan.selections.unresolved)


@pytest.mark.parametrize("authority", [Authority.OBSERVED, Authority.PROPOSED])
def test_unaccepted_requirement_stays_unresolved(authority):
    proposed = CapabilityRequirement("framework", (reason(authority=authority),))
    plan = resolve_repository(RepositoryInput("service", capabilities=(proposed,)))
    assert not plan.ready
    assert plan.selections.unresolved[0].code == "unaccepted-requirement"
    assert plan.selections.capabilities[0].reasons[0].source.authority == authority


def test_legacy_conversion_rejects_unresolved_plans():
    plan = resolve_repository(
        RepositoryInput("service", checks=(CheckRequirement("security", ()),))
    )
    with pytest.raises(ValueError, match="unresolved"):
        legacy_file_lists(plan)


def test_missing_dependency_and_conflict_are_structured_and_keep_other_findings():
    repo = RepositoryInput(
        "service",
        capabilities=(
            capability("eval", requires=("runtime",)),
            capability("gherkin", conflicts=("compact-only",)),
            capability("compact-only"),
        ),
        checks=(check("security"),),
    )
    plan = resolve_repository(repo)
    assert not plan.ready
    assert {d.code for d in plan.selections.unresolved} == {
        "missing-capability",
        "capability-conflict",
    }
    assert all(d.id and d.affected and d.reasons for d in plan.selections.unresolved)
    assert plan.selections.checks == repo.checks
    assert plan.to_json() == resolve_repository(repo).to_json()


def test_decision_ids_do_not_collapse_distinct_dependency_pairs():
    repo = RepositoryInput(
        "service",
        capabilities=(
            capability("a|b", requires=("c",)),
            capability("a", requires=("b|c",)),
        ),
    )
    plan = resolve_repository(repo)
    assert len(plan.selections.unresolved) == 2
    assert len({decision.id for decision in plan.selections.unresolved}) == 2
    assert {decision.affected for decision in plan.selections.unresolved} == {
        ("a|b", "c"),
        ("a", "b|c"),
    }


def test_conflicting_artifact_ids_do_not_silently_choose_a_winner():
    first = artifact()
    other = dataclasses.replace(first, source_path="other/guide.md")
    plan = resolve_repository(RepositoryInput("service", artifacts=(first, other)))
    assert not plan.ready
    assert [d.code for d in plan.selections.unresolved] == ["conflicting-declaration"]
    assert plan.selections.unresolved[0].affected == ("artifact:guide",)


def test_duplicates_keep_all_reasons_and_directory_contributions():
    first = artifact()
    duplicate = dataclasses.replace(first, reasons=(reason("Required by team policy"),))
    second = dataclasses.replace(
        first, id="other-guide", source_path="other/", destination="docs/guide.md"
    )
    plan = resolve_repository(RepositoryInput("service", artifacts=(first, duplicate, second)))
    assert plan.ready
    assert len(plan.selections.artifacts) == 2
    assert {r.text for r in plan.selections.artifacts[0].reasons} == {
        "Resource from selected pack",
        "Required by team policy",
    }


def test_missing_provenance_is_an_unresolved_decision():
    plan = resolve_repository(
        RepositoryInput("service", checks=(CheckRequirement("security", ()),))
    )
    assert not plan.ready
    assert plan.selections.unresolved[0].code == "missing-reason"


@pytest.mark.parametrize("authority", [Authority.OBSERVED, Authority.PROPOSED, Authority.BUNDLED])
def test_unaccepted_source_cannot_be_constructed_as_accepted_policy(authority):
    with pytest.raises(ValueError, match="accepted"):
        AcceptedPolicy(SourceRef("discovered.md", authority))


def test_observation_proposal_and_scoped_transition_keep_their_authority():
    observed = Observation(
        SourceRef("src/service.py", Authority.OBSERVED), "Uses SQL", ("src/",), "partial"
    )
    proposal = ProposedDecision(
        SourceRef("proposal.md", Authority.PROPOSED), "Adopt a port?", ("src/",)
    )
    current = ContractRef(SourceRef("current-architecture.md", Authority.ACCEPTED), ("src/",))
    target = ContractRef(SourceRef("target-architecture.md", Authority.ACCEPTED), ("src/new/",))
    exception = PolicyException(
        "old-adapter", SourceRef("exception.md", Authority.ACCEPTED), ("src/old/",), "2026-12-31"
    )
    transition = ArchitectureTransition(
        "port-migration",
        SourceRef("transition.md", Authority.ACCEPTED),
        ("src/",),
        "improve",
        (current,),
        (target,),
        "new-and-changed",
        (exception,),
    )
    repo = RepositoryInput(
        "service",
        observations=(observed,),
        proposals=(proposal,),
        policy=AcceptedPolicy(
            SourceRef("policy.yaml", Authority.ACCEPTED), transitions=(transition,)
        ),
    )
    plan = resolve_repository(repo)
    data = json.loads(plan.to_json())
    assert plan.policy.transitions == (transition,)
    assert data["observations"][0]["source"]["authority"] == "observed"
    assert data["proposals"][0]["source"]["authority"] == "proposed"
    assert plan.selections.capabilities == plan.selections.checks == ()
    assert data["policy"]["transitions"][0]["scope"] == ["src/"]
    assert data["policy"]["transitions"][0]["exceptions"][0]["expires_at"] == "2026-12-31"


def test_serialization_is_versioned_canonical_and_inputs_are_not_mutated():
    first = artifact(attributes={"path_scoped": True, "custom": {"z": 1, "a": [2]}})
    repo = RepositoryInput("service", artifacts=(first,))
    original = copy.deepcopy(repo)
    plan = resolve_repository(repo)
    reordered = dataclasses.replace(
        first, attributes={"custom": {"a": [2], "z": 1}, "path_scoped": True}
    )
    equivalent = resolve_repository(dataclasses.replace(repo, artifacts=(reordered,)))
    assert plan.to_json() == equivalent.to_json()
    assert plan.identity == equivalent.identity
    assert json.loads(plan.to_json())["schema_version"] == 1
    assert repo == original
    first.attributes["custom"]["a"].append(3)
    assert plan.to_json() == equivalent.to_json(), "The result must not alias mutable caller data"


def test_core_executes_without_io_or_console_output(monkeypatch, capsys):
    repo = RepositoryInput(
        "service", capabilities=(capability("application"),), artifacts=(artifact(),)
    )
    request = RequestInput("change", SourceRef("intent.json", Authority.ACCEPTED))

    def forbidden(*args, **kwargs):
        raise AssertionError("Resolution attempted I/O")

    with monkeypatch.context() as guard:
        guard.setattr(builtins, "open", forbidden)
        guard.setattr(builtins, "print", forbidden)
        guard.setattr(Path, "open", forbidden)
        guard.setattr(socket, "socket", forbidden)
        plan = resolve_repository(repo)
        workflow = resolve_request(repo, request)
        serialized = plan.to_json(), workflow.to_json()
    assert plan.ready and workflow.ready
    assert all(serialized)
    assert capsys.readouterr() == ("", "")


@pytest.mark.parametrize(
    "level,expected",
    [
        ("3", ["application-governance"]),
        ("4", ["application-governance", "gherkin-delivery"]),
        ("5", ["application-governance", "gherkin-delivery", "llm-evaluation"]),
    ],
)
def test_legacy_adapter_translates_levels_only_at_the_boundary(level, expected):
    manifest = load_manifest("codex")
    options = {"level": level, "type": "api", "ci": "azure", "stack": "python-fastapi"}
    repo = adapt_legacy_manifest(manifest, options)
    plan = resolve_repository(repo)
    assert plan.ready
    assert [c.id for c in plan.selections.capabilities] == expected
    assert legacy_file_lists(plan) == resolve_variant_files(manifest, options)
    assert plan.provenance[0].details["options"]["level"] == level
    assert "level" not in {f.name for f in dataclasses.fields(RepositoryInput)}
    assert all(
        a.reasons[0].source.reference.startswith("agents/codex/manifest.json#")
        for a in plan.selections.artifacts
    )
    assert all(a.reasons[0].source.authority == Authority.LEGACY for a in plan.selections.artifacts)
    assert plan.selections.checks == (), "Installed CI files are not proof of executed checks"


def test_core_imports_only_stdlib_and_its_models():
    root = Path(__file__).resolve().parents[1]
    for module in ("resolution", "resolution_models"):
        tree = ast.parse((root / "cli" / f"{module}.py").read_text())
        allowed = {"__future__", "copy", "dataclasses", "enum", "hashlib", "json", "typing"}
        imports = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
        for node in imports:
            if isinstance(node, ast.Import):
                assert all(a.name in allowed for a in node.names)
            elif node.level:
                assert module == "resolution" and node.module == "resolution_models"
            else:
                assert node.module in allowed
