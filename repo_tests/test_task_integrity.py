"""Regression tests for scripts/task_integrity.py — the shared checksum module.

The module is the single source of truth for the `.step2b-checksum`
sentinel that scripts/check-task.sh writes (Phase C) and scripts/approve_task.py
verifies before packaging. These tests pin:
  - the round-trip behavior on a clean task tree
  - the diff messages for added / removed / modified files
  - the missing-sentinel and forged-JSON failure paths
  - the parity between the file-selection predicate here and the
    dotfile/pycache exclusion in approve_task.should_skip_packaged_path
  - the CLI exit codes (so scripts/check-task.sh can rely on them)
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path, PurePosixPath

from scripts import approve_task
from scripts import task_integrity


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "scripts/task_integrity.py"


def _seed_task_tree(root: Path) -> dict[str, bytes]:
    """Build a minimal task tree under `root` and return the bytes
    written for each tracked file (path -> bytes)."""
    files = {
        "instruction.md": b"Repair the imaginary widget.\n",
        "task.toml": b'artifacts = ["/app/output.txt"]\n',
        "environment/Dockerfile": b"FROM python:3.12-slim\nWORKDIR /app\n",
        "environment/src/app.py": b"def main():\n    return 0\n",
        "solution/solve.sh": b"#!/usr/bin/env bash\nexit 0\n",
        "tests/test.sh": b"#!/usr/bin/env bash\npytest -q\n",
        "tests/test_outputs.py": b"def test_x():\n    assert True\n",
    }
    for rel, payload in files.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    return files


class TaskIntegrityRegressionTest(unittest.TestCase):
    def test_round_trip_clean(self) -> None:
        """Writing a manifest then immediately verifying must succeed."""
        with tempfile.TemporaryDirectory() as tmp:
            task_dir = Path(tmp)
            _seed_task_tree(task_dir)

            sentinel = task_integrity.write_step2b_checksum(task_dir)
            self.assertTrue(sentinel.exists(), "write must produce a sentinel file")
            self.assertEqual(sentinel.name, task_integrity.CHECKSUM_FILE_NAME)

            ok, msg = task_integrity.verify_step2b_checksum(task_dir)
            self.assertTrue(ok, msg)
            self.assertIn("verified", msg)

    def test_modified_file_detected(self) -> None:
        """Modifying any tracked task file must surface in the diff message."""
        with tempfile.TemporaryDirectory() as tmp:
            task_dir = Path(tmp)
            _seed_task_tree(task_dir)
            task_integrity.write_step2b_checksum(task_dir)

            (task_dir / "instruction.md").write_bytes(b"Different now.\n")

            ok, msg = task_integrity.verify_step2b_checksum(task_dir)
            self.assertFalse(ok, msg)
            self.assertIn("modified", msg)
            self.assertIn("instruction.md", msg)

    def test_added_file_detected(self) -> None:
        """A file that did not exist at write time must be reported as added."""
        with tempfile.TemporaryDirectory() as tmp:
            task_dir = Path(tmp)
            _seed_task_tree(task_dir)
            task_integrity.write_step2b_checksum(task_dir)

            (task_dir / "environment/src/extra.py").write_bytes(
                b"def added():\n    return None\n"
            )

            ok, msg = task_integrity.verify_step2b_checksum(task_dir)
            self.assertFalse(ok, msg)
            self.assertIn("added", msg)
            self.assertIn("environment/src/extra.py", msg)

    def test_removed_file_detected(self) -> None:
        """A file that disappeared after write must be reported as removed."""
        with tempfile.TemporaryDirectory() as tmp:
            task_dir = Path(tmp)
            _seed_task_tree(task_dir)
            task_integrity.write_step2b_checksum(task_dir)

            (task_dir / "tests/test_outputs.py").unlink()

            ok, msg = task_integrity.verify_step2b_checksum(task_dir)
            self.assertFalse(ok, msg)
            self.assertIn("removed", msg)
            self.assertIn("tests/test_outputs.py", msg)

    def test_missing_sentinel_handled(self) -> None:
        """Verifying without a sentinel must point the contributor to
        scripts/check-task.sh (the actionable next step)."""
        with tempfile.TemporaryDirectory() as tmp:
            task_dir = Path(tmp)
            _seed_task_tree(task_dir)

            ok, msg = task_integrity.verify_step2b_checksum(task_dir)
            self.assertFalse(ok)
            self.assertIn(task_integrity.CHECKSUM_FILE_NAME, msg)
            self.assertIn("check-task.sh", msg)

    def test_forged_json_handled(self) -> None:
        """A sentinel that is not valid JSON must produce a parse-error
        message rather than crashing."""
        with tempfile.TemporaryDirectory() as tmp:
            task_dir = Path(tmp)
            _seed_task_tree(task_dir)
            sentinel = task_dir / task_integrity.CHECKSUM_FILE_NAME
            sentinel.write_text("this is not json {{{")

            ok, msg = task_integrity.verify_step2b_checksum(task_dir)
            self.assertFalse(ok)
            self.assertIn(task_integrity.CHECKSUM_FILE_NAME, msg)

    def test_predicate_parity_with_packaging_skip(self) -> None:
        """`_is_tracked_task_file` must agree with
        `approve_task.should_skip_packaged_path` on the dotfile / pycache /
        pyc rules. If they ever drift, the packager could ship files that
        weren't in the manifest at write time (or vice versa).

        The synthetic tree intentionally omits FORBIDDEN_ROOT_FILES
        (output_contract.toml, quality_check_adjudication.json, etc.) —
        those are an additional packaging-only restriction and are out of
        scope for the checksum-vs-package parity assertion.
        """
        with tempfile.TemporaryDirectory() as tmp:
            task_dir = Path(tmp)
            relative_paths = [
                "instruction.md",
                "task.toml",
                "environment/src/app.py",
                "environment/data/sample.json",
                "solution/solve.sh",
                "tests/test_outputs.py",
                ".gitignore",
                ".hidden_root_file",
                ".tooling/state.json",
                "environment/.cache/build.log",
                "environment/__pycache__/app.cpython-312.pyc",
                "tests/__pycache__/test.cpython-312.pyc",
                "environment/src/app.cpython-312.pyc",
                "environment/.dotdir/nested/file.txt",
            ]
            for rel in relative_paths:
                target = task_dir / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(b"x")

            for rel in relative_paths:
                target = task_dir / rel
                rel_posix = PurePosixPath(target.relative_to(task_dir).as_posix())
                packaging_skips = approve_task.should_skip_packaged_path(rel_posix)
                manifest_tracks = task_integrity._is_tracked_task_file(
                    target, task_dir
                )
                self.assertEqual(
                    manifest_tracks,
                    not packaging_skips,
                    msg=(
                        f"predicate disagreement on {rel}: "
                        f"_is_tracked_task_file={manifest_tracks}, "
                        f"should_skip_packaged_path={packaging_skips}"
                    ),
                )

    def test_dotfile_excluded_including_sentinel_itself(self) -> None:
        """The sentinel is a dotfile and must be excluded from the
        manifest — otherwise the manifest would contain a hash of itself
        and verification would always fail on second write."""
        with tempfile.TemporaryDirectory() as tmp:
            task_dir = Path(tmp)
            _seed_task_tree(task_dir)
            sentinel = task_integrity.write_step2b_checksum(task_dir)

            manifest = json.loads(sentinel.read_text())
            self.assertNotIn(task_integrity.CHECKSUM_FILE_NAME, manifest)
            for key in manifest:
                self.assertFalse(
                    key.startswith("."),
                    f"manifest unexpectedly contains a dotfile entry: {key}",
                )
                self.assertFalse(
                    key.endswith(".pyc"),
                    f"manifest unexpectedly contains a .pyc entry: {key}",
                )
                self.assertNotIn(
                    "__pycache__",
                    key.split("/"),
                    f"manifest unexpectedly contains a __pycache__ entry: {key}",
                )

    def test_cli_write_and_verify_exit_codes(self) -> None:
        """The CLI is the entry point for scripts/check-task.sh Phase C
        and scripts/approve_task.py error reporting; its exit codes must be:
          - write on a clean tree: 0
          - verify on a clean tree: 0
          - verify after a modification: 1
        """
        with tempfile.TemporaryDirectory() as tmp:
            task_dir = Path(tmp)
            _seed_task_tree(task_dir)

            write = subprocess.run(
                [sys.executable, str(MODULE_PATH), "write", str(task_dir)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(write.returncode, 0, write.stderr)

            verify_clean = subprocess.run(
                [sys.executable, str(MODULE_PATH), "verify", str(task_dir)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(verify_clean.returncode, 0, verify_clean.stderr)

            (task_dir / "instruction.md").write_bytes(b"changed\n")

            verify_dirty = subprocess.run(
                [sys.executable, str(MODULE_PATH), "verify", str(task_dir)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(verify_dirty.returncode, 1, verify_dirty.stdout)


if __name__ == "__main__":
    unittest.main()
