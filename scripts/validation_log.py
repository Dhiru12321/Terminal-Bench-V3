#!/usr/bin/env python3
"""scripts/validation_log.py — append helper for the per-task validation log.

Spec: docs/exec-plans/instrumentation.md, Change Surface §
scripts/validation_log.py and False-positive risk § specs/<task-name>.md
absent or freshly renamed.

Public API:

    append_metrics_block(spec_path, block_text) -> bool

Reads the current `<task-name>-validation-log.md` next to the spec,
appends the rendered block, and writes atomically (tmp + rename).
Creates the log file if absent. Returns True on success, False when
the spec markdown is missing (the v1-grandfathering / CNI-back-burner
skip path — the metrics are still in
tasks/<task-name>/.step2b-metrics.jsonl, only the spec-side
rendering is skipped).

If the tmp + rename path fails (e.g., cross-filesystem rename), the
helper falls back to an fcntl-locked in-place append and logs the
degraded path to stderr. The fallback is sufficient because the
metrics file is append-only and the lock prevents concurrent
appenders from interleaving partial writes.
"""

from __future__ import annotations

import fcntl
import os
import sys
import tempfile
from pathlib import Path

VALIDATION_LOG_SUFFIX = "-validation-log.md"


def _log_path_for(spec_path: Path) -> Path:
    return spec_path.with_name(spec_path.stem + VALIDATION_LOG_SUFFIX)


def _compose(existing: str, block_text: str) -> str:
    """Append block_text to existing log content with a single
    blank-line separator. The validation log uses H2 entries (e.g.
    `## Attempt 1`, `## Per-task authoring metrics`) so a blank line
    between entries keeps markdown parsing happy."""
    if not existing:
        body = block_text
    else:
        normalized = existing if existing.endswith("\n") else existing + "\n"
        if not normalized.endswith("\n\n"):
            normalized = normalized + "\n"
        body = normalized + block_text
    if not body.endswith("\n"):
        body = body + "\n"
    return body


def append_metrics_block(spec_path: Path, block_text: str) -> bool:
    """Append a rendered metrics block to the spec's validation log.

    Returns True on success (block written), False on skip (spec
    markdown missing). Raises OSError only if both the tmp-rename
    and fcntl-locked fallback paths fail.
    """
    spec_path = Path(spec_path)
    if not spec_path.exists():
        print(
            "validation_log: skipping metrics block; "
            f"spec not found: {spec_path.name} "
            f"(searched {spec_path.parent})",
            file=sys.stderr,
        )
        return False

    log_path = _log_path_for(spec_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    existing = (
        log_path.read_text(encoding="utf-8") if log_path.exists() else ""
    )
    new_content = _compose(existing, block_text)

    tmp_fd, tmp_str = tempfile.mkstemp(
        prefix=log_path.name + ".",
        suffix=".tmp",
        dir=str(log_path.parent),
    )
    tmp_path = Path(tmp_str)
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as fh:
            fh.write(new_content)
        os.replace(tmp_path, log_path)
        return True
    except OSError as exc:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        print(
            f"validation_log: tmp+rename to {log_path.name} failed "
            f"({exc}); falling back to fcntl-locked in-place append",
            file=sys.stderr,
        )
        _append_with_lock(log_path, block_text)
        return True


def _append_with_lock(log_path: Path, block_text: str) -> None:
    """Cross-filesystem fallback: exclusive-mode append with fcntl
    advisory lock. The lock prevents two concurrent appenders from
    interleaving partial writes within the same degraded operation.
    """
    with open(log_path, "a", encoding="utf-8") as fh:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        try:
            if fh.tell() > 0:
                fh.write("\n")
            fh.write(block_text)
            if not block_text.endswith("\n"):
                fh.write("\n")
        finally:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
