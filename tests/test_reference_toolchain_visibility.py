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
    # `scheme_dirs=()` as well as an absent interpreter dir: the resolver
    # consults sysconfig by default and would otherwise find this very venv's
    # copy, which is the right behaviour and the wrong fixture.
    resolved, reason = reference.resolve_lint_imports(
        interpreter_dir="/nonexistent", search_path="", scheme_dirs=()
    )

    assert resolved is None
    assert "import-linter" in reason


def test_the_reason_distinguishes_not_installed_from_not_on_path():
    """Two different problems needing two different fixes. The old message
    said "not installed" for both, which sends someone to reinstall a package
    they already have."""
    absent = reference.resolve_lint_imports(
        interpreter_dir="/nonexistent", search_path="", scheme_dirs=(), importable=False
    )[1]
    installed_but_hidden = reference.resolve_lint_imports(
        interpreter_dir="/nonexistent", search_path="", scheme_dirs=(), importable=True
    )[1]

    assert "not installed" in absent
    assert "not installed" not in installed_but_hidden
    assert "PATH" in installed_but_hidden


# --- review of PR #161 -------------------------------------------------------

def test_a_windows_scripts_subdirectory_is_searched(tmp_path):
    """A non-virtualenv Windows interpreter lives at `...\\Python312\\python.exe`
    while its console scripts install to `...\\Python312\\Scripts\\`. Only a
    venv puts them side by side.

    Getting this wrong is worse than the bug this PR fixes: the guard below
    carries no skip mark, so an unresolvable-but-installed toolchain turns a
    working installation into a red suite rather than a silent skip.
    """
    scripts = tmp_path / "Scripts"
    scripts.mkdir()
    launcher = scripts / "lint-imports.exe"
    launcher.write_text("")
    launcher.chmod(0o755)

    resolved, reason = reference.resolve_lint_imports(
        interpreter_dir=str(tmp_path), search_path=""
    )

    assert resolved == str(launcher), reason


def test_the_install_scheme_is_consulted_before_giving_up(tmp_path):
    """`pip install --user` and other schemes put scripts somewhere sysconfig
    knows about and `sys.executable` does not."""
    script = tmp_path / "lint-imports"
    script.write_text("")
    script.chmod(0o755)

    resolved, _ = reference.resolve_lint_imports(
        interpreter_dir="/nonexistent", search_path="", scheme_dirs=(str(tmp_path),)
    )

    assert resolved == str(script)
