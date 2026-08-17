# Implementation Plan: Cgroup Freeze Accounting Drift

## 1. Task identity

- **Working task folder:** `cgroup-freeze-accounting-drift`
- **Primary category:** `system-administration`
- **Task type:** regular non-milestone task
- **Target difficulty:** hard
- **Recommended implementation language:** Go for the supervisor/CLI, Bash for replay scripts
- **Do not list Python in `task.toml` languages:** tests may use pytest, but task languages should be `go` and `bash`
- **Codebase size:** `small` with 20+ files under `environment/`
- **Core premise:** a local cgroup-slice supervisor simulates service slice migration, reload, freeze/thaw, and child restart behavior using a safe pseudo-cgroup tree under `/app/var/cgroupfs`. After a service is migrated and reloaded, health/status output looks correct, but restarted children inherit stale limits from an old runtime snapshot. The agent must fix the policy/accounting implementation so active slice policy, generated runtime exports, and restarted child limits stay aligned.

This should be a **safe simulation**, not real kernel cgroup manipulation. Do not require `--privileged`, `SYS_ADMIN`, `systemd`, writable `/sys/fs/cgroup`, or host-level service management.

## 2. Why this should be hard

The task should require the agent to reason across several surfaces and state transitions instead of editing one obvious literal:

1. Static slice defaults in `/app/config/slices/*.toml`.
2. Service assignments in `/app/config/services/*.toml`.
3. Drop-in overrides in `/app/config/dropins/*.toml`.
4. Environment override files in `/app/config/env/*.env`.
5. CLI override flags passed to the replay command.
6. Generated runtime snapshots under `/app/var/lib/slice-warden/state/*.json`.
7. Pseudo-cgroup files under `/app/var/cgroupfs/...`.
8. Exported status artifacts under `/app/run/status/`.
9. Supervisor logs under `/app/run/logs/`.

The visible symptom should be misleading: the replay command exits successfully and the parent slice export reports the active target slice, but restarted children still carry limits from the old slice or frozen snapshot. Correctness requires deriving effective policy at the right time, applying it consistently to restarted descendants, and regenerating durable artifacts from state rather than manually writing expected outputs.

## 3. Public vs author-private boundaries

### Publicly visible in `instruction.md`

The public prompt may disclose:

- The app root: `/app`.
- The replay/admin command path.
- The fact that service migration, reload, restart, freeze/thaw, and status export are involved.
- The required durable artifact paths and schemas.
- The observable success condition: active service slices and restarted children must agree after replay/restart.
- The requirement to preserve existing clean-start behavior.

### Keep out of `instruction.md`

Do not disclose:

- The exact stale authority used by the broken implementation.
- The exact source file/function that needs patching.
- A full precedence table in the task prompt.
- A scenario-to-verdict table that maps each fixture to expected values.
- Any phrase like “the runtime snapshot wins incorrectly” or “fix restart.go”.

The agent should discover the root cause from source, local docs, fixtures, logs, and replay traces.

## 4. Suggested user-facing instruction.md

Keep the final `instruction.md` concise. Do not include the task name as a heading.

```md
The supervisor in `/app` is used to migrate services between local slice policies and export their effective capacity state. The provided replay flow reports a healthy migrated service, but after a reload and child restart some exported child limits no longer match the active slice. Fix the implementation so the replay command regenerates consistent status artifacts for clean starts, reloads, migrations, restarts, and freeze/thaw cycles.

After your fix, `/app/bin/slicectl replay --scenario /app/scenarios/migration-reload-freeze.toml --export-dir /app/run/status` should produce `/app/run/status/effective-policy.json`, `/app/run/status/service-tree.json`, and `/app/run/status/replay-trace.jsonl` from the current config/runtime state. The exported JSON must follow the contracts documented under `/app/docs`, and rerunning the replay from the same scenario should be deterministic without manually editing files under `/app/run/status`.
```

This prompt is short, uses absolute paths, gives the observable contract, and does not name the stale authority or exact patch location.

## 5. Repository layout to create

Use a regular non-milestone skeleton:

