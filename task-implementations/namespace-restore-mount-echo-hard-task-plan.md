# Namespace Restore Mount Echo — Hard Task Implementation Plan

## 1. Task summary

Create a **regular, non-milestone Project Terminus task** in the `system-administration` category. The task should simulate a realistic mount namespace restore subsystem where a restore command reports success, but a restored container-style namespace can still read bind-mounted content from an earlier generation after a supervisor restart and replay.

The agent must fix the source under `/app` so the restore workflow reconstructs the active namespace state from conflicting mutable evidence, emits consistent status and trace artifacts, and preserves declared kept paths across repeated restore/replay cycles.

Recommended implementation language: **Go + Bash**.

- Go: CLI, restore engine, state reconciliation, trace/status exporters, fixture readers.
- Bash: supervisor/restart scripts, fixture setup helpers, oracle entrypoint.
- Pytest may still be used only for the verifier, but do not list Python as an application language in `task.toml`.

## 2. Why this should be hard

This task should be hard because the visible symptom is simple, but the correct fix requires understanding several conflicting state surfaces:

1. A generation manifest describing the intended restored view.
2. Runtime mount records that can survive a restart.
3. A checkpoint snapshot from a previous restore.
4. Exported status JSON that may report green even when the readable filesystem is stale.
5. JSONL replay traces that expose the inconsistency without directly naming the root cause.

A shallow fix can make the status file look right while leaving the readable namespace stale. Another shallow fix can make the first replay pass while failing after a second restart/replay cycle. The verifier should catch both.

Target difficulty: **Hard**. The task should require at least 10 meaningful steps: inspect commands, reproduce restore, inspect logs/status, trace state surfaces, inspect several Go packages, fix reconciliation, rebuild, rerun restore, restart/replay, verify preservation, and confirm artifacts.

## 3. Safety and realism boundary

Do **not** require real Linux mount namespace operations, real `mount(2)`, `unshare`, `pivot_root`, `chroot`, `SYS_ADMIN`, privileged Docker mode, or host mounts. Those would conflict with the safe Docker environment rules.

Instead, implement a user-space namespace restore simulator:

- A namespace is a materialized directory tree under `/var/lib/ns-restore/views/<name>/rootfs`.
- Bind mounts are modeled as entries mapping a target path to a source directory and generation.
- `nsmgr read --name <name> --path <path>` reads through the simulated mount table.
- `nsmgr restore ...` rebuilds the view and exports status/trace artifacts.
- `scripts/restart-supervisor.sh` simulates a service restart by rotating runtime state and reloading durable records.

This keeps the task realistic for system administration while remaining reproducible and non-privileged.

## 4. Public task prompt strategy

The public `instruction.md` must remain concise, symptom-oriented, and must not disclose the exact stale authority, corrupted metadata location, precedence table, helper name, or reconstruction algorithm.

### Publicly allowed disclosures

Expose:

- The admin command to reproduce restore.
- The restart/reload scenario.
- Observable logs, status JSON, trace JSONL, and durable artifacts.
- Preservation constraints for kept paths.
- Required output paths and schemas.

### Forbidden public disclosures

Do not expose:

- The exact stale metadata file.
- The source-of-truth rule.
- The broken Go function or package.
- The reconciliation algorithm.
- A manifest-to-verdict table.
- A step-by-step solution path.

### Draft `instruction.md`

```md
The restore tool in `/app` reports a clean restore for the provided replay bundle, but after `/app/scripts/restart-supervisor.sh` and a second replay the restored namespace can still read content from an earlier bind source. Fix the implementation under `/app` so `/app/bin/nsmgr restore --bundle /app/fixtures/replay/site-a --name worker-a --status /var/lib/ns-restore/status.json --trace /var/log/ns-restore/restore.trace.jsonl` makes the readable namespace, status JSON, and trace JSONL agree on the active generation across repeated restore/replay cycles.

Preserve files under `/var/lib/ns-restore/kept/worker-a/` across restores, and keep generated artifacts under `/var/lib/ns-restore/` and `/var/log/ns-restore/` reproducible after the supervisor restart. Do not replace the workflow with static artifact writes; the CLI should work for replay bundles with the same schema.
```

