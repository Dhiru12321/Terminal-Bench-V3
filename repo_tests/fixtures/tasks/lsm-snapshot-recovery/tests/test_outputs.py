"""Behavioral verifier for pinned views, compaction visibility, and WAL-prefix recovery."""

from __future__ import annotations

import json
import random
import shutil
import subprocess
import textwrap
from dataclasses import dataclass, field
from pathlib import Path

import pytest

APP_DIR = Path("/app")
BUILD_DIR = APP_DIR / "build"
DATA_DIR = APP_DIR / "data"
SAMPLES_DIR = APP_DIR / "samples"
SRC_ROOT = APP_DIR / "src"
TRACE_DRIVER = Path("/app/build/trace_driver")
PROBE_DIR = Path("/tmp/lsm_snapshot_probe")
PROBE_CPP = PROBE_DIR / "main.cpp"
PROBE_CMAKELISTS = PROBE_DIR / "CMakeLists.txt"
PROBE_BIN = PROBE_DIR / "build" / "engine_probe"
NO_EMBED_TOKEN = "tb_probe_noembed_z88"
TOMB = "__T__"


@dataclass
class Snap:
    vals: dict[str, str] = field(default_factory=dict)
    tombs: set[str] = field(default_factory=set)


@dataclass
class Tile:
    id: int
    rows: dict[str, str]


