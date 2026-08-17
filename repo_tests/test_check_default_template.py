from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts import check_default_template


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE_DIR = REPO_ROOT / "default-template"


def _copy_template_without_comments(tmpdir: str) -> Path:
    task_dir = Path(tmpdir) / "template-task"
    shutil.copytree(DEFAULT_TEMPLATE_DIR, task_dir)
    test_sh = task_dir / "tests" / "test.sh"
    kept_lines = [
        line
        for line in test_sh.read_text(encoding="utf-8").splitlines()
        if not (line.strip().startswith("#") and not line.strip().startswith("#!"))
    ]
    test_sh.write_text("\n".join(kept_lines) + "\n", encoding="utf-8")
    return task_dir


class CheckDefaultTemplateTest(unittest.TestCase):
    def test_default_template_test_sh_passes_semantics(self) -> None:
        test_sh = (REPO_ROOT / "default-template" / "tests" / "test.sh").read_text(encoding="utf-8")
        substantive_lines = check_default_template.run_static_checks.substantive_shell_lines(test_sh)
        mismatches = check_default_template.run_static_checks.test_sh_prefix_mismatches(
            substantive_lines
        )
        self.assertEqual(mismatches, [])

    def test_template_without_comments_warns(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            task_dir = _copy_template_without_comments(tmpdir)
            report = check_default_template.evaluate(task_dir, strict=False)
        self.assertEqual(report.failures, [])
        self.assertTrue(any("missing default-template comment markers" in item for item in report.warnings))

    def test_template_without_comments_fails_in_strict_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            task_dir = _copy_template_without_comments(tmpdir)
            report = check_default_template.evaluate(task_dir, strict=True)
        self.assertTrue(any("missing default-template comment markers" in item for item in report.failures))

    def test_default_template_passes_strict(self) -> None:
        report = check_default_template.evaluate(DEFAULT_TEMPLATE_DIR, strict=True)
        self.assertEqual(report.failures, [], report.failures)

    def test_cli_json_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            task_dir = Path(tmpdir) / "template-task"
            shutil.copytree(DEFAULT_TEMPLATE_DIR, task_dir)
            exit_code = check_default_template.main([str(task_dir), "--json"])
        self.assertEqual(exit_code, 0)

    def test_missing_reward_section_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            task_dir = Path(tmpdir) / "template-task"
            shutil.copytree(DEFAULT_TEMPLATE_DIR, task_dir)
            test_sh = task_dir / "tests" / "test.sh"
            lines = test_sh.read_text(encoding="utf-8").splitlines()
            test_sh.write_text("\n".join(lines[:-5]) + "\n", encoding="utf-8")
            report = check_default_template.evaluate(task_dir, strict=False)
        self.assertTrue(
            any("Must end with the platform reward section" in item for item in report.failures)
        )

    def test_missing_template_apt_block_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            task_dir = Path(tmpdir) / "template-task"
            shutil.copytree(DEFAULT_TEMPLATE_DIR, task_dir)
            dockerfile = task_dir / "environment" / "Dockerfile"
            content = dockerfile.read_text(encoding="utf-8")
            content = content.replace("        tmux \\\n", "").replace("        asciinema \\\n", "")
            dockerfile.write_text(content, encoding="utf-8")
            report = check_default_template.evaluate(task_dir, strict=False)
        self.assertTrue(
            any("default-template apt block" in item for item in report.failures)
        )

    def test_template_apt_block_allows_extra_packages(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            task_dir = Path(tmpdir) / "template-task"
            shutil.copytree(DEFAULT_TEMPLATE_DIR, task_dir)
            dockerfile = task_dir / "environment" / "Dockerfile"
            content = dockerfile.read_text(encoding="utf-8")
            content = content.replace(
                "        asciinema \\\n",
                "        asciinema \\\n        curl \\\n",
            )
            dockerfile.write_text(content, encoding="utf-8")
            report = check_default_template.evaluate(task_dir, strict=False)
        apt_failures = [
            item for item in report.failures if "default-template apt block" in item
        ]
        self.assertEqual(apt_failures, [])

    def test_comment_between_rc_and_if_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            task_dir = Path(tmpdir) / "template-task"
            shutil.copytree(DEFAULT_TEMPLATE_DIR, task_dir)
            test_sh = task_dir / "tests" / "test.sh"
            content = test_sh.read_text(encoding="utf-8")
            content = content.replace(
                "rc=$?\n" 'if [ "$rc" -eq 0 ]; then',
                "rc=$?\n\n# Grade the run.\n" 'if [ "$rc" -eq 0 ]; then',
            )
            test_sh.write_text(content, encoding="utf-8")
            report = check_default_template.evaluate(task_dir, strict=False)
        self.assertTrue(
            any("Must end with the platform reward section" in item for item in report.failures),
            report.failures,
        )

    def test_legacy_rc_reward_tail_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            task_dir = Path(tmpdir) / "template-task"
            shutil.copytree(DEFAULT_TEMPLATE_DIR, task_dir)
            test_sh = task_dir / "tests" / "test.sh"
            content = test_sh.read_text(encoding="utf-8")
            content = content.replace(
                "rc=$?\n"
                'if [ "$rc" -eq 0 ]; then\n'
                "    echo 1 > /logs/verifier/reward.txt\n"
                "else\n"
                "    echo 0 > /logs/verifier/reward.txt\n"
                "fi",
                "RC=$?\n\n"
                'if [ "$RC" -eq 0 ]; then\n'
                "  echo 1 > /logs/verifier/reward.txt\n"
                "else\n"
                "  echo 0 > /logs/verifier/reward.txt\n"
                "fi\n\n"
                'exit "$RC"',
            )
            test_sh.write_text(content, encoding="utf-8")
            report = check_default_template.evaluate(task_dir, strict=False)
        self.assertTrue(
            any("Must end with the platform reward section" in item for item in report.failures),
            report.failures,
        )
