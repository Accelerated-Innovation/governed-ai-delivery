"""One check, every commitment — increment 13A.

The gate shipped in #165 asks one question about one hand-configured
baseline. Three things are wrong with that at a protected boundary:

- **It checks whatever `BASELINE:` was set to**, which is a `CHANGE_ME`
  placeholder in the template and a single path afterwards. A repository
  with four commitments gates one of them.
- **It never checks drift.** Authority is about the approval; the working
  tree can say something else entirely and the gate passes.
- **Two providers, two hand-wired shell steps.** The acceptance criterion is
  that GitHub and Azure produce equivalent outcomes for the same cases, and
  equivalence between two copies of a shell snippet is a hope, not a fact.

So the checking moves into one command both providers call. Discovery is
`commitments/<key>/baseline.json`, the layout the baseline schema already
defines, which also means a code change whose contract files were untouched
is still checked against every commitment in the repository — the plan is
explicit that a PR author's declaration that a change is internal is not
evidence.
"""

from __future__ import annotations

import json
import subprocess

import pytest

from cli import contract_gate

FEATURE = """\
Feature: Response approval

  Background:
    Given a representative is signed in

  @rule:only-approved-may-send
  Rule: Only an approved response may be sent

    @scenario:unapproved-blocked
    Scenario: An unapproved response cannot be sent
      Given a drafted response
      When the representative sends it
      Then the send is refused
"""


def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)


@pytest.fixture
def project(tmp_path):
    """A repo that is its own single source, with one commitment package."""
    repo = tmp_path / "support-app"
    (repo / "features").mkdir(parents=True)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(repo, "config", "user.name", "test")
    (repo / "features" / "response-approval.feature").write_text(FEATURE, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "approved state")
    revision = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    _add_commitment(repo, "support-response-approval", revision)
    return repo


def _add_commitment(repo, key: str, revision: str) -> None:
    package = repo / "commitments" / key
    package.mkdir(parents=True, exist_ok=True)
    (package / "baseline.json").write_text(json.dumps({
        "version": 1,
        "commitment_key": key,
        "opportunity": {
            "opportunity_ref": f"OPP-{key}",
            "outcome": "Representatives cannot send unapproved responses",
        },
        "sources": [{
            "source_key": "support-app",
            "repository": "https://example.invalid/acme/support-app",
            "revision": revision,
            "path": "features",
            "kind": "repository",
        }],
        "selected_behavior": [{
            "ref": "support-app/response-approval#scenario:unapproved-blocked",
            "kind": "scenario",
            "id_source": "tag",
        }],
    }), encoding="utf-8")


def authorizing(baseline: dict) -> dict:
    """What the PDG answers for a commitment that currently authorizes work."""
    from cli.baseline import compute_digest

    source = baseline["sources"][0]
    return {
        "schema_version": 1,
        "commitment_id": baseline["commitment_key"],
        "authorizes_work": True,
        "baseline_digest": compute_digest(baseline),
        "opportunity_ref": baseline["opportunity"]["opportunity_ref"],
        "source_scope": source["source_key"],
        "source_revision": source["revision"],
    }


def fetcher(project, *, authorizes=True):
    """A PDG that answers about whatever baseline the gate found."""
    def fetch(commitment_id: str) -> dict:
        path = project / "commitments" / commitment_id / "baseline.json"
        status = authorizing(json.loads(path.read_text(encoding="utf-8")))
        status["authorizes_work"] = authorizes
        return status
    return fetch


# --- discovery ---------------------------------------------------------------


def test_every_commitment_in_the_repository_is_found(project):
    """Not one configured path. A repository with four commitments and a
    gate pointed at one of them is gating a quarter of its behavior."""
    _add_commitment(project, "second-commitment", "HEAD")

    found = contract_gate.discover(project)

    assert [p.parent.name for p in found] == ["second-commitment", "support-response-approval"]


def test_discovery_is_ordered_so_the_report_does_not_shuffle(project):
    """A gate whose output reorders between runs makes a diff of two runs
    useless, which is how a new failure hides among reordered lines."""
    for key in ("zulu", "alpha", "mike"):
        _add_commitment(project, key, "HEAD")

    found = [p.parent.name for p in contract_gate.discover(project)]

    assert found == sorted(found)


def test_a_repository_with_no_commitments_finds_none(tmp_path):
    assert contract_gate.discover(tmp_path) == []


# --- the two checks, together ------------------------------------------------


def test_an_untouched_tree_with_a_current_approval_passes(project):
    report = contract_gate.run(project, fetch=fetcher(project))

    assert report.ok
    assert len(report.packages) == 1
    assert report.packages[0].authorized is True


