"""ADR approval attestation — the shipped policy and the checks that read it.

`Accepted` on an ADR was a word someone typed. The L4 governance rule gates
implementation on it and nothing in `cli/` or `ci/` had ever read it, while the
templates' `## Status` and `## Approval` sections sat ~140 lines apart, unlinked,
with Approval three empty colon-terminated labels bound to no identity, no date,
no commit.

`AUTHORITY_AND_APPROVAL_CONTRACT.md` — which govkit ships to govern the agent
systems its users build — lists among prohibited patterns "permission
declarations inside prompt text" and "approval by an unauthorized identity", and
requires an approval be scoped, identity-bound, time-bounded and evidence-linked.
`governance/approval_policy.yaml` is what turns an authenticated review into an
approval: without a policy saying *this identity holds the Approver role*, the
design collapses the distinction the contract requires.
"""

import json
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
POLICY_SRC = REPO_ROOT / "governance" / "approval_policy.yaml"
SCHEMA_SRC = REPO_ROOT / "governance" / "schemas" / "approval_policy.schema.json"
AGENTS = ("claude-code", "codex", "copilot")

# The value a fresh install ships, mirroring repo-scope-check's REPO_OWNER and
# the fix-lane gate's SOURCE_PATHS: inert until a team edits it.
SENTINEL = "YOUR_APPROVER_LOGIN"


def _policy() -> dict:
    return yaml.safe_load(POLICY_SRC.read_text(encoding="utf-8"))


class TestShippedPolicy:
    def test_policy_ships(self):
        assert POLICY_SRC.is_file(), f"missing {POLICY_SRC.relative_to(REPO_ROOT)}"

    def test_policy_validates_against_the_shipped_schema(self):
        jsonschema = pytest.importorskip("jsonschema")
        schema = json.loads(SCHEMA_SRC.read_text(encoding="utf-8"))
        errors = list(
            jsonschema.Draft202012Validator(schema).iter_errors(_policy())
        )
        assert not errors, "\n".join(e.message for e in errors)

    def test_policy_carries_the_sentinel_login(self):
        """A fresh install must stay green. govkit cannot know a customer's
        approvers, and guessing one would be the prohibited pattern itself."""
        logins = [a["login"] for a in _policy()["approvers"]]
        assert SENTINEL in logins, logins

    def test_every_shipped_entry_is_the_sentinel(self):
        """No real login may ship — an unedited policy must authorise nobody."""
        logins = [a["login"] for a in _policy()["approvers"]]
        assert set(logins) == {SENTINEL}, logins

    def test_the_sentinel_holds_the_approver_role(self):
        """Editing the login is the whole setup step. If the shipped entry were
        a reviewer, a team that edited only the login would still authorise
        nobody and never learn why."""
        entry = next(a for a in _policy()["approvers"] if a["login"] == SENTINEL)
        assert entry["role"] == "approver"

    def test_policy_version_is_an_integer(self):
        """House convention, asserted here too so the shipped instance cannot
        drift from the schema it is validated against."""
        assert isinstance(_policy()["version"], int)


class TestPolicyShipsToTargets:
    """The schema is govkit's; the policy is the customer's.

    That split is the whole point of the two install categories: `governed`
    files are refreshed by `govkit upgrade`, `shared` files are skipped when
    present. A policy in `governed` would have its approver list overwritten by
    the next upgrade — silently reverting a repo to authorising nobody.
    """

    def _entries(self, agent: str, key: str) -> set[str]:
        manifest = json.loads(
            (REPO_ROOT / "agents" / agent / "manifest.json").read_text(encoding="utf-8")
        )
        found: set[str] = set()

        def walk(node, level: str | None):
            if isinstance(node, dict):
                for k, v in node.items():
                    if k in ("level_4", "level_5"):
                        walk(v, k)
                    elif k == key and isinstance(v, list) and level:
                        found.update(v)
                    else:
                        walk(v, level)
            elif isinstance(node, list):
                for v in node:
                    walk(v, level)

        walk(manifest["variants"], None)
        return found

    @pytest.mark.parametrize("agent", AGENTS)
    def test_schema_is_governed(self, agent):
        assert "governance/schemas/approval_policy.schema.json" in self._entries(
            agent, "governed",
        ), agent

    @pytest.mark.parametrize("agent", AGENTS)
    def test_policy_is_shared_not_governed(self, agent):
        assert "governance/approval_policy.yaml" in self._entries(agent, "shared"), agent
        assert "governance/approval_policy.yaml" not in self._entries(
            agent, "governed",
        ), (
            f"{agent} installs the approval policy as a governed contract — "
            "`govkit upgrade` would overwrite the team's approver list"
        )

    # data is an L3/L4 shape — dbt has no L5 GenAI-ops tier, so the data type
    # declares no level_5 and resolves to an empty set there.
    TYPE_LEVELS = [
        (t, lvl)
        for t in ("api", "cli", "ui-react", "ui-angular", "ui-nextjs", "data")
        for lvl in ("4", "5")
        if not (t == "data" and lvl == "5")
    ]

    @pytest.mark.parametrize("agent", AGENTS)
    def test_every_project_type_receives_both(self, agent):
        """Every type ships an ADR template, so every type needs the policy that
        makes its `Accepted` status derivable."""
        from cli.manifest import load_manifest, resolve_variant_files

        manifest = load_manifest(agent)
        for project_type, level in self.TYPE_LEVELS:
            _files, shared, governed = resolve_variant_files(
                manifest,
                {"level": level, "type": project_type, "ci": "github",
                 "stack": "python-dbt" if project_type == "data" else "python-fastapi"},
            )
            assert "governance/approval_policy.yaml" in shared, (
                f"{agent} {project_type} L{level}"
            )
            assert "governance/schemas/approval_policy.schema.json" in governed, (
                f"{agent} {project_type} L{level}"
            )
