# Implementation Plan: Overlay Journal Vacuum Reappears

## 1. Task Identity

- **Working folder name:** `overlay-journal-vacuum-reappears`
- **Primary category:** `system-administration`
- **Task type:** Regular non-milestone task
- **Target difficulty:** Hard
- **Preferred implementation language:** Go + Bash
- **Alternative languages:** Rust + Bash, C++ + Bash
- **Codebase size:** `small` with 20+ meaningful files under `environment/`
- **Core challenge:** A cleanup command reports success, but a restart/replay path reconstructs deleted overlay-style workload layers from stale durable state.
- **Safety design:** Do not use real kernel overlayfs mounts. Model overlayfs-like layer cleanup and replay in a user-space admin tool so the Docker task does not require `SYS_ADMIN`, privileged mode, or host mounts.

## 2. High-Level User-Facing Scenario

A local overlay-style workload layer manager lives in `/app`. It keeps durable state under `/var/lib/ovlkeeper`, writes public service logs under `/var/log/ovlkeeper`, and exposes an admin CLI at `/app/bin/ovlkeeperctl`.

The visible failure is:

1. An admin vacuums a retired workload.
2. The command exits successfully and the status export shows the retired workload as gone.
3. The service is restarted, replaying durable state.
4. Some deleted workload layers reappear even though the vacuum looked green.

The agent must fix the real implementation so cleanup, replay, restart, and a second rerun are durable and idempotent.

## 3. Public `instruction.md` Draft

Keep this concise and symptom-only. Do not include the task name, stale authority, exact broken source file, or the journal/checkpoint bug.

```md
The overlay layer cleanup tool in `/app` reports a successful vacuum, but deleted workload layers return after the service is restarted from `/var/lib/ovlkeeper`. Fix the implementation so `/app/bin/ovlkeeperctl vacuum --root /var/lib/ovlkeeper --workload retired-api --export /var/lib/ovlkeeper/exports/status.json` followed by `/app/scripts/restart-ovlkeeper.sh` leaves removed workload layers durably removed across repeated replay/restart cycles.

Preserve live workloads and shared layers. Regenerate the status export at `/var/lib/ovlkeeper/exports/status.json`, the replay trace at `/var/lib/ovlkeeper/exports/replay-trace.jsonl`, and the service log at `/var/log/ovlkeeper/service.log` from the fixed tool; do not replace them with static files.
```

Why this works:

- It uses absolute paths.
- It exposes the admin command and restart workflow.
- It names observable artifacts and preservation constraints.
- It does not reveal the stale durable surface, patch location, or replay algorithm.

## 4. Required Repository Layout

Use a regular task skeleton:

```text
overlay-journal-vacuum-reappears/
├── instruction.md
├── task.toml
├── environment/
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── go.mod
│   ├── go.sum
│   ├── Makefile
│   ├── bin/
│   │   └── ovlkeeperctl                 # prebuilt broken binary or build wrapper
│   ├── cmd/
│   │   └── ovlkeeperctl/
│   │       └── main.go
│   ├── internal/
│   │   ├── cli/
│   │   │   ├── args.go
│   │   │   └── commands.go
│   │   ├── config/
│   │   │   ├── config.go
│   │   │   └── defaults.go
│   │   ├── journal/
│   │   │   ├── record.go
│   │   │   ├── reader.go
│   │   │   ├── writer.go
│   │   │   └── compact.go
│   │   ├── layers/
│   │   │   ├── model.go
│   │   │   ├── store.go
│   │   │   ├── lineage.go
│   │   │   └── refs.go
│   │   ├── replay/
│   │   │   ├── recover.go
│   │   │   ├── apply.go
│   │   │   └── trace.go
│   │   ├── status/
│   │   │   ├── export.go
│   │   │   └── validate.go
│   │   ├── vacuum/
│   │   │   ├── planner.go
│   │   │   ├── prune.go
│   │   │   ├── commit.go
│   │   │   └── sweep.go
│   │   └── safeio/
│   │       ├── atomic.go
│   │       └── fsync.go
│   ├── fixtures/
│   │   ├── demo-root/
│   │   │   └── ... initial `/var/lib/ovlkeeper` tree ...
│   │   └── legacy-root/
│   │       └── ... older journal/checkpoint format ...
│   ├── scripts/
│   │   ├── seed-demo-root.sh
│   │   ├── restart-ovlkeeper.sh
│   │   └── show-public-state.sh
│   └── docs/
│       ├── status-schema.md
│       └── admin-workflow.md
├── solution/
│   └── solve.sh
└── tests/
    ├── test.sh
    └── test_outputs.py
```

