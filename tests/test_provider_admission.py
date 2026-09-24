"""PR admission validates native context and caller pins before executing checks."""

import json
import os
import subprocess
import sys

import pytest
import yaml

from cli.pipeline_runtime import run_bound
from cli.provider_admission import admit_run
from cli.schema_validation import content_digest
from tests.test_change_conformance import git
from tests.test_pipeline_render import artifact
from tests.test_pipeline_runtime import fixture


def policy(provider="github", **updates):
    return {
        "provider": provider,
        "repository": "team/project",
        "target_ref": "refs/heads/main",
        "allow_forks": False,
        **updates,
    }


def event(provider, head, base):
    if provider == "github":
        return {
            "event_name": "pull_request",
            "payload": {
                "action": "synchronize",
                "repository": {"full_name": "team/project"},
                "pull_request": {
                    "number": 7,
                    "state": "open",
                    "draft": False,
                    "base": {"ref": "main", "sha": base, "repo": {"full_name": "team/project"}},
                    "head": {"sha": head, "repo": {"full_name": "team/project"}},
                },
            },
        }
    return {
        "event_name": "PullRequest",
        "payload": {
            "repository": {"id": "team/project"},
            "pullRequestId": 7,
            "status": "active",
            "isDraft": False,
            "targetRefName": "refs/heads/main",
            "sourceRefName": "refs/heads/topic",
            "lastMergeSourceCommit": {"commitId": head},
            "lastMergeTargetCommit": {"commitId": base},
        },
    }


def prepared(tmp_path, provider="github"):
    target, trusted, base, req, rendered = fixture(tmp_path, provider)
    for root in (target, trusted):
        if not (root / ".git").exists():
            git(root, "init")
        git(root, "add", ".")
        git(
            root,
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-m",
            "prepared",
        )
    head, revision = (git(p, "rev-parse", "HEAD") for p in (target, trusted))
    return target, trusted, base, req, rendered, event(provider, head, base), revision


@pytest.mark.parametrize("provider", ["github", "azure"])
def test_native_pr_context_binds_clean_head_base_policy_and_request(tmp_path, provider):
    target, trusted, base, req, _, context, revision = prepared(tmp_path, provider)
    admitted = admit_run(
        policy(provider),
        context,
        target,
        trusted,
        req,
        base,
        policy_revision=revision,
        request_digest=content_digest(req.read_bytes()),
    )
    assert admitted.head == git(target, "rev-parse", "HEAD")
    assert admitted.base == base and not admitted.fork


@pytest.mark.parametrize("provider", ["github", "azure"])
@pytest.mark.parametrize(
    "bad",
    [
        "event",
        "base",
        "head",
        "repository",
        "fork",
        "draft",
        "ref",
        "dirty-target",
        "dirty-policy",
        "policy-pin",
        "request-pin",
    ],
)
def test_unsafe_context_never_reaches_common_engine(tmp_path, provider, bad, monkeypatch):
    target, trusted, base, req, rendered, context, revision = prepared(tmp_path, provider)
    binding = {**rendered.document["binding"], "admission": policy(provider)}
    digest = content_digest(req.read_bytes())
    payload = context["payload"]
    pr = payload["pull_request"] if provider == "github" else payload
    if bad == "event":
        context["event_name"] = "push"
    elif bad == "base":
        base = "a" * 40
    elif bad == "head":
        (pr["head"] if provider == "github" else pr["lastMergeSourceCommit"])[
            "sha" if provider == "github" else "commitId"
        ] = "a" * 40
    elif bad == "repository":
        payload["repository"]["full_name" if provider == "github" else "id"] = "other/repo"
    elif bad == "fork":
        if provider == "github":
            pr["head"]["repo"]["full_name"] = "fork/repo"
        else:
            pr["forkSource"] = {"repository": {"id": "fork/repo"}}
    elif bad == "draft":
        pr["draft" if provider == "github" else "isDraft"] = True
    elif bad == "ref":
        if provider == "github":
            pr["base"]["ref"] = "untrusted"
        else:
            pr["targetRefName"] = "refs/heads/untrusted"
    elif bad == "dirty-target":
        (target / "unreviewed.py").write_text("changed")
    elif bad == "dirty-policy":
        (trusted / "conformance.json").write_text("{}")
    elif bad == "policy-pin":
        revision = "a" * 40
    elif bad == "request-pin":
        digest = "a" * 64
    calls = []
    monkeypatch.setattr("cli.pipeline_runtime.inspect_change", lambda *a, **kw: calls.append(a))
    with pytest.raises(ValueError):
        run_bound(
            binding,
            target,
            trusted,
            req,
            base,
            provider_event=context,
            policy_revision=revision,
            request_digest=digest,
        )
    assert not calls


@pytest.mark.parametrize("provider", ["github", "azure"])
def test_admitted_runtime_runs_actual_required_checks(tmp_path, provider):
    target, trusted, base, req, rendered, context, revision = prepared(tmp_path, provider)
    report = run_bound(
        {**rendered.document["binding"], "admission": policy(provider)},
        target,
        trusted,
        req,
        base,
        provider_event=context,
        policy_revision=revision,
        request_digest=content_digest(req.read_bytes()),
    )
    assert report.exit_code == 0
    assert any(
        r.spec.id == "project:tests" and r.outcome.execution.value == "executed"
        for r in report.checks.results
    )


