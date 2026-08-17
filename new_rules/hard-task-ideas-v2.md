# Hard Task Ideas — Batch 2 (Project Terminus)

Seed bank for Terminus 3 idea generation, mined against
[what-makes-a-good-task.md](./upstream/03-understanding-tasks/009-what-makes-a-good-task.md)
and [idea-validation.mdc](../.cursor/rules/idea-validation.mdc). Complements
[hard-task-ideas.md](./hard-task-ideas.md) with **non-overlapping** ideas.
Nothing here has been through Step 2a.

Every entry aims at the Terminus 3 bar: understand a specialized domain,
manipulate the right system inside it, and produce a result that satisfies
several interacting constraints at once. Multi-file discovery and a long
command chain are what that work usually looks like, not the target — step
count only rules out trivially short tasks.

**The tier on each entry is a target, not a measurement.** Difficulty is
empirical — average pass@1 over 8 runs, 4 each on GPT-5.6 and Claude Opus 5 —
with `frontier` under 20%, `advanced` 20–<50%, `core` 50–<80%, and `base`
80–<100%. A tier becomes real only once the platform measures it. A high pass
rate is not a rejection reason: `base` is a deliberate tier, and only 100%
averaged across both models is unacceptable. Tiers are language-independent.

The platform envelope holds for every entry: no GPU (~2 CPU cores, ~8 GB
memory, ~10 GB storage), a single container, no milestone or staged grading,
deterministic outcomes, `[agent].timeout_sec` between 1800s and 18000s, and a
verifier that runs in its own container reading only the paths declared in the
top-level `artifacts` array. `network_mode` is `"public"` by default;
`"no-network"` is a per-idea choice, not a house rule.

---

## 1. Spectral Poisson solver boundary aliasing

**Category:** `Science` / `Physics`
**Target tier:** `frontier`

An FFT-based Poisson solver on a 2D grid converges for periodic boundaries but
**violates the discrete divergence theorem** under mixed Neumann/Dirichlet
because the spectral transform uses the wrong basis (DFT instead of
DCT/DST) on the non-periodic axis. Fix transform selection, k-space
denominator handling at the zero mode, and rescaling so conservation
invariants hold on **non-square grids with anisotropic spacing**.

**Why agents fail:** Patches the zero-mode singularity only; doesn’t notice the
basis must change per boundary class.

---

## 2. cgroup v2 + tmpfs double accounting

**Category:** `Software` / `Systems`
**Target tier:** `advanced`

A service runs fine on the host but is **OOM-killed inside a rootless container**
even though `memory.current` looks well below `memory.max`. The unit’s slice,
a `tmpfs` mount, and the app’s page cache are accounted into two cgroups
simultaneously, and a `MemoryHigh` throttles before the limit. Fix unit
delegation, mount propagation, and slice hierarchy so the workload runs
under the documented limit with deterministic memory pressure tests.

**Why agents fail:** Raises `MemoryMax`; misses delegation + mount namespace
interaction.

**T3 caveat:** one container, no privileged host access, ~8 GB of memory to
play with. The slice hierarchy and the memory-pressure workload both have to be
synthesized inside the task image, and the pressure assertions have to be
deterministic rather than load-dependent.

---

## 3. Bazel non-hermetic genrule poisons remote cache

**Category:** `Software` / `Systems`
**Target tier:** `advanced`

A Bazel workspace builds reproducibly on first invocation but **subsequent
`bazel build` invocations produce different binaries** from the remote cache
because a `genrule` reads `$BUILD_TIMESTAMP` and a tool path leaks from the
host PATH. Fix `exec_properties`, `srcs`/`tools` declarations, and stamping
so cache hits are byte-identical across two fresh workspaces.

**Why agents fail:** Disables remote cache; doesn’t make the rule hermetic.

**T3 caveat:** the toolchain and every external dependency must be baked into
the image, and the "remote" cache has to be a local on-disk cache — new
multi-container tasks are not allowed. Watch the ~10 GB storage ceiling.

---

## 4. Arrow IPC dictionary delta reordering

**Category:** `Software` / `Data engineering`
**Target tier:** `frontier`

