"""A generated pipeline that judges every feature a change touches (L08b)."""

import json
import os
import subprocess
import sys

import pytest
import yaml

from cli.change_conformance import parse_feature_verdicts
from cli.gate_catalog import compose_catalog
from cli.pack_loading import bundled_catalog
from cli.pack_store import apply_install, preview_install
from cli.pipeline_render import parse_render, parse_settings, render_pipeline
from cli.pipeline_runtime import run_bound
from cli.profiles import load_profile
from cli.schema_validation import DocumentError
from cli.version import GOVKIT_VERSION
from tests import test_change_verdicts as verdicts
from tests.test_change_verdict import FEATURE, PASSING, _with
from tests.test_discovery import write
from tests.test_pipeline_render import settings

OTHER = verdicts.OTHER
OBSERVED = "2026-09-23T12:00:00Z"
TESTS = ["project:tests"]


def fixture(tmp_path, provider="github", **updates):
    tmp_path.mkdir(exist_ok=True)
    target, trusted, base = verdicts._project(tmp_path)
    source = trusted / ".govkit/profile.yaml"
    document = json.loads(source.read_text())
    document["integrations"]["ci"] = provider
    source.write_text(json.dumps(document))
    apply_install(
        preview_install(source, trusted, bundled_catalog(), govkit_version=GOVKIT_VERSION)
    )
    request = write(tmp_path, "request.json", json.dumps(verdicts.SCOPE))
    catalog = compose_catalog(
        load_profile(source), bundled_catalog(), govkit_version=GOVKIT_VERSION
    )
    artifact = render_pipeline(catalog, parse_settings(settings(execute_checks=TESTS, **updates)))
    return target, trusted, base, request, artifact


def _step(artifact, provider):
    document = yaml.safe_load(artifact.document["content"])
    return document["runs"]["steps"][0] if provider == "github" else document["steps"][0]


def _inputs(artifact, provider):
    document = yaml.safe_load(artifact.document["content"])
    if provider == "github":
        return set(document["inputs"])
    return {parameter["name"] for parameter in document["parameters"]}


@pytest.mark.parametrize("provider", ["github", "azure"])
def test_the_setting_is_carried_in_the_binding_and_adds_one_input(tmp_path, provider):
    *_, plain = fixture(tmp_path / "plain", provider)
    *_, judged = fixture(tmp_path / "judged", provider, features="changed")
    assert "features" not in plain.document["binding"]
    assert "features" not in plain.document["settings"]
    assert judged.document["binding"]["features"] == "changed"
    assert _inputs(judged, provider) - _inputs(plain, provider) == {"feature_output"}
    assert "GOVKIT_FEATURE_OUTPUT" in _step(judged, provider)["env"]
    assert "GOVKIT_FEATURE_OUTPUT" not in _step(plain, provider)["env"]
    assert parse_render(judged.document).to_json() == judged.to_json()
    assert judged.document["digest"] != plain.document["digest"]


def test_only_the_one_value_is_a_setting():
    with pytest.raises(DocumentError):
        parse_settings(settings(features="all"))
    with pytest.raises(DocumentError):
        parse_settings(settings(features=None))


def test_the_runtime_judges_the_touched_features_as_the_engine_does(tmp_path):
    target, trusted, base, request, artifact = fixture(tmp_path, features="changed")
    verdicts._touch(target, FEATURE, OTHER)
    verdicts._results(target, [*PASSING, *verdicts.OTHER_CASES])
    report = run_bound(
        artifact.document["binding"], target, trusted, request, base, observed_at=OBSERVED
    )
    expected = verdicts._inspect(target, trusted, base)
    assert report.to_json() == expected.to_json() and report.answers == expected.answers
    assert [verdict["state"] for _, verdict in report.answers] == ["done", "done"]


def test_without_the_setting_the_runtime_judges_no_feature(tmp_path):
    target, trusted, base, request, artifact = fixture(tmp_path)
    verdicts._touch(target, FEATURE)
    report = run_bound(
        artifact.document["binding"], target, trusted, request, base, observed_at=OBSERVED
    )
    assert report.answers is None
    assert not any("[" in r.spec.id for r in report.checks.results)


