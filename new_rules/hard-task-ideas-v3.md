# Hard Task Ideas — Batch 3 (Project Terminus)

Seed bank for Terminus 3 idea generation, mined against
[what-makes-a-good-task.md](./upstream/03-understanding-tasks/009-what-makes-a-good-task.md)
and [idea-validation.mdc](../.cursor/rules/idea-validation.mdc). Complements
[hard-task-ideas.md](./hard-task-ideas.md) and
[hard-task-ideas-v2.md](./hard-task-ideas-v2.md) with **non-overlapping** ideas.
Nothing here has been through Step 2a.

Scope for this batch (by request): numerical solvers and simulation,
operating-system and service internals, security, and diagnosis. Those four
groupings organize the reading order only — each entry carries its own
Terminus 3 `Category` / `Subcategory` pair, and they do not line up one-to-one.

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

## Numerical solvers and simulation

### 1. GMRES(m) restart loses convergence via Gram–Schmidt breakdown

**Category:** `Software` / `Algorithms`
**Target tier:** `frontier`

A restarted GMRES(m) solver converges on well-conditioned systems but
**stagnates or returns a wrong residual** on an ill-conditioned, non-symmetric
matrix because the Arnoldi step uses **classical Gram–Schmidt** without
reorthogonalization, the Hessenberg `H` loses orthogonality in the restart
seam, and a **happy-breakdown** (`h[j+1,j] ≈ 0`) is treated as failure instead
of exact convergence. Fix orthogonalization (MGS or CGS2), restart-vector
carry-over, and breakdown handling so the **true residual** (`b - A x`, not the
recurrence residual) matches a dense reference to tolerance across multiple
seeds and restart lengths `m`.

**Why agents fail:** Tightens `rtol` or raises `maxiter`; treats the cheap
recurrence residual as ground truth and never recomputes the true residual.

---

### 2. AMR coarse–fine flux mismatch breaks conservation

**Category:** `Science` / `Physics`
**Target tier:** `frontier`

A block-structured **adaptive mesh refinement** advection/diffusion solver
conserves the integrated quantity on a single uniform level but **leaks mass at
refinement boundaries** because the coarse cell adjacent to a fine patch is not
**reflux-corrected**: the coarse flux is used instead of the time- and
space-averaged fine fluxes across the interface, and ghost-cell fills read
pre-update neighbor data. Fix the reflux register, the fine→coarse flux
averaging, and the update ordering so total mass is conserved to round-off
across a refine/derefine sequence on **non-square domains**.

**Why agents fail:** Patches ghost-cell interpolation only; never implements
the flux register, so conservation still drifts at every interface.

---

### 3. Nosé–Hoover thermostat invariant drifts on bad operator split

**Category:** `Science` / `Physics`
**Target tier:** `frontier`

A molecular-dynamics integrator conserves energy under plain velocity-Verlet,
but with a **Nosé–Hoover chain** thermostat the **conserved extended-system
Hamiltonian drifts** because the thermostat half-steps are applied in the wrong
order relative to the force update (no symmetric Trotter splitting), and the
chain’s coupling masses are recomputed each step from a stale temperature. Fix
the operator-splitting order, chain update, and restart of the thermostat
variables so the extended invariant is flat (to tolerance) on clean **and**
checkpoint-resumed runs.

**Why agents fail:** Lowers the timestep to hide drift; fixes kinetic energy
but not the symmetric split, so the invariant still trends over long runs.

---

### 4. FFT convolution circular wraparound corrupts deconvolution

**Category:** `Software` / `Algorithms`
**Target tier:** `advanced`

A signal pipeline computes convolution/deconvolution via FFT. It matches a
direct reference for short kernels but **corrupts the head and tail of the
output** for kernels comparable to the signal length because the transform
length is not zero-padded to at least `N+M-1` (circular vs **linear**
convolution), and the Wiener deconvolution branch divides by spectral bins near
zero without regularization, amplifying noise into NaNs. Fix padding length,
normalization, and the regularized inverse so linear-convolution and
deconvolution round-trip a hidden battery of signals.

