# Implementation Plan: Hard Regular Task — Non-Uniform Grid Numerical Solver Violates Conservation

## Task Name

`repair-nonuniform-fvm-conservation`

## Task Type

- **Category:** `scientific-computing`
- **Subcategories:** `[]`
- **Difficulty target:** Hard
- **Task style:** Regular task, not milestone
- **Codebase size:** `small`
- **Primary languages:** C++, Bash
- **Do not prefer Python:** The task application, oracle, and verifier should avoid Python. Use C++ utilities and Bash tests.
- **Suggested tags:** `cpp`, `finite-volume`, `numerical-solver`, `conservation`, `checkpoint`, `nonuniform-grid`

## 1. Task Goal

Create a hard regular Project Terminus task where a 2D finite-volume simulation appears correct on square uniform grids but violates conservation on rectangular non-uniform grids with mixed boundary conditions.

The agent must repair:

1. Flux scaling on non-uniform cells.
2. Boundary face handling for mixed boundary conditions.
3. Restart/checkpoint metadata for non-uniform grids.
4. Deterministic output and stable finite values.
5. Conservation invariants for clean and restarted runs.

The task should be difficult because a simple uniform-grid regression test passes even though the solver is numerically wrong for realistic grid geometry.

## 2. Why This Should Be Hard

This task should require real numerical and engineering reasoning.

The difficulty should come from interacting issues:

- Flux terms use a uniform `dx`/`dy` assumption even when spacing varies by cell.
- Face areas and cell volumes are mixed up for rectangular cells.
- Neumann boundaries are applied with the wrong sign or wrong face length.
- Dirichlet boundaries are applied as if all cells have equal spacing.
- Restart checkpoint files store field values but not grid spacing or boundary metadata.
- Restarted simulations use default uniform spacing after load.
- Uniform square-grid tests pass, hiding the real issue.
- Non-uniform rectangular cases fail conservation only after several timesteps.
- Floating-point tests require tolerances and invariants, not exact static outputs.

Likely weak agent fixes:

- Hardcodes expected output for one config.
- Reduces timestep or clamps values instead of fixing fluxes.
- Fixes `dx` but not `dy`.
- Fixes interior fluxes but not boundary fluxes.
- Fixes clean runs but not restart metadata.
- Makes conservation pass by disabling updates.
- Changes output precision but not solver correctness.
- Adds a tolerance workaround instead of preserving the invariant.

## 3. Regular Task Structure

Use the regular skeleton.

```text
repair-nonuniform-fvm-conservation/
├── instruction.md
├── task.toml
├── environment/
│   ├── Dockerfile
│   ├── CMakeLists.txt
│   └── app/
│       ├── README.md
│       ├── CMakeLists.txt
│       ├── src/
│       │   ├── main.cpp
│       │   ├── grid.cpp
│       │   ├── grid.hpp
│       │   ├── boundary.cpp
│       │   ├── boundary.hpp
│       │   ├── solver.cpp
│       │   ├── solver.hpp
│       │   ├── checkpoint.cpp
│       │   ├── checkpoint.hpp
│       │   ├── config.cpp
│       │   ├── config.hpp
│       │   ├── output.cpp
│       │   └── output.hpp
│       ├── configs/
│       │   ├── uniform.ini
│       │   ├── rectangular.ini
│       │   ├── mixed-boundary.ini
│       │   ├── restart-clean.ini
│       │   └── restart-from-checkpoint.ini
│       ├── reference/
│       │   ├── README.md
│       │   └── invariants.txt
│       ├── tools/
│       │   ├── check_invariants.cpp
│       │   ├── compare_runs.cpp
│       │   ├── make_grid_case.cpp
│       │   └── summarize_output.cpp
│       └── output/
│           └── .gitkeep
├── solution/
│   └── solve.sh
└── tests/
    ├── test.sh
    └── test_outputs.sh
```

Notes:

- No Python files are used.
- The verifier uses Bash plus compiled C++ checking tools.
- The task remains regular: no `steps/` directory.
- The codebase is `small`, not `minimal`.

