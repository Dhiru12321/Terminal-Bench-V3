# Systemd Reload Unit Shadow — Hard Regular Task Implementation Plan

## 1. Decision Summary

- **Task title:** Systemd Reload Unit Shadow
- **Folder name:** `systemd-reload-unit-shadow`
- **Task type:** Regular, non-milestone task
- **Primary category:** `system-administration`
- **Subcategories:** `[]`
- **Target difficulty:** `hard`
- **Preferred implementation language:** Go, with Bash for helper scripts and oracle entrypoint
- **Task metadata languages:** `["go", "bash"]`
- **Codebase size:** `small`, with 20+ real files under `environment/` excluding Dockerfile and optional Docker metadata
- **Runtime model:** Single-container only; do not use `docker-compose.yaml`
- **Real systemd dependency:** Do not require real `systemd`, privileged mode, cgroups, or host service control. Implement a local, systemd-style unit manager simulator that uses normal files under `/app`.

This plan converts the seed into a hard system-administration task around a local Go CLI named `unitctl`. The CLI models systemd-style base unit files, drop-ins, generator output, runtime state, reload, restart, and boot replay. The public prompt exposes only observable symptoms, admin commands, output paths, public logs, and durable artifacts. The causal bug stays discoverable through source inspection and command behavior.

## 2. Source Alignment

The plan follows these Terminus constraints:

- Use the **regular task skeleton** with root-level `instruction.md`, `task.toml`, `environment/`, `solution/`, and `tests/`.
- Keep `instruction.md` concise, realistic, well specified, and limited to absolute paths.
- Avoid hints such as the stale authority, exact lookup path, exact patch file, helper/table name, or generation edge.
- Use a safe Docker environment: no privileged mode, no real systemd control, no host mounts, no `/var/run/docker.sock`, no copied tests or solution, no runtime web access.
- Make the task hard through real engineering complexity: multi-file discovery, stateful reload/restart behavior, conflicting config surfaces, durable artifacts, and anti-hardcoding tests.
- Verify only final behavior and artifact consistency, not source patterns.
- Ensure `tests/test.sh` always writes `/logs/verifier/reward.txt` with binary `0` or `1`.
- Keep the implementation self-contained and reproducible.

## 3. Task Concept

Build a small Go service-management tool that behaves like a minimal systemd-style unit manager for local fixtures. It has unit files and drop-in directories under a fake root such as `/app/sandbox`. The manager supports commands such as:

```bash
/app/bin/unitctl apply /app/scenarios/reload-shadow.json --root /app/sandbox
/app/bin/unitctl daemon-reload --root /app/sandbox
/app/bin/unitctl restart web-gateway.service --root /app/sandbox
/app/bin/unitctl boot-replay --root /app/sandbox
/app/bin/unitctl status --root /app/sandbox --json
```

The visible failure is that a reload reports that a new drop-in has been accepted, but later durable status and boot replay can still show an older interpretation. The agent must fix the implementation so live status, generated status JSON, public logs, and replay traces agree after reload, restart, and repeated reruns.

The system should feel realistic: a fleet operator installed a new drop-in, ran a reload, restarted the unit, saw a green reload log entry, but the next boot replay used stale service settings. The bug is in the manager's state handling, not in the test fixture.

## 4. Public `instruction.md` Draft

Keep this as the complete public contract. Do not add a hints section.

```md
The unit manager in `/app` reports a successful reload after new systemd-style drop-ins are installed, but the generated status under `/app/var/status` and the next boot replay can still reflect an older interpretation. Fix the implementation so `/app/bin/unitctl apply /app/scenarios/reload-shadow.json --root /app/sandbox`, `/app/bin/unitctl daemon-reload --root /app/sandbox`, `/app/bin/unitctl restart web-gateway.service --root /app/sandbox`, and `/app/bin/unitctl boot-replay --root /app/sandbox` agree across the live status, public log, and regenerated artifacts after repeated runs.

Do not replace fixture data or write static outputs. The durable artifacts are `/app/var/status/effective-units.json`, `/app/var/log/unitctl.log`, and `/app/var/traces/reload-trace.jsonl`. The status JSON must contain a `units` object keyed by unit name; each unit entry must include `exec_start`, `environment`, `restart_policy`, `dropins`, `provenance`, and `generation`. Trace rows must include `event`, `unit`, `generation`, `selected`, and `surfaces`, and the artifacts must explain the config surfaces used for conflicting cases.
```

