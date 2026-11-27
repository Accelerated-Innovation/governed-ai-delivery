"""`govkit verification-run push`: one explicit write to the Product Definition Graph.

The tests drive the client through its `opener` seam. No test opens a
connection, and nothing here shows that a real graph accepts a run.
"""

import http.client
import io
import json
import urllib.error
from pathlib import Path

import pytest

from cli import paths
from cli import verification_push as vp

EXAMPLE = paths.GOVERNANCE_DIR / "examples" / "verification-run" / "verification-run.json"
URL = "https://graph.example.invalid"
TOKEN = "service-token-value"


def _document() -> dict:
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


class _Response:
    def __init__(self, status: int, body) -> None:
        self.status = status
        self._body = body if isinstance(body, bytes) else json.dumps(body).encode()

    def read(self, limit=-1):
        return self._body if limit < 0 else self._body[:limit]

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _Truncated(_Response):
    """A response whose body ends early, as a closed chunked response does."""

    def read(self, limit=-1):
        raise http.client.IncompleteRead(b"{")


class _Graph:
    """Stands in for the graph: records the call and answers as told."""

    def __init__(self, status=201, body=None, raises=None) -> None:
        self.status, self.body, self.raises, self.calls = status, body, raises, []

    def __call__(self, request, timeout):
        self.calls.append(request)
        if self.raises is not None:
            raise self.raises
        if self.status >= 300:
            raise urllib.error.HTTPError(
                request.full_url,
                self.status,
                "refused",
                {},
                io.BytesIO(json.dumps(self.body).encode()),
            )
        sent = json.loads(request.data)
        body = self.body if self.body is not None else {"data": {**sent, "schema_version": 1}}
        return _Response(self.status, body)


def _post(graph, request=None, url=URL, token=TOKEN):
    return vp.post(url, request or _document()["request"], token=token, opener=graph)