The exact file names can change, but keep at least 20 files in `environment/` and make the root cause span several packages.

## 5. Initial Environment Design

### Runtime paths inside the container

```text
/app/                               # source code and CLI wrapper
/app/bin/ovlkeeperctl               # admin binary path used in instruction.md
/app/scripts/restart-ovlkeeper.sh   # restart/replay workflow used in instruction.md
/var/lib/ovlkeeper/                 # durable root copied from fixtures at build or container start
/var/lib/ovlkeeper/state/           # active workload/layer manifests
/var/lib/ovlkeeper/layers/          # layer payload directories
/var/lib/ovlkeeper/journal/         # append-only recovery records
/var/lib/ovlkeeper/checkpoints/     # replay checkpoint snapshots
/var/lib/ovlkeeper/exports/         # generated status and trace artifacts
/var/log/ovlkeeper/service.log      # public service log
```

### Workload fixture shape

Create at least three workloads:

1. `retired-api` — the workload the public command vacuums.
2. `billing-worker` — a live workload that shares a lower/base layer with `retired-api`.
3. `search-indexer` — a live workload with an independent layer lineage.

Create at least five layers:

- One shared lower/base layer.
- One retired-only upper layer.
- One retired-only scratch layer.
- One live upper layer for `billing-worker`.
- One independent layer for `search-indexer`.

The vacuum must remove only layers no longer referenced by live workloads. It must not delete the shared base layer.

## 6. Private Bug Design for the Task Author

Do not place this in `instruction.md`.

Seed the code with a replay-safety bug where the visible active state and the durable replay state diverge after vacuum:

- The vacuum path removes layer directories and updates the active workload manifest.
- The status exporter reads the active manifest and therefore reports a green state.
- The restart script calls replay/recover.
- Replay reconstructs part of the retired workload from older durable records because the cleanup commit did not advance or reconcile the replay lineage consistently.
- A second vacuum may appear to fix the demo case but leaves either duplicate deletion records, a stale pending record, or a resurrectable lineage edge.

Good bug locations to distribute across the codebase:

- `internal/vacuum/planner.go` decides which layers are unreferenced.
- `internal/vacuum/commit.go` writes the visible cleanup result.
- `internal/journal/compact.go` compacts or checkpoints durable records.
- `internal/replay/apply.go` applies replay records after restart.
- `internal/status/export.go` emits status artifacts from only one surface.

A correct fix should make the durable replay surface, checkpoint surface, active manifest, and layer directories agree after cleanup and restart.

## 7. Expected Correct Behavior

After the agent fixes the task:

1. Running the visible vacuum command removes the retired workload and its unshared layers.
2. Running `/app/scripts/restart-ovlkeeper.sh` does not resurrect the retired workload or its private layers.
3. Running the same vacuum command a second time is safe and does not change the final state except for allowed timestamp-free trace append semantics.
4. Live workloads remain intact.
5. Shared layers referenced by live workloads remain present.
6. Generated artifacts are produced by the fixed tool, not by static manual writes.
7. Replay trace and status export describe the same durable generation/checkpoint after restart.

## 8. Public Artifact Schemas

Document these in `/app/docs/status-schema.md` and ensure the instruction names the output paths.

### `/var/lib/ovlkeeper/exports/status.json`

