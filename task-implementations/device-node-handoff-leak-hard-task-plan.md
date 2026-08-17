# Device Node Handoff Leak — Hard Project Terminus Task Implementation Plan

## 1. Task Summary

Create a **regular, non-milestone Project Terminus task** in the `system-administration` category. The task models a host-side device handoff subsystem used to grant simulated device-node access to short-lived tenants. The visible symptom is that an administrative detach flow exits successfully and the audit/status surfaces say the device is detached, but after a reload/restore path the access checker still allows a later tenant to use the detached device.

The intended task name is:

```text
device-handoff-revocation
```

Use **Go + Bash** for the task implementation. Do not use Python as a task language in `task.toml`; Python may only appear in `/tests` as verifier tooling.

This should be a **hard** task because the fix requires reconciling several authority surfaces: encoded grant exports, decoded runtime state, durable lease state, checkpoint replay, audit decisions, and status artifacts. The public prompt should disclose only the admin command, reload/restore scenario, public logs, and durable artifacts. It must not reveal the stale authority, vulnerable enforcement surface, exploit primitive, exact patch file, or generation edge.

## 2. Why This Fits the Seed

Seed mapping:

| Seed Field | Implementation Choice |
|---|---|
| Category | `system-administration` |
| Bug family | Device authority handoff |
| Profile | `security_authority_split` |
| Topology | `udev container handoff` style, simulated safely without privileged Docker |
| Public symptom | Detached device remains accessible after successful detach and tenant rotation |
| Required discovery | Agent must identify which state surface enforces access and which only records audit/status |
| Hardness bar | Split encode/decode/enforce authorities reconcile under changing state |
| Verifier risk | Avoid toy checklist, blocklist, and one exploit-string tests by using generated scenarios and multiple principals/actions |

## 3. Safety and Realism Boundary

Do **not** use real `/dev` nodes, `mknod`, `udev`, cgroups, privileged Docker, `SYS_ADMIN`, `CAP_MKNOD`, or host mounts. The task should simulate device nodes as regular files plus metadata under `/app/var/lib/devhandoff/devices`. This preserves the authority-handoff reasoning without violating Docker safety rules.

Suggested simulated device concepts:

- `device_id`: stable logical name, such as `cam-front`, `tty-bridge`, `disk-cache`, `sensor-lab`.
- `node_path`: path under `/app/var/lib/devhandoff/devices/<device_id>.node`.
- `class`: `camera`, `serial`, `block`, `sensor`.
- `actions`: `read`, `write`, `ioctl`, `admin`.
- `tenant_id`: `tenant-red`, `tenant-blue`, `tenant-green`, etc.
- `generation`: monotonically increasing integer assigned by the admin state machine.

The code should feel like a stripped-down host device broker rather than a puzzle. Use product names like `devhandoff`, `lease`, `grant`, `export`, `runtime`, `checkpoint`, `audit`, and `tenant`.

## 4. Regular Task Structure

Create this directory layout:

```text
device-handoff-revocation/
├── instruction.md
├── task.toml
├── environment/
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── go.mod
│   ├── cmd/
│   │   └── devhandoff/
│   │       └── main.go
│   ├── internal/
│   │   ├── access/
│   │   │   ├── checker.go
│   │   │   └── decision.go
│   │   ├── admin/
│   │   │   ├── attach.go
│   │   │   ├── detach.go
│   │   │   ├── reload.go
│   │   │   └── restore.go
│   │   ├── audit/
│   │   │   ├── log.go
│   │   │   └── record.go
│   │   ├── checkpoint/
│   │   │   ├── checkpoint.go
│   │   │   └── replay.go
│   │   ├── config/
│   │   │   ├── config.go
│   │   │   └── defaults.go
│   │   ├── export/
│   │   │   ├── grants.go
│   │   │   ├── status.go
│   │   │   └── writer.go
│   │   ├── model/
│   │   │   ├── device.go
│   │   │   ├── grant.go
│   │   │   ├── lease.go
│   │   │   └── tenant.go
│   │   ├── paths/
│   │   │   └── paths.go
│   │   ├── store/
│   │   │   ├── files.go
│   │   │   ├── journal.go
│   │   │   ├── state.go
│   │   │   └── atomic.go
│   │   └── version/
│   │       └── version.go
│   ├── configs/
│   │   ├── devices.json
│   │   ├── tenants.json
│   │   └── policy.json
│   ├── fixtures/
│   │   ├── seed-events.jsonl
│   │   ├── legacy-checkpoint.json
│   │   └── rotated-tenants.json
│   └── scripts/
│       ├── build.sh
│       ├── reset_state.sh
│       ├── replay_handoff.sh
│       ├── reload_restore.sh
│       └── inspect_status.sh
├── solution/
│   └── solve.sh
└── tests/
    ├── test.sh
    └── test_outputs.py
```

