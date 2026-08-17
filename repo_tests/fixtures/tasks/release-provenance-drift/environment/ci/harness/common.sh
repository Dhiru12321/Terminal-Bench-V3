#!/bin/bash
export STAGE_ROOT=/app/stage
export PKG_ROOT=/app/out/pkg
export CARGO_TARGET_DIR=/app/target
export CMAKE_BUILD_DIR=/app/build/cpp
export PROFILE="${PROFILE:-release}"

build_cpp() {
  cmake -S /app/cpp-bridge -B "$CMAKE_BUILD_DIR" -DCMAKE_BUILD_TYPE=Release
  cmake --build "$CMAKE_BUILD_DIR" --parallel
}

build_rust() {
  (cd /app && cargo build -p plugin-core)
  (cd /app && cargo build --release -p plugin-core)
}

stage_all() {
  chmod +x /app/stage_graph/stage_rust.sh /app/stage_graph/stage_cpp.sh /app/ship_seal/package.sh
  /app/stage_graph/stage_rust.sh
  /app/stage_graph/stage_cpp.sh
}

package_all() {
  /app/ship_seal/package.sh
}

build_loader() {
  mkdir -p /app/out
  gcc -Wall -Wextra -o /app/out/loader /app/loader/load.c -ldl
}

run_loader() {
  /app/out/loader "${PKG_ROOT}/bin/libplugin_core.so" "${PKG_ROOT}/seal.json"
}

verify_seal_matches_layout() {
  python3 - <<'PY'
import json
from pathlib import Path
layout = json.loads(Path("/app/stage_graph/stage_layout.json").read_text())
seal = json.loads(Path("/app/out/pkg/seal.json").read_text())
exp = set(layout["release"]["rust"]) | set(layout["release"]["cpp"])
got = set(seal["files"])
if got != exp:
    raise SystemExit(f"seal keys {got} != layout {exp}")
PY
}

clean_artifacts() {
  rm -rf "$STAGE_ROOT" "$PKG_ROOT" /app/out/loader
  mkdir -p "$STAGE_ROOT" "$PKG_ROOT"
}
