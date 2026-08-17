# Implementation Collapse Audit

Use this file whenever a task idea looked promising at first, but you want to know whether the **concrete instance** would collapse into something too easy.

This file exists because many weak tasks do **not** fail at ideation. They fail later, when the implementation plan, file tree, and verifier make the real solve path obvious and tiny.

## Core Principle

Always judge the task at its **current stage**, not by the strength of the original idea family.

A task can start with a strong real-world concept and still collapse into a trivial benchmark once:

- the prompt honestly states the checked behavior
- the editable frontier is only a few obvious files
- the verifier maps each requirement to one obvious helper or config block
- the oracle mostly overwrites one small declarative cluster

## 5 Hardness Axes (must satisfy ALL)

A task is hard only when solving it requires the agent to:

1. **Discover** — find information not in the instruction (by reading code, running experiments, analyzing behavior). Specifically: list 3+ facts the agent must discover from the codebase. If you can't, this axis fails.
2. **Synthesize** — build understanding across multiple interacting systems; no single file contains the answer. If the fix is in one file, this axis fails.
3. **Diagnose** — figure out WHAT is wrong from symptoms, not from being told the cause. If the instruction specifies exact correct behavior (thresholds, schemas, formulas), diagnosis is replaced by spec-diffing and this axis fails.
4. **Navigate coupling** — handle cases where local fixes break distant invariants. If each bug can be fixed independently, this axis fails.
5. **Reason beyond training** — apply domain-specific reasoning that can't be pattern-matched from common implementations

**Instruction completeness test:** Can the agent solve the task by reading ONLY instruction.md without deeply engaging with the codebase? If yes, the instruction IS the specification, and implementing specs is easy. This includes "fix broken code" tasks where the instruction specifies every correct behavior — the agent just diffs spec against code.

**The #1 failure mode (79% of easy/trivial tasks):** The task is "implement this spec" — the instruction gives complete algorithms, schemas, rules, and output formats. The agent just translates English to code. Complex output (200-field JSON, 8 validation rules, multi-stage pipelines) ≠ hard problem. Fan-out from a few simple fixes is not hardness.

## Fatal Question

Ask this first:

> After the prompt is fully honest and the concrete file tree is visible, what nontrivial reasoning still remains?

If the answer is "not much" or "mostly transcription / recipe filling / tiny local repair," the task is not hard enough for this bundle.

## Post-Disclosure Collapse Test

Hidden requirements are not allowed. But if revealing the requirement makes the
task easy, regenerate or reject the task instead of hiding the rule.

After every externally tested formula, invariant, constant, event rule, and
schema is solver-visible, ask whether the remaining work is mostly matching
each public rule to one obvious function or module. If yes, reject or redesign.

Bad: event semantics state exact `WAKE`/`TICK` formulas, and each formula maps
to one named function. Bad: tests directly import the coordination modules and
assert the same formulas documented in `contract.md`. Good: visible contract
defines product-level outcomes, but the solver must discover which
authority/source/path controls them under runtime variation, and local formula
matching is insufficient.

Python tasks need especially strong post-disclosure hardness because strong
models are good at direct source-code formula repair.

## Output-Contract Design Audit

Structured outputs should expose observations, traces, measurements, artifacts,
or run records. Tests should derive verdicts from those records instead of
asking the solver to emit named truth bits.

Avoid named boolean verdict fields unless they are a real product contract.
Fields ending in `_ok`, `_green`, `_valid`, `_passes`, or `_stays_green` need a
specific justification. Avoid `scenario->key->expected` boolean tables in
`instruction.md`.

Prefer cross-run invariants, metamorphic properties, round-trip checks, derived
hashes from visible formulas, state convergence, schema/type checks, and
partial-revert traps. If exact formulas, types, sizes, constants, digest
algorithms, or tolerances are tested, they must be visible.

Bad:

```json
{
  "readiness_green_alpha": true,
  "bodies_match_across_profiles": true
}
```

Good:

```json
{
  "runs": [...],
  "entries": [...],
  "refreshes": [...]
}
```

