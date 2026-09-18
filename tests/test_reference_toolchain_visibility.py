"""A skip that should have been a run — increment 10 follow-up.

`tests/test_importlinter_reference.py` guards itself with
`shutil.which("lint-imports")` and skips with the reason *"import-linter not
installed"*. But import-linter is a **declared test dependency**, so whenever
the extras are installed the package is there — and `python -m pytest` does
not put the interpreter's own `bin` directory on `PATH`, so the console script
was invisible and eleven tests skipped while claiming a missing install.

Locally that meant `pytest` reported **3086 passed** one way and **3097** the
other, with nothing saying which you got. The tests that skipped are the only
ones proving the shipped import-linter reference actually enforces
BOUNDARIES.md.

This module carries no skip mark of its own, deliberately: a guard that can be
skipped by the condition it guards is not a guard.
"""

from __future__ import annotations

import importlib.util

import pytest

from tests import test_importlinter_reference as reference


def test_the_reference_tests_run_whenever_import_linter_is_installed():
    """The whole point. If the package is importable, these tests must not be
    skipped for the reason that it is missing."""
    if importlib.util.find_spec("importlinter") is None:
        pytest.skip("import-linter genuinely absent; nothing to guard here")

    resolved, reason = reference.resolve_lint_imports()

    assert resolved is not None, (
        f"import-linter is installed but the reference tests would skip: {reason}"
    )


def test_a_genuinely_absent_toolchain_still_reports_as_absent():
    """The positive control. A resolver that returned something regardless
    would silence the honest case too — the one where an adopter really has
    not installed the extras."""
    resolved, reason = reference.resolve_lint_imports(
        interpreter_dir="/nonexistent", search_path=""
    )

    assert resolved is None
    assert "import-linter" in reason


def test_the_reason_distinguishes_not_installed_from_not_on_path():
    """Two different problems needing two different fixes. The old message
    said "not installed" for both, which sends someone to reinstall a package
    they already have."""
    absent = reference.resolve_lint_imports(
        interpreter_dir="/nonexistent", search_path="", importable=False
    )[1]
    installed_but_hidden = reference.resolve_lint_imports(
        interpreter_dir="/nonexistent", search_path="", importable=True
    )[1]

    assert "not installed" in absent
    assert "not installed" not in installed_but_hidden
    assert "PATH" in installed_but_hidden
