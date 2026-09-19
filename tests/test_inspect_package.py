"""Converting an existing feature package into a baseline draft — 15.

The plan asks for "an explicit conversion/inspection path for existing
packages: preserve IDs where authored; flag derived identities; retain
history and require a real decision for the new baseline", and, in the
same breath, "never convert an old 'Committed' label into a new approval
automatically".

There is no 'Committed' label in govkit to convert, so the requirement
lands as something stronger and simpler: **the conversion path must be
incapable of producing an approval.** A draft it emits is a proposal that
does not validate until a person supplies the parts only a person can.

The interesting constraint is one increment 01 already set: a baseline
*rejects* `id_source: derived`, because a slug taken from an element's
name changes when the name does and cannot bind an approval. So untagged
elements cannot be converted at all — and the useful thing this can do is
say exactly which ones, rather than inventing identities that would be
refused later or, worse, accepted and unstable.
"""

from __future__ import annotations

import json
import pathlib
import subprocess

import pytest

from cli import inspect_package

TAGGED = """\
Feature: Response approval

  @rule:only-approved-may-send
  Rule: Only an approved response may be sent

    @scenario:unapproved-blocked
    Scenario: An unapproved response cannot be sent
      Given a drafted response
      When the representative sends it
      Then the send is refused
"""

MIXED = """\
Feature: Response approval

  @rule:only-approved-may-send
  Rule: Only an approved response may be sent

    @scenario:unapproved-blocked
    Scenario: An unapproved response cannot be sent
      Given a drafted response
      Then the send is refused

    Scenario: A second path nobody tagged
      Given a drafted response
      Then something else happens
"""

UNTAGGED = """\
Feature: Response approval

  Rule: Only an approved response may be sent

    Scenario: An unapproved response cannot be sent
      Given a drafted response
      Then the send is refused
"""


def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)


@pytest.fixture
def package(tmp_path):
    """A repository holding one feature package, committed."""
    def make(text=TAGGED, key="response-approval"):
        feature_dir = tmp_path / "features" / key
        feature_dir.mkdir(parents=True, exist_ok=True)
        (feature_dir / "acceptance.feature").write_text(text, encoding="utf-8")
        if not (tmp_path / ".git").exists():
            _git(tmp_path, "init", "-q")
            _git(tmp_path, "config", "user.email", "t@e.invalid")
            _git(tmp_path, "config", "user.name", "t")
        _git(tmp_path, "add", "-A")
        _git(tmp_path, "commit", "-q", "-m", "package")
        return tmp_path, key
    return make


# --- what converts ----------------------------------------------------------


def test_authored_identities_become_references(package):
    """"Preserve IDs where authored" — the tag the team wrote is the
    identity, and the draft points at it rather than at a name."""
    target, key = package()

    report = inspect_package.inspect(target, key, source_key="app")

    refs = [entry["ref"] for entry in report.draft["selected_behavior"]]
    assert "app/response-approval#rule:only-approved-may-send" in refs
    assert "app/response-approval#scenario:unapproved-blocked" in refs


def test_every_converted_reference_is_tagged_not_derived(package):
    """A baseline refuses `id_source: derived`, so emitting one would
    produce a draft that cannot ever be approved."""
    target, key = package()

    report = inspect_package.inspect(target, key, source_key="app")

    assert all(e["id_source"] == "tag" for e in report.draft["selected_behavior"])


def test_the_pinned_revision_is_the_commit_not_a_branch(package):
    """A commitment bound to a moving pointer can change without anyone
    deciding to change it — the engine refuses branch names for the same
    reason."""
    target, key = package()

    report = inspect_package.inspect(target, key, source_key="app")

    revision = report.draft["sources"][0]["revision"]
    assert len(revision) == 40
    assert revision != "HEAD"


# --- what is flagged rather than invented -----------------------------------


def test_an_untagged_element_is_flagged_and_not_converted(package):
    """The useful output. Inventing a derived identity produces something
    refused later, or — worse — accepted and unstable."""
    target, key = package(MIXED)

    report = inspect_package.inspect(target, key, source_key="app")

    assert any("A second path nobody tagged" in flag for flag in report.needs_identity)
    refs = " ".join(e["ref"] for e in report.draft["selected_behavior"])
    assert "second" not in refs


def test_a_package_with_no_authored_identity_yields_no_draft(package):
    """Nothing here can bind an approval, and a draft implying otherwise
    would be the most misleading possible output."""
    target, key = package(UNTAGGED)

    report = inspect_package.inspect(target, key, source_key="app")

    assert report.draft is None
    assert report.needs_identity


def test_the_flag_says_what_to_do_about_it(package):
    target, key = package(UNTAGGED)

    report = inspect_package.inspect(target, key, source_key="app")

    assert any("@scenario:" in flag or "@rule:" in flag for flag in report.needs_identity)


# --- what it cannot produce -------------------------------------------------


