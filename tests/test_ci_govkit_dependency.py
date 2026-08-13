"""A shipped CI gate that runs `govkit` must also install it, at a bounded version.

Four gates invoked `govkit doctor` / `govkit validate` while setting up only Node
(`ci/{github,azure}/ui-nextjs-quality-gate.yml` and their `l3-` variants). On a
clean runner those steps exit 127, so the Next.js quality gate was red for every
adopter that wired it up.

The two gates that *did* install govkit installed it unpinned, which couples a
customer's merge criteria to whatever PyPI serves that morning — while the payload
prose beside it is frozen at install time. CI templates are `governed`, so
`govkit upgrade` rewrites them; pinning to the shipping version means a contract
change reaches a customer's gate only through an explicit upgrade.
"""

import re
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CI_DIRS = [REPO_ROOT / "ci" / "github", REPO_ROOT / "ci" / "azure"]

# `govkit <subcommand>` as an executed command, not a prose mention.
INVOKES_RE = re.compile(r"^\s*(?:-\s*script:\s*|run:\s*)?govkit\s+(doctor|validate|apply|init)\b", re.MULTILINE)
# A pinned install: govkit~=X.Y.Z (compatible-release, patch-only within the minor)
PINNED_RE = re.compile(r"pip install\s+['\"]?govkit~=(\d+\.\d+\.\d+)['\"]?")
# Any install at all, pinned or not.
ANY_INSTALL_RE = re.compile(r"pip install\s+\S*govkit")


def _project_version() -> str:
    with (REPO_ROOT / "pyproject.toml").open("rb") as fh:
        return tomllib.load(fh)["project"]["version"]


def _gates_invoking_govkit() -> list[Path]:
    found = []
    for d in CI_DIRS:
        for path in sorted(d.glob("*.yml")):
            if INVOKES_RE.search(path.read_text(encoding="utf-8")):
                found.append(path)
    return found


GATES = _gates_invoking_govkit()


def _rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def test_found_gates_that_invoke_govkit():
    """Non-vacuous guard: if the detection regex stops matching, every
    parametrized test below silently collects zero cases and passes."""
    assert len(GATES) >= 6, (
        f"expected at least 6 gates invoking govkit, found {[_rel(p) for p in GATES]}"
    )


@pytest.mark.parametrize("gate", GATES, ids=lambda p: f"{p.parent.name}/{p.name}")
def test_gate_installs_govkit_before_invoking_it(gate: Path):
    text = gate.read_text(encoding="utf-8")
    assert ANY_INSTALL_RE.search(text), (
        f"{_rel(gate)} runs a govkit subcommand but never installs govkit — "
        "on a clean runner the step exits 127"
    )


@pytest.mark.parametrize("gate", GATES, ids=lambda p: f"{p.parent.name}/{p.name}")
def test_gate_pins_govkit_to_shipping_version(gate: Path):
    """An unpinned install makes a customer's merge criteria depend on whatever
    PyPI served that morning, against payload prose frozen at install time."""
    text = gate.read_text(encoding="utf-8")
    match = PINNED_RE.search(text)
    assert match, (
        f"{_rel(gate)} installs govkit without a bounded version — "
        "use `pip install govkit~=<version>` so the gate cannot change under the customer"
    )
    assert match.group(1) == _project_version(), (
        f"{_rel(gate)} pins govkit~={match.group(1)} but this project ships "
        f"{_project_version()} — the shipped gate and the shipping validator must agree"
    )
