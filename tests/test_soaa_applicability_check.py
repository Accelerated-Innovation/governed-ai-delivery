"""The opt-in SOAA applicability coverage check (Phase A Increment 10).

Synthetic fixtures only: a single agent with fixed skills, shaped like the
Value Builder pilot, never an application run.
"""

import copy
import json
import subprocess
import sys

import pytest
import yaml

from cli import paths
from cli.check_models import State
from cli.conformance import inspect_repository
from cli.pack_loading import bundled_catalog
from cli.pack_store import apply_install, preview_install
from cli.version import GOVKIT_VERSION
from tests.test_capability_packs import profile
from tests.test_pack_store import write_profile

PACK = "skill-oriented-agent-architecture"
EXT_DIR = paths.EXTENSION_PACKS_DIR / PACK
SCRIPT = EXT_DIR / "checks/applicability.py"
CHECK = "soaa-applicability"
EXAMPLE = paths.GOVERNANCE_DIR / "examples/experiments/relied/features/discovery/experiments.yaml"
APPLIES = ("adaptive-run", "skill-activation", "untrusted-input")
CONDITIONS = (
    "adaptive-run",
    "skill-activation",
    "untrusted-input",
    "external-read",
    "external-mutation",
    "multi-tenant-data",
    "model-selection",
    "workflow-switching",
    "persistent-memory",
    "human-takeover",
    "delegation",
    "executable-assets",
)
SINGLE_AGENT_CASES = [f"GK-SOAA-{n:02d}" for n in (*range(1, 10), 12, 13, 15, 16)]


def conditions(**overrides):
    rows = []
    for identifier in CONDITIONS:
        row = (
            {
                "id": identifier,
                "status": "applies",
                "reason": "",
                "evidence": "",
                "owner": "",
                "change_trigger": "",
            }
            if identifier in APPLIES
            else {
                "id": identifier,
                "status": "not-applicable",
                "reason": "The fixed-skill assistant has no such interface",
                "evidence": "src/runtime/ports.py declares no such port",
                "owner": "platform team",
                "change_trigger": "A port for this behavior is added",
            }
        )
        rows.append({**row, **overrides.get(identifier, {})})
    return rows


def preflight(rows, *, version=1):
    block = yaml.safe_dump({"soaa_applicability": {"version": version, "conditions": rows}})
    return f"# Architecture preflight\n\n### 15a. SOAA applicability\n\n```yaml\n{block}```\n"


def experiments(refs=SINGLE_AGENT_CASES, *, outcome="pass", required="synthetic-fixture"):
    document = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
    document["feature"] = "value-builder"
    experiment = document["experiments"][0]
    experiment["required_evidence_class"] = required
    experiment["acceptance_criteria"][0]["refs"] = list(refs)
    experiment["result"]["criteria"][0]["outcome"] = outcome
    if outcome != "pass":
        experiment["status"] = "failed"
    return document


def write(tmp_path, rows=None, record=None, *, text=None):
    feature = tmp_path / "features/value-builder"
    feature.mkdir(parents=True, exist_ok=True)
    (feature / "architecture_preflight.md").write_text(
        text if text is not None else preflight(conditions() if rows is None else rows),
        encoding="utf-8",
    )
    if record is not False:
        (feature / "experiments.yaml").write_text(
            yaml.safe_dump(experiments() if record is None else record), encoding="utf-8"
        )
    return [
        "--preflight",
        "features/value-builder/architecture_preflight.md",
        *([] if record is False else ["--experiments", "features/value-builder/experiments.yaml"]),
    ]


