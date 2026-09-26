# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Admission of caller-supplied native PR context; no credentials or network access."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, replace
from pathlib import Path

from .change_policy import load_change_policy
from .change_scope import _git, capture_change
from .observation_limits import DEFAULT_OBSERVATION_LIMITS
from .observation_policy import (
    POLICY_SOURCE_BYTES,
    ObservationBudget,
    policy_budget,
    read_policy_source,
)
from .pack_loading import contained_file
from .profiles import parse_profile
from .schema_validation import DocumentError, content_digest, parse_document, validate_document


@dataclass(frozen=True)
class Admission:
    head: str
    base: str
    fork: bool
    observation: ObservationBudget | None = None


def _sha(value):
    if (
        not isinstance(value, str)
        or not re.fullmatch(r"(?:[a-fA-F0-9]{40}|[a-fA-F0-9]{64})", value)
        or set(value) == {"0"}
    ):
        raise DocumentError("Provider admission requires full nonzero commit SHAs")
    return value.lower()


def parse_event(policy, event):
    validate_document(policy, "provider-admission")
    try:
        payload = event["payload"]
        if policy["provider"] == "github":
            if event["event_name"] != "pull_request" or payload["action"] not in {
                "opened",
                "reopened",
                "synchronize",
                "ready_for_review",
                "edited",
            }:
                raise ValueError("Unsupported GitHub event")
            pr = payload["pull_request"]
            if pr["state"] != "open" or pr["draft"] is not False:
                raise ValueError("PR is closed or draft")
            repo = payload["repository"]["full_name"]
            if pr["base"]["repo"]["full_name"] != repo:
                raise ValueError("PR target repository mismatch")
            ref = "refs/heads/" + pr["base"]["ref"]
            source = pr["head"]["repo"]["full_name"]
            head, base = pr["head"]["sha"], pr["base"]["sha"]
            number = pr["number"]
        else:
            if event["event_name"] != "PullRequest":
                raise ValueError("Unsupported Azure build reason")
            pr = payload
            if pr["status"] != "active" or pr["isDraft"] is not False:
                raise ValueError("PR is closed or draft")
            repo, ref = pr["repository"]["id"], pr["targetRefName"]
            source = pr["forkSource"]["repository"]["id"] if pr.get("forkSource") else repo
            head, base = (
                pr["lastMergeSourceCommit"]["commitId"],
                pr["lastMergeTargetCommit"]["commitId"],
            )
            number = pr["pullRequestId"]
        if type(number) is not int or number <= 0 or not isinstance(source, str) or not source:
            raise ValueError("Incomplete PR identity")
        if repo != policy["repository"] or ref != policy["target_ref"]:
            raise ValueError("PR repository or target ref differs from accepted policy")
        fork = source != repo
        if fork and not policy["allow_forks"]:
            raise ValueError("Fork PR requires explicit accepted opt-in")
        return Admission(_sha(head), _sha(base), fork)
    except (KeyError, TypeError, ValueError) as exc:
        raise DocumentError(f"Provider admission rejected: {exc}") from exc


def pinned_observation_budget(root, revision, profile_digest):
    """Verify small bootstrap inputs against pinned blobs before expanding capture."""
    revision = _sha(revision)
    if root.is_symlink() or not root.is_dir():
        raise DocumentError("Policy bootstrap requires a real checkout")

    def head():
        if _git(root, "rev-parse", "HEAD").decode().strip() != revision:
            raise DocumentError("Policy bootstrap HEAD differs from the pinned revision")

    def pinned_bytes(reference):
        current = read_policy_source(root, reference)
        entry = _git(
            root, "ls-tree", "-l", "-z", revision, "--", ":(literal)" + reference, limit=8192
        )
        records = entry.rstrip(b"\0").split(b"\0")
        if len(records) != 1 or b"\t" not in records[0]:
            raise DocumentError("Policy bootstrap source is absent from the pinned revision")
        metadata, name = records[0].split(b"\t", 1)
        mode, kind, sha, size = metadata.split()
        if (
            name.decode() != reference
            or kind != b"blob"
            or mode not in (b"100644", b"100755")
            or int(size) > POLICY_SOURCE_BYTES
        ):
            raise DocumentError("Policy bootstrap source has an unsupported kind or size")
        # Windows does not expose Git executable mode via stat; the full index
        # capture still compares pinned Git modes on every platform.
        executable = bool(contained_file(root, reference).stat().st_mode & 0o111)
        if os.name != "nt" and executable != (mode == b"100755"):
            raise DocumentError("Policy bootstrap source mode differs from the pinned blob")
        if _git(root, "cat-file", "blob", sha.decode(), limit=POLICY_SOURCE_BYTES) != current:
            raise DocumentError("Policy bootstrap bytes differ from the pinned blob")
        return current

    head()
    profile_bytes = pinned_bytes(".govkit/profile.yaml")
    profile = parse_profile(parse_document(profile_bytes))
    if profile_digest is not None and profile.digest != profile_digest:
        raise DocumentError("Policy bootstrap differs from the pipeline profile pin")
    reference = profile.document["policy"].get("conformance", {}).get("reference")
    if reference:
        config_bytes = pinned_bytes(reference)
        config, digest = load_change_policy(root, profile)
        if content_digest(config_bytes) != digest:
            raise DocumentError("Policy bootstrap changed while reading")
        budget = policy_budget(config, digest)
    else:
        budget = ObservationBudget()
    if profile_digest is None and budget.limits != DEFAULT_OBSERVATION_LIMITS:
        raise DocumentError("Expanded observation requires the pipeline profile pin")
    if pinned_bytes(".govkit/profile.yaml") != profile_bytes:
        raise DocumentError("Policy bootstrap profile changed while reading")
    if reference and pinned_bytes(reference) != config_bytes:
        raise DocumentError("Policy bootstrap configuration changed while reading")
    head()
    return budget


def admit_run(
    policy,
    event,
    target,
    policy_target,
    request_path,
    base,
    *,
    policy_revision,
    request_digest,
    profile_digest=None,
):
    admitted = parse_event(policy, event)
    if any(Path(p).is_symlink() for p in (target, policy_target, request_path)):
        raise DocumentError("Provider inputs cannot be symlinks")
    target, policy_target, request_path = (
        Path(p).resolve() for p in (target, policy_target, request_path)
    )
    if (
        target == policy_target
        or target in policy_target.parents
        or policy_target in target.parents
        or target == request_path
        or target in request_path.parents
    ):
        raise DocumentError(
            "Admission requires independent policy and caller-accepted request paths"
        )
    if admitted.base != _sha(base):
        raise DocumentError("Provider base differs from the conformance base")
    budget = pinned_observation_budget(policy_target, policy_revision, profile_digest)
    for root, expected in ((target, admitted.head), (policy_target, _sha(policy_revision))):
        snapshot = capture_change(root, "HEAD", limits=budget.limits)
        if not snapshot.complete or snapshot.revision != expected or snapshot.document["changes"]:
            raise DocumentError(
                "Provider checkout must be complete, clean and at its pinned revision"
            )
    with request_path.open("rb") as stream:
        data = stream.read(4 * 1024 * 1024 + 1)
    if len(data) > 4 * 1024 * 1024 or content_digest(data) != request_digest:
        raise DocumentError("Caller-accepted request digest mismatch")
    return replace(admitted, observation=budget)
