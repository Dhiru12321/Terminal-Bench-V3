#!/usr/bin/env python3
"""Verify the task final runtime Docker base image is canonical or justified.

Exit codes:
  0 = PASS (canonical final runtime image, or non-canonical with credible justification)
  1 = FAIL (non-canonical final runtime image without credible justification)
  2 = WARN (non-canonical with local justification — surfaced for reviewers)
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import canonical_base_images, run_static_checks


@dataclass
class CheckReport:
    status: str
    final_runtime_image: str | None = None
    canonical: bool = False
    justification: str | None = None
    messages: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "final_runtime_image": self.final_runtime_image,
            "canonical": self.canonical,
            "justification": self.justification,
            "messages": self.messages,
        }


def check_task(task_dir: Path) -> CheckReport:
    dockerfile = task_dir / "environment" / "Dockerfile"
    if not dockerfile.is_file():
        return CheckReport(
            status="PASS",
            messages=["environment/Dockerfile missing; canonical base image check skipped"],
        )

    content = dockerfile.read_text(encoding="utf-8")
    from_images = run_static_checks.parse_docker_from_images(content)
    if not from_images:
        return CheckReport(
            status="FAIL",
            messages=["environment/Dockerfile has no FROM instructions"],
        )

    final_runtime_image = from_images[-1]
    if canonical_base_images.docker_image_is_scratch(final_runtime_image):
        return CheckReport(
            status="PASS",
            final_runtime_image=final_runtime_image,
            messages=["Final runtime image is scratch; canonical base image check skipped"],
        )

    if canonical_base_images.docker_image_is_canonical_base(final_runtime_image):
        digest = canonical_base_images.extract_image_digest(final_runtime_image)
        entry = (
            canonical_base_images.canonical_base_image_for_digest(digest)
            if digest
            else None
        )
        family = entry.family if entry else "canonical"
        return CheckReport(
            status="PASS",
            final_runtime_image=final_runtime_image,
            canonical=True,
            messages=[f"Final runtime image matches canonical {family} base image digest"],
        )

    justification = canonical_base_images.find_non_canonical_justification(task_dir, content)
    if justification:
        return CheckReport(
            status="WARN",
            final_runtime_image=final_runtime_image,
            canonical=False,
            justification=justification,
            messages=[
                "Final runtime image is non-canonical but has a credible local justification. "
                "Surface to reviewers; at submission select **No** on the canonical-base-image "
                "field and include the same rationale.",
                f"Justification: {justification}",
            ],
        )

    return CheckReport(
        status="FAIL",
        final_runtime_image=final_runtime_image,
        canonical=False,
        messages=[
            "Final runtime FROM is not a canonical Terminal-Bench base image "
            f"({final_runtime_image}). Use an exact digest from "
            "docs/DOCKERFILE_AND_IMAGE_BEST_PRACTICES.md / scripts/canonical_base_images.py, "
            "or add a credible non-canonical justification in a Dockerfile comment "
            "(# Non-canonical base image: …). Terminus 3 generates README.md during "
            "packaging, so a README section never reaches CI.",
        ],
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check that the task final runtime Docker image is canonical or justified."
    )
    parser.add_argument("task_dir", type=Path, help="Path to the task directory")
    parser.add_argument("--json", action="store_true", help="Emit JSON report on stdout")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat WARN (non-canonical with justification) as exit 0; FAIL still exits 1",
    )
    args = parser.parse_args(argv)

    task_dir = args.task_dir.resolve()
    if not task_dir.is_dir():
        print(f"ERROR: task directory not found: {task_dir}", file=sys.stderr)
        return 1

    report = check_task(task_dir)

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        for message in report.messages:
            print(message)
        print(f"Status: {report.status}")

    if report.status == "FAIL":
        return 1
    if report.status == "WARN" and not args.strict:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