def _run(tmp_path, provider, project, **variables):
    target, trusted, base, request, artifact = project
    step = _step(artifact, provider)
    environment = {
        **os.environ,
        **step["env"],
        "GOVKIT_PYTHON": sys.executable,
        "GOVKIT_TARGET": str(target),
        "GOVKIT_POLICY_TARGET": str(trusted),
        "GOVKIT_REQUEST": str(request),
        "GOVKIT_BASE": base,
        "GOVKIT_PACK_ARGUMENTS": "",
        "GOVKIT_OBSERVED_AT": OBSERVED,
        "GOVKIT_FEATURE_OUTPUT": "",
        **variables,
    }
    return subprocess.run(
        ["bash", "-c", step.get("run", step.get("bash"))],
        env=environment,
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize("provider", ["github", "azure"])
def test_the_generated_script_writes_the_answers_and_keeps_the_record(tmp_path, provider):
    project = fixture(tmp_path, provider, features="changed")
    target = project[0]
    verdicts._touch(target, FEATURE, OTHER)
    verdicts._results(target, [*_with(PASSING, PASSING[0][0], "skip"), *verdicts.OTHER_CASES])
    output = tmp_path / "answers.json"
    result = _run(tmp_path, provider, project, GOVKIT_FEATURE_OUTPUT=str(output))
    record = json.loads(result.stdout)
    assert record["kind"] == "change-results" and result.returncode == 1 == record["exit_code"]
    assert f"Feature {FEATURE}: ESCALATE" in result.stderr
    assert f"Feature {OTHER}: DONE" in result.stderr
    answers = json.loads(output.read_text())
    assert parse_feature_verdicts(answers) == answers and answers["change"] == record
    assert [a["state"] for a in answers["features"]] == ["escalate", "done"]


def test_every_touched_feature_done_exits_zero(tmp_path):
    project = fixture(tmp_path, features="changed")
    verdicts._touch(project[0], FEATURE)
    verdicts._results(project[0], PASSING)
    result = _run(tmp_path, "github", project)
    assert result.returncode == 0, result.stderr
    assert result.stderr.strip() == f"Feature {FEATURE}: DONE"


def test_no_touched_feature_says_so_and_writes_an_empty_list(tmp_path):
    project = fixture(tmp_path, features="changed")
    write(project[0], "src/service.py", "# good changed\n")
    output = tmp_path / "answers.json"
    result = _run(tmp_path, "github", project, GOVKIT_FEATURE_OUTPUT=str(output))
    assert result.returncode == 0, result.stderr
    assert "touches no feature directory" in result.stderr
    assert json.loads(output.read_text())["features"] == []


def test_an_existing_answers_file_is_not_overwritten(tmp_path):
    project = fixture(tmp_path, features="changed")
    output = write(tmp_path, "answers.json", "kept")
    result = _run(tmp_path, "github", project, GOVKIT_FEATURE_OUTPUT=str(output))
    assert result.returncode == 1 and output.read_text() == "kept"


@pytest.mark.parametrize("place", ["relative", "policy", "target"])
def test_an_unsafe_answers_path_is_refused(tmp_path, place):
    project = fixture(tmp_path, features="changed")
    path = {
        "relative": "answers.json",
        "policy": str(project[1] / "answers.json"),
        "target": str(project[0] / "answers.json"),
    }[place]
    result = _run(tmp_path, "github", project, GOVKIT_FEATURE_OUTPUT=path)
    assert result.returncode == 1 and result.stdout == "" and "Error:" in result.stderr
    assert not (tmp_path / "answers.json").exists()
    assert not (project[0] / "answers.json").exists()


def test_an_answers_path_needs_the_setting(tmp_path):
    project = fixture(tmp_path)
    output = tmp_path / "answers.json"
    result = _run(tmp_path, "github", project, GOVKIT_FEATURE_OUTPUT=str(output))
    assert result.returncode == 1 and "generated to judge features" in result.stderr
    assert not output.exists()
