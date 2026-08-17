# harness-v2.1-rollout

> Destination on disk: `docs/exec-plans/harness-v2.1-rollout.md`.
> This file is itself the first artifact of the rollout — `docs/exec-plans/`
> does not exist in the repo yet; creating this file (and its `_template.md`
> sibling) is part of phase 1 below.

## Goal

Convert the TB3 task-authoring harness from prose-rule discipline to mechanical enforcement, by landing the v2.1 plan in three phases — starting with a load-bearing phase 1 (one always-on router, agent-requested critical rule, shared checksum module, expanded preflight script, mandatory spec sections, and a short architecture codemap), then verifying Cursor behavior in phase 2, then promoting failure-triage in phase 3.

## Trigger

This rollout is responding to four converging signals from recent task-authoring work:

1. **Repeated reviewer feedback that prose rules don't fire reliably.** The conversation history this rollout follows shows three back-to-back instruction-eval policy updates (milestone-language warning, AI-scaffolding filename ban, hidden-instructions check in `environment/`) where the pattern was the same each time — a policy existed, agents missed it, the fix was a mechanical check in `scripts/run_static_checks.py` or `scripts/validate_submission_zip.py`, not more prose. The v2.1 plan generalizes that observation: the harness should make a rule mechanical whenever it can.

2. **Honor-system rules failing under skim-and-comply pressure.** The current `.cursor/rules/*.mdc` set is ~1759 lines across four files. v1's red team showed that always-on prose at this scale gets skimmed; v1's `00-authoring-critical.mdc` proposal addressed the symptom but kept a 150-line file always-on. v2/v2.1 cuts always-on content to ~50 lines and converts the dirty-flag (the rule most often violated) from prose to checksum.

3. **The repo already has a working `specs/` system that v1 didn't reference.** Every existing task has `specs/<task>.md` with Authoring Brief + Reviewer Appendix and a `scripts/validate_loop.py` gate. The mistake in v1 was proposing a parallel `docs/exec-plans/` for tasks; v2 corrected this and v2.1 ratifies it. The new mandatory sections (Triviality Ledger / Per-gate Pitfall Inventory / Initial Draft Commitments) extend the existing schema rather than replacing it.

4. **Recent enforcement-code changes shipped without written pre-commitment.** The milestone warning, AI-filename ban, and hidden-instructions check were each landed in the same back-and-forth chat, with verification done inline. They worked, but a written exec-plan would have surfaced edge cases earlier (e.g., `milestone_count` as an identifier in backticks). The mandatory `docs/exec-plans/` format introduced here closes that gap going forward — and this rollout is the first instance of that format.

Specific evidence:
- `tb3-repo-agent-harness_plan.md` (v1, uploaded artifact).
- `tb3-repo-agent-harness_plan-v2.md` (v2, generated in this thread; lives in outputs).
- `tb3-repo-agent-harness_plan-v2.1.md` (v2.1, generated in this thread; lives in outputs).
- Pre-existing baseline failures in `repo_tests/test_run_static_checks` (`release-provenance-drift` Dockerfile COPY paths, `oracle_path_discoverability` warning count) — unrelated to this rollout but tracked here so they're not mistakenly attributed to it.

## Change surface

Phase 1 lands all of the following. Phases 2 and 3 are sketched after.

### Phase 1 — new files

