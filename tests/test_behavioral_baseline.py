"""The behavioral-baseline contract: schema, canonical digest, and the
cross-field checks a JSON Schema cannot express.

Increment 01 of the AIPOS behavior-contract plan
(plans/AIPOS_BEHAVIOR_CONTRACT_PLAN.md).

A baseline is what a product commitment binds: exactly which behavior was
approved, against exactly which immutable source revisions. Two properties
have to hold or the contract is not portable, and they are what this module
tests:

  - **Two consumers agree.** The same baseline digests identically regardless
    of key order, array order, indentation or Unicode composition — and
    differently the moment approved content changes.
  - **A manifest cannot approve itself.** No field means "approved", and the
    schema refuses to carry one.

Fixtures live under governance/fixtures/behavioral-baseline/ so they ship with
the wheel: a plugin or engine consumer conforms against the same bytes without
needing a checkout of this repository beside theirs.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

jsonschema = pytest.importorskip("jsonschema")
from jsonschema import Draft202012Validator  # noqa: E402

from cli import baseline, paths  # noqa: E402

# Resolved through the bundled-asset anchor rather than this file's location,
# so the suite exercises the same lookup a consumer performs — and so pointing
# govkit at a different bundle points the tests there too. A test that reads
# the checkout while the code reads the bundle proves nothing about the bundle.
SCHEMA_PATH = paths.GOVERNANCE_DIR / "schemas" / "behavioral_baseline.schema.json"
FIXTURES = paths.GOVERNANCE_DIR / "fixtures" / "behavioral-baseline"
VALID_BASELINE = FIXTURES / "valid" / "support-response.baseline.json"
GOLDEN_DIGEST = FIXTURES / "valid" / "support-response.digest"


def _schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _schema_errors(doc: dict) -> list[str]:
    validator = Draft202012Validator(_schema())
    return [e.message for e in validator.iter_errors(doc)]


# ---------------------------------------------------------------------------
# The schema itself
# ---------------------------------------------------------------------------


def test_schema_is_a_valid_json_schema():
    """The contract must itself conform to the meta-schema before it can judge
    anything else."""
    Draft202012Validator.check_schema(_schema())


def test_no_property_in_the_schema_means_approved():
    """The structural guarantee behind 'a manifest cannot assert approval'.

    Authority is read from the decision service, freshly, at the boundary that
    needs it. If a property here could carry it, every other control in the
    plan would be one JSON edit away from irrelevant — so the absence is
    asserted rather than assumed.
    """
    schema_text = json.dumps(_schema())
    properties = set(_schema()["properties"])

    assert not {p for p in properties if "approv" in p.lower() or "authoriz" in p.lower()}
    assert '"approved"' not in schema_text
    assert _schema()["additionalProperties"] is False


# ---------------------------------------------------------------------------
# The worked example
# ---------------------------------------------------------------------------


def test_support_response_fixture_conforms_to_the_schema():
    assert _schema_errors(_load(VALID_BASELINE)) == []


def test_support_response_fixture_passes_every_cross_field_check():
    issues, warnings = baseline.validate_baseline(_load(VALID_BASELINE))

    assert issues == []
    assert warnings == []


def test_excluded_prototype_behavior_is_recorded_as_a_decision_not_an_omission():
    """The prototype sent automatically; the commitment does not.

    The distinction that matters six months later is between "we never
    considered it" and "we considered it and did not commit it". An exclusion
    carrying a reason is the second one, and the scope check has to see it as
    out of scope rather than merely absent.
    """
    doc = _load(VALID_BASELINE)

    auto_send = "support-app/response-approval#scenario:automatic-send-on-high-confidence"
    excluded = {x["ref"]: x["reason"] for x in doc["exclusions"]}
    selected = {e["ref"] for e in doc["selected_behavior"]}

    assert auto_send in excluded
    assert excluded[auto_send].strip() != ""
    assert auto_send not in selected


# ---------------------------------------------------------------------------
# Rejection — schema level
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("fixture", "because"),
    [
        ("missing-opportunity-ref.json", "a baseline with no opportunity justifies nothing"),
        ("no-sources.json", "references cannot resolve without a source"),
        ("no-selected-behavior.json", "a commitment to no behavior is not a commitment"),
        ("mutable-source-revision.json", "'main' is a moving pointer, not a revision"),
        ("asserts-its-own-approval.json", "no caller may assert approval in a manifest"),
        ("unqualified-reference.json", "an unqualified ref cannot resolve across features"),
        ("moving-tag-as-repository-revision.json", "a git tag can be moved; a commit SHA cannot"),
        ("source-path-escapes-repository.json", "resolution must stay inside the bound revision"),
        ("constraint-listed-as-selected-behavior.json", "a constraint is not scope"),
    ],
)
def test_schema_rejects(fixture: str, because: str):
    errors = _schema_errors(_load(FIXTURES / "invalid" / fixture))

    assert errors, f"schema accepted {fixture} — {because}"


# ---------------------------------------------------------------------------
# Rejection — cross-field, where a schema cannot see the relationship
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("fixture", "expected_phrase"),
    [
        ("unsupported-version.json", "Unsupported baseline version"),
        ("reference-to-undeclared-source.json", "not declared in `sources`"),
        ("derived-identifier.json", "cannot bind an approval"),
        ("selected-and-excluded.json", "not both"),
        ("duplicate-reference.json", "One element, one entry"),
        ("kind-disagrees-with-ref.json", "must agree"),
        ("blocking-unresolved-question.json", "blocks commitment"),
        ("duplicate-source-key.json", "duplicate source_key"),
        ("duplicate-exclusion.json", "duplicate reference"),
        ("exclusion-from-undeclared-source.json", "records nothing"),
    ],
)
def test_cross_field_check_rejects(fixture: str, expected_phrase: str):
    """Each of these is schema-valid. The schema sees fields; these are
    relationships between fields."""
    doc = _load(FIXTURES / "invalid" / fixture)
    schema_errors = _schema_errors(doc)
    issues, _warnings = baseline.validate_baseline(doc)

    assert schema_errors == [], f"{fixture} should be schema-valid; the point is the cross-check"
    assert any(expected_phrase in issue for issue in issues), issues


def test_unsupported_version_short_circuits_instead_of_piling_on_reference_errors():
    """A baseline from the future is newer, not malformed.

    Reporting reference errors against a shape this build does not understand
    would be confidently wrong about fields that may mean something else in
    that version.
    """
    doc = _load(FIXTURES / "invalid" / "unsupported-version.json")
    doc["selected_behavior"][0]["ref"] = "undeclared-source/f#rule:x"

    issues, warnings = baseline.validate_baseline(doc)

    assert len(issues) == 1
    assert "Unsupported baseline version" in issues[0]
    assert "99" in issues[0]
    assert warnings == []


def test_derived_identifier_is_rejected_but_stays_readable():
    """Derived ids may be *read* from legacy corpora; they may not be
    *approved*. A slug derived from an element's name is stable only while the
    name is, so binding an approval to one binds it to a rename."""
    doc = _load(FIXTURES / "invalid" / "derived-identifier.json")

    assert _schema_errors(doc) == []
    issues, _ = baseline.validate_baseline(doc)

    assert any("id_source 'derived'" in i for i in issues)


# ---------------------------------------------------------------------------
# The digest — the cross-consumer contract
# ---------------------------------------------------------------------------


def test_golden_digest_matches_the_committed_vector():
    """If this fails, either the canonicalization changed or the fixture did.
    Either way every consumer's stored digest just stopped matching, so the
    change is a contract-version decision, not a fix."""
    expected = GOLDEN_DIGEST.read_text(encoding="utf-8").strip()

    assert baseline.compute_digest(_load(VALID_BASELINE)) == expected


@pytest.mark.parametrize(
    "vector",
    sorted(p.name for p in (FIXTURES / "digest-vectors").glob("same--*.json")),
)
def test_non_normative_difference_preserves_the_digest(vector: str):
    """Reordered keys, reordered arrays, different indentation, added advisory
    material — none of these is behavior, so none may read as drift."""
    expected = GOLDEN_DIGEST.read_text(encoding="utf-8").strip()

    assert baseline.compute_digest(_load(FIXTURES / "digest-vectors" / vector)) == expected


@pytest.mark.parametrize(
    "vector",
    sorted(p.name for p in (FIXTURES / "digest-vectors").glob("differs--*.json")),
)
def test_normative_change_changes_the_digest(vector: str):
    """A changed Examples row, a changed source revision, a scenario dropped
    from scope, or excluded behavior promoted into it — each changes what was
    approved, and must be visible as a different digest."""
    golden = GOLDEN_DIGEST.read_text(encoding="utf-8").strip()

    assert baseline.compute_digest(_load(FIXTURES / "digest-vectors" / vector)) != golden


def test_unicode_composition_does_not_change_the_digest():
    """The same characters in NFD (as a macOS checkout can hand them over) and
    NFC must agree, or two developers digest the same baseline differently."""
    nfc = _load(VALID_BASELINE)
    nfc["opportunity"]["outcome"] = "résumé of approved behavior"
    nfd = _load(VALID_BASELINE)
    nfd["opportunity"]["outcome"] = "résumé of approved behavior"

    assert baseline.compute_digest(nfc) == baseline.compute_digest(nfd)


def test_canonical_bytes_are_published_so_a_mismatch_can_be_localized():
    """A digest mismatch says two implementations disagree; the bytes say
    where. A consumer in another language is tested against these."""
    raw = baseline.canonical_bytes(_load(VALID_BASELINE))

    assert raw == raw.decode("utf-8").encode("utf-8")
    assert b'"advisory"' not in raw
    assert json.loads(raw)["commitment_key"] == "support-response-approval"


def test_canonicalization_does_not_mutate_its_input():
    """A validator that rewrites its input cannot detect drift, because it
    erases the drift it exists to find."""
    doc = _load(VALID_BASELINE)
    before = json.dumps(doc, sort_keys=True)

    baseline.compute_digest(doc)

    assert json.dumps(doc, sort_keys=True) == before


# ---------------------------------------------------------------------------
# Distribution — the contract is only shared if it ships
# ---------------------------------------------------------------------------


def test_schema_and_fixtures_resolve_through_the_bundled_asset_anchor():
    """Consumers must not need a sibling checkout. The anchor is what makes the
    same lookup work from an editable install and from the wheel, where
    governance/ ships as cli/governance/."""
    assert SCHEMA_PATH.is_file()
    assert (FIXTURES / "valid").is_dir()
    assert SCHEMA_PATH.is_relative_to(paths.GOVERNANCE_DIR)


def test_a_moving_git_tag_cannot_be_a_repository_revision():
    """`v1.2.3` is immutable for a published package and movable for a
    repository. Accepting it for both would let approved content change
    without the baseline changing — the one thing the revision binding
    exists to prevent."""
    doc = _load(VALID_BASELINE)
    doc["sources"][0]["revision"] = "v1.2.3"

    assert _schema_errors(doc), "a repository source accepted a movable tag"

    as_package = _load(VALID_BASELINE)
    as_package["sources"][0]["kind"] = "package"
    as_package["sources"][0]["revision"] = "v1.2.3"

    assert _schema_errors(as_package) == []


@pytest.mark.parametrize(
    "escape",
    ["../outside", "/etc/passwd", "..\\..\\other", "features/../../x", "C:/win", "./here"],
)
def test_source_path_cannot_leave_the_bound_revision(escape: str):
    """Resolution outside the source would read content the digest was never
    taken against, so the immutable binding would be immutable in name only."""
    doc = _load(VALID_BASELINE)
    doc["sources"][0]["path"] = escape

    schema_errors = _schema_errors(doc)
    issues, _ = baseline.validate_baseline(doc)

    assert schema_errors or any("leaves the source tree" in i for i in issues)


def test_whole_number_written_as_a_float_digests_identically():
    """`1` and `1.0` are the same number and both satisfy `type: integer`,
    but they serialize differently. Two producers spelling a whole number
    differently must not disagree on the digest."""
    as_int = _load(VALID_BASELINE)
    as_float = _load(VALID_BASELINE)
    as_float["version"] = 1.0

    assert baseline.check_version(as_float) == []
    assert baseline.compute_digest(as_float) == baseline.compute_digest(as_int)


def test_booleans_are_not_normalized_into_numbers():
    """`bool` subclasses `int` in Python, so the whole-number rule has to skip
    it or `true` would canonicalize to `1`."""
    doc = _load(VALID_BASELINE)
    doc["unresolved_questions"] = [{"question": "open", "blocks_commitment": False}]

    assert b'"blocks_commitment":false' in baseline.canonical_bytes(doc)


def test_duplicate_source_key_is_rejected_even_with_different_revisions():
    """Two declarations of one key make every reference through it ambiguous:
    a consumer cannot tell which revision the approved content came from."""
    doc = _load(VALID_BASELINE)
    shadow = json.loads(json.dumps(doc["sources"][0]))
    shadow["revision"] = "0" * 40
    doc["sources"].append(shadow)

    issues, _ = baseline.validate_baseline(doc)

    assert any("duplicate source_key" in i for i in issues)


def test_behavior_cannot_hide_in_constraints_and_constraints_cannot_claim_scope():
    """The two fields mean different things. Behavior recorded as a constraint
    is invisible to every scope check, which is how a Rule quietly stops being
    part of what anyone verifies."""
    nfr_as_scope = _load(VALID_BASELINE)
    nfr_as_scope["selected_behavior"].append(
        {
            "ref": "support-app/response-approval#nfr:another-nfr",
            "kind": "nfr",
            "id_source": "tag",
            "content_digest": "sha256:" + "0" * 64,
        }
    )
    scenario_as_constraint = _load(VALID_BASELINE)
    scenario_as_constraint["constraints"].append(
        {
            "ref": "support-app/response-approval#scenario:another-scenario",
            "kind": "scenario",
            "id_source": "tag",
            "content_digest": "sha256:" + "0" * 64,
        }
    )

    assert _schema_errors(nfr_as_scope)
    assert _schema_errors(scenario_as_constraint)
