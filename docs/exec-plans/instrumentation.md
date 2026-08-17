# Per-task authoring instrumentation

## Goal

Wire per-task authoring metrics into the harness so phase 2's
demotion review has data to read.

## Trigger

Phase 1 verification found this gap; the v2.1 plan §12 (lines 863-885
of `tb3-repo-agent-harness_plan-v2.1.md`) requires it, and phase 2's
quarterly demotion review (plan §10 and plan §"Phased rollout" entry
criteria for Phase 2) depends on ≥10 task authorings of recorded
metrics before phase 2 can enter. Without this code, phase 2
demotion runs on vibes — the failure mode v2.1 was explicitly
designed to replace.

The v2.1 spec (`docs/exec-plans/harness-v2.1-rollout.md`) lists the
`specs/<task-name>-validation-log.md` metrics write as part of
phase 1 but the rollout shipped without it.

## Change surface

Anticipated; refine during implementation. This exec-plan is the
pre-commitment artifact; the PR implementing it must either hit
exactly these files or file an amendment here naming the
divergence.

Per plan §12 the target metrics block is:

```md
## Per-task authoring metrics

_Note: the start-anchor metric was renamed from "wall-clock from
spec approval to first Step 2b PASS" to "wall-clock from first
preflight to first preflight PASS" because `check-task.sh` has
no spec-approval signal; see `docs/exec-plans/instrumentation.md`
for rationale._

- count of scripts/run_static_checks.py FAIL exits before first PASS
- count of scripts/run_static_checks.py WARN-only exits before approval
- count of scripts/collapse_check.py FAIL exits before first PASS
- count of dirty-flag triggers (scripts/approve_task.py refused due to
  checksum mismatch)
- wall-clock time from first preflight to first preflight PASS
- wall-clock time from first Step 2b PASS to scripts/approve_task.py exit 0
- list of CNI references that fired during the authoring (e.g.
  "milestone-language warning fired and was rephrased")
- whether the spec's Initial Draft Commitments matched the final
  file set — `draft_commitments_diff`: `null` initially; the
  parser is deferred to a follow-up exec-plan, mirroring the
  CNI-fired list path (see False-positive risk)
```

- **New: `scripts/metrics_collector.py`.** Library that owns counter-file
  format and aggregation. Exposes `record_exit(tool, outcome)` for
  the per-tool hooks and `aggregate(task_dir) -> dict` for the
  approval-time read. Counter file format: append-only JSONL, one
  line per hook invocation, fields
  `{tool, outcome, timestamp_ns, run_id}`. `run_id` is read from
  the `TB3_METRICS_RUN_ID` env var; if unset (one-shot reviewer
  invocation, CI smoke-test) the record uses the literal sentinel
  `"adhoc"`. `aggregate()` groups events by `run_id` so successive
  authoring loops over the same task dir remain distinguishable.
  When `t_first_step2b_pass_ns` is absent (Phase C never went
  green during the captured window), `aggregate()` reports the
  wall-clock duration as the literal string `"no Step 2b PASS yet"`
  rather than crashing or emitting `0`; the rendered block surfaces
  that string in place of a duration.
- **New: `scripts/validation_log.py`.** Append helper. Exposes
  `append_metrics_block(spec_path, block_text)`. Reads current
  `specs/<task-name>-validation-log.md`, appends the rendered block,
  writes atomically (tmp + rename). Creates the log file if absent.
- **Modified: `scripts/approve_task.py`.** Extend `build_report` (line 538
  and the dirty-flag branch at line 563) to:
  - Increment the dirty-flag counter via `metrics_collector` when
    `verify_step2b_checksum` returns mismatch, before raising the
    blocking failure.
  - On successful approval, aggregate metrics, render the block,
    and call `validation_log.append_metrics_block`. Emission is
    conditional on `--emit-metrics` (default on for CLI, off for
    library consumers) so existing test fixtures are not forced
    into the log-write path.
- **Modified: `scripts/check-task.sh`.** At start of run, generate
  a per-invocation run_id (`RUN_ID="$(uuidgen | head -c 8)"`) and
  export it as `TB3_METRICS_RUN_ID` for the duration of the
  script, alongside `TB3_METRICS_TASK_DIR`. Timestamp markers for
  the two wall-clock windows: write
  `t_first_check_task_invocation_ns` on first Phase A entry
  (renamed from `t_spec_approved_ns`; the script has no
  spec-approval signal, so it captures what it can actually
  measure — first preflight invocation), and write
  `t_first_step2b_pass_ns` at the end of Phase C (all three
  phases green). Implementation uses `date +%s%N` — POSIX-portable
  if the build host has GNU coreutils; fall back to Python
  one-liner via `metrics_collector` CLI if not.
