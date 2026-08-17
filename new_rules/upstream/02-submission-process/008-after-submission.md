---
title: "After Submission"
section: "Submission Process"
source: "https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/submitting-tasks/after-submission"
captured: 2026-08-12
---

# After Submission

What happens after you submit your task, and how to handle feedback.

## Review Timeline

| Stage | Duration |
| --- | --- |
| Automated CI checks | Immediate |
| Peer review assignment | 1 day |
| Initial review | 1-7 business days |
| Follow-up reviews | 1-7 business days |
| **Total** | 7-14 business days |

## Review Process

### 1. Automated Checks

Immediately after submission, your task goes through:

- CI checks (syntax, structure, dependencies)
- LLMaJ checks (quality, completeness)
- Oracle agent run

### 2. Peer Review

A qualified coding expert reviews:

- Task clarity and correctness
- Solution validity
- Test coverage
- Anti-cheating measures
- Overall quality

### 3. Agent Evaluation

Your task is run against:

- Claude Opus 5 with Claude Code (4 runs)
- GPT-5.6 with Codex agent (4 runs)

Pass rate determines final difficulty classification.

> **This is the full measurement.** While you were iterating, the platform ran 2 trials per model (4 runs). The 8-run measurement here runs only after a reviewer accepts the task, and it sets the final tier — which can differ from what you saw during iteration.

## Review Outcomes

### Approved ✓

Congratulations! Your task is accepted.

- Task added to benchmark suite
- Credit recorded in your profile

### Changes Requested

Reviewer identified issues that need fixing.

**What to do:**

1. Read feedback carefully
2. Understand each requested change
3. Make fixes locally
4. Re-run all checks
5. Resubmit / push updates

### Declined ✗

Task doesn't meet criteria. Common reasons:

- Too easy
- Unclear requirements
- Similar task already exists
- Fundamental design issues

**What to do:**

1. Review the feedback
2. Consider if it can be salvaged
3. Either significantly revise or start fresh
4. You can appeal if you disagree

## Addressing Feedback

### Read Carefully

Understand exactly what's being asked:

- Is it a minor fix or major revision?
- Does reviewer explain the reasoning?
- Are there specific lines/files mentioned?

### Make Targeted Changes

Don't rewrite everything. Fix only what's needed. Use the [Reviewer Checklist](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/reviewing-tasks/reviewer-checklist) to make sure all high-severity and relevant medium-severity criteria are covered before resubmitting.

### Explain Your Changes

When you resubmit: **Platform:** Add a note with your revision summary.

### Re-request Review

After pushing changes, let the reviewer know: **Platform:** Update submission status

## Disagreements

If you disagree with feedback:

1. **Respond politely** with your reasoning
2. **Provide evidence** for your approach
3. **Be open** to compromise
4. **Escalate** to Slack if needed

Remember: Reviewers want to help. Most disagreements are resolved through discussion.

## Tips for Faster Acceptance

1. **Run all checks locally** before submitting
2. **Follow the checklist** exactly
3. **Write clear documentation** in `instruction.md`
4. **Address feedback promptly**
5. **Ask questions** if feedback is unclear

---

## Need Help?

- Slack: `#terminus-3-submissions`
- [FAQ](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/reference/faq)
- [Troubleshooting](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/reference/troubleshooting)

---

[Previous: Submission Checklist](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/submitting-tasks/submission-checklist) · [Next: What Makes a Good Task](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/what-makes-a-good-task)
