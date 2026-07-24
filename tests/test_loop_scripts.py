"""The run_tests / full_test wrappers own the -m marker expression.

The wrappers exist to enforce loop semantics (fast = `not e2e`, full = fast
then `e2e`). A user-supplied -m/--markexpr would compete with the wrapper's
and — because pytest lets the last -m win — could silently invert them, so
the wrappers reject it with a pointer to plain pytest.

`--collect-only -q <one file>` is passed so that even a broken (guardless)
wrapper only collects for a moment instead of running a nested suite.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

_BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(_BASH is None, reason="bash not on PATH — wrappers are bash scripts")


def _run(script, *args):
    return subprocess.run(
        [_BASH, str(REPO_ROOT / script), *args, "--collect-only", "-q", "tests/test_features.py"],
        capture_output=True, text=True, cwd=REPO_ROOT, timeout=120,
    )


class TestWrapperOwnsMarkerExpression:
    @pytest.mark.parametrize(
        "spelling",
        [["-m", "e2e"], ["-me2e"], ["--markexpr", "e2e"], ["--markexpr=e2e"]],
        ids=["separate", "glued", "long", "long-eq"],
    )
    def test_run_tests_rejects_user_markexpr(self, spelling):
        result = _run("run_tests", *spelling)
        assert result.returncode == 2
        assert "-m/--markexpr" in result.stderr

    def test_full_test_rejects_user_markexpr(self):
        result = _run("full_test", "-m", "e2e")
        assert result.returncode == 2
        assert "-m/--markexpr" in result.stderr
