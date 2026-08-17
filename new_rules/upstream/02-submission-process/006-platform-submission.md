---
title: "Platform Submission"
section: "Submission Process"
source: "https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/submitting-tasks/platform-submission"
captured: 2026-08-12
---

# Platform Submission Guide

Complete step-by-step guide for creating and submitting tasks through the Snorkel Expert Platform.

## High-Level Workflow

Tasking is performed through the **Terminus-3-Prod** project on the Snorkel Expert Platform. The complete workflow:

1. Download the task skeleton template *(coming soon)*
2. Extract and rename the folder
3. Write your task instructions and configure metadata
4. Set up the Docker environment
5. Create and test your solution
6. Write and verify tests
7. Run agents
8. Create ZIP file, check rubric generation checkbox, and Submit on platform
9. Review CI feedback and iterate + review generated rubric and edit for accuracy and completeness
10. When CI is passing, submit on platform to a reviewer

---

## Prerequisites

Before starting, ensure you have:

- Docker Desktop installed and running
- Harbor CLI installed (or access to Harbor commands)
- API key for running agents
- Access to the Snorkel Expert Platform

---

## Step 1: Download the Task Skeleton

> **Pending.** The Terminus 3 task skeleton is being prepared. Milestone and UI skeletons no longer apply — milestone tasks are not part of this edition, and the old UI subtype has been replaced by the new taxonomy. This page will link the skeleton once available.

## Step 2: Extract and Rename

1. Extract the ZIP file to your desired location
2. **Rename the folder** to match your task name (use kebab-case, e.g., `fix-memory-leak-python`)

## Step 3: Write Task Instructions and Configuration

### Author your instruction.md

See the [Prompt Styling Guide](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/prompt-styling) for detailed instructions and requirements about how you should style your instructions.

### Configure task.toml

Set up metadata and configuration:

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

> Descriptive fields go under `[metadata]` — top-level copies are no longer counted by the structure check. `artifacts` stays top-level, and `name` resolves in either place.
>
>
> `network_mode = "public"` is the default. Use `"no-network"` only when the task does not make sense to complete with internet access. See [Dockerfile Requirements](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/creating-tasks/dockerfile-best-practices).

## Step 4: Configure Docker Environment

Edit the `environment/Dockerfile` to set up your task environment:

- Install `tmux` and `asciinema` — **required by the agent runtime**. Leaving them out breaks any task running without network access, since nothing can fetch them at runtime. Install them explicitly regardless of `network_mode`.
- Add any dependencies required by your task
- Pin all package versions for reproducibility
- Digest-pin every `FROM` image with `@sha256:<digest>`
- For the final runtime stage, use a [canonical Terminal-Bench base image](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/creating-tasks/dockerfile-best-practices) when one matches your task's language. Non-canonical images are allowed with a brief written justification as a `Dockerfile` comment; missing justifications are blocked.
- Keep `environment/` at or below 100 MiB total and no file over 50 MiB
- Add `.dockerignore` for non-trivial environments
- Never copy `solution/` or `tests/` folders in the Dockerfile

For multi-container environments or custom configurations, see the [Docker environment documentation](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/creating-tasks/creating-docker-environment).

### Docker Troubleshooting

If you encounter Docker issues:

1. Ensure Docker Desktop is running
2. On macOS, enable in Advanced Settings: **"Allow the default Docker socket to be used (requires password)"**
3. Try these commands if needed:

```bash
sudo dscl . create /Groups/docker
sudo dseditgroup -o edit -a $USER -t user docker
```

## Step 5: Test Your Solution Locally

Enter your task container interactively to test your solution:

```bash
stb harbor tasks start-env -p <task-folder> -i
```

While in the container, test your solution approach to ensure it works as expected.

## Step 6: Create Solution File

Create `solution/solve.sh` with the verified commands:

- This file is used by the Oracle agent to verify the task is solvable
- Must be deterministic (same result every run)
- Should demonstrate the command sequence, not just output the answer

See [Writing Oracle Solution](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/creating-tasks/writing-oracle-solution) for guidance.

