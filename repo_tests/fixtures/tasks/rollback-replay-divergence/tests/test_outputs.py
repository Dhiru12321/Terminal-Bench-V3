"""Outcome checks for the netplay matrix driver and replay artifacts."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

APP = Path("/app")
OUT = APP / "output"
REPORT = OUT / "matrix_report.json"
TRACE = OUT / "trace_bundle.jsonl"
BIN = APP / "bin" / "netplay_matrix"
PACK = APP / "data" / "seed_scenarios.json"

# Expected scenario digests with both timeline and re-exec paths corrected (full fix).
SIGNOFF = {
    "lane_stable": "530971d403b7641192ca6f69c35d4003386a69e02dc2ea98c6a48416f19bb13a",
    "split_handshake": "19a00a3924035800d95c88bbecacc8828ae416f3b2a8879dc6a4bfbfeebd3f44",
    "tape_roundtrip": "783caae8005bb6d81daf7c5729bc7238963c66c5fd50f215c6a4e3715a59ea7a",
    "staged_resume": "5aa8384a0438641d578be4bb15013bb5be5d4978c446b6d9c6a4d29fed4315be",
    "burst_lane": "0eb09f6d581ad24f63f2aa8c9a9ee2f63ca25eec5a624a3ac6a4a421185f8136",
    "archive_lane": "234dab0756dd9f9f10f7f4a891c11bae15486cea5023f0e2c6a4841bcd0a5a4a",
}

SIGNOFF_RNG_WORLD = 146
SIGNOFF_RNG_NET = 146


def run_checked(cmd: list[str], *, timeout: int = 180) -> None:
    result = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout, check=False)
    if result.returncode != 0:
        raise AssertionError(
            f"command failed: {' '.join(cmd)}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )


def run_matrix(out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    run_checked([str(BIN), "--out", str(out_dir), "--pack", str(PACK)])
    return json.loads((out_dir / "matrix_report.json").read_text(encoding="utf-8"))


def build_and_run_matrix(tmp_build: Path, out_dir: Path, *, timeline: int, reexec: int) -> dict:
    tmp_build.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    run_checked(
        [
            "cmake",
            "-S",
            str(APP),
            "-B",
            str(tmp_build),
            "-DCMAKE_BUILD_TYPE=Release",
            f"-DTB_TIMELINE_MODE={timeline}",
            f"-DTB_REEXEC_MODE={reexec}",
        ]
    )
    run_checked(["cmake", "--build", str(tmp_build), "-j2"])
    exe = tmp_build / "netplay_matrix"
    run_checked([str(exe), "--out", str(out_dir), "--pack", str(PACK)])
    return json.loads((out_dir / "matrix_report.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def report() -> dict:
    assert BIN.is_file(), "netplay_matrix binary missing"
    OUT.mkdir(parents=True, exist_ok=True)
    return run_matrix(OUT)


def test_tail_projection_non_empty(report: dict) -> None:
    """Every scenario row exposes a non-empty tail_projection string as required by the contract."""
    for sid in (
        "lane_stable",
        "split_handshake",
        "tape_roundtrip",
        "staged_resume",
        "burst_lane",
        "archive_lane",
    ):
        s = report["scenarios"][sid]
        assert "tail_projection" in s
        assert isinstance(s["tail_projection"], str)
        assert len(s["tail_projection"]) > 0


def test_straight_through_duplicate(report: dict) -> None:
    """Repeated uninterrupted runs with the same seed must agree and match the signoff digest."""
    s = report["scenarios"]["lane_stable"]
    assert s["duplicate_match"] is True
    assert s["state_digest_hex"] == SIGNOFF["lane_stable"]
    assert s["straight_run_a"] == s["straight_run_b"] == SIGNOFF["lane_stable"]


def test_reconnect_digest_matches_signoff(report: dict) -> None:
    """After a mid-run reconnect simulation, the final digest matches the corrected baseline."""
    s = report["scenarios"]["split_handshake"]
    assert s["state_digest_hex"] == SIGNOFF["split_handshake"]


def test_replay_roundtrip_agrees(report: dict) -> None:
    """Export/import of the replay blob reproduces the uninterrupted fingerprint."""
    s = report["scenarios"]["tape_roundtrip"]
    assert s["roundtrip_match"] is True
    assert s["state_digest_hex"] == SIGNOFF["tape_roundtrip"]
    assert s["roundtrip_digest"] == SIGNOFF["tape_roundtrip"]


def test_resume_path_agrees(report: dict) -> None:
    """Prefix live simulation plus decoded suffix matches the uninterrupted baseline."""
    s = report["scenarios"]["staged_resume"]
    assert s["resume_ok"] is True
    assert s["baseline_digest_hex"] == SIGNOFF["staged_resume"]
    assert s["state_digest_hex"] == SIGNOFF["staged_resume"]


def test_rollback_burst_digest(report: dict) -> None:
    """Masked remote gaps still yield a stable final digest under the stress scenario."""
    s = report["scenarios"]["burst_lane"]
    assert s["state_digest_hex"] == SIGNOFF["burst_lane"]


def test_legacy_revision_load(report: dict) -> None:
    """Revision-one blobs remain readable and produce the same outcome as the live timeline."""
    s = report["scenarios"]["archive_lane"]
    assert s["state_digest_hex"] == SIGNOFF["archive_lane"]
    assert s["legacy_revision_read"] == 1


def test_rng_streams_reported(report: dict) -> None:
    """World and net RNG counters are reported and match the expected totals for a full fix."""
    t = report["rng_channel_totals"]
    assert t["world"] == SIGNOFF_RNG_WORLD
    assert t["net"] == SIGNOFF_RNG_NET
    assert t["world"] > 0 and t["net"] > 0


def test_matrix_schema_and_revision(report: dict) -> None:
    """Matrix report carries schema and format revision metadata declared in the contract."""
    assert report["schema_version"] == 4
    assert report["replay_format_revision"] == 2
    assert report["reader_lowest_revision"] == 1


def test_trace_bundle_lines_parse(report: dict) -> None:
    """Trace bundle JSONL lines expose the tick, merged inputs, positions, and entropy field."""
    del report  # Only needed so the module-scoped fixture runs before this test under pytest-randomly.
    assert TRACE.is_file()
    lines = TRACE.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) >= 6
    for line in lines:
        row = json.loads(line)
        assert "scenario_id" in row
        assert isinstance(row["tick"], int)
        assert isinstance(row["merged_dx"], list) and len(row["merged_dx"]) == 2
        assert isinstance(row["positions"], list) and len(row["positions"]) == 2
        assert "entropy_mix" in row


def test_partial_reexec_only_lane_differs_from_signoff(tmp_path: Path) -> None:
    """Alternate harness build leaves the stable lane fingerprint off the expected value."""
    rep = build_and_run_matrix(tmp_path / "b2", tmp_path / "o2", timeline=1, reexec=2)
    assert rep["scenarios"]["lane_stable"]["state_digest_hex"] != SIGNOFF["lane_stable"]


def test_partial_timeline_only_reconnect_differs_from_signoff(tmp_path: Path) -> None:
    """Symmetric partial-fix check: a timeline-only fix (reexec still broken) must not
    produce the signoff digest for the reconnect scenario. The reexec fix affects the
    catch-up-from-queue RNG ordering that split_handshake exercises; a correct timeline
    fix alone is not sufficient."""
    rep = build_and_run_matrix(tmp_path / "b3", tmp_path / "o3", timeline=2, reexec=1)
    assert rep["scenarios"]["split_handshake"]["state_digest_hex"] != SIGNOFF["split_handshake"]
