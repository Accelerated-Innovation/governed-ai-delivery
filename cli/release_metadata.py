# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Approved release facts and candidate selection, independent of installation."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from packaging.specifiers import SpecifierSet
from packaging.version import Version

from .schema_validation import DocumentError, parse_document, validate_document

MAX_METADATA_BYTES = 2 * 1024 * 1024


def validate_source_url(url):
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise DocumentError("Metadata requires an HTTPS URL without credentials, query or fragment")


def timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("Timezone is required")
        return parsed.astimezone(timezone.utc)
    except (AttributeError, TypeError, ValueError, OverflowError) as exc:
        raise DocumentError("Invalid timezone-aware metadata timestamp") from exc


def parse_metadata(document, profile):
    document = deepcopy(document)
    validate_document(document, "release-metadata")
    sources = {s.id: s for s in profile.maintenance.sources}
    source = sources.get(document["source_id"])
    if source is None or document["source_url"] != source.url:
        raise DocumentError("Release metadata source is not approved by this profile")
    validate_source_url(source.url)
    for key in ("as_of", "retrieved_at"):
        if document[key] is not None:
            timestamp(document[key])
    seen = set()
    for release in document["releases"]:
        identity = (release["component"], Version(release["version"]), release["channel"])
        if identity in seen:
            raise DocumentError("Duplicate release version/channel")
        seen.add(identity)
        if release["channel"] not in source.channels:
            raise DocumentError("Release channel is not approved")
        SpecifierSet(release["requires_govkit"])
        SpecifierSet(release["requires_python"])
        for specification in release["dependencies"].values():
            SpecifierSet(specification)
    return document


def _freshness(document, policy, as_of):
    if document["lookup_status"] in {"failed", "unavailable"}:
        return "unknown", None
    if as_of is None or document["as_of"] is None or document["retrieved_at"] is None:
        return "unknown", None
    observed, published, retrieved = map(
        timestamp, (as_of, document["as_of"], document["retrieved_at"])
    )
    if published > retrieved or retrieved > observed:
        return "unknown", None
    age = (observed - published).total_seconds() / 3600
    if policy.metadata_max_age_hours is None:
        return "unknown", age
    return ("fresh" if age <= policy.metadata_max_age_hours else "stale"), age


def _version_reasons(candidate, channel, compatibility, pin, pack_pin):
    """Policy facts that do not depend on a publisher's release record."""
    reasons = []
    if channel == "stable" and (candidate.is_prerelease or candidate.is_devrelease):
        reasons.append("prerelease-channel")
    if pack_pin and candidate != Version(pack_pin["version"]):
        reasons.append("profile-pack-pin")
    if candidate not in compatibility:
        reasons.append("policy-compatibility")
    if pin is not None and candidate != pin:
        reasons.append("pin")
    return reasons