Notes:

- Uses absolute paths.
- Does not include the task title.
- Names the command and observable artifact paths.
- Does not tell the agent which file or algorithm to patch.
- Mentions same-schema bundles to imply generality and prevent hardcoded fixture-only fixes.

## 5. Proposed task name and metadata

Folder name:

```text
namespace-restore-mount-echo
```

`task.toml` skeleton:

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
tags = ["namespace-restore", "filesystem-state", "restart-replay", "state-reconstruction", "system-admin"]
expert_time_estimate_min = 120
junior_time_estimate_min = 240

[agent]
timeout_sec = 1200.0

[verifier]
timeout_sec = 600.0

[environment]
build_timeout_sec = 900.0
cpus = 2
memory_mb = 4096
storage_mb = 10240
allow_internet = false
```

Do not use `codebase_size = "minimal"`. Keep the agent-facing environment at **20+ files**.

## 6. Required task directory layout

```text
namespace-restore-mount-echo/
├── instruction.md
├── task.toml
├── environment/
│   ├── Dockerfile
│   ├── .dockerignore
│   └── app/
│       ├── go.mod
│       ├── go.sum
│       ├── Makefile
│       ├── cmd/
│       │   └── nsmgr/
│       │       └── main.go
│       ├── internal/
│       │   ├── cli/
│       │   │   ├── args.go
│       │   │   └── commands.go
│       │   ├── config/
│       │   │   └── defaults.go
│       │   ├── fixture/
│       │   │   ├── bundle.go
│       │   │   └── validate.go
│       │   ├── fsview/
│       │   │   ├── materialize.go
│       │   │   ├── read.go
│       │   │   └── overlay.go
│       │   ├── logging/
│       │   │   └── jsonl.go
│       │   ├── mount/
│       │   │   ├── entry.go
│       │   │   ├── resolve.go
│       │   │   └── table.go
│       │   ├── restore/
│       │   │   ├── apply.go
│       │   │   ├── checkpoint.go
│       │   │   ├── reconcile.go
│       │   │   ├── replay.go
│       │   │   └── status.go
│       │   ├── state/
│       │   │   ├── durable.go
│       │   │   ├── generation.go
│       │   │   └── runtime.go
│       │   └── status/
│       │       ├── export.go
│       │       └── schema.go
│       ├── scripts/
│       │   ├── clean-runtime.sh
│       │   ├── inspect-view.sh
│       │   └── restart-supervisor.sh
│       ├── fixtures/
│       │   └── replay/
│       │       └── site-a/
│       │           ├── bundle.json
│       │           ├── generations/
│       │           │   ├── gen-001.json
│       │           │   ├── gen-002.json
│       │           │   └── gen-003.json
│       │           └── sources/
│       │               ├── cfg-a/
│       │               │   └── app.conf
│       │               ├── cfg-b/
│       │               │   └── app.conf
│       │               └── cfg-c/
│       │                   └── app.conf
│       └── docs/
│           ├── status-schema.md
│           ├── replay-bundle-format.md
│           └── operator-runbook.md
├── solution/
│   └── solve.sh
└── tests/
    ├── test.sh
    └── test_outputs.py
```

This layout gives a small but non-trivial Go codebase with more than 20 files and requires discovery across CLI, restore, mount resolution, runtime state, and artifact export packages.

## 7. Environment design

### Dockerfile requirements

Use a digest-pinned sanctioned base image. Example pattern:

```dockerfile
FROM golang:1.22-bookworm@sha256:<real_digest_here> AS build
WORKDIR /src
COPY app/go.mod app/go.sum ./
RUN go mod download
COPY app/ ./
RUN CGO_ENABLED=0 go build -trimpath -o /out/nsmgr ./cmd/nsmgr

