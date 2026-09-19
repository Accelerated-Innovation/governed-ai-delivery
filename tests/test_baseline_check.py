"""Checking a working tree against an approved baseline — increment 10.

The classifier is a pure function over two closures. This is what supplies
them: the *approved* side comes from the immutable revision the baseline pins,
the *current* side from the working tree. That is what `sources[].revision`
is for — a digest alone could say "different" but never which clause moved.

The repositories here are real: two commits, `git show` at the pinned
revision. A fake would prove the plumbing against itself.
"""

from __future__ import annotations

import json
import subprocess

import pytest

from cli import baseline_check

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
    subprocess.run(["git", "-C", str(repo), *args], check=True,
                   capture_output=True, text=True)


@pytest.fixture
def source(tmp_path):
    """A repo with the feature committed, plus author identity so CI can commit."""
    repo = tmp_path / "support-app"
    (repo / "features").mkdir(parents=True)
    _git_init(repo)
    (repo / "features" / "response-approval.feature").write_text(FEATURE, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "approved state")
    revision = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                              check=True, capture_output=True, text=True).stdout.strip()
    return repo, revision


def _git_init(repo):
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(repo, "config", "user.name", "test")


def baseline_for(revision: str, **overrides) -> dict:
    baseline = {
        "version": 1,
        "commitment_key": "support-response-approval",
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
    }
    baseline.update(overrides)
    return baseline


