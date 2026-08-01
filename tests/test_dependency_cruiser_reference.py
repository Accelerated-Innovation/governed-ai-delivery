"""The shipped dependency-cruiser reference must actually enforce BOUNDARIES.md.

The Node counterpart of tests/test_importlinter_reference.py, and held to the
same standard: run the real linter against generated skeletons rather than
asserting on the config's text. A config that parses is not a config that
enforces.

dependency-cruiser fails **open** in two ways, both found while building this
reference against dependency-cruiser 17.4.3:

1. `--output-type json` prints every violation and still exits 0. A gate
   built on it is green on a repo that breaches every boundary.
2. With TypeScript 7 installed it cruises 0 modules and exits 0 — the
   TS 5.x parser API it uses is gone. Nothing in the output says the analysis
   was empty unless you read the module count.

So every assertion here checks the module count too. A green run that cruised
nothing proves nothing, which is the same trap `root_package = "src"` set for
the import-linter reference.

Marked `e2e` — these shell out to `depcruise` and are excluded from the fast
loop. They skip when Node is unavailable; CI asserts the toolchain is present
so a skip cannot pass for a pass there.
"""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
REFERENCE = REPO_ROOT / "governance" / "backend" / "dependency-cruiser-reference.cjs"

LAYERS = ("api", "ports", "services", "models", "adapters", "common")

_NPM = shutil.which("npm") or shutil.which("npm.cmd")

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(_NPM is None, reason="Node/npm not installed"),
]

_CRUISED = re.compile(r"(\d+) modules?, (\d+) dependenc\w* cruised")

# dependency-cruiser's TypeScript analysis needs the 5.x compiler API.
_TYPESCRIPT = "typescript@^5.9"
_DEPCRUISE = "dependency-cruiser@^17"


def _layer_files(prefix: str) -> dict[str, str]:
    """A conforming hexagonal service, rooted at `src/<prefix>`.

    Imports exercise every *allowed* edge, so a rule that over-forbids shows
    up as a failing conforming case rather than passing unnoticed.
    """
    return {
        f"{prefix}common/index.ts": "export const noop = (): void => {};\n",
        f"{prefix}models/index.ts": "export class Entity { id = '1'; }\n",
        f"{prefix}ports/index.ts": (
            "import type { Entity } from '../models';\n"
            "export interface Port { get(): Entity; }\n"
        ),
        f"{prefix}services/core.ts": (
            "import type { Port } from '../ports';\n"
            "import type { Entity } from '../models';\n"
            "export const run = (p: Port): Entity => p.get();\n"
        ),
        f"{prefix}adapters/db.ts": (
            "import type { Port } from '../ports';\n"
            "import { run } from '../services/core';\n"
            "export const use = (p: Port) => run(p);\n"
        ),
        f"{prefix}api/routes.ts": (
            "import type { Port } from '../ports';\n"
            "export const handler = (p: Port) => p.get();\n"
        ),
    }


def _build(root: Path, layout: str, extra: tuple[str, str] | None = None) -> None:
    """Write a skeleton in one of the three layouts the reference supports.

    `flat` is what cli/stacks/nodejs-fastify/LAYER_IMPLEMENTATION.md documents
    (`src/services/`); `nested` is what REPO_STRUCTURE_README.md prescribes
    (`src/<package>/services/`). The reference has to handle both, because the
    payload currently describes both.
    """
    src = root / "src"
    if src.exists():
        shutil.rmtree(src)
    if layout == "flat":
        tree = _layer_files("")
        tree["app.ts"] = "import { use } from './adapters/db';\nexport const boot = () => use;\n"
    elif layout == "nested":
        tree = _layer_files("svc/")
        tree["app.ts"] = (
            "import { use } from './svc/adapters/db';\nexport const boot = () => use;\n"
        )
    else:
        tree = {**_layer_files("orders/"), **_layer_files("billing/")}
        tree["app.ts"] = (
            "import { use } from './orders/adapters/db';\n"
            "import { use as u2 } from './billing/adapters/db';\n"
            "export const boot = () => [use, u2];\n"
        )
    for rel, body in tree.items():
        path = src / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    if extra:
        rel, statement = extra
        path = src / rel
        path.write_text(statement + path.read_text(encoding="utf-8"), encoding="utf-8")


