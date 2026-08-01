"""Boundary enforcement ships per backend stack, not per backend install.

`import-linter` is Python-only, but the `boundary-check` job lived in the
shared `l3-quality-gate.yml`, so `go-gin`, `dotnet-aspnet`,
`java-spring-boot` and `nodejs-fastify` installs all received a Python
linter job that cannot read their source. Since #95 it skips when no
contract is configured, which made the failure silent rather than absent —
a skipped job still enforces nothing while the architecture docs promise
enforcement.

The job now lives in its own stack-selected file. `python-fastapi` receives
`ci/<flavour>/boundary-gate-python.yml`; a stack with no boundary tooling
yet receives no boundary gate at all, rather than one that skips.

Increment 1 of plans/PER_STACK_BOUNDARY_ENFORCEMENT_PLAN.md (#93). The
remaining four stacks arrive in increments 2-5; the "ships nothing" cases
below are the ones that flip as each lands.
"""

import re

import pytest
import yaml

from cli import paths
from cli.manifest import load_manifest, resolve_variant_files

AGENTS = ("claude-code", "codex", "copilot")
CI_FLAVOURS = ("github", "azure")
BACKEND_TYPES = ("api", "cli")
LEVELS = ("3", "4", "5")

PYTHON_STACK = "python-fastapi"

# Stacks whose boundary tool govkit ships enforcement for, and the gate file
# each receives. Grows by one per increment of the per-stack plan.
STACK_GATES = {
    "python-fastapi": "boundary-gate-python.yml",
    "nodejs-fastify": "boundary-gate-node.yml",
}
STACKS_WITHOUT_A_GATE = (
    "dotnet-aspnet",
    "java-spring-boot",
    "go-gin",
)

# The reference contract each gate tells the team to copy in. It has to ship
# with the gate: a gate whose notice names a file the install never received
# is a dead end.
STACK_REFERENCES = {
    "python-fastapi": "governance/backend/importlinter-reference.toml",
    "nodejs-fastify": "governance/backend/dependency-cruiser-reference.cjs",
}
_ALL_REFERENCES = set(STACK_REFERENCES.values())

_AZ_STAGE = re.compile(r"^\s*- stage:\s*([A-Za-z0-9_]+)\s*$", re.MULTILINE)


def _governed(agent: str, ci: str, project_type: str, level: str, stack: str) -> list[str]:
    manifest = load_manifest(agent)
    _files, _shared, governed = resolve_variant_files(
        manifest,
        {"level": level, "type": project_type, "ci": ci, "stack": stack},
    )
    return [str(entry) for entry in governed]


def _boundary_gates(governed: list[str], ci: str) -> list[str]:
    return [path for path in governed if path.startswith(f"ci/{ci}/boundary-gate-")]


def _gate_text(rel_path: str) -> str:
    return (paths.REPO_ROOT / rel_path).read_text(encoding="utf-8")


def _github_jobs(rel_path: str) -> set[str]:
    parsed = yaml.safe_load(_gate_text(rel_path)) or {}
    jobs = parsed.get("jobs")
    assert isinstance(jobs, dict) and jobs, f"{rel_path} defines no jobs"
    return set(jobs)


def _azure_stages(rel_path: str) -> set[str]:
    stages = set(_AZ_STAGE.findall(_gate_text(rel_path)))
    assert stages, f"{rel_path} defines no stages"
    return stages


