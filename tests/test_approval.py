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

from cli.approval import (
    check_approval_policy,
    discover_adrs,
    parse_adr_status,
)
from cli.headers import format_editable_header

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


# ---------------------------------------------------------------------------
# The working-tree half: cli/approval.py
# ---------------------------------------------------------------------------


def _write_adr(
    target: Path, name: str, status: str = "Accepted",
    area: str = "backend", approval: str | None = None,
    heading: str = "## 10. Approval",
    govkit_authored: bool = False,
) -> Path:
    body = f"# ADR-0001: {name}\n\n## Status\n{status}\n\n## 1. Context\n\nWhy.\n"
    if approval is not None:
        body += f"\n{heading}\n{approval}\n"
    if govkit_authored:
        from cli.headers import compute_body_hash

        body = format_editable_header(
            baseline="0.18.0", body_hash=compute_body_hash(body),
        ) + body
    path = target / "docs" / area / "architecture" / "ADR" / f"{name}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def _install_policy(target: Path, data: dict | str | None = None) -> Path:
    """Mirror what `govkit apply` ships. `None` installs the real shipped file."""
    path = target / "governance" / "approval_policy.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    if data is None:
        path.write_text(POLICY_SRC.read_text(encoding="utf-8"), encoding="utf-8")
    elif isinstance(data, str):
        path.write_text(data, encoding="utf-8")
    else:
        path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def _install_schema(target: Path) -> None:
    dest = target / "governance" / "schemas"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "approval_policy.schema.json").write_text(
        SCHEMA_SRC.read_text(encoding="utf-8"), encoding="utf-8"
    )


def _configured(login: str = "octo-architect") -> dict:
    return {"version": 1, "approvers": [{"login": login, "role": "approver"}]}


class TestDiscovery:
    def test_no_docs_tree_is_silent(self, tmp_path):
        assert discover_adrs(tmp_path) == []

    def test_finds_adrs_under_every_area(self, tmp_path):
        _write_adr(tmp_path, "0001-alpha", area="backend")
        _write_adr(tmp_path, "0002-beta", area="data")
        _write_adr(tmp_path, "0003-gamma", area="ui")
        assert [p.name for p in discover_adrs(tmp_path)] == [
            "0001-alpha.md", "0002-beta.md", "0003-gamma.md",
        ]

    def test_excludes_the_template(self, tmp_path):
        _write_adr(tmp_path, "0001-alpha")
        _write_adr(tmp_path, "TEMPLATE")
        assert [p.name for p in discover_adrs(tmp_path)] == ["0001-alpha.md"]

    def test_ignores_non_markdown_and_other_doc_dirs(self, tmp_path):
        _write_adr(tmp_path, "0001-alpha")
        (tmp_path / "docs" / "backend" / "architecture" / "ADR" / "notes.txt").write_text(
            "x", encoding="utf-8",
        )
        stray = tmp_path / "docs" / "backend" / "architecture" / "BOUNDARIES.md"
        stray.write_text("## Status\nAccepted\n", encoding="utf-8")
        assert [p.name for p in discover_adrs(tmp_path)] == ["0001-alpha.md"]


class TestStatusParsing:
    def test_reads_the_status_line(self, tmp_path):
        path = _write_adr(tmp_path, "0001-alpha", status="Accepted")
        assert parse_adr_status(path.read_text(encoding="utf-8")) == "Accepted"

    def test_reads_a_non_accepted_status(self, tmp_path):
        path = _write_adr(tmp_path, "0001-alpha", status="Proposed")
        assert parse_adr_status(path.read_text(encoding="utf-8")) == "Proposed"

    def test_unparseable_status_is_none(self):
        assert parse_adr_status("# ADR-0001\n\nno status here\n") is None

    def test_the_shipped_template_vocabulary_line_is_not_an_accepted_claim(self):
        """`Proposed | Accepted | Rejected | Superseded` is a menu, not a claim."""
        text = "# ADR-XXX\n\n## Status\nProposed | Accepted | Rejected | Superseded\n"
        assert parse_adr_status(text) != "Accepted"


