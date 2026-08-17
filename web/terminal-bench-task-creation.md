# Terminus 3 (Terminal-Bench 3.0) — Standalone Task Creation Guide

Use this file as the canonical authoring reference inside the standalone `web` bundle.

- If any older note or example conflicts with this guide, follow this guide.
- This guide is synced to the current active authoring rules; the active ruleset is `terminus_3`.
- If the active rules are silent or ambiguous on a point, prefer the stricter interpretation already stated elsewhere in this bundle. If the bundle still does not resolve it, flag the ambiguity instead of inventing a new rule.
- This bundle generates for the scarce end of the Terminus 3 curve — `frontier` and `advanced`. Difficulty is measured rather than declared, so draft the provisional tier as `advanced` and, if a candidate looks like it would land in `core` or `base`, regenerate or stop rather than carrying it forward. `core` and `base` are legitimate accepted tiers; they are simply not what this bundle is sized for.

## The Shift This Edition Asks For

Earlier editions asked an agent to perform a difficult terminal task. Terminus 3 asks it to understand a specialized domain, manipulate the right system inside that domain, and produce a result that satisfies several interacting constraints at once.

Tasks are stronger when:

- the requirements must be **inferred from domain evidence** rather than read off the instruction
- the output is a **semantically valid artifact** rather than something that merely looks right
- correctness spans **several axes that affect one another**, so a fix on one axis can break another

Keep this framing in view while shaping the idea. It is the difference between a task that is long and a task that is hard.

## Intake Rules

### Required inputs

1. **Task idea**
   What should the task accomplish? What problem should the agent solve?

2. **Programming language(s)**
   Use the primary implementation languages the task actually needs. The dataset targets Python, C, C++, JavaScript, TypeScript, Java, Go, Rust, and C#, and multi-language tasks are preferred. `languages` records only the primary implementation language(s); domain toolchains such as proof assistants, HDLs, CAD scripting languages, and query languages belong in the environment rather than in that list. Difficulty tiers are language-independent — there is no rule requiring Python tasks to be harder than tasks in other languages.

3. **Difficulty tier**
   One of `frontier`, `advanced`, `core`, `base`, written lowercase. The tier is an empirical measurement, not a self-assessment — see **Difficulty Evaluation**. `easy`, `medium`, and `hard` are retired names and fail validation.

4. **Category and subcategory**
   Exactly one `category` and exactly one `subcategory`, Title Case, matching this table exactly:

   | Category | Subcategories |
   |---|---|
   | `Science` | `Biology`, `Chemistry`, `Physics`, `Earth`, `Robotics`, `Math`, `Linguistics` |
   | `Software` | `Algorithms`, `Systems`, `Databases`, `Data engineering`, `Frontend`, `Languages` |
   | `ML` | `Training`, `Inference`, `Evaluation`, `Kernels` |
   | `Operations` | `Finance`, `Logistics`, `Supply chain`, `Claims`, `Compliance`, `Marketing` |
   | `Security` | `Cryptography`, `Reverse engineering`, `Forensics`, `AppSec` |
   | `Hardware` | `CAD`, `RTL` |
   | `Media` | `Music`, `Design` |

   Pick the category describing the domain the task lives in, then the subcategory describing the specific work. The most common tagging mistake is defaulting to `Software` because the task involves writing code — nearly every task does. Ask instead what the agent has to understand to get the task right: a task that debugs a training loop is `ML` / `Training`, not `Software` / `Systems`; a task that parses mass spectra to infer a molecular structure is `Science` / `Chemistry`, not `Software` / `Algorithms`. Reserve `Software` for tasks where software engineering itself is the subject matter. If a task genuinely spans two categories, choose the one whose domain knowledge the agent cannot succeed without.

   `ML` / `Kernels` is authorable without a GPU in two shapes: a CPU-simulated kernel whose numerical output the verifier checks against a reference, or compile-only verification that checks the kernel builds and passes structural checks without executing it on a device.

   The taxonomy pair is not enough for Step 1. Each seed also needs a
   `category_profile.profile_name` from the bundled `TASK_PROPOSAL_RUBRIC.md`
   profile table, plus bug family, coverage role, disclosure boundary, verifier
   risks, and waiver pressure. The category profile is design vocabulary for
   screening; it never substitutes for the taxonomy pair.

5. **Task name**
   A short kebab-case directory name such as `distributed-trace-analysis`.

