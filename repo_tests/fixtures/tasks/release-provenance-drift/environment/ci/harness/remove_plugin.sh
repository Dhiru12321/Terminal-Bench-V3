#!/bin/bash
set -euo pipefail
# shellcheck source=/dev/null
source "$(dirname "$0")/common.sh"
clean_artifacts
build_rust
build_cpp

rm -f /app/cpp-bridge/src/legacy.cpp
python3 - <<'PY'
from pathlib import Path
p = Path("/app/cpp-bridge/CMakeLists.txt")
lines = [ln for ln in p.read_text(encoding="utf-8").splitlines() if "legacy" not in ln.lower()]
p.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY
python3 - <<'PY'
import json
from pathlib import Path
p = Path("/app/stage_graph/stage_layout.json")
data = json.loads(p.read_text(encoding="utf-8"))
for profile in data.values():
    profile["cpp"] = [name for name in profile["cpp"] if "legacy" not in name]
p.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
PY

cmake -S /app/cpp-bridge -B "$CMAKE_BUILD_DIR" -DCMAKE_BUILD_TYPE=Release
cmake --build "$CMAKE_BUILD_DIR" --parallel
cp "${CMAKE_BUILD_DIR}/libcpp_bridge.so" "${CMAKE_BUILD_DIR}/stale_ghost.so"
(cd /app && cargo build --release -p plugin-core)

stage_all
package_all
build_loader
run_loader
verify_seal_matches_layout