## Category-Profile Check

Before the generic collapse tests, bind the candidate to one initial category
profile from `TASK_PROPOSAL_RUBRIC.md` and answer the profile-specific checks.
This is validation, not labeling.

Repo source of truth: `docs/CATEGORY_PROFILES.md`. The audit must check the
profile's allowed inferential leaps, anti-patterns, recommended output-contract
shape, recommended verifier structure, and waiver pressure in addition to the
basic hard bar and one-shot collapse mode.

Required profile audit fields:

```yaml
category_profile:
  bug_family:
  profile_name:
  allowed_instruction_disclosures:
  forbidden_instruction_leaks:
  category_specific_hardness_bar:
  category_specific_verifier_risks:
  coverage_role:
satisfiability_risk:
  rc2_planned_name_risk:
  gx9_contract_risk:
  cr1_symbol_frontier_risk:
  hidden_contract_risk:
actionability_plan:
  verifier_command_visible:
  source_fix_intent_visible:
  generated_output_rule_visible:
  exact_formula_home:
  schema_home:
waiver_plan:
  waivers_expected:
  waiver_rationale:
```

Reject or regenerate when:

- the candidate uses a broad category label but cannot name a concrete profile
- the profile's required instruction disclosures would make the patch obvious
- the profile's forbidden leaks are already present in symptom wording, titles,
  filenames, planned test names, or artifact names
- verifier risks are not mitigated by the planned evidence surface
- the hard bar reduces to one local patch, one table, one constant, or one
  hidden instance
- the waiver plan expects a waiver for leakiness, hidden requirements, or
  triviality rather than a genuine checker false positive

## Mandatory Information Delta Test

This test catches the single most common failure mode: the instruction fully specifies every correct behavior, so the agent just diffs the spec against the code and patches divergences. This is spec-diffing, not debugging — and it is easy regardless of how complex the output looks.

**Enumerate every piece of information the agent must discover FROM THE CODEBASE that is NOT stated or directly derivable from instruction.md.** Write each item down explicitly.

This list must contain **at least 3 non-trivial items**. Each item must require reading and understanding code or running experiments — not just grepping for a keyword.

Examples of what **counts** as a discovery item:
- "The agent must discover that module X silently truncates timestamps before passing them to module Y, causing downstream drift"
- "The agent must discover that the retry logic in service A conflicts with the connection pool timeout in service B"
- "The agent must discover which of several interacting modules is the actual root cause of the symptom described in the instruction"
- "The agent must discover undocumented coupling between the cache eviction policy and the write-ahead log"

Examples of what **does not count**:
- "The agent must find which line has the wrong constant" — that is grep, not discovery
- "The agent must discover the correct threshold value" — if the instruction already states it (e.g. "session gap must be 600 seconds"), there is nothing to discover
- "The agent must understand the code" — too vague; name the specific fact that isn't in the instruction
- "The agent must find the bugs" — if the instruction specifies every correct behavior, finding bugs = diffing spec against code

**If the list has fewer than 3 items, or if every item reduces to "find where the code doesn't match the spec," the task is not hard. Reject or regenerate.**

### Instruction specificity hierarchy

Use this to evaluate how much the instruction reveals:

- **Spec-complete** (always easy): The instruction gives exact algorithms, thresholds, schemas, formulas, and key names. Example: "Session gap must be exactly 600 seconds; dedup key is (user_id, event_id); risk_score = round((bursts×2 + travel×3 + resets×4 + mfa×5) / max(events,1), 4)." The agent's job is transcription.
- **Cause-revealing** (usually medium): The instruction names the broken component or mechanism but not the full fix. Example: "The cache invalidation key doesn't incorporate file content changes." The agent must still figure out the correct cache strategy.
- **Symptoms-only** (can be hard): The instruction describes observable misbehavior without indicating where or why. Example: "Resumed pipeline runs produce stale aggregates when historical shards are rewritten." The agent must diagnose, locate, and design the fix.