```text
cgroup-freeze-accounting-drift/
├── instruction.md
├── task.toml
├── environment/
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── go.mod
│   ├── go.sum
│   ├── Makefile
│   ├── cmd/
│   │   └── slicectl/
│   │       └── main.go
│   ├── internal/
│   │   ├── config/
│   │   │   ├── loader.go
│   │   │   ├── loader_test.go
│   │   │   ├── envfile.go
│   │   │   ├── service.go
│   │   │   └── slice.go
│   │   ├── policy/
│   │   │   ├── model.go
│   │   │   ├── resolver.go
│   │   │   ├── resolver_test.go
│   │   │   └── explain.go
│   │   ├── runtime/
│   │   │   ├── state.go
│   │   │   ├── snapshot.go
│   │   │   ├── migrate.go
│   │   │   ├── reload.go
│   │   │   ├── restart.go
│   │   │   ├── freeze.go
│   │   │   └── cgroupfs.go
│   │   ├── replay/
│   │   │   ├── scenario.go
│   │   │   ├── runner.go
│   │   │   ├── events.go
│   │   │   └── trace.go
│   │   └── export/
│   │       ├── effective_policy.go
│   │       ├── service_tree.go
│   │       └── jsonl.go
│   ├── config/
│   │   ├── slices/batch.toml
│   │   ├── slices/latency.toml
│   │   ├── slices/frozen-maintenance.toml
│   │   ├── services/api-ingest.toml
│   │   ├── services/report-worker.toml
│   │   ├── dropins/api-ingest.override.toml
│   │   └── env/replay.env
│   ├── docs/
│   │   ├── operator-contract.md
│   │   ├── status-schema.md
│   │   └── replay-scenarios.md
│   ├── scenarios/
│   │   ├── clean-start.toml
│   │   ├── migration-reload-freeze.toml
│   │   ├── env-cli-conflict.toml
│   │   └── restart-after-restore.toml
│   └── scripts/
│       ├── build.sh
│       ├── replay.sh
│       ├── reset-state.sh
│       └── smoke.sh
├── solution/
│   └── solve.sh
└── tests/
    ├── test.sh
    └── test_outputs.py
```

This gives the agent at least 30 meaningful environment files and forces discovery across source, config, docs, scenarios, and generated runtime state.

## 6. Application behavior design

### CLI

Build a single binary at `/app/bin/slicectl`.

Recommended commands:

```bash
/app/bin/slicectl replay --scenario /app/scenarios/migration-reload-freeze.toml --export-dir /app/run/status
/app/bin/slicectl replay --scenario /app/scenarios/clean-start.toml --export-dir /app/run/status
/app/bin/slicectl inspect --service api-ingest --state-dir /app/var/lib/slice-warden/state
/app/bin/slicectl reset --state-dir /app/var/lib/slice-warden/state --cgroup-root /app/var/cgroupfs
```

The replay command should execute scenario events such as:

- `load_config`
- `restore_runtime_state`
- `migrate_service`
- `reload_policy`
- `freeze_service`
- `restart_child`
- `thaw_service`
- `export_status`

### Pseudo-cgroup tree

Represent pseudo-cgroup files as normal files:

```text
/app/var/cgroupfs/slices/batch.slice/cpu.weight
/app/var/cgroupfs/slices/batch.slice/memory.max
/app/var/cgroupfs/slices/latency.slice/cpu.weight
/app/var/cgroupfs/slices/latency.slice/memory.max
/app/var/cgroupfs/services/api-ingest/children/worker-1/cpu.weight
/app/var/cgroupfs/services/api-ingest/children/worker-1/memory.max
/app/var/cgroupfs/services/api-ingest/freezer.state
```

Keep all paths under `/app`; never touch host `/sys/fs/cgroup`.

### Status artifacts

`effective-policy.json` should be generated, not static. Suggested schema:

```json
{
  "schema_version": 1,
  "scenario": "migration-reload-freeze",
  "services": [
    {
      "service": "api-ingest",
      "active_slice": "latency.slice",
      "freezer_state": "thawed",
      "effective": {
        "cpu_weight": 420,
        "memory_max_bytes": 268435456,
        "io_weight": 180
      },
      "children": [
        {
          "id": "worker-1",
          "slice": "latency.slice",
          "cpu_weight": 420,
          "memory_max_bytes": 268435456,
          "started_from": "restart"
        }
      ],
      "explain": [
        {
          "surface": "config-file",
          "path": "/app/config/slices/latency.toml",
          "keys": ["cpu_weight", "memory_max_bytes", "io_weight"]
        }
      ]
    }
  ]
}
```

Avoid a field like `passed: true` or `verdict: correct`, because that restates test outcomes instead of exporting useful system state.

