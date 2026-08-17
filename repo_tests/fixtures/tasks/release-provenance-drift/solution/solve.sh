#!/usr/bin/env bash
set -euo pipefail

cd /app

cat > /app/plugin-core/build.rs <<'RS'
use sha2::{Digest, Sha256};
use std::env;
use std::fs;
use std::path::{Path, PathBuf};

fn update_with_file(hasher: &mut Sha256, label: &str, path: &Path) {
    let bytes = fs::read(path).unwrap_or_else(|err| panic!("read {label}: {err}"));
    hasher.update(label.as_bytes());
    hasher.update([0]);
    hasher.update(&bytes);
    hasher.update([0xff]);
}

fn main() {
    let manifest_dir = PathBuf::from(env::var("CARGO_MANIFEST_DIR").expect("CARGO_MANIFEST_DIR"));
    let out_dir = PathBuf::from(env::var("OUT_DIR").expect("OUT_DIR"));
    let tpl_path = manifest_dir.join("../codegen/templates/ffi.rs.tpl");
    let lib_rs_path = manifest_dir.join(format!("src/lib{}", ".rs"));
    let layout_path = manifest_dir.join(format!("../stage_graph/stage_{}", "layout.json"));

    for path in [&tpl_path, &lib_rs_path, &layout_path] {
        println!("cargo:rerun-if-changed={}", path.display());
    }

    let tpl = fs::read_to_string(&tpl_path).expect("read template");
    let mut hasher = Sha256::new();
    update_with_file(&mut hasher, "ffi.rs.tpl", &tpl_path);
    update_with_file(&mut hasher, concat!("lib", ".rs"), &lib_rs_path);
    update_with_file(&mut hasher, concat!("stage_layout", ".json"), &layout_path);
    let full = format!("{:x}", hasher.finalize());
    let epoch: String = full.chars().take(24).collect();

    let generated = tpl.replace("@@EPOCH@@", &epoch);
    let gen_dir = out_dir.join("generated");
    fs::create_dir_all(&gen_dir).expect("mkdir generated");
    fs::write(gen_dir.join("ffi.rs"), generated).expect("write ffi.rs");
    fs::write(out_dir.join("prov_epoch.txt"), format!("{epoch}\n")).expect("write epoch");
}
RS

python3 - <<'PY'
from pathlib import Path

