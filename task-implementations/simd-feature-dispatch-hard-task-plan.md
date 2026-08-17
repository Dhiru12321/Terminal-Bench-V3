# SIMD Feature Dispatch — Hard Task Implementation Plan

## GO decision

This seed is strong enough for a **Hard Project Terminus task** if it is implemented as a **debugging + build/toolchain cache invalidation** task, not as a simple SIMD math bug.

The hardness should come from diagnosing a mismatch across:

```text
CPU feature report → generated dispatch artifact → copied runtime bundle → replay metadata → runtime dispatcher
```

The public symptom should remain: the obvious diagnostic looks correct, but replayed or variant execution paths fail nonlocally.

---

## Task title

Use a subsystem-level name that does **not** reveal the fix path:

```text
simd-dispatch-replay-drift
```

Avoid names such as:

```text
generated-dispatch-cache-fix
mask-cache-dependency-bug
stale-dispatch-object
```

Those names collapse the task by revealing the causal surface.

---

## Final task shape

Use a **regular non-milestone task**, not a multi-container or UI task.

```text
simd-dispatch-replay-drift/
├── instruction.md
├── task.toml
├── output_contract.toml
├── environment/
│   ├── Dockerfile
│   ├── .dockerignore
│   └── app/
│       ├── CMakeLists.txt
│       ├── build.ninja.in
│       ├── include/
│       ├── src/
│       ├── kernels/
│       ├── tools/
│       ├── profiles/
│       ├── fixtures/
│       ├── scripts/
│       └── docs/
├── solution/
│   └── solve.sh
└── tests/
    ├── test.sh
    └── test_outputs.py
```

Keep the agent-facing codebase at **20+ real files**. Do not pad the tree with irrelevant files.

---

## Agent-facing story

Build a small C++ vector runtime with a simulated CPU feature mask. The runtime has three execution paths:

1. **Clean execution** after a fresh build.
2. **Incremental execution** after changing the CPU feature mask and rebuilding.
3. **Replay execution** from a saved run record.

The visible CPU report should show the active mask correctly, but the runtime can still execute a stale dispatch path on replay or non-default variants.

The agent must fix the system so clean, incremental, reversed-mask, and replayed runs all agree.

---

## Public `instruction.md`

Keep this short, symptoms-only, and absolute-path based. Do not include function names, generated object names, cache paths, or exact dependency edges.

Suggested content:

```md
The SIMD runtime in `/app/simd-lab` reports the requested CPU feature mask correctly after rebuilds, but replayed runs and non-default vector variants can still produce inconsistent dispatch traces.

Fix the project so `/app/simd-lab/scripts/run_matrix.sh` produces deterministic records under `/app/simd-lab/out` for clean, incremental, and replayed executions after changing the CPU feature mask. Each record must be derived from the actual runtime execution and include the reported mask, selected kernel family, input digest, result digest, and replay source when applicable.

Do not replace the runtime or generated records with hardcoded outputs.
```

Why this is safe:

- It reveals observable contract and output schema.
- It reveals artifact identities and run shape.
- It does **not** reveal resolver bug, cache path, generated-file source, exact package edge, or missing build dependency.
- It avoids a truth table such as “scenario A must select AVX2, scenario B must select scalar.”

---

## Hidden implementation design

Creator-only detail; do **not** put this in `instruction.md`.

The simulated CPUID report reads the current mask from:

```text
/app/simd-lab/profiles/active-mask.json
```

But the runtime dispatcher does not use that file directly. It uses a generated dispatch table embedded in a runtime bundle:

```text
/app/simd-lab/build/generated/dispatch_table.cpp
/app/simd-lab/build/libsimd_runtime.a
/app/simd-lab/out/runtime-bundle/dispatch.snapshot
```

The build graph has a stale edge:

```text
profiles/active-mask.json
  updates cpuid report
  does NOT invalidate generated dispatch table or replay snapshot
```

After changing the mask and rebuilding:

- `/app/simd-lab/bin/simd-lab diagnose` looks correct.
- Clean rebuild passes.
- Incremental rebuild can reuse a stale dispatch artifact.
- Replay path can load the old runtime-bundle snapshot.
- Unit-vector smoke tests pass because scalar/SSE/AVX kernels return the same digest on trivial inputs.
- Long or variant inputs expose the wrong selected kernel/result digest.