### Fixed values for this standalone bundle

- `author_name = "anonymous"`
- `author_email = "anonymous"`
- provisional drafting tier: `difficulty = "advanced"`

Treat the provisional tier during ideation as a hypothesis until it is measured against both platform models. If later evidence says the task lands outside the `frontier`/`advanced` band this bundle is generating for, send it back to regeneration or stop rather than relabeling and continuing.

## Task Shape

Terminus 3 has exactly one task shape:

```text
your-task-name/
├── task.toml
├── instruction.md
├── environment/
│   ├── Dockerfile          # or docker-compose.yaml for existing multi-container tasks
│   ├── .dockerignore       # required for non-trivial environments
│   └── data/               # bundled inputs, fixtures, configs
├── solution/
│   └── solve.sh
└── tests/
    ├── Dockerfile          # builds the separate verifier image
    ├── test.sh             # verifier entrypoint
    └── test_outputs.py     # pytest assertions
```

Rules that shape the idea, not just the files:

- `tests/Dockerfile` is required. It builds the verifier image, bakes in the verifier's own pinned dependencies (`pytest`, `pytest-json-ctrf`, and any verifier-only wheels), copies the verifier sources into `/tests`, and creates the landing directory for every declared artifact.
- The verifier runs in **its own container**. It cannot reach the agent's container and it sees **only** the absolute paths listed in the top-level `artifacts` array. An oracle that produces the right result at an undeclared path fails exactly like an empty run.
- Never copy `solution/` or `tests/` into the environment image.
- Do not author `rubrics.txt` or `README.md`. Snorkel generates both at packaging time — the rubric from the platform submission UI, the README from the four explanation fields in `task.toml`. Neither file belongs in the task directory or the submission zip.

### `task.toml`

```toml
artifacts = ["/app/output/report.json"]   # top-level; the only paths the verifier ever sees
name = "your-task-name"

[metadata]
author_name = "anonymous"
author_email = "anonymous"
category = "Software"                     # exactly one, Title Case
subcategory = "Databases"                 # exactly one, valid for that category
tags = ["sqlite", "wal", "recovery"]      # 3-6 descriptive values, no filler
languages = ["python"]
difficulty = "advanced"                   # measured tier, lowercase
expert_time_estimate_hours = 6
difficulty_explanation = "The crux an agent has to get right."
solution_explanation = "How the oracle derives the result."
verification_explanation = "How the verifier decides the task was solved."
relevant_experience = "The background that qualified you to author this task."

[verifier]
timeout_sec = 1800
environment_mode = "separate"             # always; grading happens in an isolated container

[agent]
timeout_sec = 3600                        # 1800 floor, 18000 ceiling; most tasks land 3600-5400

[environment]
network_mode = "public"                   # default; "no-network" only when access would hand over the answer
build_timeout_sec = 900
cpus = 2
memory_mb = 8192
storage_mb = 10240
```

- `artifacts` is top-level. Nested under `[verifier]` it raises no error, the value is silently dropped, and the verifier receives nothing.
- The descriptive fields live under `[metadata]`. A top-level copy reads as present locally and missing upstream.
- The four explanation write-ups are the only place that reasoning is recorded, because the packaged README is assembled from them.
- `[agent].timeout_sec` has a **floor** of 1800 and a ceiling of 18000. The floor is not a target: a task that genuinely finishes in under half an hour is usually not deep enough for this edition.
- Every dependency is baked into the image at build time even when `network_mode = "public"`, and `tests/test.sh` never fetches anything at trial time.
- These keys are retired and must never be written: `version`, `codebase_size`, `number_of_milestones`, `subcategories`, `allow_internet`, `junior_time_estimate_min`, `expert_time_estimate_min`, `task_subtypes`, `custom_docker_compose`.

### Environment image

- Digest-pin every base image with `@sha256:<digest>`, in `environment/Dockerfile` and `tests/Dockerfile` alike. Tags are optional readability; the digest is authoritative. Never use `latest`.
- If the final runtime image is not the canonical one for the task's primary language family, the justification must be a comment in the `Dockerfile` itself. A README section no longer works, because the README is generated at packaging and never reaches CI.
- One apt transaction per stage: `apt-get update && apt-get install -y --no-install-recommends ... && rm -rf /var/lib/apt/lists/*`. No `apt-get upgrade`.
- Do **not** version-pin apt packages. Pinned apt installs are blocked; pin language dependencies instead, with the ecosystem's lockfile (`requirements.txt` with exact versions plus `uv.lock`/`poetry.lock`, `package-lock.json`, `Cargo.lock`, `go.sum`).
- Install `tmux` and `asciinema` explicitly in the environment image. The agent runtime needs both to start a session, and a task with network access can appear to work without them right up until it does not.
- Keep the build context at or below 100 MiB with no single file over 50 MiB, and ship a `.dockerignore` for any non-trivial environment.

