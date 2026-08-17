---
title: "Task Taxonomy"
section: "Understanding Tasks"
source: "https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/task-taxonomy"
captured: 2026-08-12
---

# Task Category Taxonomy

Every task carries **exactly one category and exactly one subcategory**, set in `task.toml`:

```toml
[metadata]
category = "Science"
subcategory = "Chemistry"
```

Values are **Title Case** and must match the taxonomy exactly.

## Categories

### Science

Natural sciences, mathematics, and engineering science.

| Subcategory | Covers |
| --- | --- |
| `Biology` | Genomics, proteomics, structural/computational biology, bioinformatics |
| `Chemistry` | Molecular structure, spectra, crystallography, reaction/property analysis |
| `Physics` | Simulation and numerical modeling of physical systems, including electromagnetic/FDTD device simulation and inverse design |
| `Earth` | Earth, climate, hydrology, and environmental modeling |
| `Robotics` | Dynamics, trajectory optimization, control |
| `Math` | Formalized mathematics and theorem proving (Coq/Lean/Isabelle), formal verification |
| `Linguistics` | Computational and historical linguistics |

### Software

General software engineering — where the domain *is* software.

| Subcategory | Covers |
| --- | --- |
| `Algorithms` | Algorithmic problems, solvers, computational geometry, optimization |
| `Systems` | Concurrency, backends, distributed systems, infrastructure; build pipelines, bundling, release engineering |
| `Databases` | Storage engines, transactions, indexing, recovery |
| `Data engineering` | ETL, record linkage, data processing at scale; ontologies, RDF/OWL, SPARQL, knowledge graphs |
| `Frontend` | Web/UI applications and their client/server pipelines |
| `Languages` | Language tooling, compilers, program analysis |

### ML

Machine-learning training, serving, evaluation, and infrastructure.

| Subcategory | Covers |
| --- | --- |
| `Training` | Training loops, optimization, debugging training runs; training infrastructure (checkpointing, cluster recovery, data integrity) |
| `Inference` | Inference implementations and LLM serving stacks; serving infrastructure, production monitoring/drift |
| `Evaluation` | Eval harnesses, benchmark construction, grading |
| `Kernels` | Custom compute kernels and accelerator programming — CPU-simulated or compile-only, since tasks must not require a GPU |

> **`Kernels` without a GPU.** Terminus 3 tasks must not require a GPU, but kernel and accelerator work is still in scope. Two patterns work: **CPU-simulated kernels**, where the agent implements the kernel logic and the verifier checks numerical correctness against a reference on CPU; and **compile-only verification**, where the verifier checks that the kernel compiles and passes static or structural checks without executing it on device. All other requirements still apply — deterministic tests, an oracle solution that runs within the [compute limits](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/task-requirements), and a verifier in a separate container.

### Operations

Business, financial, and operational domain reasoning.

| Subcategory | Covers |
| --- | --- |
| `Finance` | Quantitative finance, risk, regulatory capital |
| `Logistics` | Dispatch, routing, fleet/flight planning, transportation |
| `Supply chain` | Procurement, production planning, manufacturing, ERP |
| `Claims` | Insurance/utility claims, billing rules, adjudication |
| `Compliance` | Regulatory reporting and compliance workflows |
| `Marketing` | Ads, CTR, marketing analytics |

### Security

Offensive and defensive security.

| Subcategory | Covers |
| --- | --- |
| `Cryptography` | Ciphers, cryptographic protocols and analysis |
| `Reverse engineering` | Binary RE, vulnerability hunting and patching, malware/backdoor analysis |
| `Forensics` | Network/host forensics, incident analysis and remediation |
| `AppSec` | Application- and web-layer vulnerabilities and defenses |

### Hardware

Physical and digital hardware design.

| Subcategory | Covers |
| --- | --- |
| `CAD` | Parametric CAD, mechanical part design |
| `RTL` | HDL, RTL, digital logic |

### Media

Creative and design work.

| Subcategory | Covers |
| --- | --- |
| `Music` | Music theory, audio transcription and processing |
| `Design` | Visual/layout design and reconstruction |

## Choosing Your Category

Pick the category describing the **domain the task lives in**, then the subcategory describing the specific work.

The most common tagging mistake is defaulting to **Software** because the task involves writing code. Nearly every task involves writing code. Ask instead: *what does the agent have to understand to get this right?* A task that debugs a training loop is `ML / Training`, not `Software / Systems`. A task that parses mass spectra to infer a molecular structure is `Science / Chemistry`, not `Software / Algorithms`. Reserve **Software** for tasks where software engineering itself is the subject matter.

If a task genuinely spans two categories, choose the one whose domain knowledge the agent cannot succeed without.

---

## Next Steps

- [Task Components](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/task-components)
- [Difficulty Guidelines](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/difficulty-guidelines)

---

[Previous: Task Requirements](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/task-requirements) · [Next: Rubrics](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/understanding-tasks/rubrics)