### Why this prompt is safe

- It names the observable admin workflow and output schema.
- It uses only absolute paths.
- It does not name the stale state holder, lookup path, broken layer, patch file, or exact precedence table.
- It forbids static artifact writes without instructing the exact implementation.
- It makes artifact schemas public so tests will not enforce hidden format requirements.

## 5. Private Authoring-Only Bug Design

Do not leak this section into `instruction.md`.

The intended root cause should be split across multiple modules. A reload path accepts new disk drop-ins and increments a generation marker, but restart/export/replay code can still consult an older runtime interpretation. The public log says reload succeeded because parsing worked, while the durable status and boot replay are built from a different state surface.

Implement the broken starter state with at least three coupled defects:

1. **Live reload and durable export are inconsistent.** Reload updates an in-memory unit view but the status exporter reads a persisted runtime snapshot that was not invalidated.
2. **Restart and boot replay disagree after repeated reruns.** Restart uses current parsed files in some cases, while boot replay restores the older generated snapshot if it exists.
3. **Provenance is misleading.** The trace writer emits the accepted drop-in path but attaches selected values from the stale runtime view.

The honest solution should unify effective unit resolution for all command paths and make generated artifacts derive from the same resolved unit object. It should not be solvable by editing one literal table or changing one hardcoded path.

## 6. Required Codebase Shape

Use a Go module with a realistic multi-package layout. Keep names ordinary and domain-specific; avoid obvious challenge names like `shadow`, `stale_authority`, `broken_precedence`, or `fix_table` in code.

Suggested `environment/` layout:

```text
environment/
├── .dockerignore
├── Dockerfile
├── app/
│   ├── Makefile
│   ├── go.mod
│   ├── go.sum                    # omit only if no third-party deps are used
│   ├── cmd/
│   │   └── unitctl/
│   │       └── main.go
│   ├── internal/
│   │   ├── command/
│   │   │   ├── apply.go
│   │   │   ├── boot.go
│   │   │   ├── reload.go
│   │   │   ├── restart.go
│   │   │   ├── root.go
│   │   │   └── status.go
│   │   ├── unit/
│   │   │   ├── model.go
│   │   │   ├── parser.go
│   │   │   ├── dropin.go
│   │   │   └── validate.go
│   │   ├── catalog/
│   │   │   ├── scan.go
│   │   │   ├── layer.go
│   │   │   ├── stack.go
│   │   │   ├── merge.go
│   │   │   └── paths.go
│   │   ├── runtime/
│   │   │   ├── generation.go
│   │   │   ├── journal.go
│   │   │   ├── session.go
│   │   │   └── snapshot.go
│   │   ├── export/
│   │   │   ├── status.go
│   │   │   ├── trace.go
│   │   │   └── log.go
│   │   ├── scenario/
│   │   │   ├── apply.go
│   │   │   ├── manifest.go
│   │   │   └── seed.go
│   │   └── fsutil/
│   │       ├── atomic.go
│   │       └── checksum.go
│   ├── configs/
│   │   ├── vendor/web-gateway.service
│   │   ├── vendor/metrics-agent.service
│   │   ├── etc/systemd/system/web-gateway.service.d/20-network.conf
│   │   ├── etc/systemd/system/web-gateway.service.d/40-reload.conf
│   │   ├── run/systemd/system/web-gateway.service.d/10-runtime.conf
│   │   ├── run/systemd/generator/web-gateway.service.d/30-generated.conf
│   │   └── env/web-gateway.env
│   ├── scenarios/
│   │   ├── reload-shadow.json
│   │   ├── runtime-drop-removed.json
│   │   └── replay-after-reload.json
│   └── docs/
│       └── unitctl-format.md
```

