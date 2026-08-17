---
title: "Quick Start Guide"
section: "Getting Started"
source: "https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/getting-started/quick-start"
captured: 2026-08-12
---

# Quick Start Guide

Get up and running with Terminus 3 in just a few minutes. This guide covers everything you need to start creating tasks.

## Prerequisites

Before you begin, make sure you have:

- Access to the **[Snorkel Expert Platform](https://experts.snorkel-ai.com/)**
    - You will use the **Terminus-3-Prod** project to submit your task
- Joined the Slack channels [`#terminus-3-submissions`](https://snorkel-team.enterprise.slack.com/archives/C0BLQ26GN2W) and [`#terminus-3-announcements`](https://snorkel-team.enterprise.slack.com/archives/C0BLN0YUNQN)
- Set up the **Snorkel CLI** tool
    - Read the [Snorkel CLI user guide](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/cli-user-guide)
    - Using the Snorkel CLI you can:
        - Check submission status
            - Accepted, pending review, evaluation pending, etc.
        - Generate your API key
        - Refresh your API key
        - Submit your tasks via CLI instead of platform *(optional)*
        - *and much more!*

## Environment Setup

Once you have the prerequisites taken care of, choose your setup path:

### Option A: Quick Setup with uv (Recommended)

For the fastest setup experience, use [uv](https://github.com/astral-sh/uv), a modern Python package manager:

**1. Install uv:**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**2. Install the Snorkel CLI (Python 3.12+):**

```bash
uv tool install snorkelai-stb \
  --find-links https://snorkel-python-wheels.s3.us-west-2.amazonaws.com/stb/index.html \
  --python ">=3.12"
```

**3. Log in and configure credentials:**

```bash
stb login
stb keys refresh   # if AI credentials are missing or expired
```

For full CLI details, see the [CLI User Guide](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/cli-user-guide).

**4. You're ready!** to start working and submitting your tasks!

> **Note:** You still need [Docker Desktop](https://www.docker.com/products/docker-desktop/) (v24.0.0+) installed and running.

---

### Option B: Manual Setup

If you need a more detailed setup path, follow these steps:

**Expandable section — Windows Users: Install WSL2 First**

If you're on Windows, you need to set up WSL2 before installing Docker.

**1. Install WSL2**

Open PowerShell as Administrator and run:

```powershell
wsl --install
```

When prompted, choose **Ubuntu 22.04** as your Linux distribution.

**2. Install Docker Desktop with WSL2 Integration**

- [Download Docker Desktop](https://www.docker.com/products/docker-desktop/)

During installation, make sure to:

- Enable **"Use WSL 2 based engine"**
- Enable **"Integrate with WSL"** → check Ubuntu

**3. Verify Docker in Ubuntu**

Open your Ubuntu terminal and run:

```bash
docker ps
```

This should run without errors. If you see a permissions error, you may need to restart Docker Desktop or your WSL session.

**Expandable section — Step 1: Install Docker Desktop**

Docker is required to run task environments. Note that you need to have at least version 24.0.0 or higher.

**Install:**

- [Download Docker Desktop](https://www.docker.com/products/docker-desktop/)

**Verify installation:**

```bash
docker --version
# Docker version 24.0.0 or higher
```

**Special macOS Configuration:**

1. Open Docker Desktop → Settings → Advanced
2. Enable: "Allow the default Docker socket to be used (requires password)"
3. If needed, run:

```bash
sudo dscl . create /Groups/docker
sudo dseditgroup -o edit -a $USER -t user docker
```

**Expandable section — Step 2: Install the Snorkel CLI**

```bash
uv tool install snorkelai-stb \
  --find-links https://snorkel-python-wheels.s3.us-west-2.amazonaws.com/stb/index.html \
  --python ">=3.12"
```

**Expandable section — Step 3: Configure Your API Keys**

```bash
stb login
stb keys refresh   # if AI credentials are missing or expired
```

For detailed setup instructions, see the [CLI User Guide](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/cli-user-guide).

**Expandable section — Step 4: Work On Your First Task**

Follow the complete [Platform Submission Guide](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/submitting-tasks/platform-submission) for detailed step-by-step instructions on:

- Downloading the task skeleton template
- Writing task instructions and configuration
- Setting up the Docker environment
- Creating your solution and tests
- Running local validation
- Submitting via ZIP upload to the Snorkel Expert Platform

---

We have found the following VS Code extensions will improve your experience with Terminus 3:

- **Docker** — For managing containers in VS Code;
- **Python** — For highlighting syntax, linting, etc.;
- **Markdown** — For editing markdown files (instruction.md);
- **TOML** — For editing task.toml files;
- **GitLens** — For an improved Git integration;

**Expandable section — Troubleshooting**

### Docker Issues

**"Cannot connect to Docker daemon"**

- Ensure Docker Desktop is running
- On macOS, check menu bar for Docker icon

**Permission denied**

```bash
sudo chmod 666 /var/run/docker.sock
```

For more help, see the [Troubleshooting Guide](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/reference/troubleshooting).

---

## What's Next?

Now that you're set up:

- Read [What Makes a Good Task](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/what-makes-a-good-task) for quality guidelines
- Check the [Task Components](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/task-components) reference
- Review the [Submission Checklist](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/submitting-tasks/submission-checklist) before submitting your tasks

---

[Previous: Welcome to Terminus 3](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/getting-started/welcome) · [Next: Onboarding Video and Slides](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/onboarding/platform-onboarding)
