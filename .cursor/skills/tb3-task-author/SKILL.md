---
name: tb3-task-author
description: Step 2b construction macro for TB3 tasks. Pull when drafting files for a new task whose Step 2a spec has been approved by scripts/validate_loop.py (specs/<task>.md exists with Authoring Brief sections including Triviality Ledger, Per-gate Pitfall Inventory, and Initial Draft Commitments). Walks through reading the spec, drafting files per the commitments, running scripts/check-task.sh preflight, and capturing instrumentation output before claiming Step 2b PASS.
disable-model-invocation: true
---

# tb3-task-author — Step 2b construction macro

Drives Step 2b drafting only. Review is `tb3-reviewer`; packaging is
`tb3-packager`.

## 1. Pre-conditions

Stop if any fails — do not start drafting.

- `specs/<task-name>.md` exists (Step 2a produced it via
  `scripts/validate_loop.py`).
- The Authoring Brief contains `Triviality Ledger`, `Per-gate Pitfall
  Inventory`, and `Initial Draft Commitments`. If `scripts/lint_spec.py` would
  reject the spec, stop and tell the user to re-run Step 2a.
- `tasks/<task-name>/` does not exist or is empty. Do not edit an
  existing draft from this skill — pull `tb3-reviewer` if files are
  already there.

## 2. Read first, then draft

- Read `specs/<task-name>.md` **Authoring Brief section only**. The
  Reviewer Appendix is for `tb3-reviewer`, not for drafting.
- `task-creation.mdc` should auto-attach once you touch
  `tasks/<task-name>/`. If it does not, pull it explicitly.
- Open `commands.md` for harbor and preflight syntax. Do not invent
  commands.

## 3. Draft per Initial Draft Commitments