`service-tree.json` should summarize the slice/service/child hierarchy and limits.

`replay-trace.jsonl` should include one JSON event per action, with fields such as:

```json
{"event":"reload_policy","service":"api-ingest","active_slice":"latency.slice","sequence":4}
{"event":"restart_child","service":"api-ingest","child":"worker-2","active_slice":"latency.slice","sequence":5}
```

Do not require exact string equality in tests; parse JSON and check fields/invariants.

## 7. Intentional broken implementation

The broken code should pass simple smoke tests and clean-start scenarios, but fail only when multiple surfaces interact.

### Broken behavior to seed

1. Clean start applies the service’s initial slice correctly.
2. Migration updates the service-level active slice export correctly.
3. Reload refreshes parent slice export correctly.
4. Freeze/thaw logs look healthy.
5. **Restarted children after reload/freeze inherit stale limits from a previous runtime snapshot or pre-migration parent.**
6. The trace records a restart event, but the exported child limits are inconsistent with the active slice.
7. A second replay may appear idempotent if only top-level service fields are inspected, but child state remains wrong.

### Author-private likely patch areas

Use these as implementation notes only; do not reveal them in `instruction.md`.

- `internal/runtime/restart.go`: restart path should resolve current effective policy at restart time, not reuse cached child limits.
- `internal/runtime/snapshot.go`: snapshot restore should mark runtime-derived values as historical unless the current scenario explicitly makes them active.
- `internal/policy/resolver.go`: resolver should merge public surfaces consistently and produce traceable explanations.
- `internal/export/effective_policy.go`: exporter should serialize child state from the same effective policy used to write pseudo-cgroup files.

The oracle should apply a real source fix in these areas. It must not simply rewrite expected JSON artifacts.

## 8. Configuration and scenario details

### Slice defaults

Use realistic but small deterministic values:

`batch.slice`:

```toml
name = "batch.slice"
cpu_weight = 120
memory_max_bytes = 134217728
io_weight = 80
freeze_accounting = "defer"
```

`latency.slice`:

```toml
name = "latency.slice"
cpu_weight = 420
memory_max_bytes = 268435456
io_weight = 180
freeze_accounting = "current"
```

`frozen-maintenance.slice`:

```toml
name = "frozen-maintenance.slice"
cpu_weight = 60
memory_max_bytes = 67108864
io_weight = 40
freeze_accounting = "hold"
```

### Service config

`api-ingest.toml` starts in `batch.slice`, has two children, and allows migration to `latency.slice`.

### Scenario: migration-reload-freeze

The scenario should include:

1. Reset pseudo-cgroup and runtime state.
2. Start `api-ingest` in `batch.slice` with child `worker-1`.
3. Export status once.
4. Freeze `api-ingest`.
5. Migrate `api-ingest` to `latency.slice`.
6. Reload policy from config/drop-in/env surfaces.
7. Restart child `worker-2` while the service has restored freeze accounting state.
8. Thaw.
9. Export status.

The failing artifact should show the service active on `latency.slice` while `worker-2` still has `batch.slice` limits or old memory/cpu values.

### Scenario: env-cli-conflict

This scenario strengthens the config-policy-precedence profile without making the prompt a table transcription exercise. Put the detailed rules in `/app/docs/operator-contract.md`; the public instruction only says to follow docs. The test should verify the behavior under a new conflict combination not identical to the visible scenario.

## 9. Tests to implement

Use pytest in `tests/test_outputs.py`, but keep task metadata languages as Go/Bash.

### Test 1: replay produces required artifacts and schemas

- Run `/app/scripts/reset-state.sh`.
- Run `/app/bin/slicectl replay --scenario /app/scenarios/migration-reload-freeze.toml --export-dir /app/run/status`.
- Assert the three required files exist.
- Parse JSON/JSONL.
- Verify required fields and types.
- Verify no artifact has verdict-style fields such as `passed`, `expected`, or `test_ok`.

### Test 2: migrated restarted children inherit active slice limits

- Use `migration-reload-freeze.toml`.
- Load the active slice from `effective-policy.json`.
- Load child limits from `service-tree.json`.
- Assert every restarted child under `api-ingest` has the same slice and effective limits as the active service policy.
- Compute expected values from config/docs/scenario copies in the test fixture, not from a hardcoded exported result.

### Test 3: freeze accounting is not double-counted across restart/thaw

