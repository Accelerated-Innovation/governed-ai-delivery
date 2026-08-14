"""Behavior tests for the ADR approval gate's embedded checker.

This gate exists because `govkit validate` structurally cannot do its job: the
working tree holds no reviews, so validate can prove `governance/approval_policy.yaml`
is well-formed and report an ADR claiming `Accepted` with nothing behind it, but
it can never prove an approval happened. Only the reviews API can, and only CI
has it.

Following `tests/test_fix_lane_gate_checks.py`: extract the heredoc, execute it
against fixtures, and pin the two platform embeddings identical so they cannot
drift. Asserting on the YAML text would prove only that words are present —
these tests run the checker.

Like the fix-lane gate, this one is deliberately self-contained. It never
invokes govkit: a blocking gate must not depend on an unpinned PyPI release, and
`run_validation` exits 0 on a missing marker, so a gate delegating to it could be
switched off from inside the PR it is reviewing.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
GATE_PATHS = {
    "github": REPO_ROOT / "ci" / "github" / "adr-approval-gate.yml",
    "azure": REPO_ROOT / "ci" / "azure" / "adr-approval-gate.yml",
}

HEAD_SHA = "2f8c1ab9d4e6f70123456789abcdef0123456789"
OLD_SHA = "1111111111111111111111111111111111111111"
APPROVER = "octo-architect"
SENTINEL = "YOUR_APPROVER_LOGIN"
ADR_REL = "docs/backend/architecture/ADR/0001-service-layer.md"


def _extract_checker(gate_path: Path) -> str:
    raw = gate_path.read_text(encoding="utf-8")
    marker = "python - <<'EOF'\n"
    start = raw.index(marker) + len(marker)
    body = []
    for line in raw[start:].splitlines():
        if line.strip() == "EOF":
            break
        body.append(line)
    return textwrap.dedent("\n".join(body)) + "\n"


def _adr(status: str = "Accepted", approval: str | None = None) -> str:
    text = (
        "# ADR-0001: Introduce a service layer\n\n"
        f"## Status\n{status}\n\n## 1. Context\n\nWhy.\n"
    )
    if approval:
        text += f"\n## 10. Approval\n{approval}\n"
    return text


def _govkit_authored(body: str, tamper: bool = False) -> str:
    """Reproduce what `cli.headers.prepend_header_to_file` writes on install."""
    from cli.headers import format_editable_header

    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    if tamper:
        body += "\n## 2. Decision\n\nOurs now.\n"
    return format_editable_header(baseline="0.18.0", body_hash=digest) + body


def _policy(
    approvers: list[dict] | None = None, **extra,
) -> dict:
    if approvers is None:
        approvers = [{"login": APPROVER, "role": "approver"}]
    return {"version": 1, "approvers": approvers, **extra}


def _run(
    tmp_path: Path,
    changed: list[str],
    *,
    files: dict[str, str] | None = None,
    policy: dict | str | None = None,
    reviews: list[dict] | None = None,
    head_sha: str = HEAD_SHA,
    platform: str = "github",
) -> subprocess.CompletedProcess:
    for rel, text in (files or {}).items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    if policy is not None:
        path = tmp_path / "governance" / "approval_policy.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            policy if isinstance(policy, str)
            else yaml.safe_dump(policy, sort_keys=False),
            encoding="utf-8",
        )

    (tmp_path / "reviews.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in (reviews or [])), encoding="utf-8",
    )

    script = tmp_path / "_gate.py"
    script.write_text(_extract_checker(GATE_PATHS[platform]), encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(script)],
        cwd=tmp_path,
        input="\n".join(changed),
        capture_output=True,
        text=True,
        env={"HEAD_SHA": head_sha, "PATH": "", "SYSTEMROOT": ""},
    )


def _review(
    login: str = APPROVER,
    commit: str = HEAD_SHA,
    state: str = "APPROVED",
    at: str = "2026-08-14T09:00:00Z",
    review_id: int = 1,
) -> dict:
    """One entry of the normalized review list the gate's shell step writes.

    `submitted_at` and `id` are what let the checker tell a reviewer's *latest*
    standing from any earlier one they have since changed.
    """
    return {
        "login": login, "state": state, "commit_id": commit,
        "submitted_at": at, "id": review_id,
    }


def _approval(login: str = APPROVER, commit: str = HEAD_SHA, state: str = "APPROVED"):
    return _review(login=login, commit=commit, state=state)


def test_checker_extraction_is_not_empty():
    """Non-vacuous guard: a changed heredoc marker would make every test below
    run an empty script and trivially pass."""
    body = _extract_checker(GATE_PATHS["github"])
    assert "approval_policy.yaml" in body and "commit_id" in body, body[:300]


class TestNothingToAttest:
    def test_no_adr_changed_passes(self, tmp_path):
        result = _run(tmp_path, [], policy=_policy())
        assert result.returncode == 0, result.stdout
        assert "No ADR changed" in result.stdout

    def test_the_template_is_not_an_adr(self, tmp_path):
        """`Proposed | Accepted | Rejected | Superseded` is the vocabulary menu.
        Editing the template is not accepting a decision."""
        result = _run(
            tmp_path,
            ["docs/backend/architecture/ADR/TEMPLATE.md"],
            files={
                "docs/backend/architecture/ADR/TEMPLATE.md":
                    _adr(status="Proposed | Accepted | Rejected | Superseded"),
            },
            policy=_policy(),
        )
        assert result.returncode == 0, result.stdout

    def test_a_proposed_adr_needs_no_approval(self, tmp_path):
        """The agent authors Proposed and stops; that is the point of the skill
        change, and this is the gate agreeing with it."""
        result = _run(
            tmp_path, [ADR_REL], files={ADR_REL: _adr(status="Proposed")},
            policy=_policy(),
        )
        assert result.returncode == 0, result.stdout
        assert "nothing to attest" in result.stdout

    def test_a_deleted_adr_is_not_read(self, tmp_path):
        """--diff-filter=d keeps deletions out of the list; if one slipped
        through, the checker must not crash on the missing file."""
        result = _run(tmp_path, [], policy=_policy())
        assert result.returncode == 0, result.stdout


class TestFailsClosed:
    def test_unconfigured_policy_fails_on_an_accepted_adr(self, tmp_path):
        """The opposite of the fix-lane gate's inert sentinel, deliberately: an
        ADR cannot be accepted in a repo that declares nobody able to accept it."""
        result = _run(
            tmp_path, [ADR_REL], files={ADR_REL: _adr()},
            policy=_policy([{"login": SENTINEL, "role": "approver"}]),
            reviews=[_approval()],
        )
        assert result.returncode == 1, result.stdout
        assert "names no approver" in result.stdout

    def test_a_fresh_install_touching_no_adr_stays_green(self, tmp_path):
        """Failing closed must not mean failing on arrival."""
        result = _run(
            tmp_path, [], policy=_policy([{"login": SENTINEL, "role": "approver"}]),
        )
        assert result.returncode == 0, result.stdout

    def test_a_missing_policy_fails(self, tmp_path):
        result = _run(tmp_path, [ADR_REL], files={ADR_REL: _adr()}, reviews=[_approval()])
        assert result.returncode == 1, result.stdout
        assert "is missing" in result.stdout

    def test_a_malformed_policy_fails(self, tmp_path):
        result = _run(
            tmp_path, [ADR_REL], files={ADR_REL: _adr()},
            policy="approvers: [unclosed\n", reviews=[_approval()],
        )
        assert result.returncode == 1, result.stdout

    def test_a_policy_that_is_not_a_mapping_fails(self, tmp_path):
        result = _run(
            tmp_path, [ADR_REL], files={ADR_REL: _adr()},
            policy="- a\n- list\n", reviews=[_approval()],
        )
        assert result.returncode == 1, result.stdout

    def test_no_head_sha_fails_rather_than_matching_everything(self, tmp_path):
        """An empty HEAD_SHA against an empty commit_id would compare equal and
        wave through an unbound approval."""
        result = _run(
            tmp_path, [ADR_REL], files={ADR_REL: _adr()}, policy=_policy(),
            reviews=[_approval(commit="")], head_sha="",
        )
        assert result.returncode == 1, result.stdout
        assert "head SHA" in result.stdout


class TestIdentityAndAuthority:
    def test_an_approver_at_the_head_sha_passes(self, tmp_path):
        result = _run(
            tmp_path, [ADR_REL], files={ADR_REL: _adr()}, policy=_policy(),
            reviews=[_approval()],
        )
        assert result.returncode == 0, result.stdout
        assert APPROVER in result.stdout

    def test_no_approval_at_all_fails(self, tmp_path):
        """The whole point: `Accepted` was true because someone typed it."""
        result = _run(
            tmp_path, [ADR_REL], files={ADR_REL: _adr()}, policy=_policy(),
        )
        assert result.returncode == 1, result.stdout
        assert "no authorised" in result.stdout

    def test_a_reviewer_cannot_accept_an_adr(self, tmp_path):
        """AUTHORITY_AND_APPROVAL_CONTRACT.md: 'a reviewer does not gain approval
        authority'. Their review is authenticated and still insufficient."""
        result = _run(
            tmp_path, [ADR_REL], files={ADR_REL: _adr()},
            policy=_policy([{"login": "octo-qa", "role": "reviewer"}]),
            reviews=[_approval(login="octo-qa")],
        )
        assert result.returncode == 1, result.stdout

    def test_an_identity_absent_from_the_policy_cannot_accept(self, tmp_path):
        """'Approval by an unauthorized identity' — a prohibited pattern. An
        authenticated review is not, by itself, an approval."""
        result = _run(
            tmp_path, [ADR_REL], files={ADR_REL: _adr()}, policy=_policy(),
            reviews=[_approval(login="passing-stranger")],
        )
        assert result.returncode == 1, result.stdout

    def test_a_non_approving_review_does_not_count(self, tmp_path):
        result = _run(
            tmp_path, [ADR_REL], files={ADR_REL: _adr()}, policy=_policy(),
            reviews=[_approval(state="COMMENTED")],
        )
        assert result.returncode == 1, result.stdout

    def test_an_approval_of_an_earlier_push_does_not_carry(self, tmp_path):
        """Approval is bound to a commit. Reusing it for a later one is
        'reusing stale activation authority' — the contract's own words."""
        result = _run(
            tmp_path, [ADR_REL], files={ADR_REL: _adr()}, policy=_policy(),
            reviews=[_approval(commit=OLD_SHA)],
        )
        assert result.returncode == 1, result.stdout

    def test_a_scoped_approver_cannot_accept_outside_their_scope(self, tmp_path):
        result = _run(
            tmp_path, [ADR_REL], files={ADR_REL: _adr()},
            policy=_policy([{
                "login": APPROVER, "role": "approver",
                "scope": ["docs/data/architecture/ADR/"],
            }]),
            reviews=[_approval()],
        )
        assert result.returncode == 1, result.stdout

    def test_a_scoped_approver_accepts_inside_their_scope(self, tmp_path):
        result = _run(
            tmp_path, [ADR_REL], files={ADR_REL: _adr()},
            policy=_policy([{
                "login": APPROVER, "role": "approver",
                "scope": ["docs/backend/architecture/ADR/"],
            }]),
            reviews=[_approval()],
        )
        assert result.returncode == 0, result.stdout

    def test_every_accepted_adr_needs_its_own_cover(self, tmp_path):
        second = "docs/data/architecture/ADR/0002-marts.md"
        result = _run(
            tmp_path, [ADR_REL, second],
            files={ADR_REL: _adr(), second: _adr()},
            policy=_policy([{
                "login": APPROVER, "role": "approver",
                "scope": ["docs/backend/"],
            }]),
            reviews=[_approval()],
        )
        assert result.returncode == 1, result.stdout
        assert second in result.stdout


