"""The shipped go-arch-lint reference must actually enforce BOUNDARIES.md.

The Go counterpart of tests/test_importlinter_reference.py and
tests/test_dependency_cruiser_reference.py, held to the same standard: run the
real linter against generated skeletons rather than asserting on the YAML.

Two Go-specific facts shape these tests, both established by running
go-arch-lint v1.16.0 rather than reading its documentation.

**go-arch-lint exits 0 on source it cannot parse.** A fixture with a syntax
error reports "OK - No warnings found". So every case here compiles the
skeleton with `go build ./...` first; a violation case that does not compile
proves nothing. The shipped gate runs `go build` for the same reason.

**Go itself forbids import cycles.** In a fully-wired conforming skeleton,
`adapters` imports `services`, so adding `services -> adapters` yields a
project that does not compile — and, per the above, go-arch-lint would then
pass it. Each forbidden edge is therefore tested against a *minimal* skeleton
holding only that one edge, so the linter is what rejects it, not the
compiler. Both give an error in real use; only one of them is this file's
subject.

Marked `e2e` — these shell out to `go` and `go-arch-lint`, and are excluded
from the fast loop. They skip when the toolchain is absent; CI asserts it is
present so a skip cannot pass for a pass there.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
REFERENCE = REPO_ROOT / "governance" / "backend" / "go-arch-lint-reference.yml"

LAYERS = ("api", "ports", "services", "models", "adapters", "common")
MODULE = "example.com/svc"

_GO = shutil.which("go")
_ARCH_LINT = shutil.which("go-arch-lint")
if _ARCH_LINT is None:
    _candidate = Path(os.path.expanduser("~")) / "go" / "bin" / "go-arch-lint"
    for suffix in ("", ".exe"):
        if _candidate.with_suffix(suffix).exists():
            _ARCH_LINT = str(_candidate.with_suffix(suffix))
            break

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        _GO is None or _ARCH_LINT is None,
        reason="Go toolchain or go-arch-lint not installed "
               "(go install github.com/fe3dback/go-arch-lint@latest)",
    ),
]


def _source(package: str, imports: list[str], body: str) -> str:
    block = "".join(f'\t_ "{MODULE}/internal/{name}"\n' for name in imports)
    header = f"import (\n{block})\n\n" if imports else ""
    return f"package {package}\n\n{header}{body}"


def _conforming() -> dict[str, str]:
    """Every *allowed* edge populated, so a rule that over-forbids shows up
    as a failing conforming case rather than passing unnoticed."""
    return {
        "go.mod": f"module {MODULE}\n\ngo 1.24\n",
        "internal/common/log.go": _source("common", [], "func Log(s string) string { return s }\n"),
        "internal/models/entity.go": _source("models", [], "type Entity struct{ ID string }\n"),
        "internal/ports/ports.go": _source(
            "ports", ["models", "common"], "type Repo interface{ Get() string }\n"),
        "internal/services/core.go": _source(
            "services", ["ports", "models", "common"], "func Run() string { return \"\" }\n"),
        "internal/adapters/db.go": _source(
            "adapters", ["ports", "services", "models", "common"],
            "func Use() string { return \"\" }\n"),
        "internal/api/routes.go": _source(
            "api", ["ports", "models", "common"], "func Handler() string { return \"\" }\n"),
        # Composition root. It wires adapters into services, so it imports
        # both — which is why it must live outside internal/, the scanned
        # workdir. LAYER_IMPLEMENTATION.md prescribes cmd/api/main.go.
        "cmd/api/main.go": (
            f'package main\n\nimport (\n\t_ "{MODULE}/internal/adapters"\n'
            f'\t_ "{MODULE}/internal/api"\n)\n\nfunc main() {{}}\n'
        ),
    }


def _minimal() -> dict[str, str]:
    """Six packages, no edges between them — the base for violation cases."""
    files = {"go.mod": f"module {MODULE}\n\ngo 1.24\n"}
    bodies = {
        "common": "func Log(s string) string { return s }\n",
        "models": "type Entity struct{ ID string }\n",
        "ports": "type Repo interface{ Get() string }\n",
        "services": "func Run() string { return \"\" }\n",
        "adapters": "func Use() string { return \"\" }\n",
        "api": "func Handler() string { return \"\" }\n",
    }
    for layer, body in bodies.items():
        files[f"internal/{layer}/{layer}.go"] = _source(layer, [], body)
    return files


def _write(root: Path, files: dict[str, str], extra: tuple[str, str] | None = None) -> None:
    for name in ("internal", "cmd"):
        if (root / name).exists():
            shutil.rmtree(root / name)
    for rel, body in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    if extra:
        rel, target = extra
        path = root / rel
        text = path.read_text(encoding="utf-8")
        line = f'\t_ "{MODULE}/internal/{target}"\n'
        if "import (" in text:
            text = text.replace("import (\n", f"import (\n{line}", 1)
        else:
            head, rest = text.split("\n\n", 1)
            text = f"{head}\n\nimport (\n{line})\n\n{rest}"
        path.write_text(text, encoding="utf-8")
    shutil.copyfile(REFERENCE, root / ".go-arch-lint.yml")


def _assert_compiles(root: Path) -> None:
    """go-arch-lint reports success on source it cannot parse, so a fixture
    that does not build would make its verdict meaningless."""
    result = subprocess.run(
        [_GO, "build", "./..."], cwd=root,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert result.returncode == 0, (
        "fixture is not valid Go, so go-arch-lint's verdict proves nothing:\n"
        + result.stdout + result.stderr
    )


def _mapped_file_count(root: Path) -> int:
    """Files the linter attached to a component — the 'did it see anything'
    signal, equivalent to import-linter's dependency count."""
    result = subprocess.run(
        [_ARCH_LINT, "mapping", "--project-path", str(root), "--json"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return -1
    payload = payload.get("Payload") or payload.get("payload") or {}
    rows = payload.get("MappingGrouped") or payload.get("mappingGrouped") or []
    return sum(len(row.get("FileNames") or row.get("fileNames") or []) for row in rows)


def _check(root: Path) -> tuple[int, str]:
    result = subprocess.run(
        [_ARCH_LINT, "check", "--project-path", str(root)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    out = (result.stdout or "") + (result.stderr or "")
    assert out.strip(), "go-arch-lint produced no output — it did not run"
    return result.returncode, out


@pytest.fixture
def go_project(tmp_path) -> Path:
    return tmp_path


def test_conforming_repo_passes(go_project):
    _write(go_project, _conforming())
    _assert_compiles(go_project)
    mapped = _mapped_file_count(go_project)
    assert mapped >= len(LAYERS), (
        f"only {mapped} files attached to a component — the config resolved "
        "little or nothing, so a clean verdict is meaningless"
    )
    code, out = _check(go_project)
    assert code == 0, f"conforming repo rejected:\n{out}"


@pytest.mark.parametrize(
    ("label", "where", "target"),
    [
        ("api -> services", "internal/api/api.go", "services"),
        ("api -> adapters", "internal/api/api.go", "adapters"),
        ("adapters -> api", "internal/adapters/adapters.go", "api"),
        ("services -> adapters", "internal/services/services.go", "adapters"),
        ("services -> api", "internal/services/services.go", "api"),
        ("ports -> services", "internal/ports/ports.go", "services"),
        ("ports -> adapters", "internal/ports/ports.go", "adapters"),
        ("models -> services", "internal/models/models.go", "services"),
        ("models -> ports", "internal/models/models.go", "ports"),
        ("common -> models", "internal/common/common.go", "models"),
        ("common -> services", "internal/common/common.go", "services"),
    ],
)
def test_forbidden_edge_is_rejected(go_project, label, where, target):
    _write(go_project, _minimal(), extra=(where, target))
    _assert_compiles(go_project)
    code, out = _check(go_project)
    assert code != 0, f"{label} was permitted:\n{out}"


def test_undeclared_package_inside_workdir_is_reported(go_project):
    """go-arch-lint refuses to silently ignore code under its workdir.

    Worth pinning: it is the one thing keeping a mis-scoped config from
    passing vacuously, and it constrains where the composition root may live.
    A team putting theirs at internal/app/ must declare an `app` component —
    the reference cannot pre-declare one, because go-arch-lint errors on a
    component whose folder does not exist.
    """
    _write(go_project, _conforming())
    stray = go_project / "internal" / "app" / "app.go"
    stray.parent.mkdir(parents=True, exist_ok=True)
    stray.write_text(_source("app", ["services"], "func Boot() {}\n"), encoding="utf-8")

    code, out = _check(go_project)
    assert code != 0, f"an undeclared package under internal/ was ignored:\n{out}"
    assert "not attached to any component" in out


def test_reference_declares_every_canonical_layer():
    """Structural guard that runs without a Go toolchain."""
    import yaml

    config = yaml.safe_load(REFERENCE.read_text(encoding="utf-8"))
    assert set(config["components"]) == set(LAYERS), (
        f"components are {sorted(config['components'])}, expected {sorted(LAYERS)}"
    )
    # `common` must depend on nothing. go-arch-lint rejects an explicit empty
    # `mayDependOn: []`, so the contract is expressed by omitting the entry —
    # which reads like an oversight unless it is asserted somewhere.
    assert "common" not in config["deps"], (
        "common must have no deps entry: go-arch-lint rejects `mayDependOn: []`, "
        "so absence is how 'depends on nothing' is expressed"
    )
    for layer in ("api", "services", "ports", "models", "adapters"):
        assert layer in config["deps"], f"{layer} has no deps entry"