- **Modified: `scripts/run_static_checks.py`.** FAIL/WARN counter hook.
  The tool already emits FAIL/WARN as exit codes; the hook is a
  `try/finally` wrapper in the CLI entry point that calls
  `metrics_collector.record_exit("run_static_checks", outcome)`
  with `outcome ∈ {"FAIL", "WARN", "PASS"}`. Hook is
  gated on `TB3_METRICS_TASK_DIR` env var to keep one-shot
  invocations (CI, reviewer spot-checks) unaffected.
- **Modified: `scripts/collapse_check.py`.** Same pattern as
  `scripts/run_static_checks.py`; `outcome ∈ {"FAIL", "PASS"}` (no WARN tier
  in collapse).
- **Modified: `scripts/task_integrity.py`.** Add a named constant
  `EXCLUDED_DOTFILES = (".step2b-checksum", ".step2b-metrics.jsonl")`
  and exclude those names *in addition* to the generic dotfile
  rule. Defense-in-depth: if a future refactor narrows or removes
  the generic dotfile rule, the explicit names remain excluded
  from the checksum manifest. Pinned by a regression test (see
  Tests below).
- **Modified: `scripts/validate_submission_zip.py`.** Add
  `.step2b-metrics.jsonl` to `FORBIDDEN_ROOT_FILES` (+1 LOC). The
  generic dotfile filter already rejects it implicitly; listing
  the name explicitly makes the rejection survive a future change
  to the implicit filter — same defense-in-depth pattern as the
  `scripts/task_integrity.py` change above. Pinned by a new regression
  test mirroring the existing checksum-at-archive-root case.
- **New: `repo_tests/test_instrumentation.py`.** Regression tests
  (see Tests below).

Counter file location: `tasks/<task-name>/.step2b-metrics.jsonl`,
next to `.step2b-checksum`. Dotfile, so it is naturally excluded
from submission zips by the existing `-x '.*'` in Phase B. The
exclusion from `scripts/task_integrity.py`'s checksum manifest is made
explicit via the `EXCLUDED_DOTFILES` constant (see Change Surface
bullet) — this file changes during Phase B/C legitimately, so it
must be excluded from the manifest exactly like `.step2b-checksum`
itself, and the explicit constant ensures the protection survives
any future change to the generic dotfile rule. Likewise,
`scripts/validate_submission_zip.py` rejects the name explicitly through
`FORBIDDEN_ROOT_FILES` rather than relying solely on the implicit
dotfile filter. Include in `.gitignore` alongside
`.step2b-checksum`.

## False-positive risk

Walk through each counter-file edge case and the closest
legitimate behavior that might trip it:

- **Counter-file conflicts between concurrent runs.** Two parallel
  `check-task.sh` invocations against the same task dir (rare but
  possible — a reviewer running the preflight while the author is
  mid-authoring) would both append to the same JSONL file. JSONL
  append is safe at the byte level on POSIX (`O_APPEND` is atomic
  for `PIPE_BUF` writes; each JSON line is <200 bytes), so records
  interleave but do not corrupt. Aggregation reads the whole file
  and sorts by `timestamp_ns`, so ordering is recovered. The
  closest legitimate concern — one process reading mid-write —
  is handled by `validation_log.append_metrics_block` using
  tmp-file + rename rather than in-place edit.

- **Log corruption from partial writes.** `scripts/approve_task.py` can
  be interrupted (Ctrl-C, OOM) between reading the current log
  and writing the appended version. Mitigated by the tmp-file +
  rename pattern in `scripts/validation_log.py`; rename is atomic on the
  same filesystem. If rename fails cross-filesystem, the helper
  falls back to an exclusive-mode append with a `fcntl` advisory
  lock and logs the degraded path.

- **Sentinel-file race with `.step2b-checksum`.** The dirty-flag
  counter increments *before* `scripts/approve_task.py` raises the
  blocking failure. If the counter write itself fails, the
  blocking failure must still fire; the counter hook is therefore
  wrapped in a broad try/except that logs-and-continues. A dropped
  increment is a known-accepted miss (one undercount per failure
  event across 10+ authorings is below the signal floor for
  demotion decisions), whereas failing to surface the blocking
  failure is a correctness regression.