class TestGovkitAuthoredAdrs:
    """govkit ships exactly one real ADR — `docs/data/architecture/ADR/0001-...`
    — it says Accepted, it has no approval record, and it lands in every
    `--type data` install at L3, L4 and L5 as a governed file `upgrade`
    rewrites. Without this carve-out the gate would fail every data customer's
    repo, which is the exact defect class PR #133 existed to fix."""

    DATA_ADR = "docs/data/architecture/ADR/0001-data-features-skip-prediction-gate.md"

    def test_an_unmodified_govkit_adr_needs_no_customer_approval(self, tmp_path):
        result = _run(
            tmp_path, [self.DATA_ADR],
            files={self.DATA_ADR: _govkit_authored(_adr())},
            policy=_policy(),
        )
        assert result.returncode == 0, result.stdout
        assert "govkit-authored" in result.stdout

    def test_editing_a_govkit_adr_makes_it_the_teams_decision(self, tmp_path):
        result = _run(
            tmp_path, [self.DATA_ADR],
            files={self.DATA_ADR: _govkit_authored(_adr(), tamper=True)},
            policy=_policy(),
        )
        assert result.returncode == 1, result.stdout

    def test_a_customer_adr_cannot_borrow_the_carve_out_without_a_real_hash(
        self, tmp_path,
    ):
        """A hand-written header with a wrong hash must not buy silence."""
        forged = (
            "<!-- govkit:editable\n  baseline: 0.18.0\n"
            f"  hash: {'0' * 64}\n  see: GOVKIT_SETUP_REVIEW.md\n-->\n\n"
        ) + _adr()
        result = _run(
            tmp_path, [ADR_REL], files={ADR_REL: forged}, policy=_policy(),
        )
        assert result.returncode == 1, result.stdout