## 4. `task.toml` Plan

Use `codebase_size = "small"` because `minimal` is not acceptable.

```toml
version = "2.0"

[metadata]
author_name = "anonymous"
author_email = "anonymous"
difficulty = "hard"
category = "scientific-computing"
subcategories = []
number_of_milestones = 0
codebase_size = "small"
languages = ["cpp", "bash"]
tags = ["cpp", "finite-volume", "nonuniform-grid", "checkpoint", "conservation", "numerical-solver"]
expert_time_estimate_min = 120
junior_time_estimate_min = 240

[verifier]
timeout_sec = 600.0

[agent]
timeout_sec = 1500.0

[environment]
build_timeout_sec = 900.0
cpus = 2
memory_mb = 4096
storage_mb = 10240
allow_internet = false
```

## 5. Docker Environment Plan

Use a single-container C++ environment.

### Dockerfile requirements

The Dockerfile should:

- Use a specific versioned base image.
- Set `WORKDIR /app`.
- Install `tmux` and `asciinema`.
- Install C++ build tools.
- Install CMake.
- Install Bash/coreutils.
- Copy only application files.
- Never copy `tests/` or `solution/`.
- Avoid runtime network fetching.
- Avoid privileged mode.

Example:

```dockerfile
FROM debian:bookworm-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        build-essential \
        cmake \
        coreutils \
        findutils \
        tmux \
        asciinema \
    && rm -rf /var/lib/apt/lists/*

COPY app/ /app/

RUN cmake -S /app -B /app/build \
    && cmake --build /app/build --target heat2d check_invariants compare_runs summarize_output
```

No dependencies should be fetched at test runtime.

## 6. Initial Buggy Application Design

The application should be a compact but realistic C++ finite-volume heat/diffusion solver.

### `/app/src/grid.hpp` and `/app/src/grid.cpp`

Represent a 2D grid.

Fields:

- `nx`, `ny`
- `x_faces`, `y_faces`
- `dx(i) = x_faces[i+1] - x_faces[i]`
- `dy(j) = y_faces[j+1] - y_faces[j]`
- `cell_volume(i, j) = dx(i) * dy(j)`
- cell-centered values

Initial bug options:

- stores `dx0` and `dy0` from the first cell and reuses them everywhere
- computes volume as `dx0 * dy0`
- uses `nx` when indexing `ny` for rectangular grids
- assumes square grid in serialization

Buggy shape:

```cpp
double Grid::dx(int) const {
    return x_faces_[1] - x_faces_[0]; // BUG: ignores non-uniform spacing
}

double Grid::dy(int) const {
    return y_faces_[1] - y_faces_[0]; // BUG: ignores non-uniform spacing
}

double Grid::volume(int, int) const {
    return dx(0) * dy(0); // BUG: wrong for non-uniform cells
}
```

### `/app/src/boundary.hpp` and `/app/src/boundary.cpp`

Supports mixed boundary conditions:

- left: Neumann no-flux
- right: Neumann no-flux
- bottom: Dirichlet fixed value
- top: Robin or Neumann, depending on config

Initial bug options:

- Neumann flux sign wrong on right/top boundaries
- boundary face length uses `dx` where `dy` is required
- Dirichlet ghost-cell distance assumes uniform spacing
- boundary condition metadata not serialized into checkpoint

### `/app/src/solver.cpp`

Finite-volume update step.

Correct conservative update shape:

```text
new_value = old_value + dt / cell_volume * sum(face_fluxes)
```

Flux through vertical faces should scale with vertical face length `dy(j)`.
Flux through horizontal faces should scale with horizontal face length `dx(i)`.

Initial bug options:

- uses `dt / (dx * dy)` with global `dx`, `dy`
- uses center-to-center spacing incorrectly for non-uniform grids
- applies face fluxes without multiplying by face length
- assumes uniform spacing for east/west/north/south fluxes
- clamps negative values to hide instability

### `/app/src/checkpoint.cpp`

Writes and reads checkpoint files.

Initial bug options:

