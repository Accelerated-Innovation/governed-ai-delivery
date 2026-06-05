#!/usr/bin/env python3
# Copyright 2026 Accelerated Innovation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
govkit — governed AI delivery kit installer

Usage:
    govkit apply --agent claude-code --target /path/to/project
    govkit apply --agent claude-code --level 3 --type api --ci github --target /path/to/project
    govkit list
    govkit init my_feature --target /path/to/project
    govkit init my_feature --starter backend --target /path/to/project
    govkit validate --target /path/to/project
"""

from __future__ import annotations

import argparse

from .calibrate import register as _register_calibrate
from .cmd_apply import register as _register_apply
from .cmd_extension import register as _register_extension
from .cmd_init import register as _register_init
from .cmd_list import register as _register_list
from .cmd_stack import register as _register_stack
from .cmd_upgrade import register as _register_upgrade
from .cmd_validate import register as _register_validate
from .doctor import register as _register_doctor

# Subcommand registrars. Each command module owns its argparse surface and
# binds its handler via `set_defaults(func=...)`. Adding a command = create its
# module with a register(subparsers) function and list it here.
_REGISTRARS = (
    _register_apply,
    _register_list,
    _register_stack,
    _register_extension,
    _register_init,
    _register_doctor,
    _register_calibrate,
    _register_validate,
    _register_upgrade,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="govkit",
        description="governed AI delivery kit — apply spec scaffolding to a project",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for register in _REGISTRARS:
        register(subparsers)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
