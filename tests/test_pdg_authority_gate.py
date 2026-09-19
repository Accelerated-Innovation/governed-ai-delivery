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
    the change land, and one that runs on every branch gates nothing in
    particular."""
    workflow = yaml.safe_load(GITHUB.read_text(encoding="utf-8"))

    triggers = workflow.get(True) or workflow.get("on")
    pull_request = next(v for k, v in triggers.items() if str(k).startswith("pull_request"))
    assert "main" in pull_request["branches"]


def test_the_gate_does_not_hard_code_an_endpoint():
    """A default endpoint in a shipped template is the one someone forgets to
    change, and it would receive their token."""
    for path in (GITHUB, AZURE):
        body = path.read_text(encoding="utf-8")
        assert "https://" not in body.replace("https://github.com", ""), path


# ---------------------------------------------------------------------------
# Who controls the definition that holds the credential
# ---------------------------------------------------------------------------


def _github_steps() -> list[dict]:
    workflow = yaml.safe_load(GITHUB.read_text(encoding="utf-8"))
    return workflow["jobs"]["pdg-authority"]["steps"]


def test_the_github_gate_definition_cannot_be_edited_by_the_branch_it_gates():
    """`pull_request` runs the workflow *from the pull request's own branch*,
    with repository secrets, for any contributor who can push a branch. The
    gate's flags then protect nothing: the attacker deletes them, or simply
    adds a step that posts `GOVKIT_PDG_TOKEN` somewhere.

    `pull_request_target` runs the definition from the base branch, which is
    the branch protection already guards. Every reason this gate sits at
    merge — that it is a real chokepoint — depends on the chokepoint not
    being editable by the thing passing through it.
    """
    workflow = yaml.safe_load(GITHUB.read_text(encoding="utf-8"))
    triggers = workflow.get(True) or workflow.get("on")

    assert "pull_request_target" in triggers
    assert "pull_request" not in triggers


def test_the_github_gate_checks_out_the_pull_request_without_its_credentials():
    """`pull_request_target` checks out the *base* by default, which would
    verify the wrong tree — the gate must read the baseline the pull request
    proposes. So the merge ref is explicit.

    And `persist-credentials: false`, because that event's token is
    write-scoped: leaving it in `.git/config` beside a checkout of untrusted
    code is the footgun `pull_request_target` is notorious for.
    """
    checkout = next(s for s in _github_steps() if "checkout" in str(s.get("uses", "")))

    assert "merge" in str(checkout["with"]["ref"])
    assert checkout["with"]["persist-credentials"] is False


@pytest.mark.parametrize("path", [GITHUB, AZURE])
def test_the_gate_executes_nothing_the_pull_request_could_have_written(path):
    """The safety of running with secrets over an untrusted tree rests
    entirely on this: the job reads those files and executes none of them.

    One pinned install from PyPI and one govkit invocation. No editable
    install, no requirements file, no build script, no task runner — each of
    which would hand the credential to code the pull request authored.
    """
    body = path.read_text(encoding="utf-8")
    scripts = "\n".join(
        line for line in body.splitlines() if not line.lstrip().startswith("#")
    )

    for tree_sourced in ("pip install -e", "pip install -r", "setup.py", "./", "make ", "npm ", "tox"):
        assert tree_sourced not in scripts, tree_sourced


def test_the_azure_gate_records_the_exposure_it_cannot_close():
    """Azure DevOps builds pull-request validation from the YAML **in the
    source branch**, and has no `pull_request_target` equivalent. So the same
    hazard the GitHub gate closes stays open there, and the only controls are
    organizational.

    Recording it in the template is not a fix and is not offered as one. It
    is the alternative to shipping a gate whose adopters believe their token
    is protected the way the GitHub one is.
    """
    body = AZURE.read_text(encoding="utf-8")

    assert "source branch" in body.lower()
    assert "read-only" in body.lower()


@pytest.mark.parametrize("path", [GITHUB, AZURE])
def test_both_templates_say_what_happens_to_a_fork_pull_request(path):
    """An enforced gate with no credential fails closed, which is right for an
    outage and wrong for a fork: it makes every external contribution
    unmergeable, and the maintainer cannot tell the two apart from the log."""
    assert "fork" in path.read_text(encoding="utf-8").lower()


# ---------------------------------------------------------------------------
# One command, both providers — increment 13A
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", [GITHUB, AZURE])
def test_the_gate_checks_every_commitment_not_one_configured_path(path):
    """`verify-authority` answers about one baseline a variable points at.
    A repository with four commitments gated one of them, and local drift
    was never checked at all — authority is about the approval, and the
    working tree can say something else entirely.
    """
    body = path.read_text(encoding="utf-8")

    assert "govkit verify-contract" in body


@pytest.mark.parametrize("path", [GITHUB, AZURE])
def test_no_placeholder_survives_in_a_shipped_gate(path):
    """`CHANGE_ME` in a required check is a gate that fails for everyone who
    installs it or, worse, points at whatever path somebody typed once.
    Discovery replaces it: `commitments/<key>/baseline.json` is the layout
    the baseline schema already defines."""
    body = path.read_text(encoding="utf-8")

    assert "CHANGE_ME" not in body


@pytest.mark.parametrize("path", [GITHUB, AZURE])
def test_the_gate_tells_the_checker_what_it_is_merging_into(path):
    """Without a base ref a pull request removes a commitment from
    enforcement by deleting its file. The provider knows the target branch;
    passing it is what lets the check notice the deletion."""
    body = path.read_text(encoding="utf-8")

    assert "--base-ref" in body


def test_both_providers_pass_the_same_flags():
    """The acceptance criterion is equivalent outcomes for the same cases.
    Two hand-wired shells cannot be compared; two invocations of one command
    can, so the flags are compared directly."""
    import re

    def flags(path):
        body = path.read_text(encoding="utf-8")
        start = body.index("govkit verify-contract")
        return set(re.findall(r"--[a-z-]+", body[start:start + 400]))

    assert flags(GITHUB) == flags(AZURE)


@pytest.mark.parametrize("path", [GITHUB, AZURE])
def test_the_gate_documents_the_pointer_it_requires(path):
    """The gate reads `commitments/<key>/commitment.json` for the id the
    decision service assigned. A template that documents only
    `baseline.json` sends adopters to build a package the gate will report
    as unauthorized — and the failure looks like a withdrawn approval
    rather than a missing file."""
    body = path.read_text(encoding="utf-8")

    assert "commitment.json" in body


def test_the_ci_readme_documents_the_package_layout():
    readme = pathlib.Path("ci/README.md").read_text(encoding="utf-8")

    assert "commitment.json" in readme
    assert "baseline.json" in readme
