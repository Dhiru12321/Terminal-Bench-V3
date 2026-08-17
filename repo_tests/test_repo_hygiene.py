from __future__ import annotations

import os
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

OPERATIONAL_PYTHON_SCRIPTS = {
    "actionability_check.py",
    "agent_brief.py",
    "analyze_trials.py",
    "approve_task.py",
    "category_coverage.py",
    "collapse_check.py",
    "failure_meta_review.py",
    "first_look_packet.py",
    "gate_extras.py",
    "harbor_gate.py",
    "instruction_audit.py",
    "lint_spec.py",
    "log_failure.py",
    "metrics_collector.py",
    "no_hidden_contracts.py",
    "obfuscation_lint.py",
    "package_task.py",
    "quality_check_adjudicate.py",
    "reference_task_check.py",
    "run_static_checks.py",
    "spec_satisfiability.py",
    "step2b_ready.py",
    "task_gate.py",
    "task_integrity.py",
    "task_runtime_deps.py",
    "tb3_doctor.py",
    "validate_loop.py",
    "validate_submission_zip.py",
    "validation_log.py",
    "verifier_health.py",
    "waiver_lint.py",
}


class RepoHygieneTest(unittest.TestCase):
    def test_no_root_python_tools_remain(self) -> None:
        root_py = sorted(path.name for path in REPO_ROOT.glob("*.py"))
        self.assertEqual(root_py, [])

    def test_generated_root_clutter_is_absent(self) -> None:
        forbidden = [
            REPO_ROOT / "__pycache__",
            REPO_ROOT / "scripts" / "__pycache__",
            REPO_ROOT / "collapsechurn.md",
            REPO_ROOT / "jobs",
            REPO_ROOT / "revise task",
        ]
        existing = [path.relative_to(REPO_ROOT).as_posix() for path in forbidden if path.exists()]
        self.assertEqual(existing, [])
        local_archives = sorted(path.name for path in REPO_ROOT.glob("terminal-bench-3*.zip"))
        self.assertEqual(local_archives, [])

    def test_no_transcript_markdown_artifacts(self) -> None:
        root_transcripts = [
            "hardening.md",
            "promotion.md",
            "agentconv.md",
            "review.md",
            "review and validation.md",
            "Continuation.md",
            "validation and creation.md",
        ]
        root_transcripts.extend(path.name for path in REPO_ROOT.glob("1st_task*.md"))
        existing_root = sorted(name for name in root_transcripts if (REPO_ROOT / name).exists())
        self.assertEqual(existing_root, [])
        scripts_markdown = sorted(path.name for path in (REPO_ROOT / "scripts").glob("*.md"))
        self.assertEqual(scripts_markdown, [])

    def test_operational_python_scripts_live_under_scripts(self) -> None:
        missing = sorted(
            name for name in OPERATIONAL_PYTHON_SCRIPTS if not (REPO_ROOT / "scripts" / name).is_file()
        )
        self.assertEqual(missing, [])

    def test_shell_entrypoints_are_executable(self) -> None:
        for rel in ("scripts/check-task.sh", "scripts/smoke_task.sh"):
            path = REPO_ROOT / rel
            self.assertTrue(path.is_file(), f"{rel} is missing")
            self.assertTrue(os.access(path, os.X_OK), f"{rel} must be executable")

    def test_audition_gate_artifacts_are_removed(self) -> None:
        removed_paths = [
            REPO_ROOT / "docs" / ("MODEL" + "_AUDITION.md"),
            REPO_ROOT / "scripts" / ("model" + "_audition_report.py"),
            REPO_ROOT / "repo_tests" / ("test_model" + "_audition_report.py"),
        ]
        existing = [path.relative_to(REPO_ROOT).as_posix() for path in removed_paths if path.exists()]
        self.assertEqual(existing, [])

        forbidden_terms = [
            "model" + " audition",
            "model" + "-audition",
            "model" + "_audition",
            "MODEL" + "_AUDITION",
            "target" + "-model " + "audition",
            "--" + "model" + "-audition-report",
            "scripts/" + "model" + "_audition_report.py",
            "docs/" + "MODEL" + "_AUDITION.md",
        ]
        checked_files = [
            REPO_ROOT / "AGENTS.md",
            REPO_ROOT / "commands.md",
            REPO_ROOT / "workflow-prompts.md",
            REPO_ROOT / ".cursor" / "rules" / "review-and-submit.mdc",
            REPO_ROOT / ".cursor" / "rules" / "00-authoring-critical.mdc",
            REPO_ROOT / "docs" / "HARD_BUT_FAIR_AUTHORING.md",
            REPO_ROOT / "docs" / "ARCHITECTURE.md",
            REPO_ROOT / "docs" / "WAIVERS.md",
            REPO_ROOT / "docs" / "reference_tasks" / "README.md",
            REPO_ROOT / "docs" / "reference_tasks" / "reference_task_template.md",
            REPO_ROOT / "scripts" / "approve_task.py",
            REPO_ROOT / "scripts" / "reference_task_check.py",
            REPO_ROOT / "scripts" / "waiver_lint.py",
            REPO_ROOT / "failures" / "catalog.schema.json",
            REPO_ROOT / "docs" / "FAILURE_CATALOG.md",
        ]
        offenders: list[str] = []
        for path in checked_files:
            text = path.read_text(encoding="utf-8")
            for term in forbidden_terms:
                if term in text:
                    offenders.append(f"{path.relative_to(REPO_ROOT)} contains {term}")
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
