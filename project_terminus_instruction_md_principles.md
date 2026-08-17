# Project Terminus `instruction.md` Principles

Every `instruction.md` should follow these six general principles.

## 1. Task Instructions Must Be Concise

Task instructions should be concise and clear. This means outlining the task in as little as one sentence and as much as three paragraphs.

Tasks should not be long-running prompts with many different instructions or requirements to follow.

Aim to create tasks that represent genuinely challenging coding problems, not tasks that simply challenge an AI agent's ability to follow many instructions.

Task instructions should generally read like how a human would prompt a coding agent. This means no emojis, minimal markdown styling, and no long-running prompts.

## 2. Task Instructions Must Be Well Specified

While task instructions are required to be concise, they still must be well specified. The goal of the task should be clear and obvious to the human or agent.

The main issue to watch for is tasks with a large number of edge cases and requirements. If a task is primarily hard because of many edge cases or requirements that are not handled well, it should be rejected.

## 3. Task Instructions Must Be Interesting

The task instruction should not be obscure or irrelevant to the point that no group of developers or users would find it interesting.

Every task must be interesting or useful in some way.

## 4. Task Instructions Must Not Give Answers or Hints

Tasks should represent one-shot requests from a user to a terminal agent.

If `instruction.md` contains significant hints, rubrics, or stepwise guidance for how to solve the task, it is not representative of the desired task style.

Requirements can be included, but hints or step-by-step instructions should not be included.

## 5. Task Instructions Must Be Unique

The task must be noticeably unique compared to any task in Terminal Bench 2, Terminal Bench 3, or Snorkel's original Project Terminus Edition 1.

Similarity search evaluation results are provided to help make this determination.

Generally, a task is too similar if the initial state and instructions are not different in a non-trivial way, or if the expected output is not different in a non-trivial way.

## 6. Task Instructions Must Use Absolute Paths

The `instruction.md` file should use absolute paths.

The `instruction.md` file should not contain a canary string. A canary string is usually an indicator that an older task skeleton is being used. The canary string gets passed as part of the prompt, which should not be represented in the data.

# Human-Centric vs. Synthetic Styling

To maintain authenticity, prefer human-centric task wording over synthetic assistant-style wording.

| Feature | Synthetic Style to Avoid | Human-Centric Style to Target |
|---|---|---|
| Tone | `You are an expert programmer. Your goal is to...` | `We need to migrate the existing SQLite schema to...` |
| Guidance | `First, use the ls command to see files, then...` | `The source data is in /data. Output the result to...` |

# Quick Checklist

Before submitting an `instruction.md`, verify that it:

- Is concise, ideally one sentence to three paragraphs.
- Has a clear and obvious goal.
- Describes an interesting or useful engineering task.
- Does not include solution hints, rubrics, or step-by-step guidance.
- Is noticeably unique from existing benchmark tasks.
- Uses absolute paths.
- Does not include a canary string.
- Sounds like a real human request to a coding agent.