This is more than 20 task-relevant environment files without padding. The agent must inspect source packages, configs, scenarios, logs, and generated artifacts.

## 7. Go CLI Behavior to Implement

### Commands

- `apply <scenario> --root <path>`
  - Copies a deterministic scenario into the fake root.
  - Clears only documented generated directories for that root.
  - Seeds public logs and runtime journals needed for reproduction.

- `daemon-reload --root <path>`
  - Reads base unit files and drop-ins under the fake root.
  - Refreshes the effective unit view.
  - Regenerates `/app/var/status/effective-units.json` and appends trace rows.

- `restart <unit> --root <path>`
  - Uses the effective unit view for the specified unit.
  - Writes a public log entry that includes the unit, generation, selected settings, and contributing surfaces.
  - Must not resurrect old runtime-only values after reload.

- `boot-replay --root <path>`
  - Reconstructs manager state from durable files after a simulated boot.
  - Must produce the same effective values as the reload/restart workflow.
  - Must be idempotent.

- `status --root <path> --json`
  - Prints the same status data written to `/app/var/status/effective-units.json`.

### Artifact schema

`/app/var/status/effective-units.json`:

```json
{
  "root": "/app/sandbox",
  "generation": 3,
  "units": {
    "web-gateway.service": {
      "exec_start": "/usr/local/bin/web-gateway --mode=current",
      "environment": {
        "FEATURE_FLAG": "reload-safe",
        "PORT": "8088"
      },
      "restart_policy": "on-failure",
      "dropins": [
        "/app/sandbox/etc/systemd/system/web-gateway.service.d/20-network.conf",
        "/app/sandbox/etc/systemd/system/web-gateway.service.d/40-reload.conf"
      ],
      "provenance": [
        {"field": "exec_start", "surface": "etc-dropin", "path": "..."}
      ],
      "generation": 3
    }
  }
}
```

`/app/var/traces/reload-trace.jsonl` row:

```json
{"event":"reload","unit":"web-gateway.service","generation":3,"selected":{"restart_policy":"on-failure"},"surfaces":[{"name":"vendor","path":"..."},{"name":"etc-dropin","path":"..."}]}
```

The exact field values should be generated from input fixtures and scenarios, not copied from fixed expected output files.

## 8. Starter Failure Cases

Design the initial broken project so these behaviors fail before the oracle fix:

1. **Reload accepted but status stale:**
   - `daemon-reload` logs the new drop-in path.
   - `effective-units.json` still contains an older `exec_start` or environment value.

2. **Restart green but boot replay stale:**
   - `restart web-gateway.service` logs the current generation.
   - `boot-replay` rebuilds status from a previous runtime snapshot.

3. **Runtime drop-in removed but resurrected:**
   - Scenario removes `/run`-style runtime override.
   - Repeated reload/restart reintroduces the deleted runtime value from durable state.

4. **Provenance mismatch:**
   - Trace rows list the new drop-in in `surfaces`.
   - `selected` field values come from the older layer.

5. **Rerun mutation hazard:**
   - Running the admin sequence twice changes evidence in the broken implementation, making the second run appear cleaner than the first. Correct behavior should be idempotent.

## 9. Expected Correct Fix Characteristics

The correct fix should:

- Resolve each unit's effective settings from the current fake root state on every reload/restart/replay path.
- Ensure status JSON, status CLI output, log entries, and trace JSONL rows are emitted from the same resolved data model.
- Make generation handling monotonic and deterministic without relying on wall-clock time.
- Avoid stale durable state after runtime overrides are removed or disk drop-ins change.
- Preserve existing parse validation and malformed-unit error behavior.
- Make repeated `apply`, `daemon-reload`, `restart`, and `boot-replay` runs converge to the same artifacts.
- Keep provenance explainable without adding verdict-style booleans such as `passed`, `is_correct`, or `expected_match`.

