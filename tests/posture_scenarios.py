"""Controlled synthetic repositories for reporting examples; never adoption evidence."""

import os
import subprocess

from cli.discovery import discover
from cli.maintenance import assess_repository
from cli.pack_loading import load_pack
from cli.pack_store import apply_install, preview_install
from cli.profiles import parse_profile
from tests.test_capability_packs import make_pack
from tests.test_maintenance import ci_evidence
from tests.test_pack_store import write_profile
from tests.test_release_metadata import AS_OF, metadata, project, release


def make_scenario(root, name):
    target = root / "consumer"
    pack = load_pack(make_pack(root / "source", skills=True))
    profile = project(pin="1.0" if name == "intentional-pin" else None).document
    profile["repository"]["id"] = "synthetic-posture-" + name
    profile["integrations"]["ci"] = "github"
    profile["maintenance"]["assessment_max_age_hours"] = 24
    if name == "required-upgrade":
        profile["maintenance"]["constraints"][0]["compatibility"] = ">=1.1,<3"
    path = write_profile(target, parse_profile(profile))
    apply_install(preview_install(path, target, (pack,), govkit_version="0.21.1"))
    (target / "policy.md").write_text("Synthetic accepted policy\n")
    for args in (
        ("init",),
        ("add", "."),
        (
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "-qm",
            "scenario",
        ),
    ):
        subprocess.run(
            ["git", "-C", str(target), *args],
            check=True,
            capture_output=True,
            env={**os.environ, "GIT_AUTHOR_DATE": AS_OF, "GIT_COMMITTER_DATE": AS_OF},
        )
    baseline = discover(target).document
    if name in ("resource-drift", "overlap"):
        (target / ".agents/skills/sample-help/SKILL.md").write_text(
            "Synthetic user customization\n"
        )
    if name in ("changed-needs", "overlap"):
        (target / "model.py").write_text("import openai\n")
    releases = [release("1.0")]
    if name in ("optional-update", "required-upgrade", "overlap"):
        releases.append(release("1.1"))
    if name in ("incompatible", "intentional-pin"):
        releases.append(
            release("2.0", requires_govkit=">=9" if name == "incompatible" else ">=0.21")
        )
    source = metadata(*releases)
    if name == "unavailable":
        source.update(lookup_status="unavailable", releases=[])
    if name == "stale":
        source["as_of"] = "2026-09-20T12:00:00Z"
    provider = None if name == "overlap" else ci_evidence(target)
    assessment = assess_repository(
        target, as_of=AS_OF, metadata=(source,), baseline=baseline, ci_report=provider
    )
    return target, assessment
