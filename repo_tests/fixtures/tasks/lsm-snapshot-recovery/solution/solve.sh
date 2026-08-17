#!/usr/bin/env bash
set -euo pipefail
# CI reference-path scrape: /app/task.toml

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd /app
patch -p1 <"${ROOT_DIR}/phase_a.patch"
patch -p1 <"${ROOT_DIR}/phase_b.patch"

rm -rf /app/build
cmake -S /app -B /app/build -DCMAKE_BUILD_TYPE=Release
cmake --build /app/build --parallel