Do not make the oracle fix a one-line reorder in a visible table. A strong implementation will touch command flow, state refresh, artifact generation, and provenance emission.

## 10. `task.toml` Draft

```toml
version = "2.0"

[metadata]
author_name = "anonymous"
author_email = "anonymous"
difficulty = "hard"
category = "system-administration"
subcategories = []
number_of_milestones = 0
codebase_size = "small"
languages = ["go", "bash"]
tags = ["systemd", "reload", "configuration", "state-recovery", "service-management"]
expert_time_estimate_min = 180
junior_time_estimate_min = 360

[agent]
timeout_sec = 1800.0

[verifier]
timeout_sec = 600.0

[environment]
build_timeout_sec = 900.0
cpus = 2
memory_mb = 4096
storage_mb = 10240
allow_internet = false
```

Notes:

- Do not use `minimal` for `codebase_size`.
- Do not add `custom_docker_compose` or `is_multi_container` because this plan is single-container.
- Do not list Python in `languages`; Python is only verifier tooling, not task implementation.

## 11. Docker Plan

Use one digest-pinned Go base image. Resolve and commit the actual digest when creating the task; do not leave a placeholder in the submitted Dockerfile.

Example shape:

```dockerfile
FROM golang:1.24.2-bookworm@sha256:<resolve-and-commit-real-digest>

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        make \
        tmux \
        asciinema \
        python3 \
        python3-pip \
    && rm -rf /var/lib/apt/lists/*

COPY app/ /app/
RUN python3 -m pip install --break-system-packages --no-cache-dir \
        pytest==8.4.1 \
        pytest-json-ctrf==0.3.5 \
    && go test ./... \
    && go build -trimpath -o /app/bin/unitctl ./cmd/unitctl

ENV PATH="/app/bin:${PATH}"
```

`.dockerignore` must exclude:

```text
.git
__pycache__/
.pytest_cache/
.venv/
node_modules/
solution/
tests/
logs/
*.tmp
```

Docker constraints:

- No privileged mode.
- No `docker-compose.yaml`.
- No runtime network requirement.
- No copying `solution/` or `tests/` into the image.
- No reserved directory creation or modification for `/tests`, `/solution`, or `/oracle`.
- Keep build context under 100 MB and avoid large datasets.

## 12. Verifier Design

Use `tests/test.sh` and `tests/test_outputs.py`.

### `tests/test.sh`

```bash
#!/usr/bin/env bash
set -uo pipefail

if [ "$PWD" = "/" ]; then
    echo "Error: No working directory set. Please set a WORKDIR in your Dockerfile before running this script."
    mkdir -p /logs/verifier
    echo 0 > /logs/verifier/reward.txt
    exit 0
fi

mkdir -p /logs/verifier
python3 -m pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA
rc=$?

if [ "$rc" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
```

### Test cases to implement

1. `test_reload_restart_and_boot_replay_share_effective_unit`
   - Creates a fresh temp fake root.
   - Runs `unitctl apply`, `daemon-reload`, `restart`, and `boot-replay`.
   - Parses status JSON, log lines, and trace JSONL.
   - Asserts that all three artifacts report the same effective settings for `web-gateway.service`.

2. `test_repeated_admin_sequence_is_idempotent`
   - Runs the same sequence twice.
   - Normalizes trace ordering and generation fields where appropriate.
   - Asserts stable effective unit state and no duplicate stale provenance entries.

3. `test_removed_runtime_dropin_does_not_reappear`
   - Uses a verifier-created scenario where a runtime override exists at first and is then removed before reload.
   - Asserts that restart and boot replay do not resurrect the removed runtime value.

