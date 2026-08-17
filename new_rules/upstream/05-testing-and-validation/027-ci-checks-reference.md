---
title: "CI Checks Reference"
section: "Testing & Validation"
source: "https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/testing-and-validation/ci-checks-reference"
captured: 2026-08-12
---

# CI Checks Reference

Automated checks run against every submission. Errors block acceptance; warnings should be fixed unless a reviewer approves an exception.

Run them locally before submitting:

```bash
stb harbor check <task-folder>
```

> **Check list evolving.** Terminus 3 uses the Terminal-Bench 3.0 check suite. The list below covers the checks that apply to Terminus 3 submissions; individual checks may be added or adjusted as the edition progresses.

---

## Manifest & Metadata

**Required fields present** — `task.toml` must contain every required field. See [Task Components](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/task-components).

**Verifier configured for separate mode** — `[verifier].environment_mode` must be `"separate"`, and `artifacts` must be a **top-level** key.

> ⚠️ **Silent failure:** nesting `artifacts` under `[verifier]` does not error — the value is silently dropped and your verifier receives nothing. Keep it top-level.

**Timeout ceiling** — `[agent].timeout_sec` and `[verifier].timeout_sec` must not exceed **18000 seconds (5 hours)**. The agent-timeout *minimum* of 1800 seconds is a reviewer criterion rather than a CI error.

**Task folder name length** — the folder name is capped at a maximum number of hyphen-separated tokens. Long slugs become unwieldy in CLI output, logs, and artifact paths.

---

## Instructions

**Absolute paths** — instructions must reference absolute paths (`/app/output.json`), never paths relative to an assumed working directory.

**Referenced files are described** — every file your tests read or write must be mentioned in `instruction.md`. If a test checks `/app/output/results.json`, the instruction has to tell the agent to produce it. This catches tasks with implicit expectations the agent cannot know about.

**Human-authored content** — `instruction.md` and `solve.sh` are screened for AI-generated text, and a submission fails if the probability of AI generation exceeds a threshold. Write your own prompts. See [Instruction Prompt Styling](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/prompt-styling).

---

## Environment & Dockerfile

**Pinned pip installs** — every `pip` / `uv pip` / `uvx --with` install must pin an exact version with `==`. Unpinned installs let runtime versions drift after the task was authored.

**Unpinned apt installs** — the opposite applies to apt: use `apt install <package>`**without**`=version`.

**No platform pinning** — Dockerfiles must not pin a CPU architecture via `FROM --platform=...`. Tasks should be portable across architectures.

**No bare `nproc`** — inside a container, `nproc` reports the *host* CPU count, not your configured limit. Scripts in `Dockerfile`, `test.sh`, or `solve.sh` that call it can request far more parallelism than the task is allocated.

**Dockerfile references resolve** — files your Dockerfile copies or references must exist in the build context.

**Dockerfile hygiene** — additional non-fatal warnings flag common issues. See [Dockerfile Requirements](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/creating-tasks/dockerfile-best-practices).

**No host bind mounts in compose** — multi-container environments must not use host bind mounts as volume sources. Containers that need to share state must do so another way.

---

## Verifier & Tests

**Tests and solution absent from the agent image** — `tests/` and `solution/` must never be copied into the environment image.

**Verifier tooling baked in** — in separate-verifier mode, test tooling must be installed in `tests/Dockerfile`. Installing pytest at trial time inside `test.sh` fails.

**Pinned test tooling** — verifier dependencies must be pinned to exact versions.

**CTRF reporting** — pytest-based verifiers must run with `--ctrf /logs/verifier/ctrf.json`. Enforced by the `ctrf_reporting` check.

**Digest-pinned verifier base** — every `FROM` in `tests/Dockerfile` must be digest-pinned and on a sanctioned base, the same rule as `environment/Dockerfile`. Currently reported as a warning rather than a hard failure.

**No trial-time network fetches** — `tests/test.sh` must not fetch external resources. Bootstrap patterns like `curl … | sh`, `wget … | sh`, and `bash <(curl …)` are flagged. Everything the verifier needs belongs in its image.

**test.sh sanity** — the verifier entrypoint is checked for structural problems, including system-wide or global side effects.

---

## Internet Access

`network_mode = "public"` is the default. Use `"no-network"` only when the task does not make sense to complete with internet access:

```toml
network_mode = "public"       # or "no-network"
```

Regardless of the setting, verifier tooling must be baked into `tests/Dockerfile` — `test.sh` may never fetch at trial time.

---

## Acting on Failures

1. **Errors first** — these block acceptance.
2. **Then warnings** — fix unless a reviewer has approved an exception.
3. **Re-run**`stb harbor check` until clean, then measure difficulty.

---

## Next Steps

- [Submission Checklist](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/submitting-tasks/submission-checklist)
- [Writing Tests](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/creating-tasks/writing-tests)

---

[Previous: CI Feedback Training](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/testing-and-validation/ci-feedback-training) · [Next: LLMaJ Checks Reference](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/testing-and-validation/llmaj-checks-reference)
