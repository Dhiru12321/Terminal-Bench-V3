#!/bin/bash
set -euo pipefail
# shellcheck source=/dev/null
source "$(dirname "$0")/env.sh"
mkdir -p "${STAGE_ROOT}/bin"
bd="${CMAKE_BUILD_DIR}"
find "$bd" -maxdepth 1 -name '*.so' -exec install -m0755 {} "${STAGE_ROOT}/bin/" \;
