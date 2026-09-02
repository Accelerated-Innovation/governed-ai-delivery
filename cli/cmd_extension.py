#!/usr/bin/env python3
# Copyright 2026 Accelerated Innovation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
"""govkit extension — list bundled extension packs and add one to a project.

Extension packs ship with the wheel (cli/extension_packs/, force-included from
the repo's extensions/). `extension add` copies a pack into the target's
extensions/<id>/ folder, where govkit's existing discovery/validate already
operates. Mirrors the shape of `cmd_stack` (list + apply over a bundled set).

`extension add --from-git <url>` fetches a pack from a git repository whose
root carries a govkit manifest.yaml instead of using the bundled set. This is
the one place govkit touches the network, and only on this explicit opt-in —
`apply` and everything else stay offline. The fetched copy lands under the
target's extensions/<id>/ with the resolved commit recorded in
origin.upstream_ref, so the *project* holds the pin and later re-adds show
upstream changes as reviewable diffs.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

from . import paths
from .agent_layout import AGENT_LAYOUTS
from .extensions import (
    EXTENSIONS_DIR,
    MANIFEST_FILE,
    Extension,
    discover_extensions,
    discover_in,
    is_valid_extension_id,
    load_manifest,
    validate_extension,
)
from .marker import read_govkit_marker


def _bundled_packs() -> list:
    """Discover the bundled extension packs, skipping any with parse errors."""
    return [e for e in discover_in(paths.EXTENSION_PACKS_DIR) if not e.errors]


def _compat_warnings(manifest: dict, marker: dict) -> list[str]:
    """Return warn-and-proceed messages when the target's marker level/type is
    not covered by the pack's supported_levels / supported_project_types.
    Empty when compatible or when the pack declares no constraint."""
    warnings: list[str] = []
    level = marker.get("level")
    levels = manifest.get("supported_levels") or []
    if levels and level is not None:
        try:
            if int(level) not in [int(x) for x in levels]:
                warnings.append(
                    f"project level {level} is not in supported_levels {levels} "
                    "— installing anyway"
                )
        except (TypeError, ValueError):
            pass
    ptype = (marker.get("options") or {}).get("type")
    types = manifest.get("supported_project_types") or []
    if types and ptype is not None and ptype not in types:
        warnings.append(
            f"project type {ptype!r} is not in supported_project_types {types} "
            "— installing anyway"
        )
    return warnings


def cmd_extension_list(_args: argparse.Namespace) -> None:
    """Print every bundled extension pack (id, name, description, supported
    levels/types). Source of truth for what `govkit extension add` can install.
    """
    packs = _bundled_packs()
    if not packs:
        print("No bundled extension packs found.")
        return
    print("\nAvailable extension packs:\n")
    for ext in packs:
        m = ext.manifest
        print(f"  {ext.id:20s} {m.get('name', ext.id)}")
        desc = (m.get("description") or "").strip()
        if desc:
            print(f"  {'':20s}   {desc}")
        meta: list[str] = []
        levels = m.get("supported_levels") or []
        types = m.get("supported_project_types") or []
        if levels:
            meta.append("levels " + ",".join(str(x) for x in levels))
        if types:
            meta.append("types " + ",".join(types))
        if meta:
            print(f"  {'':20s}   ({'; '.join(meta)})")
    print(
        "\nAdd one to your project:\n"
        "  govkit extension add <id> --target <path>\n"
    )


def _resolve_dest(target: Path, pack) -> Path:
    """Return the safe install destination for a pack, or exit non-zero.

    Guards against a malformed manifest id (path separators, '..') escaping
    <target>/extensions/ before any rmtree/copytree.
    """
    if not is_valid_extension_id(pack.id):
        print(
            f"Error: extension id {pack.id!r} is not a valid identifier "
            "(must match ^[a-z0-9][a-z0-9-]*$); refusing to install.",
            file=sys.stderr,
        )
        sys.exit(1)
    ext_root = (target / EXTENSIONS_DIR).resolve()
    dest = target / EXTENSIONS_DIR / pack.id
    if not dest.resolve().is_relative_to(ext_root):
        print(
            f"Error: destination for '{pack.id}' resolves outside {ext_root}; refusing.",
            file=sys.stderr,
        )
        sys.exit(1)
    return dest


def _print_validation_notes(target: Path, ext_id: str) -> None:
    """Validate the just-installed pack in place; print any issues as non-fatal
    notes (warn and proceed)."""
    added = next((e for e in discover_extensions(target) if e.id == ext_id), None)
    if added is None:
        return
    issues = validate_extension(added, target)
    if not issues:
        return
    print(
        f"\nValidation notes ({len(issues)}) — "
        f"run `govkit doctor --target {target}` for detail:"
    )
    for issue in issues:
        print(f"  - {issue}")


def _install_pack_skills(
    pack_copy: Path,
    manifest: dict,
    target: Path,
    marker: dict | None,
    force: bool,
    previously_declared: set[str] | None = None,
) -> None:
    """Install the pack's declared skills[] into the applied agent's skills dir.

    Third-party skill dirs are NOT govkit's "files" category (unconditional
    overwrite): the team may have edited them or installed the same skill
    another way, and govkit never destroys what it cannot regenerate as its
    own. An existing destination is skipped unless --force; re-add with
    --force is the refresh path. The copy source is the target's own pack
    copy — extensions/<id>/ stays the source of truth.

    `previously_declared` carries the install_as names the replaced pack
    version declared; names it dropped are reported (never deleted) so a
    refresh cannot leave a removed skill active in silence.
    """
    skills = manifest.get("skills") or []
    agent = (marker or {}).get("agent")
    layout = AGENT_LAYOUTS.get(agent)
    if layout is None or layout.skills_dir is None:
        if skills:
            print(
                "  WARN: this pack declares agent skills, but no applied agent was "
                "found in the target. Run `govkit apply` first, then re-run "
                "`govkit extension add` with --force to install them."
            )
        return
    skills_base = target / layout.skills_dir
    skills_root = skills_base.resolve()
    declared_now: set[str] = set()
    for entry in skills:
        if not isinstance(entry, dict):
            continue
        path, install_as = entry.get("path"), entry.get("install_as")
        # Defense in depth: validation reports these as notes, but nothing
        # before this point refuses them — never let a bad manifest reach an
        # rmtree/copytree outside the pack copy or the skills dir.
        if not isinstance(path, str) or not is_valid_extension_id(install_as):
            print(f"  WARN: skipping invalid skills entry {entry!r}")
            continue
        declared_now.add(install_as)
        source = (pack_copy / path).resolve(strict=False)
        if not source.is_relative_to(pack_copy.resolve()) or not (source / "SKILL.md").is_file():
            print(f"  WARN: skipping skills entry with unsafe or empty path {path!r}")
            continue
        # fs ops use the UNRESOLVED dest: resolving first would follow a
        # symlink and point rmtree at whatever the link targets. The resolved
        # form is only the containment check.
        dest = skills_base / install_as
        if not dest.resolve(strict=False).is_relative_to(skills_root):
            print(f"  WARN: skipping skills entry {install_as!r} (unsafe destination)")
            continue
        if dest.is_symlink() or (dest.exists() and not dest.is_dir()):
            print(
                f"  WARN: {layout.skills_dir}/{install_as} exists but is not a "
                "regular directory — refusing to touch it."
            )
            continue
        if dest.exists():
            if not force:
                print(f"  skip: {layout.skills_dir}/{install_as}/ exists (use --force to refresh)")
                continue
            shutil.rmtree(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        # Same symlink rule as the git fetch: never dereference a pack's
        # symlink into the project.
        shutil.copytree(source, dest, ignore=_ignore_git_and_symlinks)
        print(f"  installed: {layout.skills_dir}/{install_as}/")
    for stale in sorted((previously_declared or set()) - declared_now):
        if is_valid_extension_id(stale) and (skills_base / stale).exists():
            print(
                f"  WARN: {layout.skills_dir}/{stale}/ was installed by the "
                "previous pack version but is no longer declared — remove it "
                "manually if it is unwanted."
            )


def _git(cmd: list[str], cwd: Path | None = None) -> str:
    """Run a git command; exit with the stderr on failure, and with an
    instruction to install git when the binary is absent."""
    try:
        return subprocess.run(
            ["git", *cmd], cwd=cwd, check=True, capture_output=True, text=True
        ).stdout.strip()
    except FileNotFoundError:
        print("Error: --from-git requires the `git` command on PATH.", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as exc:
        print(f"Error: git {cmd[0]} failed: {exc.stderr.strip()}", file=sys.stderr)
        sys.exit(1)


def _fetch_git_pack(url: str, ref: str | None, clone_dir: Path) -> tuple[Extension, str]:
    """Clone `url` (checked out at `ref` when given) and read the govkit
    manifest at its root. Returns the pack plus the resolved commit SHA —
    the pin recorded into the installed copy."""
    # A value starting with "-" would be parsed by git as an option
    # (e.g. --upload-pack=<cmd> executes a command); refuse it outright and
    # terminate option parsing with "--" as a second layer.
    for label, value in (("--from-git URL", url), ("--ref", ref)):
        if value is not None and value.startswith("-"):
            print(f"Error: {label} {value!r} must not start with '-'.", file=sys.stderr)
            sys.exit(1)
    _git(["clone", "--quiet", "--", url, str(clone_dir)])
    if ref:
        _git(["checkout", "--quiet", ref, "--"], cwd=clone_dir)
    sha = _git(["rev-parse", "HEAD"], cwd=clone_dir)

    manifest, err = load_manifest(clone_dir / MANIFEST_FILE)
    if manifest is None:
        print(
            f"Error: {url} does not carry a govkit extension pack — "
            f"expected {MANIFEST_FILE} at the repository root ({err}).",
            file=sys.stderr,
        )
        sys.exit(1)
    ext_id = manifest.get("id")
    if not is_valid_extension_id(ext_id):
        print(
            f"Error: the fetched manifest's id {ext_id!r} is not a valid "
            "extension id; refusing to install.",
            file=sys.stderr,
        )
        sys.exit(1)
    return Extension(id=ext_id, root=clone_dir, manifest=manifest), sha


def _ignore_git_and_symlinks(src: str, names: list[str]) -> set[str]:
    """copytree ignore for fetched repos: drop .git, and drop symlinks —
    dereferencing a hostile repo's symlink would copy files from the
    maintainer's machine into a folder that gets committed."""
    return {n for n in names if n == ".git" or (Path(src) / n).is_symlink()}


