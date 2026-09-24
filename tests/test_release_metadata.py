"""Offline release facts and explicitly approved, data-only refresh."""

import copy
import json

import pytest

from cli.profiles import parse_profile
from cli.release_metadata import parse_metadata, refresh_metadata, select_candidates
from tests.test_capability_packs import profile

AS_OF = "2026-09-24T12:00:00Z"
URL = "https://example.invalid/releases.json"


def project(*, pin=None, compatibility=">=1,<3", allow_refresh=False):
    doc = profile(["sample"]).document
    doc["maintenance"] = {
        "sources": [{"id": "team", "url": URL, "channels": ["stable", "preview"]}],
        "constraints": [
            {
                "component": "sample",
                "source_id": "team",
                "channel": "stable",
                "pin": pin,
                "compatibility": compatibility,
            }
        ],
        "metadata_max_age_hours": 24,
        "allow_refresh": allow_refresh,
    }
    return parse_profile(doc)


def release(version="1.1.0", **changes):
    return {
        "component": "sample",
        "version": version,
        "channel": "stable",
        "requires_govkit": ">=0.21",
        "requires_python": ">=3.11",
        "dependencies": {},
        **changes,
    }


def metadata(*releases, **changes):
    return {
        "schema_version": 1,
        "kind": "release-metadata",
        "source_id": "team",
        "source_url": URL,
        "as_of": AS_OF,
        "retrieved_at": AS_OF,
        "lookup_status": "cached",
        "releases": list(releases or [release()]),
        **changes,
    }


def candidates(doc=None, policy=None, **kwargs):
    return select_candidates(
        policy or project(),
        doc or metadata(),
        installed={"sample": "1.0.0"},
        running_govkit="0.21.1",
        python_version="3.12.14",
        as_of=AS_OF,
        **kwargs,
    )


def test_versions_policy_compatibility_dependencies_and_newest_are_separate():
    doc = metadata(
        release("1.9"),
        release("1.10"),
        release("2.0", requires_govkit=">=9"),
        release("2.1", requires_python=">=9"),
        release("2.2", dependencies={"other": ">=1"}),
        release("2.3rc1", channel="preview"),
        release("3.0"),
    )
    result = candidates(doc)[0]
    assert result["newest_known"] == "3.0"
    assert result["compatible_candidates"] == ["1.10", "1.9"]
    assert result["selected_target"] == "1.10"
    reasons = {r["version"]: r["reasons"] for r in result["excluded"]}
    assert "govkit" in reasons["2.0"] and "python" in reasons["2.1"]
    assert "dependency:other" in reasons["2.2"]
    assert "channel" in reasons["2.3rc1"] and "policy-compatibility" in reasons["3.0"]


def test_intentional_pin_is_compliant_without_requiring_available_update():
    result = candidates(metadata(release("1.0"), release("2.0")), project(pin="1.0"))[0]
    assert result["current_policy_state"] == "compliant"
    assert result["selected_target"] is None
    assert result["newest_known"] == "2.0"
    assert result["excluded"][0]["reasons"] == ["pin"]


@pytest.mark.parametrize(
    "status,stamp,expected",
    [
        ("cached", "2026-09-20T00:00:00Z", "stale"),
        ("failed", AS_OF, "unknown"),
        ("unavailable", AS_OF, "unknown"),
        ("cached", "2026-09-25T00:00:00Z", "unknown"),
    ],
)
def test_stale_failed_and_future_metadata_never_claim_current(status, stamp, expected):
    result = candidates(metadata(lookup_status=status, as_of=stamp))[0]
    assert result["freshness"] == expected
    assert result["selected_target"] is None
    assert result["latest_verified"] is False


@pytest.mark.parametrize("mutation", ["url", "source", "version", "specifier", "time", "duplicate"])
def test_invalid_or_unapproved_metadata_is_rejected(mutation):
    doc = metadata()
    if mutation == "url":
        doc["source_url"] = "https://other.invalid/releases"
    if mutation == "source":
        doc["source_id"] = "unapproved"
    if mutation == "version":
        doc["releases"][0]["version"] = "garbage"
    if mutation == "specifier":
        doc["releases"][0]["requires_govkit"] = "garbage"
    if mutation == "time":
        doc["as_of"] = "yesterday"
    if mutation == "duplicate":
        doc["releases"].append(copy.deepcopy(doc["releases"][0]))
    with pytest.raises(ValueError):
        parse_metadata(doc, project())


