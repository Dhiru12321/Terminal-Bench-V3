#!/usr/bin/env python3
"""Build a task-directory zip using the same skip rules as approve_task.

Phase B of ``scripts/check-task.sh`` calls this instead of the Info-ZIP
``zip`` CLI so preflight works on hosts without ``zip`` installed.

Keep ``PACKAGING_ZIP_X_PATTERNS_DOCUMENTED`` in sync with ``commands.md``
§ Packaging (machine-readable ``-x`` list); drift is caught by
``repo_tests/test_check_task_sh.py::test_phase_b_exclusions_match_commands_md``.
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path, PurePosixPath

# Script lives under ``scripts/``; repo modules (e.g. validate_submission_zip)
# live at the repository root. Tests also copy this file into a temp tree
# with sibling modules at the parent of ``scripts/``.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import validate_submission_zip  # noqa: E402

# Documented in commands.md ## Packaging — must match the -x glob list there.
PACKAGING_ZIP_X_PATTERNS_DOCUMENTED: frozenset[str] = frozenset(
    {
        "*/__pycache__/*",
        "*.pyc",
        ".*",
        "output_contract.toml",
        "quality_check_adjudication.json",
        "construction_manifest.json",
        "rubric.txt",
        "rubrics.txt",
        "CLAUDE.md",
        "*/CLAUDE.md",
        "AGENTS.md",
        "*/AGENTS.md",
        "skills.md",
        "*/skills.md",
        ".cursor/*",
        "*/.cursor/*",
        ".aider/*",
        "*/.aider/*",
        ".continue/*",
        "*/.continue/*",
        ".claude/*",
        "*/.claude/*",
    }
)


def should_skip_packaged_path(path: PurePosixPath) -> bool:
    """Same semantics as ``approve_task.should_skip_packaged_path``."""
    if ":Zone.Identifier" in path.as_posix():
        return True
    parts = path.parts
    if any(part == "__pycache__" for part in parts):
        return True
    if any(part.startswith(".") for part in parts):
        return True
    if path.suffix == ".pyc":
        return True
    if len(parts) == 1 and parts[0] in validate_submission_zip.FORBIDDEN_ROOT_FILES:
        return True
    return False


def _iter_packaged_files(task_dir: Path):
    task_dir = task_dir.resolve()
    for path in sorted(task_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = PurePosixPath(path.relative_to(task_dir).as_posix())
        if should_skip_packaged_path(rel):
            continue
        yield rel.as_posix(), path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Zip a task directory for validate_submission_zip preview.",
    )
    p.add_argument(
        "--task-dir",
        type=Path,
        required=True,
        help="Path to the task root (Edition 2 layout).",
    )
    p.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Path to the .zip to create (overwritten).",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    task_dir = args.task_dir.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if not task_dir.is_dir():
        raise SystemExit(f"task dir is not a directory: {task_dir}")
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()

    with zipfile.ZipFile(
        output,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=6,
    ) as zf:
        for arcname, path in _iter_packaged_files(task_dir):
            zf.write(path, arcname)


if __name__ == "__main__":
    main()