This gives the agent 30+ meaningful environment files, satisfying the `small` codebase floor without padding. Do not include `tests/` or `solution/` inside `environment/` or copy them into the Docker image.

## 5. Public `instruction.md`

Keep the prompt concise and symptoms-only. Do not include the task name in the instruction.

Recommended `instruction.md`:

```md
The device handoff simulator in `/app/device-broker` is leaking detached device access across tenant rotation. You can reproduce the public failure with `/app/scripts/replay_handoff.sh leak-after-reload`: the detach command exits successfully and `/app/var/log/devhandoff/audit.jsonl` records the device as detached, but after `/app/scripts/reload_restore.sh` a later access check can still open the same device.

Fix the implementation under `/app/device-broker` so attach, detach, reload, and restore preserve least-privilege device access. After the fix, `/app/bin/devhandoff status --json` and `/app/var/lib/devhandoff/exports/status.json` must agree on active device access; detached devices must be denied to every tenant until explicitly reattached; audit entries must report the same final decision returned by access checks; and rerunning the replay scripts must be idempotent.
```

Publicly disclosed:

- Admin reproduction command.
- Reload/restore scenario.
- Public log path.
- Durable status artifact path.
- Observable allowed/denied behavior.

Not disclosed:

- Which internal surface is stale.
- Which package contains the vulnerable enforcement decision.
- The exact restoration ordering bug.
- The exact generation comparison rule.
- The patch locus.

## 6. `task.toml` Draft

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
tags = ["device-access", "state-recovery", "least-privilege", "audit", "replay"]
expert_time_estimate_min = 150
junior_time_estimate_min = 360

[agent]
timeout_sec = 1200.0

[verifier]
timeout_sec = 450.0

