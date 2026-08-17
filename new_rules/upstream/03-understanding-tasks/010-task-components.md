---
title: "Task Components"
section: "Understanding Tasks"
source: "https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/task-components"
captured: 2026-08-12
---

# Task Components

Every Terminus 3 task is a directory that is fully compatible with the Terminal-Bench 3.0 framework. This page covers the required structure; see [Task Requirements](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/task-requirements) for the design rules each task must satisfy.

## Directory Layout

```
your-task-name/
├── task.toml                    # Metadata and manifest
├── instruction.md               # What the agent is asked to do
├── environment/
│   ├── Dockerfile               # Agent-facing environment
│   │   └── (or docker-compose.yaml for multi-container)
│   └── data/                    # Bundled inputs (sample data, configs)
├── solution/
│   └── solve.sh                 # Oracle solution
├── tests/
│   ├── Dockerfile               # Verifier environment (separate container)
│   ├── test.sh                  # Verifier entrypoint
│   └── test_outputs.py          # Python pytest assertions
├── rubrics.txt                  # Added by Snorkel at packaging
└── README.md                    # Added by Snorkel at packaging
```

## The Verifier Runs in a Separate Container

**This is the most important structural change.** Grading no longer runs inside the agent's environment. The verifier is built from `tests/Dockerfile` and runs in an isolated container the agent cannot access:

```toml
[verifier]
environment_mode = "separate"
```

Two consequences:

1. **Tests and oracle data are never visible to the agent.** Automated checks confirm `tests/` and `solution/` are absent from the agent image.
2. **The verifier only sees what you declare.** It cannot read the agent's filesystem freely — it reads the paths listed in `artifacts`.

### Artifacts

The top-level `artifacts` array lists the paths the verifier reads from the agent's final environment:

```toml
artifacts = ["/app/output.json", "/app/results/"]
```

> ⚠️ **`artifacts` is a top-level key.** Nesting it under `[verifier]` does not raise an error — the value is silently dropped and your verifier receives nothing.

**Parent directories for declared artifacts must exist in the verifier image.** If you declare `/app/output.json`, your `tests/Dockerfile` needs:

```dockerfile
RUN mkdir -p /app
```

Forgetting this is a common cause of verifier failures that look like test bugs.

## Component Requirements

### `instruction.md`

A clear, self-contained description of **what the agent must achieve**. Each task is a single-shot, outcome-verified problem: state the goal up front and do **not** enumerate the intermediate steps the agent should take. Avoid vague wording or reliance on external, changing information.

Aim for **around 2 short paragraphs or a list of up to 20 bullets**; more complex tasks may need more room. Prompts must not be LLM-generated. See [Instruction Prompt Styling](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/prompt-styling).

### `environment/Dockerfile`

Fully sets up the environment, including all tools and dependencies. A small subset of tasks use `docker-compose.yaml` for multi-container environments. See [Dockerfile Requirements](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/creating-tasks/dockerfile-best-practices).

> **Multi-container tasks.** The harness picks up `environment/docker-compose.yaml` on its own — no field in `task.toml` points at it. Set `[metadata].is_multi_container = true` when the task runs multiple containers; otherwise leave the field out.

### `solution/solve.sh`

A reference shell script that reliably completes the task. Helper scripts (`solve.py`, etc.) are permitted in `solution/` and called from `solve.sh`.

### `tests/`

Deterministic Python tests that check whether the task was solved, based on the **final state of the environment**. `tests/test.sh` is the entrypoint; `tests/Dockerfile` builds the verifier image. See [Writing Tests](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/creating-tasks/writing-tests).

### `rubrics.txt`

Criteria an LLM-as-Judge uses to evaluate an agent-generated solution.

> **You don't create this file.** Generate and edit your rubric in the platform submission UI exactly as before; Snorkel adds `rubrics.txt` to the task directory during packaging. Your ZIP does not need it. See [Rubrics](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/rubrics).

