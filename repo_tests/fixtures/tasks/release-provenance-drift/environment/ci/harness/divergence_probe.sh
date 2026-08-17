#!/bin/bash
set -euo pipefail
# shellcheck source=/dev/null
source "$(dirname "$0")/common.sh"
clean_artifacts
build_rust
build_cpp
printf '\n// divergence probe %s\n' "$(date +%s)" >>/app/codegen/templates/ffi.rs.tpl
(cd /app && cargo build --release -p plugin-core)
cp "${CMAKE_BUILD_DIR}/libcpp_bridge.so" "${CMAKE_BUILD_DIR}/stale_ghost.so"
stage_all
package_all
build_loader
run_loader
verify_seal_matches_layout
