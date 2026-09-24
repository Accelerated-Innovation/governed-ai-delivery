# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Directory-bound pipeline writes; pathname swaps cannot redirect operations."""

from __future__ import annotations

import os
import secrets
import stat
from contextlib import contextmanager
from pathlib import Path

from .schema_validation import DocumentError

SUPPORTED = all(
    operation in os.supports_dir_fd
    for operation in (os.open, os.mkdir, os.stat, os.rename, os.unlink, os.rmdir)
) and all(hasattr(os, flag) for flag in ("O_DIRECTORY", "O_NOFOLLOW", "O_NONBLOCK"))


class BoundDirectory:
    def __init__(self, descriptor):
        self.descriptor = descriptor
        self.staged = set()

    def read(self, name):
        try:
            descriptor = os.open(
                name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=self.descriptor
            )
        except FileNotFoundError:
            return None, None
        with os.fdopen(descriptor, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode):
                raise DocumentError("Pipeline destination is not a regular file")
            content = stream.read(4 * 1024 * 1024 + 1)
            if len(content) > 4 * 1024 * 1024:
                raise DocumentError("Pipeline destination exceeds 4 MiB")
        return content, info

    def stage(self, content, previous=None, *, restore_time=False):
        name = ".govkit-stage-" + secrets.token_hex(16)
        descriptor = os.open(
            name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=self.descriptor,
        )
        self.staged.add(name)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            if previous is not None:
                os.fchmod(stream.fileno(), previous.st_mode & 0o777)
                if restore_time:
                    os.utime(stream.fileno(), ns=(previous.st_atime_ns, previous.st_mtime_ns))
            os.fsync(stream.fileno())
        return name

    def replace(self, staged, name):
        os.replace(staged, name, src_dir_fd=self.descriptor, dst_dir_fd=self.descriptor)
        self.staged.remove(staged)

    def unlink(self, name):
        os.unlink(name, dir_fd=self.descriptor)

    def clean(self):
        for name in self.staged:
            try:
                self.unlink(name)
            except FileNotFoundError:
                pass


class PipelineFiles:
    def __init__(self):
        self.descriptors = []
        self.links = []
        self.directories = {}
        self.created = []

    def _directory(self, parent, name, *, create=False):
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        created = False
        try:
            descriptor = os.open(name, flags, dir_fd=parent)
        except FileNotFoundError:
            if not create:
                raise
            try:
                os.mkdir(name, dir_fd=parent)
                created = True
            except FileExistsError:
                pass
            descriptor = os.open(name, flags, dir_fd=parent)
        self.descriptors.append(descriptor)
        self.links.append((parent, name, descriptor))
        if created:
            self.created.append((parent, name, descriptor))
        return descriptor

    def open_target(self, target):
        if not SUPPORTED:
            raise DocumentError(
                "Safe pipeline generation requires no-follow directory-descriptor support"
            )
        target = Path(target)
        if not target.is_absolute() or ".." in target.parts:
            raise DocumentError("Pipeline target must be absolute without parent traversal")
        root = os.open(target.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        self.descriptors.append(root)
        for part in target.parts[1:]:
            root = self._directory(root, part)
        self.directories[()] = BoundDirectory(root)

    def parent(self, relative):
        parts = Path(relative).parts
        if Path(relative).is_absolute() or ".." in parts:
            raise DocumentError("Invalid relative pipeline destination")
        key = ()
        for part in parts[:-1]:
            parent = self.directories[key].descriptor
            key += (part,)
            if key not in self.directories:
                self.directories[key] = BoundDirectory(self._directory(parent, part, create=True))
        return self.directories[key]

    @staticmethod
    def _matches(parent, name, descriptor):
        current = os.stat(name, dir_fd=parent, follow_symlinks=False)
        opened = os.fstat(descriptor)
        return stat.S_ISDIR(current.st_mode) and (current.st_dev, current.st_ino) == (
            opened.st_dev,
            opened.st_ino,
        )

    def verify(self):
        if not all(self._matches(*link) for link in self.links):
            raise DocumentError("Pipeline directory changed during generation")

    def close(self):
        try:
            for directory in self.directories.values():
                directory.clean()
            for parent, name, descriptor in reversed(self.created):
                try:
                    if self._matches(parent, name, descriptor):
                        os.rmdir(name, dir_fd=parent)
                except OSError:
                    # Keep nonempty or concurrently changed directories.
                    pass
        finally:
            for descriptor in reversed(self.descriptors):
                os.close(descriptor)


@contextmanager
def bound_pipeline_files(target):
    files = PipelineFiles()
    try:
        files.open_target(target)
        yield files
    finally:
        files.close()
