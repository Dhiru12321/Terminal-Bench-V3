# CNI-firing parser

## Goal

Populate the `cni_references_fired` field of the per-task authoring
metrics block so the next demotion review has the policy's stated
primary input — an in-window agent-side detector of which CNI items
fired during a given authoring.

## Trigger

Q1 demotion review (`docs/exec-plans/v2.1-demotion-review-q1.md`)
found that 14 of 14 bullets are bound either to live counters
(5 bullets — AGENTS.md #2, #4, #5; §3, §4) or to a deferred signal
(9 bullets — AGENTS.md #1, #3; §0, §1, §2, §5, §6, §7, §8 — five of
which currently render "fired" only via *secondary* signals like
reviewer-grep, lint_spec implicit fires, or maintainer-side CNI
history). Without the parser, the next two quarterly reviews will
have to lean on the same secondary signals as Q1, and the policy
never reaches its design intent.

The deferred-parser gap is documented in two existing places:

- `docs/exec-plans/instrumentation.md` "False-positive risk" → "CNI-fired
  list population" (the original deferral, with the choice of (b)
  empty-list-and-defer over (a) wire-machine-readable-footers).
- `scripts/approve_task.py:790-797` (`render_metrics_block` docstring: *"The
  deferred fields `cni_references_fired` and `draft_commitments_diff`
  always render as `[]` and `null` respectively until follow-up
  exec-plans ship parsers."*).

This exec-plan is the (a) → (b) flip those docstrings anticipated.

## Change surface (anticipated; refine on landing)

This exec-plan is the pre-commitment artifact. The PR implementing it
must either hit exactly these files or file an amendment naming the
divergence — same contract as `docs/exec-plans/instrumentation.md`.

- **New: `cni_collector.py`.** Library module that owns the
  spec/reviewer scan and the resulting CNI-item-id list. Exposes
  `scan_for_fired_cni(spec_path, reviewer_path, *, run_id) -> list[str]`
  returning a list of CNI-item slugs in deterministic order. The
  module reads `CNI.md`, parses each `## …` heading into a
  slug + canonical title, and scans the spec/reviewer markdown for
  matches.
- **Modified: `scripts/metrics_collector.py`.** `aggregate(task_dir)` gains
  a parallel call to `cni_collector.scan_for_fired_cni(...)` and
  surfaces the result under the `cni_references_fired` key. The new
  read is gated on `TB3_CNI_COLLECTOR=1` env var (defaults on for
  the CLI path, off for library callers and existing tests) so
  pre-existing fixtures don't tip over on the first land.
- **Modified: `scripts/approve_task.py`.** `render_metrics_block` already
  reads `cni_references_fired` from the aggregated dict; the body of
  `aggregate()` populates it (no change in `render_metrics_block`'s
  contract). The deferred-fields docstring at lines 790-797 gets
  updated to reflect the new state — `cni_references_fired` is
  promoted from "deferred" to "live" once this exec-plan lands;
  `draft_commitments_diff` stays deferred and gets its own follow-up
  exec-plan when its bar clears.
- **Modified: `validation_log.append_metrics_block`.** No surface
  change — the helper already passes the aggregated dict through
  `render_metrics_block`. Pinned by an existing test plus one new
  assertion.
- **New: `repo_tests/test_cni_collector.py`.** Pin the grep semantics
  (see Tests below).

The change is purely additive on top of existing instrumentation.

## Detection contract

Two design choices to make at landing time. Both are listed here so
the implementer can pick with eyes open and document the choice in a
docstring.

- **Choice 1 — explicit "fired:" prefix vs. fixed `## CNI references
  fired` block.** The two false-positive mitigations from
  `instrumentation.md` "False-positive risk":
  1. Require an explicit `fired:` prefix in spec/reviewer markdown
     (e.g. `fired: milestone-language-warning`). Restrictive but
     forgeable; an author copy-pasting a CNI title in passing won't
     accidentally match.
  2. Restrict the grep to a fixed `## CNI references fired` block
     authors are required to include in the reviewer markdown. More
     structural; a missing block is a no-op rather than an error.
  Recommendation: ship (2) first because it composes with the
  existing reviewer-template structure. Promote to (1) if (2) shows
  >5% miss rate after one quarter.

- **Choice 2 — slug normalization.** `CNI.md` uses heading text like
  `## Codebase-to-fix-surface ratio floor` and tracked-item subheadings
  like `### Fixture-mirror gap promoted to packager skill (filed
  2026-05-06)`. The parser should normalize to a slug (`lowercase`,
  whitespace → `-`, drop parenthetical filed-dates) so the metrics
  block records a stable identifier across reviews. The slug
  generator should be unit-tested (see Tests).

## False-positive risk

Walked per pattern.

- **Spec/reviewer text that quotes a CNI item title in passing
  without the item actually firing.** Example: a reviewer writing
  *"this is not a milestone-language case"* would match a literal
  `milestone-language-warning` slug substring. **Mitigation:**
  Choice 1 above — the fixed `## CNI references fired` block, with
  one slug per bullet under the heading. Free-text mentions outside
  that block are ignored. The `instrumentation.md` deferral
  explicitly named this risk; (2) is the chosen mitigation.

- **Authors not including the new block in older specs.** Specs
  authored before this exec-plan lands won't have the section. The
  parser must treat absence as `[]` (the current default), not as a
  parse error. Existing 19 logs continue to render `[]` until a
  re-run authoring populates them. **Pinned by**
  `test_metrics_block_with_no_cni_block_renders_empty_list`.

- **Slug drift across CNI edits.** If a CNI heading is renamed,
  prior fired-records become orphaned slugs in old metrics blocks.
  The parser must either (a) freeze slugs at the time of fire (the
  recorded slug is historical, not a live cross-reference) or (b)
  refuse to parse if the spec's slug isn't present in the current
  `CNI.md`. Recommendation: (a). Slugs in metrics blocks are
  audit-trail entries, not live foreign keys. **Pinned by**
  `test_metrics_block_records_slug_at_time_of_fire`.

- **Multiple-fire deduplication.** A CNI item cited twice in the
  reviewer block should record once, not twice. **Pinned by**
  `test_duplicate_cni_cites_dedupe_to_single_record`.

- **Unicode/whitespace edge cases.** CNI headings are free-text;
  authors might paste with non-breaking spaces, smart quotes, or
  trailing whitespace. The slug normalizer must NFC-normalize and
  trim. **Pinned by** `test_slug_normalizer_handles_nfc_and_smart_quotes`.

## Effect on existing fixtures and tasks

- **The 19 in-scope validation logs (Q1 review):** unchanged. They
  render `[]` because none of them include a `## CNI references fired`
  block. Re-running their authorings would not produce a different
  log without re-authoring the spec/reviewer markdown.
- **Pre-existing `repo_tests`:** none should change status. The
  env-var opt-in (`TB3_CNI_COLLECTOR=1`) is the primary mechanism
  that keeps existing fixtures unaffected. Default for the library
  entry point is `False`; only the CLI defaults to `True`.
- **`scripts/approve_task.py` test fixtures:** the deferred-fields docstring
  update at lines 790-797 is documentation only; existing
  `repo_tests/test_approve_task.py` cases that pin
  `cni_references_fired == []` should continue to pass when
  `TB3_CNI_COLLECTOR=0`. New tests pin the populated path under
  `TB3_CNI_COLLECTOR=1`.

## Tests

- **`test_scan_returns_empty_when_no_block_present`** — synthetic spec
  + reviewer with no CNI references block; expect `[]`.
- **`test_scan_returns_slugs_from_block`** — synthetic reviewer with
  a `## CNI references fired` block listing two known CNI titles;
  expect both slugs in deterministic order.
- **`test_scan_ignores_inline_quotes_outside_block`** — synthetic
  reviewer that mentions a CNI title in inline prose ("this is not a
  milestone-language case") but has no block; expect `[]`.
- **`test_slug_normalizer_handles_nfc_and_smart_quotes`** — feed
  `## Codebase‑to‑fix‑surface ratio floor` (with U+2011 non-breaking
  hyphen and smart-quote variants); assert canonical slug matches the
  ASCII baseline.
- **`test_duplicate_cni_cites_dedupe_to_single_record`** — block lists
  the same CNI twice; expect single slug in result.
- **`test_metrics_block_records_slug_at_time_of_fire`** — slug
  recorded at scan time; subsequent rename of the CNI heading does
  not retro-update old metrics blocks.
- **`test_env_var_opt_in_gates_collector`** —
  `TB3_CNI_COLLECTOR` unset/`0` returns `[]` regardless of input.
- **`test_metrics_block_renders_populated_list`** — end-to-end:
  synthetic task + spec + reviewer with two CNI fires under the
  block, run `scripts/approve_task.py --emit-metrics`, assert the rendered
  block's `cni_references_fired` line lists both slugs in
  deterministic order separated by commas inside the brackets.
- **`test_existing_19_corpus_unchanged_until_re_authored`** —
  regression: read all 19 in-scope `specs/<task>-validation-log.md`
  files; assert `cni_references_fired` is still `[]`. Pins the
  expectation that the parser does not retro-edit old logs.

## Rollback

1. Revert `cni_collector.py`, the `scripts/metrics_collector.py` change,
   the `scripts/approve_task.py` docstring update, and the new test file.
2. Re-pin the deferred-fields docstring at `scripts/approve_task.py:790-797`
   to the original "always render as `[]` and `null` respectively
   until follow-up exec-plans ship parsers" wording.
3. Existing logs with populated `cni_references_fired` are
   historical record; do not retroactively scrub them. The next
   demotion review will see them as a partial signal during the
   rollback window, which is acceptable.

## Verification done

- [ ] `cni_collector.py` shipped with NFC normalization and the
  `## CNI references fired` block contract.
- [ ] `metrics_collector.aggregate()` populates the new field when
  `TB3_CNI_COLLECTOR=1`.
- [ ] `scripts/approve_task.py:790-797` docstring updated to reflect the
  promotion of `cni_references_fired` from deferred to live.
- [ ] `repo_tests/test_cni_collector.py` covers all bullets in the
  Tests section above.
- [ ] Baseline `repo_tests` failure-set fingerprint unchanged when
  `TB3_CNI_COLLECTOR=0` (verifying the env-var opt-in keeps the
  pre-existing test surface stable).
- [ ] `repo_tests/cases.py` updated if any new pass-message lands.
- [ ] `REPO_CONVENTIONS.md` and `commands.md` updated with one-line
  pointers to the new env-var and the reviewer-template block
  contract.
- [ ] First Q2 quarterly review reads the new field and exits the
  "all bullets bound to deferred parser get plausible" branch for
  at least one bullet (proving the parser changes review behavior
  in practice).
