"""Verifier for storesim replay bundles and /app/output/report.json."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

APP = Path("/app")

_GO = shutil.which("go") or "/usr/local/go/bin/go"
REPORT = APP / "output" / "report.json"
FIXTURES = APP / "fixtures" / "replays"
CONFIG = APP / "config" / "sim_defaults.yaml"

GOLD_FAILOVER_SHA = (
    "acfde0f01079e331794c5aeb5bb2b6cdb970b44f42f772caed429f8a7bd84b42"
)
GOLD_LARGE_SHA = "9d2568c97ec622262333bf17035b8a9cd989a07723ecec1855e734c2c0864f05"
GOLD_MIXED_SHA = "3d3f19b6694b9579934d9e2db30e6387c2fcad99eaae6eb548d237fb05f08f8e"


def _environ_for_build() -> dict[str, str]:
    env = os.environ.copy()
    prefix = "/usr/local/go/bin"
    if prefix not in env.get("PATH", ""):
        env["PATH"] = f"{prefix}:{env.get('PATH', '')}"
    return env


def rebuild_storesim() -> None:
    subprocess.run(
        [_GO, "build", "-o", "/app/storesim", "./cmd/storesim"],
        cwd=str(APP),
        check=True,
        env=_environ_for_build(),
    )


def run_storesim() -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["/app/storesim", "-replays", str(FIXTURES), "-out", str(REPORT)],
        cwd=str(APP),
        check=True,
        env=_environ_for_build(),
    )


def run_storesim_env(extra: dict[str, str]) -> None:
    env = _environ_for_build()
    env.update(extra)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["/app/storesim", "-replays", str(FIXTURES), "-out", str(REPORT)],
        cwd=str(APP),
        check=True,
        env=env,
    )


@pytest.fixture(scope="session", autouse=True)
def _session_build() -> None:
    rebuild_storesim()


@pytest.fixture()
def report() -> dict:
    run_storesim()
    return json.loads(REPORT.read_text())


def _replay_by_name(report: dict, name: str) -> dict:
    for r in report["replays"]:
        if r["name"] == name:
            return r
    raise AssertionError(f"missing replay {name!r}")


def test_report_schema(report: dict) -> None:
    """report.json matches the published contract."""
    assert isinstance(report, dict)
    reps = report["replays"]
    assert isinstance(reps, list) and len(reps) == 3
    names = sorted(r["name"] for r in reps)
    assert names == [
        "failover_rebalance",
        "large_segment_handoff",
        "mixed_catalog_merge",
    ]
    for r in reps:
        assert set(r.keys()) >= {
            "name",
            "finish_reason",
            "steps",
            "delivery_applies",
            "reloc_ticks",
            "checkpoints",
        }
        assert isinstance(r["name"], str)
        assert isinstance(r["finish_reason"], str)
        assert isinstance(r["steps"], int)
        assert isinstance(r["delivery_applies"], int)
        assert isinstance(r["reloc_ticks"], int)
        assert isinstance(r["checkpoints"], list)
        for ck in r["checkpoints"]:
            assert isinstance(ck["id"], str)
            assert isinstance(ck["tensor_sha256_hex"], str)
            assert len(ck["tensor_sha256_hex"]) == 64


def test_all_bundled_replays_complete(report: dict) -> None:
    """Every bundled replay reaches a completed simulation."""
    for name in (
        "failover_rebalance",
        "large_segment_handoff",
        "mixed_catalog_merge",
    ):
        assert _replay_by_name(report, name)["finish_reason"] == "complete"


def test_checkpoint_digests_failover(report: dict) -> None:
    """Failover checkpoint tensor digest matches the regression golden."""
    r = _replay_by_name(report, "failover_rebalance")
    ck = {c["id"]: c["tensor_sha256_hex"] for c in r["checkpoints"]}
    assert ck["ck0"] == GOLD_FAILOVER_SHA


def test_large_segment_handoff_digest(report: dict) -> None:
    """Wide streaming fingerprint path matches golden for the large handoff bundle."""
    r = _replay_by_name(report, "large_segment_handoff")
    assert r["finish_reason"] == "complete"
    ck = {c["id"]: c["tensor_sha256_hex"] for c in r["checkpoints"]}
    assert ck["wide0"] == GOLD_LARGE_SHA


def test_mixed_catalog_planner_safety(report: dict) -> None:
    """Mixed-version catalog snapshot allows the planner to finish rebalance."""
    r = _replay_by_name(report, "mixed_catalog_merge")
    assert r["finish_reason"] == "complete"
    assert r["reloc_ticks"] >= 1
    ck = {c["id"]: c["tensor_sha256_hex"] for c in r["checkpoints"]}
    assert ck["live"] == GOLD_MIXED_SHA


def test_no_relocation_disable() -> None:
    """Relocation stays enabled in defaults and the unsafe env knob does not change digests."""
    text = CONFIG.read_text()
    assert "enabled: true" in text
    assert "strict_legacy_only: false" in text
    run_storesim()
    base = json.loads(REPORT.read_text())
    run_storesim_env({"STORESIM_UNSAFE_FASTPATH": "1"})
    alt = json.loads(REPORT.read_text())
    assert _replay_by_name(base, "failover_rebalance") == _replay_by_name(
        alt, "failover_rebalance"
    )


def test_epoch_journal_idempotency(report: dict) -> None:
    """Journal replay does not double-apply the same delivery for the failover bundle."""
    r = _replay_by_name(report, "failover_rebalance")
    assert r["delivery_applies"] == 1


def test_fixture_isolation_random_order(report: dict) -> None:
    """Re-running the driver yields stable checkpoint bytes (order-agnostic harness)."""
    run_storesim()
    second = json.loads(REPORT.read_text())
    assert report["replays"] == second["replays"]