- **`specs/<task-name>.md` absent or freshly renamed.** The log
  helper infers `specs/<task-name>-validation-log.md` from the
  task directory name. If the spec is missing (v1 grandfathering
  or CNI back-burner task), the metrics block write is skipped
  with a stderr note, not a fatal error. The metrics are still
  useful for demotion review even without a co-located spec —
  the counter file carries the same data.

- **CNI-fired list population.** The plan's fourth-from-last
  bullet — "list of CNI references that fired" — has no
  mechanical source today. The implementation must either (a) wire
  `scripts/run_static_checks.py` and `scripts/collapse_check.py` to emit CNI IDs
  in a machine-readable footer, or (b) defer that bullet to a
  follow-up exec-plan and leave it as an empty list in the
  initial metrics block. The safer choice is (b); promote to (a)
  only if phase-2 demotion review reveals that the empty list is
  blocking demotion decisions.

- **"Initial Draft Commitments matched" diff.** Requires a
  non-trivial parser of the spec's `Initial Draft Commitments`
  section that doesn't currently exist — `scripts/lint_spec.py` only
  enforces presence of the heading, not structured extraction of
  the bulleted file list. The implementation must either (a) ship
  that parser as part of this exec-plan, or (b) defer the parser
  to a follow-up exec-plan and emit
  `"draft_commitments_diff": null` in the initial metrics block.
  The safer choice is (b), mirroring the CNI-fired list path;
  promote to (a) only if phase-2 demotion review reveals that
  the null is blocking demotion decisions. The block is
  *advisory for demotion review*, not a blocking gate, so a
  null entry is non-fatal.

- **Env-var opt-in for hook gates.** `scripts/run_static_checks.py` and
  `scripts/collapse_check.py` are invoked from many places — `check-task.sh`,
  `scripts/approve_task.py`, reviewer one-shots, CI.
  `TB3_METRICS_TASK_DIR` opt-in avoids polluting one-shot
  invocations with stray counter writes to a task dir that
  happens to be CWD. `check-task.sh` sets this env var for the
  duration of its run; nothing else should.

## Effect on existing fixtures and tasks

- **Baseline `repo_tests`.** Current 32 failures are unrelated;
  none should change status. New tests under
  `test_instrumentation.py` must not tip existing tests over —
  the env-var opt-in is the primary mechanism that keeps this
  safe.
- **`repo_tests/test_approve_task.py`.** Existing fixtures may
  need the same mechanical top-up precedent established in
  `harness-v2.1-corrections.md` (d): each test that calls
  `build_report(...)` with `emit_metrics=True` must now provide
  either a spec-log path or set `emit_metrics=False`. Default
  for the library entry point should be `False` so existing
  fixtures need no edit; only the CLI caller (`main`) defaults
  to `True`.
- **Tasks under `tasks/`.** On next run of `check-task.sh` each
  task will accumulate `.step2b-metrics.jsonl`. Rollback must
  remove these; `.gitignore` entry keeps them out of history.

## Tests

- **`test_metrics_block_lands_on_successful_approval`** —
  synthetic tasks/<fixture>/ plus specs/<fixture>.md; run
  `check-task.sh` (stubbed tools, real `metrics_collector`),
  run `scripts/approve_task.py` against the resulting zip, assert
  `specs/<fixture>-validation-log.md` now contains a
  `## Per-task authoring metrics` heading with all eight
  bullets present.
- **`test_dirty_flag_counter_increments_on_stale_sentinel`** —
  preflight, modify a task file, approve; assert the counter
  file has at least one
  `{"tool":"approve_task","outcome":"dirty_flag",...}` record
  carrying a `run_id` matching the preflight's exported
  `TB3_METRICS_RUN_ID`.
- **`test_run_static_checks_hook_counts_fail_then_pass`** — two
  invocations with `TB3_METRICS_TASK_DIR` and `TB3_METRICS_RUN_ID`
  set, first FAIL then PASS; assert counter file has both records
  with matching `timestamp_ns` order, each tagged with the
  exported `run_id`.
- **`test_collapse_check_hook_counts_fail`** — same pattern for
  `scripts/collapse_check.py`.
- **`test_no_opt_in_leaves_no_counter`** — invoke both tools
  without `TB3_METRICS_TASK_DIR`; assert no counter file is
  created in CWD or elsewhere.
- **`test_wall_clock_markers_populate`** — end-to-end synthetic
  run; assert `t_first_check_task_invocation_ns` (renamed from
  `t_spec_approved_ns`) and `t_first_step2b_pass_ns` are both
  present in the counter file and the former is ≤ the latter.