- Create exactly the files listed in the spec's `Initial Draft
  Commitments` section, one per commitment.
- Do not add files outside that list. If you need one that is not
  listed, the spec is incomplete — flag for amendment and return to
  Step 2a rather than going off-spec.
- Construction is spec-aware, not spec-discovering: every rule the
  later gates check (RC1-RC8, CR1/CR2/CR7-CR9, GX1-GX10,
  `review-and-submit.mdc` §1-7, `difficulty-calibration.mdc`
  Part A and Part B) is documented upstream. Apply each rule while
  writing the file, not after.
- **Milestone tasks** (`number_of_milestones > 0`): new milestone
  tasks are blocked — net-new milestone submissions are rejected by
  an eval check. Only milestone tasks already in the revision queue
  or awaiting review are exempt (they continue through to Accepted
  as normal); the rules below apply to those exempt tasks. The
  canonical layout is `steps/milestone_N/{instruction.md,
  tests/{test.sh, test_mN.py}, solution/{solve.sh, solveN.sh}}`. Do not create a
  top-level `instruction.md`, `tests/`, `solution/`, `milestones.md`,
  or `milestone_X.md` for a milestone task — that shape is
  deprecated. `task.toml` must use `version = "2.0"` with `[[steps]]`
  blocks (one per milestone, `name = "milestone_N"`), per-step
  `[steps.agent]` / `[steps.verifier]` timeouts, no top-level
  `[agent]` / `[verifier]`, and `[metadata].number_of_milestones`
  equal to the number of `[[steps]]` blocks. See
  `task-creation.mdc` "Milestone task" for the full layout, naming,
  and rubric requirements (each milestone gets 10–40 points).
- **Task types and categories we no longer accept:** new starts of
  multi-container, UI building, software-engineering, debugging, or
  milestone tasks must not be drafted — net-new submissions in these
  areas are rejected by an eval check. If the spec implies any of
  these, stop and return to Step 2a for a redesign. (Exception:
  milestone tasks already in revision or awaiting review may
  continue.)
- **No templated tasks:** do not draft a reskin of a prior submission
  (same scaffold with keyword/instruction or test-pattern swaps).
- **Canonical base images:** `environment/Dockerfile` final runtime must `FROM` a digest that matches `docs/DOCKERFILE_AND_IMAGE_BEST_PRACTICES.md` / `scripts/canonical_base_images.py`. Digest pinning and canonical image choice are separate requirements. Non-canonical: Dockerfile/README justification + submission UI **No**. Run `python3 scripts/check_canonical_base_image.py tasks/<task>`.
- **Environment files & licensing:** no AI-specific filenames
  (`CLAUDE.md`, `skills.md`, `AGENTS.md`, `.cursor/`, …) anywhere in
  the archive; no hidden agent instructions in environment files
  (HINT:/STEP N: walkthroughs, "to solve this..." phrasing, or
  prescriptive TODOs aimed at the solver). LICENSE files: omit on
  minimal/small codebases; on large codebases use the
  project-provided repos or MIT/Apache 2.0/BSD only.
- **Verifier and contract coverage:** every tested behavior, including
  behavior enforced by shared verifier helpers, must have a
  solver-visible home in `instruction.md`, a referenced environment
  contract doc, or a visible code/docstring stub. Every required
  structured-output field needs value-level test coverage; boolean
  fields cover both polarities when both states matter. Test docstrings
  should name observable invariants in plain language.
- **Clean collapse by construction:** oracle targets should be
  distributed across real fix roots, use opaque manifest-declared
  symbols, and avoid instruction/path noun collisions. Oracle writes
  should be comparable to existing environment files; for inline
  Python writes, prefer `os.chdir("/app/environment")` plus relative
  `Path("pkg/file.py").write_text(...)`. Avoid tiny semantic diffs
  hidden in whole-file rewrites; GX2/GX3 should pass honestly, not via
  padding.

## 4. Preflight

```bash
./scripts/check-task.sh tasks/<task-name>
```

All three phases must pass:

- Phase A — `scripts/run_static_checks.py` then `scripts/collapse_check.py`.
- Phase B — `scripts/validate_submission_zip.py` against a tmp-zip preview.
- Phase C — writes `tasks/<task-name>/.step2b-checksum` and appends
  to `tasks/<task-name>/.step2b-metrics.jsonl`.

A FAIL or WARN in Phase A is a missed construction-time signal unless
a human reviewer explicitly accepts it later. The authoring default is
`scripts/collapse_check.py` with 0 FAIL and 0 WARN before oracle. Read the
specific check, use `python3 scripts/collapse_check.py tasks/<task-name> --json`
when needed, apply substantive fixes only, then rerun the script. The
checksum will catch any subsequent edit.

## 5. Step 2b PASS criteria

Preflight green, including clean collapse (0 FAIL / 0 WARN), AND both
of the following per `commands.md`:

```bash
harbor run -p "tasks/<task-name>" -a oracle    # 1x — no -k
harbor run -p "tasks/<task-name>" -a nop
```

Oracle must score 1.0; NOP must score 0.0. Do **not** run oracle 10x
here — that is `tb3-packager`'s job in Step 4.

If either fails, fix, then rerun preflight (the checksum is now
stale) before re-running oracle / NOP. See
`00-authoring-critical.mdc` §4.

## 6. Confirm instrumentation output

Before declaring PASS:

- `tasks/<task-name>/.step2b-checksum` exists (Phase C wrote it).
- `tasks/<task-name>/.step2b-metrics.jsonl` exists with records for
  this preflight: a `run_id` value, `run_static_checks` outcome
  `PASS` (FAIL count for the final invocation is 0), `collapse_check`
  outcome `PASS`, and `timestamp_ns` populated on every record.

If the metrics file is missing or empty, surface that before
claiming PASS — it blocks the metrics block in Step 4.

## 7. Hand-off

Report:

- Files drafted (one line per file).
- Preflight phase verdicts (A / B / C).
- Oracle and NOP scores, verbatim from harbor output.
- Sentinel files confirmed (checksum + metrics).

Then say verbatim:

> Step 2b complete. Ready for Step 3b paper review (pull
> `tb3-reviewer` skill).

Stop. Do not run `scripts/validate_submission_zip.py` standalone, oracle
10x, or `scripts/approve_task.py` here — those are Step 4.
