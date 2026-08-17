#!/bin/bash
set -euo pipefail
# shellcheck source=/dev/null
source "/app/stage_graph/env.sh"
mkdir -p "${PKG_ROOT}/bin"
rm -f "${PKG_ROOT}/bin/"*
cp -a "${STAGE_ROOT}/bin/." "${PKG_ROOT}/bin/"
td="${CARGO_TARGET_DIR}"
epoch_file=$(find "${td}/debug/build" -name prov_epoch.txt 2>/dev/null | sort | head -1)
epoch=$(cat "$epoch_file")
python3 - <<'PY' "$PKG_ROOT/seal.json" "$epoch" "${PKG_ROOT}/bin"
import hashlib, json, os, sys
out, epoch, st = sys.argv[1], sys.argv[2].strip(), sys.argv[3]
files = {}
for name in sorted(os.listdir(st)):
    p = os.path.join(st, name)
    if not os.path.isfile(p):
        continue
    h = hashlib.sha256(open(p, "rb").read()).hexdigest()
    files[name] = h
payload = {"epoch": epoch, "files": files}
os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, "w", encoding="utf-8") as f:
    json.dump(payload, f, sort_keys=True)
    f.write("\n")
PY