class TestPolicyChecks:
    def test_silent_when_nothing_is_installed(self, tmp_path):
        """A repo with no ADRs and no policy hears nothing — absence is not a
        finding, the same contract the defect lane carries."""
        assert check_approval_policy(tmp_path) == ([], [])

    def test_adrs_without_a_policy_warn(self, tmp_path):
        _write_adr(tmp_path, "0001-alpha")
        issues, warnings = check_approval_policy(tmp_path)
        assert not issues
        assert any("approval_policy.yaml" in w for w in warnings), warnings

    def test_unparseable_policy_is_an_issue(self, tmp_path):
        _install_policy(tmp_path, "version: 1\napprovers: [oops\n")
        issues, _warnings = check_approval_policy(tmp_path)
        assert any("could not be parsed" in i for i in issues), issues

    def test_policy_that_is_not_a_mapping_is_an_issue(self, tmp_path):
        _install_policy(tmp_path, "- just\n- a\n- list\n")
        issues, _warnings = check_approval_policy(tmp_path)
        assert issues

    def test_missing_approvers_key_is_an_issue(self, tmp_path):
        _install_policy(tmp_path, "version: 1\n")
        issues, _warnings = check_approval_policy(tmp_path)
        assert any("approvers" in i for i in issues), issues

    def test_unedited_sentinel_policy_warns_that_attestation_is_unconfigured(
        self, tmp_path,
    ):
        """The shipped file authorises nobody by design. Saying so is the point:
        a repo must not read 'no findings' as 'attestation is on'."""
        _install_policy(tmp_path)
        issues, warnings = check_approval_policy(tmp_path)
        assert not issues
        assert any("not configured" in w for w in warnings), warnings

    def test_empty_approver_list_warns(self, tmp_path):
        _install_policy(tmp_path, {"version": 1, "approvers": []})
        issues, warnings = check_approval_policy(tmp_path)
        assert not issues
        assert any("not configured" in w for w in warnings), warnings

    def test_reviewers_alone_do_not_configure_attestation(self, tmp_path):
        """AUTHORITY_AND_APPROVAL_CONTRACT.md: 'a reviewer does not gain
        approval authority'. A policy of reviewers authorises nobody."""
        _install_policy(
            tmp_path,
            {"version": 1, "approvers": [{"login": "octo-qa", "role": "reviewer"}]},
        )
        _issues, warnings = check_approval_policy(tmp_path)
        assert any("not configured" in w for w in warnings), warnings

    def test_a_configured_policy_is_silent(self, tmp_path):
        _install_schema(tmp_path)
        _install_policy(tmp_path, _configured())
        assert check_approval_policy(tmp_path) == ([], [])

    def test_schema_violation_is_an_issue_when_the_schema_is_installed(self, tmp_path):
        _install_schema(tmp_path)
        _install_policy(
            tmp_path,
            {"version": 1, "approvers": [{"login": "octo", "role": "wizard"}]},
        )
        issues, _warnings = check_approval_policy(tmp_path)
        assert any("approval_policy.schema.json" in i for i in issues), issues

    def test_missing_schema_reduces_coverage_visibly(self, tmp_path):
        """Three-tier degradation, as check_eval_criteria established: reduced
        coverage is a warning, never a silent pass."""
        _install_policy(tmp_path, _configured())
        _issues, warnings = check_approval_policy(tmp_path)
        assert any("no approval_policy schema installed" in w for w in warnings), warnings


class TestAdrStatusChecks:
    def test_a_proposed_adr_is_silent(self, tmp_path):
        _install_policy(tmp_path, _configured())
        _install_schema(tmp_path)
        _write_adr(tmp_path, "0001-alpha", status="Proposed")
        assert check_approval_policy(tmp_path) == ([], [])

    def test_accepted_without_an_approval_section_warns(self, tmp_path):
        _install_policy(tmp_path, _configured())
        _install_schema(tmp_path)
        _write_adr(tmp_path, "0001-alpha", status="Accepted")
        issues, warnings = check_approval_policy(tmp_path)
        assert not issues, "migration posture: warn on pre-existing, never fail"
        assert any("0001-alpha.md" in w for w in warnings), warnings

    def test_an_empty_approval_section_does_not_count(self, tmp_path):
        """The shipped template's three empty colon-terminated labels are bound
        to no identity, no date and no commit — that is the defect, not the fix."""
        _install_policy(tmp_path, _configured())
        _install_schema(tmp_path)
        _write_adr(
            tmp_path, "0001-alpha",
            approval="Approved by:\n- Architect:\n- Security (if applicable):",
        )
        _issues, warnings = check_approval_policy(tmp_path)
        assert any("0001-alpha.md" in w for w in warnings), warnings

    @pytest.mark.parametrize(
        "heading",
        ["## 10. Approval", "## 11. Approval", "## Approval", "## Review"],
    )
    def test_both_shipped_vocabularies_and_the_numbered_prefix_are_accepted(
        self, tmp_path, heading,
    ):
        """The templates emit `## 10. Approval` (UI numbers it `## 11.`) while the
        adr-author skill teaches `## Review`. Both ship from govkit, so a
        customer's ADR may carry either."""
        _install_policy(tmp_path, _configured())
        _install_schema(tmp_path)
        _write_adr(
            tmp_path, "0001-alpha", heading=heading,
            approval="Approved by @octo-architect in PR #12 at 2f8c1ab.",
        )
        assert check_approval_policy(tmp_path) == ([], [])

    def test_a_govkit_authored_unmodified_adr_is_silent(self, tmp_path):
        """govkit ships exactly one real ADR — data's 0001 — with no Approval
        section at all. Requiring a customer's approver to attest a decision
        govkit made for them is incoherent, and would have failed every data
        repo on the next upgrade."""
        _install_policy(tmp_path, _configured())
        _install_schema(tmp_path)
        _write_adr(tmp_path, "0001-alpha", area="data", govkit_authored=True)
        assert check_approval_policy(tmp_path) == ([], [])

    def test_an_edited_govkit_adr_is_the_customers_again(self, tmp_path):
        _install_policy(tmp_path, _configured())
        _install_schema(tmp_path)
        path = _write_adr(tmp_path, "0001-alpha", area="data", govkit_authored=True)
        path.write_text(
            path.read_text(encoding="utf-8") + "\n## 2. Decision\n\nOurs now.\n",
            encoding="utf-8",
        )
        _issues, warnings = check_approval_policy(tmp_path)
        assert any("0001-alpha.md" in w for w in warnings), warnings

    def test_require_approval_for_scopes_which_adrs_are_checked(self, tmp_path):
        _install_policy(
            tmp_path,
            _configured() | {"require_approval_for": ["docs/backend/"]},
        )
        _install_schema(tmp_path)
        _write_adr(tmp_path, "0001-alpha", area="backend")
        _write_adr(tmp_path, "0002-beta", area="data")
        _issues, warnings = check_approval_policy(tmp_path)
        joined = " ".join(warnings)
        assert "0001-alpha.md" in joined and "0002-beta.md" not in joined, warnings

    def test_never_raises_on_an_unreadable_adr(self, tmp_path):
        _install_policy(tmp_path, _configured())
        _install_schema(tmp_path)
        path = _write_adr(tmp_path, "0001-alpha")
        path.write_bytes(b"\xff\xfe\x00bad")
        issues, warnings = check_approval_policy(tmp_path)
        assert any("0001-alpha.md" in m for m in issues + warnings)