4. `test_conflict_trace_lists_surfaces_without_boolean_verdicts`
   - Creates conflicting vendor, generated, runtime, and disk drop-in values.
   - Asserts trace rows contain all observed surfaces and selected values.
   - Rejects verdict-restating fields such as `passed`, `expected`, `is_correct`, or `matches_test`.

5. `test_static_artifact_replacement_does_not_pass`
   - Runs two distinct temp-root scenarios with different unit names and values.
   - Asserts outputs differ according to inputs and still satisfy schema/invariants.
   - This blocks hardcoded `/app/var/status/effective-units.json` replacements.

6. `test_existing_parse_errors_remain_errors`
   - Feeds a malformed drop-in with invalid section or missing field.
   - Asserts the CLI returns nonzero and does not update durable artifacts.

7. `test_status_cli_matches_written_status_file`
   - Runs `unitctl status --json` and compares parsed JSON to `/app/var/status/effective-units.json`.

Test style rules:

- Use temp directories for verifier-created roots.
- Do not derive expected values from mutable agent-edited expected-output files.
- Avoid source-code grepping.
- Avoid exact full-log string matching; parse JSON and check semantic fields.
- Use deterministic generation values, no sleeps or wall-clock assertions.
- Give every pytest test an informative docstring.

## 13. Oracle Solution Plan

`solution/solve.sh` should be Bash and deterministic:

```bash
#!/usr/bin/env bash
set -euo pipefail
cd /app

# Apply source patches with cat/sed/perl or patch files stored under solution/.
# Rebuild and run the public workflow.
go test ./...
go build -trimpath -o /app/bin/unitctl ./cmd/unitctl
/app/bin/unitctl apply /app/scenarios/reload-shadow.json --root /app/sandbox
/app/bin/unitctl daemon-reload --root /app/sandbox
/app/bin/unitctl restart web-gateway.service --root /app/sandbox
/app/bin/unitctl boot-replay --root /app/sandbox
/app/bin/unitctl status --root /app/sandbox --json >/tmp/unitctl-status.json
```

The oracle implementation should patch the Go source, not write final JSON artifacts directly. Good oracle changes include:

- One central effective-unit resolution object shared by reload, restart, boot replay, status, trace, and log writers.
- Durable snapshot invalidation or refresh when reload observes changed unit/drop-in inputs.
- Deterministic generation increments based on state transition count or content digest, not wall-clock time.
- Trace generation from the same resolved object used by status export.
- Preservation of existing validation tests and malformed config behavior.

Avoid these oracle anti-patterns:

- Echoing expected JSON into `/app/var/status/effective-units.json`.
- Deleting fixtures or scenarios.
- Disabling parts of the CLI.
- Special-casing `web-gateway.service` only.
- Using network access, sleeps, random values, or host-specific state.

## 14. Hardness Calibration

This task should be hard because a successful agent must:

- Discover command behavior by running `unitctl` workflows and inspecting generated logs/artifacts.
- Synthesize across CLI command flow, unit parsing, config scanning, runtime journals, snapshot replay, and artifact export.
- Diagnose a symptom that appears successful at reload time but fails after restart or boot replay.
- Navigate coupling: changing only reload can break boot replay; changing only status can leave logs and traces inconsistent.
- Reason about system-administration concepts such as systemd-style unit files, drop-ins, runtime vs disk state, generator output, daemon reload, restart, and durable state.

The task should not be hard because of vague wording, hidden required output fields, flaky timing, missing dependencies, or unavailable real systemd behavior.

## 15. Anti-Collapse Rules

Do not do any of the following in `instruction.md`:

- Name the stale state holder.
- Name the exact broken file or helper.
- Provide the complete config-surface precedence table.
- Say which command path has the wrong source of truth.
- Say “invalidate the runtime snapshot” or equivalent patch guidance.
- List exact expected field values for each scenario.
- Include the task name as a heading or first-line canary.