A columnar pipeline writes Arrow IPC streams with **dictionary delta batches**
across multiple shards. Concatenation works for the first reader; a second
reader sees **wrong string values** because delta dictionaries are merged
out of order and a dictionary `id` collides across shards. Fix encoder
state, merge logic, and round-trip equality without rewriting the input.

**Why agents fail:** Re-encodes as plain UTF8 (loses delta semantics) or
sorts batches by row count instead of dictionary lineage.

---

## 5. TUF root rotation rejects valid metadata

**Category:** `Security` / `Cryptography`
**Target tier:** `frontier`

A local TUF (The Update Framework) client verifies releases correctly until a
**root key rotation** is performed offline; afterwards the client accepts a
stale targets file because threshold counting reuses the old role
specification, and a delegated role is verified against the new root before
its chain is rotated. Fix verification order, threshold scoping, and
rollback protection so old + new clients reach the same head.

**Why agents fail:** Bumps thresholds; doesn’t implement N-of-M crossover
correctly across consecutive root versions.

---

## 6. epoll ET + TLS 1.3 half-close deadlock

**Category:** `Software` / `Systems`
**Target tier:** `frontier`

A small C/Go reverse proxy passes smoke tests but **hangs under load** when a
TLS 1.3 client issues a `close_notify` mid-stream. epoll edge-triggered mode
misses a level-style readiness because the userland buffer wasn’t drained
to `EAGAIN` and `SSL_read` returned `WANT_READ` while the socket already
held more data. Fix readiness loop, OpenSSL/BoringSSL state handling, and
shutdown sequencing without disabling ET.

**Why agents fail:** Switches to level-triggered (regresses throughput);
adds spurious `epoll_wait` timeouts.

**T3 caveat:** "hangs under load" is not a deterministic outcome. The
`close_notify` interleaving has to be driven by a scripted client on a fixed
schedule so the deadlock reproduces every run on ~2 CPU cores.

---

## 7. KV cache reuse boundary-token corruption

**Category:** `ML` / `Inference`
**Target tier:** `frontier`

An inference server reuses KV cache across requests that share a long prefix.
Outputs match a no-cache baseline for prefixes ending on a word boundary
but **diverge at the next token** when the prefix ends mid-tokenizer-merge.
Position IDs and RoPE base for the seam token are recomputed from the wrong
offset. Fix prefix matching at the **token granularity** (not character),
position embedding seam, and attention mask so cached and uncached
generation agree on a deterministic toy model.

**Why agents fail:** Matches prefixes on raw strings; patches sampling
temperature instead of attention seam.

**T3 caveat:** no GPU. The toy model, the tokenizer, and the cached-vs-uncached
comparison all have to run on ~2 CPU cores with greedy decoding, so the
divergence is exact rather than sampled.

---

## 8. 7-bag tetromino randomizer leaks via hold

**Category:** `Software` / `Algorithms`
**Target tier:** `advanced`

A terminal Tetris implementation uses a 7-bag randomizer with a fixed seed,
but invoking **hold** during the last piece of a bag re-seeds the next bag
from `time(NULL)`, producing biased distributions visible only over many
games. Fix seed plumbing, hold semantics, and bag boundary so a seeded run
produces identical sequences across **with-hold and without-hold inputs**,
verified statistically over hidden seeds.

**Why agents fail:** Fixes the visible per-game ordering; misses cross-bag
seed contamination that only shows up in chi-square invariants.

**T3 caveat:** the statistical check must run over a fixed set of hidden seeds,
never a sampled one, so the verdict is identical on every run.

---

## 9. Raft log truncation reorders committed indices

**Category:** `Software` / `Systems`
**Target tier:** `frontier`

A small in-process Raft demo elects leaders and replicates entries; on a
**leader change after a prefix conflict**, the new leader truncates a
follower’s log but the snapshot index isn’t advanced atomically with the
log header, so a subsequent restart **re-applies already-committed
entries** to the state machine. Fix snapshot/log atomicity, term checks on
truncation, and apply-index persistence; verify with kill/restart + linearizability
checks across hidden histories.

