# **Terminus Unified Ground Truth Specification**

> **Precedence:** the authoritative policy files are `.cursor/rules/` (task-creation.mdc, review-and-submit.mdc, difficulty-calibration.mdc), the canonical CLI reference is `commands.md`, and anything mechanical is settled by `scripts/run_static_checks.py` and `default-template/`. If this document conflicts with them, they win.

This document is the consolidated per-file reference for Terminus 3 task creation, evaluation, and submission. Terminus 3 has exactly one task shape. The verifier runs in its own container, built from `tests/Dockerfile`, which the agent cannot reach; it sees only the paths declared in the top-level `artifacts` array of `task.toml`.

## **Table of Contents**

1. [submission.zip](#1-submissionzip)
2. [instruction.md](#2-instructionmd)
3. [task.toml](#3-tasktoml)
4. [environment/Dockerfile](#4-environmentdockerfile)
5. [environment/docker-compose.yaml](#5-environmentdocker-composeyaml)
6. [environment/\[additional build files and task assets\]](#6-environmentadditional-build-files-and-task-assets)
7. [solution/solve.sh](#7-solutionsolvesh)
8. [solution/ helper scripts (and legacy solution.yaml)](#8-solution-helper-scripts-and-legacy-solutionyaml)
9. [tests/Dockerfile](#9-testsdockerfile)
10. [tests/test.sh](#10-teststestsh)
11. [tests/test_outputs.py](#11-teststest_outputspy)
12. [Logs and Rewards (ctrf.json, reward.txt)](#12-logs-and-rewards-ctrfjson-rewardtxt)
13. [Forbidden & Optional Root Artifacts (rubrics.txt, README.md, jobs/, data/)](#13-forbidden--optional-root-artifacts-rubricstxt-readmemd-jobs-data)
14. [Platform, Submission, and Workflow Rules](#14-platform-submission-and-workflow-rules)

## **1. submission.zip**

**CRITICAL RULE:** The uploaded ZIP **MUST** contain the task files directly at the archive root.

**Rule:** The submission archive MUST contain exactly one task's files at the ZIP root, not an extra enclosing directory layer.

**Consequence of Violation:** Platform upload UI will reject the archive, or reviewers will block it with a structural failure.

**Rule:** The author MUST start from the Terminus 3 skeleton — the official skeleton, or this repo's `default-template/`, which already carries the separate-verifier layout. There is exactly one skeleton in this edition.

**Consequence of Violation:** Missing required files (most often `tests/Dockerfile`), wrong verifier patterns, and structural CI failures.

**Rule:** The archive MUST contain, at the archive root: `instruction.md`, `task.toml`, `environment/` with `Dockerfile` (or `docker-compose.yaml`), `solution/solve.sh`, and `tests/` with `Dockerfile`, `test.sh`, and `test_outputs.py`.

**Consequence of Violation:** `scripts/validate_submission_zip.py` rejects the archive; the platform reports a required-files failure.

**Rule:** The build context MUST stay within the documented size limits: `environment/` at or below 100 MiB in total, with no single file over 50 MiB.

**Consequence of Violation:** `scripts/run_static_checks.py --only build_context` failure and platform size rejection.

**Rule:** The task folder name MUST be kebab-case (lowercase letters, digits, hyphens) and MUST NOT exceed 6 hyphen-separated tokens — e.g. `configure-nginx-ssl`.

**Consequence of Violation:** `--only task_name` failure. Long slugs are unwieldy in CLI output, logs, and artifact paths.

**Rule:** The archive MUST NOT copy work from the Terminal-Bench 2.1 / 3.0 repositories, prior Terminus editions, or open-source tasks without substantial non-trivial differentiation. Novelty is checked automatically with embedding similarity.

**Consequence of Violation:** High-severity uniqueness failure during review.

**Rule:** Templated tasks are NOT allowed. Each submission MUST be substantively different from the author's prior work — not the same structure, solution approach, or test patterns with keyword/instruction swaps or plug-and-play surface changes.

**Consequence of Violation:** High-severity uniqueness failure during review via similarity search; templated reskins may constitute removal from Project Terminus.

## **2. instruction.md**

**CRITICAL RULE:** Every behavior enforced by the verifier MUST be explicitly stated or clearly implied by schemas in instruction.md.

**Rule:** instruction.md MUST exist at the task root. This exact filename is canonical; do not rename it to instructions.md.

**Consequence of Violation:** High-severity structural failure; task is invalid.

**Rule:** instruction.md MUST begin with a clear intro and MUST stay concise, human-authored, and authentic. Aim for around 2 short paragraphs or a list of up to 20 bullets; genuinely complex tasks may need more room.

**Consequence of Violation:** High-severity review failure (Task Instruction is concise / authentic).

**Rule:** instruction.md and solution/solve.sh MUST be written by the author. Both are screened for AI-generated text and fail above a probability threshold.

**Consequence of Violation:** Automated human-authored-content failure (`ci_checks/check-ai-detection.py` locally).

**Rule:** The task MUST be well specified, interesting, and give the agent the **what**, not the **how**. It MUST NOT provide hints, solution guidance, rubrics, or step-by-step instructions.

**Consequence of Violation:** High-severity prompt-quality or ambiguity rejection.

**Rule:** instruction.md MUST NOT include large design tables, heavy markdown, emojis, or generic LLM-style prose.

**Consequence of Violation:** Automated instruction-quality failure or reviewer rejection.

**Rule:** Every output file, modified file, or strict schema the verifier checks MUST be explicitly named.

**Consequence of Violation:** Automated behavior-description failures (behavior_in_task_description, file_reference_mentioned, structured_data_schema).

**Rule:** Paths shown to the agent MUST use in-container absolute paths (e.g., /app/...). Local-workstation absolute paths and relative paths (e.g., config/settings.json) are forbidden.

**Consequence of Violation:** Absolute-path check failure (`--only absolute_paths`).

**Rule:** It MUST NOT mention specific tools (e.g., "Use vim") unless the verifier can actually prove that specific tool was used.

**Consequence of Violation:** Reviewer rejection for unverifiable tool requirements.

**Rule:** instruction.md MUST NOT include the task name or canary strings. Canary strings are banned in every component — instruction, environment, solution, tests, and metadata — because this is a training dataset.

**Consequence of Violation:** Medium-severity review issue or canary static-check failure (`--only canary`).

**Rule:** instruction.md SHOULD avoid the literal word "milestone" and similar staging vocabulary. That task shape no longer exists, so the wording reads as a leftover from a ported Edition 2 task; use "step", "stage", or "phase" instead.

**Consequence of Violation:** Non-blocking WARN from `--only instruction`.

## **3. task.toml**

**CRITICAL RULE:** The manifest is task.toml. task.yaml is obsolete and MUST NOT be used, and the Edition 2 `version = "2.0"` schema key is retired.

**Rule:** task.toml MUST exist at the task root and MUST follow the Terminus 3 shape: a top-level `artifacts` array, a top-level or `[metadata]` `name`, and `[metadata]`, `[verifier]`, `[agent]`, and `[environment]` tables.

```toml
artifacts = ["/app/output/report.json"]   # top-level; the only paths the verifier ever sees
name = "your-task-name"

[metadata]
author_name = "anonymous"
author_email = "anonymous"
category = "Software"                     # exactly one, Title Case
subcategory = "Databases"                 # exactly one, valid for that category
tags = ["sqlite", "wal", "recovery", "storage-engine"]   # 3-6 values
languages = ["python"]
difficulty = "advanced"                   # measured tier, lowercase
expert_time_estimate_hours = 6
difficulty_explanation = "The core crux an agent has to get right."
solution_explanation = "How the oracle solves it."
verification_explanation = "How the verifier decides the task was solved."
relevant_experience = "The background that qualified you to author this task."

[verifier]
timeout_sec = 1800
environment_mode = "separate"

[agent]
timeout_sec = 3600

[environment]
network_mode = "public"
build_timeout_sec = 900
cpus = 2
memory_mb = 8192
storage_mb = 10240
```

**Consequence of Violation:** `--only task_toml` failure; upstream required-fields failure.

**Rule:** The descriptive fields (author_name, author_email, category, subcategory, tags, languages, difficulty, expert_time_estimate_hours, difficulty_explanation, solution_explanation, verification_explanation, relevant_experience) MUST live under `[metadata]`. A top-level copy is silently ignored by the platform structure check.

**Consequence of Violation:** Metadata reads as present locally and missing upstream; `--only task_toml` failure.

**Rule:** `artifacts` MUST be a top-level array of absolute container paths, and MUST NOT be nested under `[verifier]`. Nesting raises no error upstream — the value is silently dropped and the verifier receives nothing. Reserved paths (/tests, /solution, /oracle, /logs) MUST NOT be declared.

**Consequence of Violation:** The verifier receives no artifacts and every assertion fails for a reason that looks like a broken test.

**Rule:** Every parent directory of a declared artifact MUST be created in `tests/Dockerfile` (`RUN mkdir -p /app/output`). Harbor's artifact upload fails when the landing directory is missing.

**Consequence of Violation:** Verifier failure that presents as a test bug; check this first.

**Rule:** category MUST be exactly one value and subcategory exactly one value, both Title Case, matching the taxonomy exactly:

| Category | Subcategories |
|---|---|
| `Science` | `Biology`, `Chemistry`, `Physics`, `Earth`, `Robotics`, `Math`, `Linguistics` |
| `Software` | `Algorithms`, `Systems`, `Databases`, `Data engineering`, `Frontend`, `Languages` |
| `ML` | `Training`, `Inference`, `Evaluation`, `Kernels` |
| `Operations` | `Finance`, `Logistics`, `Supply chain`, `Claims`, `Compliance`, `Marketing` |
| `Security` | `Cryptography`, `Reverse engineering`, `Forensics`, `AppSec` |
| `Hardware` | `CAD`, `RTL` |
| `Media` | `Music`, `Design` |

Pick the category describing the domain the task lives in, then the subcategory describing the specific work. The common mistake is defaulting to `Software` because the task involves writing code — nearly every task does. A task that debugs a training loop is `ML` / `Training`; a task that parses mass spectra to infer a molecular structure is `Science` / `Chemistry`. Reserve `Software` for tasks where software engineering itself is the subject matter. Front-end work is `Software` / `Frontend` and is built and verified like any other task. `ML` / `Kernels` is authorable without a GPU, as a CPU-simulated kernel checked against a reference or as compile-only verification.

**Consequence of Violation:** `--only task_toml` failure. The Edition 2 flat names (`software-engineering`, `debugging`, `data-processing`, and the rest of that nine-name list) and the `subcategories` array are retired and are not valid values.

**Rule:** tags MUST contain 3-6 descriptive keywords — tools, libraries, techniques, or subtopics. languages MUST record the primary implementation language(s); domain toolchains (proof assistants, HDLs, query languages) live in the environment instead.

**Consequence of Violation:** Metadata validation failure or a warning on off-list languages.

**Rule:** difficulty MUST be a measured Terminus 3 tier: `frontier` (< 20%), `advanced` (20% – < 50%), `core` (50% – < 80%), or `base` (80% – < 100%). Accuracy is the average pass@1 across 8 runs — 4 per model over GPT-5.6 and Claude Opus 5. `easy` / `medium` / `hard` are retired Edition 2 names. Tiers are language-independent: Python tasks carry whatever tier they measure at, like any other language.

**Consequence of Violation:** `--only task_toml` failure and rejection for invalid benchmarking.

**Rule:** `[verifier].environment_mode` MUST be `"separate"`, and `[verifier].timeout_sec` MUST be between 120 and 18000. Raise it to at least `[environment].build_timeout_sec` when `tests/` invokes a build step.

**Consequence of Violation:** `--only task_toml` / `--only timeout_coherence` failure.

**Rule:** `[agent].timeout_sec` MUST be at least 1800 (the floor, not the cap) and at most 18000. Most tasks land in the 3600-5400 range.

**Consequence of Violation:** `--only task_toml` failure; reviewer criterion on the low end, hard CI error above the ceiling.

**Rule:** `[environment]` MUST declare `network_mode`, `build_timeout_sec`, `cpus`, `memory_mb`, and `storage_mb`. `network_mode = "public"` is the default; use `"no-network"` only when the task does not make sense to complete with internet access. Tasks MUST NOT require a GPU (`gpus > 0` fails).

**Consequence of Violation:** `--only task_toml` failure.

**Rule:** The four explanation fields MUST be written properly. Snorkel assembles the packaged `README.md` from `difficulty_explanation`, `solution_explanation`, `verification_explanation`, and `relevant_experience`, so they are the only place this reasoning is recorded.

**Consequence of Violation:** Short stubs draw a WARN; the packaged README carries no usable rationale.

**Rule:** Retired keys MUST NOT appear: `version`, `codebase_size`, `number_of_milestones`, `subcategories`, `allow_internet`, `junior_time_estimate_min`, `expert_time_estimate_min`, `task_subtypes`, `custom_docker_compose`. `expert_time_estimate_min` becomes `expert_time_estimate_hours`; the others have no replacement.

**Consequence of Violation:** `--only task_toml` failure (a top-level `version` is a WARN). Their presence signals a manifest carried over from Edition 2 without migration.

**Rule:** If using `environment/docker-compose.yaml` with more than one service, `[metadata].is_multi_container = true` MUST be set. The harness discovers the compose file on its own; nothing in task.toml points at it, and the field is omitted for single-container tasks.

**Consequence of Violation:** High-severity review failure or `--only task_toml` failure.

## **4. environment/Dockerfile**

**CRITICAL RULE:** The environment must be reproducible and self-contained without leaking answers or requiring web fetches at runtime.

**Rule:** environment/Dockerfile MUST exist inside the environment/ directory and MUST set a real working directory (e.g., WORKDIR /app).

**Consequence of Violation:** Verifier exit failure (Error: No working directory set).

**Rule:** Base images MUST be pinned by digest (`@sha256:` on every `FROM` except `scratch`); never use `:latest`, and never pin a CPU architecture with `FROM --platform=...`. **Separately**, the final runtime `FROM` digest MUST match a canonical base image from `docs/DOCKERFILE_AND_IMAGE_BEST_PRACTICES.md`. Builder stages may use toolchain images. A non-canonical final runtime image requires a credible justification **in a Dockerfile comment** (`# Non-canonical base image: …`) plus selecting **No** on the submission UI canonical-base-image field — a README section no longer works, because Snorkel generates `README.md` at packaging and an authored copy never reaches the check. `scripts/check_canonical_base_image.py` enforces this locally.

**Consequence of Violation:** Pinned-dependency and canonical-base-image failures; Agent Review critical findings.

**Rule:** Language dependencies MUST be pinned to exact versions and paired with a lockfile. apt packages MUST NOT be version-pinned (`pkg=version`) — this is the opposite of the pip rule, and CI blocks pinned apt installs. Use one apt transaction per stage (a single `apt-get update && apt-get install -y --no-install-recommends … && rm -rf /var/lib/apt/lists/*`), never `apt-get upgrade`, and keep build tools out of the final runtime image unless required.

**Consequence of Violation:** `--only dockerfile` failure on either side of the pinning rule; Dockerfile-hygiene findings for the rest.

**Rule:** `tmux` and `asciinema` MUST be installed explicitly, regardless of `network_mode`. The agent runtime needs both to start a session.

**Consequence of Violation:** `--only dockerfile` failure; at runtime, "Failed to start tmux session" and a verifier_did_not_run result.

**Rule:** The Dockerfile MUST NOT copy solution/, tests/, or oracle answers into the image, nor create reserved paths (/tests, /solution, /oracle, /logs).

**Consequence of Violation:** Dockerfile-reference and tests_or_solution_in_image failures, plus anti-cheating rejection.

**Rule:** Verifier-only dependencies MUST NOT be installed here. The pytest stack and any other verifier-only tooling belong in `tests/Dockerfile` — not in this image and not in `tests/test.sh`.

**Consequence of Violation:** `--only dockerfile` failure for verifier-only tools in the agent image.

**Rule:** Build context MUST NOT escape the environment/ directory (e.g., `context: ../` is banned), and every `COPY`/`ADD` source MUST resolve inside it.

**Consequence of Violation:** Environment scope rejection; a dead reference breaks the image build before any test runs.

**Rule:** The Dockerfile MUST NOT use privileged mode (--privileged, SYS_ADMIN, mounting docker.sock).

**Consequence of Violation:** High-severity security rejection.

**Rule:** Non-trivial environments SHOULD ship an `environment/.dockerignore` excluding caches, `.git`, virtualenvs, build outputs, credentials, `.env`, logs, `solution/`, and `tests/`. It is part of the deliverable and stays in the packaged archive.

**Consequence of Violation:** `--only build_context` warning and a needlessly large build context.

## **5. environment/docker-compose.yaml**

**CRITICAL RULE:** New multi-container tasks are no longer accepted in this repo. Single-container is the default; the rules in this section apply only to tasks that already ship a compose file.

**Rule:** environment/docker-compose.yaml MAY be used only when a single container is genuinely insufficient. When an idea would naturally land as multi-container, redesign it or reject it at idea validation rather than carrying it forward.

**Consequence of Violation:** Reviewer pushback for unjustified complexity; a net-new multi-container task is not accepted.

**Rule:** Every `image:` MUST be digest-pinned, the same rule as `FROM`.

**Consequence of Violation:** `--only compose` failure and reproducibility rejection.

**Rule:** Compose volume mounts MUST NOT conflict with Harbor-reserved mounts (/logs/verifier/, /logs/agent/, /tests/, /solution/), and MUST NOT use host bind mounts as volume sources. Containers that need to share state must do so another way.

**Consequence of Violation:** High-severity harness collision failure.

## **6. environment/\[additional build files and task assets\]**

**Rule:** Assets needed at runtime SHOULD live inside environment/, NOT at the root level (data/). Data files belong in `environment/data/`.

**Consequence of Violation:** Cleanup feedback or broken build context.

**Rule:** Additional assets MUST NOT fetch internet data at runtime. Every dependency is baked in at build time; `network_mode = "public"` exists for the task's own work, not as a substitute for a complete image. Repositories MUST be pinned to a specific commit if cloned.

**Consequence of Violation:** No-web-data failure and reproducibility rejection.

**Rule:** AI-specific filenames are banned anywhere in the archive: `CLAUDE.md`, `skills.md`, `AGENTS.md`, `.cursor/`, `.aider/`, `.continue/`, `.claude/`, and similar. Use realistic engineering filenames instead (`README.md`, `architecture.md`, API docs, schemas, sample configs), and vary them across tasks.

**Consequence of Violation:** `scripts/validate_submission_zip.py` rejects the archive; the names read as AI scaffolding leaking into the task.

**Rule:** Environment files MUST NOT contain hidden instructions to the agent — no step-by-step walkthroughs, solution hints, `HINT:` / `STEP N:` markers, prescriptive TODOs, or solver-direction phrasing ("Claude should…", "to solve this task…", "the fix is to…"). Litmus test: an environment file should look like something a human engineer would plausibly find in a real repo, not a guide written for the agent.

**Consequence of Violation:** `--only environment_hidden_instructions` failure.

**Rule (LICENSE files):** For minimal and small codebases, omit by default. For large codebases, prefer the repos provided by the project (already permission-cleared); if sourcing your own, the repo MUST be licensed under MIT, Apache 2.0, or BSD — anything else is rejected.

**Consequence of Violation:** Licensing rejection.

## **7. solution/solve.sh**

**CRITICAL RULE:** The oracle is the solvability proof. It must cleanly and deterministically solve the exact prompt.

**Rule:** solution/solve.sh MUST exist, MUST solve the *entire* instruction, and MUST be perfectly deterministic.

**Consequence of Violation:** Oracle Agent flakiness or broken task rejection.

**Rule:** It MUST perform real work, not simply hardcode the final answer or copy it from test expectations.

**Consequence of Violation:** hardcoded_solution failure.

**Rule:** It MUST NOT require interactive hangs (e.g., vim without scripted inputs) and MUST NOT fetch web dependencies.

**Consequence of Violation:** Oracle timeout and no-web-data rejection.

**Rule:** It SHOULD fail-fast (`set -e` or `set -euo pipefail`) and MUST apply the exact same test logic used for the agent. No conditional testing based on evaluation mode.

**Consequence of Violation:** Silent oracle failures or oracle/agent parity rejection.

## **8. solution/ helper scripts (and legacy solution.yaml)**

**Rule:** Helper scripts (`solve.py` and friends) MAY live in solution/ and be called from solve.sh. solve.sh remains the REQUIRED entrypoint.

**Consequence of Violation:** Structural failure if solve.sh is missing.

**Rule:** solution/solution.yaml is a legacy, optional format for interactive terminal tools (e.g., keystroke tracing). It does not replace solve.sh and is not part of the Terminus 3 skeleton.

**Consequence of Violation:** Structural failure if the task ships solution.yaml instead of solve.sh.

## **9. tests/Dockerfile**

**CRITICAL RULE:** tests/Dockerfile is REQUIRED. It builds the separate verifier image, which runs in its own container the agent cannot reach and which sees ONLY the paths declared in the top-level `artifacts` array.

**Rule:** tests/Dockerfile MUST exist, and every `FROM` in it MUST be digest-pinned and on a sanctioned base image, exactly as in environment/Dockerfile.

**Consequence of Violation:** Missing-file rejection; unpinned bases are reported as a warning today but should be treated as required.

**Rule:** The image MUST own `/tests` by copying its own build context (`COPY . /tests/`). Separate-mode verifiers receive no upload of tests/.

**Consequence of Violation:** `--only task_structure` failure; at runtime the verifier has no test sources to run.

**Rule:** Every verifier dependency MUST be baked in and exact-pinned — `pytest`, `pytest-json-ctrf`, and anything else the assertions need. Nothing may be installed or downloaded at trial time.

**Consequence of Violation:** `--only task_structure` failure on unpinned installs; verifier-tooling and trial-time-network failures upstream.

**Rule:** The image MUST create the landing directory for every declared artifact (`RUN mkdir -p /app/output`).

**Consequence of Violation:** Harbor's artifact upload fails and the verifier reports what looks like a broken test.

```dockerfile
FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

# Every verifier dependency is pinned and baked in; nothing is installed at trial time.
RUN pip install --no-cache-dir pytest==8.4.1 pytest-json-ctrf==0.3.5

# Separate-mode verifiers receive no upload of tests/, so the image must own /tests.
# The build context is this tests/ directory.
COPY . /tests/

# Landing directories for every path declared in the top-level `artifacts` array.
RUN mkdir -p /app
```

## **10. tests/test.sh**

**CRITICAL RULE:** The verifier entrypoint runs the pytest suite and ALWAYS emits a reward artifact on both success and failure. It installs nothing.

**Rule:** tests/test.sh MUST exist. `default-template/tests/test.sh` is the source of truth; copy it and preserve command order, section comments, control flow, the `$PWD` guard, and the reward block.

**Consequence of Violation:** Missing-file rejection or `--only test_sh` failure for drifting from the maintained template.

**Rule:** The script MUST use `set -uo pipefail` and MUST NOT enable or toggle errexit (`set -e`, `set -euo pipefail`, `set -o errexit`, `set +e`). With `-e` a failing pytest aborts the script before the reward file is written and the trial records no result at all.

**Consequence of Violation:** `--only test_sh` failure; at runtime, a legitimate failure is scored as an error.

**Rule:** The script MUST run from a valid working directory. If `$PWD` resolves to `/`, treat that as a task-environment misconfiguration, write a failure reward, and exit 0.

**Consequence of Violation:** Verifier exit failure ("No working directory set").

**Rule:** It MUST always produce /logs/verifier/reward.txt. Failed runs MUST still emit a failure reward rather than exiting before the artifact is written. reward.json is not a supported reward sink.

**Consequence of Violation:** RewardNotFoundError / RewardFileNotFound.

**Rule:** pytest MUST be invoked as `python -m pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA`, with the reward block immediately after — `rc=$?` on the line directly before `if [ "$rc" -eq 0 ]`, no blank lines or comments in between (the platform also accepts `if [ $? -eq 0 ]` immediately after the pytest line).

**Consequence of Violation:** `--only test_sh` failure; the structured CTRF report is enforced separately.

**Rule:** test.sh MUST NOT install or download anything (`apt-get`, `curl`, `wget`, `uv`, `uvx`, `pip install`, `npm install`, `git clone`), MUST NOT add pre-pytest commands beyond the `$PWD` guard and `mkdir -p /logs/verifier`, and MUST NOT delegate to another test framework (`go test`, `npm test`, `jest`, `vitest`, `cargo test`). Every verifier dependency belongs in tests/Dockerfile; drive other toolchains from test_outputs.py via subprocess.

**Consequence of Violation:** `--only test_sh` failure; upstream verifier-tooling and trial-time-network failures.

**Rule:** Oracle and agent runs MUST use identical test logic. No conditional testing based on evaluation mode.

**Consequence of Violation:** Identical testing parity failure.

## **11. tests/test_outputs.py**

**CRITICAL RULE:** tests/test_outputs.py must verify task completion by checking observable behavior, not hidden implementation details.

**Rule:** tests/test_outputs.py MUST exist for every task, and the verifier MUST be Python pytest regardless of the task's implementation language.

**Consequence of Violation:** Structural rejection.

**Rule:** Tests MUST assert against the final state of the environment as delivered through the declared artifacts. The verifier cannot read the agent's filesystem freely — it sees only what `artifacts` lists.

**Consequence of Violation:** Assertions that reference undeclared paths fail regardless of whether the agent solved the task.

**Rule:** Tests MUST run the task and inspect its outputs, APIs, database state, or CLI behavior as appropriate. They MUST NOT parse source code or grep for implementation patterns inside /app/... files.

**Consequence of Violation:** Behavior-testing rejection for testing implementation instead of outcomes.

**Rule:** Every test function MUST have an informative docstring explaining the behavior it checks. This is validated automatically.

**Consequence of Violation:** Automated failure (informative_test_docstrings).

**Rule:** Every requirement in instruction.md MUST have a corresponding test, and every tested behavior MUST appear in instruction.md.

**Consequence of Violation:** Automated failures (behavior_in_tests, behavior_in_task_description).

**Rule:** Tests SHOULD cover edge cases and boundary conditions, not just the happy path.

**Consequence of Violation:** Reviewer feedback or rejection for under-specified verification.

**Rule:** When checking outputs, prefer structured or property-based assertions—schemas, headers, counts, ranges, status codes, database rows, or key content—over brittle full-string equality. Exact string matching is allowed only when the task explicitly requires exact wording.

**Consequence of Violation:** Brittle-test rejection.

**Rule:** Tests MUST include anti-cheating measures and MUST NOT hardcode a specific random value, use latency/hardware thresholds, or rely on execution order/shared global state. They MUST NOT contain a callable end-to-end solver that maps task inputs to the complete expected artifact — that belongs in solution/ — though running the agent's own program, golden fixtures, and spec-derived invariants are all legitimate.

**Consequence of Violation:** Automated anti-cheating or test-quality failure; reference-implementation leakage.

**Rule:** The test module itself MUST pass ruff/lint validation.

**Consequence of Violation:** ruff failure.

## **12. Logs and Rewards (ctrf.json, reward.txt)**

**Rule:** The verifier MUST emit /logs/verifier/reward.txt (`1` pass, `0` fail), using the reward block from `default-template/tests/test.sh` verbatim. Harbor grades from the reward file, not from the script's exit status.

**Rule:** The verifier MUST emit /logs/verifier/ctrf.json via the pytest `--ctrf` flag. The structured report is enforced by the `ctrf_reporting` check.

## **13. Forbidden & Optional Root Artifacts (rubrics.txt, README.md, jobs/, data/)**

**CRITICAL RULE:** Rubrics and the task README are generated by Snorkel at packaging time. Neither is authored, and neither ships in the ZIP.

**Rule (rubrics.txt / rubric.txt):** A rubric file MUST NOT be included in the task directory or the ZIP. The rubric is generated and edited in the platform submission UI, and Snorkel adds the file during packaging.

**Consequence of Violation:** `--only task_structure` failure before packaging; the zip validator rejects the archive; an author copy makes the packaged task disagree with the platform.

**Rule (README.md):** A README MUST NOT be authored at the task root. Snorkel assembles it at packaging from the four `[metadata]` explanation fields plus category and subcategory. Write the reasoning into those fields; there is no second write-up to do.

**Consequence of Violation:** `--only task_structure` failure and archive-root rejection. A README section also no longer satisfies the non-canonical base-image justification — that must be a Dockerfile comment.

**Rule (jobs/, data/):** These SHOULD NOT be included at the root level. Run logs must be purged. Environment data must go in environment/.

**Consequence of Violation:** Clutter finding or repo-local warning.

**Rule (repo-local authoring files):** `output_contract.toml`, `quality_check_adjudication.json`, `construction_manifest.json`, `waivers.json`, `.step2b-checksum`, and `.step2b-metrics.jsonl` live at the task root for repo tooling but MUST NOT appear at the archive root. `scripts/package_task.py` excludes them for you.

**Consequence of Violation:** `scripts/validate_submission_zip.py` rejects the archive.

## **14. Platform, Submission, and Workflow Rules**

### **A. Task-Level Acceptance Gates**

* **One task shape:** task.toml, instruction.md, environment/, solution/solve.sh, and tests/{Dockerfile, test.sh, test_outputs.py}. Milestone tasks were removed from the edition — no `steps/` directory, no `[[steps]]`, no `number_of_milestones`, no per-step test or solve files — and there is no grandfathered path for one. The `ui_building` subtype is gone as well.
* **Multi-step & Terminal-driven:** Tasks MUST require chaining commands with intermediate state and real reasoning — error recovery, branching, or reacting to what the previous step produced. "At least 5 agent steps" is a heuristic for ruling out trivially short tasks, not a number anyone counts.
* **Standalone:** MUST run to completion without human input. All parameters arrive via files, flags, or environment variables.
* **Runtime:** `[agent].timeout_sec` is a floor of 1800s, not a target; most tasks should land in the 60-90 minute range, with a ceiling of 18000s.
* **Unique:** MUST be distinct from Terminal-Bench 2.1 / 3.0, prior Terminus editions, and open-source data. MUST NOT be a templated reskin of the author's prior submissions.
* **Compute:** No GPU; ~2 CPU cores, ~8 GB memory, ~10 GB storage.

### **B. Difficulty, Pass Rate, and Evaluation Rules**

* **Oracle MUST pass; NOP MUST fail.**
* **Empirical difficulty:** accuracy is the average pass@1 across 8 runs — 4 per model over GPT-5.6 and Claude Opus 5 — not a best-model or worst-model figure. Tiers: `frontier` < 20%, `advanced` 20% – < 50%, `core` 50% – < 80%, `base` 80% – < 100%.
* **Two measurement stages:** while iterating, the platform runs 4 trials (2 per model) and at least one MUST fail for the task to reach review; the full 8-run measurement that fixes the recorded tier runs only after a reviewer accepts. The tier seen while building is provisional.
* **High pass rates are not a rejection reason.** Above 80% is the `base` tier. The only unacceptable result is 100% averaged across both models — one model going 4/4 is fine as long as the other fails at least once.
* **Failures must come from the task.** Failures caused by unclear instructions, environment defects, or flaky tests are bugs, not difficulty — fix them and re-measure.
* **Trial analysis flags:** `task_specification` and `reward_hacking` mean the task must change; `difficulty_crux`, `near_miss`, `refusals`, and `low_timeout` need an answer before submission.
* **Repo-local evaluation:** external model attempts are not part of this repo's required approval workflow. Do not claim empirical model-stumping evidence unless it was separately run and clearly labeled as non-required context.

### **C. Diversity and Dataset-Balance Rules**

* **Target suite shares by tier:** Frontier 20-30%, Advanced 25-35%, Core 30-40%, Base 5-15%. These describe the shape of the whole suite, not a personal quota; Frontier and Advanced are the scarcest and most valuable.
* **Languages:** the dataset targets Python, C, C++, JavaScript, TypeScript, Java, Go, Rust, and C#. Multi-language tasks are preferred. Domain-specific toolchains are welcome even when they are not on the list.
* **Task shapes:** the Edition 2 `subcategories` labels are retired, but their design constraints still apply when a task takes one of those shapes — long-context material must genuinely require semantic understanding (~50k tokens and up, not solvable by keyword search); API-interaction tasks must mock the API locally inside Docker with no external web access; database tasks must require the engine rather than reading raw data files.
* **No new multi-container tasks.** Avoid FastAPI.

### **D. Canonical Local Workflow and CLI Commands**

```bash
# New task skeleton.
cp -R default-template tasks/<task-name>

# Repo-local static checks (terminus_3 is the only supported ruleset, and the default).
python3 scripts/run_static_checks.py --task-dir tasks/<task-name> --version terminus_3

# Checksum-bearing preflight.
./scripts/check-task.sh --strict --report-dir /tmp/tb3-gates tasks/<task-name>

# Oracle / NOP evidence, then the 10x oracle stress.
python3 scripts/harbor_gate.py tasks/<task-name> --oracle --nop
python3 scripts/harbor_gate.py tasks/<task-name> --oracle-repeat 10

# Interactive debug (shell into the container).
harbor tasks start-env -p "tasks/<task-name>" -e docker -a -i

# Package and approve.
python3 scripts/package_task.py tasks/<task-name> --out Task_Ready_To_Submit/<task-name>.zip --validate
python3 scripts/approve_task.py --strict --task-dir tasks/<task-name> \
    --zip Task_Ready_To_Submit/<task-name>.zip --skip-verifier-health
```

Upstream-side checks and the optional difficulty probes:

```bash
stb harbor check harbor_tasks/<task_name>
stb harbor run -m @openai/gpt-5.6 -p tasks/<task-name> -k 4
stb harbor run -m @anthropic/claude-opus-5 -p tasks/<task-name> -k 4
```

See `commands.md` at the repo root for the full, up-to-date CLI reference, including the gate flags `scripts/approve_task.py --strict` requires.

### **E. Automated Checks (CI, Behavior Validation, and Agent Review)**

* **Manifest & metadata:** required fields present; `[verifier].environment_mode = "separate"` with a top-level `artifacts` array; the 18000s timeout ceiling; the task folder name length cap.
* **Instructions:** absolute paths; referenced files described in instruction.md; human-authored content screening on instruction.md and solve.sh.
* **Environment & Dockerfile:** pinned pip installs; **unpinned** apt installs; no `FROM --platform=`; no bare `nproc`; Dockerfile references resolve; Dockerfile hygiene warnings; no host bind mounts in compose.
* **Verifier & tests:** tests/ and solution/ absent from the agent image; verifier tooling baked into tests/Dockerfile; pinned test tooling; `ctrf_reporting`; digest-pinned verifier base (warning); no trial-time network fetches; test.sh sanity.
* **LLMaJ checks:** behavior_in_task_description, behavior_in_tests, informative_test_docstrings, anti_cheating_measures, structured_data_schema, hardcoded_solution, file_reference_mentioned. Run them with `stb harbor check`.
* **ruff** on verifier files and on `environment/` Python.
* **Agent Review:** an automated static review that flags safety and structure issues (e.g., latency tests, conditional oracle logic, reserved-directory creation). Non-blocking, but worth reading.
* **Repo-local wrappers:** the entrypoints in `ci_checks/` delegate to `scripts/run_static_checks.py`, which is the source of truth for per-task semantics.

### **F. Submission UI, CI, Rubric, and Reviewer Workflow**

* **Initial Submission (CI pass):** upload with the **rubrics checkbox CHECKED** and **Send to reviewer UNCHECKED**. This runs CI and generates the rubric draft without burning a review cycle.
* **Iteration:** read the CI results, fix what they flag, edit the generated rubric in the platform textbox, and re-upload a corrected zip if the fixes touched task files. Keep Send to reviewer unchecked while iterating.
* **Rubric Generation:** rubrics must be single lines, start with `Agent`, and end with a comma and score (e.g., `Agent creates file, +2`). Allowed scores: ±1, ±2, ±3, ±5 (±4 is banned), written with an ASCII hyphen. Positive criteria total 10-40 points, with at least 3 distinct negative criteria. Grade the *trace*, not the verifier/test logic.
* **Final Submission:** once CI is clean and the rubric is edited, **UNCHECK the rubrics checkbox** (so you don't overwrite your edits) and **CHECK Send to reviewer**. Any significant change to the task requires updating the rubric to match.

### **G. After-Submission, Review, Revision, and Disputes**

* **Timeline:** automated checks are immediate, peer review assignment takes about a day, and each review round takes 1-7 business days.
* **Direct Messaging:** authors MUST NOT message reviewers directly to speed up review.
* **Revisions:** address *all* feedback points, make targeted changes rather than rewriting, and leave a revision summary.
* **Disputes:** respond politely with concrete evidence, use the platform dispute path, and escalate in Slack if needed. Escalated appeals are final.
* **Final tier:** the 8-run measurement runs after acceptance, so the recorded tier can differ from what you saw while iterating.

### **H. Payment and Project Administration**

* Payment is tied to Accepted submissions, not merely Submitted.
* Billing weeks run Friday to Thursday UTC. Payments process 1-2 weeks after the billing week closes.

### **I. Troubleshooting and Documented Workarounds**

* Ensure Docker Desktop (v24.0.0+) is running. Allow default Docker socket usage in macOS. Apply Linux Docker-group fixes if permissions fail.
* "Provider List" warnings and model-retrieval warnings in agent logs are safe to ignore.
* If API key refresh hits the maximum limit, ask an admin to reset.

### **J. Quality and Anti-Pattern Summary**

* **Good Failures:** reasoning gaps, missed edge cases, interacting constraints, multi-step complexity.
* **Bad Failures:** ambiguity, hardware-timing, external resource crashes, overfit tests, and thresholds so tight that a substantively working solution misses them. If agents fail for bad reasons, the task is defective, not Frontier.

### **K. Known Bugs and Source-Grounded Workarounds**

* **No installers in test.sh:** legacy docs show `uv venv` and `uvx` bootstrapping inside the verifier entrypoint. Neither belongs there now — verifier tooling is baked into tests/Dockerfile and test.sh only runs `python -m pytest`.
* **Concurrency:** n-concurrent evaluations can cause port collisions. Ensure tasks are network-isolated if possible.
* **Rubric Overwrite:** a known platform UI bug will delete your manual rubric edits if you leave the rubrics checkbox checked on your final submission.

### **L. Minimal Checklist of Non-Negotiable Acceptance Conditions**

1. **Structure:** instruction.md, task.toml, environment/Dockerfile, solution/solve.sh, tests/Dockerfile, tests/test.sh, and tests/test_outputs.py are present and properly formatted; the top-level `artifacts` array declares every path the verifier reads, and tests/Dockerfile creates each landing directory.
2. **Metadata:** descriptive fields under `[metadata]`; exactly one Title Case category and subcategory; a measured difficulty tier; `[verifier].environment_mode = "separate"`; `[agent].timeout_sec` between 1800 and 18000; no retired keys.
3. **Performance:** oracle passes, NOP fails, and the task is not solved by every trial across both models. The verifier checks final state deterministically.
4. **Safety:** no web data fetches at runtime, in the image build or in the verifier; no privileged containers; no test files or solution baked into the agent image.
5. **Process:** CI and automated behavior checks pass, ruff passes, the rubric is manually audited in the platform UI, and the zip contains files at the archive root (no nested folders) with no authored rubrics.txt or README.md.
