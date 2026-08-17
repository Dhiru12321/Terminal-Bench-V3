#!/usr/bin/env python3
"""Check that a task follows the repo default-template layout and verifier template.

Source of truth: ``default-template/`` at the repository root. This checker validates
the standard task skeleton (files, task.toml sections, Dockerfile WORKDIR, the
template apt block (tmux + asciinema), and ``tests/test.sh`` semantics/comments)
without requiring task-specific content to match the placeholder hello-world files.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import run_static_checks
DEFAULT_TEMPLATE_DIR = REPO_ROOT / "default-template"

STANDARD_TEMPLATE_PATHS = (
    "instruction.md",
    "task.toml",
    "environment/Dockerfile",
    "solution/solve.sh",
    "tests/Dockerfile",
    "tests/test.sh",
    "tests/test_outputs.py",
)

TEMPLATE_METADATA_KEYS = run_static_checks.REQUIRED_METADATA_KEYS
TEMPLATE_TOP_LEVEL_SECTIONS = ("metadata", "verifier", "agent", "environment")
REQUIRED_ENVIRONMENT_KEYS = ("network_mode", "build_timeout_sec", "cpus", "memory_mb", "storage_mb")

TEST_SH_COMMENT_MARKERS = (
    "# Check if we're in a valid working directory",
    "# Produce reward file (REQUIRED)",
)

WORKDIR_IN_DOCKERFILE_PATTERN = re.compile(r"^\s*WORKDIR\s+", re.IGNORECASE | re.MULTILINE)
TEMPLATE_DOCKERFILE_PATH = DEFAULT_TEMPLATE_DIR / "environment" / "Dockerfile"
# default-template/environment/Dockerfile apt block for tmux + asciinema.
TEMPLATE_DOCKERFILE_APT_BLOCK_LINE_START = 6
TEMPLATE_DOCKERFILE_APT_BLOCK_LINE_END = 10
# Semantic markers from that block.
TEMPLATE_APT_BLOCK_MARKERS = (
    "apt-get update",
    "apt-get install",
    "--no-install-recommends",
    "tmux",
    "asciinema",
    "rm -rf /var/lib/apt/lists/*",
)
FORBIDDEN_TEST_SH_PATTERNS = (
    (re.compile(r"^set\s+-euo?\s+pipefail\b", re.MULTILINE), "set -euo pipefail"),
    (re.compile(r"^set\s+-e\b", re.MULTILINE), "set -e"),
    (re.compile(r"^set\s+\+e\b", re.MULTILINE), "set +e"),
    (re.compile(r"/opt/verifier/", re.MULTILINE), "/opt/verifier/"),
    (re.compile(r"^apt-get\s+update\b", re.MULTILINE), "apt-get in test.sh"),
    (re.compile(r"^curl\b.*astral\.sh/uv/", re.MULTILINE), "uv installer in test.sh"),
    (re.compile(r"^uvx\b", re.MULTILINE), "uvx"),
)

# Must match default-template/tests/test.sh exactly (see run_static_checks.STANDARD_REWARD_TAIL).
REQUIRED_REWARD_SECTION_LINES = run_static_checks.STANDARD_REWARD_TAIL
REQUIRED_REWARD_SECTION_TEXT = "\n".join(REQUIRED_REWARD_SECTION_LINES)


@dataclass
class TemplateReport:
    passes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)

    @property
    def status(self) -> str:
        if self.failures:
            return "FAIL"
        if self.warnings:
            return "WARN"
        return "PASS"

    def ok(self, message: str) -> None:
        self.passes.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    def fail(self, message: str) -> None:
        self.failures.append(message)


def resolve_task_dir(task_dir: Path) -> Path:
    path = task_dir.expanduser()
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path.resolve()


def collect_test_sh_paths(task_dir: Path) -> list[Path]:
    candidate = task_dir / "tests/test.sh"
    return [candidate] if candidate.is_file() else []


def check_template_files(task_dir: Path, report: TemplateReport) -> None:
    if not DEFAULT_TEMPLATE_DIR.is_dir():
        report.fail(f"default-template directory is missing at {DEFAULT_TEMPLATE_DIR}")
        return

    missing = [
        relative
        for relative in STANDARD_TEMPLATE_PATHS
        if not (task_dir / relative).is_file()
    ]
    if missing:
        report.fail(
            "task is missing default-template files: " + ", ".join(missing)
        )
    else:
        report.ok("standard default-template file layout is present")


def check_task_toml(task_dir: Path, report: TemplateReport) -> dict | None:
    task_toml = task_dir / "task.toml"
    if not task_toml.is_file():
        report.fail("task.toml is missing")
        return None

    try:
        task_data = run_static_checks.load_toml_file(task_toml)
    except Exception as exc:  # pragma: no cover - malformed TOML
        report.fail(f"task.toml could not be parsed: {exc}")
        return None

    if not isinstance(task_data.get("artifacts"), list) or not task_data["artifacts"]:
        report.fail(
            "task.toml must declare a non-empty top-level `artifacts` array "
            "(see default-template/task.toml)"
        )
    else:
        report.ok("task.toml declares top-level artifacts")

    missing_sections = [name for name in TEMPLATE_TOP_LEVEL_SECTIONS if name not in task_data]
    if missing_sections:
        report.fail(
            "task.toml is missing default-template sections: " + ", ".join(missing_sections)
        )
    else:
        report.ok("task.toml contains default-template top-level sections")

    metadata = task_data.get("metadata")
    if not isinstance(metadata, dict):
        report.fail("task.toml [metadata] section is missing or not a table")
    else:
        missing_keys = [key for key in TEMPLATE_METADATA_KEYS if key not in metadata]
        if missing_keys:
            report.fail(
                "task.toml [metadata] is missing default-template keys: "
                + ", ".join(missing_keys)
            )
        else:
            report.ok("task.toml [metadata] contains default-template keys")

    verifier = task_data.get("verifier")
    if isinstance(verifier, dict):
        mode = verifier.get("environment_mode")
        if mode != run_static_checks.REQUIRED_VERIFIER_ENVIRONMENT_MODE:
            report.fail(
                "task.toml [verifier].environment_mode must be "
                f'"{run_static_checks.REQUIRED_VERIFIER_ENVIRONMENT_MODE}"; got {mode!r}'
            )
        else:
            report.ok("task.toml [verifier] runs in a separate container")

    environment = task_data.get("environment")
    if not isinstance(environment, dict):
        report.fail("task.toml [environment] section is missing or not a table")
    else:
        missing_env = [key for key in REQUIRED_ENVIRONMENT_KEYS if key not in environment]
        if missing_env:
            report.fail(
                "task.toml [environment] is missing default-template keys: "
                + ", ".join(missing_env)
            )
        else:
            report.ok("task.toml [environment] contains default-template keys")

    return task_data


def trim_trailing_blank_lines(lines: list[str]) -> list[str]:
    trimmed = list(lines)
    while trimmed and not trimmed[-1].strip():
        trimmed.pop()
    return trimmed


def default_template_reward_tail_matches(trimmed_lines: list[str]) -> bool:
    """True when the reward footer matches the platform template shape and adjacency rules."""
    return run_static_checks.standard_reward_tail_matches(trimmed_lines)


def load_template_dockerfile_apt_block() -> str:
    if not TEMPLATE_DOCKERFILE_PATH.is_file():
        return ""
    lines = TEMPLATE_DOCKERFILE_PATH.read_text(encoding="utf-8").splitlines()
    start = TEMPLATE_DOCKERFILE_APT_BLOCK_LINE_START - 1
    end = TEMPLATE_DOCKERFILE_APT_BLOCK_LINE_END
    return "\n".join(lines[start:end])


def normalize_dockerfile_text(content: str) -> str:
    without_comments: list[str] = []
    for raw_line in content.splitlines():
        without_comments.append(raw_line.split("#", 1)[0])
    joined = " ".join(without_comments)
    joined = joined.replace("\\\n", " ")
    joined = re.sub(r"\s+", " ", joined)
    return joined.strip().lower()


def dockerfile_has_template_apt_block(content: str) -> bool:
    normalized = normalize_dockerfile_text(content)
    return all(marker in normalized for marker in TEMPLATE_APT_BLOCK_MARKERS)


def check_dockerfile_workdir(task_dir: Path, report: TemplateReport) -> None:
    dockerfile = task_dir / "environment" / "Dockerfile"
    if not dockerfile.is_file():
        return
    content = dockerfile.read_text(encoding="utf-8")
    if WORKDIR_IN_DOCKERFILE_PATTERN.search(content):
        report.ok("environment/Dockerfile sets WORKDIR (default-template requirement)")
    else:
        report.fail(
            "environment/Dockerfile must set WORKDIR (see default-template/environment/Dockerfile)"
        )


def check_dockerfile_template_apt_block(task_dir: Path, report: TemplateReport) -> None:
    dockerfile = task_dir / "environment" / "Dockerfile"
    if not dockerfile.is_file():
        return
    if not TEMPLATE_DOCKERFILE_PATH.is_file():
        report.fail(f"default-template Dockerfile is missing at {TEMPLATE_DOCKERFILE_PATH}")
        return

    content = dockerfile.read_text(encoding="utf-8")
    if dockerfile_has_template_apt_block(content):
        report.ok(
            "environment/Dockerfile includes default-template apt block (tmux, asciinema)"
        )
        return

    reference = load_template_dockerfile_apt_block()
    report.fail(
        "environment/Dockerfile must include the default-template apt block "
        f"(lines {TEMPLATE_DOCKERFILE_APT_BLOCK_LINE_START}-"
        f"{TEMPLATE_DOCKERFILE_APT_BLOCK_LINE_END} of "
        "default-template/environment/Dockerfile):\n"
        f"{reference}"
    )


def check_test_sh_file(task_dir: Path, test_sh: Path, report: TemplateReport, *, strict: bool) -> None:
    label = test_sh.relative_to(task_dir).as_posix()
    content = test_sh.read_text(encoding="utf-8")
    lines = content.splitlines()

    for pattern, description in FORBIDDEN_TEST_SH_PATTERNS:
        if pattern.search(content):
            report.fail(f"{label}: must not use {description} (not in default-template/tests/test.sh)")

    if run_static_checks.FORBIDDEN_ERREXIT_PATTERN.search(content):
        report.fail(
            f"{label}: must not enable errexit (default-template/tests/test.sh uses set -uo pipefail without -e)"
        )

    if not run_static_checks.REQUIRED_SET_FLAGS_PATTERN.search(content):
        report.fail(f"{label}: must start with set -uo pipefail (see default-template/tests/test.sh)")

    if run_static_checks.LEGACY_UVX_PYTEST_PATTERN.search(content):
        report.fail(
            f"{label}: must invoke pytest with python -m pytest (install verifier deps in environment/Dockerfile)"
        )

    if not run_static_checks.PYTHON_PYTEST_MODULE_PATTERN.search(content):
        report.fail(f"{label}: must invoke pytest with python -m pytest")

    if not run_static_checks.CTRF_PATTERN.search(content):
        report.fail(f"{label}: must run pytest with --ctrf /logs/verifier/ctrf.json")

    if "/logs/verifier/reward.json" in content:
        report.fail(f"{label}: must write reward.txt, not reward.json")

    if not run_static_checks.WORKDIR_GUARD_PATTERN.search(content):
        report.fail(f'{label}: must guard against "$PWD" = "/"')

    substantive_lines = run_static_checks.substantive_shell_lines(content)
    prefix_mismatches = run_static_checks.test_sh_prefix_mismatches(substantive_lines)
    if prefix_mismatches:
        report.fail(
            f"{label}: pre-pytest block does not match default-template/tests/test.sh semantics:\n"
            + "\n".join(prefix_mismatches)
        )
    else:
        report.ok(f"{label}: pre-pytest block matches default-template semantics")

    trimmed_lines = trim_trailing_blank_lines(lines)
    if not default_template_reward_tail_matches(trimmed_lines):
        report.fail(
            f"{label}: Must end with the platform reward section ({run_static_checks.PLATFORM_REWARD_TAIL_HELP}):\n"
            f"{REQUIRED_REWARD_SECTION_TEXT}"
        )
    else:
        report.ok(f"{label}: ends with default-template reward section")

    missing_markers = [marker for marker in TEST_SH_COMMENT_MARKERS if marker not in content]
    if missing_markers:
        message = (
            f"{label}: missing default-template comment markers: " + "; ".join(missing_markers)
        )
        if strict:
            report.fail(message)
        else:
            report.warn(message)
    else:
        report.ok(f"{label}: includes default-template section comments")

    if "before running this script." not in content:
        message = (
            f"{label}: WORKDIR guard should use the default-template message "
            '(...Dockerfile before running this script.")'
        )
        if strict:
            report.fail(message)
        else:
            report.warn(message)


def evaluate(task_dir: Path, *, strict: bool) -> TemplateReport:
    report = TemplateReport()
    check_template_files(task_dir, report)
    task_data = check_task_toml(task_dir, report)
    check_dockerfile_workdir(task_dir, report)
    check_dockerfile_template_apt_block(task_dir, report)

    if task_data is None:
        return report

    test_sh_paths = collect_test_sh_paths(task_dir)
    if not test_sh_paths:
        report.fail("tests/test.sh is missing")
        return report

    for test_sh in test_sh_paths:
        check_test_sh_file(task_dir, test_sh, report, strict=strict)

    return report


def render_human(report: TemplateReport, task_dir: Path) -> str:
    lines = [f"default-template check: {task_dir}"]
    for message in report.passes:
        lines.append(f"PASS  - {message}")
    for message in report.warnings:
        lines.append(f"WARN  - {message}")
    for message in report.failures:
        lines.append(f"FAIL  - {message}")
    lines.append(f"RESULT: {report.status}")
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check that a task follows default-template/ layout and tests/test.sh conventions."
    )
    parser.add_argument(
        "task_dir",
        type=Path,
        help="Path to tasks/<task-name> (or a path containing tests/test.sh)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat missing default-template comment markers and WORKDIR wording as failures",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON only")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    task_dir = resolve_task_dir(args.task_dir)
    if not task_dir.is_dir():
        print(f"check_default_template.py: task dir not found: {task_dir}", file=sys.stderr)
        return 2

    report = evaluate(task_dir, strict=args.strict)
    payload = {
        "status": report.status,
        "task_dir": str(task_dir),
        "template_dir": str(DEFAULT_TEMPLATE_DIR),
        "passes": report.passes,
        "warnings": report.warnings,
        "failures": report.failures,
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(render_human(report, task_dir))
    return 1 if report.failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
