---
title: "Welcome to Terminus 3"
section: "Getting Started"
source: "https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/getting-started/welcome"
captured: 2026-08-12
---

# Welcome to Terminus 3

## Latest Updates

Recent announcements. **[See the full Changelog →](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/changelog)**

| Date | Type | Change |
| --- | --- | --- |
| Jul 31, 2026 | 🆕 New | **Terminus 3 is now live.** Terminus 2nd Edition has concluded. The docs now cover Terminus 3: a new task category taxonomy, four empirical difficulty tiers, and a verifier that runs in a separate container. Milestone tasks are no longer part of the program. ***[Start with What's New](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/getting-started/whats-new)*** |

## What is Terminus 3?

Terminus 3 is Snorkel's expert-authored dataset targeting **Terminal-Bench 3.0**, a benchmark for evaluating AI coding agents on genuinely difficult, domain-grounded work.

Earlier editions asked agents to perform a difficult terminal or software task. Terminus 3 asks for something harder: tasks where the agent must **understand a specialized domain, manipulate the right system inside it, and produce a result that satisfies several interacting constraints at once** — verified against checks it cannot see.

Your job is to create those tasks.

> **Your work matters.**
>
>
> Every accepted task directly advances the development of AI coding agents by revealing their current limitations and pushing them to improve.

## Your Role as a Coding Expert

1. **Design tasks** grounded in a real domain, that challenge frontier models
2. **Write oracle solutions** that demonstrate correct completion
3. **Build verifiers** that check semantics, not appearance
4. **Iterate on feedback** from automated checks and peer review

## Difficulty Tiers

Difficulty is **measured, not declared** — from accuracy across GPT-5.6 and Claude Opus 5 (average pass@1 over 8 runs, 4 per model):

| Tier | Accuracy | Share of suite |
| --- | --- | --- |
| **Frontier** | < 20% | 20–30% |
| **Advanced** | 20% – < 50% | 25–35% |
| **Core** | 50% – < 80% | 30–40% |
| **Base** | 80% – < 100% | 5–15% |

See [Difficulty Guidelines](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/difficulty-guidelines).

## Evaluation Process

Each task goes through:

1. **Automated CI checks** — structure, manifest, dependencies, verifier isolation
2. **LLM-as-Judge (LLMaJ)** — quality evaluation
3. **Peer review** — human expert verification
4. **Agent evaluation** — run against Claude Opus 5 and GPT-5.6, 4 trials each after acceptance

## Quick Links

| Resource | Description |
| --- | --- |
| **[Quick Start Guide](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/getting-started/quick-start)** | Get set up |
| **[What's New in Terminus 3](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/getting-started/whats-new)** | Everything that changed |
| **[What Makes a Good Task](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/what-makes-a-good-task)** | What a strong task looks like |
| **[Task Components](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/task-components)** | Required files and structure |
| **[Task Taxonomy](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/task-taxonomy)** | Categories and subcategories |
| **[FAQ](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/reference/faq)** | Common questions |
| **[Snorkel Expert Platform](https://experts.snorkel-ai.com/)** | Submit and track your work |
| **[Glossary](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/reference/glossary)** | Project terms explained |

## Need Help?

| Resource | Link |
| --- | --- |
| **Slack** | [`#terminus-3-submissions`](https://snorkel-team.enterprise.slack.com/archives/C0BLQ26GN2W) |
| **Announcements** | [`#terminus-3-announcements`](https://snorkel-team.enterprise.slack.com/archives/C0BLN0YUNQN) |
| **Office Hours** | See the [Office Hours page](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/reference/office-hours) |

---

**Ready to dive in?****[Start with the Quick Start Guide](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/getting-started/quick-start)**

---

[Next: Quick Start Guide](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/getting-started/quick-start)
