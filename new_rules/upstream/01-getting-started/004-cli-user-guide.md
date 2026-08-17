---
title: "CLI User Guide"
section: "Getting Started"
source: "https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/cli-user-guide"
captured: 2026-08-12
---

# Snorkel Terminal-Bench CLI

The `stb` command-line tool provides an end-to-end interface for creating, testing, submitting, and reviewing Terminal-Bench tasks.

## Installation

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) installed and running
- [uv](https://docs.astral.sh/uv/) package manager

### Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Install stb

```bash
uv tool install snorkelai-stb --find-links https://snorkel-python-wheels.s3.us-west-2.amazonaws.com/stb/index.html --python ">=3.12"
```

The `stb` command will be available globally (restart your terminal if needed).

### Verify Installation

Check the version and available commands:

```bash
stb --version
stb --help
```

---

## Getting Started

### Authentication

```bash
stb login
```

This opens the API key page directly on the Experts platform. Click "Generate Key", copy the key, and paste it into your terminal.

### AI Credentials

Refresh AI credentials if exhausted or expired:

```bash
stb keys refresh
```

**View current credentials:**

```bash
stb keys show
```

### Using Your API Key Efficiently

Here are some tips for using your API key efficiently to avoid exhausting it quickly:

- **Run agents sequentially, not concurrently.** Running GPT-5.6 and Claude Opus 5 at the same time burns through your key budget much faster. Finish one model's runs before starting the other.
- **Test your task thoroughly with the oracle agent first.** Run `stb harbor run -a oracle -p <task-folder>` and make sure it passes consistently before spending key budget on real agent runs. If your oracle fails, you'll waste agent runs on a broken task.
- **Start with fewer runs.** You don't need 4 runs per model during early development. Do 1–2 runs per model to get a rough difficulty signal, then do the full set only when you're confident the task is ready.
- **Fix issues between runs.** If the first agent run fails for a "bad reason" (unclear instructions, environment problems, missing dependencies), fix the issue before running again rather than burning more attempts on a known-broken task.
- **Use interactive mode for debugging.** Instead of running full agent attempts to troubleshoot, use `stb harbor tasks start-env -p <task-folder> -i` to test commands manually — this doesn't consume API key budget.
- **Track your own usage.** Your key carries a $10 budget and expires after 30 days, but the CLI cannot report how much is left — keep a rough count of your agent runs so a batch doesn't exhaust the key mid-way.

---

## Task Submission Workflow

### Overview

```
1. Initialize  →  2. Develop  →  3. Test  →  4. Submit  →  5. Check Status  →  6. Iterate
```

### 1. Initialize Task

**First, find your assigned project:**

```bash
stb projects list
```

This shows your projects with names, IDs, and assignment status for each role (Submitter, Reviewer, Adjudication):

- **active**: You are assigned and the project is open
- **inactive**: You are assigned but the project is closed
- **unassigned**: You are not assigned to this role (contact admin to request assignment)

**Create a new task folder:**

```bash
stb init my-task-name -p PROJECT_ID -t TEMPLATE_NAME
```

You can use either the project name or UUID. If a project has only one template, `-t` is optional.

```bash
# Using project name
stb init my-task-name -p "Terminus-3-Prod" -t default

# Using project UUID
stb init my-task-name -p 3f2a9c1e-7b4d-4e88-9a15-c0d6e2f8b731
```

This creates a folder with `instruction.md`, `task.toml`, `environment/Dockerfile`, `solution/solve.sh`, and `tests/test.sh`. See [Task Components](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/task-components) for details.

### 2. Develop Your Task

Edit the generated files:

- `instruction.md` - Task instructions ([Task Components](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/task-components))
- `task.toml` - Metadata and configuration ([Task Components](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/task-components))
- `environment/Dockerfile` - Environment setup ([Docker Environment](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/creating-tasks/creating-docker-environment))
- `solution/solve.sh` - Oracle solution ([Writing Oracle Solution](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/creating-tasks/writing-oracle-solution))
- `tests/test.sh` - Verification tests ([Writing Tests](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/creating-tasks/writing-tests))

### 3. Test Locally

**Test your solution interactively:**

```bash
stb harbor tasks start-env -p ./my-task-name -i
```

**Run oracle agent:**

```bash
stb harbor run -a oracle -p ./my-task-name
```

**Test with real agents:**

```bash
# GPT-5.6
stb harbor run -m @openai/gpt-5.6 -p ./my-task-name

# Claude Opus 5
stb harbor run -m @anthropic/claude-opus-5 -p ./my-task-name
```

Run each agent 2-3 times to gauge difficulty. See [Testing Agent Performance](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/testing-and-validation/running-real-agents) for guidance.

### 4. Submit

> *⚠️ Before submitting: The rubric must be set up via the platform UI. The CLI does not include a rubric step. Navigate to the Experts platform, open your task, and complete the rubric configuration.*

```bash
stb submissions create ./my-task-name -p PROJECT_ID --time MINUTES
```

Use `--time` to specify time spent in minutes (e.g., `--time 120` for 2 hours).

The CLI automatically:

- Zips your task folder
- Uploads to the platform
- Runs automated checks
- Creates a submission record

### 5. Check submission status

To check the status of your tasks (which submissions you've made and what state they're in), list every submission you've made for a project:

```bash
stb submissions list -p PROJECT_ID
```

Add `--show-folder-names` to also see the local task folder name each submission came from (slower):

```bash
stb submissions list -p PROJECT_ID --show-folder-names
```

**Submission status reference:**

| Status | Meaning | Can update? |
| --- | --- | --- |
| `EVALUATION_PENDING` | Automated checks running | No |
| `NEEDS_REVISION` | Reviewer requested changes | Yes ✓ |
| `REVIEW_PENDING` | Waiting for a human reviewer | No |
| `ACCEPTED` | Task accepted | No |
| `OFFERED` | Offer made | No |
| `REJECTED` | Task rejected | No |
| `SKIPPED` | Task skipped | No |

**Drill into a specific submission:**

```bash
# Open in the browser
stb submissions view SUBMISSION_ID

# Download the submitted task files
stb submissions download SUBMISSION_ID

# Download the latest reviewer / automated feedback
stb submissions feedback SUBMISSION_ID
```

Feedback typically includes:

- Agent-generated quality and difficulty check results
- Notes from expert reviewers

### 6. Iterate on Feedback

Read any feedback carefully and either revise your submission accordingly or provide a rebuttal note when updating.

**Update when in `NEEDS_REVISION` state:**

```bash
stb submissions update ./my-task-name -s SUBMISSION_ID --time MINUTES
```

Use `--time` to specify time spent in minutes (e.g., `--time 60` for 1 hour).

If the submission was created using the CLI, you can omit the submission ID:

```bash
stb submissions update ./my-task-name --time MINUTES
```

**Control reviewer notification:** By default, submissions are sent to reviewers after evaluation passes. To skip this:

```bash
stb submissions update ./my-task-name --time MINUTES --no-send-to-reviewer
```

---

## Task Review Workflow

### Overview

```
1. Get Assignment  →  2. Download  →  3. Review  →  4. Make Decision
```

### 1. Get Review Assignment

```bash
stb reviews get -p PROJECT_ID
```

Fetches your current review or requests a new assignment.

**List your review assignments:**

```bash
stb reviews list -p PROJECT_ID
```

### 2. Download Submission

```bash
stb reviews download REVIEW_ID
```

Downloads and extracts the submission to your local machine.

**View feedback:**

```bash
stb reviews feedback REVIEW_ID
```

**Open in browser (optional):**

```bash
stb reviews view REVIEW_ID
```

### 3. Review the Task

Test and evaluate using the guidelines in [Review Guidelines](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/reviewing-tasks/review-guidelines) and [Reviewer Training](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/reviewing-tasks/reviewer-training).

### 4. Make Decision

**Accept:**

```bash
stb reviews accept REVIEW_ID --time MINUTES
```

Optional: Add notes with `-n` or `--notes`:

```bash
stb reviews accept REVIEW_ID --time MINUTES -n "Optional acceptance notes"
```

**Request revision:**

```bash
stb reviews revise REVIEW_ID --notes "Specific issues to address" --time MINUTES
```

Both commands require:

- `--time` or `-t`: Time spent in minutes (e.g., `--time 45` for 45 minutes)
- `--notes` or `-n`: Required for revisions, optional for acceptance

**Skip (if not qualified to review):**

```bash
stb reviews skip REVIEW_ID --reason REASON --rationale "Explanation"
```

Valid skip reasons: `outside_expertise`, `unclear_or_ambiguous`, `too_time_consuming`, `invalid_input`, `other`

---

## Task Adjudication Workflow

### Overview

```
1. Get Assignment  →  2. Download  →  3. Adjudicate  →  4. Make Decision
```

### 1. Get Adjudication Assignment

```bash
stb adjudications get -p PROJECT_ID
```

Fetches your current adjudication assignment or requests a new one.

**List your adjudication assignments:**

```bash
stb adjudications list -p PROJECT_ID
```

### 2. Download Submission

```bash
stb adjudications download ADJUDICATION_ID
```

Downloads the submission file, submission payload, and review payloads.

**View feedback:**

```bash
stb adjudications feedback ADJUDICATION_ID
```

**Open in browser (optional):**

```bash
stb adjudications view ADJUDICATION_ID
```

### 3. Adjudicate the Task

Review the submission along with the previous review feedback. Test and evaluate using the guidelines in [Review Guidelines](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/reviewing-tasks/review-guidelines) and [Reviewer Training](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/reviewing-tasks/reviewer-training).

### 4. Make Decision

**Accept:**

```bash
stb adjudications accept ADJUDICATION_ID --time MINUTES
```

Optional: Add notes with `-n` or `--notes`:

```bash
stb adjudications accept ADJUDICATION_ID --time MINUTES -n "Explanation of decision"
```

**Request revision:**

```bash
stb adjudications revise ADJUDICATION_ID --notes "Specific issues to address" --time MINUTES
```

Both commands require:

- `--time` or `-t`: Time spent in minutes (e.g., `--time 30` for 30 minutes)
- `--notes` or `-n`: Required for revisions, optional for acceptance

**Skip (if not qualified to adjudicate):**

```bash
stb adjudications skip ADJUDICATION_ID --reason REASON --rationale "Explanation"
```

Valid skip reasons: `outside_expertise`, `unclear_or_ambiguous`, `too_time_consuming`, `invalid_input`, `other`

---

## Additional Commands

### Claude Code Integration

Run Claude Code for interactive development:

```bash
stb claude
```

This launches Claude Code with pre-configured AI credentials from the platform.

---

## Troubleshooting

### "This folder has already been submitted"

Use `stb submissions update` instead of `create`.

### "Cannot update: submission is in X state"

You can only update submissions in `NEEDS_REVISION` state. Check with `stb submissions list`.

### Docker Issues

1. Ensure Docker Desktop is running
2. On macOS: Enable **"Allow the default Docker socket to be used"** in Docker Advanced Settings

See [Troubleshooting Guide](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/reference/troubleshooting) for more issues.

**Note:** Windows is not supported.

### API Key Issues

Run `stb login` to re-authenticate.

### "Maximum refresh limit" Error

If you see `Bad Request: Maximum refresh limit reached` when running `stb keys refresh`, you've exceeded the current cap on AI credential requests. Contact an admin to reset or raise it, then run `stb keys refresh` again.

### Model Warnings (Safe to Ignore)

```
Failed to retrieve model info for '@anthropic/claude-opus-5'...
```

This is a known harmless warning that can be safely ignored. Your testing will work fine.

---

## Upgrading

The CLI checks for updates hourly. When available, you'll see:

⚠️ Update available: 2.0.2 → 2.1.0 *(Versions shown for illustration purposes only)*

Run the following command to upgrade:

```bash
uv tool install snorkelai-stb --find-links https://snorkel-python-wheels.s3.us-west-2.amazonaws.com/stb/index.html --python ">=3.12" --reinstall --no-cache
```

Your config and credentials are preserved.

---

## Uninstallation

### Uninstall CLI

```bash
uv tool uninstall snorkelai-stb
```

### Remove Configuration (Optional)

```bash
rm -rf ~/.config/stb/
```

**Note:** Windows is not supported.

---

## Next Steps

- **New to Terminal-Bench?** Read [What Makes a Good Task](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/what-makes-a-good-task)
- **Ready to create?** See [Task Components](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/task-components) and [Platform Submission Guide](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/submitting-tasks/platform-submission)
- **Before submitting:** Review the [Submission Checklist](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/submitting-tasks/submission-checklist)
- **Need help?** Check the [FAQ](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/reference/faq) or ask in Slack

---

[Previous: Onboarding Video and Slides](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/onboarding/platform-onboarding) · [Next: NEW in Terminus 3](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/getting-started/whats-new)
