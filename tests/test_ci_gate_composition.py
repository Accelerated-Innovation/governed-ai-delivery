"""Gate workflows that ship together must not define the same job twice.

Levels are additive (L3 ⊂ L4 ⊂ L5), and so are the CI files: an L4 install
receives the L3 gate *and* the L4 gate. That only works if the L4 gate is
additive over the L3 one. When both defined `boundary-check`,
`commit-format`, `sonarqube` and `security-scan`, every L4+ repo ran those
four twice on every push — two workflows, duplicate PR checks, two
SonarQube runs against the same commit.

Scoped to the `api` and `cli` types. `ui-nextjs` has the same shape at L4
and is tracked separately as part of the wider UI review; adding it here
would mean a failing test for work that is deliberately parked.
"""

import re

import pytest
import yaml

from cli.manifest import load_manifest, resolve_variant_files

AGENTS = ("claude-code", "codex", "copilot")
TYPES = ("api", "cli")
LEVELS = ("3", "4", "5")

_GH_JOB = re.compile(r"^  ([a-z][a-z0-9-]*):\s*$", re.MULTILINE)
_AZ_JOB = re.compile(r"^\s*- job:\s*([A-Za-z0-9_]+)\s*$", re.MULTILINE)


def _gate_files(agent: str, ci: str, project_type: str, level: str):
    """Workflow files this install actually receives, as repo-relative paths."""
    manifest = load_manifest(agent)
    _files, shared, governed = resolve_variant_files(
        manifest, {"level": level, "type": project_type, "ci": ci},
    )
    return [
        str(entry) for entry in list(governed) + list(shared)
        if str(entry).startswith(f"ci/{ci}/") and str(entry).endswith((".yml", ".yaml"))
    ]


def _job_names(repo_root, rel_path: str, ci: str) -> set[str]:
    text = (repo_root / rel_path).read_text(encoding="utf-8")
    if ci == "github":
        # Parse rather than regex alone so a malformed workflow fails loudly.
        parsed = yaml.safe_load(text) or {}
        jobs = parsed.get("jobs")
        if isinstance(jobs, dict):
            return set(jobs)
        return set(_GH_JOB.findall(text))
    return set(_AZ_JOB.findall(text))


@pytest.fixture(scope="module")
def repo_root():
    from pathlib import Path
    return Path(__file__).resolve().parent.parent


@pytest.mark.parametrize("agent", AGENTS)
@pytest.mark.parametrize("ci", ["github", "azure"])
@pytest.mark.parametrize("project_type", TYPES)
@pytest.mark.parametrize("level", LEVELS)
def test_no_job_is_defined_by_two_gates_that_ship_together(
    repo_root, agent, ci, project_type, level,
):
    seen: dict[str, str] = {}
    duplicates: list[str] = []
    for rel in _gate_files(agent, ci, project_type, level):
        for job in sorted(_job_names(repo_root, rel, ci)):
            if job in seen:
                duplicates.append(f"{job!r} in both {seen[job]} and {rel}")
            else:
                seen[job] = rel
    assert not duplicates, (
        f"{agent} {project_type} L{level} ({ci}) runs duplicate jobs:\n  "
        + "\n  ".join(duplicates)
    )


@pytest.mark.parametrize("ci", ["github", "azure"])
def test_the_level_4_gate_is_additive_over_the_level_3_gate(repo_root, ci):
    """The L4 gate should contribute what L3 does not, rather than restating
    it. Stated as its own test so the intent survives even if the level
    matrix above changes shape."""
    suffix = "yml"
    l3 = _job_names(repo_root, f"ci/{ci}/l3-quality-gate.{suffix}", ci)
    l4 = _job_names(repo_root, f"ci/{ci}/quality-gate.{suffix}", ci)
    assert l3, "L3 gate defines no jobs"
    assert l4, "L4 gate defines no jobs"
    assert not (l3 & l4), (
        f"{ci}: L4 gate restates L3 jobs {sorted(l3 & l4)} — an L4 install "
        "receives both files, so these run twice"
    )