**Why agents fail:** Adds `np.real(...)` to suppress imaginary residue and
clamps NaNs, masking the wraparound instead of fixing the transform length.

---

## Operating-system and service internals

### 5. systemd socket activation passes the wrong file descriptor

**Category:** `Software` / `Systems`
**Target tier:** `advanced`

A socket-activated service has two `.socket` units (a public stream socket and
an internal admin socket). The service starts but **answers admin commands on
the public port** because it iterates `LISTEN_FDS` by index instead of matching
`FileDescriptorName` via `LISTEN_FDNAMES`, the `.socket` units lack
`FileDescriptorName=`, and `Accept=yes` vs `Accept=no` semantics are mixed so
the fd count is off by one. Fix the socket units, the `sd_listen_fds_with_names`
lookup, and start ordering so each listener binds the intended role under a
non-root `User=`.

**Why agents fail:** Hardcodes `fd == 3`; works in isolation but breaks when
socket start order or count changes in the hidden tests.

**T3 caveat:** the task container has no init system running the `.socket`
units. The activation protocol (`LISTEN_FDS`, `LISTEN_FDNAMES`, fd inheritance)
has to be driven by a harness inside the single container, and whatever the
verifier checks has to land in declared `artifacts`.

---

### 6. cpuset/quota-unaware thread pool oversubscribes under cgroup limits

**Category:** `Software` / `Systems`
**Target tier:** `advanced`

A worker runs fine on the host but **thrashes and misses its deadline inside a
CPU-restricted cgroup** because the pool sizes itself from
`os.cpu_count()`/`nproc` (host count) rather than the effective allowance from
`cpu.max` (quota/period) and `cpuset.cpus.effective`. It also pins threads with
`sched_setaffinity` to CPUs outside the assigned cpuset, which silently fails.
Fix the parallelism computation, affinity handling, and a `MADV`/poll loop so
the service respects both **quota-based** and **cpuset-based** limits with
deterministic throughput assertions.

**Why agents fail:** Reads only `cpu.max` (quota) and ignores
`cpuset.cpus.effective`, or vice versa, so one of the two limit modes regresses.

**T3 caveat:** the container has about 2 CPU cores, so a real host/cgroup
mismatch barely exists. The limit surfaces have to be presented as fixtures the
pool reads, and the assertions have to be on the computed parallelism and
affinity decisions rather than on measured throughput, which is not
deterministic.

---

### 7. logrotate copytruncate races a daemon that never reopens

**Category:** `Software` / `Systems`
**Target tier:** `advanced`

Nightly log rotation appears to work, but **log lines are silently lost and
disk never frees** because the config uses `copytruncate` while the daemon holds
the original inode and keeps writing at the old offset (sparse-file growth),
the `postrotate` `SIGHUP` is sent to a **stale PID** from a wrong `PIDFile`, and
`create` mode conflicts with the daemon’s own `O_APPEND` reopen. Fix the
logrotate stanza (drop `copytruncate` for reopen-on-`HUP`), the PID/signaling
path, and ownership/permissions so rotation is lossless and idempotent across
repeated runs with a running writer.

**Why agents fail:** Adds `compress`/`delaycompress` cosmetics; never resolves
the open-fd vs truncate race, so lines keep dropping under load.

**T3 caveat:** "under load" cannot decide the verdict. The writer has to emit a
fixed, countable line sequence and the rotation has to be triggered at fixed
points in it, so the same lines are lost on every unfixed run.

---

### 8. Asymmetric routing + rp_filter drops second-NIC replies

**Category:** `Software` / `Systems`
**Target tier:** `advanced`

