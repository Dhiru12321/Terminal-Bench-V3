#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

resolve_task_dir() {
    local input="$1"
    local search=""

    if [ -d "$input" ] || [ -f "$input" ]; then
        search="$input"
    elif [ -d "tasks/$input" ]; then
        search="tasks/$input"
    else
        return 1
    fi

    if [ -f "$search" ]; then
        search="$(dirname "$search")"
    fi

    while [ "$search" != "/" ] && [ "$search" != "." ]; do
        if [ -f "$search/task.toml" ]; then
            printf '%s\n' "$search"
            return 0
        fi
        search="$(dirname "$search")"
    done

    return 1
}

collect_task_dirs() {
    if [ $# -eq 0 ]; then
        find tasks -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort
        return
    fi

    local arg
    for arg in "$@"; do
        if ! resolve_task_dir "$arg"; then
            echo "Path $arg does not resolve to a task directory, skipping" >&2
        fi
    done | sort -u
}

mapfile -t TASK_DIRS < <(collect_task_dirs "$@")

if [ ${#TASK_DIRS[@]} -eq 0 ]; then
    echo "No task directories to check"
    exit 0
fi

FAILED=0
for task_dir in "${TASK_DIRS[@]}"; do
    if ! python3 "$ROOT_DIR/scripts/run_static_checks.py" \
        --task-dir "$task_dir" \
        --version terminus_3 \
        --only task_toml \
        --only task_structure \
        --only task_name; then
        FAILED=1
    fi
done

if [ $FAILED -ne 0 ]; then
    echo "Task manifest/structure validation failed"
    exit 1
fi

echo "All task manifest/structure validations passed"