```json
{
  "root": "/var/lib/ovlkeeper",
  "generation": 18,
  "workloads": [
    {
      "name": "billing-worker",
      "state": "active",
      "layers": [
        {"id": "base-a", "kind": "lower", "present": true, "refcount": 2},
        {"id": "billing-upper", "kind": "upper", "present": true, "refcount": 1}
      ]
    }
  ],
  "orphans": [],
  "journal": {
    "applied_through": 42,
    "pending_count": 0
  }
}
```

Rules:

- `workloads` sorted by name.
- `layers` sorted by id within each workload.
- `orphans` sorted by id.
- No wall-clock timestamps required.
- The deleted workload must be absent from `workloads` after cleanup and restart.
- Unshared deleted layers must be absent from `/var/lib/ovlkeeper/layers/` and from active status.

### `/var/lib/ovlkeeper/exports/replay-trace.jsonl`

Each line is a JSON object:

```json
{"seq": 41, "generation": 18, "event": "replay.apply", "layer": "billing-upper", "workload": "billing-worker"}
```

Rules:

- `seq` is integer and strictly increasing within a run.
- `generation` is integer and must match the exported final generation.
- Every line must parse as JSON.
- Trace must not mention resurrecting `retired-api` after a successful restart.

## 9. Test Plan

Use behavioral pytest tests. The tests should build the current source, create fresh temporary durable roots, run the public commands, and inspect the filesystem plus generated JSON artifacts.

### `tests/test.sh`

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

### Behavioral tests to implement

1. **Vacuum survives restart**
   - Build `/app/cmd/ovlkeeperctl` to a temp binary.
   - Copy `/app/fixtures/demo-root` to a temp durable root.
   - Run `vacuum --workload retired-api`.
   - Run the restart script against that temp root.
   - Assert `retired-api` is absent from `status.json`.
   - Assert retired-only layer directories are absent.

2. **Shared live layers are preserved**
   - Run the same workflow.
   - Compute expected live layer ids from the fixture before cleanup.
   - Assert shared base and live-only layers still exist.
   - Assert live workloads still reference only present layers.

3. **Replay and status surfaces agree**
   - Parse `status.json` and `replay-trace.jsonl`.
   - Assert final trace generation equals status generation.
   - Assert no pending replay records remain after restart.
   - Assert all JSONL lines are valid and sequence numbers increase.

4. **Second rerun is idempotent**
   - Run vacuum, restart, vacuum, restart.
   - Export normalized status after each restart.
   - Strip allowed append-only trace details if needed.
   - Assert normalized workload/layer state is unchanged.

5. **Legacy checkpoint fixture is repaired**
   - Copy `/app/fixtures/legacy-root` to a temp durable root.
   - The legacy root should contain an older checkpoint format or extra stale replay record.
   - Run the same admin workflow.
   - Assert the same durable invariants hold.

6. **Hardcoding guard variant**
   - In the test, generate a temp root with a different retired workload name, layer ids, and generation numbers using the same documented schema.
   - Run vacuum on that generated root.
   - Assert the fix works without relying on fixture-specific ids.

Avoid source parsing unless absolutely necessary. Prefer black-box CLI behavior.

## 10. Anti-Cheating and Anti-Triviality Guards

- Tests build the binary from source during verification.
- Tests use fresh temp roots instead of only checking the preseeded `/var/lib/ovlkeeper` tree.
- Tests generate at least one variant root dynamically so hardcoded layer ids fail.
- Expected values are computed from generated fixture state, not stored as editable golden outputs.
- The verifier reads no private implementation internals.
- The Docker image must not copy `tests/` or `solution/` into `/app`.
- Generated outputs must be regenerated by CLI commands during tests.
- The public prompt must not mention the exact stale authority or patch file.

## 11. Oracle Solution Plan

`solution/solve.sh` should be deterministic and patch source code, then rebuild and run the visible workflow.

Recommended outline:

