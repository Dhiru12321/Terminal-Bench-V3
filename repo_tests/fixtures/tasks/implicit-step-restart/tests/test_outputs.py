"""Verifiers for implicit integrator restart outputs and snapshot round-tripping."""

from __future__ import annotations

import json
import math
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

APP_DIR = Path("/app")
BUILD_DIR = APP_DIR / "build"
OUT_DIR = APP_DIR / "out"
WORK_DIR = APP_DIR / "work"
BIN = BUILD_DIR / "dem_runner"
REPORT = OUT_DIR / "restart_report.json"
AUDIT = OUT_DIR / "persistence_audit.log"
GOLDEN_A = Path("/tests/golden/uninterrupted_A.jsonl")
GOLDEN_B = Path("/tests/golden/uninterrupted_B.jsonl")
GOLDEN_C = Path("/tests/golden/uninterrupted_C.jsonl")
DEFAULT_TOML = APP_DIR / "data" / "default.toml"
SNAPSHOT = WORK_DIR / "snapshot.bin"
PROBE_BUNDLE = WORK_DIR / "probe_bundle.bin"
BUNDLE_PROBE_DIR = Path("/tmp/implicit_step_restart_bundle_probe")
BUNDLE_PROBE_CPP = BUNDLE_PROBE_DIR / "main.cpp"
BUNDLE_PROBE_CMAKELISTS = BUNDLE_PROBE_DIR / "CMakeLists.txt"
BUNDLE_PROBE_BIN = BUNDLE_PROBE_DIR / "build" / "bundle_probe"