A hard task's instruction must be at the symptoms-only level. If any requirement bullet in the instruction reads like a spec line (exact value, exact schema, exact formula), ask whether that specificity is necessary for the contract or whether it's handing the agent the answer.

### "Fix broken code" ≠ "debug from symptoms"

A common mistake is framing a spec-complete task as "fix this broken pipeline." But when the instruction specifies every correct behavior — thresholds, schemas, formulas, edge cases — then "fix the code" reduces to "make the code match this spec." The codebase is decorative.

Hard debugging tasks require the agent to figure out WHAT is wrong. If the instruction already says what correct behavior looks like at every level of detail, the agent is just proofreading code against a reference document.

## The Audit

For each candidate, answer all of these.

### 1. Residual-hardness test

What remains hard **after** the prompt is honest?

Reject or regenerate if the residual work is mostly:

- filling in named settings
- editing one small mapping table
- implementing a known secure-coding recipe in a tiny scaffold
- rewriting a few obvious helper files from memory
- mechanical alignment between prose bullets and obvious code sites

### 2. Smallest-successful-patch test

State the smallest plausible successful patch in plain English.

Examples of bad answers:

- "set the listed scheduler knobs in the three named files"
- "fix the phase tables for the named rollover stages"
- "rewrite the obvious jail scripts and `sshd_config`"
- "fill in `validate`, `extract`, and `install` with the standard safe-tar recipe"

If the smallest successful patch already sounds easy, that is a major warning sign.

### 3. Editable-frontier test

List the likely editable files or config blocks.

Reject or regenerate when:

- the meaningful frontier is only 1-4 obvious files or helpers
- each major requirement has one obvious destination
- the solver does not need real search to find where to work

A small edit frontier is not automatically fatal, but **small + obvious + directly specified** usually is.

### 4. Requirement-to-file map

Map each requirement to its likely file, function, or config block.

If most prompt bullets map 1:1 to one obvious place, the task may be a checklist rather than a hard problem.

This catches:
- policy-knob transcription
- finite phase-table repair
- toy jail hardening
- pre-factored safe extractor tasks

### 5. Grep-collapse test

Could a strong model grep the exact nouns from the prompt and land directly on the buggy block?

Examples of bad signs:

- prompt phase names match phase-table keys exactly
- prompt security nouns match helper names like `validate`, `extract`, `canon`, `install`
- prompt names exact config files and exact product-specific knobs

If yes, treat that as a serious collapse signal.

### 6. Small declarative cluster test

Reject or regenerate when the real solve is mostly one of these:

- 1-3 config files
- one manifest or seed script
- one tiny state table
- one policy table
- one finite mapping table
- one whole-file overwrite of a short helper

Many dynamic tests can still fan out from one tiny declarative cluster. Do not confuse fan-out with hardness.

### 7. Pre-factored helper / stub-completion test

Look for helpers whose names already encode the task contract, such as:

- `validate`
- `extract`
- `install`
- `canon`
- `ensure-layout`
- `finalize-staged`

If the prompt bullets map directly onto those helpers, the task is often scaffolded completion rather than hard debugging.

### 8. Recipe-discount test

Do not over-credit standard recipes.

Examples that deserve a strong difficulty discount unless there is deeper coupling:

- safe tar extraction
- traversal blocking
- symlink / hardlink escape prevention
- jail permission normalization
- manifest regeneration
- atomic staged-to-active switching
- filling in scheduler policy knobs
- updating finite DNS / key / phase state tables

Security or ops flavor alone does not make a task hard.

### 9. Orthogonal-checklist test

Count **coupled insight clusters**, not number of bullets or tests.

Reject or regenerate when the task is mostly an orthogonal checklist, even if it has many tests:

- each requirement can be implemented independently
- one fix does not force non-obvious tradeoffs with other fixes
- the solver can work linearly through the list without backtracking

### 10. Harness-discount test

Do not count these as difficulty by themselves:

- real daemons
- docker-compose
- databases
- generated malicious inputs
- service topologies
- reset scripts
- seed generators

These increase realism, not necessarily hardness. They only count if the solver must genuinely debug them.