This preserves the seed’s **dispatch cache shadow** topology.

---

## Codebase layout

Use C++17 for the runtime and Python only for fixture/build helper scripts.

```text
/app/simd-lab/
├── CMakeLists.txt
├── include/
│   ├── cpuid_report.hpp
│   ├── dispatch_record.hpp
│   ├── dispatcher.hpp
│   ├── digest.hpp
│   └── vector_io.hpp
├── src/
│   ├── main.cpp
│   ├── cpuid_report.cpp
│   ├── dispatcher.cpp
│   ├── dispatch_record.cpp
│   ├── digest.cpp
│   ├── replay.cpp
│   └── vector_io.cpp
├── kernels/
│   ├── scalar_kernel.cpp
│   ├── sse2_kernel.cpp
│   ├── avx2_kernel.cpp
│   └── kernel_registry.hpp
├── tools/
│   ├── gen_dispatch.py
│   ├── inspect_record.py
│   ├── make_fixture.py
│   └── mutate_mask.py
├── profiles/
│   ├── active-mask.json
│   ├── scalar.json
│   ├── sse2.json
│   └── avx2.json
├── fixtures/
│   ├── unit.vec
│   ├── ramp.vec
│   ├── alternating.vec
│   └── unaligned.vec
├── scripts/
│   ├── configure_mask.sh
│   ├── build_runtime.sh
│   ├── run_matrix.sh
│   └── replay_record.sh
└── docs/
    └── record_schema.md
```

The schema doc is allowed because it describes observable records, not the fix location.

---

## Runtime behavior

The binary should support these modes:

```bash
/app/simd-lab/bin/simd-lab diagnose
/app/simd-lab/bin/simd-lab run --fixture /app/simd-lab/fixtures/ramp.vec --variant dot --record /app/simd-lab/out/run.json
/app/simd-lab/bin/simd-lab replay --record /app/simd-lab/out/run.json --record-out /app/simd-lab/out/replay.json
```

Public records should be JSON, not verdict booleans:

```json
{
  "schema_version": 1,
  "mode": "run",
  "reported_mask": ["sse2", "avx2"],
  "selected_kernel_family": "avx2",
  "fixture_name": "ramp.vec",
  "variant": "dot",
  "input_digest": "sha256:...",
  "result_digest": "sha256:...",
  "replay_source": null
}
```

For replay:

```json
{
  "schema_version": 1,
  "mode": "replay",
  "reported_mask": ["sse2", "avx2"],
  "selected_kernel_family": "avx2",
  "fixture_name": "ramp.vec",
  "variant": "dot",
  "input_digest": "sha256:...",
  "result_digest": "sha256:...",
  "replay_source": "/app/simd-lab/out/run.json"
}
```

Avoid answer-key fields such as:

```json
{
  "passed": true,
  "expected_kernel": "avx2",
  "cache_stale": false
}
```

---

## Buggy initial state

Seed the repo with these defects:

1. `diagnose` reads the active mask live, so it appears correct.
2. `gen_dispatch.py` emits dispatch metadata from the active mask.
3. `CMakeLists.txt` or `build_runtime.sh` does not declare the active mask/profile as an input to the generated dispatch source.
4. `run_matrix.sh` performs mask changes through normal scripts, not by directly editing generated files.
5. `replay.cpp` prefers the saved runtime bundle snapshot if present.
6. The smoke fixture `unit.vec` passes under every kernel.
7. `ramp.vec`, `alternating.vec`, and `unaligned.vec` expose divergence.

The oracle should fix the build graph and runtime invalidation behavior, not just delete the whole cache every time.

---

## Oracle solution plan

`solution/solve.sh` should:

1. Use `set -euo pipefail`.
2. Patch the build graph so dispatch generation depends on the mask/profile inputs.
3. Patch runtime bundle or replay metadata invalidation so replay cannot silently use dispatch metadata from a different mask.
4. Ensure generated records are regenerated through the normal pipeline.
5. Run the public matrix script and hidden verifier-relevant scenarios locally.
6. Avoid hardcoded output JSON.