def run_checked(cmd: list[str], *, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    """Run a subprocess and surface stdout/stderr on failure."""
    result = subprocess.run(
        cmd,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"command failed: {' '.join(cmd)}\n"
            f"returncode={result.returncode}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return result


def fnv1a64(s: str) -> int:
    h = 14695981039346656037
    prime = 1099511628211
    for b in s.encode("utf-8"):
        h ^= b
        h = (h * prime) & 0xFFFFFFFFFFFFFFFF
    return h


def parse_default_toml(path: Path) -> dict[str, dict[str, str]]:
    sections: dict[str, dict[str, str]] = {}
    cur = ""
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            cur = line[1:-1].strip()
            sections.setdefault(cur, {})
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            sections.setdefault(cur, {})[k.strip()] = v.strip()
    return sections


def fingerprint_from_parsed(sec: dict[str, dict[str, str]]) -> str:
    raw = sec["mass"]["diagonal"].strip("[]")
    parts = [float(x.strip()) for x in raw.split(",") if x.strip()]
    assert len(parts) == 3
    m0, m1, m2 = parts
    k0 = float(sec["model"]["k0"])
    k1 = float(sec["model"]["k1"])
    k2 = float(sec["model"]["k2"])
    gamma = float(sec["butcher"]["gamma"])
    damp = float(sec["discretization"]["stability_extra_damping"])
    return (
        f"M:{m0:.17f},{m1:.17f},{m2:.17f}"
        f"|k0:{k0:.17f}|k1:{k1:.17f}|k2:{k2:.17f}"
        f"|gamma:{gamma:.17f}|damp:{damp:.17f}"
    )


def parse_golden(path: Path) -> tuple[list[dict], dict]:
    steps: list[dict] = []
    summary: dict = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        kind = row.get("kind")
        if kind == "step":
            steps.append(row)
        elif kind == "summary":
            summary = row
    assert summary, f"no summary line in {path}"
    return steps, summary


def relclose(a: float, b: float, rtol: float = 1e-6, atol: float = 1e-7) -> bool:
    return abs(a - b) <= max(atol, rtol * max(abs(a), abs(b), 1.0))


@pytest.fixture(scope="module", autouse=True)
def build_and_run() -> None:
    """Reconfigure, rebuild, and run from current source so stale binaries cannot pass."""
    shutil.rmtree(BUILD_DIR, ignore_errors=True)
    shutil.rmtree(OUT_DIR, ignore_errors=True)
    shutil.rmtree(WORK_DIR, ignore_errors=True)
    run_checked(["cmake", "-S", str(APP_DIR), "-B", str(BUILD_DIR), "-DCMAKE_BUILD_TYPE=Release"], timeout=180)
    run_checked(["cmake", "--build", str(BUILD_DIR), "-j2"], timeout=180)
    run_checked([str(BIN)], timeout=60)


@pytest.fixture(scope="module")
def rep() -> dict:
    """Load the restart report emitted by the freshly rebuilt harness."""
    assert REPORT.is_file(), "missing /app/out/restart_report.json after rebuild+run"
    return json.loads(REPORT.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def sec() -> dict[str, dict[str, str]]:
    """Parse the bundled TOML config that defines the operator fingerprint."""
    return parse_default_toml(DEFAULT_TOML)


@pytest.fixture(scope="module")
def bundle_probe_bin() -> Path:
    """Build a tiny helper that reloads snapshot.bin through the shipped BundleReader."""
    shutil.rmtree(BUNDLE_PROBE_DIR, ignore_errors=True)
    BUNDLE_PROBE_DIR.mkdir(parents=True, exist_ok=True)
    BUNDLE_PROBE_CPP.write_text(
        textwrap.dedent(
            """
            #include <cstdint>
            #include <iomanip>
            #include <iostream>
            #include <string>

            #include "persistence/reader.hpp"

            int main(int argc, char** argv) {
              if (argc != 3) {
                return 2;
              }
              BundleReader reader("/tmp/implicit-step-restart-bundle-probe-audit.log");
              BundlePayload payload{};
              std::string reason;
              std::uint64_t expected = 0;
              try {
                expected = static_cast<std::uint64_t>(std::stoull(argv[2]));
              } catch (...) {
                return 3;
              }
              if (!reader.try_load(argv[1], expected, payload, reason)) {
                std::cout << "FAIL " << reason << "\\n";
                return 0;
              }
              std::cout.setf(std::ios::fixed);
              std::cout << std::setprecision(17)
                        << "OK " << payload.accepted << ' ' << payload.stage_index << ' ' 
                        << payload.err_prev << ' ' << payload.integral_err << "\\n";
              return 0;
            }
            """
        ),
        encoding="utf-8",
    )
    BUNDLE_PROBE_CMAKELISTS.write_text(
        textwrap.dedent(
            """
            cmake_minimum_required(VERSION 3.20)
            project(bundle_probe LANGUAGES CXX)

            set(CMAKE_CXX_STANDARD 17)
            set(CMAKE_CXX_STANDARD_REQUIRED ON)
            set(CMAKE_CXX_EXTENSIONS OFF)

            set(APP_INCLUDE_DIR /app/include)
            set(APP_PERSIST_DIR /app/src/persistence)
            file(GLOB APP_PERSIST_SOURCES "${APP_PERSIST_DIR}/*.cpp")

            add_executable(bundle_probe main.cpp ${APP_PERSIST_SOURCES})
            target_include_directories(bundle_probe PRIVATE ${APP_INCLUDE_DIR})
            """
        ),
        encoding="utf-8",
    )
    run_checked(["cmake", "-S", str(BUNDLE_PROBE_DIR), "-B", str(BUNDLE_PROBE_DIR / "build")], timeout=120)
    run_checked(["cmake", "--build", str(BUNDLE_PROBE_DIR / "build"), "-j2"], timeout=120)
    return BUNDLE_PROBE_BIN


@pytest.fixture(scope="module")
def loaded_snapshot(rep: dict, bundle_probe_bin: Path) -> dict[str, float | int | str]:
    """Reload snapshot.bin through the task's own reader and expose the loaded state."""
    result = run_checked(
        [str(bundle_probe_bin), str(SNAPSHOT), str(rep["operator_signature_checksum"])],
        timeout=30,
    )
    parts = result.stdout.strip().split()
    assert parts, "bundle probe produced no output"
    if parts[0] != "OK":
        assert len(parts) == 2, f"unexpected probe output: {result.stdout!r}"
        return {"status": "FAIL", "reason": parts[1]}
    assert len(parts) == 5, f"unexpected probe output: {result.stdout!r}"
    return {
        "status": "OK",
        "accepted": int(parts[1]),
        "stage_index": int(parts[2]),
        "err_prev": float(parts[3]),
        "integral_err": float(parts[4]),
    }


def test_restart_report_schema(rep: dict) -> None:
    """Top-level JSON exposes checksum, probes, and three schedule blocks."""
    assert "operator_signature_checksum" in rep
    assert "integrity_probes" in rep
    ip = rep["integrity_probes"]
    assert ip.get("stale_operator_bundle_rejected") is True
    assert ip.get("stale_damping_bundle_rejected") is True
    for key in ("A", "B", "C"):
        assert key in rep["schedules"]


def test_operator_checksum_matches_config(rep: dict, sec: dict[str, dict[str, str]]) -> None:
    """Checksum matches the FNV fingerprint documented for the bundled TOML."""
    fp = fingerprint_from_parsed(sec)
    assert rep["operator_signature_checksum"] == fnv1a64(fp)


def test_schedule_parity_against_golden_a(rep: dict) -> None:
    """Schedule A matches the golden stream for final state and step counts."""
    steps, summary = parse_golden(GOLDEN_A)
    sch = rep["schedules"]["A"]
    assert sch["ok"] is True
    assert sch["accepted_steps"] == summary["accepted_steps"]
    assert sch["rejected_steps"] == summary["rejected_steps"]
    last = steps[-1]
    assert relclose(sch["final_time"], last["t"])
    for i in range(3):
        assert relclose(sch["final_state"][i], last["y"][i])
    if summary.get("event_time") is not None:
        assert sch["event_time"] is not None
        assert relclose(sch["event_time"], float(summary["event_time"]), atol=5e-7)
    else:
        assert sch["event_time"] is None


def test_schedule_parity_against_golden_b(rep: dict) -> None:
    """Schedule B reproduces the golden stream after an interrupt inside stage-1 Newton work."""
    steps, summary = parse_golden(GOLDEN_B)
    sch = rep["schedules"]["B"]
    assert sch["ok"] is True
    assert sch["accepted_steps"] == summary["accepted_steps"]
    assert sch["rejected_steps"] == summary["rejected_steps"]
    last = steps[-1]
    assert relclose(sch["final_time"], last["t"])
    for i in range(3):
        assert relclose(sch["final_state"][i], last["y"][i])
    if summary.get("event_time") is not None:
        assert sch["event_time"] is not None
        assert relclose(sch["event_time"], float(summary["event_time"]), atol=5e-7)
    else:
        assert sch["event_time"] is None


def test_schedule_parity_against_golden_c(rep: dict) -> None:
    """Schedule C preserves the saved stage index and matches the golden summary exactly."""
    steps, summary = parse_golden(GOLDEN_C)
    sch = rep["schedules"]["C"]
    assert sch["ok"] is True
    assert sch["accepted_steps"] == summary["accepted_steps"]
    assert sch["rejected_steps"] == summary["rejected_steps"]
    last = steps[-1]
    assert relclose(sch["final_time"], last["t"])
    for i in range(3):
        assert relclose(sch["final_state"][i], last["y"][i])
    if summary.get("event_time") is not None:
        assert sch["event_time"] is not None
        assert relclose(sch["event_time"], float(summary["event_time"]), atol=5e-7)
    else:
        assert sch["event_time"] is None


def test_newton_work_cap_each_schedule(rep: dict) -> None:
    """Post-restart Newton totals stay within the documented budget versus each golden reference."""
    for key, path in (("A", GOLDEN_A), ("B", GOLDEN_B), ("C", GOLDEN_C)):
        _, summary = parse_golden(path)
        n_ref = int(summary["newton_iterations"])
        n_run = int(rep["schedules"][key]["newton_iterations"])
        assert n_run <= 1.35 * n_ref + 8.0


def test_bundle_reader_restores_nonzero_controller_accumulator(loaded_snapshot: dict[str, float | int | str]) -> None:
    """Reloading snapshot.bin through the shipped reader recovers nonzero controller memory."""
    assert loaded_snapshot["status"] == "OK", loaded_snapshot
    assert loaded_snapshot["accepted"] == 1
    assert loaded_snapshot["stage_index"] == 0
    assert 0.0 < loaded_snapshot["err_prev"] < 1.0
    assert not math.isclose(float(loaded_snapshot["integral_err"]), 0.0, abs_tol=1e-12)
    assert float(loaded_snapshot["integral_err"]) < -0.1


def test_persistence_audit_is_exact_load_only_story() -> None:
    """Audit log contains only load attempts on snapshot.bin: three accepts and two signature mismatches."""
    assert AUDIT.is_file(), "missing /app/out/persistence_audit.log after rebuild+run"
    text = AUDIT.read_text(encoding="utf-8")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    assert len(lines) == 5, f"expected 5 load-attempt lines, got {len(lines)}: {lines}"
    assert all(line.startswith("ATTEMPT LOAD ") for line in lines)
    assert all(str(SNAPSHOT) in line for line in lines)
    assert all("probe_bundle.bin" not in line for line in lines)
    assert sum("STATUS=ACCEPTED REASON=OK" in line for line in lines) == 3
    assert sum("STATUS=REJECTED REASON=SIGNATURE_MISMATCH" in line for line in lines) == 2
    assert not any("WRITE bundle" in line for line in lines)
    assert not PROBE_BUNDLE.exists()


def test_all_schedules_marked_ok(rep: dict) -> None:
    """Every schedule completes successfully in the combined restart report."""
    for key in ("A", "B", "C"):
        assert rep["schedules"][key]["ok"] is True


def test_no_trailing_corrupt_json(rep: dict) -> None:
    """Restart report is a single JSON object without trailing garbage."""
    raw = REPORT.read_text(encoding="utf-8").strip()
    assert raw.endswith("}")
    assert json.loads(raw) == rep