def _record_git_origin(dest: Path, url: str, sha: str) -> None:
    """Pin the fetch into the installed manifest's origin block. The project
    copy is the record — a later re-add shows upstream changes as a diff
    against exactly this commit."""
    manifest_path = dest / MANIFEST_FILE
    manifest, err = load_manifest(manifest_path)
    if manifest is None:  # pragma: no cover — the fetch already loaded it
        print(f"  WARN: could not record origin pin: {err}")
        return
    raw_origin = manifest.get("origin")
    # A remote manifest is untrusted input: a non-mapping origin (e.g.
    # `origin: hostile`) must degrade to an empty block, not crash the add
    # after the previous pack copy was already replaced.
    origin = dict(raw_origin) if isinstance(raw_origin, dict) else {}
    origin["upstream_url"] = url
    origin["upstream_ref"] = sha
    origin.setdefault("license", "unknown")
    manifest["origin"] = origin
    manifest_path.write_text(
        yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )


def _add_pack(
    pack: Extension,
    target: Path,
    force: bool,
    git_origin: tuple[str, str] | None = None,
) -> None:
    """Shared tail of `extension add`: copy the pack into the target, warn on
    marker mismatches, install declared skills, validate in place."""
    dest = _resolve_dest(target, pack)

    if dest.exists() and not force:
        print(
            f"Error: '{dest}' already exists. Re-run with --force to overwrite.",
            file=sys.stderr,
        )
        sys.exit(1)

    previously_declared: set[str] = set()
    if dest.exists():
        # Remember what the replaced pack version declared, so skills it
        # dropped can be reported after the refresh (reported, not deleted).
        old_manifest, _ = load_manifest(dest / MANIFEST_FILE)
        for entry in (old_manifest or {}).get("skills") or []:
            if isinstance(entry, dict) and isinstance(entry.get("install_as"), str):
                previously_declared.add(entry["install_as"])
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    # Never dereference a pack's symlinks into the project — that would copy
    # arbitrary files from the machine into a committed folder. Applies to
    # bundled and hand-vendored packs the same as to git fetches.
    shutil.copytree(pack.root, dest, ignore=_ignore_git_and_symlinks)

    print(f"\nAdding extension '{pack.id}' to {target}")
    name = pack.manifest.get("name", pack.id)
    if name != pack.id:
        print(f"  {name}")
    if git_origin is not None:
        url, sha = git_origin
        _record_git_origin(dest, url, sha)
        print(f"  pinned: {url} @ {sha}")

    marker = read_govkit_marker(target)
    if marker:
        for warning in _compat_warnings(pack.manifest, marker):
            print(f"  WARN: {warning}")

    _install_pack_skills(
        dest, pack.manifest, target, marker, force,
        previously_declared=previously_declared,
    )

    print(f"Done. Extension '{pack.id}' added to {dest}")
    _print_validation_notes(target, pack.id)