```bash
#!/usr/bin/env bash
set -euo pipefail
cd /app

# Apply source edits with cat/perl/sed or a patch embedded in solve.sh.
# Rebuild the admin CLI.
make build

# Regenerate the public artifacts from the fixed implementation.
/app/bin/ovlkeeperctl vacuum \
  --root /var/lib/ovlkeeper \
  --workload retired-api \
  --export /var/lib/ovlkeeper/exports/status.json
/app/scripts/restart-ovlkeeper.sh

# Optional oracle self-checks using jq or the CLI's validate command.
/app/bin/ovlkeeperctl validate --root /var/lib/ovlkeeper
```

The source-level fix should:

- Make cleanup commits update all durable replay/checkpoint surfaces atomically enough for this simulated environment.
- Ensure replay ignores or neutralizes records for layers/workloads that were durably retired at a later generation.
- Make status export validate against replay state, not only the visible active manifest.
- Preserve live references and shared layers.
- Keep repeated cleanup/restart cycles stable.

## 12. `task.toml` Draft

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
tags = ["overlayfs", "journal-replay", "state-recovery", "cleanup", "restart"]
expert_time_estimate_min = 90
junior_time_estimate_min = 210

[verifier]
timeout_sec = 450.0

[agent]
timeout_sec = 1200.0