class TestValidateIntegration:
    """`run_validation` gains a third artifact family, exactly as extensions and
    the defect lane did: silent when absent, its own exit code, combined via
    max(). No new command — the CLI should not grow one whose only real answer
    lives in CI."""

    def _target(self, tmp_path: Path, level: str = "4") -> Path:
        (tmp_path / ".govkit").mkdir(parents=True, exist_ok=True)
        (tmp_path / ".govkit" / "marker.json").write_text(
            json.dumps({
                "version": "0.18.0", "level": level, "agent": "claude-code",
                "options": {"type": "api", "ci": "github"},
                "applied_at": "2026-08-13T00:00:00Z",
            }),
            encoding="utf-8",
        )
        # Empty features/ isolates the approval checks: list_user_features
        # returns [], so nothing else can move the exit code.
        (tmp_path / "features").mkdir(exist_ok=True)
        return tmp_path

    def test_absent_attestation_is_silent(self, tmp_path, capsys):
        """A repo with neither ADRs nor a policy sees no output change."""
        from cli.validate import run_validation

        target = self._target(tmp_path)
        assert run_validation(target) == 0
        assert "approval" not in capsys.readouterr().out.lower()

    def test_a_configured_policy_is_reported_as_passing(self, tmp_path, capsys):
        from cli.validate import run_validation

        target = self._target(tmp_path)
        _install_schema(target)
        _install_policy(target, _configured())
        assert run_validation(target) == 0
        assert "approval_policy.yaml" in capsys.readouterr().out

    def test_an_accepted_adr_without_provenance_warns_without_failing(
        self, tmp_path, capsys,
    ):
        """Migration posture: warn on pre-existing, fail on changed. Only CI
        sees 'changed', so validate never fails on this."""
        from cli.validate import run_validation

        target = self._target(tmp_path)
        _install_schema(target)
        _install_policy(target, _configured())
        _write_adr(target, "0001-alpha")
        assert run_validation(target) == 0
        assert "0001-alpha.md" in capsys.readouterr().out

    def test_a_malformed_policy_fails_the_run(self, tmp_path):
        """The policy is what makes an approval an approval. A broken one means
        the repo cannot derive Accepted at all, so this is not a warning."""
        from cli.validate import run_validation

        target = self._target(tmp_path)
        _install_policy(target, "- not\n- a mapping\n")
        assert run_validation(target) == 1

    def test_not_checked_at_l3(self, tmp_path, capsys):
        """L3 receives neither the policy nor the gate; the attestation model
        starts at L4 beside the contract that gates on Accepted."""
        from cli.validate import run_validation

        target = self._target(tmp_path, level="3")
        _install_policy(target, "- not\n- a mapping\n")
        assert run_validation(target) == 0

    def test_checked_at_l5(self, tmp_path):
        from cli.validate import run_validation

        target = self._target(tmp_path, level="5")
        _install_policy(target, "- not\n- a mapping\n")
        assert run_validation(target) == 1

    def test_a_govkit_authored_adr_alone_produces_no_finding(self, tmp_path, capsys):
        """The case that matters: a fresh `--type data` install must not warn
        about the ADR govkit put there."""
        from cli.validate import run_validation

        target = self._target(tmp_path)
        _install_schema(target)
        _install_policy(target, _configured())
        _write_adr(target, "0001-data-features", area="data", govkit_authored=True)
        assert run_validation(target) == 0
        assert "0001-data-features" not in capsys.readouterr().out
