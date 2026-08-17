#!/usr/bin/env python3
"""scripts/metrics_collector.py — per-task authoring metrics.

Spec: docs/exec-plans/instrumentation.md.

This module owns the counter-file format and aggregation for the v2.1
plan §12 metrics block. It exposes:

  - record_exit(tool, outcome) — append a JSONL record for a per-tool
    exit. Used by scripts/run_static_checks.py and scripts/collapse_check.py hooks
    (gated on TB3_METRICS_TASK_DIR) and by scripts/approve_task.py's dirty-flag
    branch.
  - record_marker(name) — append a JSONL marker for a wall-clock
    timestamp. Used by scripts/check-task.sh on first Phase A entry
    (t_first_check_task_invocation_ns) and on Phase C completion
    (t_first_step2b_pass_ns).
  - aggregate(task_dir) -> dict — read the counter file, group records
    by run_id, and emit a demotion-review-friendly summary that
    scripts/approve_task.py renders into the spec validation log.

Counter file: tasks/<task-name>/.step2b-metrics.jsonl, one record per
line, schema {tool, outcome, timestamp_ns, run_id}. POSIX O_APPEND is
atomic for writes < PIPE_BUF; each record is well under 200 bytes, so
concurrent writes interleave but do not corrupt.

Env-var contract:
  TB3_METRICS_TASK_DIR  — set by scripts/check-task.sh; gates whether
                          record_exit() actually writes anything. When
                          unset, hooks no-op (reviewer one-shot path).
  TB3_METRICS_RUN_ID    — set by scripts/check-task.sh at start of run
                          (e.g. RUN_ID="$(uuidgen | head -c 8)"); groups
                          events into a single authoring loop. When
                          unset, records use the literal sentinel
                          "adhoc" so reviewer one-shots stay
                          distinguishable from authoring loops in
                          aggregation.

Binding deferrals (per the exec-plan revision):
  - cni_references_fired = []   (parser deferred to follow-up).
  - draft_commitments_diff = null  (parser deferred to follow-up).

When t_first_step2b_pass_ns is absent (Phase C never green during the
captured window), aggregate() reports the wall-clock duration as the
literal string NO_PASS_SENTINEL ("no Step 2b PASS yet") rather than
crashing or emitting 0.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

METRICS_FILE_NAME = ".step2b-metrics.jsonl"

TASK_DIR_ENV = "TB3_METRICS_TASK_DIR"
RUN_ID_ENV = "TB3_METRICS_RUN_ID"

ADHOC_RUN_ID = "adhoc"
NO_PASS_SENTINEL = "no Step 2b PASS yet"

MARKER_TOOL = "marker"
MARKER_FIRST_INVOCATION = "t_first_check_task_invocation_ns"
MARKER_FIRST_PASS = "t_first_step2b_pass_ns"


def _resolve_task_dir(task_dir: Path | None) -> Path | None:
    if task_dir is not None:
        return task_dir
    env = os.environ.get(TASK_DIR_ENV)
    if not env:
        return None
    return Path(env)


def _resolve_run_id(run_id: str | None) -> str:
    if run_id is not None and run_id != "":
        return run_id
    env = os.environ.get(RUN_ID_ENV)
    if env is None or env == "":
        return ADHOC_RUN_ID
    return env


def _append_record(task_dir: Path, record: dict[str, Any]) -> None:
    """Append a single JSONL record using POSIX O_APPEND for atomicity.

    Each record is well under PIPE_BUF (4096 on Linux); a single
    os.write under O_APPEND is atomic against concurrent appenders, so
    interleaved records remain whole-line parseable.
    """
    target = task_dir / METRICS_FILE_NAME
    payload = (json.dumps(record, sort_keys=True) + "\n").encode("utf-8")
    fd = os.open(
        target,
        os.O_WRONLY | os.O_CREAT | os.O_APPEND,
        0o644,
    )
    try:
        os.write(fd, payload)
    finally:
        os.close(fd)


def record_exit(
    tool: str,
    outcome: str,
    *,
    task_dir: str | Path | None = None,
    timestamp_ns: int | None = None,
    run_id: str | None = None,
) -> None:
    """Append a per-tool exit record. No-op if task_dir is unresolvable.

    A failed write is silently swallowed: the counter is best-effort
    and must never surface a failure to its caller (see exec-plan §
    Sentinel-file race with .step2b-checksum). One dropped increment
    per failure event is below the signal floor for demotion review.

    `task_dir` accepts either `str` or `pathlib.Path` per the standard
    Python "accept str | Path, normalize to Path" contract. A plain
    string crashed `target_dir.is_dir()` before this normalization
    landed (regression-pinned by
    `test_record_exit_accepts_str_task_dir`).
    """
    if task_dir is not None:
        task_dir = Path(task_dir)
    target_dir = _resolve_task_dir(task_dir)
    if target_dir is None:
        return
    if not target_dir.is_dir():
        return
    if timestamp_ns is None:
        timestamp_ns = time.time_ns()
    record = {
        "tool": tool,
        "outcome": outcome,
        "timestamp_ns": int(timestamp_ns),
        "run_id": _resolve_run_id(run_id),
    }
    try:
        _append_record(target_dir, record)
    except OSError:
        return


def record_marker(
    name: str,
    *,
    task_dir: str | Path | None = None,
    timestamp_ns: int | None = None,
    run_id: str | None = None,
) -> None:
    """Append a wall-clock marker. The schema is the same JSONL record
    as record_exit; markers ride as tool=MARKER_TOOL, outcome=name.

    `task_dir` accepts either `str` or `pathlib.Path`. Normalization
    happens via `record_exit`, which this function delegates to.
    Regression-pinned by `test_record_marker_accepts_str_task_dir`.
    """
    if task_dir is not None:
        task_dir = Path(task_dir)
    record_exit(
        MARKER_TOOL,
        name,
        task_dir=task_dir,
        timestamp_ns=timestamp_ns,
        run_id=run_id,
    )


def _read_jsonl(target: Path) -> list[dict[str, Any]]:
    """Read a JSONL file, skipping malformed lines.

    Concurrent writers can theoretically produce a partial line if a
    write is split across PIPE_BUF; treat malformed lines as dropped
    rather than aborting aggregation. The exec-plan accepts dropped
    increments below the signal floor.
    """
    if not target.exists():
        return []
    records: list[dict[str, Any]] = []
    for raw in target.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            records.append(parsed)
    return records


def _earliest_marker(records: list[dict[str, Any]], name: str) -> int | None:
    earliest: int | None = None
    for record in records:
        if record.get("tool") != MARKER_TOOL:
            continue
        if record.get("outcome") != name:
            continue
        ts = record.get("timestamp_ns")
        if not isinstance(ts, int):
            continue
        if earliest is None or ts < earliest:
            earliest = ts
    return earliest


def aggregate(task_dir: str | Path) -> dict[str, Any]:
    """Aggregate counters and markers for a task dir.

    Returns a dict suitable for rendering into the spec validation log
    metrics block. Aggregation groups events by run_id but surfaces
    totals across all runs — demotion review wants both the overall
    counters and the list of run_ids so a reviewer can drill in if
    something looks anomalous.

    `task_dir` accepts either `str` or `pathlib.Path` per the standard
    Python "accept str | Path, normalize to Path" contract. The
    `task_dir / METRICS_FILE_NAME` arithmetic below requires Path, so
    we normalize at the top of the body. Regression-pinned by
    `test_aggregate_accepts_str_task_dir`.
    """
    task_dir = Path(task_dir)
    target = task_dir / METRICS_FILE_NAME
    records = _read_jsonl(target)
    records.sort(key=lambda r: r.get("timestamp_ns", 0))

    by_run: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        run_id = record.get("run_id", ADHOC_RUN_ID)
        if not isinstance(run_id, str):
            run_id = ADHOC_RUN_ID
        by_run.setdefault(run_id, []).append(record)

    static_fail = 0
    static_warn = 0
    collapse_fail = 0
    dirty_flag = 0
    for record in records:
        tool = record.get("tool")
        outcome = record.get("outcome")
        if tool == "run_static_checks":
            if outcome == "FAIL":
                static_fail += 1
            elif outcome == "WARN":
                static_warn += 1
        elif tool == "collapse_check":
            if outcome == "FAIL":
                collapse_fail += 1
        elif tool == "approve_task":
            if outcome == "dirty_flag":
                dirty_flag += 1

    first_invocation_ns = _earliest_marker(records, MARKER_FIRST_INVOCATION)
    first_pass_ns = _earliest_marker(records, MARKER_FIRST_PASS)

    if first_pass_ns is None or first_invocation_ns is None:
        wall_clock: int | str = NO_PASS_SENTINEL
    else:
        wall_clock = first_pass_ns - first_invocation_ns

    return {
        "task_dir": str(task_dir),
        "run_static_checks_fail": static_fail,
        "run_static_checks_warn": static_warn,
        "collapse_check_fail": collapse_fail,
        "dirty_flag": dirty_flag,
        "t_first_check_task_invocation_ns": first_invocation_ns,
        "t_first_step2b_pass_ns": first_pass_ns,
        "wall_clock_first_preflight_to_first_pass_ns": wall_clock,
        "cni_references_fired": [],
        "draft_commitments_diff": None,
        "runs": sorted(by_run.keys()),
    }


def _cli_record_exit(args: argparse.Namespace) -> int:
    record_exit(args.tool, args.outcome)
    return 0


def _cli_marker(args: argparse.Namespace) -> int:
    timestamp_ns = args.timestamp_ns if args.timestamp_ns is not None else None
    record_marker(args.name, timestamp_ns=timestamp_ns)
    return 0


def _cli_aggregate(args: argparse.Namespace) -> int:
    payload = aggregate(args.task_dir)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Per-task authoring metrics collector. "
            "See docs/exec-plans/instrumentation.md."
        )
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_exit = sub.add_parser(
        "record-exit",
        help="Append a tool-exit record (TB3_METRICS_TASK_DIR-gated).",
    )
    p_exit.add_argument("tool")
    p_exit.add_argument("outcome")
    p_exit.set_defaults(func=_cli_record_exit)

    p_marker = sub.add_parser(
        "marker",
        help="Append a wall-clock marker (TB3_METRICS_TASK_DIR-gated).",
    )
    p_marker.add_argument("name")
    p_marker.add_argument(
        "--timestamp-ns",
        dest="timestamp_ns",
        type=int,
        default=None,
        help="Override timestamp (default: time.time_ns()).",
    )
    p_marker.set_defaults(func=_cli_marker)

    p_aggregate = sub.add_parser(
        "aggregate",
        help="Aggregate counters/markers for a task dir; emit JSON.",
    )
    p_aggregate.add_argument("task_dir", type=Path)
    p_aggregate.set_defaults(func=_cli_aggregate)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