A host with two interfaces serves a local service that is reachable on NIC A but
**times out on NIC B** for replies, even though packets arrive. Source-based
**policy routing** tables exist but the `ip rule` priorities and `fwmark`
tagging are wrong, so replies egress NIC A; strict **reverse-path filtering**
(`rp_filter=1`) then drops the asymmetric path. Fix the routing tables, rule
priorities/marks (or set `rp_filter=2` loose mode with justification), and the
per-interface sysctls so both NICs complete request/response, verified entirely
with local network namespaces (no external network).

**Why agents fail:** Blanket-disables `rp_filter` globally (security regression
+ breaks the hidden anti-spoof test) instead of fixing the routing asymmetry.

**T3 caveat:** both NICs and both namespaces live in one container, which needs
`NET_ADMIN` — confirm the platform grants it before committing to this shape.
Keeping the topology local is a `network_mode = "no-network"` decision for this
idea, not a rule the other entries inherit.

---

## Security

### 9. JWT RS256/HS256 algorithm-confusion key reuse

**Category:** `Security` / `AppSec`
**Target tier:** `advanced`

A local API issues RS256 JWTs and verifies them, but the verifier **trusts the
token’s `alg` header** and, when `alg=HS256`, validates the signature using the
**RSA public key as the HMAC secret** — letting an attacker forge admin tokens
from public material. A secondary path also accepts `alg=none` when the claims
parse cleanly. Fix algorithm pinning (verify against an allow-list, never the
header), key-type binding, and claim validation so forged HS256/none tokens are
rejected while legitimate RS256 tokens still pass.

**Why agents fail:** Adds an `alg=none` guard only; leaves the RS256↔HS256 key
confusion exploitable on the secondary verify path.

---

### 10. SHA-256 `H(secret‖msg)` MAC is length-extension forgeable

**Category:** `Security` / `Cryptography`
**Target tier:** `advanced`

A request-signing scheme authenticates payloads with a raw
`SHA256(secret || message)` tag. Valid clients pass, but an attacker can
**append data and compute a valid tag without the secret** via a Merkle–Damgård
**length-extension** attack, and the comparison uses early-return `==` (timing
oracle). Fix the construction to HMAC-SHA256 (or SHA-256 with a keyed,
length-bound scheme), use constant-time comparison, and bind message length, so
extension-forged requests are rejected while genuine requests still verify.

**Why agents fail:** Adds a length field to the message but keeps the
`H(secret‖…)` construction, so a recomputed extension with the new length still
forges a valid tag.

---

### 11. AES-GCM counter nonce reuse after process restart

**Category:** `Security` / `Cryptography`
**Target tier:** `advanced`

A file-encryption CLI uses AES-GCM with a **per-message counter nonce** seeded
in memory. Within one process it is unique, but **after a restart the counter
resets to zero**, reusing `(key, nonce)` pairs — catastrophic for GCM
(authentication-key recovery / keystream reuse). A second bug truncates the
96-bit nonce when the counter exceeds `2^32`. Fix nonce derivation/persistence
(random or persisted monotone counter with rollover protection) and refuse to
encrypt on exhaustion, so a hidden test that encrypts across simulated restarts
finds **zero nonce collisions** and all ciphertexts authenticate.

**Why agents fail:** Persists the counter but still wraps at 32 bits, or
switches to random nonces without rejecting the birthday-bound exhaustion case.

---

### 12. SAML assertion accepted via XML signature wrapping

**Category:** `Security` / `AppSec`
**Target tier:** `frontier`

A local SAML service provider validates signed assertions correctly for normal
responses but **accepts a forged identity** when the attacker wraps the original
signed assertion and injects a second, unsigned assertion that the application
logic reads (signature checked on element A, claims read from element B —
classic **XSW**). The reference resolution uses `ID` lookup that returns the
wrong node, and `xmlsec` is told to verify “any signature present.” Fix
canonicalization, signed-element pinning (verify and read the **same** node),
and schema/`ID` handling so wrapped responses are rejected and legitimate ones
still authenticate.

