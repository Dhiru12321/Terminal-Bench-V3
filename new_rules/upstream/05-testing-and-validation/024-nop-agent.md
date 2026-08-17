---
title: "NOP Agent"
section: "Testing & Validation"
source: "https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/testing-and-validation/nop-agent"
captured: 2026-08-12
---

## NOP Agent (No Operation)

The **NOP Agent** (No Operation) is a baseline agent that performs **no work**. It serves as the **lower-bound performance baseline** for Harbor evaluations.

The NOP agent is used for **benchmarking** to validate that an evaluation pipeline is wired correctly and that failures are not caused by agent execution itself.

- **No setup**<br> Does not install dependencies or perform any environment initialization.
- **No execution**<br> Does not process the instruction or execute any task logic.
- **No results**<br> Returns immediately with an empty context after running the `test.sh` file.
- **0% success rate (expected)**<br> By definition, the NOP agent solves nothing. All task evaluations are expected to **fail**, and this failure is considered a **pass** for the CI step.<br> If the NOP agent passes a task, the task definition or evaluation logic is likely incorrect.
- **CI behavior**<br> If the NOP agent completes evaluation successfully (i.e., fails all tasks as expected), subsequent agents can run without requiring execution of the user’s `solve.sh` file.

---

[Previous: Oracle Agent](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/testing-and-validation/oracle-agent) · [Next: Testing Agent Performance](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/testing-and-validation/running-real-agents)
