"""The marker keeps `authority` across rewrites — PR #164 review.

Two defects, one consequence. The published marker schema sets
`additionalProperties: false` and declared no `authority`, so every
PDG-enabled project failed validation against the repository's own contract.
And `write_govkit_marker()` rebuilds the file from known fields, so `apply`,
`upgrade`, `stack apply` or `calibrate` dropped the key — after which the
reader defaults to `none` and even `--enforce` exits zero.

An upgrade silently disabling a security gate is the worst version of this,
because nothing about running an upgrade suggests you have turned something
off.
"""

from __future__ import annotations

import json

import jsonschema
import pytest

from cli.marker import read_govkit_marker, write_govkit_marker

SCHEMA = json.loads(
    __import__("pathlib").Path("governance/schemas/govkit-marker.schema.json")
    .read_text(encoding="utf-8")
)

AUTHORITY = {"source": "pdg"}


def test_the_published_schema_permits_an_authority_block():
    marker = {
        "version": "0.20.0", "level": "4", "agent": "claude-code",
        "options": {"type": "api", "ci": "github", "stack": "python-fastapi"},
        "applied_at": "2026-09-19T00:00:00+00:00",
        "authority": AUTHORITY,
    }

    jsonschema.validate(marker, SCHEMA)


def test_the_schema_still_refuses_an_unknown_top_level_key():
    """The positive control: widening for `authority` must not widen for
    everything."""
    marker = {
        "version": "0.20.0", "level": "4", "agent": "claude-code",
        "options": {"type": "api", "ci": "github", "stack": "python-fastapi"},
        "applied_at": "2026-09-19T00:00:00+00:00",
        "whatever": True,
    }

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(marker, SCHEMA)


def test_the_schema_refuses_an_unknown_authority_source():
    marker = {
        "version": "0.20.0", "level": "4", "agent": "claude-code",
        "options": {"type": "api", "ci": "github", "stack": "python-fastapi"},
        "applied_at": "2026-09-19T00:00:00+00:00",
        "authority": {"source": "whatever"},
    }

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(marker, SCHEMA)


def test_rewriting_the_marker_preserves_authority(tmp_path):
    """`apply`, `upgrade`, `stack apply` and `calibrate` all go through this.
    Dropping the key turns an enforced gate off without anyone deciding to."""
    write_govkit_marker(tmp_path, "claude-code", "4",
                        {"type": "api", "ci": "github", "stack": "python-fastapi"})
    path = tmp_path / ".govkit" / "marker.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["authority"] = AUTHORITY
    path.write_text(json.dumps(data), encoding="utf-8")

    write_govkit_marker(tmp_path, "claude-code", "5",
                        {"type": "api", "ci": "github", "stack": "python-fastapi"})

    rewritten = json.loads(path.read_text(encoding="utf-8"))
    assert rewritten["authority"] == AUTHORITY
    assert rewritten["level"] == "5", "the rewrite must still do its job"


def test_a_marker_without_authority_gains_nothing(tmp_path):
    """The default stays absent. Writing `source: none` into every marker
    would make an opt-in look like a setting someone chose."""
    write_govkit_marker(tmp_path, "claude-code", "4",
                        {"type": "api", "ci": "github", "stack": "python-fastapi"})

    data = json.loads((tmp_path / ".govkit" / "marker.json").read_text(encoding="utf-8"))
    assert "authority" not in data
    assert read_govkit_marker(tmp_path) is not None