files = {
    Path('/app/codegen/templates/ffi.rs.tpl'): '''const EPOCH_BYTES: &[u8] = b"@@EPOCH@@\\0";

#[no_mangle]
pub extern "C" fn plugin_epoch() -> *const c_char {
    EPOCH_BYTES.as_ptr() as *const c_char
}

#[no_mangle]
pub extern "C" fn plugin_epoch_len() -> usize {
    EPOCH_BYTES.len().saturating_sub(1)
}
''',
    Path('/app/stage_graph/stage_rust.sh'): '''#!/bin/bash
set -euo pipefail
# shellcheck source=/dev/null
source "$(dirname "$0")/env.sh"
mkdir -p "${STAGE_ROOT}/bin"
td="${CARGO_TARGET_DIR}"
case "${PROFILE}" in
  release) src="${td}/release/libplugin_core.so" ;;
  *) src="${td}/debug/libplugin_core.so" ;;
esac
install -m0755 "$src" "${STAGE_ROOT}/bin/libplugin_core.so"
''',
    Path('/app/stage_graph/stage_cpp.sh'): '''#!/bin/bash
set -euo pipefail
# shellcheck source=/dev/null
source "$(dirname "$0")/env.sh"
mkdir -p "${STAGE_ROOT}/bin"
layout_path="$(dirname "$0")/stage_""layout.json"
python3 - "$layout_path" "$PROFILE" "$CMAKE_BUILD_DIR" "$STAGE_ROOT" <<'INNER'
import json
import shutil
import sys
from pathlib import Path
layout_path = Path(sys.argv[1])
profile = sys.argv[2]
build_dir = Path(sys.argv[3])
stage_bin = Path(sys.argv[4]) / 'bin'
layout = json.loads(layout_path.read_text(encoding='utf-8'))
stage_bin.mkdir(parents=True, exist_ok=True)
for name in layout[profile]['cpp']:
    src = build_dir / name
    if not src.is_file():
        raise SystemExit(f'missing {src}')
    shutil.copy2(src, stage_bin / name)
INNER
''',
    Path('/app/ship_seal/package.sh'): r'''#!/bin/bash
set -euo pipefail
# shellcheck source=/dev/null
source /app/stage_graph/env.sh
mkdir -p "${PKG_ROOT}/bin"
rm -f "${PKG_ROOT}/bin/"*
cp -a "${STAGE_ROOT}/bin/." "${PKG_ROOT}/bin/"
epoch="$(python3 - "$CARGO_TARGET_DIR" "$PROFILE" <<'INNER'
import ctypes
import sys
from pathlib import Path

target_dir = Path(sys.argv[1])
profile = sys.argv[2]
lib_path = target_dir / profile / 'libplugin_core.so'
if not lib_path.is_file():
    raise SystemExit(f'missing plugin library for {profile}: {lib_path}')
lib = ctypes.CDLL(str(lib_path))
epoch_ptr = lib.plugin_epoch
epoch_len = lib.plugin_epoch_len
epoch_ptr.restype = ctypes.c_void_p
epoch_len.restype = ctypes.c_size_t
ptr = epoch_ptr()
size = int(epoch_len())
print(ctypes.string_at(ptr, size).decode('utf-8'))
INNER
)"
python3 - "$PKG_ROOT/seal.json" "$epoch" "${PKG_ROOT}/bin" <<'INNER'
import hashlib
import json
import os
import sys
from pathlib import Path

out_path, epoch, bin_root = sys.argv[1], sys.argv[2].strip(), sys.argv[3]
files = {}
for name in sorted(os.listdir(bin_root)):
    candidate = Path(bin_root) / name
    if candidate.is_file():
        files[name] = hashlib.sha256(candidate.read_bytes()).hexdigest()
payload = {'epoch': epoch, 'files': files}
out = Path(out_path)
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(payload, sort_keys=True) + '\n', encoding='utf-8')
INNER
''',
    Path('/app/loader/load.c'): r'''#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "inval_policy.c"

static char *slurp(const char *path) {
  FILE *f = fopen(path, "rb");
  long sz;
  char *buf;
  if (!f) {
    return NULL;
  }
  fseek(f, 0, SEEK_END);
  sz = ftell(f);
  fseek(f, 0, SEEK_SET);
  buf = malloc((size_t)sz + 1);
  if (!buf) {
    fclose(f);
    return NULL;
  }
  if (sz > 0) {
    fread(buf, 1, (size_t)sz, f);
  }
  buf[sz] = 0;
  fclose(f);
  return buf;
}

static int extract_json_string(const char *json, const char *key, char *out, size_t outsz) {
  const char *cursor = strstr(json, key);
  size_t i = 0;
  if (!cursor) {
    return -1;
  }
  cursor = strchr(cursor, ':');
  if (!cursor) {
    return -1;
  }
  cursor = strchr(cursor, '"');
  if (!cursor) {
    return -1;
  }
  cursor++;
  while (cursor[i] && cursor[i] != '"' && i + 1 < outsz) {
    out[i] = cursor[i];
    i++;
  }
  out[i] = 0;
  return 0;
}

static int extract_file_hash_json(const char *json, const char *name, char *out, size_t outsz) {
  char key[256];
  if (snprintf(key, sizeof key, "\"%s\"", name) >= (int)sizeof key) {
    return -1;
  }
  return extract_json_string(json, key, out, outsz);
}

static const char *basename_c(const char *path) {
  const char *slash = strrchr(path, '/');
  return slash ? slash + 1 : path;
}

static int sha256sum_hex(const char *path, char *out, size_t outsz) {
  char cmd[1024];
  FILE *pipe;
  if (strchr(path, '\'')) {
    return -1;
  }
  if (snprintf(cmd, sizeof cmd, "sha256sum -- '%s'", path) >= (int)sizeof cmd) {
    return -1;
  }
  pipe = popen(cmd, "r");
  if (!pipe) {
    return -1;
  }
  if (!fgets(out, (int)outsz, pipe)) {
    pclose(pipe);
    return -1;
  }
  pclose(pipe);
  for (size_t i = 0; out[i]; ++i) {
    if (out[i] == ' ' || out[i] == '\t' || out[i] == '\n') {
      out[i] = 0;
      break;
    }
  }
  return 0;
}

int main(int argc, char **argv) {
  const char *so = argc > 1 ? argv[1] : "/app/out/pkg/bin/libplugin_core.so";
  const char *seal = argc > 2 ? argv[2] : "/app/out/pkg/seal.json";
  char *js;
  char want_epoch[128];
  char want_hash[128];
  char actual_hash[128];
  void *h;
  const char *(*ep)(void);
  size_t (*eln)(void);

  js = slurp(seal);
  if (!js) {
    fprintf(stderr, "cannot read seal\n");
    return 2;
  }
  if (extract_json_string(js, "\"epoch\"", want_epoch, sizeof want_epoch) != 0) {
    free(js);
    fprintf(stderr, "bad seal\n");
    return 3;
  }
  if (extract_file_hash_json(js, basename_c(so), want_hash, sizeof want_hash) != 0) {
    free(js);
    fprintf(stderr, "missing file hash\n");
    return 8;
  }
  free(js);

  if (!cache_still_valid(so, seal)) {
    fprintf(stderr, "cache invalid\n");
    return 4;
  }
  if (sha256sum_hex(so, actual_hash, sizeof actual_hash) != 0) {
    fprintf(stderr, "hash read failed\n");
    return 9;
  }
  if (strcmp(actual_hash, want_hash) != 0) {
    fprintf(stderr, "hash mismatch\n");
    return 10;
  }

  h = dlopen(so, RTLD_NOW);
  if (!h) {
    fprintf(stderr, "dlopen: %s\n", dlerror());
    return 5;
  }
  ep = (const char *(*)(void))dlsym(h, "plugin_epoch");
  eln = (size_t (*)(void))dlsym(h, "plugin_epoch_len");
  if (!ep || !eln) {
    fprintf(stderr, "missing exports\n");
    return 6;
  }
  {
    const char *got = ep();
    size_t n = eln();
    size_t wn = strlen(want_epoch);
    if (n != wn || strncmp(got, want_epoch, n) != 0) {
      fprintf(stderr, "epoch mismatch\n");
      return 7;
    }
  }
  dlclose(h);
  return 0;
}
''',
    Path('/app/loader/inval_policy.c'): '''#include <sys/stat.h>

int cache_still_valid(const char *plugin_path, const char *seal_path) {
  struct stat plugin_stat;
  struct stat seal_stat;
  if (!plugin_path || !seal_path) {
    return 0;
  }
  if (stat(plugin_path, &plugin_stat) != 0) {
    return 0;
  }
  if (stat(seal_path, &seal_stat) != 0) {
    return 0;
  }
  return 1;
}
''',
}

