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
    # The id the decision service assigned. Real engines mint their own
    # (`cmt-<uuid>`), which is why the key cannot stand in for it.
    (package / "commitment.json").write_text(
        json.dumps({"commitment_id": f"cmt-{key}"}), encoding="utf-8"
    )


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
        key = commitment_id.removeprefix("cmt-")
        path = project / "commitments" / key / "baseline.json"
        status = authorizing(json.loads(path.read_text(encoding="utf-8")))
        status["commitment_id"] = commitment_id
        status["authorizes_work"] = authorizes
        return status
    return fetch


def remembering_fetcher(project, *, authorizes):
    """A PDG that still answers about a commitment the tree no longer has.

    Which is the whole point of the removal check: the graph outlives the
    file, so the answer cannot be read out of the working tree. Snapshotted
    up front, because the file is about to be deleted.
    """
    remembered = {
        f"cmt-{package.name}": authorizing(
            json.loads((package / "baseline.json").read_text(encoding="utf-8"))
        )
        for package in (project / "commitments").iterdir()
        if (package / "baseline.json").is_file()
    }

    def fetch(commitment_id: str) -> dict:
        status = dict(remembered[commitment_id])
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


# --- a contract that spans repositories --------------------------------------


def _two_source_commitment(repo, key, revision):
    package = repo / "commitments" / key
    package.mkdir(parents=True, exist_ok=True)
    (package / "baseline.json").write_text(json.dumps({
        "version": 1,
        "commitment_key": key,
        "opportunity": {"opportunity_ref": f"OPP-{key}", "outcome": "x"},
        "sources": [
            {"source_key": "support-app", "repository": "https://example.invalid/a",
             "revision": revision, "path": "features", "kind": "repository"},
            {"source_key": "billing-app", "repository": "https://example.invalid/b",
             "revision": revision, "path": "features", "kind": "repository"},
        ],
        "selected_behavior": [{
            "ref": "support-app/response-approval#scenario:unapproved-blocked",
            "kind": "scenario", "id_source": "tag",
        }],
    }), encoding="utf-8")
    (package / "commitment.json").write_text(
        json.dumps({"commitment_id": f"cmt-{key}"}), encoding="utf-8"
    )


