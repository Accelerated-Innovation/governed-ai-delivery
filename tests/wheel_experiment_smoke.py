"""Phase A acceptance from a clean runtime-only wheel: the experiment loop, S1-S6.

Run with the wheel's Python and -I; never import this checkout's CLI. Every
record is a bundled synthetic fixture. Passing runs show GovKit's record
handling, not application behavior, runtime evidence or SOAA conformance.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import cli
from cli import experiments, paths

assert Path(experiments.__file__).is_relative_to(sys.prefix)

COMMAND = [sys.executable, "-I", "-m", "cli.govkit"]
EXAMPLES = paths.GOVERNANCE_DIR / "examples"
SCENARIOS = EXAMPLES / "experiments"
REQUESTS = EXAMPLES / "workflows/requests"
AGENTS = ("codex", "claude-code", "copilot")
ENTRY_DOCS = {
    "codex": "AGENTS.md",
    "claude-code": ".claude/rules/govkit/governance.md",
    "copilot": ".github/instructions/govkit/governance.instructions.md",
}
SOAA = "skill-oriented-agent-architecture"
FEATURE = "features/discovery"
# The bundled scenarios' documented assessment time; results date from 2026-11-01.
OBSERVED_AT = "2026-11-10T00:00:00Z"
MEMBER_BUDGET = 116  # tests/wheel_windows_smoke.py: installed member path budget


def govkit(*args, expected=0):
    environment = dict(os.environ)
    environment.pop("CI", None)
    result = subprocess.run(
        COMMAND + [str(a) for a in args],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        env=environment,
    )
    assert result.returncode == expected, (args, result.returncode, result.stdout, result.stderr)
    return result.stdout


def git(target, *args):
    return subprocess.run(
        ["git", "-c", "maintenance.auto=false", "-C", str(target), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def snapshot(*folders):
    return {
        (str(folder), p.relative_to(folder).as_posix()): (p.read_bytes(), p.stat().st_mtime_ns)
        for folder in folders
        for p in folder.rglob("*")
        if p.is_file()
    }


def write(folder, relative, text):
    path = folder / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def place(folder, scenario):
    """Overlay one bundled scenario; earlier records and evidence are removed."""
    (folder / FEATURE / "experiments.yaml").unlink(missing_ok=True)
    shutil.rmtree(folder / FEATURE / "evidence", ignore_errors=True)
    root = SCENARIOS / scenario
    for path in sorted(root.rglob("*")):
        # Installers may compile bundled example sources into __pycache__.
        if path.is_file() and path.name != "expected.json" and "__pycache__" not in path.parts:
            destination = folder / path.relative_to(root)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(path.read_bytes())


def report(label, outcome):
    print(f"  {label}: {outcome} [synthetic-fixture]")


# Legacy route: apply L5 api, add both extensions, init, then validate each scenario.
LEGACY = (
    # scenario, acceptance scenario, exit, --strict exit, expected text
    ("boundary", "S1 established boundary", 0, 0, "approved-for-planning; 0 experiment(s)"),
    ("required", "S2 material uncertainty", 0, 1, "experiment-required"),
    ("revised", "S3 failure revised and retested", 0, 0, "records current"),
    ("synthetic", "S4 synthetic cannot satisfy application", 1, 1, "insufficient-evidence-class"),
    ("stale", "S5 changed input invalidates reliance", 1, 1, "stale-reliance"),
)


def legacy_route(workspace, agent):
    target = workspace / f"{agent}-legacy"
    target.mkdir()
    govkit(
        "apply",
        "--agent",
        agent,
        "--target",
        target,
        "--level",
        "5",
        "--type",
        "api",
        "--ci",
        "github",
    )
    govkit("extension", "add", "llm-application", "--target", target)
    govkit("extension", "add", SOAA, "--target", target)
    listed = json.loads(govkit("extension", "list", "--installed", "--target", target, "--json"))
    installed = {e["id"]: e for e in listed["extensions"]}
    assert {"llm-application", SOAA} <= installed.keys() and not listed["conflicts"]
    assert {installed[i]["source"] for i in ("llm-application", SOAA)} == {"legacy"}

    # S6: the installed entry doc routes the three layers independently.
    entry = (target / ENTRY_DOCS[agent]).read_text()
    assert "If the feature calls language models (`mode: llm`)" in entry
    assert "including a single agent with fixed skills" in entry
    assert "Agent count does not decide this" in entry
    assert "applies only when `eval_criteria.yaml` declares `multi_agent: true`" in entry

    govkit("init", "discovery", "--target", target, "--starter", "backend")
    starter = target / FEATURE
    assert (starter / "plan.md").is_file() and (starter / "architecture_preflight.md").is_file()
    # The topology fixture: declared only by an explicit, uncommented flag.
    assert "# multi_agent: true" in (starter / "eval_criteria.yaml").read_text()
    assert "Required when `multi_agent: true`" in (starter / "agent_topology.md").read_text()
    assert "preflight-blocked" in govkit("validate", "--target", target, "--only", "experiments")
    report(f"{agent} legacy S6", "LLM, SOAA and topology route independently")

    for scenario, label, code, strict, expected in LEGACY:
        place(target, scenario)
        before = snapshot(target)
        output = govkit("validate", "--target", target, "--only", "experiments", expected=code)
        assert expected in output, (scenario, output)
        govkit("validate", "--target", target, "--only", "experiments", "--strict", expected=strict)
        assert snapshot(target) == before
        report(f"{agent} legacy {label}", f"validate exit {code}, --strict exit {strict}")


# Declarative route: profile/pack apply in a trusted policy checkout, plan, conform.
DECLARATIVE = (
    # scenario, acceptance scenario, apply the fix, exit, record state, project:tests state
    ("relied", "S1/S3 passed record relied upon", True, 0, "pass", "pass"),
    ("required", "S2 outstanding experiment", True, 1, "unknown", "pass"),
    ("revised", "S3 revised design retested", True, 0, "pass", "pass"),
    ("relied", "S4 a pass alone cannot complete", False, 1, "pass", "fail"),
    ("stale", "S5 stale reliance", True, 1, "fail", "pass"),
    ("synthetic", "S4 synthetic evidence class", True, 1, "fail", "pass"),
)


def results(document):
    return {r["id"]: r for r in document["checks"]["results"]}


def declarative_route(workspace, agent, fixture, *, all_scenarios):
    policy, target = workspace / f"{agent}-policy", workspace / f"{agent}-consumer"
    for folder in (policy, target):
        for relative, content in fixture["files"].items():
            write(folder, relative, content)
    for relative, content in fixture["base_files"].items():
        write(target, relative, content)
    profile = json.loads(json.dumps(fixture["profile"]))
    profile["integrations"]["agent"] = agent
    profile["capabilities"].append({"id": SOAA})
    # SOAA supports only api and cli projects; the pilot is an API project (U2).
    profile["repository"]["project_type"] = "api"
    profile_path = workspace / f"{agent}-profile.json"
    profile_path.write_text(json.dumps(profile))
    govkit("profile", "apply", "--target", policy, "--profile", profile_path, "--json")
    write(policy, "conformance.json", json.dumps(fixture["conformance"]))
    govkit("pack", "apply", "--target", policy, "--json")

    before = snapshot(policy)
    listed = json.loads(govkit("extension", "list", "--installed", "--target", policy, "--json"))
    soaa = next(e for e in listed["extensions"] if e["id"] == SOAA)
    assert soaa["source"] == "declarative" and soaa["status"] == "verified"
    assert soaa["root"].startswith(f".govkit/packs/{SOAA}/")

    def plan(name):
        return json.loads(
            govkit("request", "plan", REQUESTS / f"{name}.json", "--target", policy, "--json")
        )

    bounded, experiment, llm = plan("enhancement"), plan("experiment"), plan("llm")
    assert bounded["workflow"] == "bounded"
    assert "experiment-record" not in {a["id"] for a in bounded["artifacts"]}
    assert experiment["workflow"] == "full-feature"
    assert not any(d["blocking"] for d in experiment["decisions"])
    assert "experiment-escalated" in {d["code"] for d in experiment["decisions"]}
    assert "experiment-record" in {a["id"] for a in experiment["artifacts"]}
    # S6: model evaluation follows the LLM impact, never the SOAA pack.
    assert "llm-evaluation" in llm["required_capabilities"]
    assert SOAA not in llm["required_capabilities"]
    assert snapshot(policy) == before
    report(f"{agent} declarative S1/S2", "bounded stays bounded; experiment escalates")

    git(target, "init", "-q")
    git(target, "config", "user.email", "pilot@example.invalid")
    git(target, "config", "user.name", "Govkit pilot")
    git(target, "add", ".")
    git(target, "commit", "-qm", "pilot baseline")
    arguments = workspace / f"{agent}-arguments.json"
    arguments.write_text('{"llm-exact-match":["--results","results.json"]}')
    cases = DECLARATIVE if all_scenarios else DECLARATIVE[:1]
    for scenario, label, fix, code, record, tests in cases:
        place(policy, scenario)
        place(target, scenario)
        git(target, "add", ".")
        git(target, "commit", "-qm", f"scenario {scenario}", "--allow-empty")
        base = git(target, "rev-parse", "HEAD")
        if fix:
            for relative, content in fixture["fixed_files"].items():
                write(target, relative, content)
        before = snapshot(policy, target)
        document = json.loads(
            govkit(
                "conform",
                "--request",
                REQUESTS / "experiment.json",
                "--target",
                target,
                "--policy-target",
                policy,
                "--base",
                base,
                "--observed-at",
                OBSERVED_AT,
                "--execute-check",
                "project:tests",
                "--execute-check",
                "llm-exact-match",
                "--pack-arguments",
                arguments,
                "--json",
                expected=code,
            )
        )
        assert snapshot(policy, target) == before
        checks = results(document)
        assert checks["artifact:experiment-record"]["state"] == record, (scenario, checks)
        assert checks["project:tests"]["state"] == tests, (scenario, checks)
        assert document["plan"]["workflow"] == "full-feature"
        git(target, "checkout", "--", ".")
        report(f"{agent} declarative {label}", f"conform exit {code}, record {record}")

    # The opt-in applicability check over the relied-upon synthetic record.
    place(policy, "relied")
    block = (SOAA_ROOT / "templates/preflight-soaa.md").read_text()
    block = block.split("```yaml\n", 1)[1].split("```", 1)[0]
    decided = block.replace(
        'status: unknown, reason: "", evidence: "", owner: "", change_trigger: ""',
        'status: not-applicable, reason: "No such port", evidence: "src/runtime/selection.py", '
        'owner: "team", change_trigger: "A port is added"',
    ).replace(
        'id: skill-activation, status: not-applicable, reason: "No such port", '
        'evidence: "src/runtime/selection.py", owner: "team", change_trigger: "A port is added"',
        'id: skill-activation, status: applies, reason: "", evidence: "", owner: "", '
        'change_trigger: ""',
    )
    preflight = policy / FEATURE / "architecture_preflight.md"
    preflight.write_text(preflight.read_text() + f"\n```yaml\n{decided}```\n")
    check = (
        "pack",
        "check",
        "--target",
        policy,
        "soaa-applicability",
        "--",
        "--preflight",
        f"{FEATURE}/architecture_preflight.md",
        "--experiments",
        f"{FEATURE}/experiments.yaml",
    )
    before = snapshot(policy)
    claimed = json.loads(govkit(*check, "--cases", "GK-SOAA-04"))
    assert [c["case"] for c in claimed["covered"]] == ["GK-SOAA-04"]
    assert claimed["covered"][0]["evidence_class"] == "synthetic-fixture"
    everything = json.loads(govkit(*check, expected=1))
    assert "GK-SOAA-03" in everything["uncovered"]
    assert snapshot(policy) == before
    report(f"{agent} soaa-applicability", "claimed case covered; full claim uncovered")


def path_budget():
    package = Path(cli.__file__).parent
    members = [
        "cli/" + p.relative_to(package).as_posix()
        for p in package.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    ]
    longest = max(members, key=len)
    assert len(longest) <= MEMBER_BUDGET, longest
    assert any(m.endswith(f"{SOAA}/checks/applicability.py") for m in members)
    print(f"  Windows member budget: {len(longest)}/{MEMBER_BUDGET}")


SOAA_ROOT = paths.EXTENSION_PACKS_DIR / SOAA
fixture = json.loads((EXAMPLES / "change-conformance/consumer.json").read_text())
with tempfile.TemporaryDirectory() as directory:
    workspace = Path(directory)
    for agent in AGENTS:
        print(f"{agent}:")
        legacy_route(workspace, agent)
        declarative_route(workspace, agent, fixture, all_scenarios=agent == "codex")
path_budget()
print(
    "Experiment wheel smoke passed: S1-S6 across 3 agents, legacy validate and declarative "
    "plan/conform, the applicability check and the path budget; synthetic fixtures only"
)
