"""Frozen pre-refactor selections, including order and installer attributes."""

import copy
import hashlib
import json
from pathlib import Path

import pytest

from cli.manifest import load_manifest, resolve_variant_files

BASELINE = json.loads(
    (Path(__file__).parent / "fixtures" / "legacy-resolution-baseline.json").read_text()
)


@pytest.mark.parametrize("case,expected", BASELINE["cases"].items())
def test_supported_legacy_selection_matches_before_refactor(case, expected):
    agent, kind, level, ci, stack = case.split("|")
    options = {"level": level, "type": kind, "ci": ci}
    if stack != "-":
        options["stack"] = stack
    manifest = load_manifest(agent)
    original = copy.deepcopy(manifest)
    result = resolve_variant_files(manifest, options)
    digest = hashlib.sha256(
        json.dumps(result, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    assert digest == expected, f"{case} changed its ordered install selection: {result!r}"
    assert manifest == original


def test_legacy_keeps_base_duplicates_and_first_entry_attributes():
    manifest = {
        "base_files": [
            {"src": "base", "dest": "AGENTS.md", "managed_block": True},
            {"src": "base", "dest": "AGENTS.md", "managed_block": False},
        ],
        "variants": {
            "type": {
                "api": {
                    "files": [
                        {"src": "base", "dest": "AGENTS.md", "path_scoped": True},
                        {"src": "rules/", "dest": "rules/", "custom": {"nested": [1, 2]}},
                    ]
                }
            }
        },
    }
    files, shared, governed = resolve_variant_files(manifest, {"type": "api"})
    assert files == manifest["base_files"] + [manifest["variants"]["type"]["api"]["files"][1]]
    assert shared == governed == []


def test_legacy_dimension_order_is_preserved():
    manifest = {
        "variants": {
            "type": {"api": {"files": [{"src": "type/", "dest": "rules/"}]}},
            "ci": {"github": {"files": [{"src": "ci/", "dest": "rules/"}]}},
        }
    }
    first = resolve_variant_files(manifest, {"type": "api", "ci": "github"})
    second = resolve_variant_files(manifest, {"ci": "github", "type": "api"})
    assert [entry["src"] for entry in first[0]] == ["type/", "ci/"]
    assert [entry["src"] for entry in second[0]] == ["ci/", "type/"]
