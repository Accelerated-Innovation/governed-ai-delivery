"""Public profile validation, authority and deterministic resolution contracts."""

import copy
import json
import socket

import pytest
import yaml
from jsonschema import Draft202012Validator

from cli import paths
from cli.profiles import ProfileError, load_profile, load_resolution, parse_profile, resolve_profile
from cli.resolution import resolve_request
from cli.resolution_models import Authority, Observation, ProposedDecision, RequestInput, SourceRef


def accepted(reference="decisions/team-policy.md"):
    return {"reference": reference, "authority": "accepted"}


def profile_document():
    return {
        "schema_version": 1,
        "source": accepted(),
        "repository": {"id": "existing-service", "project_type": None, "stack": None},
        "integrations": {"agent": "codex", "ci": "github"},
        "capabilities": [{"id": "application-governance"}, {"id": "llm-evaluation"}],
        "policy": {
            "source": accepted(),
            "required_checks": [{"id": "security"}],
            "workflows": [
                {"id": "small-change", "source": accepted(), "when": ["bounded-defect"]},
                {
                    "id": "full-feature",
                    "source": accepted(),
                    "when": ["public-contract"],
                    "required_capabilities": ["gherkin-delivery"],
                    "additional_checks": ["contract"],
                },
            ],
            "contracts": [{"source": accepted("architecture/current.md"), "scope": ["service/"]}],
        },
    }


def test_independent_profiles_preserve_unknowns_and_workflow_permissions():
    document = profile_document()
    profile = parse_profile(document)
    resolution = resolve_profile(profile)
    assert resolution.ready
    assert [c.id for c in resolution.plan.selections.capabilities] == [
        "application-governance",
        "llm-evaluation",
    ]
    assert resolution.plan.integrations.stack is None
    assert set(resolution.unknowns) == {"project_type", "stack"}
    assert [rule.id for rule in profile.workflows] == ["small-change", "full-feature"]
    assert profile.workflows[1].required_capabilities == ("gherkin-delivery",)
    assert profile.repository.policy.contracts[0].source.reference == "architecture/current.md"
    assert "level" not in json.loads(resolution.to_json())["profile"]
    document["capabilities"] = [{"id": "gherkin-delivery"}]
    assert [
        c.id for c in resolve_profile(parse_profile(document)).plan.selections.capabilities
    ] == ["gherkin-delivery"]


def test_only_required_unknown_context_blocks_its_selected_capability():
    document = profile_document()
    document["capabilities"][1]["requires_context"] = ["stack"]
    record = resolve_profile(parse_profile(document))
    assert not record.ready
    (decision,) = record.plan.selections.unresolved
    assert decision.code == "missing-context"
    assert decision.affected == ("llm-evaluation", "stack")
    assert record.plan.selections.checks[0].id == "security"
    document["repository"]["stack"] = "existing-custom-runtime"
    assert resolve_profile(parse_profile(document)).ready


def test_required_capabilities_cannot_silently_disappear():
    document = profile_document()
    document["policy"]["required_capabilities"] = ["llm-evaluation", "audit"]
    record = resolve_profile(parse_profile(document))
    assert not record.ready
    assert any(
        d.code == "missing-required-capability" and d.affected == ("audit",)
        for d in record.plan.selections.unresolved
    )


def test_request_keeps_controls_without_changing_profile():
    profile = parse_profile(profile_document())
    original = resolve_profile(profile).to_json()
    for request_id in ("bounded-defect", "full-feature"):
        request = RequestInput(request_id, SourceRef("request.json", Authority.ACCEPTED))
        workflow = resolve_request(profile.repository, request)
        assert {check.id for check in workflow.selections.checks} == {"security"}
    assert resolve_profile(profile).to_json() == original


def test_scoped_transitions_keep_current_target_and_exceptions_separate():
    document = profile_document()
    document["policy"]["transitions"] = [
        {
            "id": mode,
            "source": accepted(),
            "scope": [f"services/{mode}/"],
            "mode": mode,
            "current": [{"source": accepted("current.md"), "scope": [f"services/{mode}/"]}],
            "target": []
            if mode == "retain"
            else [{"source": accepted("target.md"), "scope": [f"services/{mode}/new/"]}],
            "applies_to": "new-and-changed",
            "exceptions": [
                {
                    "id": "old-code",
                    "source": accepted("exception.md"),
                    "scope": [f"services/{mode}/old/"],
                    "expires_at": "2026-12-31",
                }
            ],
        }
        for mode in ("retain", "improve", "migrate")
    ]
    record = resolve_profile(parse_profile(document))
    assert record.ready
    assert [t.mode for t in record.plan.policy.transitions] == ["retain", "improve", "migrate"]
    assert record.plan.policy.transitions[1].target[0].scope == ("services/improve/new/",)
    assert record.plan.policy.transitions[0].exceptions[0].expires_at == "2026-12-31"
    assert record.plan.selections.artifacts == ()