for path, content in files.items():
    path.write_text(content, encoding='utf-8')

matrix_script = Path('/app/ci/test_partial_fix_matrix.sh')
matrix_script.write_text(
    '''#!/bin/bash
set -euo pipefail
cd /app

backup_dir="$(mktemp -d)"

cleanup() {
  cp "$backup_dir/stage_rust.sh" stage_graph/stage_rust.sh 2>/dev/null || true
  chmod +x stage_graph/stage_rust.sh 2>/dev/null || true
  rm -rf build/cpp stage
  rm -rf "$backup_dir"
}
trap cleanup EXIT

cp stage_graph/stage_rust.sh "$backup_dir/stage_rust.sh"
cp ci/regress/stage_rust.sh.broken stage_graph/stage_rust.sh
chmod +x stage_graph/stage_rust.sh

if bash ci/harness/partial_edit_rust.sh >/tmp/matrix-stage-rust-regress.log 2>&1; then
  echo "expected stage_rust regression to fail partial_edit_rust" >&2
  exit 1
fi

cp "$backup_dir/stage_rust.sh" stage_graph/stage_rust.sh
chmod +x stage_graph/stage_rust.sh
bash ci/harness/build_and_load.sh
''',
    encoding='utf-8',
)
matrix_script.chmod(0o755)