class TestPythonBoundaryGateDispatch:
    """A backend install receives exactly its own stack's boundary gate."""

    @pytest.mark.parametrize("agent", AGENTS)
    @pytest.mark.parametrize("ci", CI_FLAVOURS)
    @pytest.mark.parametrize("project_type", BACKEND_TYPES)
    @pytest.mark.parametrize("level", LEVELS)
    @pytest.mark.parametrize("stack, gate", sorted(STACK_GATES.items()))
    def test_stack_receives_its_own_boundary_gate(
        self, agent, ci, project_type, level, stack, gate,
    ):
        governed = _governed(agent, ci, project_type, level, stack)

        assert _boundary_gates(governed, ci) == [f"ci/{ci}/{gate}"], (
            f"{agent} {project_type} L{level} ({ci}, {stack}) must receive "
            f"exactly {gate}; got {_boundary_gates(governed, ci)}"
        )

    @pytest.mark.parametrize("agent", AGENTS)
    @pytest.mark.parametrize("ci", CI_FLAVOURS)
    @pytest.mark.parametrize("project_type", BACKEND_TYPES)
    @pytest.mark.parametrize("level", LEVELS)
    @pytest.mark.parametrize("stack", STACKS_WITHOUT_A_GATE)
    def test_a_stack_with_no_boundary_tooling_receives_no_gate(
        self, agent, ci, project_type, level, stack,
    ):
        """Shipping nothing is the honest state — a Python linter pointed at
        Go enforces nothing whether it fails or skips."""
        governed = _governed(agent, ci, project_type, level, stack)

        assert _boundary_gates(governed, ci) == [], (
            f"{agent} {project_type} L{level} ({ci}, {stack}) must receive no "
            f"boundary gate until {stack} has enforcement of its own"
        )

    @pytest.mark.parametrize("agent", AGENTS)
    @pytest.mark.parametrize("ci", CI_FLAVOURS)
    @pytest.mark.parametrize("project_type", ["ui-react", "ui-angular", "ui-nextjs"])
    @pytest.mark.parametrize("level", LEVELS)
    def test_ui_types_never_receive_a_backend_boundary_gate(
        self, agent, ci, project_type, level,
    ):
        """The dispatch must be nested under the backend type entries. Wiring it
        at the `ci` block level instead would leak the gate into UI installs,
        which reject `--stack` outright."""
        governed = _governed(agent, ci, project_type, level, PYTHON_STACK)

        assert _boundary_gates(governed, ci) == [], (
            f"{agent} {project_type} L{level} ({ci}) must receive no backend "
            "boundary gate"
        )

    @pytest.mark.parametrize("agent", AGENTS)
    @pytest.mark.parametrize("ci", CI_FLAVOURS)
    @pytest.mark.parametrize("level", ["3", "4"])
    @pytest.mark.parametrize("stack", ["python-dbt", "databricks-lakehouse"])
    def test_data_type_never_receives_a_backend_boundary_gate(
        self, agent, ci, level, stack,
    ):
        governed = _governed(agent, ci, "data", level, stack)

        assert _boundary_gates(governed, ci) == [], (
            f"{agent} data L{level} ({ci}, {stack}) must receive no backend "
            "boundary gate"
        )


class TestBoundaryReferenceDispatch:
    """The reference contract follows the same stack selection as the gate.

    Caught by a real `govkit apply`, not by the dispatch assertions above: a
    `nodejs-fastify` install received `boundary-gate-node.yml`, whose notice
    says to copy `governance/backend/dependency-cruiser-reference.cjs`, while
    the install actually shipped `importlinter-reference.toml` — a Python
    contract the Node gate cannot use, and no `.cjs` anywhere.
    """

    @pytest.mark.parametrize("agent", AGENTS)
    @pytest.mark.parametrize("ci", CI_FLAVOURS)
    @pytest.mark.parametrize("project_type", BACKEND_TYPES)
    @pytest.mark.parametrize("level", LEVELS)
    @pytest.mark.parametrize("stack, reference", sorted(STACK_REFERENCES.items()))
    def test_stack_receives_only_its_own_reference(
        self, agent, ci, project_type, level, stack, reference,
    ):
        governed = set(_governed(agent, ci, project_type, level, stack))

        assert governed & _ALL_REFERENCES == {reference}, (
            f"{agent} {project_type} L{level} ({ci}, {stack}) must receive "
            f"{reference} and no other boundary reference; got "
            f"{sorted(governed & _ALL_REFERENCES)}"
        )

    @pytest.mark.parametrize("agent", AGENTS)
    @pytest.mark.parametrize("ci", CI_FLAVOURS)
    @pytest.mark.parametrize("project_type", BACKEND_TYPES)
    @pytest.mark.parametrize("level", LEVELS)
    @pytest.mark.parametrize("stack", STACKS_WITHOUT_A_GATE)
    def test_stack_without_a_gate_receives_no_reference(
        self, agent, ci, project_type, level, stack,
    ):
        """A Go team receiving a Python import-linter contract is the same
        defect as receiving a Python linter job."""
        governed = set(_governed(agent, ci, project_type, level, stack))

        assert governed & _ALL_REFERENCES == set(), (
            f"{agent} {project_type} L{level} ({ci}, {stack}) must receive no "
            f"boundary reference; got {sorted(governed & _ALL_REFERENCES)}"
        )

    @pytest.mark.parametrize("reference", sorted(_ALL_REFERENCES))
    def test_reference_file_exists(self, reference):
        assert (paths.REPO_ROOT / reference).is_file()


