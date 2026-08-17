# Implementation Plan: Tmpfiles Idempotence Erosion

## 1. Task Summary

Create a **regular, non-milestone Project Terminus task** in the `system-administration` category. The task should be a realistic tmpfiles-style boot cleanup/recovery bug where the user-facing health output reports success, but repeating the repair/replay/boot-cleanup workflow changes which preserved files survive.

The task should be implemented primarily in **Go** with **Bash** harness scripts. Do not list Python in `task.toml`; Python may be used only for verifier tests if the standard pytest harness is used.

Recommended task folder:

```text
tmpfiles-idempotence-erosion/
```

Recommended visible binary name:

```text
janitorctl
```

Recommended visible trace file name:

```text
/app/out/replay.trace
```

Target difficulty: **hard**.

Target codebase size: **small**, with at least **20+ files under `environment/`**.

## 2. Why This Is a Strong Hard Task

This task should remain hard after honest disclosure because the public contract can expose the failing command sequence and required durable outputs, while the actual fix requires diagnosing a mismatch across several mutable state surfaces:

- tmpfiles-like policy files
- a durable replay ledger
- a checkpoint/export cache
- restored boot snapshots
- runtime status output that can turn green before the durable invariant is restored

The intended agent failure modes are:

1. trusting the green status output instead of checking the durable file tree after the second rerun;
2. fixing only the visible demo fixture;
3. deleting or regenerating state artifacts manually instead of fixing the tool;
4. making cleanup idempotent for one path but breaking replay/resume behavior;
5. hardcoding expected survivor names from visible fixtures;
6. patching only the command wrapper while leaving the underlying reconciliation logic inconsistent.

This follows the hard-task guidance: the root cause should span state, restart/replay behavior, and non-obvious interactions rather than a one-file bug.

## 3. Compliance Constraints From the Source Rules

Follow these constraints while building the task:

- Use a regular non-milestone layout with root-level `instruction.md`, `task.toml`, `environment/`, `solution/`, and `tests/`.
- Keep `instruction.md` concise, human-style, and symptoms-only.
- Use absolute paths in `instruction.md`.
- Do not reveal the stale authority, exact patch file, exact helper/function, or generation edge in `instruction.md`.
- Do not put the task name in `instruction.md`.
- Do not use `minimal` codebase size; use `small`.
- Keep all task environment content inside `environment/`.
- Do not copy `tests/` or `solution/` into the Docker image.
- Use a digest-pinned base image in the Dockerfile.
- Install `tmux` and `asciinema` in the image.
- Use `allow_internet = false`.
- Avoid privileged mode and real systemd. Simulate tmpfiles behavior inside `/app`.
- Verifier tests must be deterministic and must not use timing, randomness without a fixed seed, or real reboot/systemd behavior.
- `tests/test.sh` must always write `/logs/verifier/reward.txt` with `0` or `1`.
- Oracle and agent must use the same verifier logic.
- No expected answers should be stored in writable agent-visible files.

## 4. Public Task Contract

The public task should expose only symptoms and observable artifacts.

The agent may be told:

- The tool lives under `/app`.
- The repair/replay command is visible.
- The boot cleanup simulation command is visible.
- Repeating the repair command currently changes the preserved file set.
- The fix must be made in source under `/app`, not by manually editing generated outputs.
- The tool must regenerate public artifacts:
  - `/app/out/status.json`
  - `/app/out/replay.trace`
  - `/app/out/service.log`
- The final behavior must be stable across repair, replay, cleanup, and a second rerun.

The public task must not disclose:

- which state surface is stale;
- which code file contains the broken precedence decision;
- the internal replay/checkpoint ordering bug;
- the exact helper or type that should be patched;
- an exhaustive precedence table;
- a scenario-to-verdict table.

## 5. Suggested `instruction.md`

Keep this short. Do not include the task name as a title or first line.

```md
The cleanup controller under `/app` reports a successful repair, but the preserved file set is not stable: running `/app/bin/janitorctl repair --instance /app/instances/demo` followed by `/app/bin/janitorctl boot --instance /app/instances/demo` twice changes which protected files survive. Fix the implementation under `/app` so repair, replay, and boot cleanup are idempotent for the provided instance and for the same workflow on newly created instances.

The tool must regenerate `/app/out/status.json`, `/app/out/replay.trace`, and `/app/out/service.log` from the repaired implementation. Do not satisfy the task by manually writing those generated artifacts; they must come from the controller commands.
```

