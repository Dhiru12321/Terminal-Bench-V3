#!/usr/bin/env python3
"""Aggregate structured failure records for closed-loop authoring review."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

try:
    from scripts import log_failure
except ModuleNotFoundError:  # pragma: no cover
    import log_failure  # type: ignore[no-redef]


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FAILURES_DIR = REPO_ROOT / "failures"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def discover_records(failures_dir: Path) -> list[Path]:
    if not failures_dir.is_dir():
        return []
    return [
        path
        for path in sorted(failures_dir.rglob("*.json"))
        if path.name != "catalog.schema.json" and not path.name.startswith(".")
    ]


def counter_to_dict(counter: Counter[str]) -> dict[str, int]:
    return {key: counter[key] for key in sorted(counter)}


def add_repeated(
    repeated: list[dict[str, Any]],
    *,
    kind: str,
    counter: Counter[str],
    min_repeat: int,
) -> None:
    for key, count in sorted(counter.items(), key=lambda item: (-item[1], item[0])):
        if count >= min_repeat:
            repeated.append({"kind": kind, "key": key, "count": count})


def build_report(paths: list[Path], *, min_repeat: int = 2) -> dict[str, Any]:
    valid_records: list[dict[str, Any]] = []
    invalid_records: list[dict[str, Any]] = []

    stage_counts: Counter[str] = Counter()
    category_counts: Counter[str] = Counter()
    profile_counts: Counter[str] = Counter()
    primary_counts: Counter[str] = Counter()
    check_counts: Counter[str] = Counter()
    response_counts: Counter[str] = Counter()
    stage_primary_counts: Counter[str] = Counter()
    profile_primary_counts: Counter[str] = Counter()
    check_primary_counts: Counter[str] = Counter()

    for path in paths:
        try:
            record = read_json(path)
        except (OSError, json.JSONDecodeError) as exc:
            invalid_records.append(
                {
                    "path": path.as_posix(),
                    "findings": [
                        {
                            "severity": "FAIL",
                            "location": path.as_posix(),
                            "message": f"could not parse record: {exc}",
                        }
                    ],
                }
            )
            continue

        findings = log_failure.validate_record(record)
        if findings:
            invalid_records.append(
                {
                    "path": path.as_posix(),
                    "findings": [finding.to_json() for finding in findings],
                }
            )
            continue

        source = record["source"]
        stage = record["failure_stage"]
        primary = record["primary_failure"]
        profile = source["category_profile"]
        valid_records.append({"path": path.as_posix(), "record": record})

        stage_counts[stage] += 1
        category_counts[source["category"]] += 1
        profile_counts[profile] += 1
        primary_counts[primary] += 1
        response_counts[record["author_response"]] += 1
        stage_primary_counts[f"{stage}:{primary}"] += 1
        profile_primary_counts[f"{profile}:{primary}"] += 1
        for check in record["checks_involved"]:
            check_counts[check] += 1
            check_primary_counts[f"{check}:{primary}"] += 1

    waiver_records = [
        item
        for item in valid_records
        if item["record"]["author_response"] == "waiver_requested"
    ]
    waiver_by_stage: Counter[str] = Counter(item["record"]["failure_stage"] for item in waiver_records)
    waiver_by_check: Counter[str] = Counter()
    for item in waiver_records:
        waiver_by_check.update(item["record"]["checks_involved"])

    repeated: list[dict[str, Any]] = []
    add_repeated(repeated, kind="stage_primary", counter=stage_primary_counts, min_repeat=min_repeat)
    add_repeated(repeated, kind="profile_primary", counter=profile_primary_counts, min_repeat=min_repeat)
    add_repeated(repeated, kind="check_primary", counter=check_primary_counts, min_repeat=min_repeat)

    status = "FAIL" if invalid_records else "PASS"
    return {
        "status": status,
        "summary": {
            "records_scanned": len(paths),
            "valid_records": len(valid_records),
            "invalid_records": len(invalid_records),
            "min_repeat": min_repeat,
        },
        "counts": {
            "failure_stage": counter_to_dict(stage_counts),
            "category": counter_to_dict(category_counts),
            "category_profile": counter_to_dict(profile_counts),
            "primary_failure": counter_to_dict(primary_counts),
            "checks_involved": counter_to_dict(check_counts),
            "author_response": counter_to_dict(response_counts),
        },
        "waiver_pressure": {
            "count": len(waiver_records),
            "by_stage": counter_to_dict(waiver_by_stage),
            "by_check": counter_to_dict(waiver_by_check),
        },
        "repeated_patterns": repeated,
        "invalid_records": invalid_records,
    }


def format_text(payload: dict[str, Any]) -> str:
    lines = [
        f"failure_meta_review.py: {payload['status']}",
        (
            "summary: "
            f"{payload['summary']['valid_records']} valid, "
            f"{payload['summary']['invalid_records']} invalid, "
            f"{payload['summary']['records_scanned']} scanned"
        ),
        "counts by stage:",
    ]
    if payload["counts"]["failure_stage"]:
        lines.extend(
            f"  - {stage}: {count}"
            for stage, count in payload["counts"]["failure_stage"].items()
        )
    else:
        lines.append("  - none")
    lines.append("waiver pressure:")
    lines.append(f"  - count: {payload['waiver_pressure']['count']}")
    if payload["repeated_patterns"]:
        lines.append("repeated patterns:")
        lines.extend(
            f"  - {item['kind']} {item['key']}: {item['count']}"
            for item in payload["repeated_patterns"]
        )
    else:
        lines.append("repeated patterns: none")
    if payload["invalid_records"]:
        lines.append("invalid records:")
        lines.extend(f"  - {item['path']}" for item in payload["invalid_records"])
    return "\n".join(lines) + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aggregate structured failure postmortems.")
    parser.add_argument("--failures-dir", type=Path, default=DEFAULT_FAILURES_DIR)
    parser.add_argument("--min-repeat", type=int, default=2)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    paths = discover_records(args.failures_dir.expanduser())
    payload = build_report(paths, min_repeat=max(1, args.min_repeat))
    print(json.dumps(payload, indent=2, sort_keys=True) if args.json else format_text(payload), end="")
    return 1 if payload["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