- Verify freeze/thaw sequence in `replay-trace.jsonl`.
- Assert final `freezer_state` is `thawed`.
- Assert capacity/accounting totals equal the current active children only once.
- Do not use sleeps or real process timing.

### Test 4: clean-start behavior remains compatible

- Run `clean-start.toml`.
- Assert a service that never migrates still gets its default slice policy.
- Assert existing top-level fields and schema remain stable.

### Test 5: env/CLI/config conflict case is derived, not hardcoded

- Tests should create or copy a temporary scenario under `/tmp/verifier-scenarios/` that combines config, env, and CLI overrides differently from the public scenario.
- Run replay against that verifier scenario.
- Assert effective policy follows the documented contract.
- This blocks solutions that hardcode only `api-ingest` and `migration-reload-freeze.toml`.

### Test 6: deterministic replay and regenerated artifacts

- Run reset + replay twice for the same scenario.
- Canonicalize JSON object key order in the test and compare semantic equality.
- Verify trace sequence numbers are stable.
- Verify artifacts are regenerated after deleting `/app/run/status`.

### Test 7: anti-dummy-program behavior

- Run at least two scenarios and inspect real pseudo-cgroup files under `/app/var/cgroupfs`.
- Ensure exported JSON matches pseudo-cgroup file values.
- This prevents replacing `slicectl` with a script that writes static JSON only.

## 10. `tests/test.sh` requirements

Use the canonical reward pattern:

```bash
#!/bin/bash
set -uo pipefail

if [ "$PWD" = "/" ]; then
    echo "Error: No working directory set. Please set a WORKDIR in your Dockerfile before running this script."
    mkdir -p /logs/verifier
    echo 0 > /logs/verifier/reward.txt
    exit 0
fi

mkdir -p /logs/verifier
python -m pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA
rc=$?

if [ "$rc" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
```

Install `pytest` and `pytest-json-ctrf` in the Docker image at build time. Do not install anything in `test.sh`.

## 11. Oracle solution plan

`solution/solve.sh` should be deterministic and fail fast:

```bash
#!/usr/bin/env bash
set -euo pipefail
cd /app

go test ./...
/app/scripts/build.sh
/app/scripts/reset-state.sh
/app/bin/slicectl replay --scenario /app/scenarios/migration-reload-freeze.toml --export-dir /app/run/status || true

# Apply source fixes, for example with perl/sed or cat > patched files.
# The patch should update the Go implementation, not generated output artifacts.

go test ./...
/app/scripts/build.sh
/app/scripts/reset-state.sh
/app/bin/slicectl replay --scenario /app/scenarios/migration-reload-freeze.toml --export-dir /app/run/status
/app/scripts/reset-state.sh
/app/bin/slicectl replay --scenario /app/scenarios/clean-start.toml --export-dir /app/run/status
```

The oracle should:

- Patch the policy/restart/export logic.
- Rebuild `/app/bin/slicectl`.
- Run local unit tests and replay commands.
- Avoid writing `/app/run/status/*.json` directly except through the CLI.
- Avoid modifying `/tests`, `/solution`, `/oracle`, or hidden verifier data.

## 12. Dockerfile plan

Use a digest-pinned sanctioned base image. Example shape:

```dockerfile
FROM golang:1.22-bookworm@sha256:<digest>

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

COPY requirements-verifier.txt /tmp/requirements-verifier.txt
RUN pip3 install --break-system-packages --no-cache-dir -r /tmp/requirements-verifier.txt

COPY go.mod go.sum ./
RUN go mod download

COPY . /app/
RUN /app/scripts/build.sh

ENV PATH="/app/bin:${PATH}"
```

Notes:

- Replace `<digest>` with a real digest before submission.
- Do not use `latest`.
- Do not copy parent-level `tests/` or `solution/` into the image.
- Keep `requirements-verifier.txt` in `environment/`, pinned to exact versions, for example `pytest==8.3.4` and `pytest-json-ctrf==0.3.5` or the version available in your environment.
- Add `.dockerignore` excluding `.git`, caches, build outputs, `solution/`, `tests/`, and secrets.

## 13. task.toml plan

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
tags = ["cgroups", "supervisor", "configuration", "state-replay", "service-restart"]
expert_time_estimate_min = 120
junior_time_estimate_min = 240

[verifier]
timeout_sec = 450.0