**Why agents fail:** Adds an fsync; doesn’t fix the apply-index vs
snapshot-index ordering.

---

## 10. rsync filter rules delete included nested paths

**Category:** `Software` / `Systems`
**Target tier:** `advanced`

A nightly backup uses `rsync -a --delete-after` with a `.rsync-filter` file. On
shallow trees it works; on a tree with **nested include patterns and
per-directory filters**, `--delete-after` removes files that the include
list explicitly preserves because filter merging order differs between the
sender and receiver. Fix filter file location, `-F` semantics, and rule
ordering so the documented include set survives a destructive sync, with
hidden tests across multiple directory shapes.

**Why agents fail:** Drops `--delete`; adds blanket excludes that leak
unrelated files into the backup.

---

## 11. ReplacingMergeTree FINAL inconsistency with TTL

**Category:** `Software` / `Databases`
**Target tier:** `advanced`

A ClickHouse table uses `ReplacingMergeTree(version)` with a row-level `TTL`
column. Queries with `FINAL` return correct rows immediately after insert,
but after the background merge runs **rows reappear or disappear** because
TTL expressions are evaluated against the unmerged part and the version
column lives outside the ORDER BY key. Fix table DDL, version semantics,
and a deterministic `OPTIMIZE`/`SYSTEM STOP MERGES` test path so FINAL and
post-merge results agree.

**Why agents fail:** Adds `SETTINGS final=1`; doesn’t restructure ORDER BY
and TTL interaction.

---

## 12. Long-spec parser with hidden shift/reduce rule

**Category:** `Software` / `Languages`
**Target tier:** `advanced`

A 60k+ token specification for a small DSL describes a parser; the provided
implementation accepts the happy-path grammar but **misparses one
construct** (e.g., trailing-comma in a typed tuple) because a single
sentence buried in the spec changes operator associativity. Agent must
reconcile spec + lexer + parser + AST printer so a hidden corpus of
spec-conformant inputs round-trips.

**Why agents fail:** Greps for keywords; misses the semantic rule that
requires reading the section in full.

---

## 13. gRPC server-streaming drops tail on half-close

**Category:** `Software` / `Systems`
**Target tier:** `advanced`

A local gRPC service streams results to the client; under specific flow
control conditions (client sends `WINDOW_UPDATE` while issuing half-close),
the **final message is dropped** before the trailers, but the client sees
`OK` status. Fix server-side stream completion ordering, HTTP/2 window
accounting, and per-RPC backpressure so all sent messages are observed by
deterministic in-process clients.

**Why agents fail:** Adds a sleep before `SendTrailers`; doesn’t fix the
flow-control race.

**T3 caveat:** a flow-control race only counts if it is forced. The
`WINDOW_UPDATE`/half-close interleaving has to come from a scripted in-process
client so the dropped tail reproduces on every run.

---

## 14. Virtualized drag-drop recycles wrong row IDs

**Category:** `Software` / `Frontend`
**Target tier:** `advanced`

A Playwright-tested table supports drag-drop reordering with row
virtualization. Visual order is correct, but the **persisted model and URL
query string** end up with swapped IDs because the drag handler reads the
DOM `dataset.id` of the recycled node, not the data model under the
viewport offset. Fix the drag source/target binding, virtualization key
strategy, and URL sync; tests assert visible + persisted + accessible-name
agreement.

**Why agents fail:** Adds `key={index}`; appears to fix visuals but breaks
persistence and screen-reader announcements.

**T3 caveat:** Playwright runs agent-side. The verifier sits in a separate
container, so the visible order, the persisted model, the URL query, and the
accessible names all have to be dumped into declared `artifacts`.

---

## 15. AppArmor profile + capability bounding mismatch

**Category:** `Software` / `Systems`
**Target tier:** `advanced`

A service runs fine outside containers but **execs a helper binary that fails
with `EPERM`** only when launched under the provided AppArmor profile inside
a rootless container. The profile allows the binary path but the capability
bounding set drops `CAP_SETUID` mid-exec, and the helper drops privileges
via `setresuid` after a fork. Fix profile, capability inheritance, and
launcher sequencing so the helper completes its workflow without disabling
confinement.

