"""The shipped import-linter reference must actually enforce BOUNDARIES.md.

`governance/backend/importlinter-reference.toml` tells adopters to copy it
into their own `pyproject.toml` and run `lint-imports`. Nothing verified
that it worked. It didn't: the contract used a single-bracket
`[tool.importlinter.contracts.hexagonal]` table that import-linter 2.x
cannot parse, and its layer order both forbade `adapters -> ports` (which
hexagonal architecture requires) and permitted `services -> adapters`
(which ARCH_CONTRACT.md forbids).

These tests run the real linter against generated skeletons, so the file
cannot drift from the contract it claims to enforce. Asserting on the
TOML's text would not have caught either defect.

Marked `e2e` — they shell out to `lint-imports` and are excluded from the
fast loop.
"""

import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
REFERENCE = REPO_ROOT / "governance" / "backend" / "importlinter-reference.toml"

LAYERS = ("api", "ports", "services", "models", "adapters", "common")

_LINT_IMPORTS = shutil.which("lint-imports")

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        _LINT_IMPORTS is None,
        reason="import-linter not installed (pip install -e '.[test]')",
    ),
]


def _write_package(root: Path, pkg: str, extra_import: str | None = None) -> None:
    """A conforming hexagonal service package, optionally with one added
    import used to prove a specific edge is rejected."""
    base = root / "src" / pkg
    for layer in LAYERS:
        (base / layer).mkdir(parents=True, exist_ok=True)
        (base / layer / "__init__.py").write_text("", encoding="utf-8")
    (base / "__init__.py").write_text("", encoding="utf-8")

    (base / "models" / "__init__.py").write_text("class Entity: pass\n", encoding="utf-8")
    (base / "ports" / "__init__.py").write_text(
        f"from src.{pkg}.models import Entity\n\n\nclass Port: pass\n", encoding="utf-8"
    )
    (base / "services" / "core.py").write_text(
        f"from src.{pkg}.ports import Port\nfrom src.{pkg}.models import Entity\n", encoding="utf-8"
    )
    (base / "adapters" / "db.py").write_text(
        f"from src.{pkg}.ports import Port\nfrom src.{pkg}.services import core\n", encoding="utf-8"
    )
    (base / "api" / "routes.py").write_text(
        f"from src.{pkg}.ports import Port\n", encoding="utf-8"
    )
    if extra_import:
        target_file, statement = extra_import
        path = base / target_file
        path.write_text(
            path.read_text(encoding="utf-8") + statement.format(pkg=pkg) + "\n",
            encoding="utf-8",
        )


def _write_pyproject(root: Path, containers: list[str], independence: bool = False) -> None:
    """Write the shipped reference contract, pointed at `containers`.

    The reference declares a placeholder container; adopters are told to
    adjust it. Substituting it here is exactly that step.
    """
    body = REFERENCE.read_text(encoding="utf-8")
    # Drop comment-only lines so the commented multi-service block stays inert.
    live = "\n".join(ln for ln in body.splitlines() if not ln.lstrip().startswith("#"))
    container_list = ", ".join(f'"{c}"' for c in containers)
    live = _replace_key(live, "containers", f"[{container_list}]")
    live = _replace_key(live, "source_modules", f'["{containers[0]}.api"]')
    live = _replace_key(live, "forbidden_modules", f'["{containers[0]}.services"]')
    if independence:
        live += textwrap.dedent(f"""
            [[tool.importlinter.contracts]]
            name = "Services are independent"
            type = "independence"
            modules = [{container_list}]
            """)
    (root / "pyproject.toml").write_text(live, encoding="utf-8")
    (root / "src" / "__init__.py").write_text("", encoding="utf-8")


def _replace_key(text: str, key: str, value: str) -> str:
    out = []
    for line in text.splitlines():
        if line.strip().startswith(f"{key} ="):
            out.append(f"{key} = {value}")
        else:
            out.append(line)
    return "\n".join(out)


def _lint(root: Path) -> subprocess.CompletedProcess:
    """Run the real `lint-imports` console script inside `root`.

    Deliberately the console script rather than `python -m importlinter.cli`
    — the latter has no __main__ entry point, exits 0 with empty output, and
    would make every assertion here pass without linting anything.
    """
    # Explicit utf-8: import-linter prints a non-ASCII banner that the
    # Windows locale codec cannot decode, which yields stdout=None rather
    # than a failure — silently voiding every assertion below.
    result = subprocess.run(
        [_LINT_IMPORTS], cwd=root, capture_output=True,
        text=True, encoding="utf-8", errors="replace",
    )
    assert result.stdout or result.stderr, (
        "lint-imports produced no output — the linter did not run, so this "
        "assertion would be meaningless"
    )
    return result


class TestSingleService:
    def test_conforming_repo_passes(self, tmp_path):
        _write_package(tmp_path, "svc")
        _write_pyproject(tmp_path, ["src.svc"])
        result = _lint(tmp_path)
        assert result.returncode == 0, (
            f"conforming repo rejected:\n{result.stdout}\n{result.stderr}"
        )

    @pytest.mark.parametrize(
        ("label", "where", "statement"),
        [
            ("services -> adapters", "services/core.py", "from src.{pkg}.adapters import db"),
            ("ports -> services", "ports/__init__.py", "from src.{pkg}.services import core"),
            ("models -> services", "models/__init__.py", "from src.{pkg}.services import core"),
            ("models -> ports", "models/__init__.py", "from src.{pkg}.ports import Port"),
            ("api -> services", "api/routes.py", "from src.{pkg}.services import core"),
            ("api -> adapters", "api/routes.py", "from src.{pkg}.adapters import db"),
        ],
    )
    def test_forbidden_edge_is_rejected(self, tmp_path, label, where, statement):
        _write_package(tmp_path, "svc", extra_import=(where, statement))
        _write_pyproject(tmp_path, ["src.svc"])
        result = _lint(tmp_path)
        assert result.returncode != 0, f"{label} was permitted:\n{result.stdout}"


class TestMultiService:
    def test_two_conforming_services_pass(self, tmp_path):
        for pkg in ("orders", "billing"):
            _write_package(tmp_path, pkg)
        _write_pyproject(tmp_path, ["src.orders", "src.billing"], independence=True)
        result = _lint(tmp_path)
        assert result.returncode == 0, (
            f"conforming multi-service repo rejected:\n{result.stdout}\n{result.stderr}"
        )

    def test_cross_service_import_is_rejected(self, tmp_path):
        """Layers apply *within* each container and say nothing about
        service-to-service edges — the independence contract is what
        catches this. Without it, cross-service coupling goes unenforced."""
        _write_package(tmp_path, "billing")
        _write_package(
            tmp_path, "orders",
            extra_import=("services/core.py", "from src.billing.services import core as _b"),
        )
        _write_pyproject(tmp_path, ["src.orders", "src.billing"], independence=True)
        result = _lint(tmp_path)
        assert result.returncode != 0, f"cross-service import was permitted:\n{result.stdout}"


def test_reference_is_parseable_by_import_linter(tmp_path):
    """The shipped table form must be one import-linter 2.x accepts.

    A single-bracket `[tool.importlinter.contracts.<name>]` table parses as
    valid TOML but fails inside import-linter with
    `'str' object has no attribute 'items'` — so a syntax-only check on the
    file would pass while the gate crashed for every adopter.
    """
    _write_package(tmp_path, "svc")
    _write_pyproject(tmp_path, ["src.svc"])
    result = _lint(tmp_path)
    combined = result.stdout + result.stderr
    assert "has no attribute" not in combined, (
        f"reference contract is not valid import-linter config:\n{combined}"
    )