This instruction is intentionally concise. It states the admin commands, expected observable behavior, and artifact paths without leaking the stale authority or patch location.

## 6. Environment Design

Build a self-contained tmpfiles-style simulator rather than relying on real `systemd-tmpfiles`.

The environment should contain:

```text
environment/
├── Dockerfile
├── .dockerignore
├── go.mod
├── go.sum
├── Makefile
├── app/
│   ├── cmd/
│   │   └── janitorctl/
│   │       └── main.go
│   ├── internal/
│   │   ├── config/
│   │   │   ├── parser.go
│   │   │   └── merge.go
│   │   ├── cleanup/
│   │   │   ├── planner.go
│   │   │   ├── executor.go
│   │   │   └── rules.go
│   │   ├── fsview/
│   │   │   ├── scan.go
│   │   │   ├── metadata.go
│   │   │   └── digest.go
│   │   ├── journal/
│   │   │   ├── entry.go
│   │   │   ├── writer.go
│   │   │   └── replay.go
│   │   ├── checkpoint/
│   │   │   ├── checkpoint.go
│   │   │   └── atomic.go
│   │   ├── restore/
│   │   │   ├── snapshot.go
│   │   │   └── hydrate.go
│   │   ├── status/
│   │   │   ├── export.go
│   │   │   └── trace.go
│   │   ├── instance/
│   │   │   ├── layout.go
│   │   │   └── seed.go
│   │   └── clock/
│   │       └── logical.go
│   ├── scripts/
│   │   ├── seed-instance.sh
│   │   ├── run-demo.sh
│   │   └── compare-survivors.sh
│   ├── configs/
│   │   ├── base.conf
│   │   ├── boot.conf
│   │   └── local-override.conf
│   ├── fixtures/
│   │   ├── demo/
│   │   │   ├── manifest.json
│   │   │   ├── snapshot.json
│   │   │   └── tree.seed
│   │   └── crash-resume/
│   │       ├── manifest.json
│   │       ├── snapshot.json
│   │       └── tree.seed
│   ├── docs/
│   │   ├── tmpfiles-contract.md
│   │   └── artifact-schema.md
│   └── bin/
│       └── janitorctl          # built during Docker build or by Makefile
```

This gives the agent a realistic codebase with enough files to satisfy `small` size and force cross-file discovery.

## 7. Simulated Instance Layout

Each instance should be rooted under a path such as `/app/instances/demo` and contain a tmpfiles-like filesystem plus durable state.

Example instance structure:

```text
/app/instances/demo/
├── root/
│   ├── run/app-cache/
│   ├── tmp/app-work/
│   └── var/tmp/app-stage/
├── etc/tmpfiles.d/
│   ├── 00-base.conf
│   ├── 20-boot.conf
│   └── 90-local.conf
├── var/lib/janitor/
│   ├── journal.jsonl
│   ├── checkpoint.json
│   ├── boot-snapshot.json
│   └── generations/
├── run/janitor/
│   └── health.json
└── out/
    ├── status.json
    ├── replay.trace
    └── service.log
```

The tool should copy or symlink final public exports to:

```text
/app/out/status.json
/app/out/replay.trace
/app/out/service.log
```

Do not use actual `/run`, `/tmp`, or `/var/tmp` as uncontrolled host state. Keep all simulated state under `/app/instances/<name>`.

## 8. Domain Contract Visible to the Agent

Document only the external contract in `/app/docs/tmpfiles-contract.md` and `/app/docs/artifact-schema.md`.

Visible contract:

- policy files describe path class, cleanup mode, and preservation markers;
- files marked as preserved by policy and instance metadata must survive repair/replay/boot cleanup;
- unprotected temporary files may be removed;
- rerunning repair/replay/boot cleanup must not change the survivor set once the first successful repair completed;
- `status.json` must list survivor paths, removed paths, generation, and a digest of the survivor set;
- `replay.trace` must contain ordered replay events;
- `service.log` must include enough public messages for an administrator to audit a run.