```
docs/exec-plans/_template.md           ~50 lines
                                       Template from v2.1 §4. Lifted verbatim.

docs/exec-plans/harness-v2.1-rollout.md   this file

docs/ARCHITECTURE.md                   ≤100 lines
                                       Codemap only. Six layer headings.
                                       No rule content, no walkthroughs.

.cursor/rules/00-authoring-critical.mdc   ≤120 lines / ≤4KB
                                       alwaysApply: false.
                                       Bullets numbered to match AGENTS.md.

scripts/task_integrity.py                      ~110 lines
                                       Module: CHECKSUM_FILE_NAME constant,
                                       _is_tracked_task_file predicate,
                                       iter_task_files, _compute_manifest,
                                       write_step2b_checksum,
                                       verify_step2b_checksum,
                                       CLI entry point (write|verify).

scripts/check-task.sh                  ~50 lines bash
                                       Phase A: run_static_checks + collapse_check
                                       Phase B: tmp zip + validate_submission_zip
                                       Phase C: python3 scripts/task_integrity.py write
                                       Exit message: preflight only, names oracle/NOP.

scripts/lint_spec.py                           ~80 lines
                                       Validates the three new mandatory sections
                                       in specs/<task>.md. Called by scripts/validate_loop.py.

repo_tests/test_task_integrity.py      round-trip, modified-file diff,
                                       missing-sentinel, forged-JSON,
                                       predicate parity with
                                       validate_submission_zip exclusions.

repo_tests/test_lint_spec.py           reject spec missing Triviality Ledger;
                                       reject spec missing Per-gate Pitfall Inventory;
                                       reject spec missing Initial Draft Commitments;
                                       accept spec with all three.

repo_tests/test_check_task_sh.py       end-to-end Phase A/B/C exit 0 on a fixture;
                                       exit message contains "preflight only";
                                       Phase B fails when a banned-AI-filename is
                                       seeded in the fixture.

repo_tests/test_approve_task_dirty_flag.py   approve refuses when sentinel missing;
                                             approve refuses when sentinel stale
                                             (file modified after write);
                                             approve passes when sentinel fresh.

repo_tests/test_step2b_sentinel_ignored_by_lints.py
                                       Seed .step2b-checksum in a fixture, run
                                       run_static_checks, collapse_check, and
                                       verifier_health; assert none surface it.

repo_tests/test_doc_size_caps.py       AGENTS.md ≤1500 bytes;
                                       docs/ARCHITECTURE.md ≤100 lines;
                                       00-authoring-critical.mdc ≤4KB.
```

### Phase 1 — modified files

