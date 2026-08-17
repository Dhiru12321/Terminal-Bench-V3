from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from scripts import tb3_doctor


REPO_ROOT = Path(__file__).resolve().parents[1]


class Tb3DoctorTest(unittest.TestCase):
    def test_missing_repo_root_is_a_blocker(self) -> None:
        tmpdir = Path(tempfile.mkdtemp(prefix="tb3-doctor-test-"))
        self.addCleanup(shutil.rmtree, tmpdir, ignore_errors=True)

        report = tb3_doctor.evaluate(tmpdir)

        self.assertEqual(report["status"], "FAIL")
        root_check = next(check for check in report["checks"] if check["id"] == "repo_root")
        self.assertEqual(root_check["status"], "FAIL")

    def test_current_repo_reports_structured_checks(self) -> None:
        report = tb3_doctor.evaluate(REPO_ROOT)

        self.assertIn(report["status"], {"PASS", "WARN"})
        ids = {check["id"] for check in report["checks"]}
        self.assertIn("python3", ids)
        self.assertIn("core_scripts", ids)
        self.assertIn("pycache_prefix_recommendation", ids)


if __name__ == "__main__":
    unittest.main()
