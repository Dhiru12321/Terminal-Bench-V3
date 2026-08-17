# Hard Task Ideas (Project Terminus)

Seed bank for Terminus 3 idea generation, mined against [what-makes-a-good-task.md](./upstream/03-understanding-tasks/009-what-makes-a-good-task.md) and [idea-validation.mdc](../.cursor/rules/idea-validation.mdc). Nothing here has been through Step 2a.

Each entry aims at the Terminus 3 bar: understand a specialized domain, manipulate the right system inside it, and produce a result that satisfies several interacting constraints at once. Multi-file discovery and a long command chain are what that work usually looks like, not the target — step count only rules out trivially short tasks.

**The tier on each entry is a target, not a measurement.** Difficulty is empirical — average pass@1 over 8 runs, 4 each on GPT-5.6 and Claude Opus 5 — with `frontier` under 20%, `advanced` 20–<50%, `core` 50–<80%, and `base` 80–<100%. A tier becomes real only once the platform measures it. A high pass rate is not a rejection reason: `base` is a deliberate tier, and only 100% averaged across both models is unacceptable. Tiers are language-independent.

The platform envelope holds for every entry: no GPU (~2 CPU cores, ~8 GB memory, ~10 GB storage), a single container, no milestone or staged grading, deterministic outcomes, `[agent].timeout_sec` between 1800s and 18000s, and a verifier that runs in its own container reading only the paths declared in the top-level `artifacts` array. `network_mode` is `"public"` by default; `"no-network"` is a per-idea choice, not a house rule.

---

## 1. Event-detection ODE restart drift

**Category:** `Science` / `Physics`  
**Target tier:** `frontier`

A SciPy/NumPy adaptive RK pipeline integrates stiff ODEs with **root-finding event detection** (zero crossings). Clean runs match reference; **checkpoint resume** after a detected event integrates with the wrong effective time because event timestamps live outside the persisted state vector. Fix checkpoint format and restore order so trajectories and event lists match a non-interrupted run on non-uniform timesteps and rectangular vs square grids.

**Why agents fail:** Confuses integrator tolerance with event-location state; fixes symptoms in the stepper only.

---

## 2. MIME-boundary DKIM signing gap

**Category:** `Security` / `Cryptography`  
**Target tier:** `advanced`

A local Postfix + OpenDKIM (or similar) stack delivers mail in tests, but **DKIM verification fails** only for messages whose HTML/text parts are split across MIME boundaries or use `quoted-printable` soft breaks. Agent must trace milter config, canonicalization, and body hashing—not just “restart postfix.”

**Why agents fail:** Assumes one-part messages; misattributes failures to DNS/keys when canonicalization is wrong.

---

## 3. Nix fixed-output hash on normalized vendor tree

**Category:** `Software` / `Systems`  
**Target tier:** `frontier`

A flake builds in CI but **`nix build` fails** on `vendorHash` / FOD mismatch: vendor script normalizes timestamps and line endings differently than the hash was computed against, and a secondary crate/vendor path is included in one target but not another. Fix fetch/normalize script and lock inputs so reproducible builds and runtime tests see the same artifact.

**Why agents fail:** Patches hash in lockfile without fixing normalization; only fixes one package manager layer.

**T3 caveat:** the vendor tree and every fetched input must be baked into the image. A fixed-output derivation that reaches the network at build time makes the outcome non-deterministic, which no `network_mode` setting rescues.

---

## 4. Watermark-skewed stream deduplication

**Category:** `Software` / `Data engineering`  
**Target tier:** `advanced`

A local SQL/stream processor dedupes events with **event-time watermarks** and session windows. Unit tests pass; integration fails because late events, **DST boundary**, and mixed `Z` vs offset timestamps shift windows—double-counting or dropping valid late arrivals. Fix watermark logic and parsing, not static expected CSVs.

**Why agents fail:** Uses processing-time; hardcodes window boundaries visible in one fixture.

---

## 5. PKCE redirect normalization bypass

**Category:** `Security` / `AppSec`  
**Target tier:** `advanced`

A local OAuth2 mock authorizes normal clients but allows **token exchange** when `redirect_uri` differs by Unicode normalization, trailing dot segments, or case—while the authorization step appeared strict. Fix URI normalization and session binding consistently across authorize, callback, and token routes.

**Why agents fail:** Patches one endpoint; breaks valid multi-tenant redirect lists.

---

## 6. WASM plugin hot-reload use-after-host-cache

**Category:** `Software` / `Systems`  
**Target tier:** `advanced`

A small WASM plugin host passes tests on cold start; **hot reload** of the same module name causes intermittent segfaults or wrong outputs because the host caches guest memory base pointers across instance teardown. Fix lifecycle, instance isolation, and reload ordering.

**Why agents fail:** Disables reload instead of fixing cache invalidation; only reproduces on second load.

**T3 caveat:** an intermittent segfault is not a verifiable outcome. The reload ordering has to be forced deterministically (single-threaded driver, fixed reload sequence) before this becomes a task.

---

## 7. Projection rebuild vs compaction tombstones

**Category:** `Software` / `Databases`  
**Target tier:** `frontier`

An event-sourced service ships a **50k+ token internal spec** on projection rules. Fresh DB tests pass; rebuilding from a compacted event log **duplicates or drops** rows when tombstones interact with idempotent handlers and out-of-order consumer retries. Agent must reconcile spec + code + migration, not keyword-search one rule.

**Why agents fail:** Implements happy-path projector; ignores compaction + idempotency interaction.

---

## 8. PDF linearization breaks CMap subset tags

**Category:** `Software` / `Data engineering`  
**Target tier:** `advanced`

