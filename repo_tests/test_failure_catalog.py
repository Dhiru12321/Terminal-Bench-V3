from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LOG_SCRIPT = REPO_ROOT / "scripts" / "log_failure.py"
META_SCRIPT = REPO_ROOT / "scripts" / "failure_meta_review.py"


def valid_record(
    *,
    task_id: str = "queue-replay-drift",
    stage: str = "collapse_check",
    primary: str = "too_leaky",
    response: str = "redesigned",
    check: str = "collapse_check",
    profile: str = "concurrency_ordering",
) -> dict[str, object]:
    return {
        "task_id": task_id,
        "source": {
            "real_bug": True,
            "category": "system-administration",
            "category_profile": profile,
        },
        "failure_stage": stage,
        "primary_failure": primary,
        "checks_involved": [check],
        "author_response": response,
        "would_have_caught": ["spec_satisfiability"],
        "rule_change_proposed": "tighten the upstream satisfiability gate",
        "rule_change_validated_on_historical_failures": False,
        "notes": "Concrete postmortem text.",
    }


class FailureCatalogTests(unittest.TestCase):
    def run_log(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(LOG_SCRIPT), *args],
            cwd=REPO_ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def run_meta(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(META_SCRIPT), *args],
            cwd=REPO_ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def test_log_failure_creates_valid_record_from_cli_args(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            failures_dir = Path(tmp) / "failures"
            result = self.run_log(
                "--task-id",
                "queue-replay-drift",
                "--real-bug",
                "--category",
                "system-administration",
                "--category-profile",
                "concurrency_ordering",
                "--failure-stage",
                "collapse_check",
                "--primary-failure",
                "too_leaky",
                "--check",
                "collapse_check",
                "--author-response",
                "redesigned",
                "--would-have-caught",
                "spec_satisfiability",
                "--rule-change-proposed",
                "tighten the upstream satisfiability gate",
                "--notes",
                "Concrete postmortem text.",
                "--failures-dir",
                str(failures_dir),
                "--json",
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "PASS")
            record_path = Path(payload["path"])
            self.assertTrue(record_path.exists())
            record = json.loads(record_path.read_text(encoding="utf-8"))

        self.assertEqual(record["task_id"], "queue-replay-drift")
        self.assertEqual(record["primary_failure"], "too_leaky")

    def test_template_writes_valid_starter_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "template.json"
            result = self.run_log("--template", "--out", str(out_path), "--json")
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            payload = json.loads(result.stdout)
            self.assertTrue(payload["template"])
            self.assertTrue(out_path.exists())
            template = json.loads(out_path.read_text(encoding="utf-8"))

        self.assertEqual(template["failure_stage"], "collapse_check")

    def test_from_json_invalid_schema_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            record = valid_record()
            record["failure_stage"] = "not_a_stage"
            path.write_text(json.dumps(record), encoding="utf-8")
            result = self.run_log("--from-json", str(path), "--json")

        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "FAIL")
        self.assertTrue(
            any("$.failure_stage" in finding["location"] for finding in payload["findings"]),
            payload["findings"],
        )

    def test_meta_review_counts_and_repeated_patterns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            failures_dir = Path(tmp) / "failures"
            failures_dir.mkdir()
            records = [
                valid_record(task_id="one", response="waiver_requested"),
                valid_record(task_id="two", response="redesigned"),
                valid_record(
                    task_id="three",
                    stage="no_hidden_contracts",
                    primary="hidden_contract",
                    response="abandoned",
                    check="no_hidden_contracts",
                    profile="file_format_serialization",
                ),
            ]
            for index, record in enumerate(records):
                (failures_dir / f"record-{index}.json").write_text(
                    json.dumps(record),
                    encoding="utf-8",
                )

            result = self.run_meta("--failures-dir", str(failures_dir), "--json")

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "PASS")
        self.assertEqual(payload["counts"]["failure_stage"]["collapse_check"], 2)
        self.assertEqual(payload["counts"]["author_response"]["waiver_requested"], 1)
        self.assertEqual(payload["waiver_pressure"]["count"], 1)
        self.assertTrue(
            any(
                item["kind"] == "stage_primary"
                and item["key"] == "collapse_check:too_leaky"
                and item["count"] == 2
                for item in payload["repeated_patterns"]
            ),
            payload["repeated_patterns"],
        )

    def test_meta_review_fails_invalid_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            failures_dir = Path(tmp) / "failures"
            failures_dir.mkdir()
            (failures_dir / "bad.json").write_text(
                json.dumps({"task_id": "missing-fields"}),
                encoding="utf-8",
            )

            result = self.run_meta("--failures-dir", str(failures_dir), "--json")

        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "FAIL")
        self.assertEqual(payload["summary"]["invalid_records"], 1)


if __name__ == "__main__":
    unittest.main()