def test_a_contract_spanning_repositories_is_checkable_when_checkouts_are_given(project):
    """`--target` stands in for a single source and only a single source. A
    schema-valid multi-source baseline with no way to supply the other
    checkouts could never pass an enforced gate — the gate would be
    rejecting valid contracts for want of an argument."""
    revision = subprocess.run(
        ["git", "-C", str(project), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    _two_source_commitment(project, "cross-repo", revision)

    report = contract_gate.run(
        project,
        fetch=fetcher(project),
        roots={"support-app": project, "billing-app": project},
    )

    cross = next(p for p in report.packages if p.key == "cross-repo")
    assert cross.drift is not None
    assert cross.drift.ok


def test_a_missing_checkout_is_refused_rather_than_skipped(project):
    """The honest answer is "I could not look", never "no differences"."""
    revision = subprocess.run(
        ["git", "-C", str(project), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    _two_source_commitment(project, "cross-repo", revision)

    report = contract_gate.run(project, fetch=fetcher(project))

    cross = next(p for p in report.packages if p.key == "cross-repo")
    assert not cross.drift.ok
    assert cross.drift.refusals


def test_a_single_source_baseline_still_needs_no_argument(project):
    """The common case stays a two-argument command."""
    report = contract_gate.run(project, fetch=fetcher(project))

    assert report.ok


# --- a commitment cannot be removed from enforcement by deleting a file ------


def test_deleting_a_commitment_that_still_authorizes_is_refused(project):
    """`discover` reads the tree the pull request proposes, so a pull request
    that deletes `commitments/foo/` removes foo from the gate entirely — and
    while any other package remains, `require_commitments` is satisfied and
    the gate goes green. Enforcement you can switch off by deleting a file is
    not enforcement.
    """
    _git(project, "add", "-A")
    _git(project, "commit", "-m", "commitment on the base branch")
    base = subprocess.run(
        ["git", "-C", str(project), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    fetch = remembering_fetcher(project, authorizes=True)
    (project / "commitments" / "support-response-approval" / "baseline.json").unlink()

    report = contract_gate.run(project, fetch=fetch, base_ref=base)

    assert not report.ok
    assert any("support-response-approval" in p for p in report.problems)


def test_a_commitment_the_pdg_no_longer_authorizes_may_be_removed(project):
    """Retirement has a designed path: invalidate it in the graph, then the
    file can go. Refusing that too would make the repository a place
    commitments accumulate forever."""
    _git(project, "add", "-A")
    _git(project, "commit", "-m", "commitment on the base branch")
    base = subprocess.run(
        ["git", "-C", str(project), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    fetch = remembering_fetcher(project, authorizes=False)
    (project / "commitments" / "support-response-approval" / "baseline.json").unlink()

    report = contract_gate.run(project, fetch=fetch, base_ref=base)

    assert report.ok


def test_a_removal_the_pdg_cannot_be_asked_about_is_refused(project):
    """Fail closed. An outage during a deletion is the one moment where
    guessing costs the most."""
    from cli.authority_check import PdgUnreachable

    _git(project, "add", "-A")
    _git(project, "commit", "-m", "commitment on the base branch")
    base = subprocess.run(
        ["git", "-C", str(project), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    (project / "commitments" / "support-response-approval" / "baseline.json").unlink()

    def unreachable(commitment_id):
        raise PdgUnreachable("connection refused")

    report = contract_gate.run(project, fetch=unreachable, base_ref=base)

    assert not report.ok


def test_without_a_base_reference_nothing_is_claimed_about_removals(project):
    """Run locally there is no base to compare against, and inventing one
    would make the advisory check disagree with the gate."""
    report = contract_gate.run(project, fetch=fetcher(project))

    assert report.ok


# --- one bad package must not take the run down ------------------------------


def test_a_structurally_invalid_baseline_is_contained(project):
    """`_load` accepts any JSON object, and the drift checker assumes shapes
    below that. An entry that is a string rather than an object raised out of
    the whole run, so one malformed file meant every later package went
    unchecked and unreported."""
    _add_commitment(project, "aaa-broken", "HEAD")
    path = project / "commitments" / "aaa-broken" / "baseline.json"
    broken = json.loads(path.read_text(encoding="utf-8"))
    broken["selected_behavior"] = ["not-an-object"]
    path.write_text(json.dumps(broken), encoding="utf-8")

    report = contract_gate.run(project, fetch=fetcher(project))

    assert [p.key for p in report.packages] == ["aaa-broken", "support-response-approval"]
    assert not report.packages[0].ok
    assert report.packages[1].drift is not None, "the healthy package was still checked"
    assert not report.ok


# --- a missing commitment is an answer ---------------------------------------


def test_a_commitment_the_pdg_has_never_heard_of_is_not_authorized(project):
    """404 is an answer: the PDG looked and found nothing. Reporting it as
    an outage turns a definite absence into a maybe, and increment 11 made
    that distinction the substance of the feature."""
    def absent(commitment_id: str) -> dict:
        raise contract_gate.NoSuchCommitment(commitment_id)

    report = contract_gate.run(project, fetch=absent)

    assert report.packages[0].authorized is False
    assert "no commitment" in report.packages[0].authority_detail.lower()


def test_a_base_reference_that_cannot_be_read_is_refused_not_ignored(project):
    """The removal check is the one that stops a deletion switching off
    enforcement, so its own failure mode matters. Returning "nothing was
    removed" for a ref the clone does not have would disable the check
    silently — a shallow clone, a renamed branch, a typo in the pipeline,
    and the protection is gone with a green tick.
    """
    report = contract_gate.run(project, fetch=fetcher(project), base_ref="no-such-ref")

    assert not report.ok
    assert any("no-such-ref" in p for p in report.problems)


# --- the pointer that names the decision -------------------------------------
#
# Found by running the gate against a live discovery-engine (2026-09-19).
# `contract_gate` looked the commitment up by `baseline.commitment_key`, and
# the engine assigns its own id (`cmt-<uuid>`) at approval. Every real
# commitment therefore 404s, which — correctly, per increment 11 — reports as
# NOT AUTHORIZED. The gate would have failed every approved change.
#
# The key cannot simply be renamed to the engine's id either: `commitment_key`
# is inside the digested document, so changing it changes the digest and the
# binding check fails instead. Increment 11 already said what the answer is —
# "the baseline names no decision ... a local pointer names the commitment and
# the PDG adjudicates it" — and the pointer is what was never built.


def _write_pointer(project, key, commitment_id):
    (project / "commitments" / key / "commitment.json").write_text(
        json.dumps({"commitment_id": commitment_id}), encoding="utf-8"
    )


def test_the_pointer_names_the_commitment_the_pdg_adjudicates(project):
    """The id the decision service assigned, recorded beside the baseline and
    deliberately outside it: anything inside changes the digest, and the
    digest is what the approval binds."""
    _write_pointer(project, "support-response-approval", "cmt-1234")
    seen = {}

    def fetch(commitment_id):
        seen["id"] = commitment_id
        status = authorizing(json.loads(
            (project / "commitments" / "support-response-approval" / "baseline.json")
            .read_text(encoding="utf-8")
        ))
        status["commitment_id"] = commitment_id
        return status

    contract_gate.run(project, fetch=fetch)

    assert seen["id"] == "cmt-1234"


def test_the_pointer_is_not_part_of_the_digest(project):
    """Adding it must not invalidate an approval that already exists. If the
    pointer changed the digest, recording the id the PDG returned would break
    the binding to the baseline that id was issued for."""
    from cli.baseline import compute_digest

    path = project / "commitments" / "support-response-approval" / "baseline.json"
    before = compute_digest(json.loads(path.read_text(encoding="utf-8")))

    _write_pointer(project, "support-response-approval", "cmt-1234")

    after = compute_digest(json.loads(path.read_text(encoding="utf-8")))
    assert before == after


def test_a_package_with_no_pointer_authorizes_nothing(project):
    """No pointer means no recorded decision. `verify` already says exactly
    that, and it is a definite answer rather than an error: a baseline is a
    well-formed proposal until something authorizes it."""
    (project / "commitments" / "support-response-approval" / "commitment.json").unlink()

    report = contract_gate.run(project, fetch=fetcher(project))

    assert report.packages[0].authorized is False
    assert "no commitment" in report.packages[0].authority_detail.lower()


def test_a_malformed_pointer_is_refused_rather_than_read_as_absent(project):
    """"Unreadable" and "absent" lead somewhere different: absent is a
    proposal nobody approved, unreadable is a package whose state cannot be
    established. Treating the second as the first reports a definite verdict
    the gate has not earned."""
    (project / "commitments" / "support-response-approval" / "commitment.json").write_text(
        "{not json", encoding="utf-8"
    )

    report = contract_gate.run(project, fetch=fetcher(project))

    assert report.packages[0].error is not None
    assert report.packages[0].authorized is None


def test_a_pointer_with_no_commitment_id_is_refused(project):
    (project / "commitments" / "support-response-approval" / "commitment.json").write_text(
        json.dumps({"note": "todo"}), encoding="utf-8"
    )

    report = contract_gate.run(project, fetch=fetcher(project))

    assert report.packages[0].error is not None


def test_a_removal_is_judged_by_the_pointer_too(project):
    """The removal check asks the PDG about a commitment that is gone, so it
    needs the same id the gate would have used — read from the base
    revision, because the working tree no longer has the package at all."""
    _write_pointer(project, "support-response-approval", "cmt-removed")
    _git(project, "add", "-A")
    _git(project, "commit", "-m", "commitment on the base branch")
    base = subprocess.run(
        ["git", "-C", str(project), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    asked = []

    def fetch(commitment_id):
        asked.append(commitment_id)
        return {"schema_version": 1, "commitment_id": commitment_id,
                "authorizes_work": True}

    import shutil
    shutil.rmtree(project / "commitments" / "support-response-approval")

    report = contract_gate.run(project, fetch=fetch, base_ref=base)

    assert asked == ["cmt-removed"], "the removal check must use the recorded id"
    assert not report.ok
