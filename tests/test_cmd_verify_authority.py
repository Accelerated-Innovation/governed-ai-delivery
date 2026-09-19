"""`govkit verify-authority` — increment 11's command surface.

The state that matters most is the one an open-source adopter is in:
**no PDG at all**. That must not be a failure, a warning, or a degraded
mode — the check simply does not apply, and everything local still works.

Conflating "no PDG" with "PDG unreachable" is the bug this is shaped to
avoid, and it fails in both directions: spurious failures for adopters who
never had a PDG, or silent passes for AIPOS projects whose engine is down.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json

import pytest

from cli import cmd_verify_authority

DIGEST = "sha256:" + "f" * 64


@pytest.fixture
def project(tmp_path):
    (tmp_path / ".govkit").mkdir()
    (tmp_path / ".govkit" / "marker.json").write_text(json.dumps({
        "version": "0.20.0", "level": "4", "agent": "claude-code",
        "options": {"type": "api", "ci": "github", "stack": "python-fastapi"},
    }), encoding="utf-8")
    (tmp_path / "baseline.json").write_text(json.dumps({
        "version": 1,
        "commitment_key": "k",
        "opportunity": {"opportunity_ref": "PDG-OPP-4471"},
        "sources": [{"source_key": "app", "repository": "https://x.invalid",
                     "revision": "1" * 40, "path": "features", "kind": "repository"}],
        "selected_behavior": [{"ref": "app/f#scenario:s", "kind": "scenario",
                               "id_source": "tag", "content_digest": DIGEST}],
    }), encoding="utf-8")
    return tmp_path


def enable_pdg(project, **extra):
    marker = json.loads((project / ".govkit" / "marker.json").read_text())
    marker["authority"] = {"source": "pdg", "base_url": "https://pdg.example.invalid",
                           "contract_version": 1, **extra}
    (project / ".govkit" / "marker.json").write_text(json.dumps(marker), encoding="utf-8")


def run(project, enforce=False, commitment=None, monkeypatch=None, status=None,
        unreachable=None, token="s3cret-value"):
    if monkeypatch is not None:
        # A credential by default: most cases are about the *answer*, and
        # leaving it unset would make every one of them fail as "undetermined,
        # no credential" for a reason the test is not about.
        if token is None:
            monkeypatch.delenv(cmd_verify_authority.TOKEN_ENV, raising=False)
        else:
            monkeypatch.setenv(cmd_verify_authority.TOKEN_ENV, token)
        from cli import authority_check

        def fake(_base, cid, **_kw):
            if unreachable:
                raise authority_check.PdgUnreachable(unreachable)
            return status
        monkeypatch.setattr(cmd_verify_authority.pdg_client, "fetch_status", fake)

    args = argparse.Namespace(
        target=str(project), baseline=str(project / "baseline.json"),
        enforce=enforce, commitment=commitment,
    )
    out = io.StringIO()
    code = 0
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        try:
            cmd_verify_authority.cmd_verify_authority(args)
        except SystemExit as exit_:
            code = exit_.code or 0
    return code, out.getvalue()


# --- the open-source path -----------------------------------------------------

def test_a_project_with_no_pdg_reports_not_applicable_and_exits_zero(project):
    """The default, and the state most adopters of this tool are in. Not a
    failure, not a warning — the question does not arise."""
    code, output = run(project)

    assert code == 0
    assert "not applicable" in output.lower()


def test_a_project_with_no_pdg_exits_zero_even_when_enforcing(project):
    """A CI pipeline that runs the enforced check on a project without a PDG
    must not fail. Enforcement raises the stakes of an *answer*; it cannot
    invent a question."""
    code, _ = run(project, enforce=True)

    assert code == 0


def test_no_pdg_is_distinguishable_from_an_unreachable_pdg(project, monkeypatch):
    absent_code, absent = run(project)
    enable_pdg(project)
    down_code, down = run(project, enforce=True, commitment="cmt-1",
                          monkeypatch=monkeypatch, unreachable="connection refused")

    assert absent_code == 0 and down_code == 1
    assert "not applicable" in absent.lower()
    assert "not applicable" not in down.lower()


# --- with a PDG configured ----------------------------------------------------

def _authorizing():
    return {"commitment_id": "cmt-1", "opportunity_ref": "PDG-OPP-4471",
            "baseline_digest": DIGEST, "source_scope": "app",
            "source_revision": "1" * 40, "consequence_class": "standard",
            "status": "authorizing", "authorizes_work": True, "reason": None,
            "schema_version": 1}


def test_a_current_approval_passes_the_enforced_gate(project, monkeypatch):
    enable_pdg(project)

    code, output = run(project, enforce=True, commitment="cmt-1",
                       monkeypatch=monkeypatch, status=_authorizing())

    assert code == 0, output


def test_an_invalidated_approval_fails_the_enforced_gate(project, monkeypatch):
    enable_pdg(project)
    invalidated = {**_authorizing(), "authorizes_work": False,
                   "status": "invalidated", "reason": "COMMITMENT_INVALIDATED"}

    code, output = run(project, enforce=True, commitment="cmt-1",
                       monkeypatch=monkeypatch, status=invalidated)

    assert code == 1
    assert "COMMITMENT_INVALIDATED" in output


def test_an_unreachable_pdg_fails_the_enforced_gate(project, monkeypatch):
    """Fail closed. A gate that passes when the PDG is unreachable is not a
    gate."""
    enable_pdg(project)

    code, output = run(project, enforce=True, commitment="cmt-1",
                       monkeypatch=monkeypatch, unreachable="connection refused")

    assert code == 1
    assert "could not" in output.lower() or "unknown" in output.lower()


def test_an_unreachable_pdg_does_not_fail_the_advisory_check(project, monkeypatch):
    """Local drafting reports and continues, which is what lets someone work
    on a train."""
    enable_pdg(project)

    code, output = run(project, enforce=False, commitment="cmt-1",
                       monkeypatch=monkeypatch, unreachable="connection refused")

    assert code == 0
    assert "unverified" in output.lower() or "unknown" in output.lower()


def test_the_token_comes_from_the_environment_and_is_never_printed(project, monkeypatch):
    enable_pdg(project)

    _code, output = run(project, enforce=True, commitment="cmt-1",
                        monkeypatch=monkeypatch, status=_authorizing(),
                        token="s3cret-value")

    assert "s3cret-value" not in output


def test_a_missing_token_is_undetermined_rather_than_unauthorized(project, monkeypatch):
    """No credential means the question could not be asked. Reporting it as
    rejection would send someone to re-approve a baseline that is fine."""
    enable_pdg(project)

    code, output = run(project, enforce=True, commitment="cmt-1",
                       monkeypatch=monkeypatch, token=None)

    assert code == 1
    assert "token" in output.lower() or "credential" in output.lower()
    assert "not authorized" not in output.lower()
