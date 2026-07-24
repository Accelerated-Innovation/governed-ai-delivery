"""Behavior tests for the dbt-gate embedded static checker.

Increment 8 of the data-enforcement hardening plan: the gate converts the
mart docs teams edit into checks the build runs — every mart model must
declare an enforced dbt model contract and appear in at least one exposure.
The pure-python checker is embedded in both platform gates via a heredoc;
these tests extract it and execute it against fixtures, and pin the two
embeddings identical so the platforms cannot drift.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
GATE_PATHS = {
    "github": REPO_ROOT / "ci" / "github" / "dbt-gate.yml",
    "azure": REPO_ROOT / "ci" / "azure" / "dbt-gate.yml",
}


def _extract_embedded_python(gate_path: Path) -> str:
    """Pull the python heredoc body out of the gate's raw text, de-indented."""
    raw = gate_path.read_text(encoding="utf-8")
    start_marker = "python - <<'PY'\n"
    start = raw.index(start_marker) + len(start_marker)
    body_lines = []
    for line in raw[start:].splitlines():
        if line.strip() == "PY":
            break
        body_lines.append(line)
    indent = min(
        (len(line) - len(line.lstrip()) for line in body_lines if line.strip()),
        default=0,
    )
    return "\n".join(line[indent:] for line in body_lines) + "\n"


def _run_checker(tmp_path: Path) -> subprocess.CompletedProcess:
    script = _extract_embedded_python(GATE_PATHS["github"])
    return subprocess.run(
        [sys.executable, "-"],
        input=script,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )


def _write_fixture(
    tmp_path: Path,
    *,
    contract: bool = True,
    exposure: bool = True,
    dbt_version: str | None = ">=1.5.0",
) -> None:
    project: dict = {"name": "fixture"}
    if dbt_version:
        project["require-dbt-version"] = dbt_version
    (tmp_path / "dbt_project.yml").write_text(
        yaml.safe_dump(project),
        encoding="utf-8",
    )
    marts = tmp_path / "models" / "marts"
    marts.mkdir(parents=True)
    (marts / "dim_customers.sql").write_text(
        "select 1 as customer_id\n",
        encoding="utf-8",
    )
    model: dict = {
        "name": "dim_customers",
        "description": "Customer dimension",
        "columns": [
            {
                "name": "customer_id",
                "description": "Primary key",
                "tests": ["unique", "not_null"],
            }
        ],
    }
    if contract:
        model["config"] = {"contract": {"enforced": True}}
    doc: dict = {"models": [model]}
    if exposure:
        doc["exposures"] = [
            {
                "name": "looker_customers",
                "type": "dashboard",
                "owner": {"name": "analytics"},
                "depends_on": ["ref('dim_customers')"],
            }
        ]
    (marts / "_customers.yml").write_text(yaml.safe_dump(doc), encoding="utf-8")


def test_embedded_checker_identical_across_platforms():
    scripts = {k: _extract_embedded_python(p) for k, p in GATE_PATHS.items()}
    assert scripts["github"] == scripts["azure"]


class TestMartContractChecks:
    def test_contracted_and_exposed_mart_passes(self, tmp_path):
        _write_fixture(tmp_path)
        result = _run_checker(tmp_path)
        assert result.returncode == 0, result.stdout + result.stderr

    def test_mart_without_contract_fails(self, tmp_path):
        _write_fixture(tmp_path, contract=False)
        result = _run_checker(tmp_path)
        assert result.returncode == 1
        assert "contract" in result.stdout
        assert "dim_customers" in result.stdout

    def test_mart_without_exposure_fails(self, tmp_path):
        _write_fixture(tmp_path, exposure=False)
        result = _run_checker(tmp_path)
        assert result.returncode == 1
        assert "exposure" in result.stdout
        assert "dim_customers" in result.stdout

    def test_old_dbt_downgrades_contract_check_to_warning(self, tmp_path):
        """Pre-1.5 dbt has no model contracts: the contract check warns with
        an upgrade pointer instead of failing (conservative-gate philosophy).
        The exposure check still applies."""
        _write_fixture(tmp_path, contract=False, dbt_version=None)
        result = _run_checker(tmp_path)
        assert result.returncode == 0, result.stdout + result.stderr
        assert "1.5" in result.stdout

    def test_no_marts_dir_adds_no_mart_errors(self, tmp_path):
        """Projects without models/marts/ (staging-only repos) see no mart
        findings; the existing model checks still run."""
        (tmp_path / "dbt_project.yml").write_text("name: fixture\n", encoding="utf-8")
        staging = tmp_path / "models" / "staging"
        staging.mkdir(parents=True)
        (staging / "_stg.yml").write_text(
            yaml.safe_dump(
                {
                    "models": [
                        {
                            "name": "stg_customers",
                            "description": "staging",
                            "columns": [
                                {
                                    "name": "customer_id",
                                    "description": "pk",
                                    "tests": ["unique", "not_null"],
                                }
                            ],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        result = _run_checker(tmp_path)
        assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("platform", sorted(GATE_PATHS))
def test_gate_documents_project_evaluator_opt_in(platform):
    text = GATE_PATHS[platform].read_text(encoding="utf-8")
    assert "dbt-project-evaluator" in text


@pytest.mark.parametrize("platform", sorted(GATE_PATHS))
def test_gate_header_lists_mart_checks_as_blocking(platform):
    text = GATE_PATHS[platform].read_text(encoding="utf-8")
    assert "contract" in text
    assert "exposure" in text
