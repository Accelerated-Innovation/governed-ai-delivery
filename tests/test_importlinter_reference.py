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

import importlib.util
import os
import re
import shutil
import subprocess
import sys
import sysconfig
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
REFERENCE = REPO_ROOT / "governance" / "backend" / "importlinter-reference.toml"

LAYERS = ("api", "ports", "services", "models", "adapters", "common")

def _script_dirs(interpreter_dir: str | None, scheme_dirs: tuple[str, ...] | None) -> list[Path]:
    """Every directory a console script could plausibly be installed into.

    `Path(sys.executable).parent` alone is a venv assumption. A non-virtualenv
    Windows interpreter sits at `...\\Python312\\python.exe` while its scripts
    install to `...\\Python312\\Scripts\\`, and `pip install --user` puts them
    somewhere only `sysconfig` knows. Missing either would be worse than the
    skip this function exists to fix: the visibility guard carries no skip
    mark, so an unresolvable-but-installed toolchain turns a working
    installation into a red suite.
    """
    if scheme_dirs is None:
        schemes = {sysconfig.get_path("scripts")}
        for scheme in ("nt_user", "posix_user"):
            if scheme in sysconfig.get_scheme_names():
                try:
                    schemes.add(sysconfig.get_path("scripts", scheme=scheme))
                except KeyError:  # pragma: no cover - scheme without a scripts path
                    pass
        scheme_dirs = tuple(sorted(d for d in schemes if d))

    base = Path(interpreter_dir) if interpreter_dir is not None else Path(sys.executable).parent
    return [base, base / "Scripts", *(Path(d) for d in scheme_dirs)]


def resolve_lint_imports(
    interpreter_dir: str | None = None,
    search_path: str | None = None,
    importable: bool | None = None,
    scheme_dirs: tuple[str, ...] | None = None,
) -> tuple[str | None, str]:
    """The `lint-imports` console script, and why it is missing if it is.

    `shutil.which` alone was wrong here, and quietly. import-linter is a
    **declared test dependency**, so the package is present whenever the
    extras are installed — but `python -m pytest` does not put the
    interpreter's own `bin` directory on `PATH`, so the script was invisible
    and every test in this module skipped claiming a missing install.

    The interpreter's directory is searched first for that reason: it is where
    the script actually is when the extras are installed, whatever `PATH`
    happens to say.

    The two failure reasons are kept apart because they need different fixes.
    "Not installed" sends an adopter to `pip install`; "installed but not on
    PATH" sends them somewhere else entirely, and telling the second person
    the first thing wastes their time reinstalling what they have.

    The arguments exist so the failure paths — and the Windows and
    user-scheme layouts — can be tested without uninstalling anything or
    being on Windows.
    """
    for directory in _script_dirs(interpreter_dir, scheme_dirs):
        for name in ("lint-imports", "lint-imports.exe"):
            candidate = directory / name
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return str(candidate), ""

    found = shutil.which("lint-imports", path=search_path) if search_path is not None else shutil.which("lint-imports")
    if found:
        return found, ""

    present = importlib.util.find_spec("importlinter") is not None if importable is None else importable
    if not present:
        return None, "import-linter not installed (pip install -e '.[test]')"
    return None, (
        f"import-linter is importable but its lint-imports script is neither beside "
        f"{sys.executable} nor on PATH"
    )


_LINT_IMPORTS, _WHY_NOT = resolve_lint_imports()

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(_LINT_IMPORTS is None, reason=_WHY_NOT),
]