**Why agents fail:** Re-runs the signature check (which still passes on the
wrapped doc) without binding the validated node to the node whose claims are
consumed.

---

## Diagnosis and reproducibility

### 13. `make -j` intermittently fails on a missing prerequisite edge

**Category:** `Software` / `Systems`
**Target tier:** `advanced`

A C/codegen project builds cleanly with `make` but **fails intermittently under
`make -j`** because a generated header has no explicit prerequisite edge to the
rule that produces it, a pattern rule’s recipe writes its output
**non-atomically** (readers see a half-written file), and a shared `.d`
dependency file is regenerated in place during the same build. Fix the
dependency graph (order-only prerequisites, atomic `mv` of generated outputs,
correct `-MMD` include guards) so the build is correct and reproducible at
`-j1` through `-j$(nproc)` across repeated runs.

**Why agents fail:** “Fixes” it with `.NOTPARALLEL` or a global `make -j1`
wrapper, regressing build time and masking the missing edge the tests probe.

**T3 caveat:** an intermittent failure is not a verdict, and `$(nproc)` is
about 2 here. The missing edge has to be provable structurally — a forced
recipe ordering, a slow-generator stub, or a dependency-graph assertion — so
the same result appears on every run.

---

### 14. Non-async-signal-safe handler deadlocks under signals

**Category:** `Software` / `Systems`
**Target tier:** `advanced`

A daemon installs a `SIGTERM`/`SIGCHLD` handler that calls
**non-async-signal-safe** functions (`malloc`, `printf`, logging that takes a
mutex). It works in smoke tests but **deadlocks or corrupts the heap** when a
signal lands while the main thread holds the allocator/log lock. Fix it with the
**self-pipe trick** (or `signalfd`), `sigaction` with restart flags and a
blocked mask, and reaping `SIGCHLD` in a loop, so the service shuts down cleanly
and reaps all children under a hidden signal-storm test.

**Why agents fail:** Wraps the handler body in a mutex (worsens the deadlock) or
ignores `SIGCHLD` reaping, leaving zombies the test counts.

**T3 caveat:** a signal storm that only sometimes deadlocks measures nothing.
Deliver the signals on a fixed schedule against a driver that holds the
allocator lock deterministically, and assert on the recorded shutdown and reap
counts.

---

### 15. File-descriptor leak on the error path exhausts the process

**Category:** `Software` / `Systems`
**Target tier:** `advanced`

A connection/file-processing service runs for a while then **fails with
`EMFILE`/`Too many open files`** under a workload that exercises error
branches: sockets and temp files are closed only on the success path, an
exception between `open()` and the `finally` skips cleanup, and an
`epoll`/`inotify` watch descriptor is registered but never removed on
disconnect. Diagnose via `/proc/<pid>/fd` growth, fix the cleanup ordering
(context managers / `defer` / RAII) on **all** paths, and prove fd count is
bounded across a long hidden error-heavy run.

**Why agents fail:** Raises the `RLIMIT_NOFILE` ulimit to delay the crash
instead of closing descriptors on the failing branches; the leak test still
trends upward.

**T3 caveat:** the verifier cannot read `/proc/<pid>/fd` — it runs in a
separate container and only sees declared `artifacts`. The fd census has to be
sampled agent-side at fixed points in a fixed workload and written out as the
artifact the tests read.

---

### 16. Hash/locale-dependent nondeterminism breaks a checksum gate

**Category:** `Software` / `Data engineering`
**Target tier:** `advanced`

A pipeline emits a manifest whose checksum **changes between runs** and fails CI
only sometimes: a `set`/`dict` is serialized in iteration order
(`PYTHONHASHSEED` sensitivity), floats are formatted with the default locale so
`LC_NUMERIC=de_DE` writes `1,5` and a downstream parser reads `15`, and a
parallel `map` writes results in completion order. Fix deterministic ordering
(sorted keys), locale-independent numeric formatting, and stable reduce ordering
so the manifest is **byte-identical** across seeds, locales, and worker counts.

