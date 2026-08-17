---
title: "Writing Tests"
section: "Detailed Tasking Guides"
source: "https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/creating-tasks/writing-tests"
captured: 2026-08-12
---

# Writing Tests

The `tests/test_outputs.py` file contains pytest tests that verify task completion. Good tests are the foundation of a quality task.

All verifier tests must be written in Python and run with pytest, regardless of the task's implementation language. For non-Python tasks, write Python tests that exercise the CLI, service, files, or processes under test. `tests/test.sh` is a bash entry point, but it should invoke the Python pytest suite rather than delegating to another language-specific test framework.

## How Verification Works

In Terminus 3 the verifier runs in a **separate container** the agent cannot see or reach:

1. The agent works in the task environment until it stops or times out.
2. Harbor collects the paths declared in `artifacts` from the agent's final environment.
3. A separate verifier container, built from `tests/Dockerfile`, starts up.
4. The collected artifacts are placed into that container.
5. `tests/test.sh` runs and writes a reward.

The verifier never runs inside the agent's environment, and it only ever sees the artifacts you declared.

### Declaring Artifacts

```toml
artifacts = ["/app/output.json", "/app/results/"]
```

> ⚠️ **`artifacts` is a top-level key in `task.toml`.** Nesting it under `[verifier]` does not raise an error — the value is silently dropped and your verifier receives nothing.

**Parent directories must already exist in the verifier image.** Harbor uploads declared artifacts into the verifier, and the upload fails if the landing directory is missing:

```dockerfile
RUN mkdir -p /app/results
```

A missing landing directory produces failures that look like broken tests. Check this first when a verifier fails inexplicably.

### Verifier Dependencies

Everything the verifier needs — pytest, plugins, browser drivers, wheels, npm packages — must be baked into `tests/Dockerfile`. Nothing may be installed or downloaded at trial time.

## Getting Started

### Video Tutorial

#### Creating Tests for Your Task