```
AGENTS.md                              full rewrite (was 52 lines).
                                       Now ≤50 lines / ≤1500 bytes.
                                       Routing + 5 must-fire bullets +
                                       forbidden-in-submissions list.

scripts/approve_task.py                        ~5 LOC added.
                                       import task_integrity
                                       Call verify_step2b_checksum before any
                                       packaging; fail-fast on (not ok).

scripts/validate_submission_zip.py             1 line added: .step2b-checksum to
                                       FORBIDDEN_ROOT_FILES.

scripts/validate_loop.py                       Wire lint_spec.run(spec_path) into the
                                       Step 2a gate; fail validation if it
                                       returns a non-empty failure list.

specs/README.md                        Document the three new mandatory sections
                                       (Triviality Ledger / Per-gate Pitfall
                                       Inventory / Initial Draft Commitments)
                                       and the lint_spec gate.

REPO_CONVENTIONS.md                    Add new section "Local generated state:
                                       .step2b-checksum" with the visibility
                                       table from v2.1 §7. Add a one-line
                                       pointer to docs/ARCHITECTURE.md.

commands.md                            Replace the existing Packaging block's
                                       per-task zip command with a pointer to
                                       scripts/check-task.sh for preflight;
                                       leave the explicit scripts/approve_task.py command
                                       for Step 4. Document
                                       `python3 scripts/task_integrity.py {write|verify}`.

workflow-prompts.md                    Add "Ralph discipline within the Step
                                       model" subsection (v2.1 §11).

CNI.md                                 Add demotion policy (v2.1 §10) and
                                       tighten promotion criteria.

repo_tests/cases.py                    No new pass message expected from
                                       phase-1 changes (check-task.sh wraps
                                       existing tools and doesn't add static-
                                       check passes), but if any does land
                                       it goes here.

.gitignore                             Add `tasks/*/.step2b-checksum`.
                                       Optional but recommended.
```

### Phases 2 and 3 — surface only

Phase 2 (sketched, not landed in this rollout):

- Verify Cursor `@reference` and `.cursor/skills/` behavior in the installed version.
- Lock the skills path; add `tb3-task-author`, `tb3-task-reviewer`, `tb3-task-packager`.
- Run the first quarterly demotion review against ≥10 tasks of instrumentation data.
- Optional: split `task-creation.mdc` into the four scoped rules from v1 §4 *only if* metrics justify it.

Phase 3 (sketched, not landed in this rollout):

- Add `tb3-failure-triage` skill.
- Promote any CNI item whose recurring-failure threshold has been hit.
- Run the second quarterly demotion review.

Each phase 2/3 component will get its own exec-plan when it's landed, per the v2.1 §4 rule.

## False-positive risk

Walked per new mechanical check.

**`task_integrity.verify_step2b_checksum` — could refuse legitimate workflows.**

The verify path returns `(False, ...)` when any tracked task file's SHA256 differs from the manifest written by the last `check-task.sh` run. The closest *legitimate* construct that could trigger a false refusal is a contributor running `harbor run -p tasks/<name> -a oracle` between preflight and approval, where oracle execution writes a file inside `tasks/<name>/`. Mitigation: the predicate `_is_tracked_task_file` excludes dotfiles, dotdirs, `__pycache__`, and `.pyc`. Oracle output goes to harbor's working area, not into the task tree, so this is not an actual concern — but it should be regression-tested. `repo_tests/test_approve_task_dirty_flag.py` includes a "run oracle 1x then approve" pathway and asserts the checksum still verifies.

**`task_integrity._is_tracked_task_file` — could drift from `validate_submission_zip` exclusions.**

The predicate must match (in spirit) the dotfile / pycache / `*.pyc` filtering already done by `scripts/approve_task.py.should_skip_packaged_path`. If they drift, `scripts/approve_task.py` could pass the checksum check and then build a zip containing files that didn't exist when the manifest was written. Mitigation: `repo_tests/test_task_integrity.py` includes a *predicate parity* test that runs both predicates over a synthetic task tree containing dotfiles, `__pycache__`, `.pyc` files, and normal files; asserts the two predicates agree on every entry. The test fails loudly if either side adds a new exclusion without updating the other.

**`scripts/lint_spec.py` — could reject legitimate spec layouts.**

The lint checks for three section headers and that each has at least one bullet. The closest legitimate construct that could fail is a spec where the author put the Triviality Ledger inside the Reviewer Appendix instead of the Authoring Brief (which is wrong but has happened in similar systems). Mitigation: the lint reports *which* section is missing and where it expected to find it (`Authoring Brief`), so the failure message is actionable rather than cryptic. `repo_tests/test_lint_spec.py` includes a "section-in-wrong-place" case that confirms the lint fails with the expected message.

**`scripts/check-task.sh` Phase B — could false-fail on tasks that legitimately need a forbidden file.**

Phase B builds a tmp zip with the same exclusion list as the documented packaging command in `commands.md`, then runs `scripts/validate_submission_zip.py` against it. If a task author intentionally has `output_contract.toml` in their working tree (which is normal — it's required for the existing `--only output_contract` static check), Phase B's zip will exclude it, and the validator won't see it. False-positive risk is therefore on the *exclusion list*, not on the validator: if the task author has a file that they need at authoring time but should not ship, the exclusion list must catch it. Mitigation: the exclusion list in `check-task.sh` mirrors the one in `commands.md`'s packaging block; both are kept in sync by the regression test `test_check_task_sh.py::test_phase_b_exclusions_match_commands_md` (new). If they drift, the test fails.

**`AGENTS.md` ≤1500 byte cap — could false-fail review on a legitimate edit.**

If a future change adds 50 bytes to `AGENTS.md` (say a new must-fire bullet because a CNI item just promoted), the cap test will fail. That's not a false positive — it's the cap doing its job — but it requires the author to choose: shorten an existing bullet, demote one to `00-authoring-critical.mdc`, or write an exec-plan justifying the cap raise. The byte cap is intentionally annoying to bump, since the demotion policy (v2.1 §10) is the alternative. No mitigation needed; the cap is the constraint.

**`.step2b-checksum` ban in `scripts/validate_submission_zip.py` — guaranteed safe.**

The sentinel starts with `.` so it's already excluded from packaging by `scripts/approve_task.py.should_skip_packaged_path`'s dotfile rule. Adding it to `FORBIDDEN_ROOT_FILES` is belt-and-suspenders; the only path by which it could appear in a zip is if a future change to the dotfile filter were to allow it through, in which case the explicit ban catches it. Zero FP risk.

## Effect on existing fixtures and tasks

Two distinct populations to consider: in-repo fixtures (under `repo_tests/fixtures/`) and the 32 real tasks under `tasks/`.

**Effect on `repo_tests/fixtures/` (5 tasks):**

- `byzantine-storage-rebalance`, `implicit-step-restart`, `lsm-snapshot-recovery`, `release-provenance-drift`, `rollback-replay-divergence`: none of these have `specs/<name>.md` in the repo (they're test fixtures, not real tasks), so the new `scripts/lint_spec.py` doesn't apply to them. Verified.
- `public-contract-standard`, `public-contract-milestone` (under `repo_tests/fixtures/run_static_checks/`): same reasoning, not real tasks. Unaffected.
- The new `repo_tests/test_step2b_sentinel_ignored_by_lints.py` will *seed* a `.step2b-checksum` file into a fixture (via `tempfile.TemporaryDirectory`); this is a transient seed, not a permanent fixture change.

Net effect: no fixture changes required. The pre-existing 3 baseline failures (`release-provenance-drift` Dockerfile COPY paths × 2, `oracle_path_discoverability`) remain unchanged.

**Effect on the 32 real tasks under `tasks/`:**

Three things change for each task:

1. *Spec backfill.* Each task already has `specs/<name>.md`. None of them have the three new mandatory sections yet. Two options: (a) require backfill before any further authoring work on a task; (b) grandfather existing specs and only require the new sections for new tasks. v2.1 doesn't mandate either — this rollout chooses **(b) grandfathering**, with the rationale that retroactively writing a Triviality Ledger for a task that's already shipped adds no value (the task is already published). New tasks and any in-flight task that re-enters Step 2a get the new sections. `scripts/lint_spec.py` reads a sentinel `version: 2` field in the spec's metadata; specs without it skip the lint. New specs default to `version: 2`; existing specs without a `version` field are treated as `version: 1` and unaffected.

2. *Checksum stamp on next preflight.* The first time `scripts/check-task.sh` runs against a real task post-rollout, it writes `.step2b-checksum` into the task dir. This is a one-time write per task (the contributor runs preflight, the file appears, gets ignored by git via `.gitignore` and by all source-tree lints via the dotfile filter). No author-visible change beyond seeing the file appear in `ls -la`.

3. *`scripts/approve_task.py` gates on the sentinel.* Any task being approved post-rollout requires a fresh checksum. Authors who have approval workflows that don't run preflight first will get a clear error message naming the missing sentinel. This is the intended behavior; not a regression.

Net effect on tasks: zero file changes required immediately; one-time checksum write on next preflight; spec-section grandfathering policy means no in-flight authoring is blocked.

**Effect on the 21 shipping zips under `Task_Ready_To_Submit/`:**

None. The shipping zips were already updated in this conversation (construction_manifest.json stripped from 7 zips). Adding `.step2b-checksum` to `FORBIDDEN_ROOT_FILES` cannot affect them because (a) the sentinel starts with `.` and is already excluded from packaging, and (b) none of them currently contain a sentinel. Verified by `repo_tests/test_validate_submission_zip.test_checked_in_submission_zips_pass_validation`, which continues to pass.

**Effect on existing CI / review processes:**

Authors who currently run the static-checks command directly (per `commands.md`) can continue to do so; nothing breaks. The new `scripts/check-task.sh` is additive and offered as the preferred path. Reviewers who require Step 2b PASS evidence will start seeing oracle/NOP output captured separately from preflight output, which is the intended behavior (preflight is preflight; Step 2b PASS is preflight + oracle 1x + NOP).

## Tests

All listed under `repo_tests/`:

- `test_task_integrity.py` (new):
  - `test_round_trip_clean` — write, then verify, expect `(True, "checksum verified")`.
  - `test_modified_file_detected` — write, modify a file, verify, expect `(False, ...)` with "modified" in the message and the file's name listed.
  - `test_added_file_detected` — write, add a new tracked file, verify, expect `(False, ...)` with "added" in the message.
  - `test_removed_file_detected` — write, remove a tracked file, verify, expect `(False, ...)` with "removed" in the message.
  - `test_missing_sentinel_handled` — verify against a task with no sentinel, expect `(False, ...)` with the exact "run check-task.sh" guidance.
  - `test_forged_json_handled` — write garbage to the sentinel, verify, expect `(False, ...)` with a parse-error message.
  - `test_predicate_parity_with_packaging_skip` — generate a synthetic tree of dotfiles / pycache / pyc / regular files; assert `_is_tracked_task_file` and `approve_task.should_skip_packaged_path` agree on every entry.
  - `test_dotfile_excluded_including_sentinel_itself` — write a sentinel, then verify; the sentinel must not be in its own manifest.
  - `test_cli_write_and_verify_exit_codes` — invoke `scripts/task_integrity.py write` then `verify` via subprocess; assert exit codes 0/0 and 0/1 respectively after a modification.

- `test_lint_spec.py` (new):
  - `test_accepts_spec_with_all_three_sections` — happy path on a synthetic spec containing `Authoring Brief` with all three sub-sections, each with at least one bullet.
  - `test_rejects_missing_triviality_ledger`.
  - `test_rejects_missing_per_gate_pitfall_inventory`.
  - `test_rejects_missing_initial_draft_commitments`.
  - `test_rejects_section_in_reviewer_appendix` — Triviality Ledger placed under Reviewer Appendix instead of Authoring Brief; expect actionable error message.
  - `test_grandfathers_v1_spec` — spec without `version: 2` metadata; expect lint to skip.
  - `test_v2_spec_requires_all_sections` — spec with `version: 2`; expect lint to enforce all three.

- `test_check_task_sh.py` (new):
  - `test_end_to_end_passes_on_clean_fixture` — run script on a fixture task; assert exit 0 and `.step2b-checksum` is written.
  - `test_exit_message_states_preflight_only` — assert script's stdout contains "preflight only" and lists `harbor run ... oracle` and `harbor run ... nop`.
  - `test_phase_b_fails_when_banned_filename_seeded` — seed `tasks/<fixture>/environment/CLAUDE.md`; assert the script's Phase B exits non-zero with the validator's banned-AI-filename failure.
  - `test_phase_b_exclusions_match_commands_md` — parse the exclusion list in both `scripts/check-task.sh` and the Packaging block of `commands.md`; assert they're identical.
  - `test_idempotent_consecutive_runs` — run twice; both succeed; checksums are identical.

- `test_approve_task_dirty_flag.py` (new):
  - `test_approve_refuses_when_sentinel_missing` — fresh fixture, no preflight; assert `scripts/approve_task.py` exits non-zero with a message naming `.step2b-checksum`.
  - `test_approve_refuses_when_sentinel_stale` — preflight, then modify a task file, then approve; assert non-zero with "task files changed" in the message.
  - `test_approve_passes_with_fresh_sentinel` — preflight, then approve; assert exit 0.
  - `test_oracle_run_does_not_dirty_sentinel` — preflight, run oracle 1x against the fixture, approve; assert exit 0 (i.e., oracle output went outside the task tree).

- `test_step2b_sentinel_ignored_by_lints.py` (new):
  - `test_run_static_checks_ignores_sentinel` — seed sentinel; run all `scripts/run_static_checks.py` selectors; assert no failure or warning references the sentinel.
  - `test_collapse_check_ignores_sentinel`.
  - `test_verifier_health_ignores_sentinel`.

- `test_doc_size_caps.py` (new):
  - `test_agents_md_within_byte_cap` — read `AGENTS.md`, assert `len(bytes) <= 1500`.
  - `test_agents_md_within_line_advisory` — read `AGENTS.md`, assert line count `<= 50` (advisory; documented as such).
  - `test_architecture_within_line_cap` — read `docs/ARCHITECTURE.md`, assert line count `<= 100`.
  - `test_architecture_contains_no_rule_content` — read `docs/ARCHITECTURE.md`, assert it does not contain forbidden phrases (`alwaysApply:`, `should not`, `must not`, `forbidden`); these belong in `*.mdc` or `REPO_CONVENTIONS.md`, not the codemap.
  - `test_critical_rule_within_byte_cap` — read `00-authoring-critical.mdc`, assert `len(bytes) <= 4096`.

- `test_validate_submission_zip.py` (modified):
  - Add `test_step2b_checksum_at_archive_root_is_rejected` mirroring the existing `test_construction_manifest_at_archive_root_is_rejected` pattern.
  - Existing `test_checked_in_submission_zips_pass_validation` continues to pass unchanged.

Total new test count: ~28 tests across 6 new files. Existing `repo_tests` module count goes from 7 modules to 13.

## Rollback

Phase 1 is large enough that rollback procedure matters. The procedure is split by component, since some are reversible cheaply and others are not.

**Cheap rollback (any time, no contributor coordination required):**

- Revert `AGENTS.md` to its pre-rollout state. The router pointer to `docs/ARCHITECTURE.md` becomes a dangling reference but doesn't break anything.
- Remove `docs/ARCHITECTURE.md`. No code depends on it.
- Remove `.cursor/rules/00-authoring-critical.mdc`. No always-on rule references it (it's agent-requested), so removing it is silent.
- Remove `scripts/lint_spec.py` and revert `scripts/validate_loop.py`'s wiring. Existing specs are unaffected (none have `version: 2` yet at rollback time).
- Revert the new section in `REPO_CONVENTIONS.md` and the new pointers in `commands.md` / `workflow-prompts.md`.
- Remove the new test files. They don't pin anything in the existing test surface.

**Coordinated rollback (requires telling in-flight contributors to stop):**

- Removing `scripts/task_integrity.py` and reverting `scripts/approve_task.py`'s import.
- Reverting `scripts/check-task.sh` (or removing it entirely).
- Reverting `scripts/validate_submission_zip.py`'s `.step2b-checksum` ban.

These are coordinated because contributors who have already run preflight on their working copy will have `.step2b-checksum` files in `tasks/*/`. Post-revert those files become orphan dotfiles — harmless, but worth a `find tasks/ -name .step2b-checksum -delete` cleanup announcement.

**Per-task cleanup after rollback:**

```bash
find tasks/ -name .step2b-checksum -delete
```

Safe to run unconditionally; any tasks that don't have a sentinel are unaffected. Submission zips were never going to contain the sentinel (dotfile exclusion), so no zips need rebuilding.

**Phase 2 / 3 rollback:**

Each phase 2/3 component will land with its own exec-plan and its own rollback section. Phase 1 rollback does not affect phase 2/3 prerequisites since those phases haven't started.

## Verification done

The following items map directly to the v2.1 phase-1 exit criteria. Each is a `[ ]` until proven; converts to `[x]` when verified with command output captured in this exec-plan's accompanying log (or in a follow-up update to this file).

- [ ] All real tasks under `tasks/` pass `scripts/check-task.sh` end-to-end (Phase A + B + C exit 0). Command: `for d in tasks/*/; do ./scripts/check-task.sh "$d" || echo FAIL "$d"; done`. Expected: zero `FAIL` lines.
- [ ] All shipping zips still pass `scripts/validate_submission_zip.py`. Command: `for f in Task_Ready_To_Submit/*.zip; do python3 scripts/validate_submission_zip.py "$f" | tail -1; done`. Expected: 21 lines of `RESULT: PASS`.
- [ ] `scripts/approve_task.py` refuses when `.step2b-checksum` is stale. Verified by `test_approve_task_dirty_flag.py::test_approve_refuses_when_sentinel_stale`.
- [ ] `scripts/approve_task.py` refuses when `.step2b-checksum` is missing. Verified by `test_approve_task_dirty_flag.py::test_approve_refuses_when_sentinel_missing`.
- [ ] `task_integrity` round-trip test passes. Verified by `test_task_integrity.py::test_round_trip_clean`.
- [ ] `task_integrity` predicate parity test passes. Verified by `test_task_integrity.py::test_predicate_parity_with_packaging_skip`.
- [ ] `scripts/lint_spec.py` rejects a v2 spec missing each of the three mandatory sections. Verified by `test_lint_spec.py` × 3.
- [ ] `scripts/lint_spec.py` grandfathers v1 specs. Verified by `test_lint_spec.py::test_grandfathers_v1_spec`.
- [ ] `AGENTS.md` fits the byte cap. Verified by `test_doc_size_caps.py::test_agents_md_within_byte_cap`.
- [ ] `docs/ARCHITECTURE.md` fits the line cap and contains no rule content. Verified by `test_doc_size_caps.py::test_architecture_within_line_cap` and `test_architecture_contains_no_rule_content`.
- [ ] `00-authoring-critical.mdc` fits the byte cap. Verified by `test_doc_size_caps.py::test_critical_rule_within_byte_cap`.
- [ ] `scripts/check-task.sh` exit message contains "preflight only" and lists `harbor run` commands. Verified by `test_check_task_sh.py::test_exit_message_states_preflight_only`.
- [ ] `scripts/check-task.sh` exclusion list matches `commands.md`. Verified by `test_check_task_sh.py::test_phase_b_exclusions_match_commands_md`.
- [ ] `.step2b-checksum` ignored by all source-tree lints. Verified by `test_step2b_sentinel_ignored_by_lints.py` × 3.
- [ ] `.step2b-checksum` rejected at submission-zip root. Verified by `test_validate_submission_zip.py::test_step2b_checksum_at_archive_root_is_rejected`.
- [ ] Pre-existing baseline test failures (`release-provenance-drift` × 2, `oracle_path_discoverability`) unchanged in count and identity. Verified by diffing the failure list before and after rollout.
- [ ] `repo_tests/cases.py` updated if any new pass message lands. (Phase 1 is not expected to add any; if it does, this checkbox lands a `cases.py` update.)
- [ ] `REPO_CONVENTIONS.md` and `commands.md` updated per the change-surface table.
- [ ] `docs/exec-plans/_template.md` exists and matches v2.1 §4 verbatim.
- [ ] This file (`docs/exec-plans/harness-v2.1-rollout.md`) checked in alongside the rollout commit.

When all 20 items are `[x]`, phase 1 is complete and the rollout enters its phase-1 instrumentation window (≥10 task authorings before phase 2 entry, per v2.1 phased-rollout entry criteria).

---

## Notes for the implementer

A few practical points that aren't part of the template but matter for execution:

- **Land `scripts/task_integrity.py` and the test before any caller depends on it.** The dependency graph is: `scripts/task_integrity.py` → `scripts/check-task.sh` (Phase C) and `scripts/task_integrity.py` → `scripts/approve_task.py` (verify). If you land the script first, the script breaks. Order: module + tests, then script Phase C, then `scripts/approve_task.py` import.

- **Dogfood this exec-plan.** The first task that re-enters Step 2a after rollout should produce a v2 spec with the three new sections, and an attempt at filing this exec-plan as a precedent reference in its `Per-gate Pitfall Inventory`. That confirms the new sections are usable in practice, not just theoretically.

- **The grandfathering decision is reversible.** If, after phase 1 has been live for some time, the demotion review reveals that grandfathered specs are causing reviewer churn, the rollback is small: bump every existing `specs/<name>.md` to `version: 2` and require backfill. This rollout doesn't pre-empt that decision.

- **The `.gitignore` line is optional.** If your team's policy is to commit local state for traceability, omit it; `validate_submission_zip` and the dotfile filter still keep the sentinel out of submissions either way. The `.gitignore` line just keeps it out of git history, which is convenience, not policy.

---

> **Errata:** see `docs/exec-plans/harness-v2.1-corrections.md`
> for known drifts between this document and the actual
> implementation. Do not re-apply this plan without reading
> the corrections.