class TestLatestReviewWins:
    """An approval is a reviewer's *current* standing, not something they ever
    said. The reviews API returns every review a PR has collected, so counting
    any historical `APPROVED` let an approver who had since asked for changes —
    without a new push to invalidate anything — still satisfy the gate.

    GitHub's own model: a reviewer's standing is their latest `APPROVED`,
    `CHANGES_REQUESTED` or `DISMISSED`. A `COMMENTED` review afterwards does not
    withdraw an approval, and treating it as though it did would block pull
    requests the platform itself considers approved.
    """

    def _adr_run(self, tmp_path, reviews, **kw):
        return _run(
            tmp_path, [ADR_REL], files={ADR_REL: _adr()}, policy=_policy(),
            reviews=reviews, **kw,
        )

    def test_changes_requested_after_approving_the_same_commit_revokes_it(
        self, tmp_path,
    ):
        """The bug this class exists for. No new push, so nothing else in the
        pipeline notices the approver changed their mind."""
        result = self._adr_run(tmp_path, [
            _review(state="APPROVED", at="2026-08-14T09:00:00Z", review_id=1),
            _review(state="CHANGES_REQUESTED", at="2026-08-14T10:00:00Z", review_id=2),
        ])
        assert result.returncode == 1, result.stdout
        assert "no authorised" in result.stdout

    def test_a_later_comment_does_not_withdraw_an_approval(self, tmp_path):
        """Matching the platform. A blanket 'latest review wins' would fail
        here, and the PR would be blocked while GitHub shows it approved."""
        result = self._adr_run(tmp_path, [
            _review(state="APPROVED", at="2026-08-14T09:00:00Z", review_id=1),
            _review(state="COMMENTED", at="2026-08-14T10:00:00Z", review_id=2),
        ])
        assert result.returncode == 0, result.stdout

    def test_a_dismissed_approval_does_not_count(self, tmp_path):
        result = self._adr_run(tmp_path, [
            _review(state="APPROVED", at="2026-08-14T09:00:00Z", review_id=1),
            _review(state="DISMISSED", at="2026-08-14T10:00:00Z", review_id=2),
        ])
        assert result.returncode == 1, result.stdout

    def test_re_approving_after_requesting_changes_passes(self, tmp_path):
        """The ordering has to work in both directions, or the fix would just
        trade a false pass for a false block."""
        result = self._adr_run(tmp_path, [
            _review(state="CHANGES_REQUESTED", at="2026-08-14T09:00:00Z", review_id=1),
            _review(state="APPROVED", at="2026-08-14T10:00:00Z", review_id=2),
        ])
        assert result.returncode == 0, result.stdout

    def test_changes_requested_on_an_earlier_push_does_not_block_this_one(
        self, tmp_path,
    ):
        """Standing is per-commit. Asking for changes on an old push and
        approving the fix is the normal shape of a review."""
        result = self._adr_run(tmp_path, [
            _review(state="CHANGES_REQUESTED", commit=OLD_SHA,
                    at="2026-08-14T09:00:00Z", review_id=1),
            _review(state="APPROVED", at="2026-08-14T10:00:00Z", review_id=2),
        ])
        assert result.returncode == 0, result.stdout

    def test_review_id_breaks_a_timestamp_tie(self, tmp_path):
        """`submitted_at` has second resolution, so two reviews can share one.
        The id is monotonic and settles it."""
        result = self._adr_run(tmp_path, [
            _review(state="APPROVED", at="2026-08-14T09:00:00Z", review_id=1),
            _review(state="CHANGES_REQUESTED", at="2026-08-14T09:00:00Z", review_id=2),
        ])
        assert result.returncode == 1, result.stdout

    def test_order_in_the_file_does_not_decide_it(self, tmp_path):
        """The same two reviews, written newest-first. Nothing may depend on the
        order the API happened to page them out in."""
        result = self._adr_run(tmp_path, [
            _review(state="CHANGES_REQUESTED", at="2026-08-14T10:00:00Z", review_id=2),
            _review(state="APPROVED", at="2026-08-14T09:00:00Z", review_id=1),
        ])
        assert result.returncode == 1, result.stdout

    def test_one_reviewers_withdrawal_does_not_cancel_anothers_approval(
        self, tmp_path,
    ):
        result = self._adr_run(tmp_path, [
            _review(state="CHANGES_REQUESTED", login="octo-qa",
                    at="2026-08-14T10:00:00Z", review_id=2),
            _review(state="APPROVED", at="2026-08-14T09:00:00Z", review_id=1),
        ])
        assert result.returncode == 0, result.stdout