class OracleState:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.tiles: list[Tile] = []
        self.buffer: dict[str, str] = {}
        self.pins: list[Snap] = []
        self.layout_generation = 0
        self.next_tile = 1
        self.wal_text = ""

    def append_wal(self, rec: dict) -> None:
        self.wal_text += json.dumps(rec, separators=(",", ":"), sort_keys=True) + "\n"

    def base_from_tiles(self) -> Snap:
        acc = Snap()
        for tile in self.tiles:
            acc = self.merge_overlay(acc, tile.rows)
        return acc

    def materialize_visible(self) -> Snap:
        return self.merge_overlay(self.base_from_tiles(), self.buffer)

    @staticmethod
    def merge_overlay(base: Snap, rows: dict[str, str]) -> Snap:
        out = Snap(dict(base.vals), set(base.tombs))
        for key, value in rows.items():
            if value == TOMB:
                out.tombs.add(key)
                out.vals.pop(key, None)
            else:
                out.vals[key] = value
                out.tombs.discard(key)
        return out

    @staticmethod
    def fold(older: Tile, newer: Tile) -> Tile:
        rows = dict(newer.rows)
        for key, value in older.rows.items():
            if key not in rows:
                rows[key] = value
        # Tile storage is key-sorted in the engine's map-backed representation.
        return Tile(newer.id, dict(sorted(rows.items())))

    @staticmethod
    def encode_get(snap: Snap, key: str) -> str:
        if key in snap.tombs:
            return "obliterate"
        return snap.vals.get(key, "")

    @staticmethod
    def encode_scan(snap: Snap, start: str, end: str) -> str:
        parts: list[str] = []
        for key in sorted(snap.vals):
            if key < start or key > end or key in snap.tombs:
                continue
            parts.append(f"{key}:{snap.vals[key]}")
        return ";".join(parts)

    def structure_snapshot(self) -> dict:
        tiles = []
        for tile in self.tiles:
            keys = list(tile.rows)
            tiles.append({"id": tile.id, "sorted_keys": keys == sorted(keys)})
        return {"tiles": tiles, "layout_generation": self.layout_generation}

    def materialize_buffer_to_tile(self) -> None:
        if not self.buffer:
            return
        # Buffer materialization into a tile follows map ordering semantics.
        self.tiles.append(Tile(self.next_tile, dict(sorted(self.buffer.items()))))
        self.next_tile += 1
        self.buffer.clear()

    def recover_from_wal(self) -> None:
        replay = self.wal_text
        self.tiles = []
        self.buffer = {}
        self.pins = []
        self.layout_generation = 0
        self.next_tile = 1
        for raw in replay.splitlines():
            if not raw:
                continue
            try:
                rec = json.loads(raw)
            except json.JSONDecodeError:
                # Replay ignores malformed trailing fragments and continues.
                continue
            self.apply_replay_line(rec)

    def apply_replay_line(self, rec: dict) -> None:
        op = rec["op"]
        if op == "put":
            self.buffer[rec["key"]] = rec["value"]
        elif op == "obliterate":
            self.buffer[rec["key"]] = TOMB
        elif op == "flush":
            self.materialize_buffer_to_tile()
        elif op == "merge":
            if len(self.tiles) >= 2:
                older = self.tiles[-2]
                newer = self.tiles[-1]
                self.tiles = self.tiles[:-2] + [self.fold(older, newer)]
        elif op == "open_pin":
            self.pins.append(self.materialize_visible())
        elif op == "close_pin":
            if self.pins:
                self.pins.pop()
        elif op == "layout_bump":
            self.layout_generation += rec["delta"]

    def apply(self, op: dict) -> dict | None:
        name = op["op"]
        if name == "put":
            self.append_wal({"op": "put", "key": op["key"], "value": op["value"]})
            self.buffer[op["key"]] = op["value"]
            return None
        if name == "obliterate":
            self.append_wal({"op": "obliterate", "key": op["key"]})
            self.buffer[op["key"]] = TOMB
            return None
        if name == "flush":
            self.append_wal({"op": "flush"})
            self.materialize_buffer_to_tile()
            return None
        if name == "merge":
            if len(self.tiles) >= 2:
                older = self.tiles[-2]
                newer = self.tiles[-1]
                folded = self.fold(older, newer)
                self.tiles = self.tiles[:-2] + [folded]
                self.append_wal({"op": "merge", "out_id": folded.id})
            return None
        if name == "open_pin":
            self.append_wal({"op": "open_pin", "id": len(self.pins) + 1})
            self.pins.append(self.materialize_visible())
            return None
        if name == "close_pin":
            self.append_wal({"op": "close_pin"})
            if self.pins:
                self.pins.pop()
            return None
        if name == "crash_truncate_journal":
            self.wal_text = self.wal_text[: int(op["keep_bytes"])]
            return None
        if name == "restart":
            self.recover_from_wal()
            return None
        if name == "partial_layout_bump":
            self.append_wal({"op": "layout_bump", "delta": int(op["delta"])})
            self.layout_generation += int(op["delta"])
            return None
        if name == "get":
            snap = self.pins[-1] if self.pins else self.materialize_visible()
            return {"kind": "get", "key": op["key"], "value": self.encode_get(snap, op["key"])}
        if name == "scan":
            snap = self.pins[-1] if self.pins else self.materialize_visible()
            return {"kind": "scan", "start": op["start"], "end": op["end"], "value": self.encode_scan(snap, op["start"], op["end"])}
        if name == "check_structure":
            return {"kind": "structure", "value": self.structure_snapshot()}
        raise ValueError(f"unknown op: {name}")

    def run(self, ops: list[dict]) -> list[dict]:
        out: list[dict] = []
        for idx, op in enumerate(ops):
            obs = self.apply(op)
            if obs is not None:
                out.append({"index": idx, **obs})
        return out