def cmd_extension_add(args: argparse.Namespace) -> None:
    """Copy an extension pack into <target>/extensions/<id>/ — a bundled pack
    by id, or any git repository carrying a root manifest.yaml via --from-git.

    Refuses to clobber an existing folder without --force. After copying,
    validates the pack in place and surfaces any issues as non-fatal notes
    (e.g. a generative pack's L5 `relates_to.extends` paths missing in a
    non-L5 project) — warn and proceed.
    """
    target = Path(args.target).resolve()
    if not target.is_dir():
        print(f"Error: target directory '{target}' does not exist.", file=sys.stderr)
        sys.exit(1)

    from_git = getattr(args, "from_git", None)
    if from_git:
        with tempfile.TemporaryDirectory() as tmp:
            pack, sha = _fetch_git_pack(
                from_git, getattr(args, "ref", None), Path(tmp) / "pack"
            )
            _add_pack(pack, target, args.force, git_origin=(from_git, sha))
        return

    pack = next((e for e in _bundled_packs() if e.id == args.extension_id), None)
    if pack is None:
        print(
            f"Error: extension '{args.extension_id}' not found. "
            f"Run `govkit extension list` to see available packs.",
            file=sys.stderr,
        )
        sys.exit(1)
    _add_pack(pack, target, args.force)


