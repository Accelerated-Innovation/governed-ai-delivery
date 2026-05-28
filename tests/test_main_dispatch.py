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
