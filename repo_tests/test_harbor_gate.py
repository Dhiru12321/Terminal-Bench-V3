from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts import harbor_gate


class HarborGateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="harbor-gate-test-"))
        self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)
        self.task_dir = self.tmpdir / "tasks" / "fixture"
        self.task_dir.mkdir(parents=True)
        self.old_path = os.environ.get("PATH", "")
        self.addCleanup(self._restore_path)

    def _restore_path(self) -> None:
        os.environ["PATH"] = self.old_path
        os.environ.pop("HARBOR_FAKE_DIR", None)

    def _write_result(self, path: Path, mean: float, trials: int = 1, errors: int = 0) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "n_total_trials": trials,
                    "stats": {
                        "n_trials": trials,
                        "n_errors": errors,
                        "evals": {
                            "oracle__adhoc": {
                                "n_trials": trials,
                                "n_errors": errors,
                                "metrics": [{"mean": mean}],
                                "reward_stats": {"reward": {str(mean): ["trial"] * trials}},
                            }
                        },
                    },
                }
            )
        )

    def test_parse_fixture_result_json(self) -> None:
        result_path = self.tmpdir / "jobs" / "run" / "result.json"
        self._write_result(result_path, 1.0, trials=3)

        parsed = harbor_gate.parse_result_file(result_path)

        self.assertEqual(parsed["mean"], 1.0)
        self.assertEqual(parsed["trials"], 3)
        self.assertEqual(parsed["errors"], 0)
        self.assertEqual(parsed["reward_distribution"], {"1.0": 3})

    def test_fake_harbor_oracle_nop_and_repeat_pass(self) -> None:
        bin_dir = self.tmpdir / "bin"
        bin_dir.mkdir()
        fake_dir = self.tmpdir / "fake-jobs"
        harbor = bin_dir / "harbor"
        harbor.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "action=oracle\n"
            "trials=1\n"
            "prev=\n"
            "for arg in \"$@\"; do\n"
            "  if [[ \"$prev\" == \"-a\" ]]; then action=\"$arg\"; fi\n"
            "  if [[ \"$prev\" == \"-k\" ]]; then trials=\"$arg\"; fi\n"
            "  prev=\"$arg\"\n"
            "done\n"
            "mean=1.0\n"
            "if [[ \"$action\" == \"nop\" ]]; then mean=0.0; fi\n"
            "job=\"$HARBOR_FAKE_DIR/${action}-${trials}\"\n"
            "mkdir -p \"$job\"\n"
            "python3 - \"$job/result.json\" \"$mean\" \"$trials\" <<'PY'\n"
            "import json, sys\n"
            "path, mean, trials = sys.argv[1], float(sys.argv[2]), int(sys.argv[3])\n"
            "payload = {'n_total_trials': trials, 'stats': {'n_trials': trials, 'n_errors': 0, 'evals': {'fake': {'n_trials': trials, 'n_errors': 0, 'metrics': [{'mean': mean}], 'reward_stats': {'reward': {str(mean): [str(i) for i in range(trials)]}}}}}}\n"
            "open(path, 'w', encoding='utf-8').write(json.dumps(payload))\n"
            "PY\n"
            "echo \"Results written to $job/result.json\"\n"
        )
        harbor.chmod(0o755)
        os.environ["PATH"] = f"{bin_dir}:{self.old_path}"
        os.environ["HARBOR_FAKE_DIR"] = str(fake_dir)

        report = harbor_gate.evaluate(self.task_dir, oracle=True, nop=True, oracle_repeat=3)

        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["summary"], {"fail": 0, "pass": 3})
        means = {run["name"]: run["mean"] for run in report["runs"]}
        self.assertEqual(means["oracle"], 1.0)
        self.assertEqual(means["nop"], 0.0)
        self.assertEqual(means["oracle_repeat_3"], 1.0)


if __name__ == "__main__":
    unittest.main()
