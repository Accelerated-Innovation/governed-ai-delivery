# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Post a built verification run to the Product Definition Graph.

This is the one place GovKit writes to the graph. It sends the `request` of a
`govkit.verification-run` document, as built, and nothing else.

- **The address and the token come from the environment.** An address read
  from the repository, with a credential from the environment, would let a
  change send the token wherever it liked.
- **Its own token.** The graph accepts a run only from the `service` role.
  The read-only credential of `pdg_client` is not used here, and this
  credential is not used there.
- **A refusal is an answer; silence is not.** A 4xx is the graph's verdict on
  the run. A 5xx, a timeout, a redirect or a body that is not the published
  envelope is no verdict at all.
- **Nothing from a response is trusted as text.** A reason code and the
  identifiers a refusal names are reduced to plain, bounded strings.

Standard-library `urllib`, as in `pdg_client`: most adopters have no graph.
"""

from __future__ import annotations

import json
import os
import stat
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

from . import verification_run
from .schema_validation import DocumentError, validate_document

URL_ENV = "GOVKIT_PDG_URL"
TOKEN_ENV = "GOVKIT_PDG_SERVICE_TOKEN"
ROUTE = "/v1/verification-runs"
TIMEOUT_SECONDS = 30
MAX_DOCUMENT_BYTES = 5 * 1024 * 1024
MAX_RESPONSE_BYTES = 1024 * 1024
_NAMED = 20
_NAME_MAX = 200
EXIT_RECORDED, EXIT_REFUSED, EXIT_NOT_STARTED, EXIT_UNANSWERED = 0, 1, 2, 3


class PushError(ValueError):
    """The push could not start. Nothing was sent."""


class Unanswered(Exception):
    """The graph gave no usable answer. Whether the run was recorded is not known."""


class Refused(Exception):
    """The graph refused the run. Nothing was recorded."""

    def __init__(self, status: int, code: str, names: tuple[str, ...] = ()) -> None:
        super().__init__(f"{status} {code}")
        self.status, self.code, self.names = status, code, names


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Following one would send the token to an address nobody stated.
        return None


def _open(request, timeout):
    return urllib.request.build_opener(_NoRedirect()).open(request, timeout=timeout)


def read_run(path: Path) -> dict:
    """The verification-run document at `path`, validated. Raises `PushError`."""
    path = Path(path)
    try:
        status = os.lstat(path)
        if not stat.S_ISREG(status.st_mode):
            raise PushError("the run is not a regular file")
        if status.st_size > MAX_DOCUMENT_BYTES:
            raise PushError("the run is larger than 5 MiB")
        document = json.loads(path.read_bytes())
    except OSError as exc:
        raise PushError(f"the run could not be read: {type(exc).__name__}") from None
    except (ValueError, RecursionError):
        raise PushError("the run is not JSON") from None
    if not isinstance(document, dict):
        raise PushError("the run is not a verification-run document")
    try:
        validate_document(document, verification_run.SCHEMA)
    except DocumentError as exc:
        raise PushError(f"the run is not a verification-run document: {exc}") from None
    return document


def endpoint(base_url: str) -> str:
    """The route under the graph's address. Raises `PushError` unless it is plain https."""
    try:
        parsed = urllib.parse.urlsplit(base_url or "")
        parsed.port  # noqa: B018 - reading it validates the port
    except ValueError:
        raise PushError(f"{URL_ENV} is not an address") from None
    if parsed.scheme != "https" or not parsed.hostname:
        raise PushError(f"{URL_ENV} must be an https:// address")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise PushError(f"{URL_ENV} must hold no credential, query or fragment")
    if any(c.isspace() or ord(c) < 32 for c in base_url):
        raise PushError(f"{URL_ENV} is not an address")
    return base_url.rstrip("/") + ROUTE


def _plain(value: object) -> str | None:
    """A bounded printable string, or None. Response text is never echoed as it came."""
    if not isinstance(value, str) or not value or len(value) > _NAME_MAX:
        return None
    return value if all(32 < ord(c) < 127 for c in value) else None


def _refusal(status: int, raw: bytes) -> Refused:
    """What an error body says, read as data. An unreadable body is still a refusal."""
    code, names = None, []
    try:
        body = json.loads(raw)
    except (ValueError, RecursionError):
        body = None
    if isinstance(body, dict):
        # Engine errors are `{"error": {...}}`; the role check answers `{"detail": {...}}`.
        for key in ("error", "detail"):
            held = body.get(key)
            if isinstance(held, dict):
                code = code or _plain(held.get("code"))
                details = held.get("details")
                if isinstance(details, dict):
                    for listed in ("requirement_ids", "differing_keys"):
                        found = details.get(listed)
                        if isinstance(found, list):
                            names += [name for name in map(_plain, found) if name]
    return Refused(status, code or "UNSPECIFIED", tuple(names[:_NAMED]))


def post(
    base_url: str,
    request: dict,
    *,
    token: str,
    timeout: float = TIMEOUT_SECONDS,
    opener: Callable[..., Any] | None = None,
) -> bool:
    """Post one run. True when the graph created it, False when it already held it.

    Raises `PushError` before anything is sent, `Refused` for the graph's
    refusal and `Unanswered` when it gave no usable answer. `opener` is the
    seam the tests drive.
    """
    url = endpoint(base_url)
    if not token or any(c.isspace() or not 32 < ord(c) < 127 for c in token):
        raise PushError(f"{TOKEN_ENV} is not a token")
    call = urllib.request.Request(  # noqa: S310 - scheme checked in endpoint()
        url,
        data=json.dumps(request).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "govkit-verification-run",
        },
    )
    try:
        with (opener or _open)(call, timeout=timeout) as response:
            status = response.status
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except urllib.error.HTTPError as answered:
        status = answered.code
        if 300 <= status < 400:
            raise Unanswered(
                f"the graph redirected the request ({status}); it was not followed"
            ) from None
        if status >= 500:
            raise Unanswered(f"the graph answered {status}") from None
        try:
            raw = answered.read(MAX_RESPONSE_BYTES + 1)
        except OSError:
            raw = b""
        raise _refusal(status, raw[:MAX_RESPONSE_BYTES]) from None
    except (urllib.error.URLError, TimeoutError, OSError) as silent:
        raise Unanswered(f"the graph could not be reached: {type(silent).__name__}") from None
    if status not in (200, 201) or len(raw) > MAX_RESPONSE_BYTES:
        raise Unanswered(f"the graph answered {status} with something that is not a stored run")
    try:
        stored = json.loads(raw)["data"]["run_reference"]
    except (ValueError, KeyError, TypeError, RecursionError):
        # A proxy's page is not the graph's answer.
        raise Unanswered("the graph's answer is not the published envelope") from None
    if stored != request["run_reference"]:
        raise Unanswered("the graph's answer names another run")
    return status == 201