class TestBoundaryGateExtraction:
    """The job moved out of the shared L3 gate — it is not defined in both."""

    @pytest.mark.parametrize("gate", sorted(STACK_GATES.values()))
    @pytest.mark.parametrize("ci", CI_FLAVOURS)
    def test_the_boundary_gate_file_exists(self, ci, gate):
        assert (paths.REPO_ROOT / f"ci/{ci}/{gate}").is_file()

    @pytest.mark.parametrize("gate", sorted(STACK_GATES.values()))
    def test_github_boundary_gate_defines_only_the_boundary_job(self, gate):
        assert _github_jobs(f"ci/github/{gate}") == {"boundary-check"}

    @pytest.mark.parametrize("gate", sorted(STACK_GATES.values()))
    def test_azure_boundary_gate_defines_only_the_boundary_stage(self, gate):
        assert _azure_stages(f"ci/azure/{gate}") == {"BoundaryCheck"}

    def test_github_l3_gate_no_longer_defines_the_boundary_job(self):
        jobs = _github_jobs("ci/github/l3-quality-gate.yml")

        assert "boundary-check" not in jobs, (
            "boundary-check is defined in both l3-quality-gate.yml and "
            "boundary-gate-python.yml — a python-fastapi install ships both "
            "files and would run it twice"
        )
        # Extraction must move one job, not gut the gate.
        assert {"commit-format", "sonarqube", "security-scan"} <= jobs

    def test_azure_l3_gate_no_longer_defines_the_boundary_stage(self):
        stages = _azure_stages("ci/azure/l3-quality-gate.yml")

        assert "BoundaryCheck" not in stages, (
            "BoundaryCheck is defined in both l3-quality-gate.yml and "
            "boundary-gate-python.yml — a python-fastapi install ships both "
            "files and would run it twice"
        )
        assert {"CommitFormat", "SonarQube", "SecurityScan"} <= stages


class TestBoundaryGateContent:
    """The opt-in skip contract from #95 survived the move."""

    @pytest.mark.parametrize(
        "rel_path, required",
        [
            (
                "ci/github/boundary-gate-python.yml",
                [
                    "tool.importlinter",
                    ".importlinter",
                    "pip install import-linter",
                    "lint-imports",
                    "::notice::",
                    "governance/backend/importlinter-reference.toml",
                ],
            ),
            (
                "ci/azure/boundary-gate-python.yml",
                [
                    "tool.importlinter",
                    ".importlinter",
                    "pip install import-linter",
                    "lint-imports",
                    "##vso[task.logissue type=warning]",
                    "governance/backend/importlinter-reference.toml",
                ],
            ),
        ],
    )
    def test_gate_keeps_the_contract_detection_and_opt_in_notice(self, rel_path, required):
        text = _gate_text(rel_path)

        for fragment in required:
            assert fragment in text, f"{rel_path} lost {fragment!r} in the move"

    @pytest.mark.parametrize("stack, gate", sorted(STACK_GATES.items()))
    @pytest.mark.parametrize("ci", CI_FLAVOURS)
    def test_gate_names_the_stack_it_is_selected_for(self, ci, stack, gate):
        """The file is stack-selected, so a reader opening it must be able to
        tell which stack it belongs to without consulting the manifest."""
        assert stack in _gate_text(f"ci/{ci}/{gate}")


class TestNodeBoundaryGateContent:
    """dependency-cruiser has two silent-pass modes. The gate must close both.

    Verified against dependency-cruiser 17.4.3 while building the reference:

    - `--output-type json` reports every violation and still **exits 0**. A
      gate built on it goes green on a repo that breaches every boundary.
    - With TypeScript 7 installed, it cruises **0 modules** and exits 0 —
      a green gate analysing nothing. TypeScript 5.x cruises normally.

    Both fail open, so the gate has to assert a non-zero module count rather
    than trusting the exit code alone.
    """

    @staticmethod
    def _executable(rel_path: str) -> str:
        """The gate with comment lines dropped.

        Both failure modes are *described* in these files' header comments, so
        a plain substring search over the whole text cannot tell an
        explanation from an invocation."""
        return "\n".join(
            line for line in _gate_text(rel_path).splitlines()
            if not line.lstrip().startswith("#")
        )

    @pytest.mark.parametrize("ci", CI_FLAVOURS)
    def test_gate_does_not_use_the_json_reporter(self, ci):
        body = self._executable(f"ci/{ci}/boundary-gate-node.yml")

        assert "--output-type" not in body, (
            "the json reporter always exits 0 — every violation would be "
            "printed and the gate would still pass"
        )
        assert "depcruise" in body or "dependency-cruiser" in body

    @pytest.mark.parametrize("ci", CI_FLAVOURS)
    def test_gate_fails_on_a_zero_module_count(self, ci):
        body = self._executable(f"ci/{ci}/boundary-gate-node.yml")

        assert "modules" in body, (
            "the gate must parse the 'N modules, M dependencies cruised' "
            "summary — a run that analyses nothing exits 0"
        )
        assert '"$modules" -eq 0' in body, (
            "the gate must fail when the module count is zero, not merely "
            "report it"
        )
        assert "exit 1" in body