A `qpdf`/Ghostscript pipeline linearizes PDFs for fast web view; simple files pass, but **embedded CJK subset fonts** lose correct ToUnicode/CMap linkage and text extraction order breaks. Fix pipeline flags and rewrite steps so structure, linearization, and extracted text match references.

**Why agents fail:** Checks file size only; doesn’t validate text layer or font objects.

---

## 9. Triplet-mining uses stale EMA embeddings after resume

**Category:** `ML` / `Training`  
**Target tier:** `advanced`

A small metric-learning trainer on a **deterministic toy dataset** reports good loss from step 0 after resume, but retrieval metrics collapse because triplet mining reads **EMA shadow weights** that checkpoint restore does not sync with the training weights. Fix checkpoint contents and mining source so batch-1 and resumed runs agree.

**Why agents fail:** Restores model only; doesn’t notice mining uses a second parameter set.

**T3 caveat:** no GPU. The trainer, the dataset, and the resumed run all have to finish on ~2 CPU cores inside the agent timeout.

---

## 10. GeoJSON shared-boundary double counting

**Category:** `Software` / `Algorithms`  
**Target tier:** `advanced`

A spatial join pipeline aggregates area/population for regions. Simple disjoint polygons work; **adjacent polygons with shared edges and mixed ring orientation** double-count border populations. Fix topology normalization (orientation, validity) before join, with deterministic output ordering.

**Why agents fail:** Bounding-box shortcut; flips orientation globally and breaks holes/islands.

---

## 11. Variable-height virtual list selection desync

**Category:** `Software` / `Frontend`  
**Target tier:** `advanced`

A terminal or Playwright-tested dashboard uses **virtualized lists with variable row heights**. Filtering or sorting restores scroll position but **selection and “focused row” state** point at the wrong entity because measured heights cache is stale across data updates. Fix measurement cache invalidation and URL/query sync.

**Why agents fail:** Fixes visual scroll only; doesn’t test selection model or keyboard nav.

**T3 caveat:** the browser drive runs agent-side. The verifier cannot reach the live page, so the interaction trace, selection model, and URL state have to be written out as declared `artifacts` for it to read.

---

## 12. GraphQL DataLoader context-blind cache keys

**Category:** `Software` / `Systems`  
**Target tier:** `advanced`

A local GraphQL server fixes obvious N+1 with DataLoader, but **tenant-scoped fields leak** across requests in integration tests because loader cache keys omit auth context/locale. Resolver-level auth looks correct; batching layer is wrong.

**Why agents fail:** Disables batching; adds per-field queries that hide the bug in unit tests.

---

## 13. Superko misclassified in seki with passes

**Category:** `Software` / `Algorithms`  
**Target tier:** `advanced`

A terminal Go (Weiqi) engine passes basic capture tests but **allows illegal repeats** in seki with shared liberties after passes, or rejects legal moves. Fix ko/superko state machine and liberty counting, verified across seeded boards—not a single puzzle answer.

**Why agents fail:** Implements simple ko only; fails on pass/seki interaction.

---

## 14. Partial unique index upsert wrong conflict target

**Category:** `Software` / `Databases`  
**Target tier:** `advanced`

PostgreSQL/SQLite migrations add a **partial unique index** for soft-deleted rows. `INSERT ... ON CONFLICT` appears to work on empty DB but on legacy snapshots **updates the wrong row** or violates an invisible constraint because conflict target doesn’t match partial predicate. Fix migrations and upsert SQL for fresh + legacy DBs.

**Why agents fail:** Drops partial index; fixes only fresh schema path.

---

## 15. Cap’n Proto capability attenuation leak

**Category:** `Security` / `AppSec`  
**Target tier:** `frontier`

A local RPC demo attenuates capabilities for untrusted clients. Direct calls are blocked, but **re-exporting a nested capability** restores full rights on one code path. Fix attenuation wrappers and import tables; tests include allowed vs denied operations without real network.

**Why agents fail:** Blocks at top-level proxy only; misses nested promise/broker paths.

---

## 16. Roguelike FOV invalidation after undo

**Category:** `Software` / `Algorithms`  
**Target tier:** `advanced`

A terminal roguelike’s **line-of-sight** is correct on forward moves but wrong after undo/redo when diagonal doors toggle: visibility cache keys on tile coordinates, not logical map generation order. Fix invalidation and deterministic seeds across move/undo sequences.

**Why agents fail:** Recomputes FOV every frame globally (slow) or only on player move forward.

---

## Category balance

| Category / Subcategory | Count |
|------------------------|------:|
| `Science` / `Physics` | 1 |
| `Software` / `Algorithms` | 3 |
| `Software` / `Systems` | 3 |
| `Software` / `Databases` | 2 |
| `Software` / `Data engineering` | 2 |
| `Software` / `Frontend` | 1 |
| `ML` / `Training` | 1 |
| `Security` / `AppSec` | 2 |
| `Security` / `Cryptography` | 1 |

**Target tiers:** `frontier` (4), `advanced` (12). Both figures are aims, not results.

---

## Hardening checklist (when authoring)

- Multiple log locations with **misleading symptoms** (symptom layer ≠ root cause).
- **Fresh vs legacy** or **clean vs resumed** verification paths.
- Property/invariant tests (conservation, idempotency, auth deny/allow pairs).
- Anti-cheat: derive expected outputs from inputs + rules, not committed golden files alone.
- Everything the tests read must be a path in the top-level `artifacts` array; the verifier runs in a separate container and sees nothing else.

---

## Idea review template

When promoting an idea to a full task spec, use the Step 2a spec format in [idea-validation.mdc](../.cursor/rules/idea-validation.mdc), judged against [what-makes-a-good-task.md](./upstream/03-understanding-tasks/009-what-makes-a-good-task.md).