def select_candidates(profile, document, *, installed, running_govkit, python_version, as_of):
    """Compare known releases to the current environment, never solve a hidden upgrade."""
    document = parse_metadata(document, profile)
    freshness, age = _freshness(document, profile.maintenance, as_of)
    results = []
    for constraint in profile.maintenance.constraints:
        if constraint.source_id != document["source_id"]:
            continue
        compatibility = SpecifierSet(constraint.compatibility or "")
        pin = Version(constraint.pin) if constraint.pin else None
        pack_pin = next(
            (p for p in profile.document.get("packs", []) if p["id"] == constraint.component), None
        )
        current = installed.get(constraint.component)
        current_version = Version(current) if current else None
        releases = sorted(
            (r for r in document["releases"] if r["component"] == constraint.component),
            key=lambda r: (Version(r["version"]), r["channel"]),
            reverse=True,
        )
        allowed, excluded = [], []
        for release in releases:
            candidate = Version(release["version"])
            reasons = []
            if release["channel"] != constraint.channel:
                reasons.append("channel")
            reasons.extend(
                _version_reasons(candidate, constraint.channel, compatibility, pin, pack_pin)
            )
            if Version(running_govkit) not in SpecifierSet(release["requires_govkit"]):
                reasons.append("govkit")
            if Version(python_version) not in SpecifierSet(release["requires_python"]):
                reasons.append("python")
            for component, specification in sorted(release["dependencies"].items()):
                selected = installed.get(component)
                if selected is None or Version(selected) not in SpecifierSet(specification):
                    reasons.append(f"dependency:{component}")
            if reasons:
                excluded.append(
                    {
                        "version": release["version"],
                        "channel": release["channel"],
                        "reasons": reasons,
                    }
                )
            elif release["version"] not in allowed:
                allowed.append(release["version"])
        target = next(
            (v for v in allowed if current_version is not None and Version(v) > current_version),
            None,
        )
        current_policy_state = "unknown"
        if current_version is not None:
            if _version_reasons(current_version, constraint.channel, compatibility, pin, pack_pin):
                current_policy_state = "outside-policy"
            elif freshness == "fresh":
                # Reuse the complete candidate evaluation, including release channel,
                # runtime and installed dependencies. Absence is not compatibility.
                if any(Version(v) == current_version for v in allowed):
                    current_policy_state = "compliant"
                elif any(Version(r["version"]) == current_version for r in releases):
                    current_policy_state = "outside-policy"
        results.append(
            {
                "component": constraint.component,
                "installed": current,
                "source_id": constraint.source_id,
                "source_url": document["source_url"],
                "channel": constraint.channel,
                "pin": constraint.pin,
                "compatibility": constraint.compatibility,
                "newest_known": releases[0]["version"] if releases else None,
                "compatible_candidates": allowed,
                "excluded": excluded,
                "selected_target": target if freshness == "fresh" else None,
                "current_policy_state": current_policy_state,
                "freshness": freshness,
                "age_hours": age,
                "lookup_status": document["lookup_status"],
                "as_of": document["as_of"],
                "retrieved_at": document["retrieved_at"],
                "latest_verified": False,
            }
        )
    return results


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise DocumentError("Release metadata redirects require separately approved source URLs")


def fetch_bytes(url):
    """One bounded anonymous GET to the exact approved URL; no project context."""
    validate_source_url(url)
    request = Request(
        url, headers={"Accept": "application/json", "User-Agent": "govkit-release-metadata"}
    )
    with build_opener(_NoRedirect()).open(request, timeout=10) as response:
        content = response.read(MAX_METADATA_BYTES + 1)
    if len(content) > MAX_METADATA_BYTES:
        raise DocumentError("Release metadata exceeds size limit")
    return content


def refresh_metadata(profile, source_id, *, as_of, fetch=fetch_bytes):
    """Return facts only. The CLI separately owns an explicitly named cache write."""
    timestamp(as_of)
    if not profile.maintenance.allow_refresh:
        raise DocumentError("Metadata refresh is disabled by accepted policy")
    source = next((s for s in profile.maintenance.sources if s.id == source_id), None)
    if source is None:
        raise DocumentError("Metadata refresh source is not approved")
    validate_source_url(source.url)
    try:
        content = fetch(source.url)
        if not isinstance(content, bytes) or len(content) > MAX_METADATA_BYTES:
            raise DocumentError("Release metadata exceeds size/type limit")
        document = parse_document(content)
        document = parse_metadata(document, profile)
        if document["source_id"] != source.id:
            raise DocumentError("Response source differs from the requested source")
        # A source may report unavailable facts; a successful GET is not a successful lookup.
        if document["lookup_status"] not in {"failed", "unavailable"}:
            document["lookup_status"] = "refreshed"
        document["retrieved_at"] = as_of
        return parse_metadata(document, profile)
    except (OSError, ValueError, TypeError):
        return {
            "schema_version": 1,
            "kind": "release-metadata",
            "source_id": source.id,
            "source_url": source.url,
            "as_of": None,
            "retrieved_at": as_of,
            "lookup_status": "failed",
            "releases": [],
        }
