"""`govkit verify-contract` — the command both CI providers call (13A).

A checker with no caller is dead code whose guarantees never run; that was
recorded as a deliberate deviation once already, in increment 08A, and it is
not repeated here. This is the seam the templates invoke, so the exit codes
and the refusals are the contract, not the internals.

The rules it has to get right are the ones increments 10 and 11 established
and which a second implementation would quietly lose:

- **Not applicable is not a pass**, and it is not a failure either, unless
  the caller asserted otherwise with `--require-authority`.
- **No credential is undetermined**, never rejection.
- **The endpoint never comes from the repository.**
"""

from __future__ import annotations

import json

import pytest

from cli.cmd_verify_contract import cmd_verify_contract


class Args:
    def __init__(self, target, **kw):
        self.target = str(target)
        self.enforce = kw.get("enforce", False)
        self.require_authority = kw.get("require_authority", False)


@pytest.fixture
def marked(tmp_path):
    def make(source="pdg"):
        (tmp_path / ".govkit").mkdir(exist_ok=True)
        marker = {
            "version": "0.21.0", "level": "4", "agent": "claude-code",
            "options": {"type": "api", "ci": "github", "stack": "python-fastapi"},
        }
        if source is not None:
            marker["authority"] = {"source": source}
        (tmp_path / ".govkit" / "marker.json").write_text(json.dumps(marker), encoding="utf-8")
        return tmp_path
    return make


def run(args) -> int:
    with pytest.raises(SystemExit) as exit_info:
        cmd_verify_contract(args)
    return exit_info.value.code


def test_a_project_without_a_pdg_is_not_applicable_and_exits_zero(marked, capsys):
    """The default. Most projects using GovKit have no PDG, and telling them
    they failed a gate they never adopted is how a governance feature gets
    deleted."""
    code = run(Args(marked("none"), enforce=True))

    assert code == 0
    assert "not applicable" in capsys.readouterr().out.lower()


def test_an_absent_authority_block_reads_the_same_as_none(marked, capsys):
    code = run(Args(marked(None), enforce=True))

    assert code == 0
    assert "not applicable" in capsys.readouterr().out.lower()


def test_require_authority_turns_not_applicable_into_a_failure(marked, capsys):
    """Without it the gate reads its own applicability out of the tree it is
    gating: a pull request removing `authority.source` turns the check into
    "not applicable" and the gate green."""
    code = run(Args(marked("none"), enforce=True, require_authority=True))

    assert code == 1


def test_a_missing_endpoint_is_a_configuration_error_not_a_verdict(marked, monkeypatch, capsys):
    monkeypatch.delenv("GOVKIT_PDG_URL", raising=False)
    monkeypatch.delenv("GOVKIT_PDG_TOKEN", raising=False)

    code = run(Args(marked("pdg"), enforce=True))

    assert code == 2
    assert "GOVKIT_PDG_URL" in capsys.readouterr().err


def test_the_endpoint_is_never_read_from_the_repository(marked, monkeypatch, capsys):
    """An endpoint from the working tree paired with a credential from the
    environment is how a pull request collects the token. Putting one in the
    marker must change nothing."""
    target = marked("pdg")
    marker_path = target / ".govkit" / "marker.json"
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    marker["authority"]["url"] = "https://attacker.invalid"
    marker_path.write_text(json.dumps(marker), encoding="utf-8")
    monkeypatch.delenv("GOVKIT_PDG_URL", raising=False)

    code = run(Args(target, enforce=True))

    assert code == 2
    assert "attacker.invalid" not in capsys.readouterr().err


def test_no_credential_is_undetermined_and_fails_closed_when_enforced(
    marked, monkeypatch, capsys
):
    """Undetermined, not rejection — the question could not be asked. It
    still fails an enforced gate, because a gate that passes when it cannot
    ask is not a gate."""
    monkeypatch.setenv("GOVKIT_PDG_URL", "https://pdg.invalid")
    monkeypatch.delenv("GOVKIT_PDG_TOKEN", raising=False)
    target = marked("pdg")
    _add_commitment(target)

    code = run(Args(target, enforce=True, require_authority=True))
    out = capsys.readouterr().out.lower()

    assert code == 1
    assert "unverified" in out
    assert "not authorized" not in out, "a missing token is not a withdrawn approval"


def test_the_same_state_advises_rather_than_blocks_without_enforce(
    marked, monkeypatch, capsys
):
    monkeypatch.setenv("GOVKIT_PDG_URL", "https://pdg.invalid")
    monkeypatch.delenv("GOVKIT_PDG_TOKEN", raising=False)
    target = marked("pdg")
    _add_commitment(target)

    assert run(Args(target, enforce=False, require_authority=True)) == 0


def test_a_pdg_project_with_no_commitments_fails_an_enforced_gate(
    marked, monkeypatch, capsys
):
    """Green because nothing was configured is indistinguishable from green
    because the behavior was approved."""
    monkeypatch.setenv("GOVKIT_PDG_URL", "https://pdg.invalid")
    monkeypatch.setenv("GOVKIT_PDG_TOKEN", "read-only")

    code = run(Args(marked("pdg"), enforce=True, require_authority=True))

    assert code == 1
    assert "no commitment" in capsys.readouterr().out.lower()


def _add_commitment(target, key="support-response-approval"):
    package = target / "commitments" / key
    package.mkdir(parents=True, exist_ok=True)
    (package / "baseline.json").write_text(json.dumps({
        "version": 1,
        "commitment_key": key,
        "opportunity": {"opportunity_ref": "OPP-1", "outcome": "x"},
        "sources": [{
            "source_key": "app", "repository": "https://example.invalid/a",
            "revision": "0" * 40, "path": "features", "kind": "repository",
        }],
        "selected_behavior": [{
            "ref": "app/f#scenario:s", "kind": "scenario", "id_source": "tag",
        }],
    }), encoding="utf-8")


def test_the_command_is_registered_on_the_real_cli():
    """A command nobody can invoke is the dead-code failure recorded in 08A."""
    import argparse

    from cli.cmd_verify_contract import register

    parser = argparse.ArgumentParser()
    register(parser.add_subparsers(dest="command"))
    args = parser.parse_args(["verify-contract", "--target", ".", "--enforce"])

    assert args.enforce is True