## Step 7: Write Tests

Create `tests/test.sh` and Python pytest files to verify task completion:

- The test script must run Python pytest and produce `/logs/verifier/reward.txt`
- Create Python pytest unit tests in `tests/test_outputs.py`
- Do not use `tests/test.sh` to run another language-specific test framework; Python pytest tests should drive any non-Python system under test
- Place any test fixtures or helper files in the `tests/` directory
- Bake all test dependencies into the Docker image; `tests/test.sh` must not install packages or download from the network at runtime

Tests must fully cover the prompt: explicit requirements, implicitly expected behavior, and critical edge cases—with every prompt requirement mapped to a test. See [Writing Tests](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/creating-tasks/writing-tests) for detail.

**Example test.sh:**

```bash
#!/bin/bash
set -uo pipefail

mkdir -p /logs/verifier

# Check if we're in a valid working directory
if [ "$PWD" = "/" ]; then
    echo "Error: No working directory set. Please set a WORKDIR in your Dockerfile before running this script."
    echo 0 > /logs/verifier/reward.txt
    exit 0
fi

# pytest and pytest-json-ctrf must be pre-installed in the Docker image.
python -m pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA
rc=$?

if [ "$rc" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
```

See [Writing Tests](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/creating-tasks/writing-tests) for detailed guidance.

## Step 8: Run Oracle Agent

Verify your solution passes all tests:

```bash
stb harbor run -a oracle -p <task-folder>
```

This should **PASS**. If it doesn't, fix issues before proceeding.

## Step 9: Test with Real Agents

1. Make sure your `stb` credentials are current (no manual `OPENAI_*` variables needed):

```bash
stb login
stb keys refresh   # if credentials are missing or expired
```

1. Run with GPT-5.6:

```bash
stb harbor run -m @openai/gpt-5.6 -p <task-folder>
```

1. Run with Claude Opus 5:

```bash
stb harbor run -m @anthropic/claude-opus-5 -p <task-folder>
```

Run each agent 4 times per model. Difficulty is the mean pass@1 across both models — see [Difficulty Guidelines](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/difficulty-guidelines). Tasks above 80% are not rejected; that is the Base tier. 100% across both models is.

## Step 10: Run LLMaJ Checks Locally

Run LLMaJ checks before submitting:

**GPT-5.6:**

```bash
stb harbor run -m @openai/gpt-5.6 -p <task-folder>
```

**Claude Opus 5:**

```bash
stb harbor run -m @anthropic/claude-opus-5 -p <task-folder>
```

All checks should pass before submission.

## Step 11: Final Verification

Before submitting, verify:

- Oracle agent passes
- All LLMaJ checks pass
- Tested against real agents (4 runs per model; tier recorded in `task.toml`)
- All files are present and correct

Run final checks:

```bash
# Oracle agent
stb harbor run -a oracle -p <task-folder>

# LLMaJ checks
stb harbor check harbor_tasks/<task_name>
```

## Step 12: Create ZIP File

**Important:** Select the individual files inside your task folder, not the folder itself.

**Task layout:**

```
.
├── task.toml            ← Select these
├── instruction.md       ←
├── environment/         ←
│   ├── Dockerfile       ← (or docker-compose.yaml)
│   └── data/            ← Bundled inputs
├── solution/            ←
│   └── solve.sh
└── tests/               ←
    ├── Dockerfile       ← Verifier image
    ├── test.sh          ← Verifier entrypoint
    └── test_outputs.py  ← Python pytest assertions
```

> `rubrics.txt` and `README.md` are **not** part of your ZIP — Snorkel adds both during packaging: the rubric from the platform UI, and the README from your `task.toml` explanation fields.

## Step 13: Submit to Platform