@pytest.mark.parametrize(
    "change,location",
    [
        (lambda d: d.update(schema_version=2), "schema_version"),
        (lambda d: d.update(level=4), "level"),
        (lambda d: d.update(observations=[]), "observations"),
        (lambda d: d.update(release_metadata={}), "release_metadata"),
        (lambda d: d["source"].update(authority="observed"), "authority"),
        (lambda d: d["policy"]["source"].update(authority="proposed"), "authority"),
        (lambda d: d["policy"].update(required_checks="security"), "required_checks"),
        (lambda d: d["integrations"].update(agent="typo"), "agent"),
        (lambda d: d["repository"].update(stack=""), "stack"),
        (
            lambda d: d["capabilities"].append({"id": "llm-evaluation", "requires": ["audit"]}),
            "duplicate",
        ),
        (lambda d: d.update(maintenance={"allow_refresh": "false"}), "allow_refresh"),
        (lambda d: d.update(maintenance={"metadata_max_age_hours": -1}), "metadata_max_age_hours"),
    ],
)
def test_runtime_rejects_invalid_or_ambiguous_profiles(change, location):
    document = profile_document()
    change(document)
    with pytest.raises(ProfileError, match=location):
        parse_profile(document)


@pytest.mark.parametrize(
    "text",
    [
        "schema_version: 1\nschema_version: 2\n",
        "schema_version: 1\nrepository: &r {id: service}\ncapabilities: *r\n",
        "schema_version: 1\nvalue: .nan\n",
        "!!python/object:foo {}",
    ],
)
def test_loader_refuses_duplicate_keys_aliases_and_non_json_yaml(tmp_path, text):
    path = tmp_path / "profile.yaml"
    path.write_text(text)
    with pytest.raises(ProfileError):
        load_profile(path)


def test_observation_and_proposal_context_never_becomes_profile_policy(tmp_path):
    profile = parse_profile(profile_document())
    observation = Observation(
        SourceRef("service.py", Authority.OBSERVED), "Uses SQL", ("service/",), "partial"
    )
    proposal = ProposedDecision(
        SourceRef("proposal.md", Authority.PROPOSED), "Adopt ports?", ("service/",)
    )
    record = resolve_profile(profile, observations=(observation,), proposals=(proposal,))
    payload = json.loads(record.to_json())
    assert payload["plan"]["observations"][0]["source"]["authority"] == "observed"
    assert payload["plan"]["proposals"][0]["source"]["authority"] == "proposed"
    assert "observations" not in payload["profile"]
    assert record.plan.policy.contracts == profile.repository.policy.contracts
    path = tmp_path / "resolution.json"
    path.write_text(record.to_json())
    assert load_resolution(path).to_json() == record.to_json()


def test_maintenance_defaults_offline_and_preserves_compatible_intentional_pins(monkeypatch):
    document = profile_document()
    document["maintenance"] = {
        "sources": [
            {
                "id": "approved",
                "url": "https://example.invalid/releases.json",
                "channels": ["stable"],
            }
        ],
        "constraints": [
            {
                "component": "govkit",
                "source_id": "approved",
                "channel": "stable",
                "pin": "0.21.1",
                "compatibility": ">=0.21,<1",
            }
        ],
        "metadata_max_age_hours": 24,
        "assessment_max_age_hours": 168,
    }

    def forbidden(*args, **kwargs):
        raise AssertionError("Profile planning attempted a network lookup")

    monkeypatch.setattr(socket, "socket", forbidden)
    profile = parse_profile(document)
    record = resolve_profile(profile)
    assert not profile.maintenance.allow_refresh
    assert profile.maintenance.constraints[0].pin == "0.21.1"
    assert record.release_metadata_status == "not-queried"
    assert record.ready
    document["maintenance"]["allow_refresh"] = True
    assert resolve_profile(parse_profile(document)).release_metadata_status == "not-queried"