[agent]
timeout_sec = 1200.0

[environment]
build_timeout_sec = 900.0
cpus = 2
memory_mb = 4096
storage_mb = 10240
allow_internet = false
```

Do not use `minimal` for `codebase_size`. Use `small` because the task should include 20+ files in `environment/`.

## 14. Hardness strengthening checklist

- The public prompt does not reveal the exact patch file.
- Visible scenario fails in a way that looks like a successful migration unless child state is inspected.
- Hidden verifier scenario changes the conflict shape to prevent hardcoding.
- Tests inspect both generated artifacts and pseudo-cgroup files.
- Tests cover clean start, reload, migration, restart, and freeze/thaw.
- The same verifier logic is used for oracle and agent runs.
- No latency, sleeps, process races, or real kernel cgroup dependencies.
- Ground truth is computed from verifier-owned scenario/config copies or documented contracts, not mutable agent outputs.
- The oracle patches source code and rebuilds; it does not write final artifacts directly.

## 15. Anti-cheating plan

- Do not include hidden expected JSON outputs in `/app`.
- Do not copy `tests/` or `solution/` into the Docker image.
- Verifier creates at least one temporary scenario not present in `/app/scenarios`.
- Verifier checks pseudo-cgroup files and exported JSON for consistency.
- Verifier deletes `/app/run/status` between runs to ensure artifacts are regenerated.
- Verifier should not rely on exact source-code grep patterns.
- Agent-visible docs can describe the contract, but tests should use different concrete combinations.

## 16. Local validation workflow

Run these before submission:

```bash
harbor run -a oracle -p cgroup-freeze-accounting-drift
harbor run -a nop -p cgroup-freeze-accounting-drift
harbor run -a oracle -p cgroup-freeze-accounting-drift -v
```

Expected:

- Oracle passes consistently.
- NOP fails.
- No reward file errors.
- No runtime internet access required.
- No privileged-mode requirement.
- Agent failures, if tested, should be due to incomplete cross-surface reasoning, not broken environment setup.

## 17. Reviewer-risk notes

Likely reviewer concerns and how to avoid them:

| Risk | Avoidance |
|---|---|
| Prompt leak reveals exact stale state source | Keep `instruction.md` symptoms-only and refer to `/app/docs` for contracts. |
| Hidden tests enforce phantom behavior | Ensure every invariant is described in `instruction.md` or `/app/docs`. |
| Real cgroup/systemd requirements need privilege | Use pseudo-cgroup files under `/app/var/cgroupfs`. |
| Tests are table transcription | Use scenario-generated expectations and cross-artifact invariants. |
| Static artifact hardcoding passes | Run multiple scenarios, delete outputs, and compare pseudo-cgroup state. |
| Flaky concurrency/restart tests | Make replay events deterministic and sequential; no sleeps. |
| `minimal` metadata rejection | Use `codebase_size = "small"` and include 20+ environment files. |

## 18. Suggested rubric for submission UI

```text
Agent diagnoses the inconsistency between active service policy, restarted child state, pseudo-cgroup files, and exported status artifacts, +5
Agent fixes the replay/restart path so migrated children inherit the current effective slice policy after reload and freeze/thaw, +5
Agent preserves clean-start behavior for services that never migrate or reload, +3
Agent regenerates status artifacts through the CLI/export pipeline instead of manually writing expected JSON, +3
Agent validates the fix with multiple replay scenarios and source-level unit tests before finishing, +2
Agent hardcodes the visible scenario, service name, or expected exported values instead of deriving policy from config/runtime state, -5
Agent edits verifier, solution, oracle, or reserved framework directories to pass the task, -5
Agent introduces privileged host cgroup/systemd dependencies or touches `/sys/fs/cgroup`, -5
Agent removes trace/explainability fields or weakens schema output to hide inconsistent child state, -3
Agent fixes only the top-level active slice export while restarted child limits remain stale, -3
```

Positive total: 18 points. Negative criteria: 5 distinct penalties.

## 19. Final implementation summary

Create a Go/Bash regular system-administration task where a safe local slice supervisor mishandles cgroup-like policy after migration, reload, freeze/thaw, and child restart. The agent sees only the operational symptom and durable artifact contract. The real challenge is discovering and fixing cross-surface policy derivation so active service state, restarted children, pseudo-cgroup files, replay traces, and JSON exports all agree across clean and replayed workflows.
