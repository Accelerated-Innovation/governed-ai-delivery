#!/usr/bin/env python3
# Copyright 2026 Accelerated Innovation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
"""Feature directories in a target project.

The single definition of "starter feature": govkit's bundled starters follow
the naming grammar `starter_{slug}` / `starter_{slug}_l5` (cmd_init derives
names inside it), so any features/ entry matching the prefix is govkit's, not
the team's. validate and upgrade both exclude starters through this module —
a starter added later needs no edits here or at the call sites.
"""

from __future__ import annotations

from pathlib import Path

_STARTER_PREFIX = "starter_"


def is_starter_feature(name: str) -> bool:
    """True when `name` is inside govkit's starter naming grammar."""
    return name.startswith(_STARTER_PREFIX)


def list_user_features(features_dir: Path) -> list[Path]:
    """Sorted team-authored feature dirs under `features_dir` — starters and
    dotdirs excluded. Empty when the dir is missing."""
    if not features_dir.exists():
        return []
    return sorted(
        d
        for d in features_dir.iterdir()
        if d.is_dir() and not is_starter_feature(d.name) and not d.name.startswith(".")
    )
