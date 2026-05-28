#!/usr/bin/env python3
# Copyright 2026 Accelerated Innovation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
"""govkit validate — check per-feature governance compliance in a project."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .validate import run_validation


def cmd_validate(args: argparse.Namespace) -> None:
    target = Path(args.target).resolve()
    level = args.level
    strict = getattr(args, "strict", False)
    sys.exit(run_validation(target, level=level, strict=strict))
