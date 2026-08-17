---
title: "Submission Checklist"
section: "Submission Process"
source: "https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/submitting-tasks/submission-checklist"
captured: 2026-08-12
---

# Submission Checklist

Run through this before every submission.

---

## Task Design

- [ ] Goal is clear and unambiguous; requirements are inferable from the materials provided
- [ ] Instruction is as concise as the task allows (around 2 short paragraphs or 20 bullets), and not LLM-generated
- [ ] Uses absolute paths (e.g. `/app/output.json`)
- [ ] Output files and formats are specified
- [ ] Not solvable in a single command or a straight-line burst — requires chaining, intermediate state, and reacting along the way
- [ ] Novel — not a variation of an existing task or a reskin of your own earlier work
- [ ] Exactly one `category` and one `subcategory` from the taxonomy
- [ ] No canary strings in any component

## Required Files

- [ ] `task.toml` — all required fields present
- [ ] `instruction.md`
- [ ] `environment/Dockerfile` — builds successfully; dependencies pinned; every `FROM` digest-pinned
- [ ] `solution/solve.sh` — deterministic, human-written
- [ ] `tests/Dockerfile` — verifier image with dependencies baked in
- [ ] `tests/test.sh` — verifier entrypoint
- [ ] `tests/test_outputs.py` — Python pytest tests with docstrings

> `rubrics.txt` and `README.md` are added by Snorkel during packaging — you don't ship either. The README is built from your `task.toml` explanation fields.

## Verifier

- [ ] `[verifier].environment_mode = "separate"`
- [ ] `artifacts` is a **top-level** key and lists every path the verifier needs
- [ ] Parent directories for those artifacts exist in the verifier image
- [ ] `solution/` and `tests/` are absent from the agent image
- [ ] Tests are deterministic — no network, no wall-clock dependence, no unseeded randomness
- [ ] Tests check semantics, not appearance
- [ ] Verification covers every correctness axis the task claims to care about

## Configuration

- [ ] `[agent].timeout_sec` is at least **1800** (30 min) and reflects the time the task actually needs
- [ ] `[verifier].timeout_sec` and `[environment].build_timeout_sec` set
- [ ] `network_mode` is `"public"` unless the task specifically needs to run offline
- [ ] No GPU required; runs within ~2 CPU cores, ~8 GB memory, ~10 GB storage
- [ ] Descriptive fields are under `[metadata]`, not at the top level
- [ ] 3–6 `tags`; `languages` and `expert_time_estimate_hours` set
- [ ] `author_name` and `author_email` set (`"anonymous"` is fine)
- [ ] `difficulty_explanation`, `solution_explanation`, `verification_explanation`, and `relevant_experience` written

## Rubric

- [ ] Rubric generated and edited in the platform submission UI
- [ ] Maximum cumulative score is 10–40 points
- [ ] **At least one** criterion assigns a negative reward
- [ ] Every line starts with "Agent" and ends with `, ±N`; positives carry an explicit `+`
- [ ] Only ±1, 2, 3, 5 used — no 4s
- [ ] Checkbox unchecked before sending to reviewer

---

## Automated Checks

```bash
stb harbor run -a oracle -p <task-folder>
```

- [ ] Oracle agent PASSES
- [ ] `stb harbor check` clean — all errors resolved, warnings fixed unless a reviewer approved an exception

---

## Difficulty Measurement

```bash
stb harbor run -m @openai/gpt-5.6 -p <task-folder> -k 4
stb harbor run -m @anthropic/claude-opus-5 -p <task-folder> -k 4
```

- GPT-5.6 pass rate: ____%
- Claude Opus 5 pass rate: ____%
- **Accuracy** (average across both): ____%

| Tier | Accuracy |
| --- | --- |
| **Frontier** | < 20% |
| **Advanced** | 20% – < 50% |
| **Core** | 50% – < 80% |
| **Base** | 80% – < 100% |

- [ ] `difficulty` in `task.toml` matches the measured tier
- [ ] Failures reflect genuine task difficulty — not unclear instructions, environment defects, or flaky tests

---

## Self-Check

1. Would a first-time reader understand what is being asked?
2. Can the agent obtain everything it needs from the environment?
3. Could a plausible-but-wrong solution pass my tests?
4. Do my tests check semantics rather than appearance?
5. Is everything deterministic?

---

## Submit

- [ ] ZIP contains the task **files**, not the enclosing folder
- [ ] All required files included
- [ ] Submitted under the **`Terminus-3-Prod`** project

---

## Need Help?

- Slack: [`#terminus-3-submissions`](https://snorkel-team.enterprise.slack.com/archives/C0BLQ26GN2W)
- [Reviewer Checklist](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/reviewing-tasks/reviewer-checklist)
- [FAQ](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/reference/faq)

---

[Previous: Platform Submission](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/submitting-tasks/platform-submission) · [Next: After Submission](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/submitting-tasks/after-submission)