1. Go to the [Snorkel Expert Platform](https://experts.snorkel-ai.com/)
2. Navigate to **Terminus-3-Prod**
3. Click **Start** on the *Submission* node
4. Upload your ZIP file
5. Keep "Send to reviewer" unchecked
6. Check the rubrics checkbox
7. Submit

## Step 14: Check CI results and rubric then Iterate until CI looks good

1. After email notification that your submission is now back in your revision queue, go to [Snorkel Expert Platform](https://experts.snorkel-ai.com/).
2. Find your task on homescreen
3. Click "Revise"
4. Check CI Results & update task as needed
5. Check the now generated rubric and edit it within the textbox for accuracy and completeness
6. Re-upload a new .zip file if necessary
    - Use the [Reviewer Checklist](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/reviewing-tasks/reviewer-checklist) to confirm you have addressed high-severity review criteria before resubmitting.
    - *If you make any significant changes to your task, you must update your rubric accordingly in order to align with the current version of your task.*
7. Keep "Send to Reviewer" Unchecked
8. Submit

## Step 15: Submit your task to Reviewer

1. After email notification that your submission is now back in your revision queue, go to [Snorkel Expert Platform](https://experts.snorkel-ai.com/).
2. Find your task on homescreen
3. Click "Revise"
4. Check CI results
5. Check rubric and edit for accuracy and completeness
6. If all good, check "Send to Reviewer"
7. Submit

## Step 16: Monitor Status

After submission. wait for peer review (1-7 business days)

---

## After Submission

### Review Process

1. **Automated checks** runs immediately
2. **Peer review** within 1-7 business days
3. **Feedback** provided if changes needed
4. **Acceptance** when all criteria met

### If Changes Requested

1. Review the feedback carefully
2. Make requested changes locally
3. Re-run all checks
4. Create new ZIP and resubmit

---

## Common Issues

### ZIP Structure Wrong

**Problem:** Files nested in extra folder.

**Fix:** ZIP the files directly, not the containing folder.

### Missing Files

**Problem:** Forgot to include a file.

**Fix:** Verify all files are in ZIP before uploading.

- check that `instruction.md`, `task.toml`, `environment/`, `solution/`, and `tests/` are all included.

### CI Failures After Upload

**Problem:** Local checks passed but platform CI fails.

**Fix:** Check for environment differences, re-run locally with exact CI commands.

### Docker Build Fails

**Problem:** Docker build fails on platform but works locally.

**Fix:** Ensure all application dependencies (pip, npm, etc.) are pinned to exact versions, every Docker base image (and any images in `docker-compose.yaml`) is digest-pinned with `@sha256:<digest>`, and the final runtime base image is sanctioned or explicitly exempt. Also check that `environment/` is at most 100 MiB total, no file is over 50 MiB, and platform-specific differences are handled.

---

## Video Walkthroughs

Watch these step-by-step videos to learn how to create and test your task:

### 1. Running Your Task

#### Running your task

[Running your task](https://www.loom.com/embed/22449b76123d41e6abff0efb39d0b960?hide_owner=true&hide_share=true&hide_title=true&hideEmbedTopBar=true)

### 2. Creating a solution/solve.sh

#### Creating a solution/solve.sh

[Creating a solution/solve.sh](https://www.loom.com/embed/140f2cf8f16d404abf5cbd7dcc66b7cb?hide_owner=true&hide_share=true&hide_title=true&hideEmbedTopBar=true)

 The video refers to solution/solve.sh file. Using Harbor, this refers to solution/solve.sh

### 3. Creating Tests for Your Task

#### Creating tests for your task

[Creating tests for your task](https://www.loom.com/embed/a00541ff2787464c84bf4601415ee624?hide_owner=true&hide_share=true&hide_title=true&hideEmbedTopBar=true)

---

## Next Steps

- [Understand task components](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/task-components)
- [Review the submission checklist](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/submitting-tasks/submission-checklist)
- [Reviewer Checklist](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/reviewing-tasks/reviewer-checklist)
- [Learn about CI checks](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/testing-and-validation/ci-checks-reference)
- [Understand the review process](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/submitting-tasks/after-submission)

---

[Previous: NEW in Terminus 3](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/getting-started/whats-new) · [Next: Submission Checklist](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/submitting-tasks/submission-checklist)
