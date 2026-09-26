# Copyright 2026 Accelerated Innovation
# Licensed under the Apache License, Version 2.0.
"""Validated internal Git capture budgets; these do not establish policy authority."""

from dataclasses import dataclass

DEFAULT_MAX_FILE_BYTES = 1024 * 1024
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_FILES = 2048
MAX_TOTAL_BYTES = 16 * 1024 * 1024
MAX_CHANGED_PATHS = 256


@dataclass(frozen=True, slots=True)
class ObservationLimits:
    """Bound one capture. Smaller companion bounds support internal callers/tests.

    Accepted-policy configuration exposes only the per-file value (ADR 0018).
    """

    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES
    max_files: int = MAX_FILES
    max_total_bytes: int = MAX_TOTAL_BYTES
    max_changed_paths: int = MAX_CHANGED_PATHS

    def __post_init__(self):
        for name, ceiling in (
            ("max_file_bytes", MAX_FILE_BYTES),
            ("max_files", MAX_FILES),
            ("max_total_bytes", MAX_TOTAL_BYTES),
            ("max_changed_paths", MAX_CHANGED_PATHS),
        ):
            value = getattr(self, name)
            if type(value) is not int or not 1 <= value <= ceiling:
                raise ValueError(
                    f"Invalid observation limit {name}: expected an integer from 1 to {ceiling}"
                )


DEFAULT_OBSERVATION_LIMITS = ObservationLimits()
