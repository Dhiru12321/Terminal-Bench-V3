# Cursor behavior verification

## Goal

Document Cursor 3.2.x's actual behavior on `@`-references and
`.cursor/skills/<name>/SKILL.md` so phase 2's skills-layer path
can be locked with evidence rather than assumption.

## Trigger

v2.1 §6 explicitly flags both behaviors as unverified. Phase 2
entry depends on knowing the answer.

## Investigation done

Three evidence channels were used. Per the Task B hard rules,
no probe files were created under `.cursor/skills/` or
`.cursor/rules/`, and no Cursor-side settings were modified.

### Channel 1 — workspace filesystem inventory

- `ls -la .cursor/` — contains `rules/` only. No `skills/`,
  no `commands/`.
- `find . -name 'SKILL.md'` — zero matches in the workspace.
- `ls -la skills/ prompts/` at workspace root — neither exists.
- `ls -la /home/mrkunfusion/.cursor/` — contains
  `skills-cursor/` (Cursor's managed built-in skill bundle per
  docs below), `plans/`, `plugins/`, `projects/`,
  `ide_state.json`, and `.gitignore`. Notably does **not**
  contain `skills/` or `commands/` — i.e. neither the personal
  user-level skills dir nor user-level slash commands are
  currently populated.

### Channel 2 — current-conversation system prompt

What I can directly observe in the injected system prompt for
this turn:

- **`<always_applied_workspace_rules>` bucket** contains two
  entries: `AGENTS.md` and `.cursor/rules/review-and-submit.mdc`.
  `review-and-submit.mdc` has `alwaysApply: false` in its
  frontmatter, so its presence in this bucket proves Cursor
  evaluated its `globs:` list, found a match
  (`tasks/barrier-replay-truncation/instruction.md` in the
  recently-viewed-files block matches `tasks/*/instruction.md`),
  and auto-attached the full body.
- **`<agent_requestable_workspace_rules>` bucket** contains
  exactly one entry: `idea-validation.mdc`. Not listed:
  `task-creation.mdc`, `difficulty-calibration.mdc`,
  `00-authoring-critical.mdc`. All three have descriptions; two
  of them match Agent-Requested frontmatter (description only,
  no globs, `alwaysApply: false`). Their absence is one of the
  unresolved questions below.
- **Plain-text documentation of `@`-references** in the system
  prompt: "Users can reference context like files and folders
  using the @ symbol, e.g. @src/components/ is a reference to
  the src/components/ folder." This is Cursor's own contract
  text, not inference.
