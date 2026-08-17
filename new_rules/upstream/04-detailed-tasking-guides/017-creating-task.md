---
title: "Creating a Task"
section: "Detailed Tasking Guides"
source: "https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/creating-tasks/videos/creating-task"
captured: 2026-08-12
---

# Creating a Task

> **Note:** These videos were recorded for Terminus 2nd Edition. The workflow still applies, but the task structure has changed — see [What's New](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/getting-started/whats-new) and [Task Components](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/task-components).

Learn how to create a new task from scratch using the task skeleton template.

## Getting Started

To create a new task, you'll start with the task skeleton template and customize it for your specific task.

## Step 1: Download the Task Skeleton

> **Coming soon.** The Terminus 3 task skeleton is being prepared — there is a single skeleton for this edition. This page will link it once available.

## Step 2: Extract and Rename

1. **Extract the ZIP file** to your desired location
2. **Rename the unzipped folder** to match your task name

**Naming conventions:**

- Use kebab-case (lowercase, hyphens)
- Be descriptive but concise
- Examples: `parse-json-logs`, `debug-python-import`, `configure-nginx-ssl`

**Good task names:**

- ✅ `parse-json-logs`
- ✅ `debug-python-import`
- ✅ `configure-nginx-ssl`

**Bad task names:**

- ❌ `task1`
- ❌ `my-task`
- ❌ `test`

## Task Structure

After extracting and renaming, you'll have a folder structure like this:

**Task layout:**

```
your-task-name/
├── task.toml           # Task configuration and metadata
├── instruction.md      # Task instructions (markdown)
├── environment/        # Environment definition folder
│   ├── Dockerfile      # OR docker-compose.yaml
│   └── data/           # Bundled inputs
├── solution/           # Oracle solution
│   └── solve.sh        # Solution script + dependencies
└── tests/              # Verifier (runs in a separate container)
    ├── Dockerfile      # Verifier image
    ├── test.sh         # Verifier entrypoint
    └── test_outputs.py # Python pytest assertions
```

## Next Steps

After downloading and renaming your task skeleton:

1. **Edit `instruction.md`** — Write clear, unambiguous task instructions
    - [Guide: Writing task instructions](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/prompt-styling)
2. **Configure `task.toml`** — Set up metadata and configuration
    - [Guide: Task Components](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/task-components)
3. **Set up environment** — Configure Docker in the `environment/` folder
    - [Guide: Creating Docker environment](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/creating-tasks/creating-docker-environment)
4. **Write the solution** — Create `solution/solve.sh`
    - [Guide: Writing oracle solution](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/creating-tasks/writing-oracle-solution)
5. **Create tests** — Write `tests/test.sh` and Python pytest files
    - [Guide: Writing tests](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/creating-tasks/writing-tests)
6. **Test locally** — Run the oracle agent to verify your task works
    - [Guide: Oracle agent](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/testing-and-validation/oracle-agent)

---

## Related Resources

- [Running your task](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/creating-tasks/videos/running-your-task)
- [Writing oracle solution](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/creating-tasks/writing-oracle-solution)
- [Writing tests](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/creating-tasks/writing-tests)
- [Task Components](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/task-components)
- [Task Requirements](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/task-requirements)

---

[Previous: Example Tasks](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/example-tasks) · [Next: Running Your Task](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/creating-tasks/videos/running-your-task)
