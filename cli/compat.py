#!/usr/bin/env python3
# Copyright 2026 Accelerated Innovation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
"""Compatibility rules for project type / maturity level combinations."""

from __future__ import annotations

import sys


_SUPPORTED_LEVELS_BY_TYPE = {
    "data": {"3", "4"},
}


def validate_level_type(
    level: str | None,
    type_value: str | None,
    context_flag: str = "--type",
) -> None:
    """Exit with a user-facing error when a type/level pair is unsupported."""
    if not level or not type_value:
        return
    supported = _SUPPORTED_LEVELS_BY_TYPE.get(type_value)
    if supported is None or level in supported:
        return

    levels = " and ".join(f"Level {value}" for value in sorted(supported))
    print(
        f"Error: {context_flag} {type_value} supports {levels} only "
        f"(requested level: {level}). "
        "Level 5 is GenAI Operations for LLM application delivery, not data projects.",
        file=sys.stderr,
    )
    sys.exit(1)
