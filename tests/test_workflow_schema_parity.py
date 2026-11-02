"""The change-results plan copy must equal the workflow-plan schema."""

import json

from cli import paths


def _schema(name):
    return json.loads((paths.GOVERNANCE_DIR / "schemas" / f"{name}.schema.json").read_text())


def test_change_results_embeds_the_workflow_plan_schema():
    plan = {k: v for k, v in _schema("workflow-plan").items() if k not in {"$schema", "title"}}
    assert _schema("change-results")["properties"]["plan"] == plan


def test_request_schema_accepts_experiment_references():
    kinds = _schema("workflow-request")["properties"]["references"]["items"]["properties"]["kind"]
    assert kinds["enum"] == [
        "acceptance",
        "nfr",
        "contract",
        "established-behavior",
        "regression-test",
        "experiment",
    ]
