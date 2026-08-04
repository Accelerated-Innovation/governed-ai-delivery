"""Regression tests for the govkit CLI registry dispatch (cli/govkit.py).

main() builds the parser by looping _REGISTRARS, each of which binds its handler
via set_defaults(func=...); main() then calls args.func(args). These tests guard
that wiring: every subcommand must route to its own handler, and an unparseable
invocation must exit non-zero. They patch the module-level handler each register
reads, so no real command logic runs.
"""

import sys

import pytest

from cli import govkit

# (argv, module_path, handler_attr) — the handler each invocation must reach.
DISPATCH_CASES = [
    (["govkit", "apply", "--agent", "claude-code", "--target", "."], "cli.cmd_apply", "cmd_apply"),
    (["govkit", "list"], "cli.cmd_list", "cmd_list"),
    (["govkit", "stack", "list"], "cli.cmd_stack", "cmd_stack_list"),
    (["govkit", "stack", "apply", "python-fastapi", "--target", "."], "cli.cmd_stack", "cmd_stack_apply"),
    (["govkit", "init", "feat", "--target", "."], "cli.cmd_init", "cmd_init"),
    (["govkit", "validate", "--target", "."], "cli.cmd_validate", "cmd_validate"),
    (["govkit", "upgrade", "--target", "."], "cli.cmd_upgrade", "cmd_upgrade"),
    (["govkit", "doctor"], "cli.doctor", "cmd_doctor"),
    (["govkit", "calibrate"], "cli.calibrate", "cmd_calibrate"),
]


@pytest.mark.parametrize("argv, module_path, handler_attr", DISPATCH_CASES)
def test_main_dispatches_to_handler(argv, module_path, handler_attr, monkeypatch):
    calls: list[str] = []
    # register() reads the handler from its module's globals when it runs (inside
    # main()), so patching the module attribute redirects set_defaults(func=...).
    monkeypatch.setattr(f"{module_path}.{handler_attr}", lambda args: calls.append(handler_attr))
    monkeypatch.setattr(sys, "argv", argv)

    govkit.main()

    assert calls == [handler_attr]


def test_apply_args_reach_handler(monkeypatch):
    """The parsed Namespace (not just the right handler) is threaded through."""
    captured = {}
    monkeypatch.setattr("cli.cmd_apply.cmd_apply", lambda args: captured.update(vars(args)))
    monkeypatch.setattr(
        sys, "argv",
        ["govkit", "apply", "--agent", "copilot", "--target", "/tmp/x", "--level", "4", "--type", "data"],
    )

    govkit.main()

    assert captured["agent"] == "copilot"
    assert captured["level"] == "4"
    assert captured["type"] == "data"


def test_no_command_exits_nonzero(monkeypatch):
    """Subparsers are required — bare `govkit` must error out, not no-op."""
    monkeypatch.setattr(sys, "argv", ["govkit"])
    with pytest.raises(SystemExit) as exc:
        govkit.main()
    assert exc.value.code != 0


def test_unknown_command_exits_nonzero(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["govkit", "bogus"])
    with pytest.raises(SystemExit) as exc:
        govkit.main()
    assert exc.value.code != 0


# ---------------------------------------------------------------------------
# --version — #123
# ---------------------------------------------------------------------------

class TestVersionFlag:
    """`govkit --version` prints the installed version and exits cleanly.

    The subparser is declared `required=True`, so a bare `govkit` is an
    error. `--version` has to resolve before that check — argparse fires a
    `version` action during parsing and exits — and this pins it, because
    getting it wrong turns `govkit --version` into a usage error rather than
    an answer.
    """

    def _run(self, monkeypatch, capsys, argv):
        import pytest as _pytest

        monkeypatch.setattr(sys, "argv", argv)
        with _pytest.raises(SystemExit) as exc:
            govkit.main()
        return exc.value.code, capsys.readouterr()

    def test_version_flag_exits_zero(self, monkeypatch, capsys):
        code, _ = self._run(monkeypatch, capsys, ["govkit", "--version"])
        assert code == 0

    def test_version_flag_prints_the_installed_version(self, monkeypatch, capsys):
        from cli.version import GOVKIT_VERSION

        _code, out = self._run(monkeypatch, capsys, ["govkit", "--version"])
        assert GOVKIT_VERSION in (out.out + out.err)

    def test_version_output_names_the_program(self, monkeypatch, capsys):
        _code, out = self._run(monkeypatch, capsys, ["govkit", "--version"])
        assert (out.out + out.err).strip().startswith("govkit ")

    def test_version_needs_no_subcommand(self, monkeypatch, capsys):
        """A bare `govkit` is a usage error; `govkit --version` must not be.
        Same reason: the version action has to win over the required
        subparser."""
        import pytest as _pytest

        monkeypatch.setattr(sys, "argv", ["govkit"])
        with _pytest.raises(SystemExit) as bare:
            govkit.main()
        assert bare.value.code != 0

        code, _ = self._run(monkeypatch, capsys, ["govkit", "--version"])
        assert code == 0

    def test_it_reports_the_same_number_the_marker_records(self, monkeypatch, capsys):
        """One number, not two. `--version` is what a user quotes in a bug
        report; the marker and `upgrade`'s comparison are what govkit acts
        on. If they could disagree, the report would describe a different
        install from the one that ran."""
        from cli import marker, version

        _code, out = self._run(monkeypatch, capsys, ["govkit", "--version"])
        reported = (out.out + out.err).split()[-1]
        assert reported == version.GOVKIT_VERSION
        assert marker.version.GOVKIT_VERSION == reported

    def test_help_still_lists_the_subcommands(self, monkeypatch, capsys):
        """Adding a top-level flag must not disturb the command surface."""
        code, out = self._run(monkeypatch, capsys, ["govkit", "--help"])
        text = out.out + out.err
        assert code == 0
        for command in ("apply", "doctor", "upgrade", "validate"):
            assert command in text