[environment]
build_timeout_sec = 600.0
cpus = 2
memory_mb = 4096
storage_mb = 10240
allow_internet = false
```

If a custom `docker-compose.yaml` is used, add:

```toml
custom_docker_compose = true
is_multi_container = false
```

Prefer not to use Docker Compose for this task.

## 13. Dockerfile Plan

Use a digest-pinned Go image and install only required system tools.

```dockerfile
FROM golang:1.23-bookworm@sha256:<resolved-approved-digest>

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        coreutils \
        jq \
        make \
        tmux \
        asciinema \
        python3 \
        python3-pytest \
    && rm -rf /var/lib/apt/lists/*

COPY go.mod go.sum ./
RUN go mod download

COPY . /app/
RUN make build \
    && bash /app/scripts/seed-demo-root.sh
```

Before submission:

- Replace `<resolved-approved-digest>` with a real digest.
- Confirm no runtime network access is needed.
- Confirm no reserved directories are created or modified in the Dockerfile.
- Ensure `.dockerignore` excludes `.git`, caches, `solution/`, `tests/`, temp files, and secrets.

## 14. Suggested Go Package Responsibilities

- `cmd/ovlkeeperctl/main.go`: CLI entrypoint.
- `internal/cli`: argument parsing and command dispatch.
- `internal/config`: default paths and root handling.
- `internal/layers`: workload/layer model, reference counting, lineage validation.
- `internal/journal`: append/read/compact replay records.
- `internal/replay`: restart recovery and replay trace generation.
- `internal/vacuum`: plan, prune, sweep, and commit cleanup work.
- `internal/status`: status export and consistency validation.
- `internal/safeio`: atomic write helpers and directory sync simulation.

This split makes the task hard because agents must follow state across several packages rather than patching one obvious function.

## 15. Difficulty Tuning

To keep the task hard:

- Keep public instructions short and symptom-focused.
- Include multiple plausible state surfaces.
- Make the health/status output initially misleading but not malicious.
- Require cleanup + restart + second rerun behavior.
- Preserve shared live layer behavior.
- Include a legacy or generated variant case in tests.
- Avoid exact expected outputs in visible files.

Avoid making it unfair:

- Do not hide the output paths or artifact schemas.
- Do not depend on real timing, sleeps, random crashes, or real kernel mounts.
- Do not require external docs, packages, or network.
- Do not create a single hidden snapshot puzzle.
- Do not make tests assert an implementation-specific helper name.

## 16. Review Checklist Before Submission

- [ ] Regular task structure is correct.
- [ ] `instruction.md` is one or two concise paragraphs.
- [ ] All paths in `instruction.md` are absolute.
- [ ] `instruction.md` does not contain the task name.
- [ ] Public prompt does not reveal the stale durable surface or exact patch file.
- [ ] `environment/` contains 20+ meaningful files.
- [ ] Docker base image is digest-pinned.
- [ ] Dockerfile installs `tmux` and `asciinema`.
- [ ] Dockerfile does not use privileged mode or mount real overlayfs.
- [ ] Dockerfile does not copy `solution/` or `tests/`.
- [ ] `.dockerignore` excludes clutter and secrets.
- [ ] `task.toml` uses `codebase_size = "small"`, not `minimal`.
- [ ] `allow_internet = false`.
- [ ] Oracle solution is deterministic and derives the repair.
- [ ] Tests are behavioral, deterministic, and have informative docstrings.
- [ ] `tests/test.sh` always writes `/logs/verifier/reward.txt`.
- [ ] Oracle Agent passes.
- [ ] NOP Agent fails.
- [ ] Generated-root variant prevents hardcoding.

## 17. Suggested Rubric

Use this in the submission UI, not inside the task files.

```text
Agent diagnoses the failure as a durable cleanup/replay inconsistency rather than only a status export problem, +5
Agent repairs the cleanup and restart workflow so removed workload layers stay absent across repeated replay cycles, +5
Agent preserves live workloads and shared layers while removing only unreferenced retired layers, +3
Agent regenerates status, replay trace, and service log artifacts from the fixed tool instead of manually editing output files, +3
Agent verifies the fix through the public vacuum and restart workflow using the durable root under `/var/lib/ovlkeeper`, +2
Agent hardcodes the visible `retired-api` fixture or specific layer ids instead of implementing general state recovery behavior, -5
Agent deletes or rewrites durable state wholesale in a way that loses live workload lineage, -5
Agent changes verifier, test, solution, or reserved framework paths instead of fixing `/app`, -5
Agent relies on sleeps, wall-clock timing, random crash timing, or privileged overlay mounts to pass, -3
Agent leaves status export green while replay trace or on-disk layer directories still disagree after restart, -3
```

## 18. Final Task-Creation Prompt

Use this prompt with a coding agent to implement the task directory:

```text
Create a new regular Project Terminus task named `overlay-journal-vacuum-reappears` from scratch. Follow the implementation plan exactly. Build a Go + Bash system-administration task where a user-space overlay-style layer manager in `/app` reports a successful vacuum, but deleted workload layers reappear after `/app/scripts/restart-ovlkeeper.sh` replays durable state from `/var/lib/ovlkeeper`.

Use a regular non-milestone skeleton with `instruction.md`, `task.toml`, `environment/`, `solution/solve.sh`, and `tests/`. The `environment/` directory must contain at least 20 meaningful files. Do not use Python as the task language; Python is acceptable only for pytest verification. Do not require real overlayfs, privileged Docker, `SYS_ADMIN`, host mounts, or runtime internet access.

The public `instruction.md` must be concise, use absolute paths, expose only the admin command, restart workflow, artifact paths, durability guarantee, and preservation constraints. It must not reveal the stale state surface, exact broken source file, journal/checkpoint internals, or patch location.

Implement a broken initial Go codebase with multiple plausible durable state surfaces: active manifests, layer directories, append-only journal records, checkpoints, replay traces, and status exports. Seed `/var/lib/ovlkeeper` with live workloads, a retired workload, shared lower layers, retired-only layers, and a state divergence that makes the vacuum look green before restart. The correct solution must coordinate cleanup, replay, checkpoint/compaction, status export, and idempotent reruns.

Write deterministic behavioral tests that build the current source, run the visible vacuum/restart workflow on fresh temp durable roots, verify deleted workload layers do not reappear, verify live/shared layers are preserved, verify status and replay trace agree, verify a second rerun is idempotent, and include a generated variant root to prevent hardcoding. `tests/test.sh` must always write `/logs/verifier/reward.txt` with binary 0/1 reward.

Write `solution/solve.sh` as a deterministic oracle that patches source code, rebuilds the CLI, runs the visible workflow, and verifies the final state. Pin dependencies, digest-pin the Docker base image, install `tmux` and `asciinema`, include `.dockerignore`, set `allow_internet = false`, and ensure Oracle passes while NOP fails.
```