def _keys(node):
    """Every key anywhere in the structure."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield key
            yield from _keys(value)
    elif isinstance(node, list):
        for value in node:
            yield from _keys(value)


def test_the_draft_carries_no_approval_field(package):
    """Increment 01 made this structurally true of baselines; the
    conversion path must not be the thing that reintroduces it.

    Asserted over **keys**, not over the serialized document. The first
    version searched the JSON text and failed on the slug
    `only-approved-may-send` — legitimate content from the feature file.
    That is the fourth unanchored absence assertion in this plan, and the
    rule by now is explicit: an absence assertion needs to name the thing
    it is asserting the absence of.
    """
    target, key = package()

    report = inspect_package.inspect(target, key, source_key="app")

    for name in _keys(report.draft):
        assert not any(word in name.lower()
                       for word in ("approv", "authoriz", "decision", "committed")), name


def test_the_draft_is_incomplete_against_the_published_schema(package):
    """The revision is a fact and can be read. The opportunity is a
    decision and cannot, so the draft omits it and is incomplete by
    design — `opportunity` is required at the top level of
    `behavioral_baseline.schema.json`.

    (`validate_baseline` is the cross-field checker and passes this
    document; the schema is the thing that requires the field. Worth
    naming, because I first asserted the wrong one.)
    """
    import json

    target, key = package()
    report = inspect_package.inspect(target, key, source_key="app")

    schema = json.loads(
        (pathlib.Path(__file__).resolve().parents[1]
         / "governance" / "schemas" / "behavioral_baseline.schema.json")
        .read_text(encoding="utf-8")
    )

    assert "opportunity" in schema["required"]
    assert "opportunity" not in report.draft


def test_the_draft_cannot_be_authorized_as_it_stands(package):
    """The stronger statement, and the one that matters: even pointed at a
    live commitment saying yes, this draft is NOT AUTHORIZED, because it
    declares no opportunity for that commitment to bind. Increment 11's
    binding check refuses it, so a draft cannot be laundered into an
    approval by submitting it.
    """
    from cli.authority_check import Outcome, verify

    target, key = package()
    report = inspect_package.inspect(target, key, source_key="app")

    result = verify(
        report.draft, commitment_id="cmt-1",
        fetch=lambda i: {"schema_version": 1, "commitment_id": i, "authorizes_work": True},
    )

    assert result.outcome is Outcome.NOT_AUTHORIZED


def test_the_draft_says_plainly_what_is_still_required(package):
    target, key = package()

    report = inspect_package.inspect(target, key, source_key="app")

    assert report.still_required
    assert any("opportunity" in item.lower() for item in report.still_required)


# --- history is retained ----------------------------------------------------


def test_inspection_does_not_modify_the_package(package):
    """"Retain history." An inspection that rewrites the source it is
    inspecting destroys the thing an approver would compare against."""
    target, key = package(MIXED)
    before = (target / "features" / key / "acceptance.feature").read_text(encoding="utf-8")

    inspect_package.inspect(target, key, source_key="app")

    after = (target / "features" / key / "acceptance.feature").read_text(encoding="utf-8")
    assert after == before


def test_a_dirty_working_tree_is_refused(package):
    """The draft pins a commit. If the file on disk differs from that
    commit, the draft describes something that was never committed and the
    digest binds text nobody can retrieve."""
    target, key = package()
    feature = target / "features" / key / "acceptance.feature"
    feature.write_text(feature.read_text(encoding="utf-8") + "\n# edited\n", encoding="utf-8")

    with pytest.raises(inspect_package.NotInspectable) as refused:
        inspect_package.inspect(target, key, source_key="app")

    assert "uncommitted" in str(refused.value).lower()


def test_a_missing_package_is_refused_clearly(package):
    target, _ = package()

    with pytest.raises(inspect_package.NotInspectable):
        inspect_package.inspect(target, "no-such-feature", source_key="app")


# --- runnable ---------------------------------------------------------------


def test_it_has_a_command_line():
    assert callable(getattr(inspect_package, "main", None))


def test_running_it_writes_a_draft(package, tmp_path):
    target, key = package()
    out = tmp_path / "draft.json"

    code = inspect_package.main([
        "--target", str(target), "--feature", key,
        "--source-key", "app", "--out", str(out),
    ])

    assert code == 0
    assert json.loads(out.read_text(encoding="utf-8"))["commitment_key"]


def test_nothing_is_written_when_there_is_nothing_to_convert(package, tmp_path):
    target, key = package(UNTAGGED)
    out = tmp_path / "draft.json"

    code = inspect_package.main([
        "--target", str(target), "--feature", key,
        "--source-key", "app", "--out", str(out),
    ])

    assert code != 0
    assert not out.exists()


# --- seven review findings --------------------------------------------------

CONSTRAINED = """\
Feature: Response approval

  @rule:only-approved-may-send @nfr:send-latency
  Rule: Only an approved response may be sent

    @scenario:unapproved-blocked @evaluation:tone-check
    Scenario: An unapproved response cannot be sent
      Given a drafted response
      Then the send is refused