def register(subparsers) -> None:
    """Register the `extension` subcommand tree (`extension list`, `extension add`)."""
    ext_parser = subparsers.add_parser(
        "extension",
        help="List or add bundled extension packs",
    )
    ext_sub = ext_parser.add_subparsers(dest="extension_command", required=True)

    list_parser = ext_sub.add_parser("list", help="List bundled extension packs")
    list_parser.set_defaults(func=cmd_extension_list)

    add_parser = ext_sub.add_parser(
        "add", help="Add a bundled or remote extension pack to a project"
    )
    add_parser.add_argument(
        "extension_id",
        nargs="?",
        help="Bundled extension pack id (e.g. vision-inference). "
        "See `govkit extension list`. Omit when using --from-git.",
    )
    add_parser.add_argument(
        "--from-git",
        metavar="URL",
        help="Fetch the pack from a git repository whose root carries a "
        "govkit manifest.yaml, instead of the bundled set. The resolved "
        "commit is recorded in the installed manifest's origin.upstream_ref.",
    )
    add_parser.add_argument(
        "--ref",
        help="Commit SHA, tag, or branch to check out with --from-git "
        "(default: the repository's default branch head).",
    )
    add_parser.add_argument("--target", required=True, help=paths.TARGET_HELP)
    add_parser.add_argument(
        "--force", action="store_true",
        help="Overwrite an existing extensions/<id>/ folder",
    )
    add_parser.set_defaults(func=_cmd_extension_add_dispatch)


def _cmd_extension_add_dispatch(args: argparse.Namespace) -> None:
    """Argument cross-checks argparse can't express, then the real handler."""
    if bool(args.extension_id) == bool(args.from_git):
        print(
            "Error: give exactly one of a bundled pack id or --from-git <url>.",
            file=sys.stderr,
        )
        sys.exit(2)
    if args.ref and not args.from_git:
        print("Error: --ref only applies with --from-git.", file=sys.stderr)
        sys.exit(2)
    cmd_extension_add(args)