class TestPost:
    def test_the_request_is_posted_as_built_with_the_service_token(self):
        graph = _Graph()
        assert _post(graph) is True
        (call,) = graph.calls
        assert call.full_url == URL + "/v1/verification-runs"
        assert call.get_method() == "POST"
        assert json.loads(call.data) == _document()["request"]
        assert call.get_header("Authorization") == f"Bearer {TOKEN}"
        assert call.get_header("Content-type") == "application/json"

    def test_a_run_the_graph_already_holds_is_not_an_error(self):
        assert _post(_Graph(status=200)) is False

    def test_a_trailing_slash_in_the_address_is_dropped(self):
        graph = _Graph()
        _post(graph, url=URL + "/")
        assert graph.calls[0].full_url == URL + "/v1/verification-runs"

    @pytest.mark.parametrize(
        "status, body, code, names",
        [
            (404, {"error": {"code": "REQUIREMENT_NOT_FOUND", "details": {"requirement_ids": ["f#scenario:a"]}}}, "REQUIREMENT_NOT_FOUND", ("f#scenario:a",)),
            (409, {"error": {"code": "VERIFICATION_RUN_CONFLICT", "details": {"differing_keys": ["results"]}}}, "VERIFICATION_RUN_CONFLICT", ("results",)),
            (422, {"error": {"code": "VERIFICATION_REVISION_MISMATCH", "details": {"requirement_ids": ["f#scenario:a", "f#scenario:b"]}}}, "VERIFICATION_REVISION_MISMATCH", ("f#scenario:a", "f#scenario:b")),
            (413, {"error": {"code": "PAYLOAD_TOO_LARGE", "details": {"count": 6000}}}, "PAYLOAD_TOO_LARGE", ()),
            (403, {"detail": {"code": "INSUFFICIENT_SCOPE", "message": "Role 'service' required"}}, "INSUFFICIENT_SCOPE", ()),
            (401, {"detail": {"code": "INVALID_TOKEN"}}, "INVALID_TOKEN", ()),
            (400, "<html>proxy</html>", "UNSPECIFIED", ()),
        ],
    )  # fmt: skip
    def test_a_refusal_names_its_code_and_what_the_graph_named(self, status, body, code, names):
        with pytest.raises(vp.Refused) as refused:
            _post(_Graph(status=status, body=body))
        assert (refused.value.status, refused.value.code, refused.value.names) == (
            status, code, names,
        )  # fmt: skip

    def test_text_from_a_refusal_is_never_passed_on_as_it_came(self):
        body = {
            "error": {
                "code": "X\x1b[31m",
                "message": "secret detail",
                "details": {"requirement_ids": ["ok#scenario:a", "two words", 7, "a" * 201, "é"]},
            }
        }
        with pytest.raises(vp.Refused) as refused:
            _post(_Graph(status=422, body=body))
        assert refused.value.code == "UNSPECIFIED"
        assert refused.value.names == ("ok#scenario:a",)
        assert "secret" not in str(refused.value)

    def test_a_long_list_of_names_is_cut(self):
        ids = [f"f#scenario:s{n}" for n in range(500)]
        body = {"error": {"code": "REQUIREMENT_NOT_FOUND", "details": {"requirement_ids": ids}}}
        with pytest.raises(vp.Refused) as refused:
            _post(_Graph(status=404, body=body))
        assert len(refused.value.names) == 20

    @pytest.mark.parametrize("status", [500, 502, 503, 301, 302, 307, 308])
    def test_an_outage_or_a_redirect_is_no_answer(self, status):
        with pytest.raises(vp.Unanswered):
            _post(_Graph(status=status, body={}))

    @pytest.mark.parametrize(
        "error", [urllib.error.URLError("down"), TimeoutError(), ConnectionResetError()]
    )
    def test_a_graph_that_cannot_be_reached_is_no_answer(self, error):
        with pytest.raises(vp.Unanswered) as silent:
            _post(_Graph(raises=error))
        assert "down" not in str(silent.value)

    @pytest.mark.parametrize(
        "status, body",
        [
            (201, b"<html>signed in</html>"),
            (200, {"data": None}),
            (201, {"data": {"run_reference": "github:other"}}),
            (204, {}),
            (201, b"x" * (vp.MAX_RESPONSE_BYTES + 5)),
        ],
    )
    def test_a_success_that_is_not_the_stored_run_is_no_answer(self, status, body):
        with pytest.raises(vp.Unanswered):
            _post(_Graph(status=status, body=body))

    @pytest.mark.parametrize(
        "url",
        [
            "http://graph.example.invalid",
            "graph.example.invalid",
            "",
            "https://user:pw@graph.example.invalid",
            "https://graph.example.invalid?x=1",
            "https://graph.example.invalid#x",
            "https://graph.example.invalid:port",
            "https://graph.example.invalid/a b",
            "file:///etc/passwd",
        ],
    )
    def test_an_address_that_is_not_plain_https_sends_nothing(self, url):
        graph = _Graph()
        with pytest.raises(vp.PushError):
            _post(graph, url=url)
        assert graph.calls == []

    @pytest.mark.parametrize("token", ["", "two words", "line\nInjected: 1", "tab\t"])
    def test_a_token_that_could_break_the_header_sends_nothing(self, token):
        graph = _Graph()
        with pytest.raises(vp.PushError):
            _post(graph, token=token)
        assert graph.calls == []

    def test_a_success_cut_short_is_no_answer(self):
        def graph(request, timeout):
            return _Truncated(201, {})

        with pytest.raises(vp.Unanswered):
            _post(graph)

    @pytest.mark.parametrize(
        "error", [http.client.RemoteDisconnected("gone"), http.client.BadStatusLine("x")]
    )
    def test_a_broken_exchange_is_no_answer(self, error):
        with pytest.raises(vp.Unanswered):
            _post(_Graph(raises=error))

    def test_a_refusal_whose_body_is_cut_short_is_still_a_refusal(self):
        class Body(io.BytesIO):
            def read(self, *args):
                raise http.client.IncompleteRead(b"{")

        def graph(request, timeout):
            raise urllib.error.HTTPError(request.full_url, 422, "refused", {}, Body())

        with pytest.raises(vp.Refused) as refused:
            _post(graph)
        assert (refused.value.status, refused.value.code) == (422, "UNSPECIFIED")

    @pytest.mark.parametrize(
        "name",
        [
            "::warning::graph-controlled",
            "f#scenario:a::error::x",
            "##vso[task.complete]",
            "##[error]x",
            "a=b",
            "a,b",
            "a%0Ab",
        ],
    )
    def test_a_name_that_could_be_a_log_command_is_dropped(self, name):
        body = {
            "error": {
                "code": name,
                "details": {"requirement_ids": [name, "07_f#scenario:ok-1", "f#evaluation:a_b.c"]},
            }
        }
        with pytest.raises(vp.Refused) as refused:
            _post(_Graph(status=404, body=body))
        assert refused.value.code == "UNSPECIFIED"
        assert refused.value.names == ("07_f#scenario:ok-1", "f#evaluation:a_b.c")

    def test_the_default_opener_does_not_follow_a_redirect(self):
        handler = vp._NoRedirect()
        assert (
            handler.redirect_request(None, None, 307, "", {}, "https://elsewhere.invalid") is None
        )