Do not document the broken precedence/authority decision.

## 9. Initial Bug Design

The seeded broken implementation should pass a superficial health check but fail after a second repair/boot cycle.

Recommended internal bug pattern:

1. `repair` replays part of `journal.jsonl` and writes a green `run/janitor/health.json`.
2. The cleanup planner computes the first survivor set from a mixed source of policy and runtime health.
3. A later `boot` command rehydrates from a durable checkpoint that was written before replay fully reconciled generation metadata.
4. A second `repair` uses the stale checkpoint/export path as if it were canonical, causing at least one preserved file to be deleted or one removed file to reappear.

This creates the visible symptom without requiring real crash timing.

The broken behavior should be deterministic. Represent “crash” with a fixture containing a checkpoint and journal that intentionally disagree, not with `kill -9`, sleeps, or actual process races.

## 10. Required Commands

The agent-visible CLI should support at least these commands:

```bash
/app/bin/janitorctl seed --instance /app/instances/demo --fixture demo
/app/bin/janitorctl repair --instance /app/instances/demo
/app/bin/janitorctl replay --instance /app/instances/demo
/app/bin/janitorctl boot --instance /app/instances/demo
/app/bin/janitorctl status --instance /app/instances/demo --json
```

The instruction should mention only the commands needed to reproduce the symptom. Additional commands can be discoverable through `--help` and docs.

## 11. Output Artifact Schemas

The schemas can be public because tests will check them.

`/app/out/status.json`:

```json
{
  "instance": "/app/instances/demo",
  "generation": 4,
  "survivor_digest": "sha256:<hex>",
  "preserved_files": ["root/tmp/app-work/session.keep"],
  "removed_files": ["root/tmp/app-work/stale.tmp"],
  "warnings": []
}
```

Rules:

- `generation` is an integer.
- `survivor_digest` is computed from the sorted preserved relative paths and file content digests.
- `preserved_files` is a sorted list of relative paths.
- `removed_files` is a sorted list of relative paths.
- `warnings` is a sorted list of strings.

`/app/out/replay.trace` should be JSONL with one event per line:

```json
{"seq":1,"phase":"repair","path":"root/tmp/app-work/session.keep","action":"preserve"}
```

Rules:

- `seq` is strictly increasing within one command invocation.
- `phase` is one of `seed`, `repair`, `replay`, `boot`, `export`.
- `path` is a relative path or `"-"` for global events.
- `action` is one of `observe`, `preserve`, `remove`, `restore`, `export`, `skip`.

`/app/out/service.log`:

- human-readable text;
- no exact string matching should be required except for broad public phrases such as `repair complete`, `boot cleanup complete`, and `exported status`.

## 12. Oracle Solution Strategy

The oracle should patch the real source, not write final outputs directly.

Expected solution shape:

1. Rebuild `janitorctl` from Go sources.
2. Repair the reconciliation logic so replay establishes the canonical durable state before cleanup planning.
3. Ensure checkpoint writes are atomic and occur after replay/cleanup/export state is internally consistent.
4. Ensure cleanup planning derives a stable survivor set from the same canonical state on first and second rerun.
5. Ensure exports are regenerated from the command result and not copied from stale runtime health.
6. Run the visible demo command sequence.
7. Run an internal smoke check against a crash-resume fixture.

Implementation should likely touch multiple files, for example:

- journal replay logic;
- checkpoint/generation reconciliation;
- cleanup planner;
- status/trace exporter;
- command orchestration.

Do not make the oracle a one-file replacement if possible. A one-file oracle patch is likely too localized and may collapse the task.

## 13. `solution/solve.sh` Plan

Use a deterministic patch-based solve script:

```bash
#!/usr/bin/env bash
set -euo pipefail
cd /app

# Apply source patch across multiple Go files.
patch -p1 < /oracle/fix.patch

go test ./...
go build -o /app/bin/janitorctl ./cmd/janitorctl

rm -rf /app/instances/demo /app/out
/app/bin/janitorctl seed --instance /app/instances/demo --fixture demo
/app/bin/janitorctl repair --instance /app/instances/demo
/app/bin/janitorctl boot --instance /app/instances/demo
/app/bin/janitorctl repair --instance /app/instances/demo
/app/bin/janitorctl boot --instance /app/instances/demo
/app/bin/janitorctl status --instance /app/instances/demo --json >/tmp/final-status.json
```

