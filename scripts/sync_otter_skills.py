#!/usr/bin/env python3
# Copyright 2026 Accelerated Innovation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
"""Re-vendor the otter-skills extension pack from a pinned upstream commit.

DEV-TIME ONLY. govkit has no network access at install time and must keep
none — this script runs on a maintainer's machine to refresh
extensions/otter-skills/ from https://github.com/tottinge/otter-skills,
then the result ships in the wheel like any other bundled pack.

    python scripts/sync_otter_skills.py --sha <40-hex> --upstream-version <v>

What it does:
  1. Clones upstream into a temp dir and checks out the given SHA (verified
     against `git rev-parse HEAD` — a branch name or short SHA is refused).
  2. Replaces the pack's skills/ with plugins/otter-skills/skills/*,
     excluding each skill's agents/ subdir (OpenAI agent-builder config no
     govkit-supported agent consumes).
  3. Copies the plugin-level LICENSE and NOTICE to the pack root so the
     Apache-2.0 attribution travels with every copy `extension add` makes.
  4. Regenerates manifest.yaml (this script owns that file: provenance,
     version, and the skills list are derived, so a re-run at the same SHA
     is a no-op) and rewrites the provenance block in the pack README.

Idempotence check: running at the currently-pinned SHA must leave
`git diff` empty.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PACK_DIR = REPO_ROOT / "extensions" / "otter-skills"
UPSTREAM_URL = "https://github.com/tottinge/otter-skills"
UPSTREAM_PLUGIN = "plugins/otter-skills"
INSTALL_PREFIX = "otter-"

MANIFEST_TEMPLATE = """\
id: otter-skills
name: Otter Skills (third-party)
version: {version}
description: >-
  Seven engineering-craft agent skills (unit testing, atomic commits, story
  splitting, naming, legacy-code safety, refactoring review) vendored from
  tottinge/otter-skills. Installs into your agent's skills directory as
  otter-<skill>.
govkit_min_version: 0.0.0
extension_type: skills
contract_sets: []
origin:
  upstream_url: {url}
  upstream_ref: {sha}
  upstream_version: {version}
  license: Apache-2.0
  license_files: [LICENSE, NOTICE]
skills:
{skills}"""

PROVENANCE_START = "<!-- sync:provenance -->"
PROVENANCE_END = "<!-- /sync:provenance -->"


def _run(args: list[str], cwd: Path | None = None) -> str:
    return subprocess.run(
        args, cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


def sync(sha: str, upstream_version: str) -> None:
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        sys.exit("Error: --sha must be a full 40-hex commit SHA (the pin must be exact).")

    with tempfile.TemporaryDirectory() as tmp:
        clone = Path(tmp) / "otter-skills"
        _run(["git", "clone", "--quiet", UPSTREAM_URL, str(clone)])
        _run(["git", "checkout", "--quiet", sha], cwd=clone)
        head = _run(["git", "rev-parse", "HEAD"], cwd=clone)
        if head != sha:
            sys.exit(f"Error: checkout resolved to {head}, not the requested {sha}.")

        plugin = clone / UPSTREAM_PLUGIN
        pack_skills = PACK_DIR / "skills"
        if pack_skills.exists():
            shutil.rmtree(pack_skills)
        for skill_dir in sorted((plugin / "skills").iterdir()):
            if not skill_dir.is_dir():
                continue
            shutil.copytree(
                skill_dir,
                pack_skills / skill_dir.name,
                ignore=shutil.ignore_patterns("agents"),
            )
        for name in ("LICENSE", "NOTICE"):
            shutil.copyfile(plugin / name, PACK_DIR / name)

    skill_names = sorted(p.name for p in pack_skills.iterdir() if p.is_dir())
    skills_yaml = "".join(
        f"  - path: skills/{name}\n    install_as: {INSTALL_PREFIX}{name}\n"
        for name in skill_names
    )
    (PACK_DIR / "manifest.yaml").write_text(
        MANIFEST_TEMPLATE.format(
            version=upstream_version, url=UPSTREAM_URL, sha=sha, skills=skills_yaml
        ),
        encoding="utf-8",
    )

    readme = PACK_DIR / "README.md"
    provenance = (
        f"{PROVENANCE_START}\n"
        f"| Upstream | {UPSTREAM_URL} |\n"
        f"|---|---|\n"
        f"| Pinned commit | `{sha}` |\n"
        f"| Upstream version | {upstream_version} |\n"
        f"| License | Apache-2.0 (LICENSE and NOTICE ship in this pack) |\n"
        f"{PROVENANCE_END}"
    )
    text = readme.read_text(encoding="utf-8")
    pattern = re.compile(
        re.escape(PROVENANCE_START) + ".*?" + re.escape(PROVENANCE_END), re.DOTALL
    )
    if not pattern.search(text):
        sys.exit(f"Error: {readme} has no {PROVENANCE_START} block to rewrite.")
    readme.write_text(pattern.sub(provenance, text), encoding="utf-8")

    print(f"Vendored {len(skill_names)} skills at {sha}.")
    print(
        "Now: review `git diff`, update the pinned SHA in NOTICE.md if it "
        "changed, add a CHANGELOG entry, and run the test suite."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sha", required=True, help="Full upstream commit SHA to vendor.")
    parser.add_argument(
        "--upstream-version", required=True,
        help="Upstream plugin version (plugins/otter-skills/.claude-plugin/plugin.json).",
    )
    args = parser.parse_args()
    sync(args.sha, args.upstream_version)


if __name__ == "__main__":
    main()