class TestReadRun:
    def test_the_bundled_example_is_read(self, tmp_path):
        path = tmp_path / "run.json"
        path.write_bytes(EXAMPLE.read_bytes())
        assert vp.read_run(path) == _document()

    @pytest.mark.parametrize(
        "content",
        [b"not json", b"[]", b"{}", json.dumps({"request": {"run_reference": "x"}}).encode()],
    )
    def test_anything_else_is_refused(self, tmp_path, content):
        path = tmp_path / "run.json"
        path.write_bytes(content)
        with pytest.raises(vp.PushError):
            vp.read_run(path)

    def test_a_request_with_a_key_the_graph_does_not_accept_is_refused(self, tmp_path):
        document = _document()
        document["request"]["results"][0]["title"] = "A scenario title"
        path = tmp_path / "run.json"
        path.write_text(json.dumps(document), encoding="utf-8")
        with pytest.raises(vp.PushError):
            vp.read_run(path)

    def test_a_missing_file_a_link_and_a_large_file_are_refused(self, tmp_path):
        real = tmp_path / "run.json"
        real.write_bytes(EXAMPLE.read_bytes())
        link = tmp_path / "link.json"
        link.symlink_to(real)
        large = tmp_path / "large.json"
        large.write_bytes(b" " * (vp.MAX_DOCUMENT_BYTES + 1))
        for path in (tmp_path / "none.json", link, large, tmp_path):
            with pytest.raises(vp.PushError):
                vp.read_run(path)


def _run(monkeypatch, capsys, path: Path, graph=None, url=URL, token=TOKEN):
    from cli import govkit

    for name, value in ((vp.URL_ENV, url), (vp.TOKEN_ENV, token)):
        if value is None:
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, value)
    graph = graph or _Graph()
    monkeypatch.setattr(vp, "_open", graph)
    monkeypatch.setattr("sys.argv", ["govkit", "verification-run", "push", "--run", str(path)])
    with pytest.raises(SystemExit) as stopped:
        govkit.main()
    captured = capsys.readouterr()
    return stopped.value.code, captured.out, captured.err, graph


@pytest.fixture
def run(tmp_path) -> Path:
    path = tmp_path / "run.json"
    path.write_bytes(EXAMPLE.read_bytes())
    return path


class TestCommand:
    def test_a_recorded_run_exits_0(self, run, monkeypatch, capsys):
        code, out, _, graph = _run(monkeypatch, capsys, run)
        assert code == 0 and len(graph.calls) == 1
        assert "recorded run github:1234567890-1 with 3 result(s)" in out

    def test_a_run_already_held_exits_0(self, run, monkeypatch, capsys):
        code, out, _, _ = _run(monkeypatch, capsys, run, _Graph(status=200))
        assert code == 0 and "already held" in out

    def test_only_the_request_is_sent(self, run, monkeypatch, capsys):
        _, _, _, graph = _run(monkeypatch, capsys, run)
        sent = graph.calls[0].data.decode()
        assert json.loads(sent) == _document()["request"]
        assert "left_out" not in sent and "no-result" not in sent

    def test_nothing_to_send_passes_and_sends_nothing(self, run, monkeypatch, capsys):
        document = _document()
        document["request"] = None
        document["summary"]["sent"] = 0
        run.write_text(json.dumps(document), encoding="utf-8")
        # Even with no address or token: there is nothing to configure a send for.
        code, out, _, graph = _run(monkeypatch, capsys, run, url=None, token=None)
        assert code == 0 and graph.calls == []
        assert "Nothing was sent to the graph." in out and "left out: no-result" in out

    def test_a_refusal_exits_1_and_names_what_the_graph_named(self, run, monkeypatch, capsys):
        body = {
            "error": {
                "code": "VERIFICATION_REVISION_MISMATCH",
                "message": "private text",
                "details": {"requirement_ids": ["07_invoice_approval#scenario:x"]},
            }
        }
        code, out, err, _ = _run(monkeypatch, capsys, run, _Graph(status=422, body=body))
        assert code == 1 and out == ""
        assert "422 VERIFICATION_REVISION_MISMATCH" in err
        assert "07_invoice_approval#scenario:x" in err and "private text" not in err

    def test_no_answer_exits_3(self, run, monkeypatch, capsys):
        code, _, err, _ = _run(monkeypatch, capsys, run, _Graph(status=503, body={}))
        assert code == 3 and "sending the same run again is safe" in err

    @pytest.mark.parametrize("missing", ["url", "token"])
    def test_without_an_address_or_a_token_nothing_is_sent(self, run, monkeypatch, capsys, missing):
        code, _, err, graph = _run(monkeypatch, capsys, run, **{missing: None})
        assert code == 2 and graph.calls == []
        assert vp.URL_ENV in err and vp.TOKEN_ENV in err

    def test_a_file_that_is_not_a_run_exits_2(self, run, monkeypatch, capsys):
        run.write_text("{}", encoding="utf-8")
        code, _, _, graph = _run(monkeypatch, capsys, run)
        assert code == 2 and graph.calls == []

    def test_the_token_is_never_printed(self, run, monkeypatch, capsys):
        for graph in (_Graph(), _Graph(status=403, body={}), _Graph(status=500, body={})):
            _, out, err, _ = _run(monkeypatch, capsys, run, graph)
            assert TOKEN not in out + err

    def test_the_token_is_not_the_read_only_credential(self):
        from cli import cmd_verify_authority

        assert vp.TOKEN_ENV != cmd_verify_authority.TOKEN_ENV
        assert vp.URL_ENV == cmd_verify_authority.URL_ENV