### `README.md`

Task documentation covering the difficulty rationale, the solution, and the verification approach. **Not provided to or used by agents.**

> **You don't create this file either.** Snorkel assembles it at packaging from your `task.toml` — the `difficulty_explanation`, `solution_explanation`, `verification_explanation`, and `relevant_experience` fields, plus `category` and `subcategory`. Put the effort into those fields — there's no second write-up to do.

## task.toml

```toml
artifacts = ["/app/output.json"]
name = "your-task-name"

[metadata]
author_name = "anonymous"
author_email = "anonymous"
category = "Software"
subcategory = "Databases"
tags = ["python", "wal", "recovery", "concurrency", "storage-engine"]
languages = ["python"]
difficulty = "advanced"
expert_time_estimate_hours = 6
difficulty_explanation = "What makes this task hard — the core crux an agent has to get right."
solution_explanation = "How the oracle solves it."
verification_explanation = "How the verifier decides the task was solved."
relevant_experience = "The background that qualified you to author this task."

[verifier]
timeout_sec = 1800
environment_mode = "separate"

[agent]
timeout_sec = 7200

[environment]
network_mode = "public"
build_timeout_sec = 900
cpus = 2
memory_mb = 8192
storage_mb = 10240
```

> ⚠️ **Descriptive fields belong under `[metadata]`.** The structure check no longer counts top-level copies of `author_name`, `category`, `subcategory`, `tags`, `languages`, `difficulty`, `expert_time_estimate_hours`, or the four `*_explanation` / `relevant_experience` fields. `name` resolves either at the top level or under `[metadata]`; `artifacts` stays **top-level**.

| Field | Requirement |
| --- | --- |
| `name` | Task name. Top level or under `[metadata]` — both resolve |
| `artifacts` | **Top-level.** Paths the separate verifier reads from the agent's final environment |
| `[metadata].category` / `.subcategory` | Exactly one of each, from [Task Taxonomy](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/task-taxonomy) |
| `[metadata].tags` | **3–6** free-form keywords capturing tools, libraries, techniques, or subtopics |
| `[metadata].languages` | Primary language(s), used for distribution accounting |
| `[metadata].difficulty` | Empirical tier — see [Difficulty Guidelines](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/difficulty-guidelines) |
| `[metadata].expert_time_estimate_hours` | Estimated expert time to author the task |
| `[metadata].author_name` / `.author_email` | Required. Both may be `"anonymous"` |
| `[metadata].difficulty_explanation` | What makes the task hard — the core crux an agent has to get right |
| `[metadata].solution_explanation` | How the oracle solves it |
| `[metadata].verification_explanation` | How the verifier decides the task was solved |
| `[metadata].relevant_experience` | The background that qualified you to author this task |
| `[metadata].is_multi_container` | Optional. Set to `true` only when the task runs multiple containers; omit it otherwise |
| `[environment].network_mode` | `"public"` (default) or `"no-network"`. Use `"no-network"` only when the task does not make sense to complete with internet access |
| `[verifier].timeout_sec` | Maximum verifier runtime |
| `[verifier].environment_mode` | Always `"separate"` |
| `[agent].timeout_sec` | Maximum agent runtime. **Minimum 1800** (30 min); ceiling 18000 (5 h). Most tasks sit around 3600–5400 |
| `[environment].build_timeout_sec` | Maximum environment build runtime |
| `[environment].cpus` / `.memory_mb` / `.storage_mb` | Resource limits — no GPU; ~2 cores, ~8 GB memory, ~10 GB storage |

---

## Next Steps

- [Task Requirements](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/task-requirements)
- [Writing Tests](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/creating-tasks/writing-tests)
- [Dockerfile Requirements](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/creating-tasks/dockerfile-best-practices)

---

[Previous: What Makes a Good Task](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/what-makes-a-good-task) · [Next: Task Requirements](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/task-requirements)
