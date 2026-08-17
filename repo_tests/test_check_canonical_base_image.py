from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts import canonical_base_images, check_canonical_base_image
from repo_tests.cases import FIXTURE_TASKS_DIR


class CanonicalBaseImagesTest(unittest.TestCase):
    def test_all_entries_have_unique_digests(self) -> None:
        digests = [
            canonical_base_images.extract_image_digest(entry.reference)
            for entry in canonical_base_images.CANONICAL_BASE_IMAGES
        ]
        self.assertEqual(len(digests), len(set(digests)))
        self.assertTrue(all(digests))

    def test_ecr_and_short_registry_refs_match_by_digest(self) -> None:
        digest = "01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb"
        short_ref = f"python:3.13-slim-bookworm@sha256:{digest}"
        ecr_ref = (
            "public.ecr.aws/docker/library/python:3.13-slim-bookworm"
            f"@sha256:{digest}"
        )
        self.assertTrue(canonical_base_images.docker_image_is_canonical_base(short_ref))
        self.assertTrue(canonical_base_images.docker_image_is_canonical_base(ecr_ref))


class CheckCanonicalBaseImageTest(unittest.TestCase):
    def test_canonical_debian_fixture_passes(self) -> None:
        report = check_canonical_base_image.check_task(
            FIXTURE_TASKS_DIR / "lsm-snapshot-recovery"
        )
        self.assertEqual(report.status, "PASS")
        self.assertTrue(report.canonical)

    def test_non_canonical_without_justification_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            task_dir = Path(tmpdir) / "task"
            task_dir.mkdir()
            (task_dir / "environment").mkdir()
            (task_dir / "environment" / "Dockerfile").write_text(
                "FROM golang:1.22-bookworm@sha256:"
                "1f298b0c9fecdf504389a0329236f948cc04a566a2bb32337207cbaaa2f8177c\n"
                "WORKDIR /app\n",
                encoding="utf-8",
            )
            report = check_canonical_base_image.check_task(task_dir)
        self.assertEqual(report.status, "FAIL")

    def test_non_canonical_with_dockerfile_justification_warns(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            task_dir = Path(tmpdir) / "task"
            task_dir.mkdir()
            (task_dir / "environment").mkdir()
            (task_dir / "environment" / "Dockerfile").write_text(
                "# Non-canonical base image: needs CUDA runtime not covered by canonical images.\n"
                "FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04@sha256:"
                "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n"
                "WORKDIR /app\n",
                encoding="utf-8",
            )
            report = check_canonical_base_image.check_task(task_dir)
        self.assertEqual(report.status, "WARN")
        self.assertIsNotNone(report.justification)


if __name__ == "__main__":
    unittest.main()