**Why agents fail:** Loosens the profile to `complain` mode; doesn’t fix
capability inheritance.

**T3 caveat:** loading an LSM profile needs host privileges the task container
does not have. Redesign around what an unprivileged single container can
actually enforce — capability bounding sets, `no_new_privs`, seccomp — or drop
the idea.

---

## 16. Time-zone-aware cron with leap second skip

**Category:** `Software` / `Systems`
**Target tier:** `advanced`

A small in-process job scheduler honors per-job IANA timezones and DST.
Tests pass for fixed offsets but **a job at `02:30 America/Santiago` is
double-scheduled on spring-forward and skipped on fall-back**, and a
midnight UTC job near a **historical leap-second** boundary fires twice
because the next-fire computation uses wall-clock arithmetic on a monotonic
base. Fix next-fire computation, persistence of last-fire in UTC, and
recovery after restart across DST + leap-second hidden fixtures.

**Why agents fail:** Switches to UTC everywhere (regresses local schedule
semantics) or special-cases one timezone.

---

## Category balance (Batch 2)

| Category / Subcategory | Count |
|------------------------|------:|
| `Science` / `Physics` | 1 |
| `Software` / `Systems` | 8 |
| `Software` / `Algorithms` | 1 |
| `Software` / `Databases` | 1 |
| `Software` / `Data engineering` | 1 |
| `Software` / `Frontend` | 1 |
| `Software` / `Languages` | 1 |
| `ML` / `Inference` | 1 |
| `Security` / `Cryptography` | 1 |

**Target tiers:** `frontier` (6), `advanced` (10). Both figures are aims, not
results.

`Software` / `Systems` is doing heavy lifting in this batch. When a seed here
is promoted, re-ask what the agent actually has to understand — a kernel
readiness protocol, a consensus log, and a backup tool are not the same domain,
and one of them may belong somewhere else entirely.

---

## Non-overlap with Batch 1

Batch 1 covered: ODE event-detection restart, DKIM MIME canonicalization,
Nix vendorHash, watermark/DST dedup, PKCE redirect, WASM hot-reload,
projection rebuild, PDF CMap, triplet-mining EMA, GeoJSON shared-boundary,
virtual list selection, GraphQL DataLoader, Go superko, partial unique
index upsert, Cap’n Proto attenuation, roguelike FOV.

Batch 2 deliberately targets **different root-cause families**: spectral
basis selection, cgroup delegation, hermeticity, columnar dictionary state,
trust-root rotation, kernel/TLS readiness state, attention-cache seams,
PRNG seed plumbing, Raft snapshot/log atomicity, rsync filter merging,
ClickHouse merge semantics, long-spec semantic compliance, HTTP/2 flow
control, virtualization key strategy, capability inheritance, and
DST/leap-second next-fire computation.

---

## Hardening checklist (when promoting any of the above)

- **Fresh vs resumed / clean vs interrupted** verification paths.
- Multiple log locations with **misleading symptoms** (e.g., `OK` status
  while data is dropped).
- **Property/invariant** tests (conservation, idempotency, linearizability,
  cache-vs-no-cache equivalence, byte-identical reproducibility).
- **Anti-cheat**: derive expected outputs from inputs + rules, with hidden
  seeds/inputs; reject solutions that hardcode visible fixtures.
- **Network is a per-task decision**: `network_mode` defaults to `"public"`;
  choose `"no-network"` when the idea should not have internet, and then every
  dependency the oracle needs must already be in the image. Either way the
  outcome has to be deterministic, so services, registries, and key
  infrastructure normally run locally.
- **Verifier reach**: everything the tests read must be a path in the top-level
  `artifacts` array — the verifier runs in its own container and sees nothing
  else of the agent's filesystem.

---

## Idea review template

When promoting any idea here to a full task spec, use the Step 2a spec format in
[idea-validation.mdc](../.cursor/rules/idea-validation.mdc), judged against
[what-makes-a-good-task.md](./upstream/03-understanding-tasks/009-what-makes-a-good-task.md).