## Current Acceptance Gates

Apply these gates while shaping the task:

- Difficulty is empirical. Accuracy is the average pass@1 across 8 runs — 4 per model, over GPT-5.6 and Claude Opus 5 — and the tier follows from it.
- Pass rates above 80% are **not** a rejection reason; that band is the `base` tier. What is rejected is 100% accuracy averaged across both models, because a task every run solves produces no signal. One model going 4/4 is fine as long as the other fails at least once.
- Tiers are language-independent. There is no requirement that Python tasks be harder than others.
- Environment file count is a realism signal, not evidence of hardness. Include the modules, data, configs, and headers the task genuinely needs; do not pad with filler files.
- Tasks must be multi-step: chained commands, intermediate state to handle, and real reasoning along the way. A task solvable in one command or one straight-line burst does not qualify.
- Tasks must be novel. Near-duplicates of prior editions or existing Terminal-Bench repositories are detected with embedding similarity, and reskinning your own earlier task counts as duplication.
- No canary strings in any component — instruction, environment, solution, tests, or metadata.
- The instruction is around two short paragraphs or up to 20 bullets, uses absolute paths, and must be human-written. Prompts are screened automatically for AI-generated text.
- No GPU. The oracle must run within roughly 2 CPU cores, 8 GB memory, and 10 GB storage.
- Prefer single-container tasks. New multi-container tasks are not accepted.
- Avoid FastAPI during ideation unless there is a compelling reason to choose it, and avoid defaulting to Python when another language fits the task more naturally.

### Task shapes this edition removed

- **Milestone tasks are gone.** There is no `steps/` directory, no `[[steps]]`, no `number_of_milestones`, no per-milestone tests or solve scripts, and no grandfathered or in-revision exemption. Do not shape an idea around staged milestones.
- **The `ui_building` subtype is gone.** Frontend work is an ordinary task under category `Software`, subcategory `Frontend`, verified with the ordinary pytest verifier. There is no separate UI test template.
- **The old flat category names are gone.** `software-engineering`, `debugging`, `data-processing`, `system-administration`, and the rest of that list are not values any more, and neither is the `subcategories` array. Choose the taxonomy pair that describes the task's domain.

## No-Collapse Principle

The biggest authoring failure mode is not a weak idea. It is a **strong idea family collapsing into a weak concrete instance**.

Do not judge the task only at the idea stage. Judge it again after the implementation plan becomes concrete.

This bundle explicitly rejects tasks that collapse into:

- disclosed policy-knob transcription
- finite state-table or phase-table repair
- toy SSH / SFTP / jail / permissions hardening checklists
- pre-factored recipe completion such as safe extractors or path-sanitization helpers
- spec-complete "fix broken code" where the instruction gives every algorithm, patch-selecting threshold, internal schema, and implementation formula — making the job a spec-to-code diff regardless of output complexity

Real systems, real daemons, security flavor, and complex output (many JSON fields, many tests, multi-stage pipelines) do not rescue those patterns. Complex output that fans out from a few simple fixes is not hardness.

## Concrete Drafting Rule

When shaping the idea, ask:

- what is the smallest plausible successful patch?
- how many obvious files or helpers are in the editable frontier?
- does the prompt map 1:1 onto those files?
- is the solver mostly filling in a standard recipe or declarative table?
- would a strong model likely solve the task in one pass without much verifier-guided search?
- **what specific facts must the agent discover from the codebase that are NOT in the instruction?** List at least 3. If you cannot, the task is easy.
- **would the instruction need to give exact algorithms, patch-selecting thresholds, internal schemas, or implementation formulas for the verifier to work?** If yes, the agent will just diff the spec against the code — that is always easy. Public output schemas, formulas, types, sizes, and profile constants that the verifier externally tests still belong in `instruction.md`.
- **does correctness span more than one interacting axis?** A single axis with many independent bullets is length. Two axes that constrain each other — performance under determinism, safety under state consistency — is difficulty.

