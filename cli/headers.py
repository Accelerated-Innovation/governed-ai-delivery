#!/usr/bin/env python3
# Copyright 2026 Accelerated Innovation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
"""govkit:editable doc header helpers.

PR 1 / Chunk B. Editable docs installed by govkit carry a top-of-file
header that records the baseline they came from so:

  - doctor can detect when an installed doc is stale (D006)
  - edit-protection can decide whether overwriting is safe (A2)
  - stack apply can preserve team edits

The header is a plain markdown comment so it travels in source control and
renders invisibly in tooling that respects markdown comments.
"""

from pathlib import Path

_HEADER_START = "<!-- govkit:editable"
_HEADER_END = "-->"
_DEFAULT_SEE = "GOVKIT_SETUP_REVIEW.md"

# Managed-block markers (A6, codex). An agent whose only instruction mechanism
# is a shared file — codex's AGENTS.md — cannot have its governance moved to a
# separate namespace. Instead govkit fences its governance between these markers
# so a team's own content in the same file is preserved across upgrades.
GOVKIT_BLOCK_BEGIN = "<!-- BEGIN GOVKIT GOVERNANCE -->"
GOVKIT_BLOCK_END = "<!-- END GOVKIT GOVERNANCE -->"
_BLOCK_NOTE = (
    "<!-- Managed by govkit — content in this block is overwritten on "
    "`govkit upgrade`. Put your own instructions outside it. -->"
)


def upsert_govkit_block(
    existing: str | None, body: str, replace_unblocked: bool = False,
) -> str:
    """Return file content carrying govkit's governance in a managed block.

    - `existing is None` (no file yet) ⇒ just the block.
    - `existing` already contains a govkit block ⇒ the block's body is replaced
      in place; everything before and after it is preserved byte-for-byte.
    - `existing` has no block and `replace_unblocked` ⇒ the whole file is
      replaced by the block. Used when the existing file is govkit's own
      pre-block full-overwrite copy (nothing of the team's to keep).
    - `existing` has no block and not `replace_unblocked` ⇒ the block is
      appended below the team's content, which is preserved.
    """
    block = f"{GOVKIT_BLOCK_BEGIN}\n{_BLOCK_NOTE}\n{body.rstrip(chr(10))}\n{GOVKIT_BLOCK_END}\n"
    if existing is None or replace_unblocked and GOVKIT_BLOCK_BEGIN not in existing:
        return block

    b_idx = existing.find(GOVKIT_BLOCK_BEGIN)
    e_idx = existing.find(GOVKIT_BLOCK_END)
    if b_idx != -1 and e_idx != -1 and e_idx > b_idx:
        before = existing[:b_idx]
        after = existing[e_idx + len(GOVKIT_BLOCK_END):]
        return before + block.rstrip("\n") + after

    # Team file with no block: keep it, append govkit's block below.
    return existing.rstrip("\n") + "\n\n" + block


def format_editable_header(
    baseline: str,
    reason: str | None = None,
    see: str = _DEFAULT_SEE,
) -> str:
    """Produce the editable-header block as a string.

    The output ends with a blank line so it slots cleanly above a markdown
    body when prepended.
    """
    lines = [_HEADER_START, f"  baseline: {baseline}"]
    if reason:
        lines.append(f"  reason: {reason}")
    lines.append(f"  see: {see}")
    lines.append(_HEADER_END)
    return "\n".join(lines) + "\n\n"


def has_editable_header(content: str) -> bool:
    """True when `content` begins with an editable header (ignoring leading
    whitespace)."""
    return content.lstrip().startswith(_HEADER_START)


def parse_editable_header(content: str) -> dict | None:
    """Extract metadata from the editable header at the top of `content`.

    Returns a dict keyed by header field (e.g. `baseline`, `reason`, `see`),
    or None if no well-formed header is present.
    """
    if not has_editable_header(content):
        return None
    stripped = content.lstrip()
    end_idx = stripped.find(_HEADER_END)
    if end_idx == -1:
        return None
    block = stripped[len(_HEADER_START):end_idx]

    result: dict[str, str] = {}
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        result[key.strip()] = value.strip()
    return result


def _strip_existing_header(content: str) -> str:
    """Remove the leading editable header (if any) and one trailing blank
    line so a replacement header can be written without stacking."""
    if not has_editable_header(content):
        return content
    stripped = content.lstrip()
    end_idx = stripped.find(_HEADER_END)
    if end_idx == -1:
        return content
    body = stripped[end_idx + len(_HEADER_END):]
    # Drop the single newline immediately after --> plus an optional blank line
    # to keep formatting stable across rewrites.
    if body.startswith("\n"):
        body = body[1:]
    if body.startswith("\n"):
        body = body[1:]
    return body


def prepend_header_to_file(
    path: Path,
    baseline: str,
    reason: str | None = None,
    see: str = _DEFAULT_SEE,
) -> None:
    """Write the editable header to the top of a markdown file in place.

    Behavior:
      - Non-existent files are silently skipped (caller may have failed to
        copy the source; we don't want to compound errors).
      - Non-.md files are skipped (other formats can't host a markdown
        comment cleanly).
      - Files that already start with a header have it replaced, not stacked.
    """
    if not path.is_file():
        return
    if path.suffix.lower() != ".md":
        return

    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return

    body = _strip_existing_header(content)
    header = format_editable_header(baseline=baseline, reason=reason, see=see)
    path.write_text(header + body, encoding="utf-8")
