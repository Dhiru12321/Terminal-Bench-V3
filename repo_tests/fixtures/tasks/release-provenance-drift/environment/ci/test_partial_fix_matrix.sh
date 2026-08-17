#!/bin/bash
set -euo pipefail
cd /app

backup_dir="$(mktemp -d)"

backup_one() {
  cp "$1" "$backup_dir/$2"
}

restore() {
  cp "$backup_dir/build.rs" plugin-core/build.rs
  cp "$backup_dir/load.c" loader/load.c
  cp "$backup_dir/stage_rust.sh" stage_graph/stage_rust.sh
  cp "$backup_dir/stage_cpp.sh" stage_graph/stage_cpp.sh
  cp "$backup_dir/package.sh" ship_seal/package.sh
  cp "$backup_dir/lib.rs" plugin-core/src/lib.rs
  cp "$backup_dir/ffi.rs.tpl" codegen/templates/ffi.rs.tpl
  cp "$backup_dir/legacy.cpp" cpp-bridge/src/legacy.cpp
  cp "$backup_dir/CMakeLists.txt" cpp-bridge/CMakeLists.txt
  cp "$backup_dir/stage_layout.json" stage_graph/stage_layout.json
  rm -rf build/cpp stage out/loader out/pkg
  chmod +x stage_graph/stage_rust.sh stage_graph/stage_cpp.sh ship_seal/package.sh
}

cleanup() {
  restore || true
  rm -rf "$backup_dir"
}
trap cleanup EXIT

backup_one plugin-core/build.rs build.rs
backup_one loader/load.c load.c
backup_one stage_graph/stage_rust.sh stage_rust.sh
backup_one stage_graph/stage_cpp.sh stage_cpp.sh
backup_one ship_seal/package.sh package.sh
backup_one plugin-core/src/lib.rs lib.rs
backup_one codegen/templates/ffi.rs.tpl ffi.rs.tpl
backup_one cpp-bridge/src/legacy.cpp legacy.cpp
backup_one cpp-bridge/CMakeLists.txt CMakeLists.txt
backup_one stage_graph/stage_layout.json stage_layout.json

check_epoch_moves() {
  bash ci/harness/build_and_load.sh >/tmp/matrix-build.log 2>&1
  before="$(python3 - <<'PY'
import json
from pathlib import Path
print(json.loads(Path('out/pkg/seal.json').read_text(encoding='utf-8'))['epoch'])
PY
)"
  bash ci/harness/partial_edit_rust.sh >/tmp/matrix-rust.log 2>&1
  after="$(python3 - <<'PY'
import json
from pathlib import Path
print(json.loads(Path('out/pkg/seal.json').read_text(encoding='utf-8'))['epoch'])
PY
)"
  [ "$before" != "$after" ]
}

check_loader_rejects_swapped_debug_binary() {
  bash ci/harness/build_and_load.sh >/tmp/matrix-loader-setup.log 2>&1
  cp target/debug/libplugin_core.so out/pkg/bin/libplugin_core.so
  if out/loader out/pkg/bin/libplugin_core.so out/pkg/seal.json >/tmp/matrix-loader.log 2>&1; then
    return 1
  fi
  grep -q 'hash mismatch' /tmp/matrix-loader.log
}

restore
cp ci/regress/build.rs.broken plugin-core/build.rs
if check_epoch_moves; then
  echo "expected build.rs regression to keep epoch unchanged" >&2
  exit 1
fi

restore
cp ci/regress/stage_rust.sh.broken stage_graph/stage_rust.sh
chmod +x stage_graph/stage_rust.sh
if bash ci/harness/partial_edit_rust.sh >/tmp/matrix-stage-rust.log 2>&1; then
  echo "expected stage_rust regression to fail" >&2
  exit 1
fi

restore
cp ci/regress/package.sh.broken ship_seal/package.sh
chmod +x ship_seal/package.sh
if bash ci/harness/partial_edit_rust.sh >/tmp/matrix-package.log 2>&1; then
  echo "expected package regression to fail" >&2
  exit 1
fi

restore
cp ci/regress/stage_cpp.sh.broken stage_graph/stage_cpp.sh
chmod +x stage_graph/stage_cpp.sh
if bash ci/harness/remove_plugin.sh >/tmp/matrix-stage-cpp.log 2>&1; then
  echo "expected stage_cpp regression to fail" >&2
  exit 1
fi

restore
cp ci/regress/load.c.broken loader/load.c
if check_loader_rejects_swapped_debug_binary; then
  echo "expected loader regression to accept the swapped debug binary" >&2
  exit 1
fi

restore
bash ci/harness/build_and_load.sh
