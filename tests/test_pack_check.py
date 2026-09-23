"""Exercise the shipped executable, including failure and invalid-input statuses."""

import json
import subprocess
import sys

import pytest

from cli import paths


@pytest.mark.parametrize(
    "document",
    [
        None,
        [],
        {},
        {"cases": []},
        {"cases": {}},
        {"cases": [{"id": "x", "expected": "secret", "actual": None}]},
        {"cases": [{"id": " ", "expected": "secret", "actual": "secret"}]},
        {"cases": [{"id": "x", "expected": "secret", "actual": "secret"}] * 2},
    ],
)
def test_invalid_evaluation_records_never_pass(tmp_path, document):
    source = tmp_path / "results.json"
    source.write_text(json.dumps(document))
    command = [
        sys.executable,
        "-I",
        str(paths.EXTENSION_PACKS_DIR / "llm-evaluation/checks/exact_match.py"),
        "--results",
        str(source),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    assert result.returncode == 2
    assert json.loads(result.stdout)["status"] == "invalid"
    assert "secret" not in result.stdout
