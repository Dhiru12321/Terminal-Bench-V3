from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from scripts import task_gate


class TaskGateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="task-gate-test-"))
        self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)
        self.task_dir = self.tmpdir / "tasks" / "fixture"
        self.task_dir.mkdir(parents=True)
        self.report_dir = self.tmpdir / "reports"
        self._old_build = task_gate.build_gate_specs
        self.addCleanup(self._restore_build_specs)

    def _restore_build_specs(self) -> None:
        task_gate.build_gate_specs = self._old_build

    def _set_specs(self, specs: list[dict]) -> None:
        task_gate.build_gate_specs = lambda task_dir, strict: specs  # type: ignore[assignment]

    def test_captures_reports_and_stops_on_fail(self) -> None:
        self._set_specs(
            [
                {
                    "name": "pass_gate.py",
                    "argv": [sys.executable, "-c", "import json; print(json.dumps({'status':'PASS'}))"],
                    "json_stdout": True,
                    "remediation": "pass remediation",
                },
                {
                    "name": "fail_gate.py",
                    "argv": [sys.executable, "-c", "import json, sys; print(json.dumps({'status':'FAIL'})); sys.exit(1)"],
                    "json_stdout": True,
                    "remediation": "fail remediation",
                },
                {
                    "name": "not_run.py",
                    "argv": [sys.executable, "-c", "print('should not run')"],
                    "json_stdout": False,
                    "remediation": "not run",
                },
            ]
        )

        report = task_gate.evaluate(self.task_dir, strict=True, report_dir=self.report_dir, skip_harbor=True)

        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["stopped_on"], "fail_gate.py")
        self.assertEqual(len(report["results"]), 2)
        for result in report["results"]:
            self.assertTrue(Path(result["stdout_path"]).exists())
            self.assertTrue(Path(result["stderr_path"]).exists())
        self.assertIn("check-task.sh remains the canonical preflight", report["check_task_canonical_note"])

    def test_collapse_warn_is_warn_not_fail(self) -> None:
        self._set_specs(
            [
                {
                    "name": "collapse_check.py",
                    "argv": [sys.executable, "-c", "import json, sys; print(json.dumps({'fails':0,'warns':1})); sys.exit(2)"],
                    "json_stdout": True,
                    "remediation": "collapse remediation",
                }
            ]
        )

        report = task_gate.evaluate(self.task_dir, strict=True, report_dir=self.report_dir, skip_harbor=False)

        self.assertEqual(report["status"], "WARN")
        self.assertEqual(report["results"][0]["status"], "WARN")


if __name__ == "__main__":
    unittest.main()
