"""Actual Git changes cannot narrow accepted governance requirements (I07)."""

import json
import shutil
import subprocess

import pytest

from cli.change_conformance import inspect_change, load_change_report
from cli.change_scope import capture_change
from cli.check_models import State
from cli.pack_loading import bundled_catalog
from cli.pack_store import apply_install, preview_install
from cli.version import GOVKIT_VERSION
from cli.workflow_store import plan_request
from cli.workflows import parse_request
from tests.test_discovery import write
from tests.test_pack_store import snapshot
from tests.test_workflows import install, request


def git(target, *args):
    return subprocess.run(
        ["git", "-C", str(target), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def setup(tmp_path, *, llm=False, transitions=(), extra_checks=()):
    target, trusted = tmp_path / "consumer", tmp_path / "trusted-policy"
    target.mkdir()
    trusted.mkdir()
    capabilities = ["application-governance", "gherkin-delivery"] + (
        ["llm-evaluation"] if llm else []
    )
    install(trusted, capabilities=capabilities)
    profile_path = trusted / ".govkit/profile.yaml"
    profile = json.loads(profile_path.read_text())
    profile["policy"]["conformance"] = {"reference": "conformance.json", "authority": "accepted"}
    profile["policy"]["transitions"] = list(transitions)
    # Unknown mandatory checks are deliberately retained even without providers.
    profile["policy"]["workflows"] = [
        {
            "id": "always",
            "source": {"reference": "policy.md", "authority": "accepted"},
            "when": ["*"],
            "additional_checks": list(extra_checks),
        }
    ]
    profile_path.write_text(json.dumps(profile))
    config = {
        "schema_version": 1,
        "impact_rules": [
            {"paths": ["src", "docs"], "impacts": {}},
            {"paths": ["src/auth"], "impacts": {"auth": True}},
        ],
        "artifacts": [
            {"id": name, "references": ["docs/" + name.replace(":", "-") + ".md"]}
            for name in [
                "spec",
                "plan",
                "architecture-preflight",
                "test-plan",
                "validation",
                "architecture-decision",
                "transition-plan",
                "review:architecture",
                "review:auth",
            ]
        ],
        "commands": [
            {
                "id": "project:tests",
                "argv": [
                    "{python}",
                    "-c",
                    "from pathlib import Path; assert 'good' in Path('src/service.py').read_text()",
                ],
                "timeout_seconds": 10,
            }
        ],
        "constraints": [
            {
                "id": "boundary",
                "source": "architecture.md",
                "paths": ["src"],
                "forbidden_text": ["import forbidden"],
            }
        ],
    }
    write(trusted, "conformance.json", json.dumps(config))
    apply_install(
        preview_install(profile_path, trusted, bundled_catalog(), govkit_version=GOVKIT_VERSION)
    )
    write(target, "src/service.py", "# good\n")
    for artifact in config["artifacts"]:
        write(target, artifact["references"][0], "# Existing accepted evidence\n")
    write(target, "results.json", '{"cases":[{"id":"hello","expected":"hi","actual":"hi"}]}')
    git(target, "init", "-q")
    git(target, "config", "user.email", "test@example.invalid")
    git(target, "config", "user.name", "Test")
    git(target, "add", ".")
    git(target, "commit", "-qm", "baseline")
    base = git(target, "rev-parse", "HEAD")
    return target, trusted, base


def result(report, identifier):
    return next(r for r in report.checks.results if r.spec.id == identifier)


def inspect(target, trusted, base, doc=None, **kwargs):
    return inspect_change(
        target,
        parse_request(doc or request()),
        base=base,
        policy_target=trusted,
        observed_at="2026-09-23T12:00:00Z",
        **kwargs,
    )


def test_actual_git_scope_includes_staged_unstaged_untracked_and_deleted(tmp_path):
    target, trusted, base = setup(tmp_path)
    write(target, "src/service.py", "# good changed\n")
    write(target, "src/staged.py", "# staged\n")
    git(target, "add", "src/staged.py")
    write(target, "src/new.py", "# untracked\n")
    (target / "docs/spec.md").unlink()
    before = snapshot(target)
    change = capture_change(target, base)
    assert change.complete
    assert set(change.paths) == {"src/service.py", "src/staged.py", "src/new.py", "docs/spec.md"}
    assert {c.status for c in change.changes} == {"added", "modified", "deleted"}
    assert change.digest == capture_change(target, base).digest
    assert snapshot(target) == before


@pytest.mark.parametrize(
    "kind,workflow",
    [("enhancement", "bounded"), ("refactor", "bounded"), ("feature", "full-feature")],
)
def test_proportional_checks_pass_and_fail_on_actual_code(tmp_path, kind, workflow):
    target, trusted, base = setup(tmp_path)
    write(target, "src/service.py", "# good updated\n")
    before = snapshot(target), snapshot(trusted)
    report = inspect(target, trusted, base, request(kind), execute_checks=("project:tests",))
    assert report.plan.document["workflow"] == workflow
    assert report.exit_code == 0
    assert result(report, "project:tests").outcome.state is State.PASS
    assert (snapshot(target), snapshot(trusted)) == before
    write(target, "src/service.py", "# broken\n")
    failing = inspect(target, trusted, base, request(kind), execute_checks=("project:tests",))
    assert failing.exit_code == 1 and result(failing, "project:tests").outcome.state is State.FAIL
    assert failing.checks.identity.change_digest != report.checks.identity.change_digest


def test_local_and_ci_inputs_produce_identical_replayable_json(tmp_path):
    target, trusted, base = setup(tmp_path)
    write(target, "src/service.py", "# good next\n")
    local = inspect(target, trusted, base, execute_checks=("project:tests",))
    ci = inspect(target, trusted, base, execute_checks=("project:tests",))
    assert local.to_json() == ci.to_json()
    record = write(tmp_path, "report.json", local.to_json())
    assert load_change_report(record).to_json() == local.to_json()
    document = json.loads(record.read_text())
    document["exit_code"] = 0 if local.exit_code else 1
    record.write_text(json.dumps(document))
    with pytest.raises(ValueError):
        load_change_report(record)


def test_stale_plan_and_auth_changes_cannot_hide_controls(tmp_path):
    target, trusted, base = setup(tmp_path, extra_checks=["security:mandatory"])
    old = plan_request(trusted, parse_request(request()))
    write(target, "src/auth/login.py", "# new auth logic\n")
    report = inspect(target, trusted, base, previous=old)
    assert report.exit_code == 1
    assert report.plan.document["workflow"] == "full-feature"
    assert result(report, "review:auth").outcome.state is State.UNKNOWN
    assert result(report, "security:mandatory").outcome.state is State.UNKNOWN
    assert result(report, "change:plan").outcome.state is State.FAIL
    assert {r.spec.id for r in report.checks.results} >= {"artifact:spec", "artifact:validation"}


def test_edited_target_policy_does_not_weaken_trusted_requirements(tmp_path):
    target, trusted, base = setup(tmp_path, extra_checks=["security:mandatory"])
    write(target, ".govkit/profile.yaml", '{"policy":{"required_checks":[]}}')
    report = inspect(target, trusted, base)
    assert result(report, "security:mandatory").spec.required
    assert result(report, "security:mandatory").outcome.state is State.UNKNOWN
    assert report.exit_code == 1


def test_unclassified_and_out_of_scope_paths_block_even_without_prior_plan(tmp_path):
    target, trusted, base = setup(tmp_path)
    write(target, "other/new.py", "# hidden expansion\n")
    report = inspect(target, trusted, base)
    assert report.exit_code == 1
    assert result(report, "change:scope").outcome.state is State.FAIL
    assert result(report, "change:plan").outcome.state is State.FAIL


def test_missing_required_artifact_and_unexecuted_tests_cannot_pass(tmp_path):
    target, trusted, base = setup(tmp_path)
    (target / "docs/spec.md").unlink()
    report = inspect(target, trusted, base, request("feature"))
    assert result(report, "artifact:spec").outcome.state is State.FAIL
    assert result(report, "project:tests").outcome.state is State.SKIPPED
    assert report.exit_code == 1


def test_llm_control_runs_independently_and_failure_is_visible(tmp_path):
    target, trusted, base = setup(tmp_path, llm=True)
    doc = request(llm=True)
    before = snapshot(target), snapshot(trusted)
    report = inspect(
        target,
        trusted,
        base,
        doc,
        execute_checks=("project:tests", "llm-exact-match"),
        pack_arguments={"llm-exact-match": ("--results", "results.json")},
    )
    assert report.plan.document["workflow"] == "bounded"
    assert result(report, "llm-exact-match").outcome.state is State.PASS
    assert report.exit_code == 0
    assert (snapshot(target), snapshot(trusted)) == before
    write(target, "results.json", '{"cases":[{"id":"hello","expected":"hi","actual":"wrong"}]}')
    bad = inspect(
        target,
        trusted,
        base,
        doc,
        execute_checks=("llm-exact-match",),
        pack_arguments={"llm-exact-match": ("--results", "results.json")},
    )
    assert result(bad, "llm-exact-match").outcome.state is State.FAIL


def test_repository_controls_scan_unchanged_files(tmp_path):
    target, trusted, base = setup(tmp_path)
    write(target, "src/old.py", "import forbidden\n")
    git(target, "add", ".")
    git(target, "commit", "-qm", "existing violation")
    base = git(target, "rev-parse", "HEAD")
    write(target, "src/service.py", "# good tiny change\n")
    report = inspect(target, trusted, base, execute_checks=("project:tests",))
    assert result(report, "change:architecture").outcome.state is State.FAIL
    assert any(
        f.code == "existing-violation" and f.location == "src/old.py"
        for f in result(report, "change:architecture").outcome.findings
    )


def transition(expires="2026-12-31"):
    return {
        "id": "ports",
        "source": {"reference": "policy.md", "authority": "accepted"},
        "scope": ["src"],
        "mode": "improve",
        "applies_to": "new-and-changed",
        "current": [
            {"source": {"reference": "architecture.md", "authority": "accepted"}, "scope": ["src"]}
        ],
        "target": [
            {"source": {"reference": "target.md", "authority": "accepted"}, "scope": ["src"]}
        ],
        "exceptions": [
            {
                "id": "old",
                "source": {"reference": "policy.md", "authority": "accepted"},
                "scope": ["src/old.py"],
                "expires_at": expires,
            }
        ],
    }


def configure_transition(trusted):
    write(trusted, "target.md", "# Accepted target\n")
    path = trusted / "conformance.json"
    config = json.loads(path.read_text())
    config["constraints"].append(
        {
            "id": "target",
            "source": "target.md",
            "paths": ["src"],
            "forbidden_text": ["import legacy"],
        }
    )
    path.write_text(json.dumps(config))


def test_transition_exceptions_do_not_excuse_new_or_expired_violations(tmp_path):
    target, trusted, base = setup(tmp_path, transitions=[transition()])
    configure_transition(trusted)
    write(target, "src/old.py", "import forbidden\nimport legacy\n")
    git(target, "add", ".")
    git(target, "commit", "-qm", "baseline exception")
    base = git(target, "rev-parse", "HEAD")
    old = inspect(target, trusted, base)
    arch = result(old, "change:architecture").outcome
    assert arch.state is State.PASS
    assert any(f.code == "existing-exception" for f in arch.findings)
    write(target, "src/old.py", "import forbidden\nimport forbidden\nimport legacy\n")
    new = inspect(target, trusted, base)
    assert result(new, "change:architecture").outcome.state is State.FAIL
    assert any(
        f.code == "new-violation" for f in result(new, "change:architecture").outcome.findings
    )
    write(target, "src/old.py", "import forbidden\nimport legacy\n")
    expired = inspect_change(
        target,
        parse_request(request()),
        base=base,
        policy_target=trusted,
        observed_at="2027-01-01T00:00:00Z",
    )
    assert result(expired, "change:architecture").outcome.state is State.FAIL
    assert any(
        f.code == "expired-exception"
        for f in result(expired, "change:architecture").outcome.findings
    )


def test_architecture_approval_stays_unknown_locally(tmp_path):
    target, trusted, base = setup(tmp_path)
    report = inspect(
        target,
        trusted,
        base,
        request("architecture", architecture=True),
        execute_checks=("project:tests",),
    )
    assert result(report, "approval:architecture").outcome.state is State.UNKNOWN
    assert report.exit_code == 1


def test_bad_base_and_symlink_have_no_silent_scope_pass(tmp_path):
    target, trusted, base = setup(tmp_path)
    assert not capture_change(target, "--help").complete
    (tmp_path / "outside.py").write_text("secret")
    (target / "src/link.py").symlink_to(tmp_path / "outside.py")
    change = capture_change(target, base)
    assert not change.complete
    assert b"secret" not in change.files.values()
    report = inspect(target, trusted, base)
    assert result(report, "change:scope").outcome.state is State.UNKNOWN
    assert report.exit_code == 1


def test_invalid_execution_selection_is_rejected_before_any_command(tmp_path):
    target, trusted, base = setup(tmp_path)
    with pytest.raises(ValueError, match="selected"):
        inspect(target, trusted, base, execute_checks=("project:tests", "change:scope"))


def test_uncovered_contract_paths_remain_unmeasured(tmp_path):
    target, trusted, base = setup(tmp_path)
    path = trusted / "conformance.json"
    config = json.loads(path.read_text())
    config["constraints"][0]["paths"] = ["src/other"]
    path.write_text(json.dumps(config))
    report = inspect(target, trusted, base, execute_checks=("project:tests",))
    assert result(report, "change:architecture").outcome.state is State.UNKNOWN
    assert report.exit_code == 1


def test_changes_during_checks_invalidate_the_captured_state(tmp_path):
    target, trusted, base = setup(tmp_path)
    path = trusted / "conformance.json"
    config = json.loads(path.read_text())
    config["commands"][0]["argv"] = [
        "{python}",
        "-c",
        "from pathlib import Path; Path('src/service.py').write_text('mutated after capture')",
    ]
    path.write_text(json.dumps(config))
    report = inspect(target, trusted, base, execute_checks=("project:tests",))
    assert result(report, "project:tests").outcome.state is State.PASS
    assert result(report, "change:stable-inputs").outcome.state is State.FAIL
    assert report.exit_code == 1


def test_change_cli_rejects_filters_and_renders_the_same_report(tmp_path, monkeypatch, capsys):
    import sys

    from cli.govkit import main

    target, trusted, base = setup(tmp_path)
    source = write(tmp_path, "request.json", json.dumps(request()))
    args = [
        "govkit",
        "conform",
        "--target",
        str(target),
        "--request",
        str(source),
        "--base",
        base,
        "--policy-target",
        str(trusted),
        "--observed-at",
        "2026-09-23T12:00:00Z",
        "--execute-check",
        "project:tests",
        "--json",
    ]
    monkeypatch.setattr(sys, "argv", args)
    main()
    document = json.loads(capsys.readouterr().out)
    assert document["kind"] == "change-results" and document["exit_code"] == 0
    monkeypatch.setattr(sys, "argv", args + ["--path", "docs"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2


def test_saved_plan_content_tampering_cannot_remove_required_checks(tmp_path):
    target, trusted, base = setup(tmp_path)
    previous = plan_request(trusted, parse_request(request()))
    document = previous.document
    document["checks"] = []
    path = write(tmp_path, "tampered.json", json.dumps(document))
    from cli.workflow_store import load_workflow_plan

    with pytest.raises(ValueError, match="replay"):
        load_workflow_plan(path)


def test_constraints_outside_transition_scope_cannot_grant_exceptions(tmp_path):
    t = transition()
    t["scope"] = ["src/inside"]
    target, trusted, base = setup(tmp_path, transitions=[t])
    configure_transition(trusted)
    write(target, "src/old.py", "import forbidden\n")
    git(target, "add", ".")
    git(target, "commit", "-qm", "outside transition")
    report = inspect(target, trusted, git(target, "rev-parse", "HEAD"))
    assert result(report, "change:architecture").outcome.state is State.FAIL
    assert not any(
        f.code == "existing-exception"
        for f in result(report, "change:architecture").outcome.findings
    )


def test_defect_retains_existing_eligibility_and_executed_red_green_evidence(tmp_path):
    from tests.test_fixes import _valid_record

    target, trusted, base = setup(tmp_path)
    doc = request("defect")
    doc["references"] = [
        {"kind": "established-behavior", "reference": "architecture.md", "authority": "accepted"},
        {"kind": "regression-test", "reference": "tests/test_service.py", "authority": "observed"},
    ]
    shutil.copy(trusted / "architecture.md", target / "architecture.md")
    write(target, "tests/test_service.py", "# existing regression\n")
    record = _valid_record("restore")
    record["expectation"]["source"] = "architecture.md"
    record["reproduction"]["test"] = "tests/test_service.py"
    record["surface"]["paths"] = ["src/service.py"]
    fix_path = write(target, "fixes/restore/fix.yaml", json.dumps(record))
    config_path = trusted / "conformance.json"
    config = json.loads(config_path.read_text())
    config["artifacts"].append({"id": "fix-record", "references": ["fixes/restore/fix.yaml"]})
    config_path.write_text(json.dumps(config))
    write(target, "src/service.py", "# broken baseline\n")
    git(target, "add", ".")
    git(target, "commit", "-qm", "reproduce bug")
    base = git(target, "rev-parse", "HEAD")
    write(target, "src/service.py", "# good fixed\n")
    before = snapshot(target), snapshot(trusted)
    report = inspect(
        target, trusted, base, doc, execute_checks=("project:tests", "defect:eligibility")
    )
    assert report.plan.document["workflow"] == "defect"
    assert result(report, "defect:eligibility").outcome.state is State.PASS
    assert report.exit_code == 0 and (snapshot(target), snapshot(trusted)) == before
    record["risk"]["security_auth"] = True
    fix_path.write_text(json.dumps(record))
    git(target, "add", "fixes/restore/fix.yaml")
    git(target, "commit", "-qm", "invalid eligibility baseline")
    invalid = inspect(target, trusted, git(target, "rev-parse", "HEAD"), doc)
    assert result(invalid, "defect:eligibility").outcome.state is State.FAIL


def test_inspection_without_execution_cannot_claim_defect_red_green(tmp_path):
    target, trusted, base = setup(tmp_path)
    doc = request("defect")
    doc["references"] = [
        {"kind": "established-behavior", "reference": "architecture.md", "authority": "accepted"},
        {"kind": "regression-test", "reference": "tests/test_service.py", "authority": "observed"},
    ]
    report = inspect(target, trusted, base, doc)
    assert result(report, "defect:eligibility").outcome.state is not State.PASS
    assert report.exit_code == 1


def test_exception_cannot_escape_its_current_contract_scope(tmp_path):
    t = transition()
    t["current"][0]["scope"] = ["src/inside"]
    target, trusted, base = setup(tmp_path, transitions=[t])
    configure_transition(trusted)
    write(target, "src/old.py", "import forbidden\n")
    git(target, "add", ".")
    git(target, "commit", "-qm", "old violation outside current scope")
    report = inspect(target, trusted, git(target, "rev-parse", "HEAD"))
    assert result(report, "change:architecture").outcome.state is State.FAIL
    assert not any(
        f.code == "existing-exception"
        for f in result(report, "change:architecture").outcome.findings
    )


def test_policy_change_between_configuration_and_plan_cannot_pass(tmp_path, monkeypatch):
    import cli.change_conformance as module

    target, trusted, base = setup(tmp_path)
    original = module.load_change_policy

    def changing(*args):
        value = original(*args)
        path = trusted / "conformance.json"
        config = json.loads(path.read_text())
        config["constraints"][0]["forbidden_text"] = ["good"]
        path.write_text(json.dumps(config))
        return value

    monkeypatch.setattr(module, "load_change_policy", changing)
    report = inspect(target, trusted, base, execute_checks=("project:tests",))
    assert report.exit_code == 1
    assert result(report, "change:policy").outcome.state is not State.PASS
    assert result(report, "project:tests").outcome.state is State.UNKNOWN


def test_invalid_contract_scope_is_unmeasured_not_vacuous_pass(tmp_path):
    target, trusted, base = setup(tmp_path)
    path = trusted / ".govkit/profile.yaml"
    profile = json.loads(path.read_text())
    profile["policy"]["contracts"][0]["scope"] = ["src/**"]
    path.write_text(json.dumps(profile))
    apply_install(preview_install(path, trusted, bundled_catalog(), govkit_version=GOVKIT_VERSION))
    report = inspect(target, trusted, base)
    assert result(report, "change:policy").outcome.state is State.UNKNOWN
    assert report.exit_code == 1


@pytest.mark.parametrize(
    "name", ["defect", "enhancement", "refactor", "mcp", "llm", "feature", "architecture"]
)
def test_bundled_pilot_pass_failure_and_local_ci_equivalence(tmp_path, name):
    from tests.wheel_change_smoke import run_pilot

    run_pilot(tmp_path, name)


def test_timeout_is_unknown_and_shared_test_provider_runs_only_once(tmp_path, monkeypatch):
    import cli.change_conformance as module

    target, trusted, base = setup(tmp_path)
    original = module.subprocess.run
    attempted = []

    def execute(argv, **kwargs):
        if argv[0] == module.sys.executable:
            attempted.append(argv)
            raise subprocess.TimeoutExpired(argv, 10)
        return original(argv, **kwargs)

    monkeypatch.setattr(module.subprocess, "run", execute)
    report = inspect(target, trusted, base, execute_checks=("project:tests",))
    assert len(attempted) == 1
    assert result(report, "project:tests").outcome.state is State.UNKNOWN
    assert report.exit_code == 1


def test_saved_change_report_cannot_change_plan_execution_identity(tmp_path):
    target, trusted, base = setup(tmp_path)
    report = inspect(target, trusted, base)
    document = report.document
    document["checks"]["identity"]["resolution_digest"] = "0" * 64
    path = write(tmp_path, "wrong-plan.json", json.dumps(document))
    with pytest.raises(ValueError, match="identit"):
        load_change_report(path)


def test_policy_required_full_delivery_is_enforced_on_a_small_change(tmp_path):
    target, trusted, base = setup(tmp_path)
    path = trusted / ".govkit/profile.yaml"
    profile = json.loads(path.read_text())
    profile["policy"]["workflows"][0]["required_capabilities"] = ["gherkin-delivery"]
    path.write_text(json.dumps(profile))
    apply_install(preview_install(path, trusted, bundled_catalog(), govkit_version=GOVKIT_VERSION))
    good = inspect(target, trusted, base, execute_checks=("project:tests",))
    assert good.plan.document["workflow"] == "full-feature" and good.exit_code == 0
    (target / "docs/spec.md").unlink()
    bad = inspect(target, trusted, base, execute_checks=("project:tests",))
    assert result(bad, "artifact:spec").outcome.state is State.FAIL


def test_exception_without_observed_time_never_passes_expiry(tmp_path):
    target, trusted, base = setup(tmp_path, transitions=[transition()])
    configure_transition(trusted)
    write(target, "src/old.py", "import forbidden\n")
    git(target, "add", ".")
    git(target, "commit", "-qm", "existing exception")
    report = inspect_change(
        target,
        parse_request(request()),
        base=git(target, "rev-parse", "HEAD"),
        policy_target=trusted,
    )
    assert result(report, "change:architecture").outcome.state is State.UNKNOWN
    assert report.exit_code == 1


def test_executable_mode_change_is_included_in_snapshot_identity(tmp_path):
    target, trusted, base = setup(tmp_path)
    path = target / "src/service.py"
    path.write_text("# good changed\n")
    path.chmod(0o644)
    before = capture_change(target, base)
    path.chmod(0o755)
    after = capture_change(target, base)
    assert before.complete and after.complete
    assert before.paths == after.paths
    assert before.digest != after.digest


def test_pack_execution_does_not_reread_an_unverified_lock(tmp_path, monkeypatch):
    import cli.pack_store as module

    target, trusted, base = setup(tmp_path, llm=True)
    original = module._read_lock
    calls = []

    def read(*args, **kwargs):
        calls.append(1)
        assert len(calls) == 1, "Execution reread the verified lock"
        return original(*args, **kwargs)

    monkeypatch.setattr(module, "_read_lock", read)
    completed = module.execute_check(
        trusted, "llm-exact-match", ("--results", "results.json"), working_directory=target
    )
    assert completed.returncode == 0 and len(calls) == 1


def test_command_arguments_may_repeat_without_weakening_policy(tmp_path):
    target, trusted, base = setup(tmp_path)
    path = trusted / "conformance.json"
    config = json.loads(path.read_text())
    config["commands"][0]["argv"] += ["same", "same"]
    path.write_text(json.dumps(config))
    report = inspect(target, trusted, base, execute_checks=("project:tests",))
    assert report.exit_code == 0