@pytest.fixture(scope="module")
def node_project(tmp_path_factory) -> Path:
    """One npm install shared by every case — it is the slow part."""
    root = tmp_path_factory.mktemp("depcruise")
    (root / "package.json").write_text(
        json.dumps({"name": "boundary-fixture", "version": "1.0.0", "private": True}),
        encoding="utf-8",
    )
    (root / "tsconfig.json").write_text(
        json.dumps({
            "compilerOptions": {
                "target": "ES2022", "module": "ESNext",
                "moduleResolution": "bundler", "strict": True,
            },
            "include": ["src/**/*.ts"],
        }),
        encoding="utf-8",
    )
    result = subprocess.run(
        [_NPM, "install", "--no-audit", "--no-fund", "--silent",
         _DEPCRUISE, _TYPESCRIPT],
        cwd=root, capture_output=True, text=True, encoding="utf-8",
        errors="replace", shell=os.name == "nt",
    )
    if result.returncode != 0:
        # Locally, an offline machine should skip rather than fail. In CI the
        # toolchain is guaranteed by the workflow, so a failed install means
        # these tests silently stopped covering the reference — the exact
        # vacuous-pass this module exists to prevent.
        message = f"npm install failed: {result.stderr[:300]}"
        if os.environ.get("CI"):
            pytest.fail(message)
        pytest.skip(f"{message} (offline?)")
    shutil.copyfile(REFERENCE, root / ".dependency-cruiser.cjs")
    return root


def _cruise(root: Path) -> tuple[int, str, int]:
    """Run the real `depcruise` with the default reporter.

    Deliberately not `--output-type json`: that reporter always exits 0, so
    every assertion below would pass on a repo that violates everything.
    """
    result = subprocess.run(
        ["npx", "--no-install", "depcruise", "src",
         "--config", ".dependency-cruiser.cjs"],
        cwd=root, capture_output=True, text=True, encoding="utf-8",
        errors="replace", shell=os.name == "nt",
    )
    out = (result.stdout or "") + (result.stderr or "")
    assert out.strip(), "depcruise produced no output — it did not run"
    match = _CRUISED.search(out)
    assert match, f"no 'N modules, M dependencies cruised' summary:\n{out}"
    return result.returncode, out, int(match.group(1))


def _assert_analysed_something(modules: int, out: str) -> None:
    """A run that cruises zero modules reports no violations and exits 0.

    That is how a TypeScript 7 project behaves with dependency-cruiser 17:
    the gate is green and enforces nothing. Any clean verdict has to prove
    the tool saw the source first.
    """
    assert modules > 0, (
        f"cruised {modules} modules — the config resolved nothing, so a clean "
        f"verdict is meaningless:\n{out}"
    )


class TestSingleService:
    @pytest.mark.parametrize("layout", ["flat", "nested"])
    def test_conforming_repo_passes(self, node_project, layout):
        _build(node_project, layout)
        code, out, modules = _cruise(node_project)
        _assert_analysed_something(modules, out)
        assert code == 0, f"conforming {layout} repo rejected:\n{out}"

    @pytest.mark.parametrize(
        ("label", "where", "statement"),
        [
            ("api -> services", "api/routes.ts", "import '../services/core';\n"),
            ("api -> adapters", "api/routes.ts", "import '../adapters/db';\n"),
            ("adapters -> api", "adapters/db.ts", "import '../api/routes';\n"),
            ("services -> adapters", "services/core.ts", "import '../adapters/db';\n"),
            ("services -> api", "services/core.ts", "import '../api/routes';\n"),
            ("ports -> services", "ports/index.ts", "import '../services/core';\n"),
            ("ports -> adapters", "ports/index.ts", "import '../adapters/db';\n"),
            ("models -> services", "models/index.ts", "import '../services/core';\n"),
            ("models -> ports", "models/index.ts", "import '../ports';\n"),
            ("common -> models", "common/index.ts", "import '../models';\n"),
            ("common -> services", "common/index.ts", "import '../services/core';\n"),
        ],
    )
    def test_forbidden_edge_is_rejected(self, node_project, label, where, statement):
        _build(node_project, "flat", extra=(where, statement))
        code, out, modules = _cruise(node_project)
        _assert_analysed_something(modules, out)
        assert code != 0, f"{label} was permitted:\n{out}"


class TestMultiService:
    def test_two_conforming_services_pass(self, node_project):
        _build(node_project, "multi")
        code, out, modules = _cruise(node_project)
        _assert_analysed_something(modules, out)
        assert code == 0, f"conforming multi-service repo rejected:\n{out}"

    def test_cross_service_import_is_rejected(self, node_project):
        """Unlike the import-linter reference, whose `independence` contract
        ships commented out, this rule can ship enabled: its pattern requires
        a `src/<service>/<layer>/` segment, so it is inert on the flat layout
        and active as soon as a repo grows a service package."""
        _build(
            node_project, "multi",
            extra=("orders/services/core.ts", "import '../../billing/services/core';\n"),
        )
        code, out, modules = _cruise(node_project)
        _assert_analysed_something(modules, out)
        assert code != 0, f"cross-service import was permitted:\n{out}"
        assert "services-are-independent" in out, (
            f"a rule other than independence caught it:\n{out}"
        )


def test_reference_covers_every_canonical_layer():
    """Structural guard that runs in the fast loop, so a reference which
    silently drops a layer fails even without Node installed."""
    text = REFERENCE.read_text(encoding="utf-8")
    for name in LAYERS:
        assert name in text, f"reference never mentions the {name!r} layer"