- saves only `nx`, `ny`, current step, and field values
- does not save `x_faces`, `y_faces`
- does not save boundary configuration
- restart reloads a uniform grid based on `nx`, `ny`
- restart loads field values in transposed order for rectangular grids

### `/app/src/config.cpp`

Reads simple INI-style configs.

Use INI instead of YAML to avoid extra dependencies.

Example config:

```ini
nx=7
ny=5
steps=40
dt=0.002
diffusivity=0.4
grid_x=0,0.05,0.12,0.25,0.45,0.7,0.9,1.0
grid_y=0,0.1,0.2,0.4,0.65,1.0
left=neumann:0.0
right=neumann:0.0
bottom=dirichlet:1.0
top=neumann:0.0
initial=localized
output=/app/output/rectangular
```

### `/app/src/output.cpp`

Writes:

- field CSV
- summary file
- invariant file

Outputs should be deterministic.

Suggested output files:

```text
/app/output/<case>/field_final.csv
/app/output/<case>/mass_history.csv
/app/output/<case>/metadata.txt
/app/output/<case>/checkpoint.chk
```

## 7. Fixture Config Design

### `uniform.ini`

A simple square uniform grid that passes even with buggy code.

Purpose:

- Prevent task from being impossible.
- Show the solver basically works.
- Hide non-uniform bug.

### `rectangular.ini`

A non-square grid with uniform spacing.

Purpose:

- Catch indexing/transposition bugs.
- Ensure `nx != ny`.

### `mixed-boundary.ini`

A rectangular non-uniform grid with:

- no-flux left/right
- fixed-value bottom
- no-flux or Robin top
- localized initial condition

Purpose:

- Catch boundary face length and sign issues.

### `restart-clean.ini`

Runs uninterrupted for N steps and writes final output.

### `restart-from-checkpoint.ini`

Runs K steps, writes checkpoint, reloads checkpoint, runs N-K steps.

Purpose:

- Restarted final field should match uninterrupted final field within tolerance.

## 8. Required Correct Behavior

After the fix:

1. Uniform square-grid case remains stable.
2. Rectangular non-square case does not transpose or drop cells.
3. Non-uniform grid conservation invariant holds within tolerance.
4. Mixed Neumann/Dirichlet boundaries are handled consistently.
5. No-flux boundaries do not create or lose mass.
6. Restarted run matches uninterrupted run within tolerance.
7. Checkpoints preserve grid spacing, boundary metadata, step count, and field values.
8. Output remains finite.
9. Output is deterministic across repeated runs.
10. The solver does not pass by freezing the field or skipping updates.

## 9. Detailed `instruction.md` Prompt for the Agent

Use this as the final agent-facing prompt.

```md
The finite-volume solver in `/app/sim` is stable on the square uniform-grid case, but the rectangular and non-uniform grid cases lose conservation and restarted runs no longer match uninterrupted runs.

Please fix the solver so the provided configurations in `/app/configs` produce finite, stable outputs, preserve the expected conservation invariants on non-uniform grids with mixed boundary conditions, and make checkpoint/restart results match the corresponding uninterrupted run within numerical tolerance. Keep generated outputs under `/app/output`.
```

Why this prompt is good:

- It is concise.
- It uses absolute paths.
- It explains the problem clearly.
- It states success criteria without revealing exact fix.
- It does not mention exact files to edit beyond the project area.
- It avoids telling the agent formulas directly.
- It is realistic for a scientific-computing debugging task.

## 10. Oracle Solution Strategy

The oracle should be a deterministic Bash script that edits C++ source files and verifies the result.

It should not hardcode output files.

Recommended oracle steps:

1. `cd /app`
2. Inspect grid spacing implementation.
3. Fix `Grid::dx(i)`, `Grid::dy(j)`, and `Grid::volume(i,j)`.
4. Fix solver face flux scaling:
   - east/west fluxes use vertical face length `dy(j)`
   - north/south fluxes use horizontal face length `dx(i)`
   - update divides by cell volume
5. Fix non-uniform center distance calculations:
   - between cell centers use half-width sums
   - boundary ghost distance uses half-cell width where appropriate
