"""The verification-run templates post a build's results to the graph (L09b).

Each template's own build and post scripts are run in a real repository, with
the provider's variables set as the provider sets them. No test reaches a
graph: the post step is run where there is nothing to send, and where no run
was built.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from cli import paths, verification_push
from cli.schema_validation import validate_document
from tests.test_verification_run import TAG, _git, _results, repo  # noqa: F401

PROVIDERS = ["github", "azure"]
BUILD, POST = "Build the verification run", "Post the verification run"
pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="the templates run bash")


def _path(provider) -> Path:
    return paths.REPO_ROOT / "ci" / provider / "verification-run.yml"


def _document(provider) -> dict:
    return yaml.safe_load(_path(provider).read_text(encoding="utf-8"))


def _steps(provider):
    document = _document(provider)
    if provider == "github":
        return document["jobs"]["verification-run"]["steps"]
    return document["stages"][0]["jobs"][0]["steps"]


def _named(provider, name):
    key = "name" if provider == "github" else "displayName"
    return next(step for step in _steps(provider) if step.get(key) == name)


def _script(step):
    return step.get("run") or step.get("bash") or step.get("script") or ""


def _run(provider, name, target, scratch, **variables):
    environment = {
        **{k: v for k, v in os.environ.items() if not k.startswith("GOVKIT_")},
        "PATH": f"{Path(sys.executable).parent}{os.pathsep}{os.environ['PATH']}",
        "OUTPUT_DIRECTORY": str(scratch),
        "GITHUB_STEP_SUMMARY": str(scratch / "summary.md"),
        "GOVKIT_BASELINE_TAG": TAG,
        "GOVKIT_GRAPH_REPOSITORY": "acme/invoices",
        "RUN_REFERENCE": f"{provider}:1234567890-1",
        "RUN_ADDRESS": "https://ci.example.invalid/acme/_build/results?buildId=1234567890",
        **variables,
    }
    return subprocess.run(
        ["bash", "-e", "-o", "pipefail", "-c", _script(_named(provider, name))],
        cwd=target, env=environment, capture_output=True, text=True,
    )  # fmt: skip


@pytest.fixture
def scratch(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp("runner")


@pytest.mark.parametrize("provider", PROVIDERS)
def test_the_template_ships_for_both_providers_and_is_listed(provider):
    assert _path(provider).is_file()
    readme = (paths.REPO_ROOT / "ci" / "README.md").read_text(encoding="utf-8")
    assert "verification-run.yml" in readme


def test_it_runs_on_the_default_branch_only():
    github = _document("github")
    # PyYAML reads the key `on` as the boolean true.
    assert github[True] == {"push": {"branches": ["main"]}}
    azure = _document("azure")
    assert azure["trigger"] == {"branches": {"include": ["main"]}}
    assert azure["pr"] == "none"


def test_it_is_skipped_until_the_baseline_tag_is_set():
    job = _document("github")["jobs"]["verification-run"]
    assert job["if"] == "${{ vars.GOVKIT_BASELINE_TAG != '' }}"
    stage = _document("azure")["stages"][0]
    assert stage["condition"] == "ne(variables['GOVKIT_BASELINE_TAG'], '')"


@pytest.mark.parametrize("provider", PROVIDERS)
def test_the_clone_holds_the_tags_and_keeps_no_credential(provider):
    checkout = _steps(provider)[0]
    if provider == "github":
        settings = checkout["with"]
        assert (settings["fetch-depth"], settings["fetch-tags"]) == (0, True)
        assert settings["persist-credentials"] is False
        assert _document("github")["permissions"] == {"contents": "read"}
    else:
        assert (checkout["fetchDepth"], checkout["fetchTags"]) == (0, True)
        assert checkout["persistCredentials"] is False


@pytest.mark.parametrize("provider", PROVIDERS)
def test_only_the_post_step_receives_the_service_token(provider):
    text = _path(provider).read_text(encoding="utf-8")
    body = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
    assert body.count(verification_push.TOKEN_ENV) == 2  # one mapping: name and value
    assert verification_push.TOKEN_ENV in _named(provider, POST)["env"]
    assert verification_push.URL_ENV in _named(provider, POST)["env"]
    post = _named(provider, POST)
    others = [step for step in _steps(provider) if step != post]
    assert len(others) == len(_steps(provider)) - 1
    assert verification_push.TOKEN_ENV not in json.dumps(others)
    # The read-only credential of the authority gate is not used here.
    assert "GOVKIT_PDG_TOKEN" not in body.replace(verification_push.TOKEN_ENV, "")


@pytest.mark.parametrize("provider", PROVIDERS)
def test_the_steps_run_in_order_even_after_failing_tests(provider):
    steps = _steps(provider)
    scripts = [_script(step) for step in steps]
    order = [
        next(i for i, text in enumerate(scripts) if marker in text)
        for marker in (
            "Not configured",
            "govkit evidence --record --target .",
            "govkit verification-run build",
            "govkit verification-run push",
        )
    ]
    assert order == sorted(order)
    condition = "if" if provider == "github" else "condition"
    assert all(steps[i].get(condition) for i in order[1:])


def test_the_two_templates_run_the_same_scripts():
    def commands(provider, name):
        lines = _script(_named(provider, name)).splitlines()
        # The summary and the notice are each provider's own.
        own = ("GITHUB_STEP_SUMMARY", "::notice", "##vso", "summary")
        return [line.strip() for line in lines if not any(mark in line for mark in own)]

    assert commands("github", BUILD) == commands("azure", BUILD)
    assert commands("github", POST) == commands("azure", POST)


@pytest.mark.parametrize("provider", PROVIDERS)
def test_the_build_step_writes_a_run_and_its_account(provider, repo, scratch):  # noqa: F811
    _results(repo)
    result = _run(provider, BUILD, repo, scratch)
    assert result.returncode == 0, result.stdout + result.stderr
    document = json.loads((scratch / "verification-run.json").read_text(encoding="utf-8"))
    validate_document(document, "verification-run")
    request = document["request"]
    assert len(request["results"]) == 5
    assert request["run_reference"] == f"{provider}:1234567890-1"
    assert request["baseline_tag"] == TAG and request["repository"] == "acme/invoices"
    assert "5 result(s) to send" in result.stdout
    summary = "summary.md" if provider == "github" else "verification-run.md"
    assert "3 left out: no-result" in (scratch / summary).read_text(encoding="utf-8")


@pytest.mark.parametrize("provider", PROVIDERS)
def test_nothing_to_send_passes_with_a_notice_and_posts_nothing(provider, repo, scratch):  # noqa: F811
    # No result files: the placeholder test step has not been replaced.
    built = _run(provider, BUILD, repo, scratch)
    assert built.returncode == 0, built.stdout + built.stderr
    assert "Nothing can be sent to the graph." in built.stdout
    # Run with no address and no token: nothing is sent, so none is needed.
    posted = _run(provider, POST, repo, scratch)
    assert posted.returncode == 0, posted.stdout + posted.stderr
    assert "Nothing was sent to the graph." in posted.stdout


@pytest.mark.parametrize("provider", PROVIDERS)
def test_a_wrong_setting_fails_the_build_step_and_then_the_post_step(provider, repo, scratch):  # noqa: F811
    _results(repo)
    built = _run(provider, BUILD, repo, scratch, GOVKIT_BASELINE_TAG="not-a-tag")
    assert built.returncode == 2
    assert "no tag named" in built.stdout
    assert not (scratch / "verification-run.json").exists()
    posted = _run(provider, POST, repo, scratch)
    assert posted.returncode == 1 and "No verification run was built" in posted.stdout


@pytest.mark.parametrize("provider", PROVIDERS)
def test_a_run_with_results_is_not_posted_without_its_settings(provider, repo, scratch):  # noqa: F811
    _results(repo)
    assert _run(provider, BUILD, repo, scratch).returncode == 0
    posted = _run(provider, POST, repo, scratch)
    assert posted.returncode == 2
    assert verification_push.TOKEN_ENV in posted.stderr


def test_the_azure_run_address_holds_no_project_name():
    # A project name may hold a space, which the graph refuses in an address.
    address = _named("azure", BUILD)["env"]["RUN_ADDRESS"]
    assert "System.TeamProjectId" in address and "System.TeamProject)" not in address