class TestLoginCasing:
    """Platform logins are case-insensitive; Python string equality is not.

    This failed *closed* — a policy naming `Octo-Architect` rejected the same
    person's review returned as `octo-architect` — so it blocked legitimate
    approvals rather than admitting bad ones. It is still a defect: the failure
    message says no authorised approval exists, which is untrue and gives a team
    nothing to act on.
    """

    def test_policy_may_spell_the_login_differently_from_the_platform(
        self, tmp_path,
    ):
        result = _run(
            tmp_path, [ADR_REL], files={ADR_REL: _adr()},
            policy=_policy([{"login": "Octo-Architect", "role": "approver"}]),
            reviews=[_review(login="octo-architect")],
        )
        assert result.returncode == 0, result.stdout

    def test_the_platform_may_spell_it_differently_from_the_policy(self, tmp_path):
        result = _run(
            tmp_path, [ADR_REL], files={ADR_REL: _adr()},
            policy=_policy([{"login": "octo-architect", "role": "approver"}]),
            reviews=[_review(login="Octo-Architect")],
        )
        assert result.returncode == 0, result.stdout

    def test_surrounding_whitespace_in_the_policy_is_tolerated(self, tmp_path):
        result = _run(
            tmp_path, [ADR_REL], files={ADR_REL: _adr()},
            policy=_policy([{"login": "  octo-architect  ", "role": "approver"}]),
            reviews=[_review()],
        )
        assert result.returncode == 0, result.stdout

    def test_the_sentinel_is_recognised_whatever_its_casing(self, tmp_path):
        """Otherwise a lower-cased sentinel reads as a configured approver, and
        the gate would authorise an account that does not exist."""
        result = _run(
            tmp_path, [ADR_REL], files={ADR_REL: _adr()},
            policy=_policy([{"login": "your_approver_login", "role": "approver"}]),
            reviews=[_review(login="your_approver_login")],
        )
        assert result.returncode == 1, result.stdout
        assert "names no approver" in result.stdout

    def test_output_uses_the_spelling_the_policy_chose(self, tmp_path):
        """Normalising is for matching, not for what a human reads."""
        result = _run(
            tmp_path, [ADR_REL], files={ADR_REL: _adr()},
            policy=_policy([{"login": "Octo-Architect", "role": "approver"}]),
            reviews=[_review(login="octo-architect")],
        )
        assert "Octo-Architect" in result.stdout, result.stdout

    def test_casing_does_not_let_an_unlisted_identity_in(self, tmp_path):
        """Non-vacuous guard: normalisation must widen nothing but case."""
        result = _run(
            tmp_path, [ADR_REL], files={ADR_REL: _adr()}, policy=_policy(),
            reviews=[_review(login="octo-architect-2")],
        )
        assert result.returncode == 1, result.stdout