def _write_package(root: Path, pkg: str, extra_import: str | None = None) -> None:
    """A conforming hexagonal service package, optionally with one added
    import used to prove a specific edge is rejected.

    Standard src-layout: `src/` holds the distributable package and is
    itself **not** a package — no `src/__init__.py`. Modules are therefore
    `<pkg>.ports`, not `src.<pkg>.ports`. Writing a `src/__init__.py` here
    would make a `root_package = "src"` config appear to work while it
    silently analyses nothing in a real project.
    """
    base = root / "src" / pkg
    for layer in LAYERS:
        (base / layer).mkdir(parents=True, exist_ok=True)
        (base / layer / "__init__.py").write_text("", encoding="utf-8")
    (base / "__init__.py").write_text("", encoding="utf-8")

    (base / "models" / "__init__.py").write_text("class Entity: pass\n", encoding="utf-8")
    (base / "ports" / "__init__.py").write_text(
        f"from {pkg}.models import Entity\n\n\nclass Port: pass\n", encoding="utf-8"
    )
    (base / "services" / "core.py").write_text(
        f"from {pkg}.ports import Port\nfrom {pkg}.models import Entity\n", encoding="utf-8"
    )
    (base / "adapters" / "db.py").write_text(
        f"from {pkg}.ports import Port\nfrom {pkg}.services import core\n", encoding="utf-8"
    )
    (base / "api" / "routes.py").write_text(
        f"from {pkg}.ports import Port\n", encoding="utf-8"
    )
    if extra_import:
        target_file, statement = extra_import
        path = base / target_file
        path.write_text(
            path.read_text(encoding="utf-8") + statement.format(pkg=pkg) + "\n",
            encoding="utf-8",
        )


def _write_pyproject(root: Path, packages: list[str], independence: bool = False) -> None:
    """Write the shipped reference contract, pointed at `packages`.

    The reference ships placeholders for the package name; substituting
    them is exactly the step adopters are told to perform.
    """
    body = REFERENCE.read_text(encoding="utf-8")
    # Drop comment-only lines so the commented multi-service block stays inert.
    live = "\n".join(ln for ln in body.splitlines() if not ln.lstrip().startswith("#"))
    package_list = ", ".join(f'"{p}"' for p in packages)
    if len(packages) == 1:
        live = _replace_key(live, "root_package", f'"{packages[0]}"')
    else:
        live = _replace_key(live, "root_package", None)
        live = f"[tool.importlinter]\nroot_packages = [{package_list}]\n" + live.split("\n", 2)[2]
    live = _replace_key(live, "containers", f"[{package_list}]")
    live = _replace_key(live, "source_modules", f'["{packages[0]}.api"]')
    live = _replace_key(live, "forbidden_modules", f'["{packages[0]}.services"]')
    if independence:
        live += textwrap.dedent(f"""
            [[tool.importlinter.contracts]]
            name = "Services are independent"
            type = "independence"
            modules = [{package_list}]
            """)
    (root / "pyproject.toml").write_text(live, encoding="utf-8")


def _replace_key(text: str, key: str, value: str | None) -> str:
    """Replace `key = ...` with `key = value`, or drop the line if value is None."""
    out = []
    for line in text.splitlines():
        if line.strip().startswith(f"{key} ="):
            if value is not None:
                out.append(f"{key} = {value}")
        else:
            out.append(line)
    return "\n".join(out)


_ANALYSED = re.compile(r"Analyzed (\d+) files?, (\d+) dependenc")


def _lint(root: Path) -> subprocess.CompletedProcess:
    """Run the real `lint-imports` console script inside `root`.

    `src/` is put on the path the way a real project's packaging config
    does, so the package is importable under its own name.

    Deliberately the console script rather than `python -m importlinter.cli`
    — the latter has no __main__ entry point, exits 0 with empty output, and
    would make every assertion here pass without linting anything.
    """
    env = dict(os.environ, PYTHONPATH=str(root / "src"))
    # Explicit utf-8: import-linter prints a non-ASCII banner that the
    # Windows locale codec cannot decode, which yields stdout=None rather
    # than a failure — silently voiding every assertion below.
    result = subprocess.run(
        [_LINT_IMPORTS], cwd=root, capture_output=True,
        text=True, encoding="utf-8", errors="replace", env=env,
    )
    assert result.stdout or result.stderr, (
        "lint-imports produced no output — the linter did not run, so this "
        "assertion would be meaningless"
    )
    return result


def _assert_analysed_something(result: subprocess.CompletedProcess) -> None:
    """A contract that resolves zero dependencies reports every layer KEPT
    while enforcing nothing.

    That is how `root_package = "src"` shipped: grimp found no package named
    `src` in a standard src-layout project, analysed 0 dependencies, and the
    gate passed vacuously. Any assertion that a repo is clean has to prove
    the linter actually saw its imports first.
    """
    match = _ANALYSED.search(result.stdout)
    assert match, f"could not find the analysis summary:\n{result.stdout}"
    files, dependencies = int(match.group(1)), int(match.group(2))
    assert files and dependencies, (
        f"analysed {files} files and {dependencies} dependencies — the contract "
        f"resolved nothing, so a KEPT verdict is meaningless:\n{result.stdout}"
    )