- **`<available_skills>` bucket** lists eight SKILL.md files,
  every one of them under `/home/mrkunfusion/.cursor/skills-cursor/`
  (Cursor's managed built-in bundle). Zero workspace-level
  skills appear — consistent with channel 1's finding that
  `.cursor/skills/` is not populated.

### Channel 3 — Cursor's own bundled skill documentation

Two of the built-in skills under `~/.cursor/skills-cursor/` are
authoritative references for the questions in Task B:

- **`~/.cursor/skills-cursor/create-skill/SKILL.md`**, section
  "Storage Locations", table:

  | Type | Path | Scope |
  |---|---|---|
  | Personal | `~/.cursor/skills/skill-name/` | Across all projects |
  | Project | `.cursor/skills/skill-name/` | Shared with anyone using the repo |

  Same file, IMPORTANT callout: "Never create skills in
  `~/.cursor/skills-cursor/`. This directory is reserved for
  Cursor's internal built-in skills and is managed automatically
  by the system."

- **`~/.cursor/skills-cursor/migrate-to-skills/SKILL.md`**
  describes the contract for converting Agent-Requested rules
  (rules with `description` but no `globs` and not
  `alwaysApply: true`) into SKILL.md files under
  `.cursor/skills/<name>/SKILL.md`, and converting slash commands
  at `.cursor/commands/*.md` into the same shape.

These two files are shipped as loaded, active skills in the
current conversation — they are Cursor's own up-to-date
documentation, not a third-party forum post.

## Findings

### (1) `@filename` reference syntax

**Status: behavior observed (partially) + documented (fully).**

What is directly observable in this conversation:

- Cursor *does* inject file content into the agent's context
  when a rule's `globs` match a file in the IDE's
  recently-viewed set. Proof: `review-and-submit.mdc` is in the
  `<always_applied_workspace_rules>` bucket despite
  `alwaysApply: false`. This is the "Auto Attached" mode
  working end-to-end in the installed Cursor version.
- Cursor exposes Agent-Requested rules as a path + description
  pair and directs the agent to `Read` them on demand. Proof:
  `idea-validation.mdc` appears this way.

What is documented but not directly observable from the agent
side:

- Whether the user typing `@filename.mdc` in the chat input
  pulls the file into context — Cursor's own system-prompt
  contract text says it does, and the description field on
  `idea-validation.mdc` instructs users to "use
  `@idea-validation.mdc` explicitly", which only works if the
  user-typed `@` syntax works.

**Conclusion: `@filename` is the real contract.** The
combination of (a) Cursor's own documented contract for users
typing `@`, (b) directly observed glob-based auto-attach on
this turn, and (c) directly observed Agent-Requested listing on
this turn is enough evidence to lock paths that depend on
`@filename` semantics.

### (2) `.cursor/skills/<name>/SKILL.md`

**Status: documented as supported (strongly) + live behavior
uncertain in this workspace (because no SKILL.md has been
created to probe).**

What Cursor's own built-in skills documentation says (channel 3):

- `.cursor/skills/<name>/SKILL.md` is the canonical
  **project-level** skill path. It is "shared with anyone using
  the repository" (create-skill SKILL.md, Storage Locations
  table).
- The SKILL.md frontmatter schema is fixed: `name` (lowercase
  with hyphens), `description` (critical for skill discovery),
  optionally `disable-model-invocation: true`.
- An entire bundled skill, `migrate-to-skills`, exists
  specifically to convert `.cursor/rules/*.mdc` files with the
  Agent-Requested shape into `.cursor/skills/<name>/SKILL.md`
  files. That skill would be pure dead code if
  `.cursor/skills/` were cosmetic.
- The v1 plan's skepticism — "forum post about a *bug* that
  creates SKILL.md files, not a documented feature" — is
  out-of-date. The installed Cursor version ships
  `create-skill/SKILL.md` in its managed bundle, which
  documents `.cursor/skills/<name>/SKILL.md` as a first-class
  supported path.

What is **not** directly verifiable from the agent side:

- Whether this workspace's `.cursor/skills/<name>/SKILL.md`
  (once populated) will actually appear in the
  `<available_skills>` bucket of a future conversation's
  system prompt. This is the one probe that requires either
  creating a test skill — forbidden by Task B's hard rules —
  or a manual user action outside the agent's control.

**Conclusion: `.cursor/skills/<name>/SKILL.md` is the right
path by documentation, but a single manual probe is prudent
before locking phase 2 assets to it.** See Open questions §1.

### (3) `disable-model-invocation: true` frontmatter field

**Status: fully documented in Cursor's bundled skill docs.**

Two citations from the installed Cursor version's managed
skill bundle close this question:

- `~/.cursor/skills-cursor/create-skill/SKILL.md` line 89:
  *"Default `disable-model-invocation: true` so the skill only
  loads when named explicitly. Omit it only when the agent
  should auto-invoke from ambient context."*
- `~/.cursor/skills-cursor/migrate-to-skills/SKILL.md` line 82:
  *"The `disable-model-invocation: true` field prevents the
  model from automatically invoking this skill. Slash commands
  are designed to be explicitly triggered by the user via the
  `/` menu, not automatically suggested by the model."*

Semantics:

- `disable-model-invocation: true` → skill does not auto-fire
  from ambient context; only loads when named explicitly.