6. Fix boundary sign and face length handling.
7. Fix rectangular indexing.
8. Fix checkpoint serialization:
   - store `nx`, `ny`
   - store `x_faces`
   - store `y_faces`
   - store boundary metadata
   - store current step/time
   - store field in deterministic row-major order
9. Fix checkpoint restore to reconstruct the exact grid.
10. Remove nondeterministic metadata from outputs.
11. Rebuild with CMake.
12. Run uniform, rectangular, mixed-boundary, and restart configs.
13. Run invariant checker and run comparison tools.

## 11. Example Oracle `solve.sh` Outline

The actual oracle should use deterministic file edits matching the final implementation.

```bash
#!/usr/bin/env bash
set -euo pipefail

cd /app

# Example approach:
# - Replace grid spacing functions.
# - Replace solver update loop.
# - Replace checkpoint read/write metadata handling.
# - Rebuild and verify.

cat > /app/src/grid.cpp <<'EOF'
// full corrected grid.cpp implementation
// computes dx(i), dy(j), cell volume, and row-major indexing correctly
EOF

cat > /app/src/solver.cpp <<'EOF'
// full corrected solver.cpp implementation
// computes finite-volume face fluxes using local spacing and face lengths
EOF

cat > /app/src/checkpoint.cpp <<'EOF'
// full corrected checkpoint.cpp implementation
// serializes grid faces, boundary config, step, time, and field values
EOF

cmake -S /app -B /app/build
cmake --build /app/build --target heat2d check_invariants compare_runs summarize_output

rm -rf /app/output
mkdir -p /app/output

/app/build/heat2d /app/configs/uniform.ini
/app/build/heat2d /app/configs/rectangular.ini
/app/build/heat2d /app/configs/mixed-boundary.ini
/app/build/heat2d /app/configs/restart-clean.ini
/app/build/heat2d /app/configs/restart-from-checkpoint.ini

/app/build/check_invariants /app/output/uniform
/app/build/check_invariants /app/output/rectangular
/app/build/check_invariants /app/output/mixed-boundary
/app/build/compare_runs /app/output/restart-clean /app/output/restart-from-checkpoint 1e-9
```

The oracle should demonstrate a real solve path and verification, not simply write expected outputs.

## 12. C++ Verification Tool Design

To avoid Python, create C++ tools used by tests and manual validation.

### `/app/tools/check_invariants.cpp`

Reads an output directory and checks:

- field values are finite
- no NaN or inf
- mass history is finite
- no-flux conservation error is within tolerance where expected
- field dimensions match metadata
- non-uniform grid metadata exists

Suggested CLI:

```bash
/app/build/check_invariants /app/output/mixed-boundary --mass-tol 1e-8 --finite
```

### `/app/tools/compare_runs.cpp`

Compares two output directories:

- final field dimensions
- field values with L2 and max absolute tolerance
- metadata compatibility
- mass history compatibility

Suggested CLI:

```bash
/app/build/compare_runs /app/output/restart-clean /app/output/restart-from-checkpoint 1e-9
```

### `/app/tools/make_grid_case.cpp`

Generates additional deterministic configs for verifier-only scenarios:

- rectangular grid with `nx != ny`
- non-uniform x spacing
- non-uniform y spacing
- no-flux boundaries
- mixed boundaries

This prevents hardcoding fixture names.

### `/app/tools/summarize_output.cpp`

Prints deterministic summary for debugging:

- dimensions
- final mass
- min/max values
- conservation error
- checkpoint metadata summary

## 13. Test Plan

Use Bash tests and compiled C++ tools. Do not use Python.

### Test 1: Uniform baseline still runs and remains finite

Purpose:

- Ensure basic functionality is not broken.

Steps:

- Build project.
- Run `/app/build/heat2d /app/configs/uniform.ini`.
- Run `/app/build/check_invariants /app/output/uniform`.

Checks:

- exit code `0`
- final field exists
- finite values
- dimensions match config

### Test 2: Rectangular non-square grid uses correct dimensions