class TestSingleService:
    def test_conforming_repo_passes(self, tmp_path):
        _write_package(tmp_path, "svc")
        _write_pyproject(tmp_path, ["svc"])
        result = _lint(tmp_path)
        _assert_analysed_something(result)
        assert result.returncode == 0, (
            f"conforming repo rejected:\n{result.stdout}\n{result.stderr}"
        )

    @pytest.mark.parametrize(
        ("label", "where", "statement"),
        [
            ("services -> adapters", "services/core.py", "from {pkg}.adapters import db"),
            ("ports -> services", "ports/__init__.py", "from {pkg}.services import core"),
            ("models -> services", "models/__init__.py", "from {pkg}.services import core"),
            ("models -> ports", "models/__init__.py", "from {pkg}.ports import Port"),
            ("api -> services", "api/routes.py", "from {pkg}.services import core"),
            ("api -> adapters", "api/routes.py", "from {pkg}.adapters import db"),
        ],
    )
    def test_forbidden_edge_is_rejected(self, tmp_path, label, where, statement):
        _write_package(tmp_path, "svc", extra_import=(where, statement))
        _write_pyproject(tmp_path, ["svc"])
        result = _lint(tmp_path)
        assert result.returncode != 0, f"{label} was permitted:\n{result.stdout}"


class TestMultiService:
    def test_two_conforming_services_pass(self, tmp_path):
        for pkg in ("orders", "billing"):
            _write_package(tmp_path, pkg)
        _write_pyproject(tmp_path, ["orders", "billing"], independence=True)
        result = _lint(tmp_path)
        _assert_analysed_something(result)
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
            extra_import=("services/core.py", "from billing.services import core as _b"),
        )
        _write_pyproject(tmp_path, ["orders", "billing"], independence=True)
        result = _lint(tmp_path)
        assert result.returncode != 0, f"cross-service import was permitted:\n{result.stdout}"


def test_shipped_placeholders_describe_a_real_src_layout():
    """The placeholders have to teach the right shape, because that is what
    an adopter copies and adapts.

    `root_package = "src"` shipped originally, which is wrong for the layout
    REPO_STRUCTURE_README.md prescribes: `src/` is a path entry, not a
    package, so there is no module named `src`. grimp then resolves zero
    dependencies and every contract reports KEPT while enforcing nothing —
    the failure mode is a silent pass, so nothing surfaces it.

    Asserting containers sit under the declared root package keeps the two
    from drifting apart again.
    """
    import tomllib

    config = tomllib.loads(REFERENCE.read_text(encoding="utf-8"))
    root = config["tool"]["importlinter"].get("root_package")
    assert root, "reference declares no root_package"
    assert root != "src", (
        "root_package must name the distributable package, not the src/ "
        "directory — `src` is a path entry in standard src-layout, so "
        "grimp finds no such package and analyses nothing"
    )
    for contract in config["tool"]["importlinter"]["contracts"]:
        for container in contract.get("containers", []):
            assert container == root or container.startswith(f"{root}."), (
                f"container {container!r} is not under root_package {root!r}"
            )
        for key in ("source_modules", "forbidden_modules"):
            for module in contract.get(key, []):
                assert module.startswith(f"{root}."), (
                    f"{key} entry {module!r} is not under root_package {root!r}"
                )


def test_reference_is_parseable_by_import_linter(tmp_path):
    """The shipped table form must be one import-linter 2.x accepts.

    A single-bracket `[tool.importlinter.contracts.<name>]` table parses as
    valid TOML but fails inside import-linter with
    `'str' object has no attribute 'items'` — so a syntax-only check on the
    file would pass while the gate crashed for every adopter.
    """
    _write_package(tmp_path, "svc")
    _write_pyproject(tmp_path, ["svc"])
    result = _lint(tmp_path)
    combined = result.stdout + result.stderr
    assert "has no attribute" not in combined, (
        f"reference contract is not valid import-linter config:\n{combined}"
    )
