# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Explicit create-only report artifacts outside protected checkouts."""

import os
from pathlib import Path

from .pipeline_files import bound_pipeline_files
from .schema_validation import DocumentError, canonical_json


def publish_assessment(document, target, output):
    """Create one private artifact outside the assessed repository, without overwriting."""
    target, output = Path(target).resolve(), Path(output).absolute()
    if output.resolve().is_relative_to(target):
        raise DocumentError("Assessment output must be outside the assessed repository")
    data = (canonical_json(document) + "\n").encode()
    with bound_pipeline_files(output.parent) as files:
        parent = files.parent(output.name)
        staged = parent.stage(data)
        files.verify()
        # A hard link publishes atomically and refuses existing destinations, including symlinks.
        os.link(
            staged,
            output.name,
            src_dir_fd=parent.descriptor,
            dst_dir_fd=parent.descriptor,
            follow_symlinks=False,
        )
        try:
            files.verify()
        except (OSError, ValueError):
            if (
                os.stat(output.name, dir_fd=parent.descriptor, follow_symlinks=False).st_ino
                == os.stat(staged, dir_fd=parent.descriptor).st_ino
            ):
                parent.unlink(output.name)
            raise
