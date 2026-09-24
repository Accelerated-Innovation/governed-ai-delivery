# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Admission of caller-supplied native PR context; no credentials or network access."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .change_scope import capture_change
from .schema_validation import DocumentError, content_digest, validate_document


@dataclass(frozen=True)
class Admission:
    head: str
    base: str
    fork: bool


def _sha(value):
    if (
        not isinstance(value, str)
        or not re.fullmatch(r"(?:[a-f0-9]{40}|[a-f0-9]{64})", value)
        or set(value) == {"0"}
    ):
        raise DocumentError("Provider admission requires full nonzero commit SHAs")
    return value


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


def admit_run(
    policy, event, target, policy_target, request_path, base, *, policy_revision, request_digest
):
    admitted = parse_event(policy, event)
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
    for root, expected in ((target, admitted.head), (policy_target, _sha(policy_revision))):
        snapshot = capture_change(root, "HEAD")
        if not snapshot.complete or snapshot.revision != expected or snapshot.document["changes"]:
            raise DocumentError(
                "Provider checkout must be complete, clean and at its pinned revision"
            )
    with request_path.open("rb") as stream:
        data = stream.read(4 * 1024 * 1024 + 1)
    if len(data) > 4 * 1024 * 1024 or content_digest(data) != request_digest:
        raise DocumentError("Caller-accepted request digest mismatch")
    return admitted