Place `fix.patch` under `solution/` if needed, or embed the patch in `solve.sh`. Do not depend on network access.

## 14. Verifier Design

Use `tests/test.sh` plus `tests/test_outputs.py`.

`tests/test.sh` must use the standard reward pattern:

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

The verifier should create fresh test instances under temporary paths, run the compiled tool, and compute expected survivor sets from generated fixture metadata. Avoid reading expected answers from agent-writable files.

Recommended tests:

### Test 1: demo repair/boot is idempotent

Workflow:

1. remove `/app/instances/demo` and `/app/out`;
2. seed the demo fixture;
3. run repair + boot;
4. capture preserved relative paths and survivor digest;
5. run repair + boot again;
6. assert preserved paths and digest are identical;
7. assert public artifacts were regenerated.

### Test 2: crash-resume fixture survives replay

Create a fixture with:

- one protected file added after the checkpoint;
- one stale file marked removed in the journal but still present in the tree;
- one unprotected file with misleading runtime health metadata.

Expected behavior:

- protected post-checkpoint file survives;
- stale removed file does not reappear after second replay;
- survivor digest is stable across repeated replay and boot cleanup.

### Test 3: generated artifacts reflect current input, not static files

Workflow:

1. seed a fresh instance;
2. add a new protected file using the public policy format;
3. run repair/replay/boot;
4. assert `status.json` includes the new protected file;
5. assert `survivor_digest` changes when content changes;
6. assert `replay.trace` has events for the new path.

This catches manual artifact writes and hardcoded fixture answers.

### Test 4: config precedence remains externally consistent

Use two generated policy files with an override. The tests should verify the final file tree behavior, not source internals.

Expected behavior:

- the effective policy is stable across reruns;
- local override does not delete protected files;
- unrelated unprotected scratch files are cleaned.

### Test 5: trace ordering and export schema

Validate:

- `status.json` has required fields and sorted lists;
- `replay.trace` is valid JSONL;
- sequence numbers are strictly increasing per command invocation;
- actions are from the documented action set;
- trace paths are relative, not absolute.

### Test 6: NOP fails meaningfully

Without any source change, the seeded implementation should fail at least the demo idempotence and crash-resume tests.

## 15. Anti-Cheating Measures

- Tests should generate at least one fresh instance that is not the visible `/app/instances/demo`.
- Expected survivor sets should be computed from test-created inputs, not static golden files.
- Tests should mutate a protected file after seeding to ensure digest/export generation is real.
- Tests should run the command sequence multiple times, not just inspect files after one command.
- Tests should fail if `/app/out/status.json` is manually written and does not match the actual instance tree.
- Tests should check behavior through the CLI, not by parsing source code.
- Keep test fixtures under `/tests` and generated temp directories, not under the agent-editable `environment/` tree.

## 16. Dockerfile Plan

Use a digest-pinned Go image. Replace the digest below with a real current digest when implementing.

```dockerfile
FROM golang:1.23-bookworm@sha256:<real_digest>

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        coreutils \
        findutils \
        jq \
        make \
        tmux \
        asciinema \
        python3 \
        python3-pip \
    && rm -rf /var/lib/apt/lists/*

COPY go.mod go.sum ./
RUN go mod download

COPY app/ /app/
COPY Makefile /app/Makefile

RUN go test ./... \
    && go build -o /app/bin/janitorctl ./cmd/janitorctl

ENV PATH="/app/bin:${PATH}"
```

Add `.dockerignore`:

```text
.git
__pycache__/
.pytest_cache/
*.pyc
solution/
tests/
.env
node_modules/
```

If pytest plugins are required, install them in the Dockerfile with exact pinned versions. Do not install verifier dependencies in `tests/test.sh`.

## 17. `task.toml` Plan

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
tags = ["tmpfiles", "recovery", "idempotence", "state-replay", "cleanup"]
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

Do not include `python` in `languages` unless the agent-facing implementation requires Python.

## 18. Rubric Draft

Use this in the submission UI, not necessarily inside the task folder.