def run(tmp_path, arguments):
    result = subprocess.run(
        [sys.executable, "-I", str(SCRIPT), *arguments],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode, json.loads(result.stdout)


# --- Positive -------------------------------------------------------------


def test_single_agent_fixed_skill_fixture_covers_the_cases_its_conditions_select(tmp_path):
    code, report = run(tmp_path, write(tmp_path))
    assert code == 0, report
    assert report["status"] == "pass"
    assert report["claimed"] == SINGLE_AGENT_CASES
    assert [c["case"] for c in report["covered"]] == SINGLE_AGENT_CASES
    assert {c["evidence_class"] for c in report["covered"]} == {"synthetic-fixture"}
    assert report["uncovered"] == [] and report["findings"] == []
    assert report["conditions"]["applies"] == sorted(APPLIES)
    assert len(report["conditions"]["not_applicable"]) == 9
    assert set(report["inputs"]) == {"preflight", "experiments", "catalog"}
    assert all(len(digest) == 64 for digest in report["inputs"].values())
    assert report["limitations"]


def test_an_explicit_claim_may_be_a_subset_of_the_applicable_cases(tmp_path):
    code, report = run(tmp_path, [*write(tmp_path), "--cases", "GK-SOAA-01", "GK-SOAA-04"])
    assert code == 0, report
    assert report["claimed"] == ["GK-SOAA-01", "GK-SOAA-04"]
    assert "GK-SOAA-02" in report["applicable_unclaimed"]


def test_all_not_applicable_needs_no_experiments(tmp_path):
    rows = conditions(**{c: conditions()[-1] | {"id": c} for c in APPLIES})
    code, report = run(tmp_path, write(tmp_path, rows, record=False))
    assert code == 0, report
    assert report["claimed"] == [] and report["inputs"]["experiments"] is None


# --- Not satisfied (exit 1) -------------------------------------------------


def test_unknown_condition_is_never_satisfied(tmp_path):
    rows = conditions(**{"delegation": {"status": "unknown", "reason": "", "evidence": ""}})
    code, report = run(tmp_path, write(tmp_path, rows))
    assert code == 1
    assert report["conditions"]["unknown"] == ["delegation"]
    assert "condition-unknown" in {f["code"] for f in report["findings"]}


def test_condition_missing_from_the_block_is_undecided(tmp_path):
    rows = [r for r in conditions() if r["id"] != "delegation"]
    code, report = run(tmp_path, write(tmp_path, rows))
    assert code == 1
    assert "condition-undecided" in {f["code"] for f in report["findings"]}


@pytest.mark.parametrize("field", ["reason", "evidence", "owner", "change_trigger"])
def test_omission_without_reason_evidence_owner_or_trigger_fails(tmp_path, field):
    rows = conditions(**{"delegation": {field: "  "}})
    code, report = run(tmp_path, write(tmp_path, rows))
    assert code == 1
    finding = next(f for f in report["findings"] if f["code"] == "omission-incomplete")
    assert field in finding["message"]


def test_a_claimed_case_declared_not_applicable_fails(tmp_path):
    code, report = run(tmp_path, [*write(tmp_path), "--cases", "GK-SOAA-10"])
    assert code == 1
    assert "case-not-applicable" in {f["code"] for f in report["findings"]}


def test_a_case_covered_only_by_a_failed_criterion_is_uncovered(tmp_path):
    code, report = run(tmp_path, write(tmp_path, record=experiments(outcome="fail")))
    assert code == 1
    assert report["uncovered"] == SINGLE_AGENT_CASES
    assert report["covered"] == []


def test_synthetic_evidence_cannot_cover_a_criterion_that_requires_application(tmp_path):
    code, report = run(tmp_path, write(tmp_path, record=experiments(required="application")))
    assert code == 1
    assert report["uncovered"] == SINGLE_AGENT_CASES


def test_a_closed_decision_withdraws_coverage(tmp_path):
    record = experiments()
    record["experiments"][0]["decision"]["outcome"] = "reject-approach"
    code, report = run(tmp_path, write(tmp_path, record=record))
    assert code == 1
    assert report["covered"] == []


def test_uncited_applicable_cases_are_uncovered(tmp_path):
    record = experiments(refs=SINGLE_AGENT_CASES[:-1])
    code, report = run(tmp_path, write(tmp_path, record=record))
    assert code == 1
    assert report["uncovered"] == ["GK-SOAA-16"]


# --- Invalid input (exit 2) -------------------------------------------------


@pytest.mark.parametrize(
    "cases",
    [["GK-SOAA-99"], ["GK-SOAA-01", "GK-SOAA-01"], ["not a case"]],
)
def test_unknown_or_duplicate_claimed_case_ids_are_invalid(tmp_path, cases):
    code, report = run(tmp_path, [*write(tmp_path), "--cases", *cases])
    assert code == 2
    assert report["status"] == "invalid"


@pytest.mark.parametrize(
    "rows",
    [
        conditions(**{"delegation": {"status": "maybe"}}),
        conditions() + [conditions()[0]],
        conditions() + [{**conditions()[-1], "id": "no-such-condition"}],
    ],
)
def test_malformed_blocks_are_invalid(tmp_path, rows):
    code, report = run(tmp_path, write(tmp_path, rows))
    assert code == 2
    assert report["status"] == "invalid"


def test_wrong_block_version_is_invalid(tmp_path):
    code, _ = run(tmp_path, write(tmp_path, text=preflight(conditions(), version=2)))
    assert code == 2


@pytest.mark.parametrize("count", [0, 2])
def test_preflight_needs_exactly_one_block(tmp_path, count):
    block = preflight(conditions()).split("### 15a. SOAA applicability\n\n", 1)[1]
    code, _ = run(tmp_path, write(tmp_path, text="# Preflight\n\n" + block * count))
    assert code == 2


def test_schema_invalid_experiments_are_invalid(tmp_path):
    record = experiments()
    del record["experiments"][0]["oracle"]
    code, report = run(tmp_path, write(tmp_path, record=record))
    assert code == 2 and report["status"] == "invalid"


def test_missing_input_file_is_invalid(tmp_path):
    code, _ = run(tmp_path, ["--preflight", "features/none/architecture_preflight.md"])
    assert code == 2


# --- Evidence binding -------------------------------------------------------


def test_a_changed_results_file_changes_the_reported_digest(tmp_path):
    arguments = write(tmp_path)
    _, first = run(tmp_path, arguments)
    record = experiments()
    record["experiments"][0]["result"]["summary"] = "A different recorded summary."
    write(tmp_path, record=record)
    _, second = run(tmp_path, arguments)
    assert first["status"] == second["status"] == "pass"
    assert first["inputs"]["experiments"] != second["inputs"]["experiments"]
    assert first["inputs"]["preflight"] == second["inputs"]["preflight"]


def test_output_is_deterministic(tmp_path):
    arguments = write(tmp_path)
    assert run(tmp_path, arguments) == run(tmp_path, arguments)


# --- Through conformance ------------------------------------------------------


def result(report, identifier):
    return next(r for r in report.results if r.spec.id == identifier)


def install(tmp_path, *, required):
    path = write_profile(tmp_path, profile([PACK], checks=[CHECK] if required else []))
    apply_install(preview_install(path, tmp_path, bundled_catalog(), govkit_version=GOVKIT_VERSION))
    return write(tmp_path)


def test_unexecuted_and_absent_from_policy_the_check_is_advisory(tmp_path):
    install(tmp_path, required=False)
    report = inspect_repository(tmp_path)
    checked = result(report, CHECK)
    assert checked.outcome.state is State.SKIPPED
    assert checked.spec.required is False
    assert report.exit_code == 0


def test_unexecuted_policy_required_check_is_not_satisfied(tmp_path):
    install(tmp_path, required=True)
    report = inspect_repository(tmp_path)
    checked = result(report, CHECK)
    assert checked.outcome.state is State.SKIPPED
    assert checked.spec.required is True
    assert report.exit_code == 1


def test_executed_through_conformance_passes_then_fails_with_the_evidence(tmp_path):
    arguments = tuple(install(tmp_path, required=True))
    options = {"execute_pack_checks": (CHECK,), "pack_arguments": {CHECK: arguments}}
    report = inspect_repository(tmp_path, **options)
    assert result(report, CHECK).outcome.state is State.PASS
    assert report.exit_code == 0
    passed = result(report, CHECK).outcome.evidence[0].digest
    write(tmp_path, record=experiments(outcome="fail"))
    report = inspect_repository(tmp_path, **options)
    assert result(report, CHECK).outcome.state is State.FAIL
    assert result(report, CHECK).outcome.evidence[0].digest != passed
    assert report.exit_code == 1


def test_fixture_helpers_do_not_mutate_the_shared_example():
    before = copy.deepcopy(yaml.safe_load(EXAMPLE.read_text(encoding="utf-8")))
    experiments(refs=["GK-SOAA-01"], outcome="fail", required="application")
    assert yaml.safe_load(EXAMPLE.read_text(encoding="utf-8")) == before


# --- PR #239 review -----------------------------------------------------------


def test_an_experiment_record_for_another_feature_is_invalid(tmp_path):
    record = experiments()
    record["feature"] = "discovery"
    code, report = run(tmp_path, write(tmp_path, record=record))
    assert code == 2 and "feature" in report["error"]


def test_experiments_outside_the_preflight_feature_directory_are_invalid(tmp_path):
    arguments = write(tmp_path)
    other = tmp_path / "features/other"
    other.mkdir(parents=True)
    other.joinpath("experiments.yaml").write_text(yaml.safe_dump(experiments()))
    arguments[-1] = "features/other/experiments.yaml"
    code, report = run(tmp_path, arguments)
    assert code == 2 and report["status"] == "invalid"


def test_a_passed_criterion_without_evidence_does_not_cover(tmp_path):
    record = experiments()
    record["experiments"][0]["result"]["criteria"][0]["evidence"] = []
    code, report = run(tmp_path, write(tmp_path, record=record))
    assert code == 1
    assert report["uncovered"] == SINGLE_AGENT_CASES


def custom_catalog(tmp_path, document):
    path = tmp_path / "catalog.yaml"
    path.write_text(yaml.safe_dump(document))
    return ["--catalog", str(path)]


@pytest.mark.parametrize(
    "document",
    [
        {"version": 1, "conditions": [{"id": ["adaptive-run"]}], "cases": []},
        {"version": 1, "conditions": [{"id": " "}], "cases": []},
        {"version": 1, "conditions": [{"id": c} for c in CONDITIONS]},
        {"version": 1, "conditions": [{"id": c} for c in CONDITIONS], "cases": "none"},
    ],
)
def test_malformed_or_empty_custom_catalogs_are_invalid(tmp_path, document):
    arguments = [*write(tmp_path), *custom_catalog(tmp_path, document)]
    code, report = run(tmp_path, arguments)
    assert code == 2 and report["status"] == "invalid"


def test_missing_parser_names_the_required_govkit_release():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "GovKit 0.23.0 or later" in text
    assert "GovKit 0.23.0 or later" in (EXT_DIR / "README.md").read_text(encoding="utf-8")


def test_pack_floor_includes_the_experiment_parser_once_released():
    from packaging.version import InvalidVersion, Version

    from cli.version import GOVKIT_VERSION

    try:
        running = Version(GOVKIT_VERSION)
    except InvalidVersion:
        pytest.skip("unversioned development install")
    floor = Version(yaml.safe_load((EXT_DIR / "manifest.yaml").read_text())["govkit_min_version"])
    if running >= Version("0.23.0"):
        assert floor >= Version("0.23.0"), "raise govkit_min_version with the 0.23.0 release"


def test_readme_conform_example_supplies_pack_arguments():
    text = (EXT_DIR / "README.md").read_text(encoding="utf-8")
    section = text[
        text.index("## Applicability coverage check") : text.index("## Source authority")
    ]
    assert "--execute-pack-check soaa-applicability" in section
    assert "--pack-arguments" in section and "soaa-applicability:" in section
