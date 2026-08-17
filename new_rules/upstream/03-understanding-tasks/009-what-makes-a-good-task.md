---
title: "What Makes a Good Task"
section: "Understanding Tasks"
source: "https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/what-makes-a-good-task"
captured: 2026-08-12
---

# What Makes a Good Task

Terminal-Bench 2.1 asked agents to perform a difficult terminal or software task. **Terminal-Bench 3.0** asks something different: **understand a specialized domain, manipulate the right system or artifact inside it, and prove the result satisfies interacting hidden invariants.**

This is not simply "harder." The difficulty moves from isolated technical execution toward vertically integrated engineering. A strong Terminus 3 task usually follows this chain:

```
specialized evidence
        ↓
domain-specific inference
        ↓
algorithm/system manipulation
        ↓
native artifact or live state
        ↓
hidden, structural, performance, and safety verification
```

## Six Properties of Strong Tasks

**1. The specification must be inferred.** The correct model of the problem is not handed over as a checklist. The agent has to work out what the requirements *mean* in the domain before implementing anything — reconstructing structure from instrument output, deriving geometry from an engineering drawing, inferring rules from examples.

**2. Output semantics matter, not appearance.** Require a native, structurally valid artifact: an editable parametric feature tree rather than a baked mesh, a checkable proof without `admit`s, synthesizable RTL, correctly mutated live database state. Producing something that merely looks similar must not pass.

**3. Correctness is multidimensional.** Rather than one dominant axis, combine several that must hold simultaneously — functional correctness, performance, determinism, safety, provenance, state consistency, structure, generalization to hidden instances.

**4. Constraints interact.** The point is not that constraints are numerous, but that they affect one another: a navigation error changes fuel burn, which changes feasible routing, which changes crosswind exposure. Interacting dependencies are far more demanding than a list of independent assertions.

**5. State is part of the problem.** Strong tasks often are not "edit files and run pytest." They involve operating databases under live traffic, stream processors, ERP workflows, model-serving runtimes, or multi-service systems — understanding current state, sequencing operations correctly, recovering from partial progress, and validating the result from a clean process.

**6. Hidden checks probe understanding.** Verify semantic equivalence across variations and metamorphic properties, not just more examples. A solution should not be able to pass by satisfying its author's happy path.

## From TB-Style to Terminus 3-Style

| TB-style task | Terminus 3-style extension |
| --- | --- |
| Compile and repair a package | Repair a runtime while preserving batching, caching, streaming, numerical, and performance semantics |
| Recover a fixed database file | Maintain recovery ordering guarantees, or perform a zero-downtime live cutover |
| Solve an explicitly specified scheduling problem | Operate dispatch or ERP state under capacity, lineage, safety, and workflow constraints |
| Read a value from an image and compute output | Infer geometry from a drawing and construct an editable parametric model |
| Implement an algorithm | Produce a behaviorally compatible, performance-qualified reimplementation under hidden workloads |
| Process a scientific dataset | Infer the scientific interpretation, implement the analysis, and emit convention-correct, provenance-preserving results |

## What Still Disqualifies a Task

Ambiguity, non-determinism, unstated requirements, and hidden knowledge the agent could not possibly obtain. Difficulty must come from the problem, never from the description.

A task is also disqualified if the agent can shortcut it — reading the tests, finding the answer in the environment, or satisfying the checks without doing the work. See [Writing Tests](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/creating-tasks/writing-tests).

---

## Next Steps

- [Task Requirements](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/task-requirements)
- [Difficulty Guidelines](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/difficulty-guidelines)
- [Example Tasks](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/example-tasks)

---

[Previous: After Submission](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/submitting-tasks/after-submission) · [Next: Task Components](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/task-components)