FROM debian:bookworm-slim@sha256:<real_digest_here>
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        coreutils \
        jq \
        tmux \
        asciinema \
        python3 \
        python3-pytest \
    && rm -rf /var/lib/apt/lists/*
COPY --from=build /out/nsmgr /app/bin/nsmgr
COPY app/ /app/
ENV PATH="/app/bin:${PATH}"
```

Before submission, replace `<real_digest_here>` with actual sha256 digests. Do not use tag-only `FROM` lines.

### `.dockerignore`

Include:

```text
.git
__pycache__/
.pytest_cache/
*.pyc
solution/
tests/
.env
*.log
node_modules/
target/
dist/
```

### No reserved path creation

Do not create or modify `/tests`, `/solution`, `/oracle`, `/logs/verifier`, or `/logs/artifacts` in the Dockerfile. Runtime scripts may create `/var/lib/ns-restore` and `/var/log/ns-restore` because those are task-specific paths.

## 8. Initial broken behavior to seed

Seed a realistic bug that has two visible layers:

### Layer A: stale runtime state selected during restore

In `internal/restore/reconcile.go`, the broken logic should prefer a durable runtime mount record from the previous restore when the target path already exists. This causes the readable namespace view to keep pointing at a previous generation’s source directory even though the new generation manifest has been loaded.

Bad internal behavior, described conceptually:

```text
if existing mount target exists in durable runtime state:
    reuse existing source id and mount token
else:
    use source id from current generation manifest
```

Correct behavior, described conceptually:

```text
derive active target entries from the requested generation manifest and validate them against source content; use durable runtime state only for preservation metadata that is explicitly independent of the bind source.
```

Do not put this algorithm into `instruction.md`.

### Layer B: status exporter reports the manifest, not the readable view

In `internal/restore/status.go` or `internal/status/export.go`, the broken status should report the requested active generation from the manifest even if the materialized readable view still resolves to the previous generation. This creates the misleading green check.

The honest fix should make the status exporter derive or validate effective readable mount state before reporting success. It should not merely copy manifest values into status.

## 9. Fixture design

Create a visible fixture at `/app/fixtures/replay/site-a` with three generations.

### `bundle.json`

```json
{
  "schema": "nsrestore.bundle.v1",
  "namespace": "worker-a",
  "default_generation": "gen-003",
  "preserve": ["/var/lib/ns-restore/kept/worker-a/"],
  "generations": ["gen-001", "gen-002", "gen-003"]
}
```

### Generation files

Each generation file should include:

```json
{
  "generation": "gen-003",
  "mounts": [
    {
      "target": "/etc/app/app.conf",
      "source_id": "cfg-c",
      "kind": "bind",
      "required_digest": "<sha256 of sources/cfg-c/app.conf>"
    }
  ],
  "exports": {
    "status_surface": "operator",
    "trace_surface": "restore"
  }
}
```

Make `cfg-a/app.conf`, `cfg-b/app.conf`, and `cfg-c/app.conf` differ in more than one field so agents cannot pass by string replacement:

```text
release=alpha
bind_generation=gen-001
feature_flag=off
```

```text
release=bravo
bind_generation=gen-002
feature_flag=staged
```

```text
release=charlie
bind_generation=gen-003
feature_flag=on
```

### Hidden verifier fixture

The tests should generate an additional same-schema bundle in a temporary directory at verifier runtime. It should use different generation names and content values, for example `gen-010`, `gen-011`, `gen-012`, with source IDs unrelated to `cfg-a/b/c`. This prevents fixture-specific hardcoding.

## 10. CLI contract

Implement these commands:

```bash
/app/bin/nsmgr restore \
  --bundle /app/fixtures/replay/site-a \
  --name worker-a \
  --status /var/lib/ns-restore/status.json \
  --trace /var/log/ns-restore/restore.trace.jsonl

/app/bin/nsmgr read \
  --name worker-a \
  --path /etc/app/app.conf

/app/bin/nsmgr status \
  --name worker-a \
  --json

/app/scripts/restart-supervisor.sh
```

`restore` should:

- Load the bundle and selected/default generation.
- Reconcile runtime and durable state.
- Materialize a readable view.
- Preserve configured kept paths.
- Write status JSON.
- Append or rewrite trace JSONL deterministically; choose one behavior and document it.

`read` should:

- Resolve the requested namespace path through the effective simulated mount table.
- Print the file content from the active source.
- Exit non-zero for missing namespace or path.

`status --json` should:

- Print effective state, not just the requested manifest.
- Use deterministic key order if generated manually, or stable `encoding/json` structs.

`restart-supervisor.sh` should:

- Simulate a supervisor restart by moving runtime state aside and rehydrating from durable records.
- Preserve `/var/lib/ns-restore/kept/<name>/`.
- Not delete status or trace files unless restore rewrites them.

## 11. Artifact schemas

### `/var/lib/ns-restore/status.json`

Schema:

```json
{
  "schema": "nsrestore.status.v1",
  "namespace": "worker-a",
  "active_generation": "gen-003",
  "healthy": true,
  "mounts": [
    {
      "target": "/etc/app/app.conf",
      "source_id": "cfg-c",
      "digest": "...",
      "readable": true
    }
  ],
  "preserved_paths": ["/var/lib/ns-restore/kept/worker-a/operator.note"]
}
```

Avoid a status field that directly restates verifier verdicts, such as `tests_passed` or `expected_generation_ok`.

### `/var/log/ns-restore/restore.trace.jsonl`

Each line is JSON. Include events like:

```json
{"event":"bundle_loaded","namespace":"worker-a","generation":"gen-003"}
{"event":"mount_resolved","target":"/etc/app/app.conf","source_id":"cfg-c","digest":"..."}
{"event":"view_materialized","namespace":"worker-a","generation":"gen-003"}
{"event":"status_exported","path":"/var/lib/ns-restore/status.json"}
```

The verifier should check consistency properties across events rather than exact event count only.

## 12. Verifier plan

Use `tests/test.sh` with the required reward-file pattern and no `set -e`.

### `tests/test.sh`

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
python3 -m pytest /tests/test_outputs.py -rA
rc=$?

if [ "$rc" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
```

If `pytest-json-ctrf` is installed, add `--ctrf /logs/verifier/ctrf.json`; otherwise keep the runner simple and deterministic.

### Behavioral tests

Implement tests like these:

1. `test_visible_read_matches_status_after_restart_and_replay`
   - Clean `/var/lib/ns-restore` and `/var/log/ns-restore`.
   - Write `/var/lib/ns-restore/kept/worker-a/operator.note`.
   - Run the visible restore command.
   - Run `/app/scripts/restart-supervisor.sh`.
   - Run the same restore command again.
   - Run `/app/bin/nsmgr read --name worker-a --path /etc/app/app.conf`.
   - Load `/var/lib/ns-restore/status.json`.
   - Assert readable content digest matches the active mount digest in status and generation `gen-003`.
   - Assert the kept file content still exists.

2. `test_hidden_bundle_same_schema_not_hardcoded`
   - Generate a temporary bundle under `/tmp/nsrestore-hidden-bundle` with three different generations and source IDs.
   - Run restore with `--bundle /tmp/nsrestore-hidden-bundle --name verifier-ns`.
   - Restart and replay.
   - Assert `read` returns the hidden bundle’s latest generation content.
   - Assert no visible fixture strings like `charlie`, `cfg-c`, or `worker-a` are required for correctness.

3. `test_status_trace_and_readable_view_are_coherent`
   - Run restore.
   - Parse status JSON and trace JSONL.
   - Assert every status mount target has a matching `mount_resolved` trace event with the same source ID and digest.
   - Assert the digest of `nsmgr read` content equals status and trace digest.
   - Assert `healthy` is not true when any mount is unreadable; generate one temporary broken bundle to verify non-zero or unhealthy behavior if the CLI supports it.

4. `test_restore_rebuilds_runtime_state_without_static_artifact_writes`
   - Remove `/var/lib/ns-restore/runtime` or the simulator’s runtime directory.
   - Keep durable bundle sources intact.
   - Run restore again.
   - Assert runtime state and readable view are regenerated.
   - Assert status JSON modification is not the only changed artifact; the effective read output must be correct.

5. `test_non_monotonic_generation_selection_if_supported`
   - If CLI supports `--generation`, restore `gen-002`, restart, then restore `gen-003`.
   - Assert the second restore does not reuse generation 2’s source.
   - This catches monotonic or “latest visible fixture only” hacks.

### What tests should not do

- Do not parse Go source code for a specific function name.
- Do not require exact trace line ordering unless the CLI explicitly promises ordering.
- Do not hardcode only visible fixture content as the expected answer.
- Do not use sleeps, polling timeouts, or real background daemons.
- Do not make oracle/agent conditional branches.

## 13. Oracle solution plan

`solution/solve.sh` should be deterministic, fail fast, patch the real source, rebuild the CLI, and run a sanity check.

High-level oracle sequence:

```bash
#!/usr/bin/env bash
set -euo pipefail
cd /app

# Patch restore reconciliation to derive effective mounts from the selected generation manifest.
# Patch status export to report effective readable mount state.
# Rebuild /app/bin/nsmgr.
# Run restore, restart, replay, read, and status sanity checks.
```

Implementation options:

- Use `perl -0pi` or `apply_patch` style modifications to change specific Go files.
- Prefer small targeted patches over replacing the entire application.
- Do not hardcode visible fixture outputs into generated status files.
- Do not edit `/tests`, `/solution`, `/oracle`, or verifier files.

The oracle should end with commands similar to:

```bash
go build -trimpath -o /app/bin/nsmgr ./cmd/nsmgr
rm -rf /var/lib/ns-restore/runtime /var/lib/ns-restore/views /var/lib/ns-restore/status.json /var/log/ns-restore/restore.trace.jsonl
mkdir -p /var/lib/ns-restore/kept/worker-a
printf 'keep-me\n' > /var/lib/ns-restore/kept/worker-a/operator.note
/app/bin/nsmgr restore --bundle /app/fixtures/replay/site-a --name worker-a --status /var/lib/ns-restore/status.json --trace /var/log/ns-restore/restore.trace.jsonl
/app/scripts/restart-supervisor.sh
/app/bin/nsmgr restore --bundle /app/fixtures/replay/site-a --name worker-a --status /var/lib/ns-restore/status.json --trace /var/log/ns-restore/restore.trace.jsonl
/app/bin/nsmgr read --name worker-a --path /etc/app/app.conf | grep -q 'bind_generation=gen-003'
grep -q 'keep-me' /var/lib/ns-restore/kept/worker-a/operator.note
```

## 14. Correct fix design, kept internal to task authoring

The intended robust fix should do all of the following:

1. Treat the selected generation manifest as the source for active bind targets.
2. Validate source content digest before materializing mount records.
3. Separate preservation metadata from active bind-source selection.
4. Rebuild effective mount tables on every restore/replay, including after restart.
5. Make `read`, `status`, and trace output use the same effective mount table.
6. Preserve configured kept paths without allowing preserved runtime records to override active source IDs.
7. Avoid static writes to status/trace as a replacement for repairing restore behavior.

This internal section can guide the oracle and tests, but must not be copied into `instruction.md`.

## 15. Common wrong solutions the verifier should catch

1. Editing only `/var/lib/ns-restore/status.json`.
2. Editing only visible fixture files so stale reads appear correct.
3. Hardcoding `gen-003`, `cfg-c`, `worker-a`, or `charlie`.
4. Deleting all durable state on restart, which breaks preservation.
5. Always selecting lexicographically newest generation, ignoring requested/default bundle semantics.
6. Fixing first restore but failing after `restart-supervisor.sh`.
7. Making `status` report manifest values while `read` resolves a different source.
8. Replacing the CLI with a shell wrapper that only handles `/app/fixtures/replay/site-a`.
9. Making trace JSON invalid or non-deterministic.
10. Introducing sleeps or background daemons into verifier-sensitive paths.

## 16. Hardness strengthening moves

Use these if early agent runs pass too often:

1. Add hidden verifier bundles with target collisions across two mount targets, for example `/etc/app/app.conf` and `/etc/app/feature.flag`.
2. Add a requested-generation test where the bundle default is not lexicographically newest.
3. Add a restart replay test that removes runtime state but keeps checkpoints.
4. Add a preservation test with a file whose name resembles a mount source ID to catch broad delete/copy fixes.
5. Add digest validation where one stale source has the same filename but different content.
6. Add a trace coherence test that checks status and read are both derived from the same effective table.

Do not harden by making the instructions longer or by hiding requirements that are not implied by the public prompt.

## 17. Anti-cheating controls

- Keep expected hidden bundle content generated inside `/tests/test_outputs.py` at verifier runtime.
- Do not store golden outputs in `/app`.
- Do not copy `/tests` or `/solution` into the Docker image.
- Tests should compute expected digests from verifier-created input files.
- Tests should verify the CLI against a same-schema bundle unknown during agent solving.
- Make fixture data writable only where normal task behavior requires it; avoid deriving expected answers from mutable agent-edited visible fixture files.
- If visible fixture files must be mutable, hidden verifier bundles become mandatory.

## 18. Review checklist before submission

- [ ] `instruction.md` is one to two concise paragraphs.
- [ ] Every path in `instruction.md` is absolute.
- [ ] `instruction.md` does not include task name, helper names, patch file, or source-of-truth rule.
- [ ] `task.toml` uses `category = "system-administration"` and `codebase_size = "small"` or `large`, not `minimal`.
- [ ] Environment has 20+ meaningful files.
- [ ] Docker base images are digest-pinned.
- [ ] Dockerfile installs `tmux` and `asciinema`.
- [ ] Dockerfile does not copy tests or solution.
- [ ] Dockerfile does not create reserved `/tests`, `/solution`, or `/oracle` paths.
- [ ] No privileged mode, `SYS_ADMIN`, host mounts, or Docker socket.
- [ ] No runtime network dependency.
- [ ] Oracle solution is deterministic and performs a real source fix.
- [ ] `tests/test.sh` always writes `/logs/verifier/reward.txt` with 0 or 1.
- [ ] Tests are behavioral, deterministic, and aligned with the prompt.
- [ ] Tests include restart/replay and hidden same-schema bundle coverage.
- [ ] NOP fails.
- [ ] Oracle passes repeatedly.
- [ ] Agent failures are due to cross-surface reasoning misses, not ambiguity or broken setup.

## 19. Suggested rubric for submission UI

```text
Agent diagnoses restore behavior using the CLI, status JSON, trace JSONL, and readable namespace output rather than relying on a single artifact, +3
Agent implements restore reconciliation so the effective readable mount table is rebuilt from the selected replay generation across restart/replay cycles, +5
Agent keeps status JSON, trace JSONL, and `nsmgr read` output coherent for each active mount target, +5
Agent preserves files under `/var/lib/ns-restore/kept/` while preventing preserved runtime records from overriding active bind sources, +3
Agent validates the fix on at least one restart followed by a second restore/replay cycle, +2
Agent preserves same-schema bundle support instead of special-casing `/app/fixtures/replay/site-a`, +3
Agent hardcodes visible generation names, source IDs, fixture strings, or status JSON values, -5
Agent fixes only status or trace artifacts while leaving the readable namespace stale, -5
Agent deletes durable kept data or broad runtime state in a way that violates preservation constraints, -3
Agent introduces privileged operations, host mounts, real namespace syscalls, sleeps, or daemon timing dependencies to pass the workflow, -5
Agent edits verifier, oracle, or reserved framework paths instead of fixing `/app`, -5
```

Positive total: 21 points. Negative criteria: 5 distinct penalties.

## 20. Final implementation order

1. Create the regular task skeleton.
2. Build the Go CLI and Bash scripts under `environment/app`.
3. Add visible replay fixture `site-a` with three generations.
4. Seed the stale runtime-state bug and misleading status exporter.
5. Add concise `instruction.md` with symptom, command, artifacts, and preservation requirement.
6. Add `task.toml` metadata and safe resource limits.
7. Add digest-pinned Dockerfile and `.dockerignore`.
8. Write deterministic pytest verifier with hidden same-schema bundle generation.
9. Write oracle `solution/solve.sh` that patches source and rebuilds.
10. Run oracle until consistently passing.
11. Run NOP and confirm failure.
12. Run frontier agents when possible; if pass rate is too high, apply the hardening moves above.