- Omitted or `false` → model may auto-invoke the skill when
  its `description` matches the conversation's apparent intent.

Dogfood evidence that the flag is taken seriously: every
bundled Cursor skill that should not fire spuriously sets
`disable-model-invocation: true`. Directly confirmed on
`create-skill/SKILL.md` line 77, `migrate-to-skills/SKILL.md`
line 8, `create-subagent/SKILL.md` line 7, and
`shell/SKILL.md` line 7 (the last two caught by the same
grep). The docs and the dogfood agree.

**Implication for phase 2 skills.** The three workflow
fragments (`tb3-task-author`, `tb3-reviewer`, `tb3-packager`)
are scoped to specific step transitions and should all ship
with `disable-model-invocation: true` so the model cannot
opportunistically auto-invoke them. Live enforcement of the
flag in the installed Cursor version remains unverified (the
probe in Open questions §1, if extended to set
`disable-model-invocation: true` on the stub, would close
it), but the documented contract is strong enough to author
the three skills against.

## Decisions enabled

- **Phase 2 skills-layer path — recommend
  `.cursor/skills/<name>/SKILL.md`.** This is the
  documentation-backed project-level path per Cursor's own
  bundled `create-skill` and `migrate-to-skills` skills.
  File layout: `.cursor/skills/tb3-task-author/SKILL.md`,
  `.cursor/skills/tb3-reviewer/SKILL.md`,
  `.cursor/skills/tb3-packager/SKILL.md` — one directory per
  skill, each containing a SKILL.md with `name` and
  `description` frontmatter plus body.

- **Single fallback if the manual probe in Open questions §1
  fails: `prompts/<name>.md` at workspace root.** The agent
  loads these on demand via `Read`; they are not auto-attached
  by Cursor.

  An earlier draft of this exec-plan proposed `skills/<name>.md`
  at workspace root as an intermediate option. Dropped:
  neither Cursor-recognized nor a familiar convention. Naming
  a plain-markdown directory `skills/` would invite the
  confusion "is this a Cursor skills dir that just isn't
  loading?" and would collide semantically with
  `.cursor/skills/` if a later probe shows the Cursor-managed
  path working. `prompts/` is the honest fallback — it signals
  plain on-demand text, not a registered loader path.

- **Auto-attached rules — phase 2 can trust them.** The
  directly observed glob match on `review-and-submit.mdc` this
  turn proves Auto Attached mode (Finding 4 of the corrections
  round) is working as intended. Phase 2 can assume that any
  rule with proper `globs:` will fire when its globs match an
  open/recently-viewed file.

- **Agent-Requested rules — phase 2 can trust them, with a
  caveat.** Agent-Requested rules do appear in the
  `<agent_requestable_workspace_rules>` bucket, proving the
  mode works. However, only a subset appears per turn
  (`idea-validation.mdc` showed up; `difficulty-calibration.mdc`
  and `00-authoring-critical.mdc` did not). The selection
  algorithm is not documented and may be relevance-based or
  turn-budget-based. See Open questions §2.

- **CNI §Promotion — no blocker.** Skills-layer authoring
  under `.cursor/skills/<name>/SKILL.md` unblocks the three
  phase-2 workflow fragments (`tb3-task-author`,
  `tb3-reviewer`, `tb3-packager`). Creation is downstream of
  this exec-plan and the probe in Open questions §1, not part
  of this unit.

## Open questions

These require action outside the agent sandbox.

1. **Does the installed Cursor version actually load a
   `.cursor/skills/<name>/SKILL.md` placed in this workspace?**
   Manual probe: in the IDE, create
   `.cursor/skills/tb3-probe/SKILL.md` with minimal frontmatter
   (`name: tb3-probe`, `description: Phase-2 probe — safe to
   delete`) and a trivial body. Open a fresh conversation and
   ask the agent whether `tb3-probe` appears in its skills
   bucket or is referenced anywhere in its context. If yes:
   lock phase-2 path to `.cursor/skills/<name>/SKILL.md` and
   delete the probe. If no: fall back to `prompts/<name>.md`
   per Decisions enabled §fallback.

