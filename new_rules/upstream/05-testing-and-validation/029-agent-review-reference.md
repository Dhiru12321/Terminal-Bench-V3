---
title: "Agent Review Reference"
section: "Testing & Validation"
source: "https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/testing-and-validation/agent-review-reference"
captured: 2026-08-12
---

# Agent Review Reference

Agent Review uses Claude Code to comprehensively evaluate Terminal-Bench tasks for compliance with format requirements, best practices, and quality standards. This automated review provides detailed feedback on task structure, correctness, and potential issues.

> **Note:** Agent Review currently does not block task submission. It is provided as an additional tool to help identify potential issues, warnings, and areas for improvement.

## How It Works

Agent Review is an automated process that uses Claude Code with a specialized skill to systematically examine your task directory. It performs static analysis—reading and evaluating files without executing any code or building containers.

The review produces a structured report with issues categorized by severity and actionable fix recommendations.

## What Gets Reviewed

Agent Review performs a systematic static analysis of your task, examining all key files without executing any code.

### Step 1: File Structure Verification

Checks that all required files exist.

Checks that all required files exist:

- `task.toml`
- `instruction.md`
- `environment/Dockerfile`
- `solution/solve.sh`
- `tests/Dockerfile` — builds the separate verifier image
- `tests/test.sh`
- `tests/test_outputs.py`

For multi-container tasks, also verifies:

- `environment/docker-compose.yaml`
- Additional Dockerfiles (e.g., `Dockerfile.server`)
- Required flags in `task.toml`

---

### Step 2: task.toml Configuration

Validates your task metadata:

| Field | Requirement |
| --- | --- |
| `name` | Task name. Top level or under `[metadata]` — both resolve |
| `artifacts` | Top-level array of paths the separate verifier reads. Nesting under `[verifier]` silently drops it |
| `[metadata].category` | Exactly one, from the Task Taxonomy |
| `[metadata].subcategory` | Exactly one, from the Task Taxonomy |
| `[metadata].tags` | 3–6 descriptive keywords |
| `[metadata].languages` | Primary language(s) of the task |
| `[metadata].difficulty` | Must be: frontier, advanced, core, or base |
| `[metadata].expert_time_estimate_hours` | Estimated expert time to author the task |
| `[metadata].author_name` / `.author_email` | Required. Both may be `"anonymous"` |
| `[metadata].difficulty_explanation` | What makes the task hard |
| `[metadata].solution_explanation` | How the oracle solves it |
| `[metadata].verification_explanation` | How the verifier decides the task was solved |
| `[metadata].relevant_experience` | Author's relevant background |
| `[verifier].timeout_sec` | Required |
| `[verifier].environment_mode` | Must be `"separate"` |
| `[agent].timeout_sec` | Required. Minimum 1800 sec, ceiling 18000 sec |
| `[environment].build_timeout_sec` | Required |
| `[environment].cpus` / `.memory_mb` / `.storage_mb` | Resource limits — no GPU |
| `[environment].network_mode` | `"public"` (default) or `"no-network"` |

---

### Step 3: Instruction Quality

Evaluates whether `instruction.md`:

- Provides clear, unambiguous task description
- States success criteria explicitly
- Specifies output format requirements
- Includes necessary context

---

### Step 4: Dockerfile Review

Checks `environment/Dockerfile` for:

- Proper `WORKDIR /app` setup
- Correct data file copying
- Dependency installation
- **Anti-pattern detection**: Tests or solution copied to image

---

### Step 5: Oracle Solution Review

Evaluates `solution/solve.sh` for:

- Proper shebang (`#!/usr/bin/env bash`)
- Error handling (`set -euo pipefail`)
- Solution completeness and correctness
- Code clarity and maintainability

---

### Step 6: Test Coverage

Analyzes `tests/test_outputs.py` for:

- Use of Python pytest framework
- Multiple test functions
- Clear, specific assertions
- Helpful error messages
- Edge case coverage

---

### Step 7: Test Runner Validation

Verifies `tests/test.sh`:

- Has proper shebang
- Runs the Python pytest verifier with pinned, pre-installed dependencies
- Does not install packages or download from the network at runtime
- **Writes reward to `/logs/verifier/reward.txt`** (critical)
- Handles working directory validation

---

### Step 8: Advanced Quality Checks

Beyond structure, the review evaluates:

#### Behavior Coverage

- All tested behavior is described in instructions
- All described behavior is verified by tests

#### Anti-Cheating Measures

- Can the agent bypass the intended solution?
- Are there shortcuts via data file editing?
- Are solutions findable in environment files?

#### Structured Data Schema

- JSON/API outputs have exact schema definitions
- Field names, types, and structure are specified

#### Dependency Pinning

- Python packages have exact version pins
- Every Docker `FROM` image and pulled compose `image:` is digest-pinned with `@sha256:<digest>`
- The final runtime base image is sanctioned or explicitly exempt
- Large optional assets are not baked into `environment/`

#### Naming and Typos

- File paths are correct
- Variable names are consistent
- API endpoints match between instruction, solution, and tests

### Trial Analysis

The difficulty check appends a trial analysis section reporting six criteria, each returning **PASS**, **FAIL**, or **NOT_APPLICABLE**:

- `task_specification` — were the instructions sufficient for an agent to succeed?
- `reward_hacking` — was the reward earned legitimately, or by manipulating the harness?
- `difficulty_crux` — did the agent fail for the reason the author described?
- `near_miss` — did a working solution fall just short of a threshold?
- `refusals` — did the agent abort on a content or safety policy?
- `low_timeout` — was the agent still making progress when time ran out?

A FAIL on `task_specification` or `reward_hacking` is a definite issue. The other four must be examined rather than waved through — see the [Reviewer Checklist](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/reviewing-tasks/reviewer-checklist) for how to handle each, and [Difficulty Guidelines](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/difficulty-guidelines) for what to do about a flag on your own task.

---

## Quality Control Criteria

The review enforces these critical guidelines:

### No Latency-Based Tests

Tests must not check for performance thresholds—these vary by hardware and aren't reproducible.

### Identical Oracle/Agent Testing

Testing logic must be exactly the same for both oracle and agent. Conditional behavior based on execution mode is banned.

### Multi-Container Tagging

Tasks that run multiple containers must set `is_multi_container = true` under `[metadata]` in `task.toml`. The field is optional — omit it for single-container tasks. The harness detects `environment/docker-compose.yaml` on its own; nothing in `task.toml` points at it.

### No Web Data Fetching

Tasks should not fetch data from URLs (except package managers). Pre-download data into `environment/`.

### Reserved Directories

Dockerfile must not create or modify `/tests`, `/solution`, or `/oracle` directories.

### Reward File Required

`test.sh` must always write to `/logs/verifier/reward.txt` after tests complete.

### Environment Variable Defaults

When using `$TEST_DIR`, provide a default value. Hardcoded paths and standard variables (`$HOME`, `$PWD`) are fine without defaults.

---

## Issue Severity Levels

### ❌ Critical (Must Fix)

Issues that make the task invalid or unfair:

- Missing required files
- Invalid TOML syntax or missing fields
- No test functions
- Reward file not written
- Behavior mismatch between instructions and tests
- Tests or solution copied to image
- Hardcoded solution outputs
- Unpinned Python dependencies or base / compose images without digest pins
- Unsanctioned final runtime base image without an exemption
- Oversized `environment/` build context
- Critical path/variable typos
- Missing structured data schema
- Latency-based tests
- Oracle/Agent conditional logic
- Web data fetching
- Reserved directory creation

### ⚠️ Warning (Should Fix)

Best practice violations:

- Missing shebang
- Brief or unclear instructions
- Missing recommended fields
- Unreasonable timeouts
- Missing WORKDIR in Dockerfile
- Poor test docstrings
- Test dependency installs in `test.sh`
- Verifier dependencies missing from Dockerfile
- Minor typos
- Questionable task quality for stated difficulty

### 💡 Suggestion (Optional)

Improvements to consider:

- Code style enhancements
- Additional test coverage
- Documentation improvements
- Better naming conventions

---

## Review Report Format

The review produces a structured report:

```
### Review Report: [task-name]

**Status:** ✅ PASS | ⚠️ WARNING | ❌ FAIL

**Task Location:** /path/to/task

---

#### Summary
[Brief overview of the task]

---

#### Critical Issues ❌
[Issues that must be fixed, with file locations and suggested fixes]

---

#### Warnings ⚠️
[Best practice violations with recommendations]

---

#### Suggestions 💡
[Optional improvements]

---

#### Overall Assessment
[Summary with key strengths, weaknesses, and recommendation]

**Recommendation:** READY TO USE | NEEDS FIXES | REQUIRES REVISION
```

---

## Example: Critical Fix

Here's an example of a critical issue Claude Code identifies and how to fix it:

**Issue:** Reward file not written after tests run

The `test.sh` script exits after running pytest but before writing the reward file, causing `RewardFileNotFound` errors.

**Before (problematic):**

```bash
#!/bin/bash
set -uo pipefail

mkdir -p /logs/verifier

python -m pytest /tests/test_outputs.py -rA

exit_code=$?
echo "Tests completed with exit code: $exit_code"
exit $exit_code  # Exits here - reward.txt never written

if [ $? -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
```

**After (fixed):**

```bash
#!/bin/bash
set -uo pipefail

mkdir -p /logs/verifier

python -m pytest /tests/test_outputs.py -rA
rc=$?

if [ "$rc" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
```

The fix ensures the reward file is always written after tests complete, which is required by the harness to determine task success or failure.

---

## Acting on Review Feedback

When addressing review findings:

1. **Start with Critical Issues** — These block task validity
2. **Fix Warnings** — Improve task quality and reliability
3. **Consider Suggestions** — Optional but beneficial

---

## Next Steps

- [Reviewer Checklist](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/reviewing-tasks/reviewer-checklist)
- [LLMaJ Checks Reference](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/testing-and-validation/llmaj-checks-reference)
- [CI Checks Reference](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/testing-and-validation/ci-checks-reference)
- [Oracle Agent](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/testing-and-validation/oracle-agent)
- [Submit your task](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/submitting-tasks/submission-checklist)

---

[Previous: LLMaJ Checks Reference](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/testing-and-validation/llmaj-checks-reference) · [Next: Review Guidelines](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/reviewing-tasks/review-guidelines)
