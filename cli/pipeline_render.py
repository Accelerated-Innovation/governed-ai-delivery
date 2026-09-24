# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Deterministic reusable provider entry points, without event/credential selection."""

from __future__ import annotations

import base64
from copy import deepcopy
from dataclasses import dataclass

import yaml
from packaging.version import Version

from .gate_catalog import parse_catalog
from .pipeline_layout import DESTINATIONS
from .schema_validation import DocumentError, canonical_json, content_digest, validate_document

INPUTS = {
    "python": "Absolute path to an isolated Python containing the exact pinned GovKit release",
    "target": "Absolute path to the inspected checkout",
    "policy_target": "Absolute path to a separate caller-trusted policy and pack checkout",
    "request": "Absolute path to caller-accepted request JSON",
    "base": "Full trusted Git base commit SHA",
    "pack_arguments": "Optional absolute path to explicit check argument JSON",
    "observed_at": "Optional explicit observation time for deterministic replay",
}
OPTIONAL = {"pack_arguments", "observed_at", "change_output"}
SCRIPT = """case "$GOVKIT_PYTHON" in
  /*) ;;
  *) printf '%s\\n' 'GOVKIT_PYTHON must be an absolute path' >&2; exit 1 ;;
esac
exec -- "$GOVKIT_PYTHON" -I -m cli.pipeline_runtime
"""


class _LiteralDumper(yaml.SafeDumper):
    """Keep generated shell readable in the proposed provider YAML."""


def _string(dumper, value):
    return dumper.represent_scalar(
        "tag:yaml.org,2002:str", value, style="|" if "\n" in value else None
    )


_LiteralDumper.add_representer(str, _string)


@dataclass(frozen=True)
class PipelineSettings:
    govkit_version: str
    execute_checks: tuple[str, ...]
    admission: dict | None = None

    @property
    def document(self):
        return {
            "schema_version": 1,
            "govkit_version": self.govkit_version,
            "execute_checks": list(self.execute_checks),
            **({"admission": deepcopy(self.admission)} if self.admission is not None else {}),
        }


@dataclass(frozen=True)
class PipelineArtifact:
    _document: dict

    @property
    def document(self):
        return deepcopy(self._document)

    def to_json(self):
        return canonical_json(self._document)


def parse_settings(document):
    validate_document(document, "pipeline-settings")
    if Version(document["govkit_version"]) < Version("0.21.1"):
        raise DocumentError("Pipeline entry points require GovKit >= 0.21.1")
    return PipelineSettings(
        document["govkit_version"],
        tuple(sorted(document["execute_checks"])),
        deepcopy(document.get("admission")),
    )


def render_pipeline(catalog, settings):
    catalog = parse_catalog(catalog.document)
    settings = parse_settings(settings.document)
    record = catalog.document
    provider = record["provider"]
    if not catalog.ready or provider not in DESTINATIONS:
        raise DocumentError("Pipeline rendering needs a resolved catalog and explicit CI provider")
    if settings.govkit_version != record["pins"]["govkit"]:
        raise DocumentError("Runtime pin differs from the composed catalog version")
    binding = {
        "schema_version": 1,
        "govkit_version": settings.govkit_version,
        "profile_digest": record["profile_digest"],
        "packs_digest": content_digest(canonical_json(record["pins"]["packs"]).encode()),
        "execute_checks": list(settings.execute_checks),
    }
    inputs = dict(INPUTS)
    if settings.admission is not None:
        if settings.admission["provider"] != provider:
            raise DocumentError("Admission provider differs from the selected CI provider")
        binding["admission"] = settings.admission
        inputs.update(
            {
                "provider_event": "Absolute path to trusted provider event JSON",
                "policy_revision": "Full caller-pinned trusted policy checkout commit SHA",
                "request_digest": "SHA-256 of the caller-accepted request bytes",
                "change_output": "Optional new change-results artifact outside both checkouts",
            }
        )
    encoded = base64.b64encode(canonical_json(binding).encode()).decode("ascii")
    if len(encoded) > 65536:
        raise DocumentError("Pipeline binding is too large for the runtime input boundary")
    env = {"GOVKIT_BINDING": encoded}
    for name in inputs:
        context = "inputs" if provider == "github" else "parameters"
        env["GOVKIT_" + name.upper()] = "${{ " + context + "." + name + " }}"
    if provider == "github":
        metadata = {
            "name": "GovKit change conformance",
            "description": "One pinned common-engine invocation over explicit prepared inputs",
            "inputs": {
                name: {
                    "description": description,
                    "required": name not in OPTIONAL,
                    **({"default": ""} if name in OPTIONAL else {}),
                }
                for name, description in inputs.items()
            },
            "runs": {
                "using": "composite",
                "steps": [
                    {
                        "name": "GovKit change conformance",
                        "shell": "bash",
                        "run": SCRIPT,
                        "env": env,
                    }
                ],
            },
        }
    else:
        metadata = {
            "parameters": [
                {"name": name, "type": "string", **({"default": ""} if name in OPTIONAL else {})}
                for name in inputs
            ],
            "steps": [{"bash": SCRIPT, "displayName": "GovKit change conformance", "env": env}],
        }
    content = "# Generated by GovKit; configure a trusted caller before activation.\n"
    content += yaml.dump(metadata, Dumper=_LiteralDumper, sort_keys=False, width=1000000)
    document = {
        "schema_version": 1,
        "kind": "pipeline-render",
        "provider": provider,
        "catalog": record,
        "settings": settings.document,
        "binding": binding,
        "path": DESTINATIONS[provider],
        "content": content,
        "execution": "not-run",
        "enforcement": "unknown",
        "requirements": [
            "isolated-pinned-runtime",
            "separate-trusted-policy-and-packs",
            "accepted-request-and-full-base-sha",
            "caller-event-and-permission-policy",
            "external-required-check-and-reviewer-enforcement",
        ],
    }
    document["digest"] = content_digest(canonical_json(document).encode())
    validate_document(document, "pipeline-render")
    return PipelineArtifact(document)


def parse_render(document):
    validate_document(document, "pipeline-render")
    expected = render_pipeline(
        parse_catalog(document["catalog"]), parse_settings(document["settings"])
    )
    if canonical_json(document) != expected.to_json():
        raise DocumentError("Saved pipeline render differs from its replayed catalog/settings")
    return expected