**Why agents fail:** Pins `PYTHONHASHSEED=0` in one entrypoint, leaving the
locale and parallel-ordering sources of nondeterminism that the hidden matrix
varies.

---

## Category balance (Batch 3)

| Category / Subcategory | Count |
|------------------------|------:|
| `Science` / `Physics` | 2 |
| `Software` / `Algorithms` | 2 |
| `Software` / `Systems` | 7 |
| `Software` / `Data engineering` | 1 |
| `Security` / `AppSec` | 2 |
| `Security` / `Cryptography` | 2 |

**Target tiers:** `frontier` (4), `advanced` (12). Both figures are aims, not
results.

The reading groups and the taxonomy do not agree, which is the point: a
restarted Krylov solver is an algorithms problem, an AMR reflux register is
physics, and a parallel-make race is systems even though all three arrived
here as "sci-comp" or "debugging". Re-derive the pair from the domain when a
seed is promoted.

---

## Non-overlap with Batches 1–2 and existing tasks

This batch deliberately avoids root-cause families already covered by existing
`tasks/` units and prior batches:

- **Sci-comp:** not FVM/heat conservation, not FFT-Poisson basis selection, not
  multigrid ghost cells, not Kalman/ODE event restart. New families: **Krylov
  reorthogonalization**, **AMR reflux**, **thermostat operator splitting**,
  **linear-vs-circular FFT convolution**.
- **Sysadmin:** not cgroup memory accounting, not mount propagation/namespaces,
  not AppArmor capabilities, not generic unit reload. New families: **socket
  activation fd naming**, **cpuset/quota-aware parallelism**, **logrotate
  open-fd race**, **policy routing + rp_filter asymmetry**.
- **Security:** not TUF rotation, not PKCE redirect, not JWT *audience*, not
  Cap'n Proto attenuation, not path-traversal symlinks. New families: **RS256↔
  HS256 alg confusion**, **length-extension MAC**, **GCM nonce reuse on
  restart**, **SAML XML signature wrapping**.
- **Debugging:** not epoll/TLS half-close, not async retry/cancel. New families:
  **parallel-make dependency race**, **async-signal-safety**, **fd leak on error
  path**, **hash/locale/parallel nondeterminism**.

---

## Hardening checklist (when promoting any of the above)

- **Clean vs resumed / single vs parallel / fresh vs restart** verification
  paths in every task.
- Multiple log locations with **misleading symptoms** (e.g. `OK` status while
  data is dropped; ulimit delaying a crash; recurrence residual hiding stalls).
- **Property/invariant** tests: conservation to round-off, flat extended
  invariant, true-residual tolerance, zero nonce collisions, bounded fd count,
  byte-identical manifests, deny/allow auth pairs.
- **Anti-cheat:** derive expected outputs from inputs + rules with hidden
  seeds/inputs/locales; reject solutions that hardcode visible fixtures, widen
  limits, or disable the safety mechanism the test probes.
- **Network is a per-task decision:** `network_mode` defaults to `"public"`;
  choose `"no-network"` when the idea should not have internet, and then every
  dependency the oracle needs must already be in the image. Determinism is the
  binding constraint, which is why services, sockets, and routing usually run
  locally anyway (network namespaces for the routing entry).
- **Verifier reach:** everything the tests read must be a path in the top-level
  `artifacts` array — the verifier runs in its own container and cannot inspect
  live processes, `/proc`, or anything else on the agent's filesystem.

---

## Idea review template

When promoting any idea here to a full task spec, use the Step 2a spec format in
[idea-validation.mdc](../.cursor/rules/idea-validation.mdc), judged against
[what-makes-a-good-task.md](./upstream/03-understanding-tasks/009-what-makes-a-good-task.md).