Purpose:

- Catch square-grid assumptions and transposed indexing.

Steps:

- Run rectangular config.

Checks:

- output has `nx * ny` cells
- row/column metadata matches config
- no indexing crash
- finite field values

### Test 3: Non-uniform no-flux case preserves mass

Purpose:

- Catch wrong volume/face-length scaling.

Setup:

- Generate a deterministic non-uniform no-flux config at test time with `make_grid_case`.

Checks:

- final mass differs from initial mass by less than tolerance
- all values finite
- no boundary-induced gain/loss

### Test 4: Mixed boundary case satisfies expected invariant

Purpose:

- Catch boundary sign and face-length bugs.

Checks:

- no-flux sides contribute no mass
- Dirichlet/Robin contribution is consistent with configured boundary flux
- mass balance residual is within tolerance

### Test 5: Restart matches uninterrupted run

Purpose:

- Catch checkpoint metadata bugs.

Steps:

- Run uninterrupted config.
- Run checkpoint/restart config.
- Compare final fields.

Checks:

- dimensions match
- grid metadata matches
- boundary metadata matches
- max absolute field difference <= tolerance
- mass histories agree after restart point

### Test 6: Generated unseen non-uniform case passes

Purpose:

- Prevent hardcoding provided configs.

Steps:

- Use `make_grid_case` to create `/tmp/generated-nonuniform.ini`.
- Run solver.
- Check invariants.

Checks:

- conservation invariant
- finite output
- deterministic rerun hash

### Test 7: Output is deterministic across repeated runs

Purpose:

- Prevent random metadata or nondeterministic iteration.

Steps:

- Run same config twice from clean output directories.
- Normalize only allowed path prefixes if needed.
- Hash final field, mass history, and metadata.

Checks:

- hashes match exactly or numeric files compare within strict deterministic formatting expectations

## 14. `tests/test.sh` Plan

Use Bash-only verifier.

```bash
#!/usr/bin/env bash

TEST_DIR="${TEST_DIR:-/tests}"

bash "$TEST_DIR/test_outputs.sh"

if [ $? -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
```

Rules:

- No runtime package installs.
- Always writes reward file.
- Uses default `TEST_DIR`.
- Same tests for Oracle and agents.

## 15. `tests/test_outputs.sh` Skeleton

```bash
#!/usr/bin/env bash
set -euo pipefail

APP=/app
BUILD="$APP/build"
OUT="$APP/output"

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

run_case() {
  local config="$1"
  "$BUILD/heat2d" "$config"
}

clean_output() {
  rm -rf "$OUT"
  mkdir -p "$OUT"
}

echo "Building solver and validation tools"
cmake -S "$APP" -B "$BUILD"
cmake --build "$BUILD" --target heat2d check_invariants compare_runs make_grid_case summarize_output

echo "Test 1: uniform baseline"
clean_output
run_case "$APP/configs/uniform.ini"
"$BUILD/check_invariants" "$OUT/uniform" --finite --mass-tol 1e-8

echo "Test 2: rectangular non-square grid"
run_case "$APP/configs/rectangular.ini"
"$BUILD/check_invariants" "$OUT/rectangular" --finite --expect-rectangular

echo "Test 3: generated non-uniform no-flux conservation"
"$BUILD/make_grid_case" \
  --case nonuniform_noflux \
  --output /tmp/generated-nonuniform.ini \
  --nx 9 \
  --ny 6
run_case /tmp/generated-nonuniform.ini
"$BUILD/check_invariants" "$OUT/generated-nonuniform" --finite --mass-tol 1e-8 --require-nonuniform

echo "Test 4: mixed boundary invariant"
run_case "$APP/configs/mixed-boundary.ini"
"$BUILD/check_invariants" "$OUT/mixed-boundary" --finite --boundary-balance-tol 5e-8 --require-nonuniform

echo "Test 5: restart matches uninterrupted"
run_case "$APP/configs/restart-clean.ini"
run_case "$APP/configs/restart-from-checkpoint.ini"
"$BUILD/compare_runs" "$OUT/restart-clean" "$OUT/restart-from-checkpoint" 1e-9

echo "Test 6: deterministic repeated output"
clean_output
run_case "$APP/configs/rectangular.ini"
sha256sum "$OUT/rectangular/field_final.csv" "$OUT/rectangular/mass_history.csv" > /tmp/first.sha
clean_output
run_case "$APP/configs/rectangular.ini"
sha256sum "$OUT/rectangular/field_final.csv" "$OUT/rectangular/mass_history.csv" > /tmp/second.sha
diff -u /tmp/first.sha /tmp/second.sha

echo "All solver invariant tests passed"
```

