---
title: "Task Requirements"
section: "Understanding Tasks"
source: "https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/task-requirements"
captured: 2026-08-12
---

# Task Requirements

Every Terminus 3 task must satisfy all of the following. See [Task Components](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/task-components) for the file structure these rules apply to.

## Novel

Avoid **any** variation of an existing task in the Terminal-Bench 2.1 or Terminal-Bench 3.0 repositories, or in Snorkel's prior Terminus editions. Each task must introduce a new setup, definition, and data.

Reskinning — the same computation behind a different cover story, different variable names, or a different language — is not novelty. Near-duplicates are detected automatically using embedding similarity, and a task can be returned for duplication even when it is individually well built.

## Multi-Step

Tasks must require chaining commands, with intermediate state to handle and real reasoning along the way — error recovery, branching, or reacting to what the previous step produced. A task solvable with a single command, or a single straight-line burst of commands, does not qualify.

You will see **"at least 5 agent steps"** used as shorthand for this. It is a **heuristic for complexity, not a number anyone counts** — nothing tallies steps, and there is no threshold to clear. It exists to rule out tasks that are trivially short. In practice, a task sized for the 30-minute minimum runtime will run well past five steps without you thinking about it.

The question to ask is not *"how many steps is this?"* but *"could an agent finish this in one shot, without reacting to anything along the way?"* If the answer is yes, the task is too simple.

## Testable

Each task must be fully specified and self-contained, solvable without ambiguity, and accompanied by tests that deterministically measure the **final state of the environment** to decide whether the task was completed correctly.

## Standalone

The task must run to completion without human input after start. All parameters are supplied via files, flags, or environment variables — no interactive prompts, no mid-run decisions.

All tasks are validated with the Harbor framework: single-container tasks in Daytona, multi-container tasks in a Docker environment.

## Runtime

Set `[agent].timeout_sec` to a **minimum of 1800 seconds (30 minutes)**, with a ceiling of 18000 seconds (5 hours).

The minimum is a floor, not a target. Terminus 3 tasks are expected to involve substantial multi-step work — inferring a specification, operating a system, and validating the result — and most should land in the **60–90 minute** range. If your task genuinely completes in under half an hour, that is usually a signal it isn't deep enough for this edition.

Set the timeout to what the work actually needs. Padding a short task doesn't make it harder, and starving a long one causes failures that look like difficulty but are really budget.

## Internet Access

`network_mode = "public"` is the **default** — use it unless you have a specific reason not to:

```toml
network_mode = "public"
```

Set `network_mode = "no-network"`**only when the task does not make sense to complete with internet access** — for example, when network access would let the agent retrieve the answer directly instead of doing the work. If you're unsure, use `"public"`.

Either way, your task's dependencies must still be baked into the image at build time, and `tests/test.sh` must never fetch from the network at trial time.

## Compute Limits

Tasks must **not require a GPU**, and oracle solutions must run successfully within:

| Resource | Limit |
| --- | --- |
| Memory | ~8 GB |
| CPU | 2 cores |
| Storage | ~10 GB |

GPU-adjacent work is still authorable — see the [`Kernels` subcategory](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/task-taxonomy) for the CPU-simulated and compile-only patterns.

## Languages

This dataset targets languages under-represented in other benchmarks:

**Python · C · C++ · JavaScript · TypeScript · Java · Go · Rust · C#**

**Multi-language tasks are preferred.** Record the primary language(s) in `task.toml`:

```toml
[metadata]
languages = ["python", "c"]
```

`languages` records the **primary implementation language(s)** of the task — the language the agent mainly works in. It does not have to list every tool involved.

**Domain-specific toolchains are welcome even when they are not on the list.** A proof assistant, an HDL, a CAD scripting language, or a query language can absolutely appear in a task; they just may not be what the task as a whole is written in. Use `languages` for the primary work and let the domain tooling live in the environment.

The list is not meant to be restrictive. If you think a language belongs on it, say so in [`#terminus-3-submissions`](https://snorkel-team.enterprise.slack.com/archives/C0BLQ26GN2W) — we are open to expanding it.

> **Changed from Terminus 2nd Edition:** the rule requiring Python tasks to be HARD no longer applies. Difficulty tiers are language-independent.

## No Canary Strings

Tasks must not include canary strings in **any** component — instruction, environment, solution, tests, or metadata. Canary strings exist to keep benchmark data out of training corpora; this is a training dataset, so they are excluded. If you adapt an existing task as a structural starting point, remove any canary lines it carries.

## Instruction Prompts

Aim for **around 2 short paragraphs or a list of up to 20 bullets**; more complex tasks may need more room. State the goal; do not enumerate the intermediate steps. Prompts must not be LLM-generated — they should read like the way people actually talk to coding agents, and are automatically screened for AI-generated text. See [Instruction Prompt Styling](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/prompt-styling).

## Dependency Pinning

Every `FROM` image must be digest-pinned with `@sha256:<digest>`, and Python packages pinned to exact versions. Verifier tooling must be baked into `tests/Dockerfile`, never installed at trial time. See [Dockerfile Requirements](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/creating-tasks/dockerfile-best-practices).

## Rubrics

Every task ships with a rubric giving clear, deterministic criteria that map to measurable outcomes and align with the oracle solution.

> Generate and edit your rubric in the platform submission UI. Snorkel adds the `rubrics.txt` file during packaging — you don't author or ship it. See [Rubrics](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/rubrics).

---

## Next Steps

- [Difficulty Guidelines](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/difficulty-guidelines)
- [Writing Tests](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/creating-tasks/writing-tests)

---

[Previous: Task Components](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/task-components) · [Next: Task Taxonomy](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/task-taxonomy)
