---
title: "Example Tasks"
section: "Understanding Tasks"
source: "https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/example-tasks"
captured: 2026-08-12
---

# Example Tasks

Five reference tasks spanning four categories, followed by anti-examples showing what to avoid. These are calibration points for scope and rigor — not templates to copy.

---

## Reference Tasks

### Repair a broken statistical monitor

```toml
artifacts = ["/app/drift_monitor", "/app/data"]

[metadata]
category = "ML"
subcategory = "Inference"
tags = ["python", "numpy", "scipy", "drift-detection", "ml-monitoring", "statistics"]
expert_time_estimate_hours = 5
```

An embedding-drift monitor compares incoming windows against a reference baseline using several statistical tests, then emits alerts through a debouncer. It is broken in more than one place: stable distributions trigger alerts they shouldn't, real drift goes undetected, and alert state flickers in ways that don't track the data.

**Why it works.** The visible symptom is in the alert layer, but the defects reach into the statistical and distance utilities underneath. An agent that patches only what it can see fails. Correctness spans statistical validity, alert stability, and behavior across distinct scenario inputs at once.

### Fix a shared submission pipeline

```toml
[metadata]
category = "Software"
subcategory = "Frontend"
tags = ["react", "typescript", "forms", "validation", "crm"]
expert_time_estimate_hours = 5
```

A React/TypeScript intake app has a broken submission workflow spanning form handling, validation, normalization, deterministic timestamping, ledger reconciliation, and export. The normative specs live in the repository as JSON, and both the UI and a CLI entry point must run through the *same* pipeline — not parallel implementations.

**Why it works.** The contract is specified in machine-readable files the agent must read rather than prose it can skim. The shared-entry-point requirement rules out fixing each surface independently, and outputs are structured artifacts checked for exact shape.

### Debug event-time stream processing

```toml
artifacts = ["/app/app/"]

[metadata]
category = "Software"
subcategory = "Systems"
tags = ["stream-processing", "session-windows", "watermarks", "event-time", "aggregation"]
expert_time_estimate_hours = 8
```

A session-window processor groups timestamped events by inactivity gap, fires aggregates when sessions complete, and garbage-collects old state. Three symptoms are reported: recently active sessions go missing when late events arrive, merged sessions emit results inconsistent with full event history, and output stalls when sources produce data at different rates.

**Why it works.** Intended semantics are documented in a design file, so the agent must reconcile observed behavior against a specification rather than guess. The three symptoms share root causes in watermark and state handling — fixing them independently produces regressions. Certain files are explicitly read-only, so the contract cannot be redefined.

### Reconstruct an intrusion from captured evidence

```toml
[metadata]
category = "Security"
subcategory = "Forensics"
tags = ["forensics", "reverse-engineering", "cryptography", "network-analysis", "custom-protocol"]
expert_time_estimate_hours = 3
```

Captured network data from a suspected exfiltration is provided. One internal host generated suspicious outbound activity and exchanged a binary session with external infrastructure. The agent identifies the host, recovers a domain-generation sequence, decodes the session, and decrypts the stolen data — writing findings to a structured JSON file with named fields.

**Why it works.** Nothing states what the protocol is; it must be inferred from artifacts. Each stage gates the next — the wrong host yields the wrong seed, which yields the wrong key. The output schema is exact, so a correct narrative in the wrong format still fails.

### Repair write-ahead-log recovery ordering

```toml
artifacts = ["/app/"]

[metadata]
category = "Software"
subcategory = "Databases"
tags = ["python", "wal", "recovery", "concurrency", "storage-engine"]
expert_time_estimate_hours = 6
```

A WAL-backed storage engine must be repaired so recovery replays entries in the correct order and reports accurate statistics. The verifier imports named functions, so specific module APIs must remain available. Application modules are barred from a list of imports and constructs, and from writing to disk.

**Why it works.** The task fixes the *interface* precisely, so the agent cannot escape by restructuring around the problem. The prohibitions block whole classes of shortcut. Recovery ordering is exactly the kind of property that looks right in the happy path and breaks under the sequences a rigorous verifier exercises.

### What These Have in Common

- Requirements are **inferred** from specs, design docs, or evidence — not handed over as a checklist.
- Outputs are **structured artifacts** judged on exact shape and semantics.
- **Multiple defects or constraints interact**, so partial fixes regress.
- Constraints are **enforced**, not suggested: read-only files, banned imports, required APIs.
- Every one involves far more than a single command's worth of work — chaining, intermediate state, and reacting to what came before.

---

## Anti-Examples: Tasks to Avoid

### ❌ Too Easy

**File: `instruction.md`**

```markdown
Write a function that reverses a string.
```

**Problem:** One-liner in most languages, agents solve instantly.

### ❌ Too Vague

**File: `instruction.md`**

```markdown
Build a web scraper.
```

**Problem:** No specific requirements, impossible to verify.

### ❌ Requires Secrets or Unverifiable External State

**File: `instruction.md`**

```markdown
Query the Twitter API to get today's trending topics.
```

**Problem:** Two issues — it needs private API **credentials/secrets** (which can't be bundled or committed), and its output is **nondeterministic** (trending topics change constantly), so no stable verifier can grade it. Needing internet **by itself** is *not* a problem — a task that genuinely requires the network is acceptable with `network_mode = "public"`. The real issues here are the secret credentials and the unverifiable, ever-changing result.

### ❌ Ambiguous Success Criteria

**File: `instruction.md`**

```markdown
Make this code better.
```

**Problem:** "Better" is subjective without specific metrics.

---

---

## Next Steps

- [What Makes a Good Task](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/what-makes-a-good-task)
- [Difficulty Guidelines](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/difficulty-guidelines)
- [Task Components](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/task-components)

---

[Previous: Difficulty Guidelines](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/difficulty-guidelines) · [Next: Creating a Task](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/creating-tasks/videos/creating-task)
