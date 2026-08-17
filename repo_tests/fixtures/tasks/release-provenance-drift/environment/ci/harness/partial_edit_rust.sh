#!/bin/bash
set -euo pipefail
# shellcheck source=/dev/null
source "$(dirname "$0")/common.sh"
clean_artifacts
build_rust
stamp="$(date +%s)"
python3 - "$stamp" <<'PY'
import re
import sys
from pathlib import Path
stamp = sys.argv[1]
p = Path("/app/plugin-core/src/lib.rs")
text = p.read_text(encoding="utf-8")
updated, count = re.subn(r'surface-anchor-[^"\\]+', f'surface-anchor-{stamp}', text, count=1)
if count != 1:
    raise SystemExit("missing BUILD_NOTE marker")
p.write_text(updated, encoding="utf-8")
PY
(cd /app && cargo build --release -p plugin-core)
build_cpp
stage_all
package_all
build_loader
run_loader
verify_seal_matches_layout