- **`test_metrics_block_skipped_when_spec_missing`** — grandfathered
  task with no `specs/<task-name>.md`; assert `scripts/approve_task.py`
  still exits 0 and logs a stderr note; counter file exists
  (block skipped, not failed).
- **`test_concurrent_appends_do_not_corrupt_jsonl`** — two
  subprocesses call `record_exit` in a tight loop; assert the
  resulting file parses as valid JSONL with all records present.
- **`test_metrics_file_excluded_from_submission_zip`** —
  seed `.step2b-metrics.jsonl` in a fixture, invoke the Phase B
  packaging logic, assert the file is absent from the zip.
- **`test_records_without_run_id_env_var_use_adhoc_sentinel`** —
  invoke a hook with `TB3_METRICS_TASK_DIR` set but
  `TB3_METRICS_RUN_ID` unset (e.g. reviewer one-shot); assert the
  resulting record has `"run_id": "adhoc"`.
- **`test_aggregate_reports_no_pass_when_second_marker_absent`** —
  end-to-end synthetic run with Phase C stubbed to FAIL forever
  so `t_first_step2b_pass_ns` is never written; assert
  `aggregate()` returns the literal string `"no Step 2b PASS yet"`
  for the wall-clock duration field, does not raise, and does not
  emit `0`; assert the rendered metrics block surfaces that
  literal in place of a duration.
- **`test_draft_commitments_diff_is_null_initially`** —
  successful approval produces a metrics block whose
  `draft_commitments_diff` field is `null`. Pin until the
  deferred parser ships in a follow-up exec-plan.
- **`test_task_integrity_excludes_step2b_dotfiles_explicitly`** —
  seed a fixture task dir with both `.step2b-checksum` and
  `.step2b-metrics.jsonl`; assert `task_integrity` exposes
  `EXCLUDED_DOTFILES = (".step2b-checksum", ".step2b-metrics.jsonl")`
  and that both names are excluded from the manifest even with
  the generic dotfile rule monkeypatched to a no-op. Pins the
  explicit exclusion so the protection survives a future
  accidental change to the dotfile rule.
- **`test_metrics_file_at_archive_root_is_rejected`** — mirrors
  the existing `test_step2b_checksum_at_archive_root_is_rejected`:
  build a fixture archive with `.step2b-metrics.jsonl` at the
  archive root, run `validate_submission_zip` against it, assert
  rejection.

## Rollback

1. Revert the nine change-surface files listed above (two new
   modules, four modifications to `scripts/approve_task.py` /
   `check-task.sh` / `scripts/task_integrity.py` /
   `scripts/validate_submission_zip.py`, two env-var-gated hooks in
   `scripts/run_static_checks.py` / `scripts/collapse_check.py`, one new test
   file).
2. Remove `.step2b-metrics.jsonl` from any `tasks/<task-name>/`
   directory where it was written:
   `find tasks -name '.step2b-metrics.jsonl' -delete`.
3. Remove the `.step2b-metrics.jsonl` pattern from `.gitignore`
   if added.
4. Leave `specs/<task-name>-validation-log.md` files in place —
   they are historical record and removing them would erase
   information legitimately gathered during the metrics window.

## Verification done

- [x] `scripts/metrics_collector.py` and `scripts/validation_log.py` shipped,
  with unit tests for format and concurrency guarantees.
- [x] `scripts/approve_task.py` emits the metrics block on successful
  approval and increments the dirty-flag counter on refusal.
- [x] `scripts/check-task.sh` writes both wall-clock markers.
- [x] `scripts/run_static_checks.py` and `scripts/collapse_check.py` record
  exits when `TB3_METRICS_TASK_DIR` is set, are no-ops when it
  is unset.
- [x] `.step2b-metrics.jsonl` is excluded from submission zips
  (tested under `test_metrics_file_excluded_from_submission_zip`)
  and ignored by `scripts/task_integrity.py`'s checksum manifest.
- [x] Baseline `repo_tests` failure count is unchanged
  (`.expected_failure_count` or equivalent preserved).
- [x] `cases.py` updated if any new pass-message lands.
- [x] `REPO_CONVENTIONS.md` updated with a short note on
  `.step2b-metrics.jsonl` visibility, matching the existing
  `.step2b-checksum` note.
- [x] `commands.md` updated with one line in Step 2b Preflight
  naming the metrics side-effect (so authors are not surprised
  by a new dotfile appearing).
- [ ] Ten task authorings completed with metrics recorded
  (phase 2 entry criterion; tracked outside this exec-plan).