2. **What is the selection algorithm for Agent-Requested
   rules?** Observed data: `idea-validation.mdc` surfaced this
   turn; `difficulty-calibration.mdc` and
   `00-authoring-critical.mdc` did not, despite all three
   being Agent-Requested. Hypotheses (not tested): relevance
   scoring on description text vs. the user query; a
   per-turn cap; a stale cache. This is a nice-to-know for
   designing descriptions but does not block phase 2 — the
   `Read`-on-demand fallback works regardless.

3. **Are `.cursor/commands/*.md` slash commands supported in
   the installed version?** The `migrate-to-skills` SKILL.md
   describes both `.cursor/rules/` → `SKILL.md` and
   `.cursor/commands/` → `SKILL.md` migration paths, implying
   slash commands exist at the source. Currently the
   workspace and user home both lack `commands/`
   directories, so there is nothing to observe. v2.1 plan §6
   does not rely on slash commands; deferring this question
   is safe.

## Verification done

- [x] `docs/exec-plans/cursor-behavior-verification.md` exists.
- [x] Both behaviors from Task B are documented with explicit
  observed-vs-documented-vs-uncertain status.
- [x] A recommendation for phase-2 skills-layer path is
  present, with a single documented fallback if the recommended
  path fails manual probe.
- [x] Open questions enumerated; each names what would close it.
- [x] No probe files were created under `.cursor/skills/` or
  `.cursor/rules/`; no existing rule frontmatter was modified
  by this task.
- [x] `repo_tests` baseline (137/32) unchanged — this exec-plan
  is documentation only.
- [x] Manual probe procedure documented with steps, outcomes,
  and a mandatory cleanup clause (see `## Manual probe procedure`
  below).
- [ ] Probe run by user; outcome and decision recorded under
  `## Probe results` below. This checkbox flips to `[x]` when
  Open questions §1 is resolved.


## Manual probe procedure

The remaining blocker for phase-2 path lock is Open questions §1
— does the installed Cursor version actually load a
`.cursor/skills/<name>/SKILL.md` placed in this workspace? The
agent cannot run this probe itself (Task B's hard rules forbid
creating files under `.cursor/skills/`). The user runs the
probe and records the outcome under `## Probe results` below.

### Step 1 — create the probe skill file

From the workspace root:

```bash
mkdir -p .cursor/skills/tb3-probe
cat > .cursor/skills/tb3-probe/SKILL.md <<'EOF'
---
name: tb3-probe
description: Phase-2 probe — safe to delete. Tests whether Cursor auto-loads workspace-level SKILL.md files.
disable-model-invocation: true
---
# tb3-probe — verification stub for cursor skills loading
EOF
```

Notes on this frontmatter:

- `name: tb3-probe` matches the schema in
  `~/.cursor/skills-cursor/create-skill/SKILL.md` (lowercase
  letters and hyphens only).
- `disable-model-invocation: true` is included so the probe
  cannot accidentally fire from ambient context if Cursor does
  load it. The flag does not affect *loading*; it only affects
  auto-invocation (see Finding (3)).

### Step 2 — fully restart Cursor

Quit the Cursor application entirely (Cmd/Ctrl+Q or File →
Quit). A window reload is **not** enough — the skills bucket
is initialized at application start, not at window open.
Relaunch Cursor and reopen this workspace.

### Step 3 — open a fresh agent conversation

Do **not** resume an existing chat. The skills bucket is
attached at conversation start; an already-running chat has
its bucket fixed from when it was opened.

### Step 4 — ask the agent what it sees

Copy-paste this prompt verbatim into the fresh chat:

> List every entry in your `<available_skills>` system-prompt
> block. For each, give the `fullPath` attribute and the first
> line of the file's body.