def test_release_source_refuses_embedded_credentials():
    document = profile_document()
    document["maintenance"] = {
        "sources": [
            {
                "id": "private",
                "url": "https://user:password@example.invalid/releases",
                "channels": ["stable"],
            }
        ]
    }
    with pytest.raises(ProfileError, match="credentials"):
        parse_profile(document)


def test_conflicting_transitions_for_the_same_scope_stay_unresolved():
    document = profile_document()
    current = {"source": accepted("architecture.md"), "scope": ["service/"]}
    document["policy"]["transitions"] = [
        {
            "id": "keep",
            "source": accepted(),
            "scope": ["service/"],
            "mode": "retain",
            "current": [current],
            "target": [],
            "applies_to": "new-and-changed",
        },
        {
            "id": "move",
            "source": accepted(),
            "scope": ["service/"],
            "mode": "migrate",
            "current": [current],
            "target": [{"source": accepted("target.md"), "scope": ["service/"]}],
            "applies_to": "new-and-changed",
        },
    ]
    record = resolve_profile(parse_profile(document))
    assert not record.ready
    assert any(d.code == "conflicting-transition" for d in record.plan.selections.unresolved)


@pytest.mark.parametrize(
    "change,match",
    [
        (
            lambda d: d["maintenance"]["constraints"][0].update(source_id="unknown"),
            "approved source/channel",
        ),
        (
            lambda d: d["maintenance"]["constraints"][0].update(channel="beta"),
            "approved source/channel",
        ),
        (lambda d: d["maintenance"]["constraints"][0].update(pin=None), "pin or compatibility"),
    ],
)
def test_maintenance_constraints_must_reference_approved_policy(change, match):
    document = profile_document()
    document["maintenance"] = {
        "sources": [
            {"id": "approved", "url": "https://example.invalid/releases", "channels": ["stable"]}
        ],
        "constraints": [
            {"component": "govkit", "source_id": "approved", "channel": "stable", "pin": "0.21.1"}
        ],
    }
    change(document)
    with pytest.raises(ProfileError, match=match):
        parse_profile(document)


def test_profile_and_resolution_roundtrip_are_deterministic_and_runtime_validated(tmp_path):
    document = profile_document()
    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text(yaml.safe_dump(document))
    first = resolve_profile(load_profile(profile_path))
    assert (
        first.to_json()
        == resolve_profile(parse_profile(dict(reversed(list(document.items()))))).to_json()
    )
    assert len(first.profile_digest) == 64
    record_path = tmp_path / "resolution.json"
    record_path.write_text(first.to_json())
    assert load_resolution(record_path).to_json() == first.to_json()
    forged = json.loads(first.to_json())
    forged["plan"]["selections"]["checks"] = []
    record_path.write_text(json.dumps(forged))
    with pytest.raises(ProfileError, match="does not match"):
        load_resolution(record_path)
    forged["schema_version"] = 9
    record_path.write_text(json.dumps(forged))
    with pytest.raises(ProfileError, match="schema_version"):
        load_resolution(record_path)


def test_resolution_uses_a_snapshot_of_profile_inputs():
    document = profile_document()
    original = copy.deepcopy(document)
    record = resolve_profile(parse_profile(document))
    before = record.to_json()
    document["policy"]["required_checks"].clear()
    assert record.to_json() == before
    assert json.loads(before)["profile"] == original


def test_packaged_schemas_and_all_profile_examples_validate():
    schemas = paths.GOVERNANCE_DIR / "schemas"
    for name in ("profile", "resolution"):
        schema = json.loads((schemas / f"{name}.schema.json").read_text())
        Draft202012Validator.check_schema(schema)
        assert schema["additionalProperties"] is False
    examples = sorted((paths.GOVERNANCE_DIR / "examples" / "profiles").glob("*.yaml"))
    assert len(examples) >= 3
    profile_schema = json.loads((schemas / "profile.schema.json").read_text())
    resolution_schema = json.loads((schemas / "resolution.schema.json").read_text())
    assert resolution_schema["$defs"]["profile"] == {
        k: v for k, v in profile_schema.items() if k not in ("$schema", "$id", "title", "$defs")
    }
    assert all(
        resolution_schema["$defs"][key] == value for key, value in profile_schema["$defs"].items()
    )
    for example in examples:
        record = resolve_profile(load_profile(example))
        Draft202012Validator(json.loads((schemas / "resolution.schema.json").read_text())).validate(
            json.loads(record.to_json())
        )
        assert record.ready
        saved = example.with_suffix(".resolution.json")
        assert load_resolution(saved).profile_digest == record.profile_digest