def test_refresh_is_opt_in_and_only_requests_the_approved_url():
    calls = []

    def fetch(url):
        calls.append(url)
        return json.dumps(metadata()).encode()

    with pytest.raises(ValueError, match="refresh"):
        refresh_metadata(project(), "team", as_of=AS_OF, fetch=fetch)
    assert calls == []
    result = refresh_metadata(project(allow_refresh=True), "team", as_of=AS_OF, fetch=fetch)
    assert calls == [URL]
    assert result["lookup_status"] == "refreshed"
    assert result["retrieved_at"] == AS_OF
    assert result["as_of"] == AS_OF


def test_failed_refresh_keeps_failure_explicit_and_does_not_leak_transport_details():
    def fetch(url):
        raise OSError("secret transport detail")

    result = refresh_metadata(project(allow_refresh=True), "team", as_of=AS_OF, fetch=fetch)
    assert result["lookup_status"] == "failed"
    assert result["releases"] == []
    assert "secret" not in json.dumps(result)


def test_no_refresh_with_unapproved_source_or_query_credentials():
    called = []
    with pytest.raises(ValueError):
        refresh_metadata(project(allow_refresh=True), "unknown", as_of=AS_OF, fetch=called.append)
    assert not called


def test_profile_pack_pin_cannot_be_overridden_by_maintenance_compatibility():
    doc = project().document
    doc["packs"] = [{"id": "sample", "version": "1.0.0", "source": "bundled"}]
    result = candidates(metadata(release("2.0")), parse_profile(doc))[0]
    assert result["selected_target"] is None
    assert "profile-pack-pin" in result["excluded"][0]["reasons"]


def test_stable_channel_cannot_smuggle_a_prerelease():
    result = candidates(metadata(release("2.0rc1")), project(compatibility=">=1.0rc1"))[0]
    assert result["selected_target"] is None
    assert "prerelease-channel" in result["excluded"][0]["reasons"]


def test_transport_uses_one_bounded_anonymous_get_and_disallows_redirects(monkeypatch):
    from cli import release_metadata as module

    calls = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, count):
            calls.append(("read", count))
            return b"{}"

    class Opener:
        def open(self, request, timeout):
            calls.append((request.full_url, request.data, request.headers, timeout))
            return Response()

    def opener(handler):
        with pytest.raises(ValueError, match="redirect"):
            handler.redirect_request(None, None, 302, "Found", {}, "https://other.invalid")
        return Opener()

    monkeypatch.setattr(module, "build_opener", opener)
    assert module.fetch_bytes(URL) == b"{}"
    assert calls[0][0:2] == (URL, None)
    assert calls[0][2] == {"Accept": "application/json", "User-agent": "govkit-release-metadata"}
    assert calls[0][3] == 10
    assert calls[1] == ("read", module.MAX_METADATA_BYTES + 1)
    for url in (
        URL + "?token=private",
        URL + "#fragment",
        "http://example.invalid",
        "https://user:pass@example.invalid",
    ):
        with pytest.raises(ValueError):
            module.fetch_bytes(url)
    assert len(calls) == 2


def test_refresh_rejects_oversized_response_and_keeps_source_as_of():
    from cli.release_metadata import MAX_METADATA_BYTES

    result = refresh_metadata(
        project(allow_refresh=True),
        "team",
        as_of=AS_OF,
        fetch=lambda _: b"x" * (MAX_METADATA_BYTES + 1),
    )
    assert result["lookup_status"] == "failed"
    old = metadata(as_of="2026-09-20T00:00:00Z")
    result = refresh_metadata(
        project(allow_refresh=True), "team", as_of=AS_OF, fetch=lambda _: json.dumps(old).encode()
    )
    assert result["as_of"] == old["as_of"]
    assert candidates(result)[0]["freshness"] == "stale"


def test_installed_version_outside_profile_pack_pin_is_not_compliant():
    doc = project().document
    doc["packs"] = [{"id": "sample", "version": "1.0.0", "source": "bundled"}]
    result = select_candidates(
        parse_profile(doc),
        metadata(),
        installed={"sample": "1.1.0"},
        running_govkit="0.21.1",
        python_version="3.12.14",
        as_of=AS_OF,
    )[0]
    assert result["current_policy_state"] == "outside-policy"


def test_refresh_rejects_sensitive_source_url_before_transport_or_failure_record():
    doc = project(allow_refresh=True).document
    doc["maintenance"]["sources"][0]["url"] = URL + "?token=secret"
    calls = []
    with pytest.raises(ValueError, match="URL"):
        refresh_metadata(parse_profile(doc), "team", as_of=AS_OF, fetch=calls.append)
    assert calls == []
