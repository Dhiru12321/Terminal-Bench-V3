#!/usr/bin/env python3
"""
Validation loop state machine for Terminal-Bench 3 task ideas.

Cursor calls this script after each validation attempt. The script tracks
state, validates structured Step 2a evidence, decides the next action, and
outputs machine-readable directives that Cursor reads to decide what to do next.

Usage (called by Cursor during Step 2a):
    python3 scripts/validate_loop.py init <task-name>
    python3 scripts/validate_loop.py record <task-name> --strict --evidence /tmp/<task-name>-validation-evidence.json
    python3 scripts/validate_loop.py select <task-name> --winner N|specs/<task-name>.md
    python3 scripts/validate_loop.py finalize <task-name>
    python3 scripts/validate_loop.py status <task-name>
    python3 scripts/validate_loop.py reset <task-name>

Output format (last lines, machine-readable):
    ACTION: CONTINUE | SELECT | GO | STOP
    SAVE_TO: specs/<authoring-path>
    REASON: <why>
    CANDIDATES: <comma-separated attempt=authoring entries>  (only for SELECT)

Normal Step 2a output is exactly one human artifact:
    specs/<task-name>.md

Internal run artifacts are stored under:
    specs/.runs/<task-name>/
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

try:
    from jsonschema import exceptions as jsonschema_exceptions
    from jsonschema import validators as jsonschema_validators
except ModuleNotFoundError:
    jsonschema_exceptions = None
    jsonschema_validators = None

try:
    from . import lint_spec
except ImportError:  # pragma: no cover - direct script execution path
    import lint_spec

SPECS_DIR = Path("specs")
SCHEMA_PATH = SPECS_DIR / "validation_schema.json"
MAX_ATTEMPTS = 5
PLATEAU_THRESHOLD = 2
MIN_DISCOVERY_BUDGET_ITEMS = 3
VALID_VERDICTS = {"PASS", "WARN", "FAIL"}
VALID_SPECIFICITY_LEVELS = {
    "spec-complete",
    "cause-revealing",
    "symptoms-only",
}

HARDNESS_AXES = {
    "discover": "Discover",
    "synthesize": "Synthesize",
    "diagnose": "Diagnose",
    "navigate_coupling": "Navigate coupling",
    "reason_beyond_training": "Reason beyond training",
}

RUBRIC_AXES = {
    "verifiable": "Verifiable",
    "well_specified": "Well-specified",
    "solvable": "Solvable",
    "difficult": "Difficult",
    "interesting": "Interesting",
    "outcome_verified": "Outcome-verified",
}

ANTI_TRIVIALIZATION_CHECKS = {
    "disclosure_collapse": "Disclosure-collapse",
    "hidden_instance": "Hidden-instance",
    "single_artifact_repair": "Single-artifact repair",
    "generalization": "Generalization",
    "prompt_honesty": "Prompt-honesty",
    "cheating_vs_difficulty": "Cheating-vs-difficulty",
    "mechanical_fix_filter": "Mechanical-fix filter",
    "localized_fix": "Localized-fix",
    "oracle_locality": "Oracle-locality",
    "small_declarative_cluster": "Small declarative-cluster",
    "grep_collapse": "Grep-collapse",
    "pre_factored_helper": "Pre-factored-helper",
    "recipe_discount": "Recipe-discount",
    "security_aura_discount": "Security-aura discount",
    "orthogonal_checklist": "Orthogonal-checklist",
    "harness_discount": "Harness-discount",
    "one_pass_solvability": "One-pass solvability",
    "hard_only_gate": "Hard-only gate",
    "discovery_budget_test": "Discovery budget test",
    "instruction_specificity_test": "Instruction specificity test",
    "topology_distribution_test": "Topology distribution test",
}

SHAPE_LEVEL_EVIDENCE_FIELDS = {
    "platform_files": "platform/task files that exist in every task scaffold",
    "task_files": "task-specific environment and step files",
    "fix_frontier": "shape-level fix-frontier commitments",
    "contract_surface": "output/assertion contract surface limits",
    "category_profile": "category-profile validation from Step 1",
    "satisfiability_risk": "pre-construction satisfiability risks",
    "actionability_plan": "instruction/actionability placement plan",
    "waiver_plan": "expected waiver pressure",
    "reference_pattern": "reference-task pattern or no-reference justification",
    "realism_source": "real-bug or synthetic-exception source record",
}

REQUIRED_PLATFORM_FILES = {
    "task.toml",
    "instruction.md",
    "output_contract.toml",
    "tests/test.sh",
    "tests/test_outputs.py",
    "solution/solve.sh",
    "environment/Dockerfile",
    "construction_manifest.json",
}


def run_dir(task_name: str) -> Path:
    return SPECS_DIR / ".runs" / task_name


def state_path(task_name: str) -> Path:
    return run_dir(task_name) / "state.json"


def legacy_state_path(task_name: str) -> Path:
    return SPECS_DIR / f".{task_name}-state.json"


def attempt_evidence_path(task_name: str, attempt: int) -> Path:
    return run_dir(task_name) / f"attempt-{attempt}-evidence.json"


def validation_log_path(task_name: str) -> Path:
    return run_dir(task_name) / "validation-log.md"


def authoring_spec_path(task_name: str, candidate_n: int | None = None) -> Path:
    if candidate_n is None:
        return SPECS_DIR / f"{task_name}.md"
    return SPECS_DIR / f"{task_name}-candidate-{candidate_n}.md"


def reviewer_spec_path(task_name: str, candidate_n: int | None = None) -> Path:
    """Legacy reviewer sidecar path.

    Normal Step 2a no longer creates or prints this path. It is retained
    only for `--emit-legacy-reviewer` diagnostics during migration.
    """
    if candidate_n is None:
        return SPECS_DIR / f"{task_name}-reviewer.md"
    return SPECS_DIR / f"{task_name}-candidate-{candidate_n}-reviewer.md"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_state(task_name: str) -> dict[str, Any]:
    sp = state_path(task_name)
    if not sp.exists() and legacy_state_path(task_name).exists():
        sp = legacy_state_path(task_name)
    if not sp.exists():
        print(f"ERROR: No active loop for '{task_name}'. Run init first.")
        sys.exit(1)
    return load_json(sp)


def save_state(task_name: str, state: dict[str, Any]) -> None:
    state_path(task_name).parent.mkdir(parents=True, exist_ok=True)
    state_path(task_name).write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _validate_named_verdict_entries(
    evidence: dict[str, Any],
    field_name: str,
    expected: dict[str, str],
    errors: list[str],
    counts: dict[str, int],
) -> list[dict[str, str]]:
    entries = evidence.get(field_name)
    if not isinstance(entries, list):
        errors.append(f"{field_name} must be a list.")
        return []

    normalized: dict[str, dict[str, str]] = {}
    for index, entry in enumerate(entries, start=1):
        prefix = f"{field_name}[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{prefix} must be an object.")
            continue

        entry_id = entry.get("id")
        if not _is_non_empty_string(entry_id):
            errors.append(f"{prefix}.id must be a non-empty string.")
            continue
        entry_id = entry_id.strip()

        if entry_id in normalized:
            errors.append(f"{field_name} has duplicate id {entry_id!r}.")
            continue

        name = entry.get("name")
        verdict = entry.get("verdict")
        reasoning = entry.get("reasoning")

        if not _is_non_empty_string(name):
            errors.append(f"{prefix}.name must be a non-empty string.")
            continue
        if verdict not in VALID_VERDICTS:
            errors.append(f"{prefix}.verdict must be one of {sorted(VALID_VERDICTS)}.")
            continue
        if not _is_non_empty_string(reasoning):
            errors.append(f"{prefix}.reasoning must be a non-empty string.")
            continue

        normalized[entry_id] = {
            "id": entry_id,
            "name": name.strip(),
            "verdict": verdict,
            "reasoning": reasoning.strip(),
        }

    missing = [entry_id for entry_id in expected if entry_id not in normalized]
    extra = [entry_id for entry_id in normalized if entry_id not in expected]
    if missing:
        errors.append(f"{field_name} is missing required ids: {', '.join(missing)}.")
    if extra:
        errors.append(f"{field_name} contains unexpected ids: {', '.join(extra)}.")

    ordered: list[dict[str, str]] = []
    for entry_id, expected_name in expected.items():
        entry = normalized.get(entry_id)
        if entry is None:
            continue
        if entry["name"] != expected_name:
            errors.append(
                f"{field_name} entry {entry_id!r} must use name {expected_name!r}, found {entry['name']!r}."
            )
            continue
        counts[entry["verdict"]] += 1
        ordered.append(entry)

    return ordered


def _validate_verdict_block(
    evidence: dict[str, Any],
    field_name: str,
    errors: list[str],
    counts: dict[str, int],
) -> dict[str, str]:
    value = evidence.get(field_name)
    if not isinstance(value, dict):
        errors.append(f"{field_name} must be an object.")
        return {}

    verdict = value.get("verdict")
    reasoning = value.get("reasoning")
    if verdict not in VALID_VERDICTS:
        errors.append(f"{field_name}.verdict must be one of {sorted(VALID_VERDICTS)}.")
        return {}
    if not _is_non_empty_string(reasoning):
        errors.append(f"{field_name}.reasoning must be a non-empty string.")
        return {}

    counts[verdict] += 1
    return {"verdict": verdict, "reasoning": reasoning.strip()}


def _validate_instruction_specificity(
    evidence: dict[str, Any],
    errors: list[str],
    hard_fail_reasons: list[str],
) -> dict[str, str]:
    value = evidence.get("instruction_specificity")
    if not isinstance(value, dict):
        errors.append("instruction_specificity must be an object.")
        return {}

    level = value.get("level")
    reasoning = value.get("reasoning")
    if level not in VALID_SPECIFICITY_LEVELS:
        errors.append(
            "instruction_specificity.level must be one of "
            f"{sorted(VALID_SPECIFICITY_LEVELS)}."
        )
        return {}
    if not _is_non_empty_string(reasoning):
        errors.append("instruction_specificity.reasoning must be a non-empty string.")
        return {}

    normalized = {"level": level, "reasoning": reasoning.strip()}
    if level != "symptoms-only":
        hard_fail_reasons.append(
            "instruction_specificity.level must be 'symptoms-only' for the default hard-only Step 2a workflow."
        )
    return normalized


def _validate_analysis_block(
    evidence: dict[str, Any],
    field_name: str,
    errors: list[str],
) -> dict[str, str]:
    value = evidence.get(field_name)
    if not isinstance(value, dict):
        errors.append(f"{field_name} must be an object.")
        return {}

    summary = value.get("summary")
    reasoning = value.get("reasoning")
    if not _is_non_empty_string(summary):
        errors.append(f"{field_name}.summary must be a non-empty string.")
        return {}
    if not _is_non_empty_string(reasoning):
        errors.append(f"{field_name}.reasoning must be a non-empty string.")
        return {}

    return {"summary": summary.strip(), "reasoning": reasoning.strip()}


def _validate_discovery_budget(
    evidence: dict[str, Any],
    errors: list[str],
    hard_fail_reasons: list[str],
) -> list[dict[str, str]]:
    value = evidence.get("discovery_budget")
    if not isinstance(value, list):
        errors.append("discovery_budget must be a list.")
        return []

    normalized: list[dict[str, str]] = []
    for index, item in enumerate(value, start=1):
        prefix = f"discovery_budget[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object.")
            continue

        discovery = item.get("discovery")
        planned_location = item.get("planned_location")
        why_instruction_must_not_reveal = item.get("why_instruction_must_not_reveal")
        if not _is_non_empty_string(discovery):
            errors.append(f"{prefix}.discovery must be a non-empty string.")
            continue
        if not _is_non_empty_string(planned_location):
            errors.append(f"{prefix}.planned_location must be a non-empty string.")
            continue
        if not _is_non_empty_string(why_instruction_must_not_reveal):
            errors.append(
                f"{prefix}.why_instruction_must_not_reveal must be a non-empty string."
            )
            continue

        normalized.append(
            {
                "discovery": discovery.strip(),
                "planned_location": planned_location.strip(),
                "why_instruction_must_not_reveal": why_instruction_must_not_reveal.strip(),
            }
        )

    if len(normalized) < MIN_DISCOVERY_BUDGET_ITEMS:
        hard_fail_reasons.append(
            "discovery_budget must contain at least 3 non-trivial solver discoveries "
            "that the finished task will force from the codebase."
        )

    return normalized


def _validate_collapse_audit(
    evidence: dict[str, Any],
    errors: list[str],
    counts: dict[str, int],
) -> dict[str, Any]:
    value = evidence.get("collapse_audit")
    if not isinstance(value, dict):
        errors.append("collapse_audit must be an object.")
        return {}

    verdict = value.get("verdict")
    reasoning = value.get("reasoning")
    residual_hardness = value.get("residual_hardness")
    red_flags = value.get("red_flags", [])

    if verdict not in VALID_VERDICTS:
        errors.append(f"collapse_audit.verdict must be one of {sorted(VALID_VERDICTS)}.")
        return {}
    if not _is_non_empty_string(reasoning):
        errors.append("collapse_audit.reasoning must be a non-empty string.")
        return {}
    if not _is_non_empty_string(residual_hardness):
        errors.append("collapse_audit.residual_hardness must be a non-empty string.")
        return {}
    if not isinstance(red_flags, list) or any(not _is_non_empty_string(flag) for flag in red_flags):
        errors.append("collapse_audit.red_flags must be a list of non-empty strings when provided.")
        return {}

    counts[verdict] += 1
    return {
        "verdict": verdict,
        "reasoning": reasoning.strip(),
        "residual_hardness": residual_hardness.strip(),
        "red_flags": [flag.strip() for flag in red_flags],
    }


def _validate_naming_pass(
    evidence: dict[str, Any],
    errors: list[str],
    hard_fail_reasons: list[str],
    counts: dict[str, int],
) -> dict[str, Any]:
    """Validate the naming-pass record and recompute concentration math.

    Schema-level structural checks already ran in `_validate_schema`; this
    function adds the cross-field invariants the schema cannot express:
    (a) `instruction_nouns_extracted` and
    `construction_manifest.code_forbidden_tokens` must agree as sets
    (case-insensitive); (b) no entry in `test_names_audited` may contain
    any token from the noun list as a case-insensitive substring; (c) the
    agent-supplied `concentration_math` must match the validator's own
    arithmetic over `flipping_point_contract.locations`, and no
    per-location ratio may exceed `concentration_cap`. An empty
    `renames_during_drafting` list is acceptable but emits a WARN — the
    intent is to make the agent state explicitly that first-pass naming
    was already clean rather than skipping the audit silently.
    """
    naming_pass = evidence.get("naming_pass")
    if not isinstance(naming_pass, dict):
        errors.append("naming_pass must be an object.")
        return {}

    nouns_raw = naming_pass.get("instruction_nouns_extracted", [])
    renames_raw = naming_pass.get("renames_during_drafting", [])
    test_names_raw = naming_pass.get("test_names_audited", [])
    concentration_raw = naming_pass.get("concentration_math", {})

    nouns = [str(noun).strip() for noun in nouns_raw if isinstance(noun, str) and str(noun).strip()]
    test_names = [
        str(name).strip()
        for name in test_names_raw
        if isinstance(name, str) and str(name).strip()
    ]

    construction_manifest = evidence.get("construction_manifest") or {}
    forbidden_tokens_raw = construction_manifest.get("code_forbidden_tokens", []) or []
    forbidden_tokens = [
        str(token).strip()
        for token in forbidden_tokens_raw
        if isinstance(token, str) and str(token).strip()
    ]

    nouns_set = {noun.lower() for noun in nouns}
    tokens_set = {token.lower() for token in forbidden_tokens}
    if nouns_set != tokens_set:
        extra_in_nouns = sorted(nouns_set - tokens_set)
        extra_in_tokens = sorted(tokens_set - nouns_set)
        errors.append(
            "naming_pass.instruction_nouns_extracted disagrees with "
            "construction_manifest.code_forbidden_tokens "
            f"(extra in nouns: {extra_in_nouns}; extra in tokens: {extra_in_tokens})."
        )

    for test_name in test_names:
        lower_name = test_name.lower()
        for noun in nouns:
            if not noun:
                continue
            if noun.lower() in lower_name:
                errors.append(
                    f"test name {test_name!r} contains forbidden instruction noun "
                    f"{noun!r}."
                )

    flipping_contract = construction_manifest.get("flipping_point_contract") or {}
    locations = flipping_contract.get("locations") or []
    concentration_cap = flipping_contract.get("concentration_cap")

    union_tests: set[str] = set()
    per_location_computed: list[dict[str, Any]] = []
    for location in locations:
        if not isinstance(location, dict):
            continue
        loc_id = location.get("id")
        controls_tests = location.get("controls_tests") or []
        if not isinstance(controls_tests, list):
            controls_tests = []
        loc_tests = [t for t in controls_tests if isinstance(t, str) and t.strip()]
        union_tests.update(loc_tests)
        per_location_computed.append(
            {
                "location_id": str(loc_id).strip() if isinstance(loc_id, str) else "",
                "test_count": len(loc_tests),
                "_controls_tests": loc_tests,
            }
        )

    total_tests_computed = len(union_tests)
    for entry in per_location_computed:
        if total_tests_computed > 0:
            entry["ratio"] = entry["test_count"] / total_tests_computed
        else:
            entry["ratio"] = 0.0

    supplied_total = concentration_raw.get("total_tests") if isinstance(concentration_raw, dict) else None
    supplied_per_location = (
        concentration_raw.get("per_location") if isinstance(concentration_raw, dict) else None
    )
    supplied_per_location = supplied_per_location if isinstance(supplied_per_location, list) else []

    mismatch_messages: list[str] = []
    if isinstance(supplied_total, int) and supplied_total != total_tests_computed:
        mismatch_messages.append(
            f"total_tests supplied={supplied_total} computed={total_tests_computed}"
        )

    supplied_by_id = {}
    for entry in supplied_per_location:
        if not isinstance(entry, dict):
            continue
        loc_id = entry.get("location_id")
        if isinstance(loc_id, str):
            supplied_by_id[loc_id.strip()] = entry

    computed_by_id = {entry["location_id"]: entry for entry in per_location_computed}
    for loc_id, computed in computed_by_id.items():
        supplied = supplied_by_id.get(loc_id)
        if supplied is None:
            mismatch_messages.append(
                f"location {loc_id!r} missing from naming_pass.concentration_math.per_location"
            )
            continue
        supplied_count = supplied.get("test_count")
        if isinstance(supplied_count, int) and supplied_count != computed["test_count"]:
            mismatch_messages.append(
                f"location {loc_id!r} test_count supplied={supplied_count} "
                f"computed={computed['test_count']}"
            )
        supplied_ratio = supplied.get("ratio")
        if isinstance(supplied_ratio, (int, float)):
            if abs(float(supplied_ratio) - computed["ratio"]) > 1e-6:
                mismatch_messages.append(
                    f"location {loc_id!r} ratio supplied={supplied_ratio} "
                    f"computed={computed['ratio']:.6f}"
                )

    for loc_id in supplied_by_id:
        if loc_id not in computed_by_id:
            mismatch_messages.append(
                f"location {loc_id!r} listed in naming_pass.concentration_math.per_location "
                f"but not present in construction_manifest.flipping_point_contract.locations"
            )

    if mismatch_messages:
        errors.append(
            "naming_pass.concentration_math disagrees with computed values: "
            + "; ".join(mismatch_messages)
        )

    if isinstance(concentration_cap, (int, float)):
        for entry in per_location_computed:
            if entry["ratio"] > float(concentration_cap) + 1e-9:
                errors.append(
                    f"location {entry['location_id']!r} controls "
                    f"{entry['test_count']}/{total_tests_computed} = "
                    f"{entry['ratio']:.4f} tests, exceeds concentration_cap "
                    f"{concentration_cap}."
                )

    renames_normalized: list[dict[str, str]] = []
    for entry in renames_raw:
        if not isinstance(entry, dict):
            continue
        renames_normalized.append(
            {
                "original": str(entry.get("original", "")).strip(),
                "renamed_to": str(entry.get("renamed_to", "")).strip(),
                "reason": str(entry.get("reason", "")).strip(),
            }
        )

    if len(renames_normalized) == 0:
        counts["WARN"] += 1

    return {
        "instruction_nouns_extracted": nouns,
        "renames_during_drafting": renames_normalized,
        "test_names_audited": test_names,
        "concentration_math": {
            "total_tests": (
                int(supplied_total)
                if isinstance(supplied_total, int)
                else total_tests_computed
            ),
            "per_location": [
                {
                    "location_id": entry.get("location_id", ""),
                    "test_count": entry.get("test_count", 0),
                    "ratio": float(entry.get("ratio", 0.0)),
                }
                for entry in supplied_per_location
                if isinstance(entry, dict)
            ],
        },
        "recomputed_concentration": {
            "total_tests": total_tests_computed,
            "concentration_cap": concentration_cap,
            "per_location": [
                {
                    "location_id": entry["location_id"],
                    "test_count": entry["test_count"],
                    "ratio": entry["ratio"],
                }
                for entry in per_location_computed
            ],
        },
    }


def _load_validation_schema() -> tuple[dict[str, Any] | None, list[str]]:
    if jsonschema_exceptions is None or jsonschema_validators is None:
        return None, [
            "jsonschema is required to validate Step 2a evidence against "
            f"{SCHEMA_PATH.as_posix()}."
        ]

    if not SCHEMA_PATH.exists():
        return None, [f"Schema file {SCHEMA_PATH.as_posix()} is missing from the repo."]

    try:
        schema = load_json(SCHEMA_PATH)
    except json.JSONDecodeError as exc:
        return None, [f"Schema file {SCHEMA_PATH.as_posix()} is not valid JSON: {exc}"]

    if not isinstance(schema, dict):
        return None, [f"Schema file {SCHEMA_PATH.as_posix()} must contain a JSON object."]

    try:
        validator_cls, runtime_schema = _schema_validator(schema)
        validator_cls.check_schema(runtime_schema)
    except jsonschema_exceptions.SchemaError as exc:
        return None, [f"Schema file {SCHEMA_PATH.as_posix()} is not a valid JSON Schema: {exc.message}"]

    return runtime_schema, []


def _format_json_path(path: Any) -> str:
    if not path:
        return "$"

    parts = ["$"]
    for component in path:
        if isinstance(component, int):
            parts.append(f"[{component}]")
        else:
            parts.append(f".{component}")
    return "".join(parts)


def _validate_schema(raw_evidence: Any) -> list[str]:
    schema, schema_load_errors = _load_validation_schema()
    if schema is None:
        return schema_load_errors

    validator_cls, runtime_schema = _schema_validator(schema)
    validator = validator_cls(runtime_schema)
    errors = sorted(
        validator.iter_errors(raw_evidence),
        key=lambda error: (_format_json_path(error.absolute_path), error.message),
    )
    return [
        f"Schema validation failed at {_format_json_path(error.absolute_path)}: {error.message}"
        for error in errors
    ]


def _schema_validator(schema: dict[str, Any]) -> tuple[Any, dict[str, Any]]:
    draft_2020_12 = getattr(jsonschema_validators, "Draft202012Validator", None)
    if draft_2020_12 is not None:
        return draft_2020_12, schema
    return jsonschema_validators.Draft7Validator, _draft7_compatible_schema(schema)


def _draft7_compatible_schema(value: Any) -> Any:
    if isinstance(value, dict):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            normalized_key = "definitions" if key == "$defs" else key
            normalized_value = _draft7_compatible_schema(item)
            if key == "$ref" and isinstance(normalized_value, str):
                normalized_value = normalized_value.replace("#/$defs/", "#/definitions/")
            normalized[normalized_key] = normalized_value
        return normalized

    if isinstance(value, list):
        return [_draft7_compatible_schema(item) for item in value]

    return value


def _shape_level_contract_warnings(raw_evidence: Any) -> list[str]:
    if not isinstance(raw_evidence, dict):
        return []

    warnings = [
        f"{field} is missing ({description}). New strict-mode specs must provide it."
        for field, description in SHAPE_LEVEL_EVIDENCE_FIELDS.items()
        if field not in raw_evidence
    ]
    platform_files = raw_evidence.get("platform_files")
    if isinstance(platform_files, list):
        platform_paths = {
            entry.get("path")
            for entry in platform_files
            if isinstance(entry, dict) and isinstance(entry.get("path"), str)
        }
        missing_platform = sorted(REQUIRED_PLATFORM_FILES - platform_paths)
        if missing_platform:
            warnings.append(
                "platform_files is missing required platform path(s): "
                + ", ".join(missing_platform)
            )

    task_files = raw_evidence.get("task_files")
    if isinstance(task_files, list):
        bad_task_paths = [
            entry.get("path")
            for entry in task_files
            if isinstance(entry, dict)
            and isinstance(entry.get("path"), str)
            and not entry["path"].startswith("environment/")
        ]
        if bad_task_paths:
            warnings.append(
                "task_files entries must be under environment/: "
                + ", ".join(sorted(bad_task_paths))
            )

    realism_source = raw_evidence.get("realism_source")
    if isinstance(realism_source, dict):
        if (
            realism_source.get("source_type") == "synthetic_exception"
            and not str(realism_source.get("synthetic_exception_review", "")).strip()
        ):
            warnings.append(
                "realism_source.synthetic_exception_review must describe the extra "
                "review when realism_source.source_type is synthetic_exception."
            )

    return warnings


def validate_evidence(raw_evidence: Any, strict: bool = False) -> dict[str, Any]:
    schema_errors = _validate_schema(raw_evidence)
    if schema_errors:
        return {
            "normalized": {},
            "errors": schema_errors,
            "hard_fail_reasons": schema_errors,
            "warnings": [],
            "score": [len(schema_errors), 0],
        }

    errors: list[str] = []
    warnings: list[str] = []
    hard_fail_reasons: list[str] = []
    counts = {"PASS": 0, "WARN": 0, "FAIL": 0}

    shape_warnings = _shape_level_contract_warnings(raw_evidence)
    if strict:
        errors.extend(shape_warnings)
    else:
        warnings.extend(shape_warnings)

    normalized: dict[str, Any] = {}
    normalized["hardness_axes"] = _validate_named_verdict_entries(
        raw_evidence, "hardness_axes", HARDNESS_AXES, errors, counts
    )
    normalized["anti_trivialization_checks"] = _validate_named_verdict_entries(
        raw_evidence, "anti_trivialization_checks", ANTI_TRIVIALIZATION_CHECKS, errors, counts
    )
    normalized["rubric_axes"] = _validate_named_verdict_entries(
        raw_evidence, "rubric_axes", RUBRIC_AXES, errors, counts
    )
    normalized["instruction_completeness_test"] = _validate_verdict_block(
        raw_evidence, "instruction_completeness_test", errors, counts
    )
    normalized["discovery_budget"] = _validate_discovery_budget(
        raw_evidence, errors, hard_fail_reasons
    )
    normalized["instruction_specificity"] = _validate_instruction_specificity(
        raw_evidence, errors, hard_fail_reasons
    )
    normalized["attack_path"] = _validate_analysis_block(raw_evidence, "attack_path", errors)
    normalized["smallest_plausible_patch"] = _validate_analysis_block(
        raw_evidence, "smallest_plausible_patch", errors
    )
    normalized["collapse_audit"] = _validate_collapse_audit(raw_evidence, errors, counts)
    normalized["topology_enumeration"] = raw_evidence.get("topology_enumeration", [])
    normalized["construction_manifest"] = raw_evidence.get("construction_manifest", {})
    normalized["naming_pass"] = _validate_naming_pass(
        raw_evidence, errors, hard_fail_reasons, counts
    )
    for field_name in SHAPE_LEVEL_EVIDENCE_FIELDS:
        if field_name in raw_evidence:
            normalized[field_name] = raw_evidence[field_name]
    if "waivers" in raw_evidence:
        normalized["waivers"] = raw_evidence["waivers"]

    anti_map = {
        entry["id"]: entry for entry in normalized["anti_trivialization_checks"] if isinstance(entry, dict)
    }
    discovery_budget_check = anti_map.get("discovery_budget_test")
    if (
        discovery_budget_check
        and discovery_budget_check["verdict"] == "PASS"
        and len(normalized["discovery_budget"]) < MIN_DISCOVERY_BUDGET_ITEMS
    ):
        errors.append(
            "anti_trivialization_checks marks discovery_budget_test PASS, but "
            "discovery_budget has fewer than 3 items."
        )

    specificity_check = anti_map.get("instruction_specificity_test")
    specificity_level = normalized["instruction_specificity"].get("level")
    if specificity_check and specificity_check["verdict"] == "PASS" and specificity_level != "symptoms-only":
        errors.append(
            "anti_trivialization_checks marks instruction_specificity_test PASS, but instruction_specificity.level is not 'symptoms-only'."
        )

    hard_fail_reasons = list(dict.fromkeys(hard_fail_reasons + errors))
    score = [counts["FAIL"] + len(hard_fail_reasons), counts["WARN"]]
    return {
        "normalized": normalized,
        "errors": errors,
        "hard_fail_reasons": hard_fail_reasons,
        "warnings": warnings,
        "score": score,
    }


def cmd_init(args: argparse.Namespace) -> None:
    task_name = args.task_name
    SPECS_DIR.mkdir(exist_ok=True)
    run_dir(task_name).mkdir(parents=True, exist_ok=True)

    sp = state_path(task_name)
    if sp.exists():
        print("Loop already active. Run 'reset' first to start over.")
        sys.exit(1)

    state = {
        "task_name": task_name,
        "attempt": 0,
        "best_score": [999, 999],
        "best_attempt": 0,
        "plateau_count": 0,
        "candidates": [],
        "history": [],
        "schema_path": SCHEMA_PATH.as_posix(),
        "emit_legacy_reviewer": bool(getattr(args, "emit_legacy_reviewer", False)),
    }
    save_state(task_name, state)

    log = validation_log_path(task_name)
    log.write_text(f"# Validation Log: {task_name}\n\n", encoding="utf-8")

    print(f"Initialized loop for '{task_name}'.")
    print(f"Evidence schema: {SCHEMA_PATH.as_posix()}")
    print(f"INTERNAL_RUN_DIR: {run_dir(task_name).as_posix()}")
    print("ACTION: CONTINUE")
    print(f"SAVE_TO: {authoring_spec_path(task_name).as_posix()}")
    if state["emit_legacy_reviewer"]:
        print(f"LEGACY_REVIEWER_SAVE_TO: {reviewer_spec_path(task_name).as_posix()}")
    print("REASON: First attempt — run CHECK on the idea and record structured evidence.")


def cmd_record(args: argparse.Namespace) -> None:
    task_name = args.task_name
    state = load_state(task_name)
    if getattr(args, "emit_legacy_reviewer", False):
        state["emit_legacy_reviewer"] = True
    emit_legacy_reviewer = bool(state.get("emit_legacy_reviewer"))

    if (args.fails is None) != (args.warns is None):
        print("ERROR: --fails and --warns must be provided together if you provide either one.")
        sys.exit(1)

    evidence_input_path = Path(args.evidence)
    if not evidence_input_path.is_absolute():
        evidence_input_path = Path.cwd() / evidence_input_path
    if not evidence_input_path.exists():
        print(f"ERROR: Evidence file {evidence_input_path} does not exist.")
        sys.exit(1)

    try:
        raw_evidence = load_json(evidence_input_path)
    except json.JSONDecodeError as exc:
        print(f"ERROR: Evidence file {evidence_input_path} is not valid JSON: {exc}")
        sys.exit(1)

    attempt = state["attempt"] + 1
    strict = bool(getattr(args, "strict", False))
    validation = validate_evidence(raw_evidence, strict=strict)
    fails, warns = validation["score"]
    provided_score = None
    provided_score_mismatch = None
    if args.fails is not None and args.warns is not None:
        provided_score = [args.fails, args.warns]
        if provided_score != [fails, warns]:
            provided_score_mismatch = (
                f"Provided score was {args.fails}F/{args.warns}W but the loop derived "
                f"{fails}F/{warns}W from structured evidence."
            )

    stored_evidence_path = attempt_evidence_path(task_name, attempt)
    stored_evidence_path.write_text(
        json.dumps(validation["normalized"], indent=2) + "\n",
        encoding="utf-8",
    )

    state["attempt"] = attempt
    history_entry = {
        "attempt": attempt,
        "fails": fails,
        "warns": warns,
        "evidence_path": stored_evidence_path.as_posix(),
        "evidence": validation["normalized"],
        "evidence_errors": validation["errors"],
        "evidence_warnings": validation["warnings"],
        "blocking_failures": validation["hard_fail_reasons"],
        "strict": strict,
    }
    if provided_score is not None:
        history_entry["provided_score"] = provided_score
    if provided_score_mismatch is not None:
        history_entry["provided_score_mismatch"] = provided_score_mismatch
    state["history"].append(history_entry)

    log = validation_log_path(task_name)
    with open(log, "a", encoding="utf-8") as handle:
        handle.write(f"## Attempt {attempt}\n")
        handle.write(f"- Derived score: {fails} FAILs, {warns} WARNs\n")
        handle.write(f"- Evidence: {stored_evidence_path.as_posix()}\n")
        if provided_score is not None:
            handle.write(f"- Provided score: {provided_score[0]} FAILs, {provided_score[1]} WARNs\n")
        if provided_score_mismatch is not None:
            handle.write(f"- Score mismatch: {provided_score_mismatch}\n")
        if validation["errors"]:
            handle.write("- Evidence errors:\n")
            for issue in validation["errors"]:
                handle.write(f"  - {issue}\n")
        if validation["warnings"]:
            handle.write("- Evidence warnings:\n")
            for issue in validation["warnings"]:
                handle.write(f"  - {issue}\n")
        if validation["hard_fail_reasons"]:
            handle.write("- Blocking evidence failures:\n")
            for issue in validation["hard_fail_reasons"]:
                handle.write(f"  - {issue}\n")
        handle.write("\n")

    best = state["best_score"]
    improved = (fails, warns) < (best[0], best[1])
    same_score = [fails, warns] == best

    if fails == 0 and warns == 0:
        state["best_score"] = [fails, warns]
        state["best_attempt"] = attempt
        _cleanup_candidate_files(task_name, state)
        state["candidates"] = []
        save_state(task_name, state)
        print(f"Attempt {attempt}: {fails}F, {warns}W — PERFECT")
        if provided_score_mismatch is not None:
            print(f"NOTE: {provided_score_mismatch}")
        if validation["warnings"]:
            print("Non-blocking evidence warnings:")
            for issue in validation["warnings"]:
                print(f"  - {issue}")
        print("ACTION: GO")
        print(f"SAVE_TO: {authoring_spec_path(task_name).as_posix()}")
        if emit_legacy_reviewer:
            print(f"LEGACY_REVIEWER_SAVE_TO: {reviewer_spec_path(task_name).as_posix()}")
        print(f"THEN_RUN: python3 scripts/validate_loop.py finalize {task_name}")
        print("REASON: Structured evidence is complete and every scored check passed.")
        return

    if improved:
        state["best_score"] = [fails, warns]
        state["best_attempt"] = attempt
        state["plateau_count"] = 0
        _cleanup_candidate_files(task_name, state)
        state["candidates"] = []
        save_to = authoring_spec_path(task_name).as_posix()
        print(f"Attempt {attempt}: {fails}F, {warns}W — IMPROVED (was {best[0]}F, {best[1]}W)")
    elif same_score:
        state["plateau_count"] += 1
        candidate_n = len(state["candidates"]) + 1
        state["candidates"].append(
            {
                "attempt": attempt,
                "candidate_n": candidate_n,
                "score": [fails, warns],
                "evidence_path": stored_evidence_path.as_posix(),
            }
        )
        save_to = authoring_spec_path(task_name, candidate_n).as_posix()
        print(
            f"Attempt {attempt}: {fails}F, {warns}W — PLATEAU "
            f"({state['plateau_count']}/{PLATEAU_THRESHOLD})"
        )
    else:
        save_to = "DISCARD"
        print(
            f"Attempt {attempt}: {fails}F, {warns}W — REGRESSION "
            f"(best is {best[0]}F, {best[1]}W, discarding)"
        )

    if provided_score_mismatch is not None:
        print(f"NOTE: {provided_score_mismatch}")

    if validation["warnings"]:
        print("Non-blocking evidence warnings:")
        for issue in validation["warnings"]:
            print(f"  - {issue}")

    if validation["hard_fail_reasons"]:
        print("Blocking evidence issues:")
        for issue in validation["hard_fail_reasons"]:
            print(f"  - {issue}")

    if state["plateau_count"] >= PLATEAU_THRESHOLD:
        save_state(task_name, state)
        if state["best_score"][0] > 0:
            print("ACTION: STOP")
            print(f"SAVE_TO: {save_to}")
            _print_legacy_reviewer_save_to(task_name, save_to, emit_legacy_reviewer)
            print("REASON: Plateau with FAILs remaining. Idea family cannot be saved.")
        else:
            print("ACTION: SELECT")
            print(f"SAVE_TO: {save_to}")
            _print_legacy_reviewer_save_to(task_name, save_to, emit_legacy_reviewer)
            print("REASON: Plateau reached. Compare candidates via collapse audit and stored evidence.")
            print(f"CANDIDATES: {_candidate_directive(task_name, state, emit_legacy_reviewer)}")
        return

    if attempt >= 3:
        last_3 = state["history"][-3:]
        no_improvement = all(
            current["fails"] >= previous["fails"] and current["warns"] >= previous["warns"]
            for previous, current in zip(last_3, last_3[1:])
        ) and last_3[-1]["fails"] > 0
        if no_improvement:
            save_state(task_name, state)
            print("ACTION: STOP")
            print(f"SAVE_TO: {save_to}")
            _print_legacy_reviewer_save_to(task_name, save_to, emit_legacy_reviewer)
            print(
                f"REASON: No score improvement across 3 consecutive attempts "
                f"(still {fails}F). Idea family cannot be saved."
            )
            return

    if attempt >= MAX_ATTEMPTS:
        save_state(task_name, state)
        if state["best_score"][0] == 0:
            if state["candidates"]:
                print("ACTION: SELECT")
                print(f"SAVE_TO: {save_to}")
                _print_legacy_reviewer_save_to(task_name, save_to, emit_legacy_reviewer)
                print("REASON: Max attempts reached. Compare candidates via collapse audit and stored evidence.")
                print(f"CANDIDATES: {_candidate_directive(task_name, state, emit_legacy_reviewer)}")
            else:
                print("ACTION: GO")
                print(f"SAVE_TO: {authoring_spec_path(task_name).as_posix()}")
                if emit_legacy_reviewer:
                    print(f"LEGACY_REVIEWER_SAVE_TO: {reviewer_spec_path(task_name).as_posix()}")
                print("REASON: Max attempts reached. Best variant has 0 FAILs with complete structured evidence.")
        else:
            print("ACTION: STOP")
            print(f"SAVE_TO: {save_to}")
            _print_legacy_reviewer_save_to(task_name, save_to, emit_legacy_reviewer)
            print("REASON: Max attempts with FAILs remaining.")
        return

    save_state(task_name, state)
    print("ACTION: CONTINUE")
    print(f"SAVE_TO: {save_to}")
    _print_legacy_reviewer_save_to(task_name, save_to, emit_legacy_reviewer)
    if validation["hard_fail_reasons"]:
        print("REASON: Structured evidence is incomplete or blocking checks still fail.")
    else:
        print(f"REASON: {'Improved — fix remaining WARNs.' if improved else 'Plateau — try different fixes.'}")


def _cleanup_candidate_files(task_name: str, state: dict[str, Any]) -> None:
    for candidate in state.get("candidates", []):
        for path in (
            authoring_spec_path(task_name, candidate["candidate_n"]),
            reviewer_spec_path(task_name, candidate["candidate_n"]),
        ):
            if path.exists():
                path.unlink()


def _print_legacy_reviewer_save_to(task_name: str, save_to: str, emit_legacy: bool) -> None:
    if not emit_legacy:
        return
    if save_to == "DISCARD":
        print("LEGACY_REVIEWER_SAVE_TO: DISCARD")
        return
    path = Path(save_to)
    candidate_n: int | None = None
    stem = path.stem
    marker = "-candidate-"
    if marker in stem:
        try:
            candidate_n = int(stem.rsplit(marker, 1)[1])
        except ValueError:
            candidate_n = None
    print(f"LEGACY_REVIEWER_SAVE_TO: {reviewer_spec_path(task_name, candidate_n).as_posix()}")


def _candidate_specs(task_name: str, state: dict[str, Any], include_legacy: bool = False) -> list[dict[str, Any]]:
    candidates = [
        {
            "attempt": state["best_attempt"],
            "candidate_n": None,
            "authoring_path": authoring_spec_path(task_name).as_posix(),
        }
    ]
    if include_legacy:
        candidates[0]["reviewer_path"] = reviewer_spec_path(task_name).as_posix()
    for candidate in state.get("candidates", []):
        entry = {
            "attempt": candidate["attempt"],
            "candidate_n": candidate["candidate_n"],
            "authoring_path": authoring_spec_path(task_name, candidate["candidate_n"]).as_posix(),
        }
        if include_legacy:
            entry["reviewer_path"] = reviewer_spec_path(task_name, candidate["candidate_n"]).as_posix()
        candidates.append(entry)
    return candidates


def _candidate_directive(task_name: str, state: dict[str, Any], include_legacy: bool = False) -> str:
    parts = []
    for candidate in _candidate_specs(task_name, state, include_legacy):
        target = candidate["authoring_path"]
        if include_legacy:
            target = f"{target}|{candidate['reviewer_path']}"
        parts.append(f"{candidate['attempt']}={target}")
    return ",".join(parts)


def _candidate_choices(task_name: str, state: dict[str, Any], include_legacy: bool = False) -> str:
    choices = []
    for candidate in _candidate_specs(task_name, state, include_legacy):
        target = candidate["authoring_path"]
        if include_legacy:
            target = f"{target} | {candidate['reviewer_path']}"
        choices.append(f"attempt {candidate['attempt']} -> {target}")
    return ", ".join(choices)


def _resolve_winner(task_name: str, state: dict[str, Any], winner: str, include_legacy: bool = False) -> dict[str, Any] | None:
    winner = winner.strip()
    if not winner:
        return None

    for candidate in _candidate_specs(task_name, state, include_legacy):
        if (
            winner == str(candidate["attempt"])
            or winner == candidate["authoring_path"]
            or (include_legacy and winner == candidate["reviewer_path"])
        ):
            return candidate

    winner_path = Path(winner)
    resolved_winner = (winner_path if winner_path.is_absolute() else Path.cwd() / winner_path).resolve()
    for candidate in _candidate_specs(task_name, state, include_legacy):
        path_keys = ("authoring_path", "reviewer_path") if include_legacy else ("authoring_path",)
        for path_key in path_keys:
            candidate_path = Path(candidate[path_key])
            resolved_candidate = (Path.cwd() / candidate_path).resolve()
            if resolved_winner == resolved_candidate:
                return candidate

    return None


def _enforce_lint_spec_or_exit(spec_path: Path) -> None:
    """Run lint_spec on `spec_path` in strict mode; exit non-zero on any failure.

    Step 2a's final gate before the spec becomes the canonical drafting
    input for Step 2b. By the time `select` runs, all candidate specs
    are freshly-authored under the v2 contract: a missing `version:`
    line is itself a defect, not a license to skip the v2 sub-section
    requirements. The lint enforces three sub-sections under
    `## Authoring Brief` (legacy v2 sections plus shape-level commitment
    sections). See `scripts/lint_spec.py` for the detailed contract.
    """
    failures = lint_spec.run(spec_path, strict=True)
    if not failures:
        return
    print(f"ERROR: lint_spec rejected the picked spec ({spec_path}):")
    for failure in failures:
        print(f"  - {failure}")
    print(
        "REASON: v2 spec is missing one or more mandatory strict-mode sub-sections under "
        "`## Authoring Brief`. Fix the spec and re-run `scripts/validate_loop.py select`."
    )
    sys.exit(1)


def cmd_select(args: argparse.Namespace) -> None:
    task_name = args.task_name
    state = load_state(task_name)
    if getattr(args, "emit_legacy_reviewer", False):
        state["emit_legacy_reviewer"] = True
    emit_legacy_reviewer = bool(state.get("emit_legacy_reviewer"))
    winner = _resolve_winner(task_name, state, args.winner, emit_legacy_reviewer)

    if winner is None:
        print(
            f"ERROR: --winner {args.winner!r} is not a valid candidate. "
            f"Valid choices: {_candidate_choices(task_name, state, emit_legacy_reviewer)}"
        )
        sys.exit(1)

    winner_attempt = winner["attempt"]
    previous_best = state["best_attempt"]
    canonical_authoring = authoring_spec_path(task_name)
    if winner_attempt == previous_best:
        required = [canonical_authoring]
        if emit_legacy_reviewer:
            required.append(reviewer_spec_path(task_name))
        missing = [path.as_posix() for path in required if not path.exists()]
        if missing:
            print(f"ERROR: Canonical spec files are missing: {', '.join(missing)}")
            sys.exit(1)
        _enforce_lint_spec_or_exit(canonical_authoring)
        print(f"Winner is the pre-plateau best (attempt {winner_attempt}), already at {canonical_authoring.name}.")
    else:
        winner_authoring = authoring_spec_path(task_name, winner["candidate_n"])
        required = [winner_authoring]
        if emit_legacy_reviewer:
            required.append(reviewer_spec_path(task_name, winner["candidate_n"]))
        missing = [path.as_posix() for path in required if not path.exists()]
        if missing:
            print(
                f"ERROR: Candidate files for attempt {winner_attempt} not found on disk: "
                f"{', '.join(missing)}"
            )
            sys.exit(1)
        _enforce_lint_spec_or_exit(winner_authoring)

        canonical_authoring.write_text(
            winner_authoring.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        if emit_legacy_reviewer:
            winner_reviewer = reviewer_spec_path(task_name, winner["candidate_n"])
            canonical_reviewer = reviewer_spec_path(task_name)
            canonical_reviewer.write_text(
                winner_reviewer.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            print(
                f"Promoted {winner_authoring.name} -> {canonical_authoring.name} and "
                f"{winner_reviewer.name} -> {canonical_reviewer.name}"
            )
        else:
            print(f"Promoted {winner_authoring.name} -> {canonical_authoring.name}")

    state["best_attempt"] = winner_attempt
    _cleanup_candidate_files(task_name, state)
    state["candidates"] = []
    save_state(task_name, state)

    print(f"Winner: attempt {winner_attempt} ({winner['authoring_path']})")
    print("ACTION: GO")
    print(f"SAVE_TO: {canonical_authoring.as_posix()}")
    if emit_legacy_reviewer:
        print(f"LEGACY_REVIEWER_SAVE_TO: {reviewer_spec_path(task_name).as_posix()}")
    print("REASON: Candidate selected and promoted. Spec is final.")


def cmd_status(args: argparse.Namespace) -> None:
    state = load_state(args.task_name)
    print(json.dumps(state, indent=2))


def cmd_reset(args: argparse.Namespace) -> None:
    task_name = args.task_name
    for path in SPECS_DIR.glob(f"{task_name}*"):
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
    for path in SPECS_DIR.glob(f".{task_name}*"):
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
    if run_dir(task_name).exists():
        shutil.rmtree(run_dir(task_name))
    print(f"Reset '{task_name}'.")


def cmd_finalize(args: argparse.Namespace) -> None:
    """Strictly lint the canonical authoring spec after Step 2a save.

    Step 2a's `record` GO path prints SAVE_TO and the agent writes the
    single canonical authoring spec next. This subcommand is the gate
    the agent runs after saving: it confirms the canonical file exists
    and that the authoring spec satisfies the v2 contract
    under strict mode (missing `version:` line is a failure, not a
    grandfather signal). Exits 0 on pass, 1 on lint failure with
    actionable detail.
    """
    task_name = args.task_name
    canonical_authoring = authoring_spec_path(task_name)
    missing = [canonical_authoring.as_posix()] if not canonical_authoring.exists() else []
    if missing:
        print(f"ERROR: Canonical spec files are missing: {', '.join(missing)}")
        print(
            "REASON: Run `scripts/validate_loop.py record` first and save the spec "
            "to the printed SAVE_TO path."
        )
        sys.exit(1)
    failures = lint_spec.run(canonical_authoring, strict=True)
    if not failures:
        print(f"OK: {canonical_authoring.as_posix()} passes strict lint.")
        print(
            "NEXT: run `python3 scripts/spec_satisfiability.py "
            f"{canonical_authoring.as_posix()} --strict` before Step 2b task authoring."
        )
        return
    print(f"ERROR: lint_spec --strict rejected {canonical_authoring.as_posix()}:")
    for failure in failures:
        print(f"  - {failure}")
    print(
        "REASON: v2 spec contract not satisfied. Add `version: 2` to "
        "`### Metadata` and ensure `## Authoring Brief` contains "
        "`### Triviality Ledger`, `### Per-gate Pitfall Inventory`, and "
        "`### Initial Draft Commitments`, plus the strict shape-level "
        "sections (`platform_files`, `task_files`, `fix_frontier`, "
        "`contract_surface`, `category_profile`, `satisfiability_risk`, "
        "`actionability_plan`, `waiver_plan`, `reference_pattern`, "
        "`realism_source`). Then re-run `scripts/validate_loop.py finalize <task>`."
    )
    sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command")

    init_parser = sub.add_parser("init")
    init_parser.add_argument("task_name")
    init_parser.add_argument(
        "--emit-legacy-reviewer",
        action="store_true",
        help="Also print legacy reviewer sidecar paths for migration diagnostics.",
    )

    record_parser = sub.add_parser("record")
    record_parser.add_argument("task_name")
    record_parser.add_argument("--evidence", required=True)
    record_parser.add_argument(
        "--strict",
        action="store_true",
        help=(
            "Require the shape-level Step 2a evidence fields "
            "(platform_files, task_files, fix_frontier, contract_surface, "
            "category_profile, satisfiability_risk, actionability_plan, "
            "waiver_plan, reference_pattern, realism_source). Without this flag, "
            "missing fields are reported as non-blocking warnings for backward "
            "compatibility."
        ),
    )
    record_parser.add_argument("--fails", type=int)
    record_parser.add_argument("--warns", type=int)
    record_parser.add_argument(
        "--emit-legacy-reviewer",
        action="store_true",
        help="Also print legacy reviewer sidecar paths for migration diagnostics.",
    )

    select_parser = sub.add_parser("select")
    select_parser.add_argument("task_name")
    select_parser.add_argument("--winner", required=True)
    select_parser.add_argument(
        "--emit-legacy-reviewer",
        action="store_true",
        help="Accept and promote legacy reviewer sidecars during migration diagnostics.",
    )

    finalize_parser = sub.add_parser("finalize")
    finalize_parser.add_argument("task_name")

    status_parser = sub.add_parser("status")
    status_parser.add_argument("task_name")

    reset_parser = sub.add_parser("reset")
    reset_parser.add_argument("task_name")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    {
        "init": cmd_init,
        "record": cmd_record,
        "select": cmd_select,
        "finalize": cmd_finalize,
        "status": cmd_status,
        "reset": cmd_reset,
    }[args.command](args)


if __name__ == "__main__":
    main()
