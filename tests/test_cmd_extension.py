"""Tests for `govkit extension` — listing and adding bundled extension packs.

Increment 1 (this file): packaging path resolution + `extension list`.
Later increments add `extension add` (copy + overwrite guard + compat warning).
"""

import argparse

from cli import paths
from cli.cmd_extension import cmd_extension_list


def test_extension_packs_dir_exists_and_has_bundled_packs():
    """EXTENSION_PACKS_DIR resolves to the bundled packs (repo: extensions/;
    wheel: cli/extension_packs/). Both reference copies must be discoverable."""
    assert paths.EXTENSION_PACKS_DIR.is_dir(), f"{paths.EXTENSION_PACKS_DIR} should exist"
    ids = {
        p.name
        for p in paths.EXTENSION_PACKS_DIR.iterdir()
        if p.is_dir() and not p.name.startswith(".")
    }
    assert {"agentic-skills", "vision-inference"} <= ids, f"bundled packs missing; found {ids}"


def test_extension_list_prints_bundled_packs(capsys):
    cmd_extension_list(argparse.Namespace())
    out = capsys.readouterr().out
    assert "vision-inference" in out
    assert "agentic-skills" in out


def test_extension_list_shows_supported_levels_and_types(capsys):
    """The list is the source of truth for `govkit extension add` — it must
    surface supported levels/types so a user can judge applicability."""
    cmd_extension_list(argparse.Namespace())
    out = capsys.readouterr().out
    # vision-inference declares api/cli and levels 4,5
    assert "api" in out
    assert "4" in out and "5" in out