def test_drift_fails_even_when_the_approval_is_current(project):
    """The two questions are independent and both are necessary. An approval
    that is live says nothing about whether the working tree still says what
    was approved — which is the whole reason `validate-baseline` exists."""
    feature = project / "features" / "response-approval.feature"
    feature.write_text(
        feature.read_text(encoding="utf-8").replace(
            "Then the send is refused", "Then the send is allowed"
        ),
        encoding="utf-8",
    )

    report = contract_gate.run(project, fetch=fetcher(project))

    assert not report.ok
    assert report.packages[0].drift is not None
    assert not report.packages[0].drift.ok


def test_a_withdrawn_approval_fails_even_when_the_tree_is_untouched(project):
    report = contract_gate.run(project, fetch=fetcher(project, authorizes=False))

    assert not report.ok
    assert report.packages[0].authorized is False


def test_one_failing_package_does_not_hide_the_others(project):
    """Every package is reported, and the healthy one still reports healthy.
    Short-circuiting on the first failure turns one fix-and-rerun cycle into
    four, and reporting the whole run as bad tells you nothing about where.
    """
    _add_commitment(project, "aaa-unreachable-revision", "0" * 40)

    report = contract_gate.run(project, fetch=fetcher(project))

    assert [p.key for p in report.packages] == [
        "aaa-unreachable-revision", "support-response-approval",
    ]
    assert not report.packages[0].ok
    assert report.packages[1].ok
    assert not report.ok


def test_an_unreachable_pdg_is_not_a_rejection(project):
    """Undetermined stays undetermined all the way to the exit status. A
    gate that reports "not authorized" during an outage sends someone to
    re-approve a baseline when the fix is a network."""
    from cli.authority_check import PdgUnreachable

    def unreachable(commitment_id: str) -> dict:
        raise PdgUnreachable("connection refused")

    report = contract_gate.run(project, fetch=unreachable)

    assert not report.ok
    assert report.packages[0].authorized is None
    assert "unreachable" in report.packages[0].authority_detail.lower() or \
           "could not be reached" in report.packages[0].authority_detail.lower()


# --- what a protected boundary must refuse -----------------------------------


def test_a_project_claiming_a_pdg_with_no_commitments_is_refused(tmp_path):
    """"Nothing to check" passing is the failure the whole gate exists to
    prevent: a gate that is green because it was never configured is
    indistinguishable from one that is green because the behavior was
    approved."""
    report = contract_gate.run(tmp_path, fetch=lambda _id: {}, require_commitments=True)

    assert not report.ok
    assert any("no commitment" in p.lower() for p in report.problems)


def test_a_project_with_no_commitments_and_no_claim_is_not_failed(tmp_path):
    """Most projects using GovKit have no PDG and no commitments. They must
    not be told they failed something they never adopted."""
    report = contract_gate.run(tmp_path, fetch=lambda _id: {}, require_commitments=False)

    assert report.ok


def test_a_malformed_baseline_is_a_refusal_not_a_pass(project):
    """A package whose baseline cannot be read is the case where the check
    could not be performed. Skipping it would let a broken file buy a green
    gate."""
    (project / "commitments" / "support-response-approval" / "baseline.json").write_text(
        "{not json", encoding="utf-8"
    )

    report = contract_gate.run(project, fetch=fetcher(project))

    assert not report.ok
    assert report.packages[0].error is not None


def test_authority_is_not_claimed_when_the_baseline_could_not_be_read(project):
    """With no baseline there is no digest to compare, so any answer about
    authority would be about a commitment id and nothing else. Reporting it
    as authorized would be the forgery path increment 11 closed."""
    (project / "commitments" / "support-response-approval" / "baseline.json").write_text(
        "{not json", encoding="utf-8"
    )

    report = contract_gate.run(project, fetch=fetcher(project))

    assert report.packages[0].authorized is None


# --- exit status --------------------------------------------------------------


def test_enforced_failure_exits_non_zero(project):
    report = contract_gate.run(project, fetch=fetcher(project, authorizes=False))

    assert contract_gate.exit_status(report, enforced=True) == 1


def test_the_same_failure_advises_rather_than_blocks_when_not_enforced(project):
    """Start of work informs; merge blocks. One implementation, and the
    difference is the call site — not a setting a pull request can flip."""
    report = contract_gate.run(project, fetch=fetcher(project, authorizes=False))

    assert contract_gate.exit_status(report, enforced=False) == 0


def test_success_exits_zero_either_way(project):
    report = contract_gate.run(project, fetch=fetcher(project))

    assert contract_gate.exit_status(report, enforced=True) == 0
    assert contract_gate.exit_status(report, enforced=False) == 0