def run_checked(cmd: list[str], *, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout, check=False)
    if result.returncode != 0:
        raise AssertionError(
            f"command failed: {' '.join(cmd)}\n"
            f"returncode={result.returncode}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return result


def build_probe() -> None:
    PROBE_DIR.mkdir(parents=True, exist_ok=True)
    PROBE_CPP.write_text(
        textwrap.dedent(
            """
            #include <filesystem>
            #include <fstream>
            #include <nlohmann/json.hpp>

            #include "api/engine.hpp"

            namespace {
            void write_report(const std::filesystem::path& p, const nlohmann::json& j) {
              std::ofstream o(p);
              o << j.dump(2) << "\\n";
            }
            }

            int main(int argc, char** argv) {
              if (argc != 3) {
                return 2;
              }
              std::ifstream in(argv[1]);
              if (!in) {
                return 2;
              }
              nlohmann::json scenario = nlohmann::json::parse(in);
              ts::Engine eng;
              eng.reset_for_test();
              nlohmann::json out;
              out["scenario_id"] = scenario.value("scenario_id", std::string("unknown"));
              out["observations"] = nlohmann::json::array();
              const auto& ops = scenario.at("ops");
              for (std::size_t i = 0; i < ops.size(); ++i) {
                const auto& op = ops[i];
                const std::string name = op.at("op").get<std::string>();
                if (name == "put") {
                  eng.put(op.at("key").get<std::string>(), op.at("value").get<std::string>());
                } else if (name == "obliterate") {
                  eng.obliterate(op.at("key").get<std::string>());
                } else if (name == "flush") {
                  eng.flush();
                } else if (name == "merge") {
                  eng.merge();
                } else if (name == "open_pin") {
                  eng.open_pin();
                } else if (name == "close_pin") {
                  eng.close_pin();
                } else if (name == "crash_truncate_journal") {
                  eng.crash_truncate_journal(static_cast<std::size_t>(op.at("keep_bytes").get<int>()));
                } else if (name == "restart") {
                  eng.restart();
                } else if (name == "partial_layout_bump") {
                  eng.partial_layout_bump(op.at("delta").get<int>());
                } else if (name == "get") {
                  const std::string key = op.at("key").get<std::string>();
                  out["observations"].push_back({{"index", i}, {"kind", "get"}, {"key", key}, {"value", eng.get(key)}});
                } else if (name == "scan") {
                  const std::string start = op.at("start").get<std::string>();
                  const std::string end = op.at("end").get<std::string>();
                  out["observations"].push_back({{"index", i}, {"kind", "scan"}, {"start", start}, {"end", end}, {"value", eng.scan(start, end)}});
                } else if (name == "check_structure") {
                  out["observations"].push_back({{"index", i}, {"kind", "structure"}, {"value", eng.structure_snapshot()}});
                }
              }
              write_report(argv[2], out);
              return 0;
            }
            """
        ),
        encoding="utf-8",
    )
    PROBE_CMAKELISTS.write_text(
        textwrap.dedent(
            """
            cmake_minimum_required(VERSION 3.20)
            project(engine_probe LANGUAGES CXX)

            set(CMAKE_CXX_STANDARD 17)
            set(CMAKE_CXX_STANDARD_REQUIRED ON)
            set(CMAKE_CXX_EXTENSIONS OFF)

            find_package(nlohmann_json 3.2.0 REQUIRED)

            add_executable(engine_probe
              main.cpp
              /app/src/api/engine.cpp
              /app/src/wal_record/wal.cpp
              /app/src/buffer/buffer.cpp
              /app/src/tile/tile.cpp
              /app/src/layout_index/layout.cpp
              /app/src/level_merge/merge.cpp
              /app/src/cursor_pin/pin.cpp
            )
            target_include_directories(engine_probe PRIVATE /app/src)
            target_link_libraries(engine_probe PRIVATE nlohmann_json::nlohmann_json)
            """
        ),
        encoding="utf-8",
    )
    run_checked(["cmake", "-S", str(PROBE_DIR), "-B", str(PROBE_DIR / "build")], timeout=180)
    run_checked(["cmake", "--build", str(PROBE_DIR / "build"), "-j2"], timeout=180)


@pytest.fixture(scope="session", autouse=True)
def build_project_and_probe() -> None:
    shutil.rmtree(BUILD_DIR, ignore_errors=True)
    shutil.rmtree(PROBE_DIR, ignore_errors=True)
    shutil.rmtree(DATA_DIR, ignore_errors=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    run_checked(["cmake", "-S", str(APP_DIR), "-B", str(BUILD_DIR), "-DCMAKE_BUILD_TYPE=Release"], timeout=180)
    run_checked(["cmake", "--build", str(BUILD_DIR), "-j2"], timeout=180)
    build_probe()


def run_scenario(ops: list[dict], scenario_id: str, tmp_path: Path) -> dict:
    scenario = {"scenario_id": scenario_id, "ops": ops}
    scen_path = tmp_path / f"{scenario_id}.json"
    report_path = tmp_path / f"{scenario_id}.report.json"
    scen_path.write_text(json.dumps(scenario), encoding="utf-8")
    run_checked([str(PROBE_BIN), str(scen_path), str(report_path)], timeout=60)
    return json.loads(report_path.read_text(encoding="utf-8"))


def expected_report(ops: list[dict], scenario_id: str) -> dict:
    oracle = OracleState()
    return {"scenario_id": scenario_id, "observations": oracle.run(ops)}


def assert_matches_contract(ops: list[dict], scenario_id: str, tmp_path: Path) -> dict:
    got = run_scenario(ops, scenario_id, tmp_path)
    want = expected_report(ops, scenario_id)
    assert got == want
    return got


def sorted_tile_rows() -> dict[str, list[str]]:
    rows: dict[str, list[str]] = {}
    for path in sorted(DATA_DIR.glob("tile_*.dat")):
        keys: list[str] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            keys.append(line.split("	", 1)[0])
        rows[path.name] = keys
    return rows


def scenario_from_file(path: Path) -> tuple[str, list[dict]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload["scenario_id"], payload["ops"]


def build_generated_scenario(seed: int, length: int = 48) -> list[dict]:
    rng = random.Random(seed)
    oracle = OracleState()
    keys = ["a", "b", "c", "d", "e", "f"]
    values = ["0", "1", "2", "3", "4", "5", "6"]
    ops: list[dict] = []

    for _ in range(length):
        choices = ["put", "obliterate", "get", "scan", "flush", "layout", "check_structure", "restart"]
        if len(oracle.tiles) >= 2:
            choices.append("merge")
        if len(oracle.pins) < 2:
            choices.append("open_pin")
        if oracle.pins:
            choices.append("close_pin")
        if oracle.wal_text:
            choices.append("truncate")

        pick = rng.choice(choices)
        if pick == "put":
            op = {"op": "put", "key": rng.choice(keys), "value": rng.choice(values)}
        elif pick == "obliterate":
            op = {"op": "obliterate", "key": rng.choice(keys)}
        elif pick == "get":
            op = {"op": "get", "key": rng.choice(keys)}
        elif pick == "scan":
            lo = rng.choice(keys)
            hi = rng.choice(keys)
            start, end = sorted((lo, hi))
            op = {"op": "scan", "start": start, "end": end}
        elif pick == "flush":
            op = {"op": "flush"}
        elif pick == "merge":
            op = {"op": "merge"}
        elif pick == "open_pin":
            op = {"op": "open_pin"}
        elif pick == "close_pin":
            op = {"op": "close_pin"}
        elif pick == "layout":
            op = {"op": "partial_layout_bump", "delta": rng.randint(1, 9)}
        elif pick == "check_structure":
            op = {"op": "check_structure"}
        elif pick == "restart":
            op = {"op": "restart"}
        elif pick == "truncate":
            cut_points = sorted({0, 1, max(0, len(oracle.wal_text) // 3), max(0, len(oracle.wal_text) // 2), max(0, len(oracle.wal_text) - 1), len(oracle.wal_text)})
            op = {"op": "crash_truncate_journal", "keep_bytes": rng.choice(cut_points)}
        else:
            raise AssertionError(pick)
        ops.append(op)
        oracle.apply(op)

    ops.extend([
        {"op": "get", "key": "a"},
        {"op": "scan", "start": "a", "end": "f"},
        {"op": "check_structure"},
    ])
    return ops


def test_project_rebuild_produces_trace_driver() -> None:
    """The verifier rebuilds the shipped project and its separate probe from current source."""
    assert TRACE_DRIVER.exists()
    assert PROBE_BIN.exists()


def test_sample_cases_match_contract(tmp_path: Path) -> None:
    """Bundled incident-style sample traces must match the behavioral oracle exactly."""
    for sample_path in sorted(SAMPLES_DIR.glob("case_*.json")):
        scenario_id, ops = scenario_from_file(sample_path)
        assert_matches_contract(ops, scenario_id, tmp_path)


def test_generated_scenarios_match_contract(tmp_path: Path) -> None:
    """Seeded mixed scenarios must agree with the oracle across reads, folds, and restarts."""
    for seed in [7, 19, 41, 73, 101]:
        ops = build_generated_scenario(seed)
        assert_matches_contract(ops, f"generated_{seed}", tmp_path)


def test_recovery_from_varied_prefixes_matches_contract(tmp_path: Path) -> None:
    """Multiple WAL truncation prefixes must replay to the same state as the oracle."""
    prefix = [
        {"op": "put", "key": "aa", "value": "1"},
        {"op": "flush"},
        {"op": "put", "key": "bb", "value": "2"},
        {"op": "open_pin"},
        {"op": "obliterate", "key": "aa"},
        {"op": "flush"},
        {"op": "merge"},
        {"op": "partial_layout_bump", "delta": 5},
        {"op": "close_pin"},
    ]
    oracle = OracleState()
    for op in prefix:
        oracle.apply(op)
    for keep_bytes in [0, 1, 17, 43, 71, 999]:
        actual_keep = min(keep_bytes, len(oracle.wal_text))
        ops = prefix + [
            {"op": "crash_truncate_journal", "keep_bytes": actual_keep},
            {"op": "restart"},
            {"op": "get", "key": "aa"},
            {"op": "get", "key": "bb"},
            {"op": "scan", "start": "aa", "end": "zz"},
            {"op": "check_structure"},
        ]
        assert_matches_contract(ops, f"prefix_{actual_keep}", tmp_path)


def test_materialized_tiles_remain_sorted_after_compaction_and_restart(tmp_path: Path) -> None:
    """Compaction output must stay sorted on disk while the logical snapshot remains correct."""
    ops = [
        {"op": "put", "key": "z", "value": "9"},
        {"op": "put", "key": "y", "value": "8"},
        {"op": "flush"},
        {"op": "put", "key": "x", "value": "7"},
        {"op": "flush"},
        {"op": "merge"},
        {"op": "partial_layout_bump", "delta": 6},
        {"op": "restart"},
        {"op": "check_structure"},
    ]
    assert_matches_contract(ops, "tile_sort", tmp_path)
    tile_rows = sorted_tile_rows()
    assert tile_rows
    for keys in tile_rows.values():
        assert keys == sorted(keys)


def test_fixed_values_exercise_pin_tombstone_and_layout_contract(tmp_path: Path) -> None:
    """A focused scenario should produce exact values for pinned reads, deletes, and layout metadata."""
    ops = [
        {"op": "put", "key": "gone", "value": "old"},
        {"op": "flush"},
        {"op": "open_pin"},
        {"op": "obliterate", "key": "gone"},
        {"op": "get", "key": "gone"},
        {"op": "flush"},
        {"op": "merge"},
        {"op": "close_pin"},
        {"op": "get", "key": "gone"},
        {"op": "partial_layout_bump", "delta": 4},
        {"op": "restart"},
        {"op": "check_structure"},
    ]
    report = assert_matches_contract(ops, "focused_values", tmp_path)
    assert report["scenario_id"] == "focused_values"
    assert report["observations"][0]["value"] == "old"
    assert report["observations"][1]["value"] == "obliterate"
    assert report["observations"][2]["value"]["layout_generation"] == 4
    assert report["observations"][2]["value"]["tiles"] == [{"id": 2, "sorted_keys": True}]


def test_engine_has_no_baked_probe_canary() -> None:
    """Engine sources must not hardcode verifier-only probe strings."""
    for path in SRC_ROOT.rglob("*.cpp"):
        assert NO_EMBED_TOKEN not in path.read_text(encoding="utf-8", errors="replace")
    for path in SRC_ROOT.rglob("*.hpp"):
        assert NO_EMBED_TOKEN not in path.read_text(encoding="utf-8", errors="replace")
