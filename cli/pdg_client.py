"""A bounded read-only client for the PDG's commitment status — increment 11.

**Stdlib `urllib`, deliberately.** The installer's entire runtime surface is
`pyyaml`. Most adopters of this open-source tool have no PDG at all, and
making every one of them carry an HTTP library so a minority feature can
issue one GET is the wrong trade.

**Read-only by construction.** One GET, no other verb reachable from here.
The credential is a verification credential, and installing a checker must
not hand anything the authority to *make* an approval.

The distinctions this module exists to draw are all about what a failure
*means*:

- **404 is an answer.** The PDG looked and found nothing. Laundering that
  into "unreachable" would turn a definite absence of authority into a
  maybe.
- **401 is not about the commitment.** It is about this checker's
  credentials, and calling it "not authorized" would be a true sentence
  about the wrong subject — sending someone to re-approve a baseline when
  the fix is a token.
- **5xx, timeouts and unreadable bodies are outages.** A proxy error page is
  not a verdict.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from typing import Any

from cli.authority_check import PdgUnreachable

#: Short on purpose. This runs at a protected boundary, and a check that
#: hangs is a build that hangs; an outage should be reported quickly rather
#: than waited out.
DEFAULT_TIMEOUT_SECONDS = 10


def fetch_status(
    base_url: str,
    commitment_id: str,
    *,
    token: str,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    opener: Callable[..., Any] | None = None,
) -> dict | None:
    """The commitment's current status, or None if the PDG has no such record.

    Raises `PdgUnreachable` when the answer could not be obtained at all.
    `opener` is the seam the tests drive; production uses `urlopen`.
    """
    parsed = urllib.parse.urlparse(base_url)
    if parsed.scheme != "https":
        # The token is read-only and still a credential. Sending it in clear
        # is not a decision this should make on a caller's behalf.
        raise ValueError(
            f"the PDG base URL must be https, got {parsed.scheme or 'no scheme'!r}"
        )

    url = f"{base_url.rstrip('/')}/v1/commitments/{urllib.parse.quote(commitment_id)}"
    request = urllib.request.Request(  # noqa: S310 - scheme checked above
        url,
        method="GET",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )

    send = opener or urllib.request.urlopen
    try:
        with send(request, timeout=timeout) as response:
            raw = response.read()
    except urllib.error.HTTPError as http_error:
        if http_error.code == 404:
            return None
        if http_error.code in (401, 403):
            raise PdgUnreachable(
                f"the PDG refused this checker's credential ({http_error.code}); "
                f"authority could not be read"
            ) from http_error
        raise PdgUnreachable(
            f"the PDG answered {http_error.code}"
        ) from http_error
    except (urllib.error.URLError, TimeoutError, OSError) as unreachable:
        raise PdgUnreachable(str(unreachable)) from unreachable

    try:
        envelope = json.loads(raw)
        data = envelope["data"]
    except (ValueError, KeyError, TypeError) as unreadable:
        # A proxy error page is not a verdict.
        raise PdgUnreachable(
            f"the PDG answered something that is not the published envelope: {unreadable}"
        ) from unreadable
    return data