rust_edit_path = Path('/app/ci/harness/partial_edit_rust.sh')
rust_edit_text = rust_edit_path.read_text(encoding='utf-8')
rust_edit_text = rust_edit_text.replace('stamp="$(date +%s)"', 'stamp="$(cat /proc/sys/kernel/random/uuid)"')
rust_edit_text = rust_edit_text.replace('stamp="$(date +%s%N)"', 'stamp="$(cat /proc/sys/kernel/random/uuid)"')
rust_edit_text = rust_edit_text.replace('build_rust\n', 'build_rust\nsleep 1\n', 1)
rust_edit_text = rust_edit_text.replace(
    '(cd /app && cargo build --release -p plugin-core)',
    'rm -rf /app/target/release/build/plugin-core-*\n(cd /app && cargo build --release -p plugin-core)',
)
rust_edit_path.write_text(rust_edit_text, encoding='utf-8')

tpl_edit_path = Path('/app/ci/harness/partial_edit_template.sh')
tpl_edit_text = tpl_edit_path.read_text(encoding='utf-8')
tpl_edit_text = tpl_edit_text.replace('$(date +%s)"', '$(cat /proc/sys/kernel/random/uuid)"')
tpl_edit_text = tpl_edit_text.replace('$(date +%s%N)"', '$(cat /proc/sys/kernel/random/uuid)"')
tpl_edit_text = tpl_edit_text.replace('build_cpp\n', 'build_cpp\nsleep 1\n', 1)
tpl_edit_text = tpl_edit_text.replace(
    '(cd /app && cargo build --release -p plugin-core)',
    'rm -rf /app/target/release/build/plugin-core-*\n(cd /app && cargo build --release -p plugin-core)',
)
tpl_edit_path.write_text(tpl_edit_text, encoding='utf-8')

remove_plugin_path = Path('/app/ci/harness/remove_plugin.sh')
remove_plugin_text = remove_plugin_path.read_text(encoding='utf-8')
remove_plugin_text = remove_plugin_text.replace('build_cpp\n', 'build_cpp\nsleep 1\n', 1)
remove_plugin_text = remove_plugin_text.replace(
    '(cd /app && cargo build --release -p plugin-core)',
    '''stamp="$(cat /proc/sys/kernel/random/uuid)"
python3 - "$stamp" <<'INNER'
import re
import sys
from pathlib import Path

stamp = sys.argv[1]
lib = Path("/app/plugin-core/src/lib.rs")
text = lib.read_text(encoding="utf-8")
updated, count = re.subn(r'surface-anchor-[^"\\\\]+', f'surface-anchor-{stamp}', text, count=1)
if count != 1:
    raise SystemExit("missing BUILD_NOTE marker")
lib.write_text(updated, encoding="utf-8")
INNER
rm -rf /app/target/release/build/plugin-core-*
(cd /app && cargo build --release -p plugin-core)''',
)
remove_plugin_path.write_text(remove_plugin_text, encoding='utf-8')

for path in (
    Path('/app/stage_graph/stage_rust.sh'),
    Path('/app/stage_graph/stage_cpp.sh'),
    Path('/app/ship_seal/package.sh'),
):
    path.chmod(0o755)
PY