The oracle must be deterministic, use absolute paths, avoid network calls, and actually solve the described task rather than writing final answers.

---

## Verifier plan

Use `pytest` in `tests/test_outputs.py`. Tests must be behavioral and deterministic, with informative docstrings. They should test final behavior rather than source patterns.

### Required verifier scenarios

Create around 14–18 tests:

1. `test_clean_matrix_writes_schema_valid_records`  
   Verifies records exist and match the public schema.

2. `test_diagnose_and_runtime_mask_agree_after_clean_build`  
   Compares reported mask to selected kernel family for clean scalar/SSE2/AVX2 profiles.

3. `test_incremental_mask_change_updates_runtime_dispatch`  
   Builds under scalar, switches to AVX2, rebuilds without deleting build dir, then verifies runtime selection/result digest changes consistently.

4. `test_incremental_downgrade_removes_retired_kernel_selection`  
   Builds under AVX2, switches to scalar, rebuilds incrementally, then verifies no stale AVX2 selection remains.

5. `test_replay_uses_current_compatible_dispatch_metadata`  
   Creates a record, changes mask, rebuilds, replays, and verifies replay record is consistent with the current legal mask behavior.

6. `test_unit_vector_smoke_is_not_sufficient`  
   Ensures the verifier also runs non-unit fixtures so trivial smoke-only fixes fail.

7. `test_ramp_variant_matches_independent_digest_oracle`  
   Computes expected digest from fixture data and public algorithm rules, not from a static golden output file.

8. `test_alternating_variant_matches_independent_digest_oracle`

9. `test_unaligned_variant_matches_independent_digest_oracle`

10. `test_repeated_runs_are_canonical_digest_stable`  
    Re-runs unchanged matrix and compares canonicalized records.

11. `test_reversed_mask_sequence_is_stable`  
    Executes AVX2→scalar→SSE2 and scalar→SSE2→AVX2 sequences, checking final records converge.

12. `test_partial_output_directory_does_not_poison_next_run`  
    Leaves old `/app/simd-lab/out/runtime-bundle` content and verifies normal scripts recover.

13. `test_records_are_generated_by_runtime_not_static_files`  
    Changes verifier-only fixture content and ensures digest changes accordingly.

14. `test_no_runtime_network_or_external_cpu_dependency`  
    Verifies execution uses local simulated masks and does not require actual AVX2 support.

15. `test_test_runner_writes_binary_reward`  
    Indirectly satisfied by `tests/test.sh`, but keep test runner logic correct.

### `tests/test.sh` pattern

```bash
#!/usr/bin/env bash
set +e

TEST_DIR="${TEST_DIR:-/tests}"

pytest "$TEST_DIR/test_outputs.py" -rA
status=$?

mkdir -p /logs/verifier
if [ "$status" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

exit "$status"
```

If using `pytest-json-ctrf`, install it in the Docker image rather than downloading it at verifier runtime.

---

## Anti-cheating protections

Add these protections:

- Do not copy `tests/`, `solution/`, or oracle files into the Docker image.
- Do not store expected final records in `/app`.
- Generate verifier-only fixtures inside `tests/test_outputs.py` or under `/tmp`, not in mutable agent-visible expected-output files.
- Compute expected digests from fixture bytes and record contents.
- Make dummy-program replacement fail by checking multiple modes: diagnose, run, replay, schema, digest, mask transitions, and regenerated records.
- Reject hardcoded outputs by mutating at least one fixture/mask in the verifier.
- Do not use source-grep tests unless there is a justified source-level contract.

---

## Docker/environment plan

Use a single container.

Recommended base:

```dockerfile
FROM debian:12-slim@sha256:<digest>
```

Install only packages needed for C++/CMake/Python verification:

```text
build-essential
cmake
ninja-build
python3
python3-pytest
tmux
asciinema
jq
```

Rules:

- Use `WORKDIR /app`.
- Copy only `environment/app` to `/app/simd-lab`.
- Do not create `/tests`, `/solution`, or `/oracle`.
- No `latest` base image.
- No privileged mode.
- No runtime web fetching.
- `allow_internet = false`.
- Include `.dockerignore`.
- Keep build context under size limits.

Suggested Dockerfile skeleton:

```dockerfile
FROM debian:12-slim@sha256:<digest>

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        ninja-build \
        python3 \
        python3-pytest \
        tmux \
        asciinema \
        jq \
    && rm -rf /var/lib/apt/lists/*

COPY app/ /app/simd-lab/

WORKDIR /app/simd-lab
```

---

## `task.toml` plan

```toml
version = "2.0"

[metadata]
author_name = "anonymous"
author_email = "anonymous"
category = "debugging"
subcategories = []
difficulty = "hard"
codebase_size = "small"
number_of_milestones = 0
languages = ["C++", "Python", "Bash"]
tags = ["simd", "build-cache", "generated-artifacts", "replay", "debugging"]
expert_time_estimate_min = 180
junior_time_estimate_min = 420

[agent]
timeout_sec = 1200

[verifier]
timeout_sec = 600

[environment]
build_timeout_sec = 900.0
cpus = 2
memory_mb = 4096
storage_mb = 10240
gpus = 0
gpu_types = []
allow_internet = false
```

Use the exact valid subcategory enum from your repo docs if your platform requires one. Otherwise keep `subcategories = []`.

---

## Hardness calibration

This task stays hard only if all of these remain true:

- The obvious diagnostic is green but not authoritative.
- The agent must inspect generated artifacts, build scripts, runtime dispatch, and replay logic.
- Clean builds alone are insufficient.
- Deleting all caches is not enough because replay and repeated-run stability are tested.
- Pinning/changing one dependency cannot solve it.
- The verifier includes at least two run shapes: clean and incremental/replayed.
- The public prompt does not name the generated dispatch object, cache path, missing dependency, or exact rebuild edge.

---

## Collapse risks to avoid

Do **not** put these in `instruction.md`:

```text
generated dispatch table is stale
CMake custom command misses active-mask.json
replay prefers stale dispatch.snapshot
fix gen_dispatch.py dependency inputs
delete build/generated/dispatch_table.cpp
```

Do **not** make tests only check:

```text
clean build
diagnose output
unit vector fixture
file exists
selected_kernel_family == one fixed value
```

That would turn the task into a medium/easy local patch.

---

## Suggested rubric

Use this in the submission UI, not inside the task folder.

```text
Agent investigates both the visible CPU feature report and the runtime dispatch records before editing files, +3
Agent identifies that clean builds are insufficient and tests an incremental mask-change rebuild path, +5
Agent fixes the build or generation dependency chain so dispatch metadata is regenerated when the mask profile changes, +5
Agent fixes replay behavior so stale runtime-bundle metadata cannot silently control later dispatch decisions, +5
Agent preserves runtime-derived JSON records instead of replacing them with static outputs, +3
Agent verifies at least one clean run, one incremental mask-change run, and one replayed run through the normal scripts, +5
Agent keeps the solution local and deterministic without network access or hardware SIMD assumptions, +3
Agent hardcodes output JSON records or selected kernel names instead of deriving them from runtime execution, -5
Agent only deletes build/output directories without repairing stale dependency or replay behavior, -3
Agent relies only on the unit-vector smoke case and misses non-default fixtures or variants, -3
Agent changes files under reserved verifier or solution paths, -5
Agent introduces hardware-dependent SIMD checks or latency thresholds, -3
```

Positive total: 29 points. Negative criteria: 5.

---

## Final acceptance checklist

Before submitting, verify:

- [ ] Oracle passes.
- [ ] NOP fails.
- [ ] At least one partial fix fails: clean-build-only fix, delete-cache-only fix, hardcoded-record fix.
- [ ] Tests cover clean, incremental, downgraded mask, replay, repeated run, reversed sequence, and verifier-only fixture.
- [ ] Every tested record field is documented in `instruction.md`, `docs/record_schema.md`, or visible code stubs.
- [ ] No hidden truth table exists.
- [ ] No hardware AVX/SSE dependency exists; masks are simulated.
- [ ] No latency/performance threshold exists.
- [ ] No runtime network exists.
- [ ] Docker does not copy tests/solution.
- [ ] `tests/test.sh` always writes binary reward.
- [ ] `task.toml` is complete and uses `difficulty = "hard"`.
- [ ] Public instruction remains symptoms-only and uses absolute paths.