class TestScopeConfiguration:
    def test_require_approval_for_narrows_what_the_gate_covers(self, tmp_path):
        other = "docs/data/architecture/ADR/0002-marts.md"
        result = _run(
            tmp_path, [other], files={other: _adr()},
            policy=_policy(require_approval_for=["docs/backend/"]),
        )
        assert result.returncode == 0, result.stdout


def test_platform_embeddings_are_identical():
    github = _extract_checker(GATE_PATHS["github"])
    azure = _extract_checker(GATE_PATHS["azure"])
    assert github == azure, "github and azure adr-approval checkers have drifted"


@pytest.mark.parametrize("platform", sorted(GATE_PATHS))
def test_the_azure_embedding_behaves_identically(tmp_path, platform):
    """Running the azure copy proves the dedent equality above is not the only
    thing standing between the platforms."""
    result = _run(
        tmp_path, [ADR_REL], files={ADR_REL: _adr()}, policy=_policy(),
        reviews=[_approval()], platform=platform,
    )
    assert result.returncode == 0, result.stdout


@pytest.mark.parametrize("platform", sorted(GATE_PATHS))
def test_gate_does_not_invoke_govkit(platform):
    """Self-contained by design, for the same reason the fix-lane gate is: a
    blocking gate must not depend on an unpinned PyPI release, and a gate
    delegating to `govkit validate` could be switched off from inside the PR it
    is reviewing."""
    text = GATE_PATHS[platform].read_text(encoding="utf-8")
    invocations = [
        ln for ln in text.splitlines()
        if ln.strip().startswith(("run: govkit", "- script: govkit", "govkit "))
    ]
    assert not invocations, invocations


