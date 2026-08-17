---
title: "Difficulty Guidelines"
section: "Understanding Tasks"
source: "https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/difficulty-guidelines"
captured: 2026-08-12
---

# Difficulty Guidelines

Difficulty is **empirical**, not self-assessed. It is measured by running your task against frontier agents and recording how often they succeed.

## The Metric

**Accuracy = average pass@1 across 8 runs — 4 per model, over both GPT-5.6 and Claude Opus 5.**

Accuracy is the mean pass rate across all 8 runs, not a best-model or worst-model figure.

Difficulty is measured in **two stages**, and they use different run counts:

| Stage | Runs | What it decides |
| --- | --- | --- |
| **In-platform iteration** — while you build | 2 per model × 2 models = **4** | Whether the task can go to review |
| **Final difficulty** — after a reviewer accepts | 4 per model × 2 models = **8** | The tier recorded for your task |

**The iteration gate: at least one of the 4 runs must fail.** If every run passes, the task is trivial — it produces no signal about agent capability — and it cannot proceed to review. Fix that by making the task harder, not by narrowing a threshold.

The full 8-run measurement only happens **after reviewer acceptance**, so the tier you see while iterating is an early read, not your final one.

## Difficulty Tiers

| Tier | Accuracy | Target share of suite |
| --- | --- | --- |
| **Frontier** | < 20% | 20–30% |
| **Advanced** | 20% – < 50% | 25–35% |
| **Core** | 50% – < 80% | 30–40% |
| **Base** | 80% – < 100% | 5–15% |

Set the resulting tier in `task.toml`:

```toml
[metadata]
difficulty = "advanced"
```

> **Changed from Terminus 2nd Edition:** tasks with pass rates above 80% are **no longer rejected**. The Base tier exists deliberately and makes up 5–15% of the suite.
>
>
> What is not accepted is **100% accuracy averaged across both models** — a task every run solves provides no signal. 90% is acceptable; 100% is not. This is measured across both models together, not per model: one model going 4/4 is fine as long as the other fails at least once.

The target shares describe the shape of the **whole suite**, not a quota you personally must hit. They tell you where submissions are most valuable: Frontier and Advanced tasks are the scarcest and hardest to author well.

## Designing for a Tier

Difficulty does not come from obscurity or volume of work. It comes from **how much has to be true simultaneously** for the result to be correct.

**Frontier (< 20%)** — the specification itself must be inferred from domain evidence, the output must be a semantically correct native artifact, and several correctness axes interact. Success requires the agent to build a correct model of the domain before it can write anything useful.

**Advanced (20–50%)** — the goal is clear but the path is not. Multiple constraints interact, state must be handled correctly across steps, and a plausible-looking result can still be wrong.

**Core (50–80%)** — a well-specified problem with real depth: multi-step, some domain knowledge, edge cases that punish careless work.

**Base (80–100%)** — genuinely solvable by a competent agent, but still multi-step and non-trivial. Base tasks anchor the low end of the curve.

## Making a Task Harder — and What Doesn't Work

**Works:**

- Require the agent to *infer* the contract from domain evidence rather than stating it.
- Demand a native, structurally valid artifact rather than something that merely looks right.
- Add a second correctness axis that interacts with the first (performance under determinism; safety under state consistency).
- Verify against hidden variations that test whether the agent understood the contract, not whether it passed one example.

**Doesn't work:**

- Piling on unrelated independent requirements — that is length, not difficulty.
- Ambiguity or under-specification. A task that is hard because it is unclear is a broken task, not a Frontier task.
- Obscure trivia with no reasoning behind it.
- Anything that makes runs non-deterministic.

## Measuring Your Task

Run against both models before submitting:

```bash
stb harbor run -m @openai/gpt-5.6 -p <task-folder> -k 4
stb harbor run -m @anthropic/claude-opus-5 -p <task-folder> -k 4
```

`-k 4` mirrors the final measurement, so it gives you the best local read on where your task will land. Fewer runs are fine for a rough signal while you iterate.

> **The tier you see while iterating is provisional.** In-platform iteration runs 4 trials, not 8, and your final tier comes from the full 8-run measurement after acceptance. A task can shift tiers between the two.

Then check *why* agents failed. Failures caused by unclear instructions, environment defects, or flaky tests are **bugs**, not difficulty — fix them and re-measure. Only failures that come from the actual challenge of the task should count toward your tier.

## Reading the Trial Analysis

The difficulty check ends with a **trial analysis** section reporting six criteria. Each returns **PASS**, **FAIL**, or **NOT_APPLICABLE** — a criterion is *flagged* when it returns FAIL. `NOT_APPLICABLE` is not a problem; it means there wasn't enough evidence to judge.

You see this before you submit, and reviewers see the same output. Resolving a flag now is far cheaper than having the task returned for it.

**Two flags mean the task must change:**

| Flag | What it means | What to do |
| --- | --- | --- |
| `task_specification` | Your tests require something `instruction.md` never states — an exact parameter name, file format, return value, or structure the agent had to guess. | Specify it in the instruction, or relax the test. |
| `reward_hacking` | The agent reached its reward illegitimately — editing tests, writing the reward file directly, or reading `solution/`. | Close the hole. See [Writing Tests](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/creating-tasks/writing-tests). |

**Four flags need you to look, and often mean the task is measuring the wrong thing:**

| Flag | What it means | What to do |
| --- | --- | --- |
| `difficulty_crux` | The agent failed for a reason unrelated to the challenge you described in `[metadata].difficulty_explanation`. | Either the task carries unintended difficulty, or your explanation doesn't describe the real crux. Fix whichever is wrong. |
| `near_miss` | The agent produced a substantively working solution that missed a quantitative threshold narrowly — 95% against a required 98%, say. | Your threshold is producing the difficulty, not the problem. A task that looks Frontier because of a tight cutoff is not a Frontier task. |
| `refusals` | The agent aborted on a content or safety policy instead of attempting the task. | Review the framing and content — a refused trial measures nothing. |
| `low_timeout` | The agent was still making real progress when the timeout hit. | Raise `[agent].timeout_sec`. Difficulty should come from the problem, not from running out of time — see [Task Requirements](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/task-requirements). |

A flag is not automatically fatal, but it does need an answer. Reviewers send a task back when a flag's reason holds up, so it is worth resolving — or being able to explain — before you submit.

---

## Next Steps

- [Task Requirements](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/task-requirements)
- [What Makes a Good Task](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/what-makes-a-good-task)

---

[Previous: Instruction Prompt Styling](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/prompt-styling) · [Next: Example Tasks](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/example-tasks)
