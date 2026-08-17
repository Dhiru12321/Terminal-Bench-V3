#!/bin/bash
set -euo pipefail
# shellcheck source=/dev/null
source "$(dirname "$0")/common.sh"
clean_artifacts
build_rust
build_cpp
stage_all
package_all
build_loader
run_loader
verify_seal_matches_layout