The agent will dump the bucket verbatim. The exact bucket name
to look for is `<available_skills>`, containing
`<agent_skill fullPath="…">` elements (this is the same
structure directly observed in the Task B investigation).

### Step 5 — classify the outcome

Look for a line of the form:

```
<agent_skill fullPath="/…/tb3-gate-hardened-with-platform-rules/.cursor/skills/tb3-probe/SKILL.md">
```

and compare against one of three outcomes:

- **Outcome A — probe appears in `<available_skills>` with the
  expected path and description line.** The primary path
  `.cursor/skills/<name>/SKILL.md` is live-verified. Lock
  phase-2 path to it; proceed to author `tb3-task-author`,
  `tb3-reviewer`, `tb3-packager` at
  `.cursor/skills/<name>/SKILL.md`, each with
  `disable-model-invocation: true`.

- **Outcome B — probe does not appear in `<available_skills>`
  (or anywhere else in the agent's context).** The
  documentation-backed primary path is not loaded by the
  installed Cursor version. Fall back to `prompts/<name>.md`
  at workspace root per the Decisions enabled section. The
  three phase-2 workflow fragments then become
  `prompts/tb3-task-author.md`, `prompts/tb3-reviewer.md`,
  `prompts/tb3-packager.md`, loaded by the agent on demand
  via `Read`.

- **Outcome C — probe loads but with unexpected metadata.**
  Examples: `fullPath` resolves under an unexpected directory;
  `name` renders differently; a `disable-model-invocation:
  true` skill fires anyway from ambient context; description
  is truncated unexpectedly; the skill shows up in a bucket
  other than `<available_skills>`. Do **not** lock phase-2
  paths yet. Paste the unexpected observation verbatim under
  `## Probe results` and raise it before authoring real
  skills.

### Step 6 — cleanup (mandatory)

After the outcome is recorded under `## Probe results`, delete
the probe entirely:

```bash
rm -rf .cursor/skills/tb3-probe
```

If `.cursor/skills/` is now empty, leaving the empty directory
is fine (it will not be loaded). The `tb3-probe` stub itself
must not survive the investigation — a leftover probe skill
creates "is this real or a probe?" ambiguity for anyone
reading the repo later. Cleanup is a hard requirement of this
procedure, not an optional nicety.

## Probe results

- **Date:** 2026-05-04
- **Cursor version:** 3.2.21
- **Probe artifact:** `.cursor/skills/tb3-probe/SKILL.md` (60 bytes, single
  identifiable line `# tb3-probe — verification stub for cursor skills loading`)
- **Restart performed:** full Cursor quit + relaunch (not a window reload)
- **Probe prompt issued:** "List the skills currently available in your
  `<available_skills>` context block. Just the names, no descriptions."
- **Observed outcome:** **A — probe appears as expected.**
  Fresh agent's `<available_skills>` listed `tb3-probe` alongside Cursor's
  ten bundled skills (`babysit`, `canvas`, `create-hook`, `create-rule`,
  `create-skill`, `cursor-sdk`, `split-to-prs`, `statusline`,
  `update-cursor-settings`). No anomalies: name reported as `tb3-probe`,
  no metadata corruption, project-level skill loaded with the same
  surface as bundled skills.
- **Decision:** Skills-layer path locked at
  `.cursor/skills/<name>/SKILL.md`. Phase 2 will author the three workflow
  skills (`tb3-task-author`, `tb3-reviewer`, `tb3-packager`) at this path,
  each with `disable-model-invocation: true` per Finding (3) of this
  exec-plan. The `prompts/<name>.md` fallback is no longer needed and
  is dropped from active consideration.
- **Probe cleanup confirmed:** yes. `rm -rf .cursor/skills/tb3-probe`
  ran cleanly; subsequent `ls -la .cursor/skills/` showed an empty
  directory (only `.` and `..`). No probe artifacts remain.
