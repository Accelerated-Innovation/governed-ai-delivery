#!/usr/bin/env python3
# Copyright 2026 Accelerated Innovation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
"""Filesystem anchors — the dependency-free kernel of govkit.

Every other module resolves the bundled agents/, the repo root, and shared
help/copy constants from here. Keeping these in one leaf module (that imports
nothing internal) is what lets command and domain modules depend *inward*
without circular imports.

Tests that need to point govkit at a fake bundle patch the attributes on this
module (e.g. monkeypatch.setattr("cli.paths.AGENTS_DIR", ...)). Callers must
therefore reference `paths.AGENTS_DIR` at call time rather than copying the
name in with `from .paths import AGENTS_DIR` — a copied binding wouldn't see
the patch.
"""

from pathlib import Path

_HERE = Path(__file__).parent

# When installed via pip, agents/ is bundled inside the cli package.
# When running from the repo directly, fall back to the repo root.
AGENTS_DIR = _HERE / "agents" if (_HERE / "agents").exists() else _HERE.parent / "agents"
REPO_ROOT = AGENTS_DIR.parent

FEATURES_PREFIX = "features/"
TARGET_HELP = "Path to the target project root"