[environment]
build_timeout_sec = 900.0
cpus = 2
memory_mb = 4096
storage_mb = 10240
allow_internet = false
```

Do not set `custom_docker_compose` or `is_multi_container`. This task should be single-container.

## 7. Docker Environment Plan

Use a digest-pinned Go image, for example:

```dockerfile
FROM golang:1.22-bookworm@sha256:<resolved-digest>

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        coreutils \
        jq \
        python3 \
        python3-pip \
        tmux \
        asciinema \
    && rm -rf /var/lib/apt/lists/*

COPY go.mod /app/device-broker/go.mod
COPY cmd/ /app/device-broker/cmd/
COPY internal/ /app/device-broker/internal/
COPY configs/ /app/device-broker/configs/
COPY fixtures/ /app/device-broker/fixtures/
COPY scripts/ /app/scripts/

RUN chmod +x /app/scripts/*.sh \
    && cd /app/device-broker \
    && go build -trimpath -o /app/bin/devhandoff ./cmd/devhandoff

ENV DEVHANDOFF_ROOT=/app/var/lib/devhandoff
ENV DEVHANDOFF_LOG=/app/var/log/devhandoff/audit.jsonl
```

Notes:

- Resolve and pin the real digest before submission.
- Pin any Go module versions and commit `go.sum` if dependencies are added.
- Prefer no external Go dependencies; the standard library is enough.
- If using `pip`, pin verifier packages exactly at build time, such as `pytest==8.3.3` and `pytest-json-ctrf==0.3.5`. Do not install verifier dependencies from `tests/test.sh`.
- Do not create `/tests`, `/solution`, or `/oracle` in the Dockerfile.
- Include `.dockerignore` with `.git`, build outputs, caches, `solution/`, `tests/`, `.venv/`, `node_modules/`, and temporary logs.

## 8. CLI Surface to Implement

The agent-visible CLI should be realistic and discoverable:

```bash
/app/bin/devhandoff seed --reset
/app/bin/devhandoff attach --tenant tenant-red --device cam-front --actions read,ioctl
/app/bin/devhandoff detach --tenant tenant-red --device cam-front
/app/bin/devhandoff check --tenant tenant-red --device cam-front --action read
/app/bin/devhandoff rotate --from tenant-red --to tenant-blue
/app/bin/devhandoff checkpoint --name before-rotate
/app/bin/devhandoff reload
/app/bin/devhandoff restore --name before-rotate
/app/bin/devhandoff status --json
/app/bin/devhandoff audit --tail 20
```

Exit-code convention:

- `check` exits `0` for allow.
- `check` exits `13` for deny.
- Admin commands exit `0` on success.
- Malformed commands exit `2`.

Keep this convention documented in CLI help and in the public prompt only as far as needed.

## 9. State Surfaces

Use these durable/runtime paths:

```text
/app/var/lib/devhandoff/state/leases.json
/app/var/lib/devhandoff/state/devices.json
/app/var/lib/devhandoff/state/tenants.json
/app/var/lib/devhandoff/state/events.jsonl
/app/var/lib/devhandoff/runtime/grants.json
/app/var/lib/devhandoff/checkpoints/<name>.json
/app/var/lib/devhandoff/exports/grants.json
/app/var/lib/devhandoff/exports/status.json
/app/var/log/devhandoff/audit.jsonl
```

State roles:

| Surface | Role | Agent-Visible? | Mutable by Program? |
|---|---|---:|---:|
| `leases.json` | Durable active lease state | Yes | Yes |
| `events.jsonl` | Durable admin/event journal | Yes | Yes |
| `runtime/grants.json` | Decoded access-check state | Yes | Yes |
| `exports/grants.json` | Exported grant snapshot | Yes | Yes |
| `exports/status.json` | User-visible status artifact | Yes | Yes |
| `audit.jsonl` | Public audit trace | Yes | Yes |
| checkpoint files | Restore basis plus replay input | Yes | Yes |

Verifier ground truth must not be a static expected output stored in `/app`. Tests should derive expected behavior from commands and generated scenarios.

## 10. Status and Audit Schemas

### `/app/var/lib/devhandoff/exports/status.json`

```json
{
  "state_epoch": 17,
  "active": [
    {
      "tenant_id": "tenant-red",
      "device_id": "cam-front",
      "actions": ["ioctl", "read"],
      "generation": 4,
      "node_path": "/app/var/lib/devhandoff/devices/cam-front.node"
    }
  ],
  "detached": [
    {
      "tenant_id": "tenant-red",
      "device_id": "cam-front",
      "generation": 5
    }
  ]
}
```

Rules:

- `state_epoch` is an integer derived from the event journal, not wall-clock time.
- `active` is sorted by `tenant_id`, then `device_id`.
- `actions` is sorted alphabetically.
- Detached devices never appear in `active` unless explicitly attached again at a newer generation.

### `/app/var/log/devhandoff/audit.jsonl`

Each line is JSON:

```json
{"seq":12,"event":"check","tenant_id":"tenant-blue","device_id":"cam-front","action":"read","decision":"deny","generation":5,"reason":"no-active-grant"}
```

Rules:

- `seq` is monotonic.
- `decision` is `allow`, `deny`, or `n/a` for admin-only events.
- A `check` audit line must match the actual exit status and stdout decision of the check command.
- Detach events must be visible as admin events.

## 11. Intended Initial Bug Design

This section is for the task author and oracle only. Do not reveal it in `instruction.md`.

Create a bug where detach updates the durable lease file and audit/status export, but a reload/restore path rebuilds access-check runtime grants from a stale export or checkpoint snapshot before applying the revocation side of the event journal. This makes visible status look correct while the access checker still uses an older grant.

Make the bug subtle by splitting responsibilities:

1. `internal/admin/detach.go` records a detach event and removes the lease.
2. `internal/export/status.go` writes status from durable leases.
3. `internal/access/checker.go` checks runtime decoded grants.
4. `internal/admin/reload.go` refreshes runtime grants.
5. `internal/checkpoint/replay.go` replays some events after restore, but mishandles detach or generation ordering.
6. `internal/audit/log.go` records audit lines from the command layer unless patched to record the final enforcement decision.

A naive solution that only edits detach, only deletes one cache file, or blocklists one device name should fail.

## 12. Correct Fix Intent

The correct fix should make all externally visible and enforcement surfaces derive from the same current state after attach, detach, reload, and restore.

Acceptable implementation strategies:

- Rebuild runtime grants only from active durable leases after all journal replay is complete.
- Treat detach events as generation-bearing revocations that dominate older grants.
- Make restore load checkpoint state and then replay subsequent journal events in order.
- Make audit check records use the final decision returned by the same access evaluator used by `check`.
- Make status export and CLI status share the same normalized state view.
- Use atomic writes for JSON state files to avoid partial status/grant divergence.

Do not require one exact implementation. The verifier should grade behavior.

## 13. Replay Scripts

### `/app/scripts/reset_state.sh`

- Removes `/app/var/lib/devhandoff` and `/app/var/log/devhandoff`.
- Runs `/app/bin/devhandoff seed --reset`.
- Creates simulated device-node files.

### `/app/scripts/replay_handoff.sh leak-after-reload`

Scenario:

1. Reset state.
2. Attach `cam-front` to `tenant-red` with `read,ioctl`.
3. Verify `tenant-red` can read.
4. Create checkpoint `attached-red`.
5. Detach `cam-front` from `tenant-red`.
6. Rotate to `tenant-blue`.
7. Run `/app/scripts/reload_restore.sh`.
8. Check `tenant-blue` and `tenant-red` access.
9. Print audit tail and status JSON.

Before the fix, this should show at least one unauthorized allow after restore. After the fix, both old and next tenants are denied unless an explicit newer attach occurs.

### `/app/scripts/reload_restore.sh`

- Runs `/app/bin/devhandoff reload`.
- Runs `/app/bin/devhandoff restore --name attached-red`.
- Runs `/app/bin/devhandoff reload` again.
- Writes status export.

This deliberately exercises decode/reload/replay ordering.

## 14. Verifier Design

Use `tests/test_outputs.py` with pytest. Tests should invoke the CLI and scripts in isolated roots where possible using `DEVHANDOFF_ROOT` and `DEVHANDOFF_LOG` environment variables. This prevents hardcoded fixture-only fixes.

Suggested tests:

### `test_public_replay_denies_detached_device_after_reload`

Purpose: public scenario from `instruction.md`.

Checks:

- `/app/scripts/replay_handoff.sh leak-after-reload` exits successfully after the fix.
- `check` for the detached device denies both old and rotated tenants after reload/restore.
- Audit tail contains `check` lines whose `decision` values match command results.
- Status CLI and status export have no active grant for the detached device.

### `test_checkpoint_restore_replays_detach_after_checkpoint`

Purpose: restore must not resurrect pre-detach access.

Deterministic scenario in a temporary root:

1. Seed.
2. Attach device to tenant A.
3. Check allow.
4. Checkpoint.
5. Detach.
6. Restore checkpoint.
7. Reload.
8. Check tenant A deny.

Expected outcome is computed from the command sequence, not from a golden file.

### `test_reattach_requires_newer_explicit_grant`

Purpose: prevent overbroad deny fixes that permanently block devices.

Scenario:

1. Attach device to tenant A with `read`.
2. Detach tenant A.
3. Check tenant A deny.
4. Attach same device to tenant B with `read,ioctl`.
5. Check tenant B read/ioctl allow.
6. Check tenant B write deny.
7. Check tenant A read deny.

### `test_status_and_audit_share_access_decision`

Purpose: audit must not only record requested/intended action; it must match enforcement.

Checks:

- For several `check` calls, parse stdout and exit code.
- Parse latest audit lines.
- Assert audit `decision` equals actual decision.
- Assert status active grants agree with allowed checks.

### `test_generated_device_and_tenant_names_are_supported`

Purpose: reject blocklists and fixture-specific patches.

Use deterministic generated names, such as:

```text
tenant-orchid-17
tenant-cobalt-23
device-sensor-91
device-serial-42
```

Create a temporary config, seed it, attach/detach/reload/restore, and assert the same invariants. Do not use random unseeded data.

### `test_replay_scripts_are_idempotent`

Purpose: rerunning admin workflows should not duplicate active grants or drift status.

Run the public replay twice from a clean state. Parse status and audit. Assert:

- No duplicate active grant tuple `(tenant_id, device_id, action)`.
- Detached grant remains denied.
- `state_epoch` is monotonic and not reset by reload.
- Export status is valid JSON and sorted.

### `test_no_static_artifact_solution`

Purpose: reject solutions that manually write `/app/var/lib/devhandoff/exports/status.json`.

Run a fresh generated scenario in a different root and verify behavior there. A static artifact written for the public fixture should not affect this scenario.

## 15. `tests/test.sh` Pattern

Use the canonical reward-safe structure:

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

If the platform requires CTRF output, install and use the pinned CTRF plugin in the Dockerfile, not in `test.sh`.

## 16. Oracle Solution Plan

`solution/solve.sh` should be deterministic, use fail-fast mode, and patch the real source rather than writing final artifacts.

High-level oracle steps:

```bash
#!/usr/bin/env bash
set -euo pipefail

cd /app/device-broker

# Apply source edits to normalize restore/reload/enforcement state flow.
# Use sed/cat/python/perl as needed, but patch source rather than tests or outputs.

# Rebuild.
go test ./...
go build -trimpath -o /app/bin/devhandoff ./cmd/devhandoff

# Verify public scenario manually before tests.
/app/scripts/replay_handoff.sh leak-after-reload
/app/bin/devhandoff status --json >/tmp/devhandoff-status.json
jq . /tmp/devhandoff-status.json >/dev/null
```

The actual oracle patch should:

- Load checkpoint state, then replay all later journal events in order.
- Ensure detach/revocation events remove matching runtime grants and dominate older grant exports.
- Rebuild runtime grants from normalized active leases after restore and reload.
- Make CLI status and exported status call the same status builder.
- Make check audit records use the final access decision.
- Preserve valid reattach behavior for a newer explicit grant.

Do not hardcode the public fixture or expected output.

## 17. Internal Go Test Suggestions

Add Go unit tests under `environment/internal/...` only if they are part of the codebase and agent-visible. They should help an expert diagnose behavior but must not reveal the exact fix.

Examples:

- `internal/store/state_test.go`: atomic write/read round trip.
- `internal/export/status_test.go`: stable sorting.
- `internal/access/decision_test.go`: deny when no grant exists.

Avoid a test named `TestRestoreUsesStaleGrantExport` or any name that leaks the root cause.

## 18. Anti-Cheating and Hardness Controls

| Collapse Risk | Mitigation |
|---|---|
| One exploit string verifier | Use generated tenant/device names and multiple workflows. |
| Blocklist patch | Test new devices and tenants not in fixtures. |
| Static status artifact write | Run tests in temporary roots and call the CLI repeatedly. |
| Delete-cache-only fix | Test restore from checkpoint plus journal replay. |
| Overbroad deny-all fix | Test explicit reattach to a new tenant with action-specific grants. |
| Audit-only fix | Compare actual access decisions to audit and status surfaces. |
| Prompt leak | Public instruction names symptoms and paths only, not stale authority or patch file. |
| Hidden contract | Status schema and observable access behavior are documented. |
| Flaky timing | No sleeps, daemons, real udev, or wall-clock assertions. |

## 19. Step-2a Validation Blocks

```yaml
platform_files:
  - path: task.toml
    role: metadata, timeouts, system-administration category, Go/Bash language declaration
  - path: instruction.md
    role: concise public prompt with reproduction command and observable success contract
  - path: environment/Dockerfile
    role: reproducible single-container Go/Bash runtime
  - path: tests/test.sh
    role: reward-safe verifier entrypoint
  - path: tests/test_outputs.py
    role: deterministic behavioral verifier
  - path: solution/solve.sh
    role: deterministic oracle implementation

task_files:
  - path: /app/device-broker/cmd/devhandoff/main.go
    role: CLI entrypoint
  - path: /app/device-broker/internal/admin/
    role: admin attach/detach/reload/restore flows
  - path: /app/device-broker/internal/access/
    role: access-check decision surface
  - path: /app/device-broker/internal/audit/
    role: audit trace writer
  - path: /app/device-broker/internal/checkpoint/
    role: checkpoint and journal replay
  - path: /app/device-broker/internal/export/
    role: status and grant exports
  - path: /app/scripts/replay_handoff.sh
    role: public reproduction harness
  - path: /app/scripts/reload_restore.sh
    role: public reload/restore workflow

fix_frontier:
  count: 5-8 files
  distribution: access decision, admin detach, reload/restore, checkpoint replay, status export, audit writer, store atomic writes
  naming_policy: product subsystem names only; avoid names that reveal stale-authority or exploit primitive
  forbidden_stems: ["stale", "vulnerable", "exploit", "backdoor", "oracle", "answer"]
  helpers_policy: helpers must be reusable product concepts, not one-scenario patches
  symbol_thin_preferred: true

contract_surface:
  boolean_fields_max: 0
  direct_boolean_assertions_max: 0
  preferred_assertion_styles: ["access decision equivalence", "status/export semantic agreement", "journal replay invariants", "least-privilege action checks"]
  forbidden_assertion_styles: ["single exploit string", "device-name blocklist", "source grep", "golden status file only"]

category_profile:
  bug_family: device authority handoff
  profile_name: security_authority_split
  allowed_instruction_disclosures: assets, principals, allowed/denied actions, audit traces, authority boundary, admin command, reload/restore scenario, public logs, durable artifacts
  forbidden_instruction_leaks: vulnerable sink, trust-boundary location, exploit primitive, patch rule, stale authority, exact patch file, generation edge
  category_specific_hardness_bar: split encode/decode/enforce authorities must reconcile under attach, detach, reload, restore, and reattach
  category_specific_verifier_risks: toy checklist, blocklist bypass, one exploit-string verifier
  coverage_role: distinct system-administration topology around simulated udev container handoff without privileged Docker

satisfiability_risk:
  rc2_planned_name_risk: low; use product subsystem names and keep exact fix symbols out of public prompt
  gx9_contract_risk: low; prompt describes observable invariants rather than scenario-to-verdict table
  cr1_symbol_frontier_risk: medium; keep exact stale/enforcement symbols out of instruction and visible filenames where practical
  hidden_contract_risk: low; commands, output paths, and schemas are visible without naming the patch locus

actionability_plan:
  verifier_command_visible: expose /app/scripts/replay_handoff.sh leak-after-reload and /app/scripts/reload_restore.sh
  source_fix_intent_visible: no; orient only to /app/device-broker implementation
  generated_output_rule_visible: name regenerated status export, audit log, replay traces, and deny static/manual artifact writes through generated tests
  exact_formula_home: not applicable; no numeric formula beyond documented state_epoch sequencing
  schema_home: instruction.md plus visible CLI/status documentation and the status/audit schemas in code comments

waiver_plan:
  waivers_expected: no
  waiver_rationale: no waiver needed if Docker remains unprivileged and tests are deterministic

reference_pattern:
  reference_task_id: none
  justification_if_none: no promoted reference task is available; this plan builds a standalone topology

realism_source:
  source_type: real_bug-inspired
  evidence_basis: local minimized reproduction plus optional private source note before final submission
  upstream_or_synthetic_rationale: modeled on recurring device handoff and revocation freshness failures, implemented as a safe local simulator
  minimization_preserves: multi-surface state, reload/restore, misleading green audit/status surface, least-privilege enforcement
  synthetic_exception_review: not required if a concrete real-bug source note is attached before submission; otherwise review as synthetic-realistic
```

## 20. Difficulty Calibration

This task should remain hard because an agent must:

1. Reproduce the failure through the provided scripts.
2. Inspect a Go codebase with separate admin, access, export, audit, checkpoint, and store packages.
3. Notice that visible audit/status success does not imply enforcement correctness.
4. Understand attach/detach/reload/restore/reattach state transitions.
5. Preserve least-privilege action behavior rather than deny-all.
6. Handle generated tenants/devices without blocklists.
7. Make durable state, runtime state, status export, and audit decisions agree.
8. Avoid manual artifact writes because tests create new roots and scenarios.

Expected good agent failures:

- Fixes status export but not runtime access checks.
- Fixes detach only, but restore resurrects old grants.
- Deletes the runtime grant file on detach, but checkpoint replay still rebuilds it.
- Blocks the public device name but fails generated devices.
- Denies all access after detach and fails explicit reattach.
- Records audit deny while access command still exits allow.

Bad failures to avoid:

- Missing dependencies.
- Real device permission errors.
- Timing races or sleeps.
- Tests enforcing behavior not in the prompt or visible schemas.
- Public prompt naming the exact broken file/function.

## 21. Review Checklist Before Submission

- [ ] Regular task skeleton only; no milestones, no UI, no multi-container.
- [ ] `instruction.md` is 1-2 paragraphs, uses absolute paths, and gives the what rather than the how.
- [ ] Instruction does not contain the task name, patch locus, stale authority, exploit primitive, or exact generation rule.
- [ ] Environment has 20+ meaningful files under `environment/` excluding Dockerfile/compose.
- [ ] `task.toml` uses `difficulty = "hard"`, `category = "system-administration"`, `codebase_size = "small"`, `languages = ["go", "bash"]`.
- [ ] Docker base image is digest-pinned.
- [ ] Docker installs `tmux` and `asciinema`.
- [ ] No `solution/`, `tests/`, `/oracle`, `/solution`, or `/tests` are created or copied in Dockerfile.
- [ ] No runtime web access.
- [ ] No privileged mode or real host device operations.
- [ ] Oracle patches source and rebuilds, not static artifacts.
- [ ] Verifier tests behavior, not implementation strings.
- [ ] `tests/test.sh` always writes `/logs/verifier/reward.txt` with `0` or `1`.
- [ ] NOP fails.
- [ ] Oracle passes repeatedly.
- [ ] Generated scenario tests defeat fixture-specific fixes.
- [ ] Tests cover public replay, restore replay, reattach, action classes, audit/status consistency, and idempotency.

## 22. Submission Rubric Draft

Use this in the submission UI, not inside the task directory:

```text
Agent identifies that successful detach/audit output is insufficient and verifies the actual access-check behavior after reload or restore, +3
Agent preserves least-privilege action handling so reattached tenants receive only explicitly granted actions, +3
Agent updates the implementation so durable leases, runtime grants, status export, and CLI status agree after attach, detach, reload, restore, and reattach, +5
Agent makes checkpoint restore replay later detach events without resurrecting older grants, +5
Agent ensures audit check records match the final access decision returned by the access checker, +3
Agent keeps the replay scripts idempotent without duplicate active grants or state reset, +2
Agent rebuilds and validates the Go binary from source rather than manually editing output artifacts, +2
Agent hardcodes public tenant or device names instead of fixing generated scenarios, -5
Agent implements a deny-all shortcut that breaks explicit reattach or valid allowed actions, -5
Agent only changes audit/status output while access checks still allow revoked grants, -5
Agent edits verifier, oracle, or reserved task directories to force success, -5
Agent introduces timing-dependent sleeps, background daemons, or privileged device operations, -3
```

Positive total: 23 points. Negative criteria: 5 distinct penalties.
