#!/bin/bash
set -euo pipefail
# shellcheck source=/dev/null
source "$(dirname "$0")/env.sh"
mkdir -p "${STAGE_ROOT}/bin"
td="${CARGO_TARGET_DIR}"
src="${td}/debug/libplugin_core.so"
install -m0755 "$src" "${STAGE_ROOT}/bin/libplugin_core.so"