## 16. Anti-Cheating Design

Prevent shallow or hardcoded solutions:

- Tests generate at least one unseen non-uniform grid config.
- Tests validate invariants instead of comparing one static output file.
- Tests check restart vs uninterrupted behavior.
- Tests verify dimensions for rectangular grids.
- Tests check finite output and mass/boundary balance.
- Tests reject freezing the field by checking expected field evolution or nonzero update norms.
- Tests compare generated output across repeated runs.
- Tests do not inspect source code for specific formulas.
- Tests do not rely only on visible reference files.
- Tests use multiple configs and generated cases.

Potential anti-cheating checks:

- Compare initial and final fields to ensure nontrivial evolution.
- Verify output metadata contains non-uniform face positions.
- Verify checkpoint file contains grid faces and boundary metadata.
- Generate a config with different `nx`, `ny`, and spacing than provided fixtures.
- Check field conservation using cell volumes, not simple unweighted sum.

## 17. Hardness Enhancements

To keep the task truly hard, include at least these interacting issues:

1. Interior flux scaling assumes uniform spacing.
2. Cell volume calculation assumes square cells.
3. Boundary face length uses wrong axis.
4. Boundary flux sign is wrong on at least one side.
5. Rectangular indexing bug exists in either output or checkpoint.
6. Checkpoint omits non-uniform grid face arrays.
7. Restart reconstructs a default uniform grid.
8. Output metadata includes nondeterministic timestamp or lacks required grid info.

Do not reveal these exact issues in `instruction.md`.

## 18. Expected Agent Failure Modes

Good failures:

- Agent fixes uniform/non-uniform volumes but misses boundary fluxes.
- Agent fixes clean runs but restart still diverges.
- Agent fixes checkpoint grid spacing but not boundary metadata.
- Agent checks unweighted sums instead of volume-weighted mass.
- Agent reduces `dt` or clamps values rather than fixing conservation.
- Agent passes provided configs but fails generated non-uniform config.
- Agent produces finite values but violates mass balance.
- Agent breaks rectangular dimensions.

Bad failures to avoid:

- Build system broken before task starts.
- Missing C++ compiler or CMake.
- Tests require Python.
- Tests use hidden formulas not implied by task.
- Tests are too tight for floating-point tolerance.
- Tests depend on wall-clock time.
- Task prompt is too vague.

## 19. Numerical Tolerance Guidance

Use careful tolerances.

Recommended:

- finite checks: exact finite requirement
- mass conservation no-flux: `1e-8` to `1e-7` for small deterministic grids
- restart max absolute difference: `1e-9` to `1e-8`
- boundary balance residual: `5e-8` or slightly looser depending scheme

Avoid:

- exact floating equality for evolved fields
- performance/latency thresholds
- tolerances so tight only the oracle implementation passes
- tolerances so loose a broken solver passes

Validation tools should print useful diagnostics:

- initial mass
- final mass
- conservation error
- max value
- min value
- max restart difference
- field dimensions

## 20. Rubric Draft

Use this as a starting rubric.

