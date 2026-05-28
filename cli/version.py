#!/usr/bin/env python3
# Copyright 2026 Accelerated Innovation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
"""Installed package version — single source of truth.

Isolated in its own leaf module so the marker writer (cli/marker.py) and the
upgrade flow (cli/govkit.py) can both stamp/compare the version without
importing each other.
"""

try:
    from importlib.metadata import version as _pkg_version

    GOVKIT_VERSION = _pkg_version("govkit")
except Exception:
    GOVKIT_VERSION = "dev"
