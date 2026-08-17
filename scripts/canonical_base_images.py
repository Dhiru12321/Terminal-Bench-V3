"""Canonical Terminal-Bench runtime base images (digest-pinned).

The final runtime ``FROM`` in ``environment/Dockerfile`` should use one of these
exact digests. Minor tag/registry variants (``python:…`` vs
``public.ecr.aws/docker/library/python:…``) are equivalent when the digest
matches.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class CanonicalBaseImage:
    reference: str
    family: str
    covers: str


CANONICAL_BASE_IMAGES: tuple[CanonicalBaseImage, ...] = (
    CanonicalBaseImage(
        reference=(
            "public.ecr.aws/docker/library/python:3.13-slim-bookworm"
            "@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb"
        ),
        family="Python",
        covers="All Python 3.10/3.11/3.12/3.13 majors + patch + slim/non-slim",
    ),
    CanonicalBaseImage(
        reference=(
            "public.ecr.aws/docker/library/node:22-bookworm-slim"
            "@sha256:f3a68cf41a855d227d1b0ab832bed9749469ef38cf4f58182fb8c893bc462383"
        ),
        family="Node.js",
        covers="All Node 18/20/22/24 majors + slim/non-slim",
    ),
    CanonicalBaseImage(
        reference=(
            "public.ecr.aws/docker/library/golang:1.24-bookworm"
            "@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac"
        ),
        family="Go",
        covers="All Go 1.21–1.26 majors + alpine/bullseye/bookworm",
    ),
    CanonicalBaseImage(
        reference=(
            "public.ecr.aws/docker/library/rust:1.85-slim"
            "@sha256:9f841bbe9e7d8e37ceb96ed907265a3a0df7f44e3737d0b100e7907a679acb36"
        ),
        family="Rust",
        covers="All Rust 1.75–1.95 + slim/non-slim + bullseye",
    ),
    CanonicalBaseImage(
        reference=(
            "public.ecr.aws/docker/library/eclipse-temurin:21-jdk-jammy"
            "@sha256:25d1276565738d3c805e632a4542c3a7598866ef967f4def6544c15de3a74b14"
        ),
        family="Java (JDK)",
        covers="All Java 17/21 jdk-jammy/noble variants",
    ),
    CanonicalBaseImage(
        reference=(
            "public.ecr.aws/docker/library/gcc:13-bookworm"
            "@sha256:930f2ebe239275fa67226654cb79273ea34eee672ae61c8a39f689c37fb7ac5c"
        ),
        family="C / C++ (GCC)",
        covers="All GCC 12/13/14/15 variants",
    ),
    CanonicalBaseImage(
        reference=(
            "public.ecr.aws/docker/library/ruby:3.3-slim-bookworm"
            "@sha256:e76733e94b3a5893e4a141024ef3a583dc10781dc24becebf74f9c9f9a33e3df"
        ),
        family="Ruby",
        covers="All Ruby 3.2/3.3/3.4 + slim/non-slim",
    ),
    CanonicalBaseImage(
        reference=(
            "public.ecr.aws/docker/library/maven:3.9.9-eclipse-temurin-21"
            "@sha256:3a4ab3276a087bf276f79cae96b1af04f53731bec53fb2e651aca79e4b10211e"
        ),
        family="Maven",
        covers="All Maven + temurin-17/21 variants",
    ),
    CanonicalBaseImage(
        reference=(
            "public.ecr.aws/docker/library/debian:bookworm-slim"
            "@sha256:4724b8cc51e33e398f0e2e15e18d5ec2851ff0c2280647e1310bc1642182655d"
        ),
        family="Debian",
        covers="All Debian bookworm/bullseye/12.x slim variants",
    ),
    CanonicalBaseImage(
        reference=(
            "public.ecr.aws/docker/library/ubuntu:24.04"
            "@sha256:0d39fcc8335d6d74d5502f6df2d30119ff4790ebbb60b364818d5112d9e3e932"
        ),
        family="Ubuntu",
        covers="All Ubuntu 22.04/24.04/jammy variants",
    ),
)

IMAGE_DIGEST_PATTERN = re.compile(r"@sha256:([a-f0-9]{64})\b", re.IGNORECASE)

JUSTIFICATION_MARKER_PATTERN = re.compile(
    r"(?:non[- ]canonical\s+base\s+image|canonical[- ]base[- ]image)"
    r"(?:\s+justification)?\s*:\s*(.+)",
    re.IGNORECASE,
)

BOILERPLATE_JUSTIFICATION_PATTERN = re.compile(
    r"^(?:tbd|todo|n/?a|none|pending|fixme|\.{2,}|-+|see\s+docs?|"
    r"placeholder|coming\s+soon|lorem\s+ipsum)\s*\.?$",
    re.IGNORECASE,
)


def extract_image_digest(image: str) -> str | None:
    match = IMAGE_DIGEST_PATTERN.search(image)
    return match.group(1).lower() if match else None


CANONICAL_BASE_IMAGE_DIGESTS: frozenset[str] = frozenset(
    digest
    for entry in CANONICAL_BASE_IMAGES
    if (digest := extract_image_digest(entry.reference)) is not None
)


def docker_image_is_scratch(image: str) -> bool:
    return image.split("@", 1)[0].strip().lower() == "scratch"


def docker_image_is_canonical_base(image: str) -> bool:
    digest = extract_image_digest(image)
    return digest is not None and digest in CANONICAL_BASE_IMAGE_DIGESTS


def is_credible_justification(text: str) -> bool:
    normalized = " ".join(text.split())
    if len(normalized) < 40:
        return False
    if BOILERPLATE_JUSTIFICATION_PATTERN.match(normalized):
        return False
    return True


def _dockerfile_comment_justifications(dockerfile_text: str) -> list[str]:
    justifications: list[str] = []
    for raw_line in dockerfile_text.splitlines():
        stripped = raw_line.strip()
        if not stripped.startswith("#"):
            continue
        comment = stripped.lstrip("#").strip()
        marker_match = JUSTIFICATION_MARKER_PATTERN.search(comment)
        if marker_match:
            justifications.append(marker_match.group(1).strip())
            continue
        if re.search(r"non[- ]canonical|canonical[- ]base[- ]image", comment, re.IGNORECASE):
            justifications.append(comment)
    return justifications


def find_non_canonical_justification(task_dir, dockerfile_text: str) -> str | None:
    """Locate a credible non-canonical justification in the Dockerfile.

    Terminus 3 generates README.md during platform packaging from the task.toml
    explanation fields, so a README section never reaches the CI check; the
    Dockerfile comment is the only place a justification survives.
    """
    del task_dir
    for candidate in _dockerfile_comment_justifications(dockerfile_text):
        if is_credible_justification(candidate):
            return candidate
    return None


def canonical_base_image_for_digest(digest: str) -> CanonicalBaseImage | None:
    normalized = digest.lower()
    for entry in CANONICAL_BASE_IMAGES:
        entry_digest = extract_image_digest(entry.reference)
        if entry_digest == normalized:
            return entry
    return None