@pytest.mark.parametrize("provider", ["github", "azure"])
def test_renderer_wires_admission_inputs_as_values(provider):
    rendered = artifact(provider, admission=policy(provider)).document
    data = yaml.safe_load(rendered["content"])
    step = data["runs"]["steps"][0] if provider == "github" else data["steps"][0]
    assert {"GOVKIT_PROVIDER_EVENT", "GOVKIT_POLICY_REVISION", "GOVKIT_REQUEST_DIGEST"} <= set(
        step["env"]
    )
    assert rendered["binding"]["admission"] == policy(provider)


def test_renderer_rejects_cross_provider_admission():
    with pytest.raises(ValueError, match="provider"):
        artifact("github", admission=policy("azure"))


def test_request_changed_after_admission_cannot_replace_accepted_intent(tmp_path, monkeypatch):
    from cli import pipeline_runtime

    target, trusted, base, req, rendered, context, revision = prepared(tmp_path)
    admit = pipeline_runtime.admit_run
    accepted = content_digest(req.read_bytes())

    def changed(*args, **kwargs):
        result = admit(*args, **kwargs)
        req.write_text('{"unaccepted":true}')
        return result

    monkeypatch.setattr(pipeline_runtime, "admit_run", changed)
    # The runtime may either reject the race or execute its original accepted byte snapshot.
    report = pipeline_runtime.run_bound(
        {**rendered.document["binding"], "admission": policy()},
        target,
        trusted,
        req,
        base,
        provider_event=context,
        policy_revision=revision,
        request_digest=accepted,
    )
    assert report.exit_code == 0


@pytest.mark.parametrize("provider", ["github", "azure"])
def test_generated_admitted_script_can_publish_change_results_explicitly(tmp_path, provider):
    from cli.gate_catalog import compose_catalog
    from cli.pack_loading import bundled_catalog
    from cli.pipeline_render import parse_settings, render_pipeline
    from cli.profiles import load_profile
    from cli.version import GOVKIT_VERSION
    from tests.test_pipeline_render import settings

    target, trusted, base, req, _, context, revision = prepared(tmp_path, provider)
    rendered = render_pipeline(
        compose_catalog(
            load_profile(trusted / ".govkit/profile.yaml"),
            bundled_catalog(),
            govkit_version=GOVKIT_VERSION,
        ),
        parse_settings(settings(execute_checks=["project:tests"], admission=policy(provider))),
    ).document
    event_path, output = tmp_path / "event.json", tmp_path / "change.json"
    event_path.write_text(json.dumps(context))
    data = yaml.safe_load(rendered["content"])
    step = data["runs"]["steps"][0] if provider == "github" else data["steps"][0]
    env = {
        **os.environ,
        **step["env"],
        "GOVKIT_PYTHON": sys.executable,
        "GOVKIT_TARGET": str(target),
        "GOVKIT_POLICY_TARGET": str(trusted),
        "GOVKIT_BASE": base,
        "GOVKIT_REQUEST": str(req),
        "GOVKIT_PACK_ARGUMENTS": "",
        "GOVKIT_OBSERVED_AT": "2026-09-24T12:00:00Z",
        "GOVKIT_PROVIDER_EVENT": str(event_path),
        "GOVKIT_POLICY_REVISION": revision,
        "GOVKIT_REQUEST_DIGEST": content_digest(req.read_bytes()),
        "GOVKIT_CHANGE_OUTPUT": str(output),
    }
    result = subprocess.run(
        ["bash", "-c", step.get("run", step.get("bash"))],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(output.read_text()) == json.loads(result.stdout)


@pytest.mark.parametrize("provider", ["github", "azure"])
def test_bundled_admitted_entry_points_and_observations_validate(provider):
    from cli import paths
    from cli.gate_catalog import compose_catalog
    from cli.pack_loading import bundled_catalog
    from cli.pipeline_render import parse_settings, render_pipeline
    from cli.profiles import parse_profile
    from cli.provider_admission import parse_event
    from cli.schema_validation import validate_document

    root = paths.GOVERNANCE_DIR / "examples/pipeline"
    config = parse_settings(json.loads((root / f"{provider}-admission-settings.json").read_text()))
    profile = json.loads((root / "profile.json").read_text())
    profile["integrations"]["ci"] = provider
    rendered = render_pipeline(
        compose_catalog(
            parse_profile(profile), bundled_catalog(), govkit_version=config.govkit_version
        ),
        config,
    )
    assert (
        rendered.document["content"] == (root / f"{provider}-admitted-entrypoint.yml").read_text()
    )
    assert (
        parse_event(
            config.admission, json.loads((root / f"{provider}-event.json").read_text())
        ).head
        == "a" * 40
    )
    validate_document(
        json.loads((root / f"{provider}-observation.json").read_text()), "provider-observation"
    )