"""


@pytest.mark.parametrize("key", ["../other", "Not-A-Slug", "", "a/b", "-leading"])
def test_a_feature_key_that_is_not_a_slug_is_refused(package, key):
    """Two problems in one. `../other` reads a different directory under
    the target, and anything outside the schema's pattern produces a draft
    whose `commitment_key` the schema rejects — a successful-looking run
    that cannot be used."""
    target, _ = package()

    with pytest.raises(inspect_package.NotInspectable):
        inspect_package.inspect(target, key, source_key="app")


@pytest.mark.parametrize("source_key", ["Not-A-Slug", "", "with/slash", "-leading"])
def test_a_source_key_that_is_not_a_slug_is_refused(package, source_key):
    target, key = package()

    with pytest.raises(inspect_package.NotInspectable):
        inspect_package.inspect(target, key, source_key=source_key)


def test_every_selected_entry_carries_a_content_digest(package):
    """`selectedBehaviorRef` requires it. Without it the draft stays
    schema-invalid even after a person supplies the opportunity, scope and
    exclusions the report asks for — so the "starting point" never becomes
    a usable baseline."""
    target, key = package()

    report = inspect_package.inspect(target, key, source_key="app")

    for entry in report.draft["selected_behavior"]:
        assert entry["content_digest"].startswith("sha256:"), entry


def test_the_digest_is_the_closure_digest_not_a_hash_of_the_file(package):
    """It has to be the same function the drift checker compares against,
    or a draft is born drifted."""
    from cli import spec_closure

    target, key = package()
    report = inspect_package.inspect(target, key, source_key="app")

    doc = spec_closure.parse_feature(
        (target / "features" / key / "acceptance.feature").read_text(encoding="utf-8")
    )
    element = spec_closure.resolve(doc, "scenario", "unapproved-blocked")
    expected = spec_closure.content_digest(spec_closure.closure(doc, element))

    entry = next(e for e in report.draft["selected_behavior"] if "scenario:" in e["ref"])
    assert entry["content_digest"] == expected


def test_a_gitignored_feature_file_is_not_treated_as_committed(package, tmp_path):
    """Ordinary porcelain omits ignored files, so an ignored feature read
    as clean and was pinned to HEAD — a draft describing text that does not
    exist at the revision it names."""
    target, key = package()
    (target / ".gitignore").write_text("features/\n", encoding="utf-8")
    _git(target, "add", "-A")
    _git(target, "commit", "-q", "-m", "ignore features")
    _git(target, "rm", "-r", "--cached", "-q", "features")
    _git(target, "commit", "-q", "-m", "untrack features")

    with pytest.raises(inspect_package.NotInspectable):
        inspect_package.inspect(target, key, source_key="app")


def test_authored_constraint_tags_are_reported_not_dropped(package):
    """`@nfr:` / `@evaluation:` / `@design:` / `@agent-authority:` are
    exactly the kinds a `constraints` entry may reference, so silently
    filtering them lost authored scope while the report claimed everything
    authored was included."""
    target, key = package(CONSTRAINED)

    report = inspect_package.inspect(target, key, source_key="app")

    flagged = " ".join(report.needs_decision)
    assert "nfr:send-latency" in flagged
    assert "evaluation:tone-check" in flagged


def test_constraint_tags_are_not_invented_into_the_draft(package):
    """A constraint entry needs a `content_digest` of content this tool
    cannot see — an NFR lives in `nfrs.md`, not in the Gherkin. Emitting
    one would mean fabricating the digest that binds it."""
    target, key = package(CONSTRAINED)

    report = inspect_package.inspect(target, key, source_key="app")

    assert "constraints" not in report.draft


def test_a_malformed_feature_file_refuses_rather_than_traces(package):
    """`parse_feature` raises, and `main` caught only `NotInspectable`."""
    target, key = package()
    # An unclosed docstring. The first attempt at this test used
    # `Scenario` with no colon, which the parser happily reads as
    # description text — a malformed-input test has to be verified to
    # actually malform something.
    (target / "features" / key / "acceptance.feature").write_text(
        'Feature: f\n  Scenario: s\n    Given x\n      """\n      never closed\n',
        encoding="utf-8",
    )
    _git(target, "add", "-A")
    _git(target, "commit", "-q", "-m", "broken")

    with pytest.raises(inspect_package.NotInspectable):
        inspect_package.inspect(target, key, source_key="app")


def test_a_checkout_with_no_origin_names_that_as_still_required(package):
    """`repository` is required and `minLength: 1`, so an empty string is
    an extra schema defect. It is a normal state for a local checkout — it
    just has to be named rather than left for someone to discover."""
    target, key = package()

    report = inspect_package.inspect(target, key, source_key="app")

    if not report.draft["sources"][0]["repository"]:
        assert any("repository" in item.lower() for item in report.still_required)


def test_the_command_module_follows_the_repository_convention():
    """`cmd_*.py` registers, the domain module holds the logic — the split
    every sibling command uses (`cmd_validate_baseline.py` beside
    `baseline_check.py`)."""
    import importlib

    module = importlib.import_module("cli.cmd_inspect_package")
    assert callable(module.register)