### 11. One-pass solvability test

Ask:

> Could a frontier model plausibly solve this in one pass after opening the obvious files, without running the verifier?

If yes, reject or regenerate for this bundle.

### 12. Profile one-shot test

Compare the concrete instance against the chosen profile's `one-shot collapse`
entry in `TASK_PROPOSAL_RUBRIC.md`.

Reject or regenerate when the smallest successful patch sounds like that
collapse pattern. A profile label does not rescue a one-lock fix, one-table
rewrite, one-version bump, one-regex guard, one-epsilon tweak, one-manifest
restore, or one hidden fixture repair.

## Collapse Early-Stop For Draft Repair

When auditing an already drafted task, do not keep locally patching until
`scripts/collapse_check.py` goes quiet.

Hard stop rules:

- After 2 consecutive `scripts/collapse_check.py` FAILs with the same root-cause set,
  stop local edits.
- After 4 total `scripts/collapse_check.py` FAILs, stop regardless of trajectory.
- If remaining failures include RC2, CR1, CR8, or GX9 and the honest repair
  would require changing paths, output schema, test contract shape, symbol
  frontier, or instruction disclosure level, return to Step 2a.

On stop, emit:

```markdown
## Collapse Redesign Report

- task/spec:
- collapse runs count:
- stable failing checks:
- likely structural root cause:
- local patches already attempted:
- redesign options:
- whether spec amendment required:
- whether waiver might be legitimate:
- commands run:
```

Ban these repair tactics: whitespace padding to dodge GX9; string
concatenation to hide symbols; `importlib`/`getattr` solely to avoid CR8;
homoglyphs; decoy files purely to dilute RC2; renaming helpers solely to chase
CR1; stripping requirements from `instruction.md` to satisfy GX9.

Redesign menus:

- **RC2**: generic-rename package roots before freezing the manifest; move fix
  material into realistic common files; separate instruction nouns from path
  tokens; request waiver only for realistic source-preserving names; avoid
  decoy dilution.
- **GX9**: replace boolean verdict fields with observations, traces,
  measurements, artifacts, or run records; use derived comparisons; move schema
  to `output_contract.toml`; reduce boolean answer keys; never pad or hide
  required behavior.
- **CR1**: make oracle-touched files symbol-thin; move helpers into sibling
  files; declare `co_resident_helpers`; inline small helpers if natural.
- **CR8**: split orchestration honestly; reduce fix-symbol fanout; do not use
  `importlib`, `getattr`, or string tricks.
- **GX6**: symptom causation is okay; patch causation is not; rewrite as
  observable behavior.

## Explicit Reject Patterns From Recent Failures

These patterns should be rejected or regenerated immediately in hard-only mode:

### 1. Disclosed policy-knob transcription
A real scheduler, real service, or real platform is not enough when the prompt names the exact files and exact knobs to set.

### 2. Finite phase-table repair
A live multi-phase system is not enough when the real solution is updating a tiny literal table that already mirrors the prompt vocabulary.

### 3. Toy jail hardening
A real `sshd` or chroot is not enough when the editable core is `sshd_config` plus a few shell scripts and the prompt is an orthogonal security checklist.

### 4. Pre-factored safe extractor
A real updater or archive format is not enough when the codebase already exposes helpers named after the missing textbook protections.

## Decision Rules

Use `GO` only when the task is still clearly hard **at the current stage**.

Use `REGENERATE` when:

- the idea family is still promising, but this concrete instance collapsed
- the file tree or verifier plan made the solve path too direct
- the oracle is too local
- the prompt wording maps too directly to the code
- the draft became a small declarative or recipe repair

Use `STOP` when:

- repeated variants in the same idea family keep collapsing
- the family naturally becomes a toy checklist or local config repair
- the task is only hard in the abstract but not in any practical concrete draft you can author honestly

## Final Reminder

The hardest-looking mistake in this workflow is:

> "The idea is hard in the real world, so this draft must be hard too."

That is false surprisingly often.

Always audit the **actual drafted instance**.