Do include:

- The admin commands.
- Absolute output paths.
- Artifact schema.
- Observable requirement that reload, restart, boot replay, status JSON, log, and trace agree.
- Requirement that repeated runs are safe and static outputs are rejected.

## 16. Rubric Draft

Use this in the submission UI, not inside the task directory.

```text
Agent diagnoses the reload/restart/boot replay mismatch by inspecting command behavior, logs, traces, and generated status artifacts, +5
Agent updates the implementation so status JSON, status CLI output, public logs, and trace rows derive from the same effective unit state, +5
Agent handles changed disk drop-ins and removed runtime drop-ins without resurrecting stale values after reload or boot replay, +5
Agent preserves existing unit parsing and validation behavior for malformed configs, +3
Agent makes the admin workflow idempotent across repeated apply, reload, restart, and boot replay runs, +3
Agent rebuilds and verifies the Go CLI after source changes, +2
Agent hardcodes scenario names, unit names, or expected artifact values instead of computing from inputs, -5
Agent edits or deletes fixture/scenario data to hide the reload inconsistency, -5
Agent writes static generated artifacts without fixing command behavior, -5
Agent introduces nondeterministic timing, sleeps, randomness, or host-specific assumptions, -3
Agent bypasses validation by disabling parser errors or making malformed configs silently pass, -3
```

Positive total: 23 points. Negative criteria: 5 distinct penalties.

## 17. Submission Validation Checklist

Before submitting, verify:

- [ ] `instruction.md` is 2–3 concise paragraphs, uses absolute paths, and contains no hints.
- [ ] `instruction.md` does not contain the task folder/name as a heading.
- [ ] The task has regular non-milestone structure.
- [ ] `task.toml` uses `difficulty = "hard"`, `category = "system-administration"`, `codebase_size = "small"`, and `languages = ["go", "bash"]`.
- [ ] `environment/` has 20+ real files excluding Dockerfile/compose metadata.
- [ ] Docker base image is digest-pinned with a real sha256 digest.
- [ ] Dockerfile installs `tmux` and `asciinema`.
- [ ] Dockerfile does not copy or create `/tests`, `/solution`, or `/oracle`.
- [ ] `.dockerignore` excludes `solution/`, `tests/`, caches, and secrets.
- [ ] Oracle solution patches source and derives outputs.
- [ ] Oracle passes repeatedly.
- [ ] NOP fails.
- [ ] Tests are behavioral, deterministic, documented, and aligned with the instruction.
- [ ] Tests create at least one verifier-owned scenario to block hardcoding.
- [ ] Tests do not depend on timing, network, real systemd, privileged mode, or host services.

## 18. Final Builder Prompt

Use this prompt to create the actual task directory from the plan:

```text
Create a new Project Terminus regular task named `systemd-reload-unit-shadow` following the attached implementation plan exactly. Use Go and Bash only for the task implementation and metadata languages. Build a single-container, non-privileged local systemd-style unit manager simulator under `/app` with the `unitctl` CLI, fixtures, scenarios, status exports, logs, and JSONL traces described in the plan. Do not use real systemd, Docker Compose, Python application code, privileged capabilities, or runtime network access.

Create all required files: `instruction.md`, `task.toml`, `environment/Dockerfile`, `environment/.dockerignore`, a 20+ file Go codebase under `environment/app`, `solution/solve.sh`, `tests/test.sh`, and `tests/test_outputs.py`. Keep `instruction.md` concise and symptoms-only; do not reveal the stale authority, exact broken file, lookup path, patch rule, or precedence table. The tests must be deterministic behavioral pytest tests that verify reload/restart/boot-replay coherence, idempotent reruns, removed runtime override behavior, trace provenance consistency, static-output hardcoding resistance, malformed config preservation, and status CLI/file agreement. The oracle must patch source code and rebuild `unitctl`, not write static final artifacts.
```