```text
Agent diagnoses the unstable survivor set by comparing behavior across repair, replay, boot cleanup, and a second rerun, +5
Agent fixes the source implementation so generated status, trace, and log artifacts reflect the actual post-cleanup file tree, +5
Agent preserves protected files across checkpoint/replay recovery while still removing unprotected temporary files, +5
Agent implements a durable idempotent reconciliation path instead of relying on the runtime health output alone, +3
Agent keeps the CLI workflow compatible with the documented commands and schemas, +3
Agent verifies the fix on at least one fresh instance beyond the visible demo instance, +2
Agent manually writes `/app/out/status.json`, `/app/out/replay.trace`, or `/app/out/service.log` instead of regenerating them through the controller, -5
Agent hardcodes visible demo survivor names or fixture paths instead of deriving behavior from policy and state, -5
Agent disables cleanup or preserves every file to avoid deletions, -5
Agent edits verifier, oracle, reserved runtime paths, or external task files instead of fixing `/app`, -5
Agent introduces nondeterministic timing, sleeps, or real systemd/reboot dependencies, -3
Agent breaks existing seed, status, or help commands while fixing the idempotence bug, -3
```

Positive total: 23 points. Negative criteria: 5+ distinct penalties.

## 19. Implementation Steps

1. Create the regular task skeleton.
2. Build the Go tmpfiles simulator with clean command boundaries: seed, repair, replay, boot, status.
3. Add docs for public policy and artifact schemas.
4. Add two visible fixtures: `demo` and `crash-resume`.
5. Seed the deterministic bug so the first repair can look healthy but the second repair/boot changes survivors.
6. Add Bash helper scripts for seeding/running the demo.
7. Add Dockerfile with digest-pinned base image, pinned dependencies, `tmux`, and `asciinema`.
8. Add `task.toml` with `system-administration`, `hard`, `small`, and languages `go`/`bash`.
9. Write concise `instruction.md` with only the symptom, commands, and artifact contract.
10. Write oracle patch and `solution/solve.sh`.
11. Write pytest verifier tests that generate fresh instances and compute expected values from public schemas.
12. Run oracle validation.
13. Run NOP validation and confirm it fails.
14. Run static review checks for Docker, metadata, reward file, hidden contracts, and instruction leakage.
15. If frontier agents pass too often, strengthen by adding a second generated crash-resume instance or an override-policy case, not by adding more instruction text.

## 20. Hardness Calibration Checklist

Before submitting, verify:

- [ ] Public instructions do not name the stale authority, patch file, helper name, or generation edge.
- [ ] At least three non-trivial discoveries are required from files/runtime behavior.
- [ ] The oracle touches at least three meaningful source locations.
- [ ] The task cannot be solved by manually writing `/app/out/*`.
- [ ] The task cannot be solved by preserving all files.
- [ ] The task cannot be solved by deleting all runtime state.
- [ ] A fresh generated instance is tested.
- [ ] Crash/restart behavior is deterministic and fixture-driven.
- [ ] NOP fails.
- [ ] Oracle passes repeatedly.
- [ ] No network is required at runtime.
- [ ] No privileged operations are required.

## 21. Collapse Risks and Fixes

| Collapse Risk | Prevention |
|---|---|
| Instruction reveals the stale state surface | Keep instruction symptoms-only; disclose commands and artifacts only. |
| Tests check only visible demo fixture | Generate at least one fresh verifier instance. |
| Agent can pass by writing static `/app/out/*` | Recompute expected artifacts from actual file tree and mutated inputs. |
| Agent can preserve every file | Tests require unprotected scratch files to be removed. |
| Agent can delete all state and start clean | Tests include post-checkpoint protected files that must survive. |
| Task becomes flaky due to crash timing | Use deterministic checkpoint/journal fixtures, not live crashes. |
| Oracle is too localized | Make the bug span replay, checkpoint, cleanup, and export behavior. |

## 22. Final Acceptance Target

The final task should feel like a realistic administrator asking a coding agent to fix a stateful boot cleanup tool. The user-facing problem is simple: repeated repair should not change protected survivors. The engineering challenge is hard because the agent must discover which observable green state is misleading, reconcile multiple durable/runtime surfaces, preserve valid files, remove invalid files, and regenerate artifacts through the real command workflow.