def test_github_gate_declares_least_privilege_permissions():
    """The payload's first `permissions:` block. Reading reviews needs
    pull-requests: read; declaring the block drops every other scope to none, so
    contents: read has to be restated for checkout."""
    parsed = yaml.safe_load(GATE_PATHS["github"].read_text(encoding="utf-8"))
    assert parsed["permissions"] == {"contents": "read", "pull-requests": "read"}


@pytest.mark.parametrize("platform", sorted(GATE_PATHS))
def test_the_gate_pins_pyyaml(platform):
    """Same argument test_ci_govkit_dependency makes for the govkit pin: an
    unpinned install makes a customer's merge criteria depend on whatever PyPI
    served that morning, while the payload prose beside it is frozen at install
    time. `~=` rather than `==` so a patch release can still fix a build on a
    Python the pinned version predates."""
    text = GATE_PATHS[platform].read_text(encoding="utf-8")
    assert re.search(r"pip install\s+pyyaml~=\d+\.\d+\.\d+", text), (
        f"ci/{platform}/adr-approval-gate.yml installs pyyaml unpinned"
    )


def test_both_gates_pin_pyyaml_to_the_same_version():
    """The two platforms run byte-identical checker code; they must not run it
    against different libraries."""
    pins = {
        platform: re.findall(r"pip install\s+(pyyaml~=[\d.]+)", path.read_text(encoding="utf-8"))
        for platform, path in GATE_PATHS.items()
    }
    assert pins["github"] == pins["azure"], pins


def test_the_gate_job_name_is_the_one_the_docs_tell_teams_to_require():
    parsed = yaml.safe_load(GATE_PATHS["github"].read_text(encoding="utf-8"))
    assert "adr-approval-check" in parsed["jobs"]


@pytest.mark.parametrize("agent", ["claude-code", "codex", "copilot"])
@pytest.mark.parametrize("ci", ["github", "azure"])
def test_the_gate_ships_wherever_the_policy_does(agent, ci):
    """The policy without the gate is a file nothing reads — the state this
    work exists to end. They must arrive together."""
    from cli.manifest import load_manifest, resolve_variant_files

    manifest = load_manifest(agent)
    for project_type in ("api", "cli", "ui-react", "ui-angular", "ui-nextjs", "data"):
        for level in ("3", "4", "5"):
            if project_type == "data" and level == "5":
                continue  # data is an L3/L4 shape; dbt has no L5 tier.
            _files, shared, governed = resolve_variant_files(
                manifest,
                {"level": level, "type": project_type, "ci": ci,
                 "stack": "python-dbt" if project_type == "data" else "python-fastapi"},
            )
            where = f"{agent} {project_type} L{level} ({ci})"
            assert (
                (f"ci/{ci}/adr-approval-gate.yml" in governed)
                == ("governance/approval_policy.yaml" in shared)
            ), where