def edit(repo, old: str, new: str) -> None:
    path = repo / "features" / "response-approval.feature"
    path.write_text(path.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")


# --- the working tree still says what was approved ---------------------------

def test_an_untouched_working_tree_reports_no_differences(source):
    repo, revision = source

    report = baseline_check.check(baseline_for(revision), {"support-app": repo})

    assert report.differences == []
    assert report.refusals == []
    assert report.ok is True


def test_a_changed_then_is_reported_with_its_clause_and_reference(source):
    repo, revision = source
    edit(repo, "Then the send is refused", "Then the send is queued")

    report = baseline_check.check(baseline_for(revision), {"support-app": repo})

    assert report.ok is False
    assert [(d.ref, d.role) for d in report.differences] == [
        ("support-app/response-approval#scenario:unapproved-blocked", "then")
    ]


def test_a_formatting_only_edit_is_accepted(source):
    """Reindenting, a comment, trailing whitespace. The approval holds."""
    repo, revision = source
    edit(repo, "      Then the send is refused", "          Then the send is refused   ")
    edit(repo, "  Background:", "  # the shared precondition\n  Background:")

    report = baseline_check.check(baseline_for(revision), {"support-app": repo})

    assert report.differences == [], [d.detail for d in report.differences]
    assert report.ok is True


def test_a_semantic_change_names_what_it_voids(source):
    repo, revision = source
    edit(repo, "Given a representative is signed in", "Given an administrator is signed in")

    report = baseline_check.check(baseline_for(revision), {"support-app": repo})

    assert "development_token" in report.voided
    assert "consequence_class" in report.voided, "an actor change needs the upstream question"


# --- approved behavior cannot disappear quietly -------------------------------

def test_deleting_the_tag_does_not_remove_the_approved_behavior(source):
    """The acceptance criterion in as many words: approved behavior cannot
    disappear by deleting a tag or a link. Losing the authored identity makes
    the reference unresolvable, which is a refusal — not a silent pass."""
    repo, revision = source
    edit(repo, "    @scenario:unapproved-blocked\n", "")

    report = baseline_check.check(baseline_for(revision), {"support-app": repo})

    assert report.ok is False
    assert any("unresolvable" in r.lower() for r in report.refusals), report.refusals


def test_deleting_the_whole_scenario_is_a_refusal_not_a_clean_report(source):
    repo, revision = source
    path = repo / "features" / "response-approval.feature"
    path.write_text(FEATURE.split("    @scenario:")[0], encoding="utf-8")

    report = baseline_check.check(baseline_for(revision), {"support-app": revision and repo})

    assert report.ok is False
    assert report.refusals


def test_a_scenario_gutted_to_nothing_is_reported_structurally(source):
    """A lowercase keyword empties a scenario while the file still parses.
    The digest of an empty thing is stable, so this must not read as a change
    that someone can simply re-approve."""
    repo, revision = source
    edit(repo, "      Given a drafted response", "      given a drafted response")
    edit(repo, "      When the representative sends it", "      when the representative sends it")
    edit(repo, "      Then the send is refused", "      then the send is refused")

    report = baseline_check.check(baseline_for(revision), {"support-app": repo})

    assert report.ok is False
    assert any("no steps" in r for r in report.refusals), report.refusals


# --- refusals -----------------------------------------------------------------

def test_a_reference_naming_an_undeclared_source_is_refused(source):
    repo, revision = source
    baseline = baseline_for(revision)
    baseline["selected_behavior"][0]["ref"] = "other-app/response-approval#scenario:x"

    report = baseline_check.check(baseline, {"support-app": repo})

    assert any("source" in r.lower() for r in report.refusals), report.refusals


def test_a_feature_key_escaping_its_source_is_refused(source):
    """Path traversal. The feature key resolves under the source's own path
    and must not reach outside it."""
    repo, revision = source
    baseline = baseline_for(revision)
    baseline["selected_behavior"][0]["ref"] = "support-app/../../etc/passwd#scenario:x"

    report = baseline_check.check(baseline, {"support-app": repo})

    assert any("outside" in r.lower() or "traversal" in r.lower() for r in report.refusals)


def test_an_unsupported_baseline_version_is_refused(source):
    repo, revision = source

    report = baseline_check.check(baseline_for(revision, version=99), {"support-app": repo})

    assert report.ok is False
    assert any("version" in r.lower() for r in report.refusals), report.refusals


def test_a_revision_that_is_not_in_the_checkout_is_refused_not_assumed(source):
    """The approved side has to come from somewhere. If the pinned revision
    is unreachable the check cannot be performed, and saying so is the only
    honest answer — reporting 'no differences' would be a lie."""
    repo, _revision = source
    absent = "0" * 40

    report = baseline_check.check(baseline_for(absent), {"support-app": repo})

    assert report.ok is False
    assert any("revision" in r.lower() for r in report.refusals), report.refusals


def test_a_source_with_no_local_checkout_is_refused(source):
    repo, revision = source

    report = baseline_check.check(baseline_for(revision), {})

    assert report.ok is False
    assert any("checkout" in r.lower() for r in report.refusals), report.refusals


# --- the validator never writes ------------------------------------------------

def test_the_check_leaves_the_working_tree_exactly_as_it_found_it(source):
    """Read-only, and the brief says so: it must not rewrite specs to make
    them pass, add missing ids, or upgrade a manifest. A validator that can
    edit what it validates is a formatter."""
    repo, revision = source
    edit(repo, "Then the send is refused", "Then the send is queued")
    before = json.dumps(sorted(
        (str(p.relative_to(repo)), p.read_text(encoding="utf-8"))
        for p in repo.rglob("*.feature")
    ))

    baseline_check.check(baseline_for(revision), {"support-app": repo})

    after = json.dumps(sorted(
        (str(p.relative_to(repo)), p.read_text(encoding="utf-8"))
        for p in repo.rglob("*.feature")
    ))
    assert before == after


# --- review of PR #163 -------------------------------------------------------

def test_a_tampered_recorded_digest_is_caught(source):
    """`content_digest` exists to be tamper evidence — the module docstring
    says so — and nothing compared it. A baseline whose recorded digest was
    altered reported clean whenever the revision and the working tree agreed,
    which is precisely the "manifest edited to hide an altered scenario" the
    brief names."""
    repo, revision = source
    baseline = baseline_for(revision)
    baseline["selected_behavior"][0]["content_digest"] = "sha256:" + "0" * 64

    report = baseline_check.check(baseline, {"support-app": repo})

    assert report.ok is False
    assert any("digest" in r.lower() for r in report.refusals), report.refusals


def test_a_matching_recorded_digest_is_accepted(source):
    """The positive control. A comparison that rejected everything would pass
    the test above and block every honest baseline."""
    repo, revision = source
    baseline = baseline_for(revision)
    approved = baseline_check.approved_digest(baseline, baseline["selected_behavior"][0],
                                              {"support-app": repo})
    baseline["selected_behavior"][0]["content_digest"] = approved

    report = baseline_check.check(baseline, {"support-app": repo})

    assert report.ok is True, report.refusals


def test_a_baseline_that_fails_its_own_schema_is_refused(source):
    """increment 01 built `validate_baseline` and this never called it, so a
    document with no sources and no selection exited zero — reporting success
    for a baseline with no approved scope at all."""
    repo, revision = source
    empty = {"version": 1, "commitment_key": "k", "sources": [], "selected_behavior": []}

    report = baseline_check.check(empty, {"support-app": repo})

    assert report.ok is False
    assert report.refusals


def test_a_symlinked_feature_file_cannot_escape_the_source(source, tmp_path):
    """Containment was checked on the directory and not on the file chosen
    inside it, so a `.feature` symlink could make the current closure come
    from outside the source while the approved side loaded from the same
    lexical path in git."""
    repo, revision = source
    outside = tmp_path / "elsewhere.feature"
    outside.write_text(FEATURE.replace("Then the send is refused", "Then anything at all"),
                       encoding="utf-8")
    directory = repo / "features" / "sneaky"
    directory.mkdir()
    (directory / "a.feature").symlink_to(outside)

    baseline = baseline_for(revision)
    baseline["selected_behavior"][0]["ref"] = "support-app/sneaky#scenario:unapproved-blocked"

    report = baseline_check.check(baseline, {"support-app": repo})

    assert report.ok is False
    assert any("outside" in r.lower() for r in report.refusals), report.refusals


def test_a_package_source_is_refused_with_its_own_reason(source):
    """`git show` cannot read a released package, and saying "revision not
    reachable" sends the reader to look for a commit that was never supposed
    to exist."""
    repo, revision = source
    baseline = baseline_for(revision)
    baseline["sources"][0].update({"kind": "package", "revision": "1.2.3"})

    report = baseline_check.check(baseline, {"support-app": repo})

    assert report.ok is False
    assert any("package" in r.lower() for r in report.refusals), report.refusals


def test_a_changed_constraint_is_reported(source):
    """`constraints` carry the approved NFR, evaluation, design and
    agent-authority obligations. Iterating only `selected_behavior` meant a
    changed constraint reported clean — approved scope disappearing quietly,
    which is the thing this checker exists to prevent."""
    repo, revision = source
    path = repo / "features" / "response-approval.feature"
    path.write_text(path.read_text(encoding="utf-8") + """
  @nfr:response-under-two-seconds
  Rule: A response is produced within two seconds
    Example: it is fast
      Given a drafted response
      Then it is produced within two seconds
""", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "with the constraint")
    revision = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                              check=True, capture_output=True, text=True).stdout.strip()

    baseline = baseline_for(revision)
    baseline["constraints"] = [{
        "ref": "support-app/response-approval#nfr:response-under-two-seconds",
        "kind": "nfr",
        "id_source": "tag",
    }]
    edit(repo, "within two seconds", "within ten seconds")

    report = baseline_check.check(baseline, {"support-app": repo})

    assert report.ok is False
    assert any("nfr:response-under-two-seconds" in d.ref for d in report.differences), \
        (report.differences, report.refusals)


def test_reordering_steps_across_roles_is_a_change(source):
    """`classify` groups steps by role, so a When moving before a Given left
    every group equal. Gherkin executes in written order, so an
    implementation can behave differently — the materiality test's own tell."""
    repo, revision = source
    edit(
        repo,
        "      Given a drafted response\n      When the representative sends it\n",
        "      When the representative sends it\n      Given a drafted response\n",
    )

    report = baseline_check.check(baseline_for(revision), {"support-app": repo})

    assert report.ok is False, "a reordered step sequence reported clean"


def test_a_missing_parser_refuses_rather_than_crashing(source, monkeypatch):
    """The module promises a refusal rather than a shallow parse. It raised
    ParserUnavailable through an uncaught path instead, so a standard install
    got a traceback where the contract said controlled non-zero."""
    repo, revision = source

    def unavailable(_text):
        raise baseline_check.spec_closure.ParserUnavailable("gherkin-official is not installed")

    monkeypatch.setattr(baseline_check.spec_closure, "parse_feature", unavailable)

    report = baseline_check.check(baseline_for(revision), {"support-app": repo})

    assert report.ok is False
    assert any("gherkin" in r.lower() for r in report.refusals), report.refusals