If the answers point toward an easy concrete instance, regenerate or stop before drafting.

### Post-disclosure collapse rule

Hidden requirements are not allowed. If tests assert exact formulas,
invariants, event rules, constants, schemas, or sizes, those requirements must
be visible. Then ask whether disclosure makes the remaining task a direct
formula-to-file repair: each public rule maps to one obvious function or
module, and tests import those modules to assert the same rules. If yes, reject
or redesign instead of rescuing difficulty by hiding the rule.

This applies to every language, and it bites hardest wherever direct
source-level formula repair is cheap for strong models once the contract is
fair.

## Instruction Style Requirement

Every new `instruction.md` should read like a natural human task prompt. It may
be concise paragraphs, a title plus `Requirements`, or another accepted-task
style. The bug-report checklist is for author planning only; public headings
are optional.

The instruction must explicitly say whether source code under
`/app/environment` must be fixed, and must say static/manual generated outputs
are insufficient when the verifier regenerates outputs. It should give a fair
subsystem or directory orientation, but not the exact patch file/function unless
the category profile allows it or a waiver is approved. It must disclose
commands, schemas, invariants, formulas, types, sizes, profile constants, and
argument splits that are externally tested, but must not enumerate a
scenario→field→expected boolean answer table.

Good: "Fix the source under `/app/environment` so the report is regenerated by
the normal pipeline." Bad: "Write the expected JSON to
`/app/output/report.json`."

## Recommended Workflow

1. Run the mandatory pre-Phase-0 idea search from `chatgpt-task-authoring-playbook.md`.
2. Screen the strongest survivor with `TASK_PROPOSAL_RUBRIC.md`.
3. Run the mandatory implementation-collapse audit before committing to an implementation plan.
4. Use `chatgpt-task-authoring-playbook.md` for intake and proposal shaping. Task drafting happens in Cursor, not ChatGPT.

## Recurring Shape Guardrails

The old subtype labels are retired, but the design constraints they carried still apply whenever a task takes one of these shapes:

- **Long-context.** Only claim it when the task truly depends on at least 50k tokens of reading, roughly 50-150 pages, and semantic understanding. If simple parsing, filtering, or keyword search is enough, the task is not long-context.
- **API interaction.** The API source must live in the environment and be mocked locally inside Docker, with no live external service. The agent interacts through the terminal only.
- **Database interaction.** The task should require real interaction with a database engine and not be solvable by reading the raw data files. Flat-file CSV "databases" should be a small minority.
- **Tool-specific.** Specialized tools where models underperform — FFmpeg, ImageMagick, Graphviz, MLFlow, Prefect, QGIS, Blender, and similar — are good material, provided the tool is doing real work rather than decorating the task.
- **Frontend.** An ordinary task under `Software` / `Frontend`, verified with the ordinary pytest verifier.

## Difficulty Evaluation

The recorded tier comes from platform measurement, in two stages with different run counts:

| Stage | Runs | What it decides |
|---|---|---|
| In-platform iteration, while building | 2 per model x 2 models = 4 | Whether the task can go to review |
| Final difficulty, after reviewer acceptance | 4 per model x 2 models = 8 | The tier recorded for the task |

The iteration gate is that **at least one of the 4 runs must fail**. If every run passes, the task produces no signal and cannot proceed to review; fix that by making the task harder, not by narrowing a threshold. The tier visible while iterating is provisional — a task can shift tiers once the full 8-run measurement lands.

| Tier | Accuracy |
|---|---|
| `frontier` | < 20% |
| `advanced` | 20% – < 50% |
| `core` | 50% – < 80% |
| `base` | 80% – < 100% |

Failures caused by unclear instructions, environment defects, or flaky tests are bugs, not difficulty. Fix them and re-measure; only failures that come from the actual challenge of the task should count toward the tier.

Local evidence for this repo is separate and mechanical: strict spec gates, static
checks, actionability/no-hidden-contract/obfuscation lints, collapse,
Harbor oracle/NOP, repeated oracle, first-look review, package validation, and
strict approval. Those gates say whether the task is well built; they do not set
the tier. Do not claim empirical model-stumping evidence unless it was
separately run outside this repo workflow and clearly labeled as non-required
context.

The standalone bundle may still draft the provisional tier as `advanced` during
ideation. That label is a hypothesis until the platform trials and reviewer
judgment support it.