[Creating Tests for Your Task](https://www.loom.com/embed/a00541ff2787464c84bf4601415ee624?hide_owner=true&hide_share=true&hide_title=true&hideEmbedTopBar=true)

### What You'll Learn

- Structure of test_outputs.py
- Writing effective test cases
- Matching tests to task requirements
- Common testing patterns

---

## Basic Structure

```python
"""Tests for the data processing task."""
import pytest
import json
from pathlib import Path

def test_output_file_exists():
    """Verify the output file was created."""
    assert Path("/output/result.json").exists()

def test_output_format():
    """Verify the output has correct JSON structure."""
    with open("/output/result.json") as f:
        data = json.load(f)

    assert "status" in data
    assert "items" in data
    assert isinstance(data["items"], list)

def test_correct_count():
    """Verify the item count is correct."""
    with open("/output/result.json") as f:
        data = json.load(f)

    assert len(data["items"]) == 42
```

## Key Principles

### 1. Test Behavior, Not Implementation

Run the code and check results. Don't parse source code looking for patterns.

**Good:**

```python
def test_function_handles_empty_input():
    """Empty input should return empty list."""
    from app.main import process
    result = process("")
    assert result == []
```

**Bad:**

```python
def test_has_empty_check():
    """Check if code has empty input handling."""
    source = open("/app/main.py").read()
    assert "if not" in source  # Brittle!
```

### 2. Informative Docstrings

Every test must have a docstring explaining what behavior it checks. This is validated by CI.

```python
def test_api_returns_json():
    """API endpoint should return valid JSON with Content-Type header."""
    response = requests.get("http://localhost:8080/api/data")
    assert response.headers["Content-Type"] == "application/json"
    assert response.json()  # Parseable JSON
```

### 3. Match Task Requirements

Tests need to fully cover all aspects of the prompt (instruction.md). This includes:

- ✅ All explicit requirements from the prompt
- ✅ Implicitly expected behavior
- ✅ Critical edge cases

Every requirement in the prompt must map to a test. If it is implied or stated in the prompt but not covered by tests, that is a miss.

| instruction.md says... | Test verifies... |
| --- | --- |
| "Return empty list for empty input" | `test_empty_input_returns_empty_list` |
| "Output to /data/result.csv" | `test_output_file_exists` |
| "Include header row" | `test_csv_has_header` |

Here's a very simplified example for demonstrative purposes only. If the prompt is:

> Write a Python function called `divide` that takes two numbers and returns the result as a float.

**Explicit tests:**

```python
def test_function_exists():
    """A function called 'divide' exists"""

def test_takes_two_numbers():
    """It accepts two numbers as input"""

def test_divides_correctly():
    """It returns the correct division result"""

def test_returns_float():
    """The return type is a float"""
```

**Implicit test / edge case:**

```python
def test_division_by_zero():
    """It handles division by zero"""
```

The prompt never mentions division by zero, but any reasonable person reading "a function that divides two numbers" would expect it to handle that case.

### 4. Cover Edge Cases

Test the boundaries, not just the happy path:

```python
def test_empty_input():
    """Empty input is handled gracefully."""
    assert process("") == []

def test_single_item():
    """Single item input works correctly."""
    assert process("a") == ["a"]

def test_large_input():
    """Large input is handled efficiently."""
    result = process("x" * 10000)
    assert len(result) == 10000

def test_special_characters():
    """Special characters are preserved."""
    assert process("héllo 世界") == ["héllo", "世界"]
```

## tests/test.sh and tests/Dockerfile

`tests/test.sh` is the verifier entrypoint. It runs the Python pytest suite and writes the reward file. Do not replace pytest with another test framework such as JUnit, Jest, or `go test` — use Python pytest tests to drive and validate those systems when needed.

What is settled for Terminus 3:

- `tests/Dockerfile` builds the verifier image and must bake in **all** verifier dependencies.
- `tests/test.sh` must **not** install packages or fetch anything from the network at runtime — no `uvx`, `pip install`, `npm install`, `curl`, `wget`, or `git clone`.
- The reward is written to `/logs/verifier/reward.txt` (`1` pass, `0` fail).
- pytest is run with `--ctrf /logs/verifier/ctrf.json` to emit a structured test report.
- Pin verifier tooling to exact versions.

### tests/Dockerfile

```dockerfile
FROM python:3.12-slim-bookworm@sha256:<digest>

# Pin every verifier dependency to an exact version — nothing is installed at trial time.
RUN pip install --no-cache-dir pytest==9.1.1 pytest-json-ctrf==0.5.2

# Separate-mode verifiers do not receive an upload of tests/, so the image must own
# /tests itself. The build context is your task's tests/ directory.
COPY . /tests/

# Artifact landing directories must exist before Harbor uploads declared artifacts.
RUN mkdir -p /app
```

Every `FROM` in `tests/Dockerfile` must be digest-pinned and on a sanctioned base image, exactly as in `environment/Dockerfile`. This is currently reported as a **warning** rather than a hard failure, but treat it as required.

### tests/test.sh

```bash
#!/bin/bash
set -uo pipefail

mkdir -p /logs/verifier

python -m pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA
rc=$?

if [ "$rc" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

exit 0
```

Three things about this script are deliberate:

- **No `set -e`.** With `-e`, a failing pytest aborts the script before the reward file is written, and the trial records no result at all. Capture the exit code instead.
- **Always `exit 0`.** Harbor grades from `/logs/verifier/reward.txt`, not from the script's exit status. A non-zero exit does not mark the task failed — it risks the trial being treated as errored.
- **`--ctrf /logs/verifier/ctrf.json` is required** for any pytest-based verifier, and is enforced by an automated check.

> **Verify against the task skeleton.** These shapes are confirmed by the team but predate the published Terminus 3 skeleton. If the skeleton differs, the skeleton wins — and please flag it. The `set -e` guidance and the digest-pinning scope for `tests/Dockerfile` are still being confirmed and may change.

## Common Patterns

### Testing File Output

```python
def test_csv_output():
    """Verify CSV output format and content."""
    import csv

    with open("/output/data.csv") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) > 0
    assert "id" in rows[0]
    assert "name" in rows[0]
```

### Testing API Endpoints

```python
import requests

def test_health_endpoint():
    """Health check endpoint returns 200."""
    response = requests.get("http://localhost:8080/health")
    assert response.status_code == 200

def test_api_error_handling():
    """Invalid requests return 400."""
    response = requests.post(
        "http://localhost:8080/api/data",
        json={"invalid": "data"}
    )
    assert response.status_code == 400
```

### Testing Database State

```python
import sqlite3

def test_database_populated():
    """Database contains expected records."""
    conn = sqlite3.connect("/app/data.db")
    cursor = conn.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    conn.close()

    assert count == 100
```

### Testing Command Output

```python
import subprocess

def test_cli_help():
    """CLI shows help message."""
    result = subprocess.run(
        ["python", "/app/cli.py", "--help"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert "Usage:" in result.stdout
```

## What a Good Verifier Legitimately Does

A rigorous verifier often contains substantial logic — that is expected and fine. The following are **legitimate and encouraged**, not violations:

- **Run the agent's own program.** Build and run the agent's binary/CLI, then grade its output.
- **Parse the agent's output** to check semantics (e.g., interpreting the config, policy, or files the agent produced).
- **Precomputed golden fixtures or hashes** for exact-match or byte-exact tasks (numerical, ML, reporting). Hardcoding the *expected result* is fine and often required.
- **Spec-derived invariants** — compute an expected property from the task's spec/config and check the output against it (e.g., a floor, budget, or cost ceiling).
- **Held-out ground truth**, ideally **sealed into memory and unlinked from `tests/` before the agent's program is built or run**, so a rebuilt program cannot read the answer key at grade time.
- **Perturbation / holdout re-runs** — re-run the agent's program on modified or held-out inputs and assert the output changes. This is the recommended way to prove the solution is *computed*, not hardcoded.

The line to hold is narrow: don't put a **callable end-to-end solver** in `tests/` that maps task inputs to the complete expected artifact (that belongs in `solution/`), and don't hardcode a value the instruction says the agent must read from a config file. Everything above stays fair game.

## Anti-Patterns to Avoid

### Reimplementing the Solution in Tests

Keep the end-to-end solution in `solution/` (never present in the agent's environment). A test file must not contain a callable function that maps task inputs to the **complete expected artifact** — if it does, the reference implementation can leak (e.g., a partner harness that bundles `tests/`, or a misconfigured image) and it becomes a maintenance/contamination liability.

```python
# BAD: tests/ contains a reusable solver that produces the expected artifact
def compute_expected(inputs):
    ...                                   # the whole task, reimplemented
    return full_expected_output

# GOOD: run the agent's program and grade its output against invariants or a golden fixture
def test_output():
    out = run_agent_binary("data")        # the agent's own program
    assert out["worst_case"] >= FLOOR     # spec-derived invariant
```

Rule of thumb: if deleting `solution/` would still let the test compute the expected answer itself, the test is doing the solving. Running the agent's binary, parsing its output, golden fixtures, and invariants are all fine (see *What a Good Verifier Legitimately Does*).

### Hardcoded Config Inputs (config-driven tasks only)

This applies **only** when the instruction says the agent must read a config/input file that can vary. Then the verifier should read those values from the same config at runtime, so an agent that ignores the config and hardcodes the parameters can't pass.

```python
# BAD (config-driven task): verifier re-declares a value the task says to read from config
assert model.features == ["age", "income", "score"]   # copied from config.json

# GOOD: read the config the task is supposed to honor
cfg = json.load(open("/app/config.json"))
assert model.features == cfg["features"]
```

**Not a ban on hardcoded values.** Hardcoding the expected *result* — exact numeric/ML targets (with tolerance), byte-exact outputs, format constants — is fine and often required. For config-driven tasks, confirm the dependency by **mutating the config and re-running** (the output must change).

### Brittle String Matching

```python
# BAD: Exact string match
def test_output():
    output = open("/output/log.txt").read()
    assert output == "Processing complete\n"

# GOOD: Check for key content
def test_output():
    output = open("/output/log.txt").read()
    assert "complete" in output.lower()
```

### Hardcoded Random Values

```python
# BAD: Assumes specific random output
def test_random():
    result = generate_random()
    assert result == 42

# GOOD: Check properties
def test_random():
    result = generate_random()
    assert 1 <= result <= 100
```

### Order-Dependent Tests

```python
# BAD: Tests depend on execution order
def test_1_setup():
    global data
    data = load_data()

def test_2_process():
    process(data)  # Fails if test_1 didn't run first

# GOOD: Each test is independent
def test_process():
    data = load_data()
    result = process(data)
    assert result is not None
```

## CI Validation

Your tests will be validated by:

| Check | Description |
| --- | --- |
| `behavior_in_tests` | All task requirements have tests |
| `behavior_in_task_description` | All tested behavior is in instruction.md |
| `informative_test_docstrings` | Each test has a docstring |
| `ruff` | Code passes linting |

---

## Next Steps

- [Run oracle agent](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/testing-and-validation/oracle-agent)
- [Review CI checks](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/testing-and-validation/ci-checks-reference)

---

[Previous: Writing Oracle Solution](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/creating-tasks/writing-oracle-solution) · [Next: Oracle Agent](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/testing-and-validation/oracle-agent)
