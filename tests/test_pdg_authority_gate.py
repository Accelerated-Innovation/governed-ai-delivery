"""The protected boundary, as a shipped CI gate — increment 11 follow-up.

Where the boundary sits was a decision, not a default. Four placements were
weighed and two survived, answering different questions:

- **Start of work → advisory.** Cheapest and earliest, and *not enforceable*:
  there is no chokepoint at the moment someone starts typing, and a PDG
  outage there would stop all new work rather than one merge.
- **Merge → enforced.** A real chokepoint via branch protection. An outage
  pauses merges while work continues, and it is the only check that sees an
  invalidation which happened *after* the work began — the cached-approval
  problem in time rather than storage.

This file covers the enforced half, because that is the half that has to be
right. The gate ships for GitHub and Azure together, per the repository's
parity rule.
"""

from __future__ import annotations

import pathlib

import pytest
import yaml

GITHUB = pathlib.Path("ci/github/pdg-authority-gate.yml")
AZURE = pathlib.Path("ci/azure/pdg-authority-gate.yml")


def test_the_gate_ships_for_both_providers():
    """`ci/github/` and `ci/azure/` move together — a gate that exists for one
    provider is a gate half the adopters do not have."""
    assert GITHUB.is_file()
    assert AZURE.is_file()


def test_the_gate_is_listed_in_the_ci_readme():
    """The README table is how an adopter discovers a gate exists at all."""
    readme = pathlib.Path("ci/README.md").read_text(encoding="utf-8")

    assert "pdg-authority-gate" in readme


@pytest.mark.parametrize("path", [GITHUB, AZURE])
def test_the_gate_enforces_and_requires_authority(path):
    """Both flags, and the reasoning is different for each.

    `--enforce` fails closed on rejection *and* on inability to determine: a
    gate that passes when the PDG is unreachable is not a gate.

    `--require-authority` stops the gate reading its own applicability out of
    the tree it is gating. Without it, a pull request removing
    `authority.source` from the marker turns the check into "not applicable"
    and exits zero.
    """
    body = path.read_text(encoding="utf-8")

    assert "--enforce" in body
    assert "--require-authority" in body


@pytest.mark.parametrize("path", [GITHUB, AZURE])
def test_the_endpoint_and_token_come_from_secrets_not_the_repository(path):
    """An endpoint read from the working tree, paired with a credential from
    the environment, is how a pull request collects the token. Both travel
    together, from the provider's secret store."""
    body = path.read_text(encoding="utf-8")

    assert "GOVKIT_PDG_URL" in body
    assert "GOVKIT_PDG_TOKEN" in body
    for provider_secret in ("secrets.", "$("):
        if provider_secret in body:
            break
    else:  # pragma: no cover - one of the two forms is always present
        pytest.fail("the gate does not read its credential from a secret store")


def test_the_github_gate_runs_on_pull_requests_to_the_protected_branch():
    """Merge is the boundary. A gate that only runs on push has already let
    the change land."""
    workflow = yaml.safe_load(GITHUB.read_text(encoding="utf-8"))

    triggers = workflow.get(True) or workflow.get("on")
    assert "pull_request" in triggers


def test_the_gate_does_not_hard_code_an_endpoint():
    """A default endpoint in a shipped template is the one someone forgets to
    change, and it would receive their token."""
    for path in (GITHUB, AZURE):
        body = path.read_text(encoding="utf-8")
        assert "https://" not in body.replace("https://github.com", ""), path
