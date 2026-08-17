---
title: "NEW in Terminus 3"
section: "Getting Started"
source: "https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/getting-started/whats-new"
captured: 2026-08-12
---

# What's New in Terminus 3

If you authored tasks for Terminus 2nd Edition, this page covers everything that changed.

## At a Glance

| Area | Terminus 2nd Edition | Terminus 3 |
| --- | --- | --- |
| Difficulty | Easy / Medium / Hard | **Frontier / Advanced / Core / Base** |
| Difficulty metric | ≤20% on best *or* worst model | Average pass@1 across **both** models, 4 trials each |
| Pass rate >80% | Rejected | **Accepted** — that's the Base tier |
| Categories | 9 flat categories | **7 categories, each with subcategories** |
| Verifier | Ran in the task container | **Separate container** the agent can't reach |
| Milestone tasks | Supported | **Removed** |
| Agent timeout | 1800s was the **maximum** | 1800s is the **minimum** (ceiling 18000s) |
| Rubrics | Platform UI | Platform UI (unchanged) — Snorkel packages the file |
| Required files | — | Adds `tests/Dockerfile`; `README.md` is packaged by Snorkel |

## The Bigger Shift

Earlier editions asked agents to perform a difficult terminal or software task. Terminal-Bench 3.0 asks them to **understand a specialized domain, manipulate the right system inside it, and produce a result that satisfies several interacting constraints at once.**

Tasks are stronger when requirements must be *inferred* from domain evidence, the output is a semantically valid artifact rather than something that merely looks right, and correctness spans several axes that affect one another. See [What Makes a Good Task](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/what-makes-a-good-task).

## What Changed in Your Task Directory

```
your-task-name/
├── task.toml
├── instruction.md
├── environment/
├── solution/
├── tests/
│   ├── Dockerfile     ← NEW: builds the verifier image
│   ├── test.sh
│   └── test_outputs.py
├── rubrics.txt        ← added by Snorkel at packaging
└── README.md          ← added by Snorkel at packaging
```

The verifier now runs in its own container. It sees **only** the paths you declare in the top-level `artifacts` array, and the parent directories for those paths must exist in the verifier image. See [Writing Tests](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/creating-tasks/writing-tests).

## What Changed in `task.toml`

**Added:**`subcategory`, `tags` (3–6), `expert_time_estimate_hours`, `artifacts`, `network_mode`, `[verifier].environment_mode`, `[environment].build_timeout_sec`.

**Removed:**`codebase_size`, `number_of_milestones`, the old `subcategories` list (`long_context`, `ui_building`, …), `allow_internet`, `junior_time_estimate_min`.

**Changed:**`difficulty` now takes a Terminus 3 tier; `category` and `subcategory` use the new taxonomy; `expert_time_estimate_min` becomes `expert_time_estimate_hours`.

**Moved:** the descriptive fields — `author_name`, `author_email`, `category`, `subcategory`, `tags`, `languages`, `difficulty`, `expert_time_estimate_hours`, and the `*_explanation` / `relevant_experience` write-ups — now live under **`[metadata]`**. Top-level copies are no longer counted by the structure check. `artifacts` stays top-level, and `name` resolves in either place.

See [Task Components](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/task-components).

## Rules Worth Re-reading

- **Agent timeout flipped meaning.** In Terminus 2nd Edition, 1800 seconds was the cap. In Terminus 3 it's the floor — tasks are expected to run longer, most in the 60–90 minute range.
- **No canary strings** in any component — this is a training dataset.
- **Novelty** is checked against prior editions and existing task repositories using embedding similarity. Reskinning your own earlier task will be caught.
- **Multi-step complexity.** "At least 5 agent steps" is a heuristic for ruling out trivially short tasks — not a number that gets counted.
- **No GPU**; ~2 CPU cores, ~8 GB memory, ~10 GB storage.
- **Instructions are screened for AI-generated text** and fail above a threshold — write your own prompts.

## What Didn't Change

The `stb` CLI, Docker setup, digest-pinned base images, dependency pinning, rubric authoring in the platform UI, and the core discipline of a deterministic oracle plus a rigorous verifier.

---

## Next Steps

- [Task Taxonomy](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/task-taxonomy)
- [Difficulty Guidelines](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/difficulty-guidelines)
- [Submission Checklist](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/submitting-tasks/submission-checklist)

---

[Previous: CLI User Guide](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/cli-user-guide) · [Next: Platform Submission](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/submitting-tasks/platform-submission)
