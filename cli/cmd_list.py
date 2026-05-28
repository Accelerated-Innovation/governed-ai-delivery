#!/usr/bin/env python3
# Copyright 2026 Accelerated Innovation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
"""govkit list — show available agents and their variant options."""

from __future__ import annotations

import argparse
import json

from . import paths


def cmd_list(_args: argparse.Namespace) -> None:
    print("\nAvailable agents:\n")
    for agent_dir in sorted(paths.AGENTS_DIR.iterdir()):
        if not agent_dir.is_dir():
            continue
        manifest_path = agent_dir / "manifest.json"
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as e:
                print(f"  Warning: failed to read {manifest_path}: {e}")
                continue
            name = manifest["agent"]
            desc = manifest.get("description", "")
            options = manifest.get("options", {})
            if options:
                opts_summary = " | ".join(
                    f"{k}: {', '.join(v['choices'])}" for k, v in options.items()
                )
                print(f"  {name:<20} {desc}")
                print(f"  {'':20} options: {opts_summary}")
            else:
                print(f"  {name:<20} {desc}")
    print()
