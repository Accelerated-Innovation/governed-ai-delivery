"""Provider entry points retain one bound common engine and literal runtime inputs."""

import base64
import json

import pytest
import yaml

from cli import paths
from cli.gate_catalog import compose_catalog
from cli.pack_loading import bundled_catalog
from cli.pipeline_render import parse_render, parse_settings, render_pipeline
from cli.profiles import parse_profile
from cli.version import GOVKIT_VERSION
from tests.test_capability_packs import profile


def settings(**updates):
    return {"schema_version": 1, "govkit_version": GOVKIT_VERSION, "execute_checks": [], **updates}


def artifact(provider="github", capabilities=None, **updates):
    doc = profile(capabilities or ["application-governance", "llm-evaluation"]).document
    doc["integrations"]["ci"] = provider
    config = parse_settings(settings(**updates))
    catalog = compose_catalog(parse_profile(doc), bundled_catalog(), govkit_version=GOVKIT_VERSION)
    return render_pipeline(catalog, config)


@pytest.mark.parametrize("provider", ["github", "azure"])
def test_renderer_is_deterministic_replayable_and_does_not_select_request_workflow(provider):
    rendered = artifact(provider, execute_checks=["project:tests"])
    assert rendered.to_json() == artifact(provider, execute_checks=["project:tests"]).to_json()
    assert parse_render(rendered.document).to_json() == rendered.to_json()
    data = yaml.safe_load(rendered.document["content"])
    step = data["runs"]["steps"][0] if provider == "github" else data["steps"][0]
    script = step.get("run", step.get("bash"))
    assert script.endswith('exec -- "$GOVKIT_PYTHON" -I -m cli.pipeline_runtime\n')
    assert "${{" not in script and "$[" not in script
    assert "if" not in step and "condition" not in step and "continueOnError" not in step
    binding = json.loads(base64.b64decode(step["env"]["GOVKIT_BINDING"]))
    assert binding["govkit_version"] == GOVKIT_VERSION
    assert binding["execute_checks"] == ["project:tests"]
    assert rendered.document["execution"] == "not-run"
    assert rendered.document["enforcement"] == "unknown"
    assert "pip install" not in script


def test_renderers_have_equivalent_controls_and_execution_opt_ins():
    first, second = artifact().document, artifact("azure").document
    assert first["catalog"]["gates"] == second["catalog"]["gates"]
    assert first["settings"] == second["settings"]
    assert first["path"] == ".github/actions/govkit-conformance/action.yml"
    assert second["path"] == "ci/azure/govkit-conformance.generated.yml"


@pytest.mark.parametrize("value", [">=0.21.1", "0.1.0", "1.0;touch pwned", True])
def test_invalid_or_unsupported_runtime_pins_are_rejected(value):
    with pytest.raises(ValueError):
        parse_settings(settings(govkit_version=value))


@pytest.mark.parametrize("value", [["x; echo unsafe"], ["project:tests", "project:tests"], "tests"])
def test_execution_opt_ins_are_explicit_unique_ids(value):
    with pytest.raises(ValueError):
        parse_settings(settings(execute_checks=value))


@pytest.mark.parametrize("mutation", ["path", "content", "catalog", "digest"])
def test_saved_render_cannot_change_destinations_or_commands(mutation):
    document = artifact().document
    if mutation == "catalog":
        document["catalog"]["gates"].clear()
    else:
        document[mutation] = "../unrelated"
    with pytest.raises(ValueError):
        parse_render(document)


def test_unresolved_composition_and_absent_provider_cannot_render():
    for provider, capabilities in ((None, ["application-governance"]), ("github", ["unknown"])):
        with pytest.raises(ValueError):
            artifact(provider, capabilities)


@pytest.mark.parametrize("provider", ["github", "azure"])
def test_bundled_provider_golden_matches_accepted_example(provider):
    root = paths.GOVERNANCE_DIR / "examples/pipeline"
    document = json.loads((root / "profile.json").read_text())
    document["integrations"]["ci"] = provider
    config = parse_settings(json.loads((root / "settings.json").read_text()))
    catalog = compose_catalog(
        parse_profile(document), bundled_catalog(), govkit_version=config.govkit_version
    )
    rendered = render_pipeline(catalog, config)
    assert rendered.document["content"] == (root / f"{provider}-entrypoint.yml").read_text()


def test_renderer_rejects_a_binding_that_the_runtime_cannot_read():
    with pytest.raises(ValueError, match="binding.*large"):
        artifact(execute_checks=["x" * 50000])
