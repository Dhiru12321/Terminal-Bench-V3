#!/bin/bash

# Compatibility wrapper for the old instruction-path checker.
# The authoritative Edition 2 behavior now comes from
# scripts/run_static_checks.py --only absolute_paths.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

resolve_task_dir() {
    local candidate="$1"

    if [ -d "$candidate" ] && [ -f "$candidate/task.toml" ]; then
        printf '%s\n' "$candidate"
        return 0
    fi

    if [ ! -e "$candidate" ]; then
        return 1
    fi

    local search_dir
    if [ -d "$candidate" ]; then
        search_dir="$candidate"
    else
        search_dir="$(dirname "$candidate")"
    fi

    while [ "$search_dir" != "." ] && [ "$search_dir" != "/" ]; do
        if [ -f "$search_dir/task.toml" ]; then
            printf '%s\n' "$search_dir"
            return 0
        fi
        search_dir="$(dirname "$search_dir")"
    done

    return 1
}

TASK_DIRS=()
if [ "$#" -eq 0 ]; then
    while IFS= read -r task_dir; do
        TASK_DIRS+=("$task_dir")
    done < <(find tasks -mindepth 1 -maxdepth 1 -type d | sort)
else
    declare -A seen=()
    for arg in "$@"; do
        if task_dir="$(resolve_task_dir "$arg")"; then
            if [ -z "${seen[$task_dir]:-}" ]; then
                seen["$task_dir"]=1
                TASK_DIRS+=("$task_dir")
            fi
        fi
    done
fi

if [ "${#TASK_DIRS[@]}" -eq 0 ]; then
    echo "No task directories found to check"
    exit 0
fi

echo "check-task-absolute-path.sh is deprecated."
echo "Using scripts/run_static_checks.py --only absolute_paths instead of a separate shell regex checker."

FAILED=0
for task_dir in "${TASK_DIRS[@]}"; do
    if ! python3 scripts/run_static_checks.py --task-dir "$task_dir" --version terminus_3 --only absolute_paths; then
        FAILED=1
    fi
done

exit "$FAILED"