```text
Agent corrects finite-volume flux scaling so non-uniform cell widths, face lengths, and cell volumes are used consistently, +5
Agent handles mixed boundary conditions with correct face geometry and signs on rectangular non-uniform grids, +5
Agent updates checkpoint save/load logic so grid spacing, boundary metadata, step/time, and field values survive restart, +5
Agent makes restarted simulations match corresponding uninterrupted runs within numerical tolerance, +5
Agent preserves finite stable output for uniform, rectangular, and generated non-uniform cases, +3
Agent validates conservation using volume-weighted mass or equivalent invariant reasoning rather than unweighted sums, +3
Agent preserves deterministic output across repeated runs, +2
Agent keeps generated outputs under `/app/output` and does not modify input configs to hide failures, +2
Agent verifies the fix with multiple configurations including non-uniform and restart cases, +3
Agent hardcodes outputs or special-cases only the provided fixture names, -5
Agent disables the solver update, clamps away errors, or freezes the field to fake conservation, -5
Agent fixes clean runs but leaves checkpoint/restart metadata incomplete or inconsistent, -5
Agent uses unweighted mass sums on non-uniform grids as the conservation check, -3
Agent introduces Python into the task implementation or verifier despite the language constraint, -3
Agent modifies tests, solution files, or reserved framework paths, -5
Agent relies on nondeterministic timing, random values, or latency-based behavior, -3
```

Positive total: 33 points.  
Negative criteria count: 7.  
Allowed scores only: 1, 2, 3, 5.

## 21. Validation Commands

During development:

```bash
cd repair-nonuniform-fvm-conservation
harbor run -a oracle -p .
```

Interactive environment:

```bash
harbor tasks start-env -p . -i
```

Inside container:

```bash
cd /app
cmake -S /app -B /app/build
cmake --build /app/build --target heat2d check_invariants compare_runs make_grid_case summarize_output

/app/build/heat2d /app/configs/uniform.ini
/app/build/heat2d /app/configs/rectangular.ini
/app/build/heat2d /app/configs/mixed-boundary.ini
/app/build/heat2d /app/configs/restart-clean.ini
/app/build/heat2d /app/configs/restart-from-checkpoint.ini

/app/build/check_invariants /app/output/mixed-boundary --finite --boundary-balance-tol 5e-8
/app/build/compare_runs /app/output/restart-clean /app/output/restart-from-checkpoint 1e-9
```

Run frontier agents when possible:

```bash
harbor run -a terminus-2 -m openai/@openai/gpt-5.2 -p .
harbor run -a terminus-2 -m anthropic/@anthropic/claude-opus-4-6 -p .
```

## 22. Final Acceptance Checklist

Before submission:

- [ ] Regular task structure is used.
- [ ] `instruction.md` is concise and uses absolute paths.
- [ ] Prompt does not reveal the exact flux formula or checkpoint fields.
- [ ] `task.toml` uses `codebase_size = "small"` or `"large"`, not `minimal`.
- [ ] Category is `scientific-computing`.
- [ ] Subcategories are `[]`.
- [ ] Languages do not include Python.
- [ ] Dockerfile installs CMake, C++ build tools, `tmux`, and `asciinema`.
- [ ] Dockerfile does not copy `tests/` or `solution/`.
- [ ] No runtime network fetching.
- [ ] No privileged mode.
- [ ] Oracle derives the fix and passes.
- [ ] Tests are behavioral and deterministic.
- [ ] Tests use generated non-uniform cases.
- [ ] Tests validate invariants rather than static answer files.
- [ ] Tests verify restart vs uninterrupted behavior.
- [ ] Tests use appropriate floating-point tolerances.
- [ ] `test.sh` always writes reward.
- [ ] NOP agent fails.
- [ ] No latency-based tests.
- [ ] Oracle and agent use identical test logic.
- [ ] Rubric has 10–40 positive points and at least three negative criteria.

## 23. Final `instruction.md`

```md
The finite-volume solver in `/app/sim` is stable on the square uniform-grid case, but the rectangular and non-uniform grid cases lose conservation and restarted runs no longer match uninterrupted runs.

Please fix the solver so the provided configurations in `/app/configs` produce finite, stable outputs, preserve the expected conservation invariants on non-uniform grids with mixed boundary conditions, and make checkpoint/restart results match the corresponding uninterrupted run within numerical tolerance. Keep generated outputs under `/app/output`.
```
