"""The bounded PDG client — increment 11.

Stdlib `urllib` on purpose. The installer's entire runtime surface is
`pyyaml`, and an open-source tool most adopters run without a PDG at all
should not gain an HTTP library so that a minority feature can make one GET.

Everything here is about the boundary, not the happy path: a timeout, a 404,
a 401, and a body that is not what the contract promises are all conditions
this has to turn into something the verdict layer can reason about.
"""

from __future__ import annotations

import json
import urllib.error

import pytest

from cli import pdg_client
from cli.authority_check import PdgUnreachable


def opener(status=200, body=None, raises=None):
    def _open(request, timeout=None):  # noqa: ANN001, ARG001
        if raises is not None:
            raise raises
        return _Response(status, body if body is not None else {"data": {}, "error": None})
    return _open


class _Response:
    def __init__(self, status, payload):
        self.status = status
        self._payload = json.dumps(payload).encode()

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


def fetch(**kwargs):
    # `pop`'s default is evaluated eagerly, so building the fallback inline
    # called `opener(opener=…)`. Chosen explicitly instead.
    send = kwargs.pop("opener", None) or opener(**kwargs)
    return pdg_client.fetch_status(
        "https://pdg.example.invalid", "cmt-1", token="s3cret", timeout=5, opener=send,
    )


def test_a_successful_read_returns_the_envelope_data():
    payload = {"data": {"commitment_id": "cmt-1", "authorizes_work": True}, "error": None}

    assert fetch(opener=opener(body=payload))["commitment_id"] == "cmt-1"


def test_a_timeout_is_unreachable_rather_than_an_answer():
    with pytest.raises(PdgUnreachable) as raised:
        fetch(opener=opener(raises=TimeoutError("timed out")))

    assert "timed out" in str(raised.value)


def test_a_connection_failure_is_unreachable():
    with pytest.raises(PdgUnreachable):
        fetch(opener=opener(raises=urllib.error.URLError("name resolution failed")))


def test_a_server_error_is_unreachable_rather_than_a_rejection():
    """A 500 says the PDG is unwell, not that authority is absent. Reading it
    as rejection would send someone to repair an approval over an outage."""
    with pytest.raises(PdgUnreachable):
        fetch(opener=opener(raises=urllib.error.HTTPError(
            "u", 503, "unavailable", {}, None)))


def test_an_authentication_failure_is_unreachable_not_unauthorized():
    """401 is about *this checker's* credentials, not about the commitment.
    Calling it "not authorized" would be a true sentence about the wrong
    subject, and would send someone to re-approve a baseline when the real
    fix is a token."""
    with pytest.raises(PdgUnreachable) as raised:
        fetch(opener=opener(raises=urllib.error.HTTPError("u", 401, "no", {}, None)))

    assert "credential" in str(raised.value).lower()


def test_a_missing_commitment_is_an_answer_not_an_outage():
    """404 means the PDG looked and found nothing. That is a real answer
    about authority and must not be laundered into "unreachable"."""
    result = fetch(opener=opener(raises=urllib.error.HTTPError("u", 404, "nf", {}, None)))

    assert result is None


def test_an_unreadable_body_is_unreachable():
    def _open(request, timeout=None):  # noqa: ANN001, ARG001
        return _Raw(b"<html>a proxy error page</html>")

    with pytest.raises(PdgUnreachable):
        pdg_client.fetch_status("https://pdg.example.invalid", "cmt-1", token="t",
                                timeout=5, opener=_open)


class _Raw:
    def __init__(self, raw):
        self.status = 200
        self._raw = raw

    def read(self):
        return self._raw

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


def test_the_token_is_sent_as_a_bearer_header_and_not_in_the_url():
    seen = {}

    def _open(request, timeout=None):  # noqa: ANN001, ARG001
        seen["url"] = request.full_url
        seen["auth"] = request.get_header("Authorization")
        return _Response(200, {"data": {"commitment_id": "cmt-1"}, "error": None})

    pdg_client.fetch_status("https://pdg.example.invalid", "cmt-1", token="s3cret",
                            timeout=5, opener=_open)

    assert seen["auth"] == "Bearer s3cret"
    assert "s3cret" not in seen["url"], "a token in a URL lands in every access log"


def test_a_non_https_base_url_is_refused():
    """The token is a read-only verification credential and still a
    credential. Sending it in clear is not a choice this should make quietly."""
    with pytest.raises(ValueError, match="https"):
        pdg_client.fetch_status("http://pdg.example.invalid", "cmt-1", token="t",
                                timeout=5, opener=opener())
