# Option A Step-2a-ready Seed Bank

Screened against: `implementation-collapse-audit.md`, `chatgpt-task-authoring-playbook.md`, `terminal-bench-task-creation.md`, `TASK_PROPOSAL_RUBRIC.md`.

## Input summary

- Seed source: `web/bulk-seed-bank-opus-weak-150-target-option-b.md`
- Mode: `step2a-bank`
- Final target: `150`
- Total input candidates screened: `128`
- Ready kept as-is: `94`
- Refined in place: `34`
- Replaced (new local seeds to reach balance/size): `22`
- Final seeds surfaced: `150`
- Category distribution: `system-administration=38, security=38, debugging=37, scientific-computing=37`
- Evidence-basis distribution: `mixed Execution/Coherence/Verification per original bank; replacements add matching tags`
- Topology collisions removed or rewritten: `22 new replacement cards added for count/balance; 34 Option B repairable inputs labeled refined (manual symptom pass optional before Step 2a)`
- Notes on backfills / saturation: `Input had 128 parsed cards; added 22 distinct replacements to reach 150 with 38/38/37/37 balance. Debugging title with embedded backticks parsed via last-backtick rule.`

## Ranked seed bank

### Category: `system-administration`

#### 1. `Stale bind mount hides post-rotate journal`
- **Status**: `ready`
- **Source**: `Option B #1`
- **Topology**: `bind-mount + logrotate + inode identity`
- **Symptom**: `After a nightly log rotation, a service keeps emitting to a path that no longer reflects the file the aggregator tails, and restart “fixes” it until the next rotate.`
- **Discoveries**: `The active log path is a bind mount layered over a rotated inode that recycling reuses at different generations.; 'df'/'ls' agree on the pathname while 'ls -i' across namespaces disagrees silently.; A “healthy” inode count check stays green because it counts files, not mount graph edges.`
- **Evidence**: `trajectory=Coherence; command_level=edge-cases; cluster=Long-Horizon-Coherence`
- **Exploits**: `Exploit 1: Long-horizon choice of mount order makes the first write land on the pre-rotate target forever in one PID namespace.; Exploit 3: Premature green check sums file size on the host path, not the container’s merged view.`
- **Why hard**: `Reconstruction requires reconciling mount topology with inode identity, not rereading config.`
- **Main collapse risk**: `Task collapses if the instruction names “bind mount” as the fix rather than symptoms.`


#### 2. `Unit restarts stampede a state dir with flock races`
- **Status**: `ready`
- **Source**: `Option B #2`
- **Topology**: `systemd burst + flock + tmpfs layout`
- **Symptom**: `Intermittent startup failure only when several units come up together after a power blip; manual single-unit starts are clean.`
- **Discoveries**: `A generator unit and its consumer both take non-blocking locks on the same lockfile path with different assumptions about stale PID files.; 'systemctl status' shows 'active (running)' while a dependent unit logs “resource busy” in a circular buffer that rotates quickly.; Order differences appear only when inotify-driven reload races the initial batch.`
- **Evidence**: `trajectory=Execution; command_level=edge-cases; cluster=Complex-System-Builds`
- **Exploits**: `Exploit 2: Destructive recovery deletes the lock without stopping the unit that recreates it mid-compaction.; Exploit 5: A “ready” probe tests TCP reachability, not durable completion of the directory reconciliation job.`
- **Why hard**: `Coupling is timing-shaped across unit graphs, not a single misconfigured flag.`
- **Main collapse risk**: `Collapse to “use a proper service manager” without observable failure chain.`


#### 3. `Cgroup v2 subtree move leaves RSS accounting on wrong leaf`
- **Status**: `ready`
- **Source**: `Option B #3`
- **Topology**: `cgroup migration + controller attribution drift`
- **Symptom**: `Memory limits appear violated in dashboards while local 'ps' looks fine, and moving workloads between slices changes blame randomly.`
- **Discoveries**: `A slice move rewrites 'cgroup' membership but a delegated child keeps charging pages to the parent’s 'memory.stat' until the next allocation burst.; Two tools read different cgroup files ('memory.current' vs 'memory.stat' detail lines) that converge only after a manual kill -9 of a helper.; Health checks sample RSS at the wrong hierarchy depth after systemd reload.`
- **Evidence**: `trajectory=Verification; command_level=none; cluster=Robust-Verification`
- **Exploits**: `Exploit 1: Two authoritative surfaces disagree until a long-running allocator crosses a watermark.; Exploit 6: External monitor validates “within limit” using the parent slice file, not the leaf that executes the workload.`
- **Why hard**: `Requires reconciling migration semantics with accounting latency, not raising limits.`
- **Main collapse risk**: `Task becomes a cgroup trivia quiz with named tunables in the instruction.`


#### 4. `Device node minor churn breaks persistent BY-id mapping`
- **Status**: `ready`
- **Source**: `Option B #4`
- **Topology**: `udev reenumeration + persistent naming + hotplug`
- **Symptom**: `A backup volume sometimes mounts read-only after chassis maintenance without clear kernel errors, until a full power cycle.`
- **Discoveries**: `'/dev/disk/by-id' symlinks reorder when a controller reorders probe results after cable swap.; 'mount' succeeds using a UUID that maps to an old superblock generation cached in multipath state.; A pre-mount validator checks block size on a stale path opened before udev settle completed.`
- **Evidence**: `trajectory=Coherence; command_level=edge-cases; cluster=Long-Horizon-Coherence`
- **Exploits**: `Exploit 4: Early boot choice of canonical device id sticks through later hotplug that reshuffles minors.; Exploit 8: The migration script returns before udev queues drain, leaving a transient correct-looking path.`
- **Why hard**: `The failure is a naming indirection problem across time, not corruption.`
- **Main collapse risk**: `Over-specifying manufacturer-specific multipath quirks.`


#### 5. `ZFS snapshot send stream replays wrong bookmark lineage`
- **Status**: `ready`
- **Source**: `Option B #6`
- **Topology**: `incremental replication + bookmark drift + receive abort`
- **Symptom**: `Replication jobs succeed in logs but downstream datasets miss files without reporting hash mismatch on casual inspection.`
- **Discoveries**: `The receive side resumes from a bookmark that predates a recent rollback on the source without failing closed.; 'zfs list -t bookmark' ordering differs from creation intent after rename storms.; A wrapper script treats nonzero 'zfs receive' stderr as warning-only when rate-limited.`
- **Evidence**: `trajectory=Verification; command_level=not-waiting; cluster=Long-Horizon-Coherence`
- **Exploits**: `Exploit 3: Local “verify” counts files with 'find | wc' against the wrong snapshot name.; Exploit 8: Send finishes transmitting bytes before receive finishes applying, and automation polls the sender only.`
- **Why hard**: `Multi-source-of-truth across bookmark identity and snapshot names.`
- **Main collapse risk**: `Vendor-specific flags dominate unless symptoms stay filesystem-agnostic.`


#### 6. `systemd timer skew triggers prune before rotate completes`
- **Status**: `ready`
- **Source**: `Option B #7`
- **Topology**: `timer units + shared spool + non-atomic rename`
- **Symptom**: `A weekly archive sometimes references truncated payloads despite “successful” upstream jobs, correlated with DST transitions only on some hosts.`
- **Discoveries**: `Two timers fire in reversed order on hosts where RTC drift crosses a boundary during suspend/resume.; Prune uses inode mtime while rotate uses wall clock in unit metadata.; A 'ConditionACPower' false negative on laptops masks the causal order.`
- **Evidence**: `trajectory=Execution; command_level=edge-cases; cluster=Complex-System-Builds`
- **Exploits**: `Exploit 4: Early decision in timer scheduling affects which file rename wins under crash.; Exploit 5: “Success” email attaches the pre-rename inode size.`
- **Why hard**: `Couples calendar time, inode metadata, and unit conditions—not a single race window.`
- **Main collapse risk**: `Too much real-world clock trivia; keep evidence self-contained.`


#### 7. `Overlay upper corruption after failed live kernel patch rollout`
- **Status**: `ready`
- **Source**: `Option B #8`
- **Topology**: `overlayfs + transactional package hook + kpatch/kexec interaction`
- **Symptom**: `Containers on one node serve stale libraries after a rolling “safe” patch that the orchestration marks complete.`
- **Discoveries**: `Upper layer whiteouts persist while lower layer RPM/db thinks versions rolled forward.; 'rpm -V' passes inside the host but fails inside a user namespace mapping the same tree differently.; A health endpoint reads binaries through a bind that bypasses the intended overlay path.`
- **Evidence**: `trajectory=Coherence; command_level=none; cluster=Complex-System-Builds`
- **Exploits**: `Exploit 1: Different authoritative trees depending on namespace at read time.; Exploit 2: Rollback script removes upper workdir without flushing page cache for mmap’d deps.`
- **Why hard**: `Demands reconciling layered FS semantics with package truth, not “rebuild image.”`
- **Main collapse risk**: `Instruction leaks “overlay” as punchline too early.`


#### 8. `Network namespace tc qdisc change desyncs conntrack expectations`
- **Status**: `ready`
- **Source**: `Option B #10`
- **Topology**: `netns + tc + conntrack + NAT edge`
- **Symptom**: `Long-lived flows drop only when shaping policy updates mid-flight during brownouts; new flows are fine.`
- **Discoveries**: `Conntrack entries retain pre-timestamped expectations while qdisc parent handles change.; 'ss' shows 'ESTABLISHED' but RTT samples go zero in one direction on pacing change.; A canary TLS probe reuses a session ticket that masks TCP-level blackholing briefly.`
- **Evidence**: `trajectory=Coherence; command_level=edge-cases; cluster=Complex-System-Builds`
- **Exploits**: `Exploit 4: Early tc apply order commits a hash bucket layout that later pacing assumes unchanged.; Exploit 7: Two remediation scripts each valid alone but invalidate the other’s assumed skb path.`
- **Why hard**: `Requires stitching stateful firewall semantics with queue discipline transitions.`
- **Main collapse risk**: `Overfits one kernel minor without observable counters.`


#### 9. `Tmpfs OOM killer targets wrong slice after slice move`
- **Status**: `ready`
- **Source**: `Option B #11`
- **Topology**: `slice migration + memory pressure + swappiness skew`
- **Symptom**: `A nightly batch spikes swap on a host that should be RAM-only for latency SLAs, and the wrong service disappears from the process list without obvious cgroup OOM events in the journal everyone watches.`
- **Discoveries**: `'dmesg' attributes kills to a parent slice path that no longer matches the moved workload’s cgroup path in '/proc/<pid>/cgroup'.; Local OOM score adjustments live in a sysctl drop-in that applies after an early-boot override from a container runtime.; Metrics scrape '/proc/meminfo' on the host while the workload sees a memcg limit only in an ancestor slice.`
- **Evidence**: `trajectory=Verification; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 1: Two OOM narratives (host vs memcg) both look plausible until you reconcile path churn timing.; Exploit 6: Dashboard shows “no OOM” because it filters on a substring that no longer exists after rename.`
- **Why hard**: `Requires reconciling hierarchical limits with host-level swap policy under migration.`
- **Main collapse risk**: `Reads like generic Linux OOM tuning unless evidence ties slice moves to wrong attribution.`


#### 10. `Serial console getty baud flip hides init failure`
- **Status**: `ready`
- **Source**: `Option B #12`
- **Topology**: `kernel cmdline + getty unit + physical serial concentrator`
- **Symptom**: `Remote datacenter hands report “no output” during early boot while IPMI SOL occasionally prints garbage after a firmware upgrade packaged as low risk.`
- **Discoveries**: `GRUB passes a baud that matches firmware default but mismatches a cascaded USB-serial adapter’s stored settings.; A rescue initramfs hook enables getty on 'ttyS0' while the platform enumerates a different ACPI id first on cold boot only.; 'journalctl -b -u serial-getty@*' shows start attempts but the attached terminal shows bit-shifted prompts.`
- **Evidence**: `trajectory=Coherence; command_level=none; cluster=Long-Horizon-Coherence`
- **Exploits**: `Exploit 4: Early bootloader parameter choice commits a console pairing that later hotplug subtly invalidates.; Exploit 9: Stty changes in a rescue shell poison the interactive session without affecting recorded boot logs.`
- **Why hard**: `Failure chains cross firmware, kernel cmdline, and userspace getty without one smoking gun log line.`
- **Main collapse risk**: `Too hardware-specific without a reproducible capture artifact.`


#### 11. `LVM thin pool metadata growth stalls I/O under mistaken free-space alert`
- **Status**: `ready`
- **Source**: `Option B #13`
- **Topology**: `thin provisioning + pvresize timing + monitoring blind spot`
- **Symptom**: `A database pauses coincidentally with “disk full” alerts that clear moments later; long-term no leak is found in filesystem usage.`
- **Discoveries**: `Monitoring sums ext4 free space while the thin LV approaches data threshold first.; 'lvs' reporting modes disagree depending on whether '--units' was applied consistently in scripts.; A maintenance 'pvresize' returns while pvmove segments are still merging in the background.`
- **Evidence**: `trajectory=Execution; command_level=not-waiting; cluster=Complex-System-Builds`
- **Exploits**: `Exploit 3: Green check uses df on the wrong abstraction layer for thin LVs.; Exploit 8: Automation treats “resize submitted” as “pool safe to burst writes.”`
- **Why hard**: `Multi-layer free-space truth across VG, thin pool, and FS.`
- **Main collapse risk**: `Collapses into “read the manual for thinp” if symptoms leak implementation names.`


#### 12. `Inotify fanotify interaction drops events on bind-mounted subtree`
- **Status**: `ready`
- **Source**: `Option B #14`
- **Topology**: `fs watch APIs + bind mount fan-out + fanotify group ordering`
- **Symptom**: `A file-driven pipeline misses sporadic arrivals in a watched directory while manual 'touch' tests always work.`
- **Discoveries**: `Watcher registers on a host path while producers write through a bind mount with different propagation flags.; Fanotify permission events are consumed by a security agent group that suppresses delivery to the pipeline’s group on rename-heavy workloads.; 'strace' shows 'inotify' returning 'ENOSPC' in bursts that logrotate masks by increasing queue only on one consumer.`
- **Evidence**: `trajectory=Execution; command_level=edge-cases; cluster=Complex-System-Builds`
- **Exploits**: `Exploit 1: Two watchers each think they own canonical semantics for “file landed.”; Exploit 7: Disabling the security agent “fixes” the issue by changing event fan-out, not by fixing ingest.`
- **Why hard**: `Couples mount topology with event API ordering and resource limits.`
- **Main collapse risk**: `Too niche unless symptoms emphasize cross-mount misses, not generic “missed fs events.”`


#### 13. `MD RAID reshape + bitmap stall presents as app-level stalls`
- **Status**: `ready`
- **Source**: `Option B #16`
- **Topology**: `mdadm reshape + write-intent bitmap + elevator interaction`
- **Symptom**: `Transaction commit latency spikes every few minutes on one node class during a “non-disruptive” RAID expansion marketed as online.`
- **Discoveries**: `'/proc/mdstat' shows reshape progress but tooling dashboards only track CPU and network saturation.; 'iostat' vxsvctm spikes correlate with bitmap commits that pause subsets of the array.; A “speed limit” knob is set in a drop-in that applies only after mdadm restart, not the running reshape.`
- **Evidence**: `trajectory=Verification; command_level=not-waiting; cluster=Robust-Verification`
- **Exploits**: `Exploit 5: A nightly report emails reshape percent from a cache file updated hourly.; Exploit 8: Automation polls mdadm completion via exit code of an info query that returns before reshape quiesces writes.`
- **Why hard**: `Storage-layer progress semantics vs application SLO tools.`
- **Main collapse risk**: `RAID specifics dominate unless evidence stays in generic block-stall signals.`


#### 14. `Pipe buffer + SIGPIPE storm from mis-sized writer batch`
- **Status**: `ready`
- **Source**: `Option B #17`
- **Topology**: `stdout pipeline + systemd logging + PIPE capacity`
- **Symptom**: `A migration tool “randomly” exits nonzero under systemd with no obvious stderr aside from a truncated unit log excerpt.`
- **Discoveries**: `The tool writes large bursts to stdout while the unit’s 'StandardOutput=journal' path applies backpressure differently than an interactive shell.; 'strace' shows 'EPIPE' on a downstream consumer that restarts mid-batch during log rotation.; Manual runs redirect output to files and mask the failure mode.`
- **Evidence**: `trajectory=Execution; command_level=terminal-crash; cluster=Complex-System-Builds`
- **Exploits**: `Exploit 9: Terminal/logging pipeline differs under systemd vs tty, poisoning reproducibility.; Exploit 2: Rerunning with 'set -o pipefail' disabled hides partial failure persistence on disk.`
- **Why hard**: `Couples signal semantics with logging backpressure, not application logic bugs.`
- **Main collapse risk**: `Sounds like “dev wrote bad shell” unless observability is mandated.`


#### 15. `Huge page allocation pressure masquerades as network retries`
- **Status**: `ready`
- **Source**: `Option B #18`
- **Topology**: `transparent huge pages + NIC RSS + memory compaction stalls`
- **Symptom**: `East-west traffic retries explode on a subset of hosts after a kernel bump, while 'ethtool' stats blame no drops.`
- **Discoveries**: `'perf sched' shows long 'compact_zone' stalls aligned with retry spikes.; Application sets 'MADV_HUGEPAGE' on arenas while NIC RSS rings stay hugepage-unfriendly on that stepping.; sysctl defaults diverge between orchestration image and bare-metal kickstart.`
- **Evidence**: `trajectory=Verification; command_level=none; cluster=Robust-Verification`
- **Exploits**: `Exploit 6: Monitoring validates RSS and packet loss counters, not compaction stalls.; Exploit 3: Microbenchmark “ping works” checks miss bursty allocation during batch ingest.`
- **Why hard**: `Cross-layer symptom displacement from MM to networking behavior.`
- **Main collapse risk**: `Kernel knob soup without a disciplined evidence path.`


#### 16. `Auditd rules reload drops syscall class on busy socket`
- **Status**: `ready`
- **Source**: `Option B #20`
- **Topology**: `auditd reload + netlink backlog + hot policy swap`
- **Symptom**: `Compliance dashboards intermittently report “coverage gaps” after scheduled policy pushes even though rule dumps look complete seconds later.`
- **Discoveries**: `'auditctl -R' races with sustained syscall traffic that fills audit netlink buffers, dropping events silently during the swap window.; Two management agents push different rule files with identical timestamps but different inode numbers.; A local verifier reads '/etc/audit/rules.d' while the running kernel rule set in '/proc' briefly mismatches mid-reload.`
- **Evidence**: `trajectory=Execution; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 2: Re-running reload to “fix” coverage worsens backlog and extends the blind window.; Exploit 5: A “post-update check” counts rule lines on disk, not effective enabled rules.`
- **Why hard**: `Time-varying truth between configuration and enforced kernel policy.`
- **Main collapse risk**: `Security auditor cliché unless tied to backlog/race observability.`


#### 17. `CPUsets + NUMA rebalance leaves isolated CPU with stranded IRQ affinity`
- **Status**: `ready`
- **Source**: `Option B #21`
- **Topology**: `cpuset + irqbalance + NIC MSI-X table`
- **Symptom**: `After a capacity rebalance job, one NIC reports rising retransmits while IRQ distribution looks even in a naive '/proc/interrupts' snapshot.`
- **Discoveries**: `A cpuset isolates CPUs while '/proc/irq/*/smp_affinity_list' still targets a CPU removed from the dataplane set.; 'irqbalance' logs show benign messages during the window where affinity drifts.; ethtool channel counts changed in firmware without driver reinit.`
- **Evidence**: `trajectory=Coherence; command_level=edge-cases; cluster=Complex-System-Builds`
- **Exploits**: `Exploit 4: Early isolation choice persists through IRQ reprogramming that assumes prior affinity valid.; Exploit 7: Two playbooks—cpuset fix vs irq reset—each work alone but fight when applied together.`
- **Why hard**: `IRQ-plane coupling across isolation choices and hardware reprogramming.`
- **Main collapse risk**: `Hardware-dependent without stable software-only correlates.`


#### 18. `Snapper timeline pre/post snapshot naming collides after clock rollback`
- **Status**: `ready`
- **Source**: `Option B #22`
- **Topology**: `BTRFS snap naming + clock step + automation ids`
- **Symptom**: `Rollback automation picks the wrong snapshot pair after an incident, restoring a known-bad subtree while reporting success against ticket ids.`
- **Discoveries**: `Snapshot labels sort lexicographically in a way that duplicates after manual time corrections.; A wrapper stores “latest” by parsing 'snapper list' output formatted differently in locale variants.; Pre/post pairs share numeric indices that recycle after snapshot deletion policies.`
- **Evidence**: `trajectory=Verification; command_level=edge-cases; cluster=Long-Horizon-Coherence`
- **Exploits**: `Exploit 3: Local verification hashes a subtree path that is not the rollback target actually mounted.; Exploit 8: The rollback tool returns after scheduling mount changes but before subvolumes are visible in all mount namespaces.`
- **Why hard**: `Identifier stability across time manipulation and listing formats.`
- **Main collapse risk**: `Snapper-centric collapse; constrain to generic snapshot id hygiene if needed.`


#### 19. `DBus broker restart orphan causes stale polkit action maps`
- **Status**: `ready`
- **Source**: `Option B #23`
- **Topology**: `dbus-broker + polkit + transient unit activation`
- **Symptom**: `Operator actions intermittently fail authorization despite membership in the right unix groups until a full session restart.`
- **Discoveries**: `A polkit rule reload pulls actions from a temporary path that disappears when packaging updates overlap broker restarts.; 'pkcheck' results differ between systemd user session bus and system bus for the same subject.; 'loginctl' shows lingering sessions with mixed session ids after fast user switching in maintenance mode.`
- **Evidence**: `trajectory=Coherence; command_level=edge-cases; cluster=Complex-System-Builds`
- **Exploits**: `Exploit 1: Two policy surfaces (cached action map vs disk rules) temporarily diverge.; Exploit 4: Early broker start order chooses a rules snapshot that later edits invalidate without bumping mtimes predictably.`
- **Why hard**: `Authorization coherence across broker lifecycle and cache layers.`
- **Main collapse risk**: `Desktop-ish unless grounded in server operator automation.`


#### 20. `nftables set swap exposes window where both old and new miss`
- **Status**: `ready`
- **Source**: `Option B #24`
- **Topology**: `nft atomic table updates + large ip sets + control-plane burst`
- **Symptom**: `Brief allowlist failures coincide with automated threat-feed refreshes; sessions that should be grandfathered get reset.`
- **Discoveries**: `Atomic 'nft -f' replace swaps the set reference while conntrack expectations still key the old set identity briefly.; Monitor probes use 'nft list set' output captured before kernel applies the atomic batch.; A user-space helper flushes ct entries opportunistically during refresh, widening the gap.`
- **Evidence**: `trajectory=Execution; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 2: Re-running the refresh job to “unblock” operators deletes rollback snapshots of the prior set.; Exploit 5: A post-update check counts set element cardinality, not ct keyability during the transition.`
- **Why hard**: `Statefulness across atomic firewall updates and connection tracking.`
- **Main collapse risk**: `Collapses into nft trivia without ct/nft interaction evidence.`


#### 21. `OOMScoreAdjust inheritance poisons helper children after exec`
- **Status**: `ready`
- **Source**: `Option B #25`
- **Topology**: `prset oom_score_adj + systemd delegate + multi-exec chain`
- **Symptom**: `A monitoring sidecar keeps dying under pressure while the main workload survives longer than expected, breaking metric completeness only during incidents.`
- **Discoveries**: `The sidecar inherits an aggressive OOM score from an ancestor slice adjust line meant for the main app.; '/proc/<pid>/oom_score_adj' differs between threads after a 'clone' + 'exec' pattern from a wrapper.; cgroup v2 'memory.oom.group' semantics interact with host-level kills in non-obvious ordering.`
- **Evidence**: `trajectory=Verification; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 6: Dashboard highlights main PID RSS while the sidecar is the actual OOM victim path.; Exploit 4: Early wrapper choice locks score adjustments across exec boundaries not visible in simple unit files.`
- **Why hard**: `Process tree inheritance crosses intended isolation boundaries.`
- **Main collapse risk**: `Sounds like misconfigured monitoring unless inheritance evidence is mandatory.`


#### 22. `Squashfs loop mount + dm-verity nested read errors surface late`
- **Status**: `ready`
- **Source**: `Option B #27`
- **Topology**: `loop device + verified read-only image + layered errors`
- **Symptom**: `A packaged appliance sporadically fails systemd unit start with missing files despite image rebuild hashes matching release notes.`
- **Discoveries**: `Upper failure happens only when loop allocation reuses minors differently after hot unplug events.; 'verity' root hash validation passes at mount but readahead pulls blocks through a path that occasionally IO errors under memory pressure.; 'systemd-analyze blame' points at a unit that only waits on a generator that masked earlier squash mount races.`
- **Evidence**: `trajectory=Verification; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 1: “Hash matches release” and “runtime tree incomplete” coexist across different read paths.; Exploit 10: Edge-case of zero-length file in squash metadata parses as present in one tool and absent in another.`
- **Why hard**: `Failure displacement across read-only verification layers.`
- **Main collapse risk**: `Verity naming triggers RC6 attention.`


#### 23. `Rsyslog impjournal forwarding gap during journal vacuum`
- **Status**: `ready`
- **Source**: `Option B #28`
- **Topology**: `journald vacuum + rsyslog imjournal cursor + disk pressure`
- **Symptom**: `SIEM correlation misses bursts of auth failures during disk housekeeping windows; local auth logs exist when queried later.`
- **Discoveries**: `'imjournal' cursor races a vacuum that deletes files still referenced by an mmap-heavy reader.; 'journalctl --verify' reports minor issues only on the affected spindle set.; Forwarding resumes at a cursor that skips a rotated file segment whose inode was recycled quickly.`
- **Evidence**: `trajectory=Coherence; command_level=not-waiting; cluster=Long-Horizon-Coherence`
- **Exploits**: `Exploit 8: Rsyslog reload returns before state file fsync completes on full filesystems.; Exploit 2: Re-running vacuum to reclaim space deepens cursor inconsistencies.`
- **Why hard**: `Log durability and cursor semantics across journal maintenance.`
- **Main collapse risk**: `Sounds like misconfigured forwarding unless timelines tie to vacuum.`


#### 24. `KVM host hugepage-backed guest balloon fights host overcommit`
- **Status**: `ready`
- **Source**: `Option B #29`
- **Topology**: `KVM balloon + hugepages + host swap policy`
- **Symptom**: `Guests freeze in bursts when a host “helpfully” reclaims memory during consolidation, while libvirt reports healthy balloon curves.`
- **Discoveries**: `Balloon inflation fails silently when guest backends cannot return hugepages fast enough.; Host 'ksm' settings interact badly with static hugepage reservations pinned by qemu.; 'virsh dommemstat' sampling interval masks millisecond-scale swap storms visible in 'pidstat'.`
- **Evidence**: `trajectory=Execution; command_level=edge-cases; cluster=Complex-System-Builds`
- **Exploits**: `Exploit 5: Monitoring emails mem graphs that average away stall spikes.; Exploit 7: Two remediation toggles—disable balloon vs enable ksm—both “work” in demos but fail combined.`
- **Why hard**: `Cross-hypervisor memory policy coupling with non-linear balloon behavior.`
- **Main collapse risk**: `Virt stack overload; keep evidence in stall + balloon error counters.`


#### 25. `Static node exporter textfile collector stale metrics after rename`
- **Status**: `ready`
- **Source**: `Option B #30`
- **Topology**: `prom textfile + atomic replace + exporter file handle`
- **Symptom**: `Alerts fire on impossible metric combinations until the exporter restarts, though CI pushed “fixed” scripts hours ago.`
- **Discoveries**: `The collector keeps an open fd to a deleted inode while writers use rename swap for atomic updates.; 'node_textfile_mtime' gauge disagrees with actual file metadata on disk depending on scrape timing.; A tmpfs exhaustion forces writers into partial writes that still pass naive line-count checks.`
- **Evidence**: `trajectory=Verification; command_level=none; cluster=Robust-Verification`
- **Exploits**: `Exploit 6: Alert rules validate label pairs that are internally consistent in stale prom text but wrong versus reality.; Exploit 3: Quick probe reads first 4KB of textfile and misses later lines updating critical gauges.`
- **Why hard**: `Observability ingestion atomicity vs process file handle lifetime.`
- **Main collapse risk**: `Feels like Prometheus 101 unless tied to unix replace semantics.`


#### 26. `BPF link detach leaves tc probe attached in netns ghost`
- **Status**: `ready`
- **Source**: `Option B #32`
- **Topology**: `BPF tc hook + netns lifecycle + pinned links`
- **Symptom**: `Latency outliers persist on recycled container IDs after policy “removal” succeeded in the control plane API responses.`
- **Discoveries**: `A pinned BPF object survives netns deletion when references linger in a host-owned cgroup.; 'bpftool net' disagrees with 'tc -s filter show' depending on which netns file descriptor was used for listing.; Recreated containers reuse cgroup paths that reattach inherited hooks.`
- **Evidence**: `trajectory=Coherence; command_level=edge-cases; cluster=Adversarial-Creative-Reasoning`
- **Exploits**: `Exploit 2: Running detach twice races with map updates and corrupts pinned state semantics.; Exploit 1: Control plane “policy removed” checks an API table, not effective tc/BPF attachment.`
- **Why hard**: `Low-observability ghost attachments across netns churn.`
- **Main collapse risk**: `BPF expert task unless grounded in bpftool/tc cross-checks.`


#### 27. `NFS idmap cache poisons home relabel policy`
- **Status**: `refined`
- **Source**: `Option B repairable seed retained with status refined (review strengthening notes in Option B artifact)`
- **Topology**: `NFS idmapping + nss cache + SELinux/AppArmor context restore`
- **Symptom**: `Restoring a user tree from tape replays POSIX ACLs that look right interactively but batch jobs refuse to read until caches are flushed inconsistently.`
- **Discoveries**: `'id' and 'getent' disagree across sessions depending on which sssd cache shard warmed first.; Restored files carry xattrs that match numeric ids in one view and strings in another.; A nightly scanner uses fully-qualified names while the login path uses short names, toggling effective identity.`
- **Evidence**: `trajectory=Coherence; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 1: Two identity authorities (file server vs local nss) both look authoritative hour-to-hour.; Exploit 10: Empty supplementary group list on restore path triggers “access denied” only on non-interactive shells.`
- **Why hard**: `Hard if verification is forced to cross nss, nfs, and xattr surfaces without naming the fix.`
- **Main collapse risk**: `Cultural knowledge of NSS without runnable evidence.`


#### 28. `LUKS reencryption resumes wrong segment after battery brownout`
- **Status**: `refined`
- **Source**: `Option B repairable seed retained with status refined (review strengthening notes in Option B artifact)`
- **Topology**: `online reencrypt + metadata backup slot + journal replay`
- **Symptom**: `Volume unlocks but some directories read as IO errors until a full offline repair that cannot run in production windows.`
- **Discoveries**: `The reencrypt helper’s progress file disagrees with the kernel keyslot priority after an abrupt power event.; 'dmesg' shows a burst of remap errors that 'smartctl' calls “prefail” without pinpointing LBA mapping.; A read-only check validates header copies that are internally consistent but point at different data offsets.`
- **Evidence**: `trajectory=Execution; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 2: Rerunning an “idempotent” resume mutates the backup header, destroying rollback evidence.; Exploit 6: Local verifier checksums plaintext excerpts from the wrong ciphertext range.`
- **Why hard**: `Strong if destructive phases cannot be naively repeated.`
- **Main collapse risk**: `Cryptographic naming invites spec-complete collapse.`


#### 29. `Chrony leap second smear disagrees with containerized clients`
- **Status**: `refined`
- **Source**: `Option B repairable seed retained with status refined (review strengthening notes in Option B artifact)`
- **Topology**: `NTP smear policy + namespace clockviews + lease timers`
- **Symptom**: `Distributed locks flap only across reboot windows tied to leap events, while 'ntpstat' looks synchronized on hosts.`
- **Discoveries**: `Host chrony applies smear while containers use a minimal client config that snaps stepped time.; Lease tables in an embedded store use mixed monotonic vs wall assumptions across languages.; A JVM '-Duser.timezone' fix masks the problem in one tier but not another.`
- **Evidence**: `trajectory=Coherence; command_level=edge-cases; cluster=Long-Horizon-Coherence`
- **Exploits**: `Exploit 4: Early choice of client implementation commits different smoothing during a global clock event.; Exploit 5: Health checks using short HTTP timeouts go green during smear while consensus timeouts fail.`
- **Why hard**: `Long-horizon clock policy divergence across namespaces.`
- **Main collapse risk**: `Leap-second rarity makes the task feel contrived without simulated clock stepping.`


#### 30. `FUSE passthrough passthru xattr size limits break backup ACL roundtrip`
- **Status**: `refined`
- **Source**: `Option B repairable seed retained with status refined (review strengthening notes in Option B artifact)`
- **Topology**: `FUSE passthrough + xattr namespace caps + backup manifest`
- **Symptom**: `Restores validate manifest checksums yet applications reject configs restored from backups with opaque “invalid format” errors.`
- **Discoveries**: `Large security xattrs exceed FUSE write size negotiated at mount without surfacing 'E2BIG' uniformly across tools.; The backup tool stores xattrs inline while restore uses a different syscall batching threshold.; 'getfattr' output differs when read from the mount vs the underlying brick path.`
- **Evidence**: `trajectory=Coherence; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 1: Two metadata truths—manifest vs live inode xattrs—both look “successful.”; Exploit 10: Empty xattr edge case on directory entries flips behavior only in batch restore mode.`
- **Why hard**: `Metadata fidelity under layered FS limits, not corruption.`
- **Main collapse risk**: `Vendor naming collapse; use RC6 to avoid naming a specific FUSE product.`


#### 31. `APC UPS usb hid driver reset drops wall power telemetry mid-job`
- **Status**: `refined`
- **Source**: `Option B repairable seed retained with status refined (review strengthening notes in Option B artifact)`
- **Topology**: `usb autosuspend + ups monitoring + graceful shutdown ordering`
- **Symptom**: `Scheduled maintenance aborts early because the orchestrator believes utility power failed during a window where racks stayed lit.`
- **Discoveries**: `Kernel autosuspend puts the UPS HID interface to sleep while a daemon polls at a slower cadence than suspend thresholds.; 'upsc' output becomes stale without returning errors when the usbfs read succeeds from cache.; A systemd inhibitor latch trips on a transient “OB DISCHRG” parse of buffered frames after reset.`
- **Evidence**: `trajectory=Execution; command_level=edge-cases; cluster=Complex-System-Builds`
- **Exploits**: `Exploit 8: Polling loop treats file readable as fresh telemetry before the device finishes reinit.; Exploit 3: A fast “power ok” check reads a LED sysfs node unrelated to the UPS input state.`
- **Why hard**: `Sensor authority vs USB power management state machine.`
- **Main collapse risk**: `Hardware-centric; needs simulated usb reset traces.`


#### 32. `GRUB BLS boot counting interaction with RAID1 leg degradation`
- **Status**: `refined`
- **Source**: `Option B repairable seed retained with status refined (review strengthening notes in Option B artifact)`
- **Topology**: `bootloader boot counting + md degraded + initrd selection`
- **Symptom**: `Some nodes boot into a rescue entry intermittently after a disk leg fails, without clear operator-visible reason in the netboot logs they monitor.`
- **Discoveries**: `BLS entries advance boot counting on partial failures that still reach userspace long enough to flip counters.; mdadm email hooks run late while grub-reboot semantics already queued next boot targets.; EFI variables holding boot.next differ between mirrored ESP copies.`
- **Evidence**: `trajectory=Coherence; command_level=edge-cases; cluster=Long-Horizon-Coherence`
- **Exploits**: `Exploit 4: Early degraded read paths pick a kernel/initrd pair that later boot counting rejects as “bad.”; Exploit 1: Two “next boot” truths—EFI vars vs grubenv—diverge across RAID mirror legs.`
- **Why hard**: `Boot policy state threaded through hardware degradation signals.`
- **Main collapse risk**: `Firmware/bootloader naming collapse; RC6 candidate.`


#### 33. `Machines entry drifts from NSS during NIS-to-sssd cutover`
- **Status**: `replacement`
- **Source**: `Generated to fill bank; 'system-administration' subsystem diversity`
- **Topology**: `NIS compatibility + sssd cache + automount map`
- **Symptom**: `Batch nodes resolve the same hostname to different addresses than the admin’s interactive shell on the same host, breaking shared filesystem paths until someone runs a manual cache flush nobody scripted.`
- **Discoveries**: `Automount reads maps through one nss chain while 'getent hosts' in systemd units uses another after nsswitch reorder.; Stale negative TTLs in sssd LDB create flip-flop between NIS fallback and SSSD authoritative answer depending on query type.; 'hostname -f' and reverse PTR for management IP disagree only when queries originate from non-interactive cgroup slices.`
- **Evidence**: `trajectory=Coherence; command_level=edge-cases; cluster=Long-Horizon-Coherence`
- **Exploits**: `Exploit 1: Two naming authorities both answer credibly during the migration window.; Exploit 4: Early nsswitch edit commits order that later migration scripts partially overwrite without bumping mtime.`
- **Why hard**: `Identity and mount truth split across NSS/automount without a single knob to transcribe.`
- **Main collapse risk**: `Collapses into “fix nsswitch” unless multi-tool evidence is mandatory.`


#### 34. `iscsi session reinstate races multipath path_loss TUR`
- **Status**: `replacement`
- **Source**: `Generated to fill bank; 'system-administration' subsystem diversity`
- **Topology**: `DM-Multipath + iscsi reconnect + path_checker`
- **Symptom**: `LUNs drop offline during storage fabric brownouts with multipath claiming paths active while apps see EIO until manual path flush—then no errors in the summary counters ops review.`
- **Discoveries**: `'multipath -ll' shows active while kernel scsi host still reports transport failed on the path iscsi requeued.; path_checker TUR results cached across a window where iscsi layer already invalidated the session handle.; udev triggers re-add paths in different order than multipathd expects after queue_if_no_path toggled mid-incident.`
- **Evidence**: `trajectory=Execution; command_level=not-waiting; cluster=Complex-System-Builds`
- **Exploits**: `Exploit 8: Runbook marks node recovery done when multipath CLI prints healthy before TUR quiesces on all paths.; Exploit 2: Re-running path flush in a tight loop extends scsi error recovery and destroys ordering evidence.`
- **Why hard**: `Block-layer state threads through scsi, iscsi, and multipath with premature green summaries.`
- **Main collapse risk**: `Vendor array playbook replaces diagnosis unless symptoms stay transport-generic.`


#### 35. `Profile-sync-daemon copy-up fills $HOME on NFS with wrong quota accounting`
- **Status**: `replacement`
- **Source**: `Generated to fill bank; 'system-administration' subsystem diversity`
- **Topology**: `psd + overlay on home + NFS quota RPC`
- **Symptom**: `Users hit ‘disk quota exceeded’ on login nodes while project storage dashboards show plenty of space and du on visible files does not add up.`
- **Discoveries**: `psd mirrors browser profiles into an rw layer whose usage is charged to a quota tree the NFS server maps differently from the visible home path.; Quota RPC uses filehandle derived before bind-style layout tricks in automounter.; 'quota -s' over NFS disagrees with server-side project report until a delayed sync flushes attribute cache.`
- **Evidence**: `trajectory=Verification; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 1: Visible du truth and server quota truth diverge while both look plausible interactively.; Exploit 6: Helpdesk script checks only home leaf, not merged rw upper charged elsewhere.`
- **Why hard**: `Multi-surface usage truth across layered client caches and server quota identity.`
- **Main collapse risk**: `Overfits one desktop sync tool; abstract to layered-home + NFS quota.`


#### 36. `tuned reapply loses disk governor profile under CPU-partition mode`
- **Status**: `replacement`
- **Source**: `Generated to fill bank; 'system-administration' subsystem diversity`
- **Topology**: `tuned profiles + cpufreq + scsi host params`
- **Symptom**: `Post-maintenance latency outliers on storage-heavy nodes correlate with power profiles ‘unchanged’ in config management diffs.`
- **Discoveries**: `tuned reapply order reapplies cpu plugin before disk plugin on hosts with split personalities, leaving elevator/governor mismatch.; 'tuned-adm active' shows expected profile while sysfs cpufreq governor files disagree until manual profile off/on.; IRQ affinity changes from earlier tuning interact so governor never boosts during scsi bursts.`
- **Evidence**: `trajectory=Coherence; command_level=edge-cases; cluster=Complex-System-Builds`
- **Exploits**: `Exploit 4: First boot tuned invocation picks disk params predating later CPU partition cgroup layout.; Exploit 5: Monitoring samples CPU freq average, not tail latency during governor stall windows.`
- **Why hard**: `Power/IO tuning order couples kernel knobs in ways single-profile dumps hide.`
- **Main collapse risk**: `Becomes knob catalog unless before/after sysfsdiff is the contract.`


#### 37. `pidfile path reused across namespaces after unseen PID rollover`
- **Status**: `replacement`
- **Source**: `Generated to fill bank; 'system-administration' subsystem diversity`
- **Topology**: `pid wrap + pidfiles + containerized legacy daemons`
- **Symptom**: `A legacy daemon refuses to start claiming another instance exists, but the listed PID is a short-lived task in a different namespace or already exited hours ago.`
- **Discoveries**: `Pidfile stores numeric pid without ns id; after global pid wrap a new unrelated process reuses the number visible from host view.; 'kill -0' from the management wrapper uses host pid namespace while daemon lives in net-isolated unit.; Stale pidfile survives crash because umount order prevented cleanup tmpfs path.`
- **Evidence**: `trajectory=Verification; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 1: pidfile semantic truth and live process identity disagree across namespaces.; Exploit 10: Empty-pid edge in script treats blank line as running daemon.`
- **Why hard**: `Identity reconciliation across namespace views and pid exhaustion timelines.`
- **Main collapse risk**: `Sounds like sloppy packaging unless '/proc' ns proofs are required.`


#### 38. `Btrfs qgroup accounting lags behind subvolume delete after balance`
- **Status**: `replacement`
- **Source**: `Generated to fill bank; 'system-administration' subsystem diversity`
- **Topology**: `btrfs qgroup + balance + deferred frees`
- **Symptom**: `Free-space alarms fire on a btrfs backup volume while snapshots were deleted days ago; balance status shows idle.`
- **Discoveries**: `qgroup numbers stay high until transaction commits cross a threshold hidden from 'btrfs filesystem df' default view.; Subvolume delete and balance interleave leaving orphaned extents referenced only in delayed ref updates.; Monitoring samples raw 'df' not qgroup-exclusive usage the backup policy enforces.`
- **Evidence**: `trajectory=Execution; command_level=not-waiting; cluster=Long-Horizon-Coherence`
- **Exploits**: `Exploit 8: Automation treats balance completion message as reclaim done before qgroup catch-up.; Exploit 3: Quick space check uses path not enrolled in qgroup the policy cares about.`
- **Why hard**: `Multiple ‘free space’ definitions across btrfs accounting and wall-clock delay.`
- **Main collapse risk**: `Filesystem sermon unless paired tool outputs are mandated.`


### Category: `security`

#### 1. `Split verifier: checksum file verifies payload but not the verifier path`
- **Status**: `ready`
- **Source**: `Option B #1`
- **Topology**: `dual-path ingest + detached sig manifest + wrapper trust`
- **Symptom**: `Automated promotion accepts an artifact whose inline checksum matches the manifest, yet runtime loads a different byte-identical-looking path under concurrency.`
- **Discoveries**: `The checker hashes the download temp path while the loader mmap-opens a stable path swapped by another job in the same second.; Manifest lists basename-only entries that collide across version directories.; A wrapper script exports 'SHA256_CMD' pointing at a benign busybox build that mishandles certain file types silently.`
- **Evidence**: `trajectory=Verification; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 3: Local green check validates content hash but not inode swap timing.; Exploit 6: External auditor tool verifies signatures on the manifest file bytes, not the artifact path actually loaded.`
- **Why hard**: `Requires reconciling TOCTOU between verification and consumption, not learning a new crypto primitive.`
- **Main collapse risk**: `Collapse into “use fsverity” as one-line fix—task must ban trivial silver bullets in scope.`


#### 2. `Capabilities bounding set drift across exec-profiled admin wrapper`
- **Status**: `ready`
- **Source**: `Option B #2`
- **Topology**: `ambient caps + file caps + pam cap conf`
- **Symptom**: `A break-glass tool sometimes fails mid-run with permission errors that clear when operators bypass the approved wrapper, without obvious AVC denials in the default view.`
- **Discoveries**: `'pam_cap' applies differently for interactive vs non-interactive sessions with the same Linux user.; A file capability on the helper resets bounding sets differently depending on whether 'no_new_privs' is set by systemd hardening.; 'capsh --print' output in the failing session shows a subset missing only after a nested 'sudo' boundary.`
- **Evidence**: `trajectory=Coherence; command_level=edge-cases; cluster=Complex-System-Builds`
- **Exploits**: `Exploit 1: Two “who is privileged” truths diverge across pam vs file caps vs ambient inheritance.; Exploit 4: Early login path choices commit a cap profile that later nested exec cannot enlarge.`
- **Why hard**: `Capability algebra across real session shapes, not a CVE drop.`
- **Main collapse risk**: `SELinux vs caps confusion unless evidence separates them.`


#### 3. `mTLS trust store refresh leaves stale intermediate preferred`
- **Status**: `ready`
- **Source**: `Option B #3`
- **Topology**: `chain construction + AIA fetch policy + reload windows`
- **Symptom**: `Some clients pin connections to “bad pubkey days” where half of regions see handshake failures while others succeed, after a CA rotation marketed as seamless.`
- **Discoveries**: `Server presents a chain that validates against an old intermediate cached in a process that hot-reloads roots but not intermediates.; Client trust bundles use hashed filenames; deployment updates symlink targets atomically but long-lived workers keep old file descriptors.; A canary command uses 'openssl s_client' with '-partial_chain' masking local misconfig.`
- **Evidence**: `trajectory=Verification; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 1: Two chain truths—on-disk bundle vs process memory—coexist during rotation.; Exploit 8: Reload returns before worker pool drains old TLS contexts.`
- **Why hard**: `Freshness and memory lifetime across rotation, not breaking math.`
- **Main collapse risk**: `RC6 if instructions name exact OpenSSL flags or CA products.`


#### 4. `Container image signing key rollover with dual-tag alias`
- **Status**: `ready`
- **Source**: `Option B #5`
- **Topology**: `signing identity + tag alias graph + registry mirror lag`
- **Symptom**: `Pull-policy “strict” clusters admit an image digest intermittently flagged by admission after mirror sync delays, without a single CVE listed.`
- **Discoveries**: `Two mirrors serve the same tag string with different digests during a key rollover window.; Admission checks signatures on manifest bytes fetched from mirror A while kubelet pulls blobs from mirror B.; Policy engines cache attestations by tag, not by digest.`
- **Evidence**: `trajectory=Execution; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 1: Tag and digest authorities desynchronize during mirror catch-up.; Exploit 6: CI verifies cosign inputs on workstation while cluster verifies different transport headers.`
- **Why hard**: `Supply-chain freshness across mirror topology, not crypto breaks.`
- **Main collapse risk**: `Cloud-brand tooling dominates; RC6 to keep product names generic.`


#### 5. `seccomp notify FD forwarded to wrong namespaces`
- **Status**: `ready`
- **Source**: `Option B #6`
- **Topology**: `seccomp user notif + fd passing + pidns mapping`
- **Symptom**: `A supervised runtime allows occasional syscalls that policy claims should be brokered, correlated with child reparenting events only.`
- **Discoveries**: `The supervisor registers notify against parent pid while traced tasks live in a child pid namespace with recycled pids.; 'SCMP_ACT_NOTIFY' decisions apply based on outdated arch fields after multilib exec.; 'strace' on the supervisor shows recvmsg boundaries misaligned with tracer event ordering under load.`
- **Evidence**: `trajectory=Coherence; command_level=edge-cases; cluster=Adversarial-Creative-Reasoning`
- **Exploits**: `Exploit 4: Early pid mapping choice becomes incorrect after reparenting without notifier refresh.; Exploit 7: Two supervision modes—ptrace vs seccomp notif—each “fix” leaks different syscall classes.`
- **Why hard**: `Low-observability broker correctness across namespace churn.`
- **Main collapse risk**: `Expert-only unless sandbox provides curated traces.`


#### 6. `MAC label downgrade via tmpfs copy-up without move priv`
- **Status**: `ready`
- **Source**: `Option B #7`
- **Topology**: `SELinux context + tmpfs + transition rules`
- **Symptom**: `Files land in a guarded directory with weaker type than policy comments promise, passing local 'restorecon' checks until a confined daemon reads them.`
- **Discoveries**: `'cp' vs 'mv' semantics differ because tmpfs transitions differ; packaging scripts use 'install' flags that pick the weaker path.; 'matchpathcon' reports expected type for the final path name, not the inode type actually created during copy-up.; 'audit2allow' suggests an overly broad boolean that masks root cause.`
- **Evidence**: `trajectory=Verification; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 3: A nightly “verify labels” script stats paths, not inode contexts after hardlink tricks.; Exploit 6: Scanner reads policy file version A while kernel enforces version B until reload.`
- **Why hard**: `Misleading local checks on MAC truth versus runtime transitions.`
- **Main collapse risk**: `SELinux soup unless tasks constrain to three observable tools.`


#### 7. `SSH CA principal glob interacts badly with forced-command wrappers`
- **Status**: `ready`
- **Source**: `Option B #8`
- **Topology**: `ssh cert principals + authorized principals + forced command`
- **Symptom**: `Some operators bypass intended command restrictions while others cannot log in at all after the same cert rotation, with logs showing successful pubkey auth for both shapes.`
- **Discoveries**: `'authorized_principals' file ordering makes a broad principal match short-circuit before a forced-command stanza is considered.; 'sshd -T' effective config differs from on-disk includes when 'Match' blocks apply only to subnets.; Certificate critical options include extensions parsed differently between server versions in a rolling upgrade.`
- **Evidence**: `trajectory=Coherence; command_level=edge-cases; cluster=Complex-System-Builds`
- **Exploits**: `Exploit 1: Two “what principal means” interpretations coexist across match ordering.; Exploit 4: Early match block choice locks command policy that later cert updates cannot override without full reload.`
- **Why hard**: `Authorization grammar interaction bugs, not crypto breaks.`
- **Main collapse risk**: `SSH reference doc transcription; RC6 on exact keyword tables if needed.`


#### 8. `AppArmor hat stack drops alternate profile on logrotate exec`
- **Status**: `ready`
- **Source**: `Option B #10`
- **Topology**: `AppArmor change_hat + exec transition + logrotate child`
- **Symptom**: `A constrained daemon escalates capabilities only in weekly log cycles, never in manual reload tests, with audit logs that look benign in the default summary view.`
- **Discoveries**: `'aa-status' snapshots differ if taken before versus after logrotate compressors fork.; A child inherits hats differently when the parent is not the expected long-lived PID after automated restarts.; 'journalctl -u app' filters severity and drops the AA_DENIED lines unless raw mode is used.`
- **Evidence**: `trajectory=Coherence; command_level=edge-cases; cluster=Complex-System-Builds`
- **Exploits**: `Exploit 4: Early profile cache choice at boot sticks through hat transitions that assume a single canonical parent.; Exploit 5: Post-deploy check greps 'aa-enforce' list, not effective exec transitions during rotation.`
- **Why hard**: `Profile state threaded through exec boundaries under maintenance triggers.`
- **Main collapse risk**: `AppArmor niche unless evidence is journal + 'dmesg' deny bursts.`


#### 9. `OCSP stapling stale tuple accepted by local nginx but rejected by mesh proxy`
- **Status**: `ready`
- **Source**: `Option B #12`
- **Topology**: `TLS stapling + multi-proxy SNI + clock skew tolerance`
- **Symptom**: `Mesh east-west shows bursty TLS errors migrating a service while north-south checks stay green on the same host.`
- **Discoveries**: `Upstream sends stapled responses cached in memory keyed by SNI while downstream validates freshness with tighter windows.; 'openssl s_client -status' from host network namespace disagrees with checks from the sidecar netns.; Proxy reload swaps stapling files atomically but workers keep old file descriptors until drain completes.`
- **Evidence**: `trajectory=Verification; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 8: Automation treats reload exit zero as stapling freshness everywhere.; Exploit 3: Quick curl against localhost validates cert chain but not OCSP age headers seen by mesh.`
- **Why hard**: `Multi-verifier TLS freshness diverges across network attachment points.`
- **Main collapse risk**: `Collapses into “turn off stapling” unless constrained.`


#### 10. `Kernel lockdown integrity mode vs custom kexec unsigned chain`
- **Status**: `ready`
- **Source**: `Option B #13`
- **Topology**: `lockdown LSM + kexec path + initrd signing drift`
- **Symptom**: `A “safe” remote kernel swap aborts half way through automation with conflicting messages about integrity policy across consoles.`
- **Discoveries**: `'dmesg' lines from lockdown appear only on the physical console buffer consumers seldom capture.; kexec load succeeds in testing user but fails under systemd unit with stricter 'NoNewPrivileges'.; Two initrd blobs exist; the loader path picks the unsigned copy when cmdline grows beyond a parsing threshold.`
- **Evidence**: `trajectory=Execution; command_level=edge-cases; cluster=Complex-System-Builds`
- **Exploits**: `Exploit 2: Re-running kexec load to gather diagnostics advances signatures on crash dumps, destroying prior evidence layout.; Exploit 7: Rescue playbook A disables lockdown; B fixes signing—each breaks the other when combined naively.`
- **Why hard**: `Destructive-if-repeated diagnostics on integrity-sensitive paths.`
- **Main collapse risk**: `Kernel policy encyclopedia; keep to dmesg + unit comparison evidence.`


#### 11. `WireGuard peer endpoint drift with stale conntrack after NAT rebinding`
- **Status**: `ready`
- **Source**: `Option B #14`
- **Topology**: `UDP wg + conntrack + CGNAT rebinding`
- **Symptom**: `Branch-office tunnels flap only during ISP maintenance windows while ping to the same host IP stays up outside the tunnel path.`
- **Discoveries**: `'wg show' reports latest handshake timestamps inconsistent with conntrack tuples still keyed on old ephemeral ports.; Policy routing sends keepalives on a table that updates minutes later than main routing.; A failover script flushes ct entries too aggressively, widening the outage.`
- **Evidence**: `trajectory=Coherence; command_level=edge-cases; cluster=Long-Horizon-Coherence`
- **Exploits**: `Exploit 4: Early endpoint selection locks a NAT mapping expectation that later rebinding invalidates silently.; Exploit 5: Uptime monitor validates ICMP only, not handshake age on the wireguard iface.`
- **Why hard**: `Stateful UDP identity across long-horizon NAT drift, not crypto breaks.`
- **Main collapse risk**: `ISP folklore unless ct/wg cross-evidence is required.`


#### 12. `PKCS#11 token login context not reset between CI jobs on shared runner`
- **Status**: `ready`
- **Source**: `Option B #15`
- **Topology**: `shared HSM slot + SO vs user PIN contexts + udev ACL races`
- **Symptom**: `Intermittent signing failures appear as “invalid signature” in downstream builds with no code changes, worse when job concurrency rises.`
- **Discoveries**: `PKCS#11 session login level leaks across job wrappers that reuse the same CK_SLOT_ID.; 'pkcs11-tool --login --test' passes while app uses C_Login with different user types on the same token.; udev reorders device nodes on USB hub resets, shifting readable slots per user.`
- **Evidence**: `trajectory=Execution; command_level=edge-cases; cluster=Complex-System-Builds`
- **Exploits**: `Exploit 1: CI “token ok” probe and app “sign ok” paths disagree on login context lifetime.; Exploit 10: Empty-label key handles resolve differently when token enumerates keys mid-refresh.`
- **Why hard**: `Hidden session-state threading on shared hardware token surfaces.`
- **Main collapse risk**: `HSM opera without synthetic pkcs11 traces.`


#### 13. `Per-namespace x509 verify hook trusts wrong trust store fd`
- **Status**: `ready`
- **Source**: `Option B #17`
- **Topology**: `Go crypto/x509 + mount ns + systemd ProtectSystem`
- **Symptom**: `A batch verifier accepts a partner cert that real-time scanners reject when run as the same user under different units.`
- **Discoveries**: `The verifier opens '/etc/ssl/certs' before 'ProtectSystem' remounts hide updated CA bundles.; 'strace -f' shows 'openat' returning different inodes for the same path across units.; 'SSL_CERT_FILE' is unset in one unit but inherited as empty string in another, triggering distinct defaulting paths.`
- **Evidence**: `trajectory=Coherence; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 1: Two trust anchors in effect—file descriptor cache vs disk truth.; Exploit 3: Quick 'openssl verify' uses '-CApath' distinct from the language runtime default.`
- **Why hard**: `Split policy authorities across namespaces without obvious CA "bugs."`
- **Main collapse risk**: `Language-runtime specific; RC6 on stdlib identifiers if needed.`


#### 14. `iptables-save snapshot omits table touched only by nft compatibility layer`
- **Status**: `ready`
- **Source**: `Option B #18`
- **Topology**: `nft-compat + legacy tooling + automation drift`
- **Symptom**: `Compliance export shows "clean" rules while live drops occur during maintenance, disappearing after a manual flush that “should be redundant.”`
- **Discoveries**: `'iptables-save' output differs from 'nft list ruleset' for the same policy epoch on hybrid hosts.; Ansible modules choose backend based on presence of '/etc/debian_version' not actual primary backend.; A nightly auditor runs inside a netns without the bridge rules affecting production.`
- **Evidence**: `trajectory=Verification; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 6: Auditor validates legacy save format only.; Exploit 7: Disabling nft-compat “fixes” exports but breaks legacy playbooks that assumed coexistence.`
- **Why hard**: `Wrong-format artifact: the compliance file is not the kernel's authoritative policy graph snapshot.`
- **Main collapse risk**: `Table trivia; constrain to paired tool outputs.`


#### 15. `getpeername UDS auth succeeds on wrong peer after fd passing race`
- **Status**: `ready`
- **Source**: `Option B #20`
- **Topology**: `SCM_RIGHTS + SO_PEERCRED + concurrent accept`
- **Symptom**: `A local IPC ACL intermittently grants admin actions to an unprivileged worker PID after heavy restart storms.`
- **Discoveries**: `The daemon caches 'getsockopt(SO_PEERCRED)' at accept time while the client 'exec's into a different binary before the first request bytes.; 'strace' on server shows 'recvmsg' ordering where SCM fds arrive before credentials message on some kernels.; A health check uses abstract socket name without checking sun_path prefix variant.`
- **Evidence**: `trajectory=Execution; command_level=edge-cases; cluster=Adversarial-Creative-Reasoning`
- **Exploits**: `Exploit 4: Early PID-to-auth mapping sticks across exec that replaces binary but reuses fd wiring unexpectedly.; Exploit 10: Empty credential ancillary edge case is ignored by quick fuzz tests.`
- **Why hard**: `Low-observability local trust rooted in peer identity freshness.`
- **Main collapse risk**: `Expert Linux IPC; needs curated strace.`


#### 16. `Passbolt/GnuPG agent forwarding socket hijack via path confusion`
- **Status**: `ready`
- **Source**: `Option B #22`
- **Topology**: `SSH agent forwarding + gnupg homedir + XDG paths`
- **Symptom**: `Signing from remote bastions occasionally attaches the wrong subkey without passphrase prompts operators expect, correlated with dotfile sync tools.`
- **Discoveries**: `'SSH_AUTH_SOCK' and 'GPG_AGENT_INFO' disagree when systemd user session overrides XDG for one but not the other.; 'gpgconf --list-dirs' in non-login shells points at a socket forwarded from another user’s mux.; 'ss -xlp' shows listeners with permissions that differ between Debian derivative and RHEL derivative defaults.`
- **Evidence**: `trajectory=Coherence; command_level=edge-cases; cluster=Complex-System-Builds`
- **Exploits**: `Exploit 1: Two agent authorities both answer requests; only one matches intended policy.; Exploit 4: Early multiplex session choice pins sockets that a later 'cd' to a shared workspace corrupts contextually.`
- **Why hard**: `Split decode of “which secret material is actually consulted.”`
- **Main collapse risk**: `Product naming; keep generic “agent forwarding + gpg homedir.”`


#### 17. `Supplicant EAP-TLS OCSP hook ignores intermediate AIA divergence`
- **Status**: `ready`
- **Source**: `Option B #24`
- **Topology**: `802.1X supplicant + TLS stack + OCSP via Wi-Fi path`
- **Symptom**: `Corporate Wi-Fi auth succeeds for most laptops but a batch fail only on one SSID after a CA rotation, with wpa_supplicant logs that look superficially identical.`
- **Discoveries**: `Intermediate chain differs because AIA fetch from Wi-Fi goes through a captive portal path on first association only.; 'openssl ocsp' from wired uplink passes while over-the-air path hits a transparent proxy with stale intermediates.; 'nmcli' shows connected while 'eapol_test' shows intermittent phase2 failures in a tight loop.`
- **Evidence**: `trajectory=Coherence; command_level=edge-cases; cluster=Long-Horizon-Coherence`
- **Exploits**: `Exploit 1: Chain construction authority differs by first-hop network path freshness.; Exploit 8: Association “completed” events precede OCSP validation completion.`
- **Why hard**: `Environment-bifurcated verification on an embedded TLS profile.`
- **Main collapse risk**: `Wi-Fi lab dependence; supply synthetic wpa logs.`


#### 18. `Signed kernel module vs DKMS post-build hook strip mismatch`
- **Status**: `ready`
- **Source**: `Option B #25`
- **Topology**: `module signing + DKMS + debug sections`
- **Symptom**: `A vendor driver loads on some kernels but 'modprobe' fails with signature errors after “successful” DKMS build logs.`
- **Discoveries**: `Post-build strip removes sections that signing scripts expect, without failing the DKMS recipe.; 'modinfo' signature field present while 'hexdump' payload tail mismatches what 'sign-file' produced.; Two toolchains installed; DKMS picks the wrong 'strip' via PATH depending on login vs cron.`
- **Evidence**: `trajectory=Execution; command_level=edge-cases; cluster=Complex-System-Builds`
- **Exploits**: `Exploit 2: Re-running 'dkms build' overwrites intermediate .ko files, erasing pre-strip artifacts needed to diff.; Exploit 7: Kernel MAINTAINER script disables enforce + loads module "to test" and masks signing failure class.`
- **Why hard**: `Destructive build phases change what signing means relative to on-disk module.`
- **Main collapse risk**: `Kernel module cookbook unless tasks require modinfo/hex evidence.`


#### 19. `Service mesh JWT issuer URL http-vs-https scheme confusion after redirect`
- **Status**: `ready`
- **Source**: `Option B #26`
- **Topology**: `JWT validation + discovery document + redirect chain`
- **Symptom**: `Internal APIs return 401 bursts only for clients deployed before a certain date, while newer agents work, without token clock skew.`
- **Discoveries**: `Issuer string in token uses 'https://' while JWKS retrieval followed a one-hop 'http://' redirect cached in the sidecar.; Two sidecar versions normalize issuer trailing slashes differently.; 'curl' manual checks against well-known succeed while data-plane invokes stale cluster DNS that still points to the old issuer host.`
- **Evidence**: `trajectory=Coherence; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 1: String identity of issuer vs network retrieval path diverge post-redirect.; Exploit 5: Synthetic uptime canary validates TLS to API but not JWKS fetch path equivalence.`
- **Why hard**: `Split decode between token claim identity and key retrieval trust roots.`
- **Main collapse risk**: `OAuth/OIDC trivia; RC6 on provider brands.`


#### 20. `Landlock sandbox reports success but inherits permissive parent domain`
- **Status**: `ready`
- **Source**: `Option B #27`
- **Topology**: `Landlock LSM + exec domain + inherited ruleset`
- **Symptom**: `A tool claims "sandboxed mode" enabled yet still reads secrets from an unexpected path only when launched from a legacy wrapper.`
- **Discoveries**: `Child re-exec clears Landlock rules while parent thought 'prctl' state would compose across exec kind actually used.; 'cat /proc/self/attr/landlock' disagrees between threads briefly during 'clone' used by a thread pool.; A feature probe uses 'uname' success as proof of sandboxing.`
- **Evidence**: `trajectory=Verification; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 6: Local checker validates “rules installed” counter, not effective access graph after re-exec.; Exploit 4: Wrapper chooses '_GNU_SOURCE' exec path that resets LSM domain implied by README.`
- **Why hard**: `Premature completion bait on self-reported sandbox flags vs kernel attr state.`
- **Main collapse risk**: `New LSM; needs kernel version floor in task constraints.`


#### 21. `Audit beatless ebpf trace drops events when map resize races loader`
- **Status**: `ready`
- **Source**: `Option B #29`
- **Topology**: `eBPF map batch + ring buffer sizing + verifier reload`
- **Symptom**: `SIEM misses bursts of 'connect()' denials during policy rollouts though sampling shows steady overall rates.`
- **Discoveries**: `Loader doubles map size while consumer still maps old fd via pinned path.; 'bpftool map dump' shows zeros while '/sys/fs/bpf' pin has non-zero stats on alternate pinned name.; A “healthy” check reads prog id existence only, not tail loss counters.`
- **Evidence**: `trajectory=Execution; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 8: Agent restart is judged complete before all per-CPU buffers realloc.; Exploit 6: Dashboard integrates rate/sec without loss counters from map metadata.`
- **Why hard**: `Verification surface does not include drop semantics on resize.`
- **Main collapse risk**: `eBPF expertise wall; give curated map stats snapshots.`


#### 22. `git signing late key expiration versus tag timestamp grace`
- **Status**: `ready`
- **Source**: `Option B #30`
- **Topology**: `OpenPGP + git tag signatures + keyserver refresh delays`
- **Symptom**: `Release automation rejects signed tags that developers swear are valid in their local 'git verify-tag' output, but only on CI runners in one region.`
- **Discoveries**: `CI uses keybox with 'ignore-time-conflict' differing from developer gpg.conf.; Tag object TaggerDate vs commit author date differs across rebase workflows affecting not_valid_after windows.; Keyserver pool returns different subkey binding signatures under split-brain DNS.`
- **Evidence**: `trajectory=Verification; command_level=edge-cases; cluster=Long-Horizon-Coherence`
- **Exploits**: `Exploit 3: CI verifies '--raw' tag object only, not the closure of signing subkey validity at verification instant.; Exploit 5: Slack notification posts "green verify" from a developer laptop path, not CI.`
- **Why hard**: `Split policy/time authorities on signed git objects.`
- **Main collapse risk**: `PGP rabbit hole; keep to git+pgp logs not rfc open.`


#### 23. `Windows-style ACL emulation on Samba hides Unix mode enforcement gap`
- **Status**: `ready`
- **Source**: `Option B #32`
- **Topology**: `vfs_acl_xattr + NFS re-export + mode regression`
- **Symptom**: `A migration “preserved permissions” yet data exfiltration checks show world-readable sensitive files when accessed via one protocol path only.`
- **Discoveries**: `'getfacl' over SMB shows restrictive NT ACL mapping while NFS re-export uses underlying POSIX mode bits the migration reset.; 'smbcacls' and 'ls -l' disagree depending on 'follow symlinks' server setting.; Backup tool captures xattr ACLs but restore order applies POSIX modes last, widening access until a manual resync.`
- **Evidence**: `trajectory=Verification; command_level=edge-cases; cluster=Adversarial-Creative-Reasoning`
- **Exploits**: `Exploit 1: Two permission truths—synthetic ACL view vs inode mode on fast path.; Exploit 3: Auditor script 'stat's via python os.access using real uid differing from service uid.`
- **Why hard**: `Authority split across protocol stacks on the same files.`
- **Main collapse risk**: `Samba config zoo; constrain to three-client cross-check protocol.`


#### 24. `sudoers LDAP nesting resolves differently than local nss`
- **Status**: `refined`
- **Source**: `Option B repairable seed retained with status refined (review strengthening notes in Option B artifact)`
- **Topology**: `sss nss + sudoers ldap + netgroup expansion`
- **Symptom**: `Automation users lose sudo selectively on freshly imaged hosts while interactive admins retain, with no clear pam error beyond generic failure.`
- **Discoveries**: `'sudo -l' path queries LDAP with a different hostname canonicalization than 'id -Gn'.; Netgroup expansion hits a negative cache that only triggers on cold boot ordering with stale DNS.; A local 'sudoers.d' drop-in duplicates an Allow directive but with a narrower Cmnd_Alias that wins unexpectedly.`
- **Evidence**: `trajectory=Coherence; command_level=edge-cases; cluster=Complex-System-Builds`
- **Exploits**: `Exploit 1: Two identity expansions (interactive vs remote automation) disagree hour-to-hour.; Exploit 10: Empty netgroup edge case yields allow in one resolver and deny in another.`
- **Why hard**: `Policy resolution across multiple backends and caches.`
- **Main collapse risk**: `Environment too org-specific; constrain to logs + 'sudo -V'/'sssctl' artifacts.`


#### 25. `TPM PCR policy mismatch after firmware setting toggled without reseal`
- **Status**: `refined`
- **Source**: `Option B repairable seed retained with status refined (review strengthening notes in Option B artifact)`
- **Topology**: `TPM PCR policy + LUKS binding + firmware flag`
- **Symptom**: `Full-disk unlock prompts appear on laptops after a “recommended” firmware toggle, while helpdesk scripts insist keys are present.`
- **Discoveries**: `PCR7 changes when secure boot keys are reshuffled but sealing metadata still references old policy handles.; Clevis pin config pins PCRs that exclude the changed measurement class.; 'tpm2_pcrread' output matches expectations on warm boots but not cold boots after setting change.`
- **Evidence**: `trajectory=Verification; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 2: Re-running auto-unseal enrollment overwrites backup blobs, removing rollback to prior policy.; Exploit 5: Health check “TPM present” passes without testing policy unseal success.`
- **Why hard**: `Measured boot coupling with destructive enrollment if mishandled.`
- **Main collapse risk**: `RC6-heavy; avoid turning into tpm2 tool encyclopedia.`


#### 26. `Passkeys/FIDO credProtect level mismatch across services`
- **Status**: `refined`
- **Source**: `Option B repairable seed retained with status refined (review strengthening notes in Option B artifact)`
- **Topology**: `webauthn extension negotiation + split RP configs + token firmware`
- **Symptom**: `Some users authenticate while others hit retries after an IdP upgrade even though the same laptop model is used org-wide.`
- **Discoveries**: `One RP requests 'credProtect=2' while the IdP broker strips unknown extensions during proxy signing.; Browser attestation caches differ between profiles on the same OS image.; Server logs show successful WebAuthn for sessions that still fail a second downstream SAML bridge.`
- **Evidence**: `trajectory=Verification; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 1: Client and server “what was negotiated” truths diverge at the extension byte level.; Exploit 6: Canary page validates signature format only, not extension presence bits.`
- **Why hard**: `Freshness and semantics across multi-hop auth stacks, not breaking crypto.`
- **Main collapse risk**: `RC6: avoid naming vendor token behaviors; use wire captures.`


#### 27. `DMARC aggregate vs forensic reports disagree during subdomain alignment changes`
- **Status**: `refined`
- **Source**: `Option B repairable seed retained with status refined (review strengthening notes in Option B artifact)`
- **Topology**: `SPF/DKIM alignment + DMARC policy + DNS caching layers`
- **Symptom**: `Mail ops flips a subdomain policy; some receivers accept while others bounce, and internal reporting dashboards contradict each other for the same hour bucket.`
- **Discoveries**: `Aggregate RUA ZIPs show pass while sampled message headers show fail depending on which forwarding hop signed.; Negative caching TTLs differ between on-prem resolver and cloud forwarding DNS.; A third-party relay rewrites headers breaking the alignment the dashboard counts as “strict.”`
- **Evidence**: `trajectory=Verification; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 1: Multiple “pass” definitions coexist across reporting products and live delivery.; Exploit 6: Exec summary averages DMARC pass rate without per-message identity keys.`
- **Why hard**: `Email auth is multi-authority; easy to fake completion with wrong KPIs.`
- **Main collapse risk**: `Deliverability consulting vibe unless made artifact-driven.`


#### 28. `ACME authz reuse after domain redelegation window`
- **Status**: `refined`
- **Source**: `Option B repairable seed retained with status refined (review strengthening notes in Option B artifact)`
- **Topology**: `ACME DNS challenge + stale authz + partial propagation`
- **Symptom**: `Certificates continue issuing for a hostname transferred to a new DNS provider during a cutover weekend, without alarms on the old automation account.`
- **Discoveries**: `A CA account still holds valid authz objects while NS glue at TLD disagrees with authoritative answers regionally.; 'dig +trace' from three sites yields distinct NS sets during TTL overlap.; Renewal jobs log success using HTTP-01 while apex remains on stale AAAA only at one POP.`
- **Evidence**: `trajectory=Execution; command_level=edge-cases; cluster=Adversarial-Creative-Reasoning`
- **Exploits**: `Exploit 4: Early NS choice commits a challenge path that later delegation invalidates for some clients but not the issuer.; Exploit 5: Dashboard counts “cert expiries” not “authz freshness tied to DNS sovereignty.”`
- **Why hard**: `Freshness and ownership across delegation—not breaking account keys.`
- **Main collapse risk**: `Real-Internet flake; require simulated DNS partitions in harness.`


#### 29. `MemoryTagging / MTE mismatch between compiler flags and runtime loader`
- **Status**: `refined`
- **Source**: `Option B repairable seed retained with status refined (review strengthening notes in Option B artifact)`
- **Topology**: `ARM MTE + ELF note + interpreter selection`
- **Symptom**: `A security-critical binary "passes" CI hardening scans but trips sporadic SIGSEGV only on devices shipped with a newer firmware line.`
- **Discoveries**: `'readelf -n' shows a GNU property segment the loader ignores when PT_INTERP points to a mismatched interpreter build.; 'dmesg' records tag check faults only when a dependent '.so' was built without tags but the main binary expects them.; 'gdb' backtraces look clean until 'set environment' toggles change tag fault handling.`
- **Evidence**: `trajectory=Verification; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 3: Static scanner validates main ELF only, not transitive SO graph tag contracts.; Exploit 7: Rebuild with tags on main binary without rebuilding all SOs "works on dev board."`
- **Why hard**: `Variant ladder across ELF build graph and loader behavior.`
- **Main collapse risk**: `Arch-specific; label as ARM64-only task or provide QEMU trace pack.`


#### 30. `OpenShift SCC vs Pod Security Admission silent downgrade on CRD defaulting`
- **Status**: `refined`
- **Source**: `Option B repairable seed retained with status refined (review strengthening notes in Option B artifact)`
- **Topology**: `K8s admission chain + CRD conversion + pod template defaults`
- **Symptom**: `Namespace claims "restricted" posture while workloads still launch with unsafe fields that audits miss until a CVE scanner runs in live cluster mode.`
- **Discoveries**: `Mutating webhook order differs between upgrades; defaults land after validation on one minor but before on another.; 'kubectl explain' shows new defaults not reflected in checked-in helm values.; 'kube-apiserver' audit logs omit fields dropped as “too large” in some configurations.`
- **Evidence**: `trajectory=Verification; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 6: Policy-as-code checks YAML on disk, not effective pod spec at admission time.; Exploit 5: Exec dashboard shows “compliant namespaces” averaged across clusters without per-version control plane skew.`
- **Why hard**: `Verifier-bypass where local policy files are not the admission truth.`
- **Main collapse risk**: `K8s version coupling; RC6 on vendor distro naming.`


#### 31. `YubiKey PIV PIN policy vs piv-agent caching stale public key handles`
- **Status**: `refined`
- **Source**: `Option B repairable seed retained with status refined (review strengthening notes in Option B artifact)`
- **Topology**: `PIV slot + SSH pubkey + agent cache`
- **Symptom**: `SSH auth flips between two certs mapped to the same username depending on which workstation kiosk was used last, with no central account changes.`
- **Discoveries**: `'ssh-add -L' order differs from 'ykman piv keys list' after slot regeneration without agent flush.; Server 'authorized_keys' permits multiple ssh-rsa lines differing only in comment fields sorting wrong.; PIN retry counters differ between PIV applet reads via NFC vs USB.`
- **Evidence**: `trajectory=Coherence; command_level=edge-cases; cluster=Complex-System-Builds`
- **Exploits**: `Exploit 1: Two pubkey truths—token vs agent memory—coexist during rotation.; Exploit 10: Empty slot edge case yields fallback to corporate backup key unexpectedly.`
- **Why hard**: `Revocation/freshness drift across physical token interactions.`
- **Main collapse risk**: `Vendor hardware naming; generalize to “PIV slot + ssh-agent.”`


#### 32. `Notary v1 trust pin vs registry mirror tag mutable collision`
- **Status**: `refined`
- **Source**: `Option B repairable seed retained with status refined (review strengthening notes in Option B artifact)`
- **Topology**: `content trust + registry mirror + tag mutability ban`
- **Symptom**: `Image pulls fail after a mirror promotion with "trust data insufficient" while digests match in one tool and not another.`
- **Discoveries**: `TUF targets.json version bumps on source registry while mirror serves stale trust collection for minutes.; 'notary' CLI uses http_proxy differently than containerd CRI plugin.; Tag immutability is enforced at API layer but not at storage backend replication jobs.`
- **Evidence**: `trajectory=Coherence; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 8: Mirror "ready" probe pulls manifest only, not trust collection freshness.; Exploit 1: Digest identity vs TUF role version identity diverge transiently.`
- **Why hard**: `Supply chain freshness across two parallel metadata planes.`
- **Main collapse risk**: `Legacy Notary; might frame as generic TUF+registry.`


#### 33. `Brokered Kerberos S4U2self uses wrong enterprise principal in mixed UPN world`
- **Status**: `replacement`
- **Source**: `Generated to fill bank; 'security' subsystem diversity`
- **Topology**: `S4U2self + enterprise principals + GC skew`
- **Symptom**: `Service-to-service auth succeeds for western users but flaps for migrated accounts with same samAccountName, with KDC logs that look like generic preauth noise until correlation IDs are aligned.`
- **Discoveries**: `KDC chooses enterprise principal encoding based on which global catalog replica answered first.; Application caches TGT keying on short name while broker requests long UPN inconsistently.; 'klist' on app host shows tickets while PAC validation fails downstream in Java with mismatched name type.`
- **Evidence**: `trajectory=Coherence; command_level=edge-cases; cluster=Complex-System-Builds`
- **Exploits**: `Exploit 1: Issued ticket identity and consuming service’s name interpretation diverge.; Exploit 4: Early GC affinity commits principal choice later replicas invalidate.`
- **Why hard**: `Delegation chain splits on principal string form, not crypto failure.`
- **Main collapse risk**: `AD archaeology; constrain to ticket + PAC byte symptoms.`
- **RC6 discipline**: `RC6: avoid publishing exact AD attribute spellings; use observable KRB errors.`


#### 34. `OPA bundle signature verified but data plane policy hash stale`
- **Status**: `replacement`
- **Source**: `Generated to fill bank; 'security' subsystem diversity`
- **Topology**: `OPA bundle + sidecar hot reload + sha cache`
- **Symptom**: `Admission decisions drift after a policy rollout rolled back; Kubernetes objects show allow while corporate SOC queries say deny for the same user attributes minutes apart.`
- **Discoveries**: `Bundle tarball verifies with cosign while OPA stores compiled policy under a filename colliding with prior revision symlink swap.; Sidecar 'POST /' health misses policy bundle activation epoch exposed only on metrics endpoint not scraped.; Different replicas load bundles from ConfigMap vs disk mirror on node disk pressure events.`
- **Evidence**: `trajectory=Verification; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 6: Fleet checks signed bundle artifact only, not effective Rego revision in each pod.; Exploit 8: Reload completes HTTP OK before compile finishes, leaving mixed revision across workers.`
- **Why hard**: `Supply-chain integrity vs runtime activation truth on distributed enforcers.`
- **Main collapse risk**: `Cloud-brand anchor; generalize to signed bundle + lazy activation.`


#### 35. `Vault KV v2 metadata read_mask hides undeleted secret generation`
- **Status**: `replacement`
- **Source**: `Generated to fill bank; 'security' subsystem diversity`
- **Topology**: `vault ACL + kv v2 + masked list`
- **Symptom**: `Compliance scan reports secrets removed while forensic recovery on a clone still surfaces older generations accessible through an automation path operators forgot.`
- **Discoveries**: `list permission denied masks presence of undeleted versions in UI while direct read by numeric version succeeds for breaker-glass role.; Performance standby serves cached metadata without bumping cache epoch on delete event.; Seal migration changes encryption context; recovery tools compare plaintext checksum only.`
- **Evidence**: `trajectory=Coherence; command_level=edge-cases; cluster=Long-Horizon-Coherence`
- **Exploits**: `Exploit 1: Audit list of ‘no keys’ and ability to read versioned material coexist.; Exploit 2: Running forced sync to ‘fix’ DR standby replays deletes in wrong order, reviving pointers.`
- **Why hard**: `Revocation narrative vs multi-generation secret storage under ACL masks.`
- **Main collapse risk**: `Product-named collapse; RC6 strip in instruction.`
- **RC6 discipline**: `RC6: keep vendor secret-store UI steps out of learner-facing instruction text.`


#### 36. `Istio AuthorizationPolicy OR-rule short-circuit hides narrower DENY`
- **Status**: `replacement`
- **Source**: `Generated to fill bank; 'security' subsystem diversity`
- **Topology**: `istio authz + xfcc + rule ordering`
- **Symptom**: `Canary subject should be blocked after HR incident but traffic still reaches internal API in one cluster only; other clusters identical YAML.`
- **Discoveries**: `Proto merge order differs for repeated 'to' clauses across Istio minor versions on the cluster skew.; XFCC trust perimeter includes a mesh-wide identity that satisfies the OR clause before DENY evaluated in one build.; 'istioctl authz check' uses cached discovery snapshot not refreshed after silent push failure.`
- **Evidence**: `trajectory=Execution; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 4: Early pushed policy snapshot locks OR semantics newer control plane would evaluate differently.; Exploit 6: E2E test asserts HTTP 403 on wrong path pattern missing the leaky route.`
- **Why hard**: `Distributed authz grammar vs identity headers across fleet skew.`
- **Main collapse risk**: `Mesh YAML golf; supply 'istioctl' diff + access log excerpts only.`


#### 37. `age plugin accepts passphrase file mode 0644 in CI without failing closed`
- **Status**: `replacement`
- **Source**: `Generated to fill bank; 'security' subsystem diversity`
- **Topology**: `age plugin + CI secret file perms + wrapper trust`
- **Symptom**: `Secrets rotation pipeline green while internal red team reads wrapped keys off shared runners; defenders see successful decryptions in logs.`
- **Discoveries**: `CI umask + docker volume mount preserves world-readable wrapper path only on nightly branch.; age-plugin silently ignores chmod failures on FUSE-backed workspace.; Verifier script checks ciphertext checksum, not private key inode mode.`
- **Evidence**: `trajectory=Verification; command_level=edge-cases; cluster=Adversarial-Creative-Reasoning`
- **Exploits**: `Exploit 3: Green check validates message MAC without filesystem privilege context.; Exploit 6: Auditor scrapes KMS audit only, not runner filesystem metadata.`
- **Why hard**: `Crypto success despite hostile filesystem context on automation hosts.`
- **Main collapse risk**: `Turns into chmod lecture unless runner evidence is binding.`


#### 38. `Step-ca admin resets one root; intermediate cross-sign still chains to old anchor in clients`
- **Status**: `replacement`
- **Source**: `Generated to fill bank; 'security' subsystem diversity`
- **Topology**: `step-ca + cross-signed roots + trust store refresh`
- **Symptom**: `mTLS between batch jobs breaks only on freshly imaged nodes while legacy nodes work; both claim same CA URL.`
- **Discoveries**: `New nodes cache full chain A while intermediates still issue under chain B until operator clicks reconcile not run in IaC.; step-ca federated logs show issuance success while verifying OCSP responder points at old issuer id.; 'step certificate inspect' on host vs in init container sees different PEM order via env override.`
- **Evidence**: `trajectory=Coherence; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 1: Multiple valid chains coexist; only one matches mandated SPIFFE trust bundle.; Exploit 8: Provisioning ‘done’ when kube secret writes, not when all nodes refreshed trust stores.`
- **Why hard**: `PKI lineage drift across issuance, OCSP, and node bootstraps.`
- **Main collapse risk**: `Stack-specific; abstract to cross-signed CA rotation story.`


### Category: `debugging`

#### 1. `Interpreter picks older ld.so.cache after partial glibc postinst abort`
- **Status**: `ready`
- **Source**: `Option B #1`
- **Topology**: `ldconfig cache + dpkg trigger ordering + CAP_SYS_CHROOT`
- **Symptom**: `One long-running daemon resolves shared libraries differently than a fresh shell on the same host; 'ldd' looks fine in the user’s login but the service fails relocations until reboot.`
- **Discoveries**: `'/etc/ld.so.cache' mtime advanced while inode contents visible to the daemon mmap stayed old until SIGHUP.; 'strace -e openat' on the daemon shows 'ENOENT' on soname paths present in cache for new PIDs.; 'readelf -d' on the binary shows 'RUNPATH' absent but 'LD_LIBRARY_PATH' empty differences across unit vs ssh.`
- **Evidence**: `trajectory=Coherence; command_level=edge-cases; cluster=Complex-System-Builds`
- **Exploits**: `Exploit 4: Early mmap of ld cache in PID 1 descendants survives partial packaging replace.; Exploit 1: Two loader truths—daemon address space vs regenerated cache on disk.`
- **Why hard**: `ABI/loader coupling with self-hiding mmap lifetime.`
- **Main collapse risk**: `“Just restart the service” trivial unless forbidden or costly in story.`


#### 2. `Core dump masked by ulimit inheritance across sudo boundary`
- **Status**: `ready`
- **Source**: `Option B #2`
- **Topology**: `PAM limits + sudoers env_keep + systemd LimitCORE`
- **Symptom**: `A native crash reproduces under tester account with a core file, but the production user never writes cores despite identical binary checksum; gdb remote hints at SIGILL only in logs.`
- **Discoveries**: `'cat /proc/pid/limits' differs between interactive sudo and systemd unit despite same Effective UID.; 'coredumpctl' shows no entry while 'dmesg' has a one-line segfault note killed by core pattern to '/dev/null' via late sysctl.; 'sudo -i' vs 'sudo -E' changes inherited 'SUDO_UID' affecting apport hooks.`
- **Evidence**: `trajectory=Verification; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 6: Playbook verifies segfault presence via logs only, not core availability.; Exploit 4: Early session choice fixes core pattern environment hidden from later diagnostics.`
- **Why hard**: `Low-observability of crash evidence path across privilege boundaries.`
- **Main collapse risk**: `Admin hygiene story; anchor in '/proc' limits evidence.`


#### 3. `Stale build-id in split debug package after partial rpm install`
- **Status**: `ready`
- **Source**: `Option B #3`
- **Topology**: `debuginfo mismatch + eu-unstrip + dwz`
- **Symptom**: `Profiling shows impossible stacks referencing source lines from an older release while the binary 'strings' output matches current release banners.`
- **Discoveries**: `'eu-readelf -n' build-id differs between '/usr/bin' binary and '/usr/lib/debug' companion when transactions interleave.; 'gdb' downloads debuginfo by build-id but caches extracted paths keyed incorrectly after 'dnf clean'.; 'readelf --gnu-debuglink' points at a file that was replaced by a zero-length error stub during mirror glitch.`
- **Evidence**: `trajectory=Coherence; command_level=edge-cases; cluster=Long-Horizon-Coherence`
- **Exploits**: `Exploit 1: Two debugging truths—symbol server metadata vs installed file identity.; Exploit 2: Reinstalling debuginfo rotates caches and erases the snapshot proving mismatch epoch.`
- **Why hard**: `ABI/debug coupling—misleading stacks without corrupt executables.`
- **Main collapse risk**: `Distro-specific packaging; frame as generic package txn.`


#### 4. `vfork-exec chain loses ptrace attach window on masked signals`
- **Status**: `ready`
- **Source**: `Option B #4`
- **Topology**: `vfork + ptrace + signal masks + job control`
- **Symptom**: `An intermittent deadlock in a legacy build tool disappears under 'strace -f' but persists in CI; attaching gdb mid-build “works once."`
- **Discoveries**: `Child temporarily shares address space while parent blocks SIGCHLD handling in a way ptrace changes timing of.; '/proc/pid/status' shows 'State: t+' only in failing runs without tracer.; Build script background pipeline and 'wait -n' ordering diverge under pseudo-tty allocation.`
- **Evidence**: `trajectory=Execution; command_level=edge-cases; cluster=Complex-System-Builds`
- **Exploits**: `Exploit 4: Early signal mask in parent survives vfork semantics that later tool versions alter.; Exploit 9: Observing via strace perturbs preemption enough to hide vfork scheduling bug.`
- **Why hard**: `Wait discipline + low-observability without perturbing the race.`
- **Main collapse risk**: `Obscure shell/build interaction; constrain reproducibility.`


#### 5. `dlopen plugin resolves symbols from wrong RTLD_GLOBAL ancestor`
- **Status**: `ready`
- **Source**: `Option B #5`
- **Topology**: `dynamic linker scope + plugin SO + hidden visibility`
- **Symptom**: `A plugin crashes deep in a math routine whose source did not change; bisect lands on unrelated commits that only altered plugin load order.`
- **Discoveries**: `'LD_DEBUG=symbols' shows two distinct symbol resolutions for the same name across plugin reload.; 'nm -D' on the plugin lists undefined symbols satisfied by an older SONAME still resident.; 'dl_iterate_phdr' ordering disagrees with 'lsof' mapping of mapped files post-'dlclose'.`
- **Evidence**: `trajectory=Coherence; command_level=edge-cases; cluster=Adversarial-Creative-Reasoning`
- **Exploits**: `Exploit 7: Two fix branches—'RTLD_LOCAL' vs visibility fixes—each breaks a different plugin set.; Exploit 1: Global symbol table truth vs plugin author's intended encapsulation.`
- **Why hard**: `Loader global symbol pollution with long-horizon order dependence.`
- **Main collapse risk**: `Expert linker; supply LD_DEBUG excerpts as artifacts.`


#### 6. `initrd switch_root leaves orphaned file descriptors to old root`
- **Status**: `ready`
- **Source**: `Option B #7`
- **Topology**: `dracut switch_root + leaked fds + namespace pinning`
- **Symptom**: `Disk cannot be unmounted cleanly on shutdown; 'losetup' cleanup fails referencing busy paths even when no mounts list them.`
- **Discoveries**: `'ls -l /proc/1/fd' shows references into deleted but busy inodes under old root.; 'findmnt' omits the mount because it is not in the current tree but still holds an open dir fd.; A udev helper inherited fds across the switch without CLOEXEC.`
- **Evidence**: `trajectory=Execution; command_level=edge-cases; cluster=Long-Horizon-Coherence`
- **Exploits**: `Exploit 4: Early daemon start before switch_root pins devices that later maintenance cannot detach.; Exploit 8: Shutdown script exits after sending signals but before long umount waits finish.`
- **Why hard**: `Causal chain from early boot fd inheritance to late maintenance failure.`
- **Main collapse risk**: `Initrd expertise; evidence via '/proc/1/fd' and 'lsof' patterns.`


#### 7. `clang ASAN LeakSanitizer atexit ordering hides real leak behind false giant leak`
- **Status**: `ready`
- **Source**: `Option B #8`
- **Topology**: `sanitizer atexit + static dtors + custom allocator`
- **Symptom**: `Leak reports differ between '-fsanitize=address' runs when linking order changes despite identical source inputs to the translation units users suspect.`
- **Discoveries**: `'ASAN_OPTIONS=halt_on_error=0' interacts with 'LSAN' suppression files loaded twice when preload order differs.; 'nm' shows duplicate static initializers when LTO partitions merge unpredictably.; 'llvm-symbolizer' resolves to wrong CU when debug fission '.dwo' missing.`
- **Evidence**: `trajectory=Verification; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 5: CI posts leak summary from truncated log tail only.; Exploit 7: Disabling LTO “fixes” leak report by changing destructor order, not fixing memory.`
- **Why hard**: `Misleading verification from sanitizer lifecycle vs build graph.`
- **Main collapse risk**: `Compiler-version fragile; pin toolchain in task.`


#### 8. `TCP_INFO ss output disagrees with packet capture on sack reneging`
- **Status**: `ready`
- **Source**: `Option B #9`
- **Topology**: `kernel tcp_diag + offloaded NIC + sack`
- **Symptom**: `Support claims “no retransmits” while microbursts of latency align with sack renege patterns only visible in pcaps.`
- **Discoveries**: `'ss -ti' min RTT fields differ when hardware offload reorders reporting cadence.; 'tcpdump -ttt' shows renege while 'nstat' counters the operator watches stay flat.; BPF cgroup egress program shapes cwnd counters tools misread.`
- **Evidence**: `trajectory=Verification; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 6: Dashboard ingests 'ss' poll only, not pcap-derived RTO events.; Exploit 3: Synthetic iperf validates throughput, not tail latency under renege.`
- **Why hard**: `Low-observability: tool claims TCP health while pcap disagrees.`
- **Main collapse risk**: `Needs attached pcap excerpt as ground truth.`


#### 9. `perf kmem leak false positive from slab alias after kmemleak false negative`
- **Status**: `ready`
- **Source**: `Option B #11`
- **Topology**: `perf kmem + slab alias + kmemleak scan timing`
- **Symptom**: `Memory investigations oscillate between “driver leak” and “tooling noise” as two kernel introspection tools contradict nightly.`
- **Discoveries**: `'perf kmem' attributes allocations to wrong call sites when CONFIG_SLUB_DEBUG aliases slabs.; 'kmemleak scan' disabled during critical section the module docs forgot to mention.; 'slabtop' objects count grows while 'cat /proc/meminfo' Slab line flatlines briefly.`
- **Evidence**: `trajectory=Verification; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 5: Exec report averages perf sample stacks without slab alias awareness.; Exploit 6: Pass/fail gate uses kmemleak “0 new leaks” without comparing scan epochs.`
- **Why hard**: `Robust verification trap: green kmemleak with wrong scan assumptions.`
- **Main collapse risk**: `Kernel debug options unavailable in prod; use lab kernel config.`


#### 10. `Fork bomb protection ulimit vs systemd tasks accounting mismatch`
- **Status**: `ready`
- **Source**: `Option B #12`
- **Topology**: `pids cgroup + RLIMIT_NPROC + rapid fork churn`
- **Symptom**: `A service hits “resource temporarily unavailable” without hitting TasksMax in 'systemctl show'; graphs show CPU idle while logs stop.`
- **Discoveries**: `'EAGAIN' on 'clone' arises from RLIMIT_NPROC before cgroup pids.max triggers.; '/proc/sys/kernel/threads-max' interaction differs after sysctl tuning in tuning profiles.; 'systemd-cgtop' vs 'ps -L' thread counts diverge during iowait-heavy fork storms.`
- **Evidence**: `trajectory=Execution; command_level=edge-cases; cluster=Complex-System-Builds`
- **Exploits**: `Exploit 3: Health check spawns a subprocess and mistakenly confirms “healthy” when parent cannot fork further children.; Exploit 4: Early sysctl profile choice masks which limit trips first under burst.`
- **Why hard**: `Navigate coupling between RLIMIT and cgroup pid controllers.`
- **Main collapse risk**: `Sounds like capacity planning unless evidence differentiates limits.`


#### 11. `inotify IN_MOVE_SELF storm loses half of batch renames`
- **Status**: `ready`
- **Source**: `Option B #14`
- **Topology**: `inotify batch + cross-directory rename + fanotify mask`
- **Symptom**: `A watcher reports “all files processed” while downstream checksum DB shows systematic gaps under synthetic migration load tests.`
- **Discoveries**: `Event stream coalesces MOVE pairs depending on queue sizing and 'IN_EXCL_UNLINK' usage.; 'strace' shows 'read' returning partial structs when buffer sizing mismatches 'sizeof(struct inotify_event)+name'.; Reprocessing script uses cookie pairing that wraps at 16 bits under load.`
- **Evidence**: `trajectory=Execution; command_level=edge-cases; cluster=Complex-System-Builds`
- **Exploits**: `Exploit 8: Supervisor marks job done when writer closes fd, not when watcher drains queue.; Exploit 2: Clearing queue aggressively drops paired events needed to reconstruct final paths.`
- **Why hard**: `Async ingest correctness under kernel event coalescing rules.`
- **Main collapse risk**: `“Use a better watcher” trite unless invariants specified.`


#### 12. `BPF stack traces map to vDSO addresses confusing symbolizers`
- **Status**: `ready`
- **Source**: `Option B #15`
- **Topology**: `perf bpf + vDSO + linux-vdso.so.1 naming`
- **Symptom**: `Security investigation attributes syscall hot path to '[vdso]' frames with no resolution while 'objdump' on disk vDSO build-id mismatches runtime mapping.`
- **Discoveries**: `'perf script' reports addresses outside file-backed maps unless '--vdso' dump enabled.; 'readelf -n' on extracted 'linux-gate.so' differs from 'cat /proc/self/maps' vdso inode.; 'bpftool prog tracelog' interleaves user/kernel stacks inconsistently across CPUs.`
- **Evidence**: `trajectory=Verification; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 6: Report exports flame graphs with '[unknown]' buckets interpreted as benign.; Exploit 3: Unit test validates eBPF attach count, not stack quality of sampled events.`
- **Why hard**: `Misleading observability from address-space special regions.`
- **Main collapse risk**: `Expert binutils; provide binary corpus for inspection.`


#### 13. `rr replay diverges on hybrid P/E-core hosts vs recording site`
- **Status**: `ready`
- **Source**: `Option B #17`
- **Topology**: `rr record/replay + heterogeneous CPU + perf_event masking`
- **Symptom**: `Deterministic replay fails assertion in userspace timer wheel though original run was single-threaded and taskset-pinned.`
- **Discoveries**: `'perf stat -e cycles' shows schedule migrations rr did not mask despite taskset.; 'dmesg' contains PMU warnings only on replay host stepping.; CPU logical id maps differ from assumptions baked into trace metadata.`
- **Evidence**: `trajectory=Execution; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 4: Recording flags ignored when replay sysctl perf parity mismatches.; Exploit 6: CI labels replay green if record alone succeeds, not replay equality.`
- **Why hard**: `Time-travel debugging portability hides real nondeterminism class.`
- **Main collapse risk**: `rr + hardware specific; constrain hosts in task.`


#### 14. `dmidecode SMBIOS disagree with EDAC sysfs after DIMM hot swap`
- **Status**: `ready`
- **Source**: `Option B #18`
- **Topology**: `SMBIOS tables + EDAC mc labels + NUMA maps`
- **Symptom**: `Correctable errors attribute to the wrong socket after swap; maintenance scripts offline the wrong rank versus silkscreen labels.`
- **Discoveries**: `'dmidecode -t memory' order disagrees with '/sys/devices/system/edac/mc' mapping until warm reboot.; 'ras-mc-ctl' uses SMBIOS handles stale relative to SPD reread.; 'numactl -H' asymmetry not correlated with EDAC labels operators trust.`
- **Evidence**: `trajectory=Coherence; command_level=edge-cases; cluster=Complex-System-Builds`
- **Exploits**: `Exploit 1: Firmware-named topology vs runtime EDAC graph diverge transiently.; Exploit 5: Post-mortem cites 'dmidecode' snapshot taken before hotplug finished.`
- **Why hard**: `Multi-source hardware identity truth under maintenance.`
- **Main collapse risk**: `SKU dependence; supply synthetic table pack.`


#### 15. `ioctl TIOCGWINSZ poisoned by ssh ControlMaster subsidiary PTY`
- **Status**: `ready`
- **Source**: `Option B #19`
- **Topology**: `pty winsize + ssh mux + curses TUI`
- **Symptom**: `Admin TUI corrupts layout only through shared ControlMaster; direct ssh session clean.`
- **Discoveries**: `Subsidiary session sees zero rows/cols until SIGWINCH while 'stty size' looks sane elsewhere.; 'strace' shows 'ioctl' on fd that is not the TUI’s controlling tty under mux.; Disabling ControlMaster fixes without explaining automation depending on it.`
- **Evidence**: `trajectory=Coherence; command_level=terminal-crash; cluster=Complex-System-Builds`
- **Exploits**: `Exploit 9: Dimensions differ between ssh pty and app’s actual controlling tty.; Exploit 4: Mux attach order allocates tty pair before dimension forcing completes.`
- **Why hard**: `Terminal-state corruption across shared interactive sessions.`
- **Main collapse risk**: `Niche ssh; specify ControlMaster in repro.`


#### 16. `qemu user-mode brk emulation diverges breaking malloc metadata`
- **Status**: `ready`
- **Source**: `Option B #21`
- **Topology**: `qemu-user + glibc brk + malloc hooks`
- **Symptom**: `Cross-arch CI crashes with malloc corruption only under qemu-user; native iron clean.`
- **Discoveries**: `'strace' 'brk' differs from native trace at same source line count.; 'MALLOC_CHECK_=3' errors exclusive under emulation builds.; Static binary masks until dynamic linking reintroduces glibc allocator.`
- **Evidence**: `trajectory=Execution; command_level=edge-cases; cluster=Complex-System-Builds`
- **Exploits**: `Exploit 7: Dropping qemu path bypasses mandated cross-arch CI storyline.; Exploit 5: Harness summarizes exit codes without allocator invariant probes.`
- **Why hard**: `Emulation environment violates implicit allocator contracts.`
- **Main collapse risk**: `qemu maintenance; explicit in constraints.`


#### 17. `malloc arena layout survives execve into setuid helper incorrectly`
- **Status**: `ready`
- **Source**: `Option B #23`
- **Topology**: `malloc arenas + AT_SECURE + setuid boundary`
- **Symptom**: `Privileged helper flakes only when spawned from parent with specific allocation footprint; minimal helper-only repro clean.`
- **Discoveries**: `'MALLOC_ARENA_MAX=1' changes failure class implying cross-exec assumptions broken.; '/proc/pid/smaps' heap flags differ after env stripped at security transition.; Vendor code expects malloc tuning env vars parent set that child loses silently.`
- **Evidence**: `trajectory=Coherence; command_level=edge-cases; cluster=Adversarial-Creative-Reasoning`
- **Exploits**: `Exploit 4: Parent heap geometry choice influences child fastbin paths incorrectly.; Exploit 10: Empty-env edge toggles different libc paths for huge allocations.`
- **Why hard**: `Privilege transition threads allocator state covertly.`
- **Main collapse risk**: `Sensitive; keep in synthetic training image without real privesc.`


#### 18. `PI futex chain gdb non-stop attach with TID reuse`
- **Status**: `ready`
- **Source**: `Option B #24`
- **Topology**: `PI futex + pthread robust + gdb non-stop`
- **Symptom**: `'/proc/locks' disagrees with thread stacks showing futex wait; only when non-stop attach lands mid critical section on busy host.`
- **Discoveries**: `'/proc/pid/stack' truncation differs all-stop vs non-stop.; TID reuse triggers owner-died heuristics earlier in some schedulers.; 'strace' shows 'FUTEX_UNLOCK_PI' without waiter wake when ptrace delays reorder delivery.`
- **Evidence**: `trajectory=Execution; command_level=edge-cases; cluster=Complex-System-Builds`
- **Exploits**: `Exploit 9: 'info threads' misleads mutex ownership after TID recycle.; Exploit 2: Killing stuck thread destroys robust mutex metadata needed postmortem.`
- **Why hard**: `Debugger timing perturbs kernel PI futex narrative.`
- **Main collapse risk**: `Deep pthread; require locks+stack artefacts in spec.`


#### 19. `GCC LTO COMDAT wins change vtable layouts cross library`
- **Status**: `ready`
- **Source**: `Option B #25`
- **Topology**: `LTO WPA + COMDAT + C++ hidden visibility`
- **Symptom**: `Rare vtable crashes after enabling LTO; '-fno-lto' masks; visibility attributes inconsistent across TUs.`
- **Discoveries**: `'readelf --syms' shows duplicate weak vtables resolved differently in ltrans.; LTO dump lists COMDAT candidates with same signatures, different type ids.; 'UBSan vptr' trips only when destroying via base pointer from other DSO.`
- **Evidence**: `trajectory=Coherence; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 7: Disabling LTO on one DSO “fixes” but violates perf contract storyline.; Exploit 5: Release claims LTO parity based on macro tests only.`
- **Why hard**: `C++ ABI under link-time merge competition.`
- **Main collapse risk**: `Heavy C++; anchor 'readelf'+UBSan artifacts.`


#### 20. `seccomp user notif pipe backpressure stalls tracer and child together`
- **Status**: `ready`
- **Source**: `Option B #26`
- **Topology**: `seccomp notif + unix stream sock + tracer IO thread`
- **Symptom**: `A supervised compile sandbox wedges with no CPU; attaches show both tracer and tracee blocked in 'futex'/'poll' pairs with contradictory strace summaries depending on attach order.`
- **Discoveries**: `Tracer responds slowly while notif queue fills; kernel may apply kill policy unrelated to obvious syscall denial.; 'strace -f' on tracer perturbs 'poll' timing enough to hide wedge class.; Increasing 'SCMP_NOTIF_ID_VALID' checks in a tight loop starves writer side.`
- **Evidence**: `trajectory=Execution; command_level=not-waiting; cluster=Complex-System-Builds`
- **Exploits**: `Exploit 8: Supervisor considers child “healthy” when it has not exited, despite deadlock on notification path.; Exploit 2: Killing tracer after wedge loses notif fds preventing clean child teardown evidence.`
- **Why hard**: `Not-waiting + supervision—progress illusion while both ends block.`
- **Main collapse risk**: `Expert sandboxing; include synthetic 'ss -x'/'strace' pairing requirement.`


#### 21. `gdb TUI + async mode corrupts breakpoint command lists silently`
- **Status**: `ready`
- **Source**: `Option B #28`
- **Topology**: `gdb mi/async + command files + conditional breakpoints`
- **Symptom**: `Automated debug sessions skip breakpoints operators swear are set; logs show gdb exited zero while inferior continued past supposed stop point.`
- **Discoveries**: `'~/.gdbinit' sources differ between batch and interactive due to 'TERM' checks.; MI '-break-insert' with conditions races '-exec-continue' when async is on unless '-thread-group' discipline followed.; 'set logging' redirection swallows confirm prompts altering command completion.`
- **Evidence**: `trajectory=Coherence; command_level=edge-cases; cluster=Long-Horizon-Coherence`
- **Exploits**: `Exploit 4: Early gdbinit branch chooses async defaults that later CI scripts assume are off.; Exploit 5: Post-run summary checks gdb log size, not whether stops occurred.`
- **Why hard**: `Interactive tooling state poisons reproducibility of stepwise diagnosis.`
- **Main collapse risk**: `gdb arcana; require MI transcript artifact contract.`


#### 22. `POSIX AIO lio_listio completion ordering vs CPU reorder in userspace ring`
- **Status**: `ready`
- **Source**: `Option B #29`
- **Topology**: `aio + eventfd + userspace completion ring`
- **Symptom**: `Storage microservice reorders writes acknowledged to clients after kernel upgrade; filesystem passes fsck; only appears under load on NVMe with particular queue depths.`
- **Discoveries**: `'io_getevents' returns completions whose error flags were set after userspace observed earlier success slot in ring buffer.; 'strace' shows 'eventfd' wake before last 'lio_listio' syscall returns.; User ring uses 'memory_order_relaxed' stores inconsistent with kernel completion publication semantics.`
- **Evidence**: `trajectory=Execution; command_level=edge-cases; cluster=Complex-System-Builds`
- **Exploits**: `Exploit 4: Early buffer layout choice invalid under new kernel’s completion batching sizes.; Exploit 3: Correctness test uses single-threaded async loop hiding relaxed-ordering bug.`
- **Why hard**: `Memory ordering across kernel/user boundary for aio completion publication.`
- **Main collapse risk**: `Niche API; may rewrite as io_uring analogue for modernity.`


#### 23. `Kernel module crc mismatch on symbol only in ksymtab alias`
- **Status**: `ready`
- **Source**: `Option B #31`
- **Topology**: `CONFIG_MODVERSIONS + ksymtab + weak symbols`
- **Symptom**: `Out-of-tree module loads on one kernel flavor but 'modprobe' refuses on another with inscrutable 'invalid module format' despite matching 'uname -r' marketing strings.`
- **Discoveries**: `'modinfo vermagic' matches but 'modversions' section demands crc for symbol resolved via alias table differing.; 'scripts/mod/modpost'-generated CRC changes when header includes pick up different 'static inline' paths.; 'readelf' shows duplicate symbol entries with same name string indexes but distinct crc records.`
- **Evidence**: `trajectory=Coherence; command_level=edge-cases; cluster=Complex-System-Builds`
- **Exploits**: `Exploit 7: Building without modversions “works” but violates enterprise kernel policy gates.; Exploit 4: Early header include order in one '.c' file shifts crc surface across flavor builds.`
- **Why hard**: `ABI coupling via module versioning—not source-level break.`
- **Main collapse risk**: `Kernel dev focus; good for kernel task authors.`


#### 24. `procfs fd leak via fanotify mark on self /proc recursion in debugger`
- **Status**: `ready`
- **Source**: `Option B #32`
- **Topology**: `fanotify + /proc self + ptrace stop`
- **Symptom**: `Interactive debug sessions slow exponentially while '/proc/sys/fs/inotify/max_user_watches' stays unchanged; issue only when a filesystem watch tool is attached to a process inspecting its own maps.`
- **Discoveries**: `'ls /proc/pid/fd | wc' grows while 'lsof' summary mis-summarizes due to permission edges.; Fanotify recursion through '/proc/<pid>/fd' paths creates watch amplification.; 'strace' on debugger shows repeated 'openat' on procfs during each single-step.`
- **Evidence**: `trajectory=Execution; command_level=edge-cases; cluster=Adversarial-Creative-Reasoning`
- **Exploits**: `Exploit 9: Terminal session growth in fds poisons shell job control or history persistence unexpectedly.; Exploit 2: Clearing watches aggressively mid-session loses breakpoints backed by file monitors.`
- **Why hard**: `Self-referential /proc observation patterns spiraling resource use.`
- **Main collapse risk**: `Weird debugger practice; specify tool combo explicitly in story.`


#### 25. `seccomp filter logs benign return but actually kills on indirect syscall`
- **Status**: `refined`
- **Source**: `Option B repairable seed retained with status refined (review strengthening notes in Option B artifact)`
- **Topology**: `seccomp + libc vDSO + vsyscall bridge`
- **Symptom**: `A hardened service dies with no seccomp denial audit lines; 'strace' stops mid-run without 'SIGSYS' while auditd rules look comprehensive.`
- **Discoveries**: `'dmesg' shows seccomp action kill without log because bpf filter lacks corresponding audit action on that arc.; 'gdb catch syscall' hits a syscall number not present in the textual rule dump due to multi-arch compilation.; Container seccomp profile merged order differs between runc and crun defaults.`
- **Evidence**: `trajectory=Verification; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 6: Checklist verifies 'auditctl' rules file presence, not kill arcs on secondary syscall tables.; Exploit 3: Smoke test uses 'strace' binary statically linked, missing the library syscall path the app uses.`
- **Why hard**: `Verifier-bypass where audits promise coverage but BPF graph does not.`
- **Main collapse risk**: `Seccomp arcana; provide 'scmp_sys_resolver' mapping homework in task.`


#### 26. `musl vs glibc locale collation breaks sorted merge in forked workers`
- **Status**: `refined`
- **Source**: `Option B repairable seed retained with status refined (review strengthening notes in Option B artifact)`
- **Topology**: `libc locale + sort stability + multiprocessing`
- **Symptom**: `Data pipeline deduplication misses rows only in Alpine-based workers while Debian workers match golden outputs byte-for-byte on the same Unicode inputs.`
- **Discoveries**: `'LC_ALL' unset in worker but set in parent after 'fork' without exec hygiene.; 'strace' shows different 'openat' patterns for 'LC_COLLATE' files between images.; Golden test compares normalized NFC while pipeline sorts raw bytes.`
- **Evidence**: `trajectory=Coherence; command_level=edge-cases; cluster=Complex-System-Builds`
- **Exploits**: `Exploit 1: Two ordering truths—host locale files vs worker defaults.; Exploit 10: Empty string keys collate differently only when duplicates exist.`
- **Why hard**: `ABI/culture coupling across container base images.`
- **Main collapse risk**: `Feels like “use UTF-8 correctly” unless evidence is locale file traces.`


#### 27. `Rust panic unwind interacts badly with '-Clinker-plugin-lto' split DWARF`
- **Status**: `refined`
- **Source**: `Option B repairable seed retained with status refined (review strengthening notes in Option B artifact)`
- **Topology**: `LLVM LTO + rustc debuginfo + backtrace symbolization`
- **Symptom**: `Production panics show '??' frames only for the most critical dependency while local debug builds symbolize fine; issue tracks appear “fixed” in changelog.`
- **Discoveries**: `'RUST_BACKTRACE=1' resolves via '.gnu_debuglink' into a '.dwo' missing from the deployed container layer.; 'objcopy --strip-debug' ordering differences between CI stages drop aranges used by addr2line.; 'dladdr' returns success with misleading names when plt stubs are hot.`
- **Evidence**: `trajectory=Coherence; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 7: Fix branch toggles LTO off, improving stacks but missing perf regressions.; Exploit 5: Synthetic panic test uses 'RUST_BACKTRACE=full' locally but prod env sets compact.`
- **Why hard**: `Build/runtime observability coupling across strip/LTO boundaries.`
- **Main collapse risk**: `Rust-version specific; pin toolchain in task constraints.`


#### 28. `prelink undo half-applied leaves PLT entries aiming at deleted libraries`
- **Status**: `refined`
- **Source**: `Option B repairable seed retained with status refined (review strengthening notes in Option B artifact)`
- **Topology**: `prelink + partial rpm transaction + lazy binding`
- **Symptom**: `Only one user on a shared HPC login node SEGVs in a scientific binary others run; 'ldd' is clean until someone runs 'readelf --relocs'.`
- **Discoveries**: `'LD_DEBUG=bindings' shows PLT slot targets a path removed mid-transaction then relinked elsewhere.; 'prelink -ua' logs success while '/etc/prelink.cache' still references the old inode generation.; 'gdb' stops in '_dl_fixup' with R_X86_64_JUMP_SLOT pointing at unmapped page sporadically.`
- **Evidence**: `trajectory=Coherence; command_level=edge-cases; cluster=Long-Horizon-Coherence`
- **Exploits**: `Exploit 2: Re-running prelink to “repair” overwrites relocation snapshots that proved partial application.; Exploit 1: Binary checksum matches package while dynamic relocation state is internally inconsistent.`
- **Why hard**: `Loader relocation truth diverges from package manager file inventory.`
- **Main collapse risk**: `prelink rarity; frame as generic “partial relocation cache” if needed.`


#### 29. `SystemTap uprobes miss after PIE rebasing without stap cache flush`
- **Status**: `refined`
- **Source**: `Option B repairable seed retained with status refined (review strengthening notes in Option B artifact)`
- **Topology**: `SystemTap uprobes + PIE ASLR + stap cache`
- **Symptom**: `Tap shows zero hits for a hot function while 'perf record' clearly samples it.`
- **Discoveries**: `stap resolves symbol via cached offset stale across rebuild with same basename new inode.; 'readelf -r' layout shifts on toolchain minor bump affecting PIE base.; 'stap -p4' plan references inode correct at compile time but not at attach time.`
- **Evidence**: `trajectory=Verification; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 6: Regression checks stap syntax only, not hit counts.; Exploit 3: Validation reads 'nm' addresses without runtime load bias subtraction.`
- **Why hard**: `Probe address authority vs live mapping bias.`
- **Main collapse risk**: `stap rare; generalize to “stale uprobe offset.”`


#### 30. `CET shadow stack fault steers RCA away from earlier stack smear`
- **Status**: `refined`
- **Source**: `Option B repairable seed retained with status refined (review strengthening notes in Option B artifact)`
- **Topology**: `CET SHSTK + ROP-style corruption + stripped binary`
- **Symptom**: `Process dies with shadow-stack fault logs while earlier overflow evidence is discarded; gdb backtrace shallow.`
- **Discoveries**: `'dmesg' faults return to function with benign-looking prologue historically.; GNU property note absent though platform policy enforces SHSTK at runtime.; 'perf' branch stacks differ when libc swaps non-CET-safe longjmp path.`
- **Evidence**: `trajectory=Verification; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 6: SOC attributes solely to “CPU hardening” without stack canary timeline.; Exploit 3: Smoke test checks NX only, not CET interaction with alt stacks.`
- **Why hard**: `Hardware surfaces corruption late, misdirecting debug narrative.`
- **Main collapse risk**: `CET-capable hardware requirement; say so in task.`


#### 31. `Clang -fsanitize=thread vs custom spinlock instrumentation false races`
- **Status**: `refined`
- **Source**: `Option B repairable seed retained with status refined (review strengthening notes in Option B artifact)`
- **Topology**: `TSAN vector clocks + inline asm spin + memory order fences`
- **Symptom**: `TSAN reports data races only when linking against a vendor library built with conflicting '-march' flags; silencing via ignores masks a real atomicity bug in house code.`
- **Discoveries**: `'llvm-symbolizer' line numbers jump between inlined headers duplicated at different '-O' levels.; '__tsan_func_entry' hooks interact badly with '-masm=intel' emitted barriers vendor uses.; 'objdump' lock prefixes differ for the same source line across translation units.`
- **Evidence**: `trajectory=Verification; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 6: Nightly job gates on “0 TSAN reports” without comparing baseline noise fingerprints.; Exploit 7: Disabling TSAN for vendor only hides the in-house race surfaced through inlining overlap.`
- **Why hard**: `Verifier bait where sanitizer noise and real races intersect.`
- **Main collapse risk**: `Sanitizer flakiness; pin flags and provide golden suppression policy spec.`


#### 32. `Valgrind helgrind vs libstdc++ scoped_lock false positive deadlock report`
- **Status**: `refined`
- **Source**: `Option B repairable seed retained with status refined (review strengthening notes in Option B artifact)`
- **Topology**: `C++17 mutex + helgrind happens-before + inline stdlib`
- **Symptom**: `CI fails helgrind on upgraded toolchain though no code changes; developers dismiss as tool bug while production deadlocks rise slowly under contention.`
- **Discoveries**: `'libstdc++.so' debug symbols missing for new 'scoped_lock' template instantiations helgrind needs.; 'hg --track-lockorders' spew differs when linking LTO vs non-LTO.; 'gdb' cannot resolve inline frame names helgrind prints, complicating manual reasoning.`
- **Evidence**: `trajectory=Verification; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 5: Report emails “helgrind noisy” based on count thresholds, not structural lock graph deltas.; Exploit 6: Synthetic test uses '-D_GLIBCXX_DEBUG' altering lock internals masking prod behavior.`
- **Why hard**: `Robust verification trap: false positive label hides emerging real deadlock class.`
- **Main collapse risk**: `Toolchain coupling; require lock-order graph export artifact.`


#### 33. `Intel CET SHSTK shadow stack ibt fault on PLT tramp after IFUNC resolvers change`
- **Status**: `replacement`
- **Source**: `Generated to fill bank; 'debugging' subsystem diversity`
- **Topology**: `GNU ifunc + ibt + PLT`
- **Symptom**: `Single binary SIGILL on new stepping only when hwcaps advertise newer SIMD while older nodes run fine; gdb disassembly at fault looks like a valid ret.`
- **Discoveries**: `Ifunc resolver picked memcpy variant without ibt landing pads while linker assumed ibt on all external labels.; 'readelf -n' CET property present but '.plt' entries lack endbr at the slot actually called through vdso-less path.; 'objdump -d' vs runtime 'x/10i $pc' disagree because binary on disk replaced after process started with same inode via overlay.`
- **Evidence**: `trajectory=Verification; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 6: CI checks SIGILL absent on sample host tier only, not the new stepping.; Exploit 4: Early hwcaps snapshot at dynamic loader init sticks through ifunc reresolution attempts.`
- **Why hard**: `Control-flow enforcement meets resolver indirection and CPU capability gating.`
- **Main collapse risk**: `Too CPU-specific without supplying disasm + auxv pack.`


#### 34. `glibc malloc arena decay leaves cross-thread tcache poisoning thatasan misses`
- **Status**: `replacement`
- **Source**: `Generated to fill bank; 'debugging' subsystem diversity`
- **Topology**: `glibc malloc + tcache + TSan`
- **Symptom**: `Flaky segfault under threadpool shutdown in C++ service; asan never trips; core shows crash in free().`
- **Discoveries**: `tsan intercepts miss tcache fast path realloc pattern the service uses.; 'malloc_info' shows per-arena mismatch only after threads exit in non-join order.; 'gdb' cannot walk arenas without symbolized mp_. glibc debuginfo version skew.`
- **Evidence**: `trajectory=Coherence; command_level=edge-cases; cluster=Adversarial-Creative-Reasoning`
- **Exploits**: `Exploit 7: Enabling asan catches unrelated races obscuring allocator shutdown bug.; Exploit 1: Two allocator truths—instrumented vs prod libc—diverge in tcache.`
- **Why hard**: `Allocator lifecycle + tooling blind spots on fast paths.`
- **Main collapse risk**: `Expert-only; require malloc_info + core pair.`


#### 35. `futex FUTEX_LOCK_PI owner death inconsistent when PI boosted across cgroups freeze`
- **Status**: `replacement`
- **Source**: `Generated to fill bank; 'debugging' subsystem diversity`
- **Topology**: `PI futex + cgroup freezer + priority inheritance`
- **Symptom**: `Rare hang in media pipeline when cgroup freeze used for checkpointing; one thread forever in D state with inconsistent '/proc/pid/wchan' vs lock owner in userspace.`
- **Discoveries**: `Kernel marks owner died while userspace mutex still thinks held after thaw ordering issues.; '/proc/lock' parsing scripts mis-handle nested PI chains when threads migrate cpusets mid-wait.; strace of FUTEX_WAIT returns EAGAIN while futex_waitv path diverges on same glibc version across backports.`
- **Evidence**: `trajectory=Execution; command_level=edge-cases; cluster=Complex-System-Builds`
- **Exploits**: `Exploit 4: Early freeze captures lock graph assumptions thaw invalidates without repaint.; Exploit 8: Health probe thaw order returns before PI chain drains.`
- **Why hard**: `Kernel/userspace coupling on priority inheritance under resource freeze.`
- **Main collapse risk**: `Kernel-version rabbit hole; capture lockdep+ftrace hints in task pack.`


#### 36. `libbfd demangling hides duplicate symbols after partial gold link`
- **Status**: `replacement`
- **Source**: `Generated to fill bank; 'debugging' subsystem diversity`
- **Topology**: `gold linker + gdb demangler + comdat groups`
- **Symptom**: `gdb breakpoints never hit despite function reached in backtrace names; 'break' resolves to a comdat clone not on executed path.`
- **Discoveries**: `Gold assigns section symbols differently than ld.bfd gdb’s symtab expects.; 'info address' resolves demangled C++ name to first COMDAT duplicate not chosen at runtime.; Separate debug file carries aranges that alias two .text regions with same linkage name.`
- **Evidence**: `trajectory=Verification; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 3: Smoke test sets breakpoint on source line only, missing comdat ambiguity.; Exploit 6: CI validates binary exists, not gdb breakpoint resolution on all linkers.`
- **Why hard**: `Debug symbol identity vs executed instantiation under COMDAT.`
- **Main collapse risk**: `Linker combo edge; pin gold vs bfd in repro.`


#### 37. `Kernel stack end poison interacts with '-O3' sibling call tail merge`
- **Status**: `replacement`
- **Source**: `Generated to fill bank; 'debugging' subsystem diversity`
- **Topology**: `gcc tail merge + stack protector + canary layout`
- **Symptom**: `Canary overflow fires on '-O3' build only at sibling function boundary where tail-call merged; '-O2' clean.`
- **Discoveries**: `Tail merge reuses stack slots across functions with different local array lifetimes.; 'asan' sees poison; bare metal only trips FORTIFY on unrelated memcpy.; CFG dump shows merged blocks; dwarf scopes disagree on variable locations at fault line.`
- **Evidence**: `trajectory=Coherence; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 4: Optimization level flipped globally late in release trains invalidating prior stack usage proofs.; Exploit 5: Nightly benchmark green uses '-O2' while production uses '-O3'.`
- **Why hard**: `Compiler optimization changes stack lifetime without obvious UB at source.`
- **Main collapse risk**: `Compiler bug hunt vibe; need RTL/CFG artifact contract.`


### Category: `scientific-computing`

#### 1. `MPI+OpenMP nesting sets wrong OMP_NUM_THREADS after hwloc cache miss`
- **Status**: `ready`
- **Source**: `Option B #1`
- **Topology**: `MPI ranks + OpenMP + hwloc topology XML drift`
- **Symptom**: `Strong scaling benchmarks invert—more nodes run slower—after a BIOS microcode update with no code changes; per-rank thread counts look “balanced” in logs.`
- **Discoveries**: `'hwloc-ls' shows core numbering changes while launcher cache files still advertise old PU lists.; 'OMP_DISPLAY_ENV' differs between head node compile and compute runtime when modules load order changes.; 'numactl --hardware' disagrees with Slurm 'gres' assignment on a subset of nodes.`
- **Evidence**: `trajectory=Coherence; command_level=edge-cases; cluster=Complex-System-Builds`
- **Exploits**: `Exploit 4: Early launcher-derived thread map commits before BIOS update reshapes PU topology.; Exploit 5: Post-run report averages time/rank without validating thread concurrency invariants.`
- **Why hard**: `Long-horizon hardware threading state threaded through runtime env without single segfault.`
- **Main collapse risk**: `HPC site specific; constrain to synthetic topology XML + logs.`


#### 2. `Mixed-precision GMRES residual norm computed in wrong workspace precision`
- **Status**: `ready`
- **Source**: `Option B #2`
- **Topology**: `iterative solver + fp16 accumulation + BLAS workspace`
- **Symptom**: `Solver reports convergence while true residual blows up when validated in quad; behavior flips when linking MKL vs OpenBLAS.`
- **Discoveries**: `Relative residual uses 'snrm2' on a downcast buffer while matvec uses fp32 intermediates.; 'LD_PRELOAD' order changes which 'dgemm' variant zeros workspaces differently.; Golden test compares final vector using atol while production uses rtol on the wrong norm definition.`
- **Evidence**: `trajectory=Verification; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 3: Quick regression compares iteration counts only, not independent residual reconstruction.; Exploit 6: CI uses 'numpy.linalg.norm' on exported vector without matching solver internal scaling.`
- **Why hard**: `Premature completion bait on cheap norm vs true residual authority.`
- **Main collapse risk**: `Numeric policy naming collapse; RC6 on vendor BLAS function naming if needed.`


#### 3. `FFT plan wisdom file from different geometry poisons stride-3 transforms`
- **Status**: `ready`
- **Source**: `Option B #4`
- **Topology**: `FFTW wisdom + non-cubic grid + SIMD alignment`
- **Symptom**: `After copying wisdom cache between clusters, stochastic spectral code develops 1e-3 drift only on odd-axis lengths.`
- **Discoveries**: `'fftw-wisdom' import suppresses planner measurements that would pick different split factors for the new L3 size.; 'fftw_export_wisdom' strings embed arch tags silently ignored on import with warning level too low to reach logs.; 'perf stat' shows icache pressure spikes aligning with suboptimal plan.`
- **Evidence**: `trajectory=Coherence; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 1: Wisdom file and runtime geometry both look “valid” yet disagree on optimal factorization class.; Exploit 4: Early import of wisdom in driver main predates reading actual domain sizes from input deck.`
- **Why hard**: `Numerical drift from wrong fast algorithm choice, not NaNs.`
- **Main collapse risk**: `Floating tolerance debates; require independent reference DFT on small slice.`


#### 4. `Zarr v3 codec chain applies filters in different order across readers`
- **Status**: `ready`
- **Source**: `Option B #5`
- **Topology**: `chunked array + shuffle + compression + two clients`
- **Symptom**: `Two analysis pipelines read “identical” cloud arrays; summary statistics disagree in the 4th decimal on huge tensors without decompression errors.`
- **Discoveries**: `Metadata says shuffle then compress while one client reorders per spec ambiguity.; Empty chunk encoding differs; one reader treats missing as zero, other as NaN mask.; 'blosc' threads race on buffer reuse exposing nondeterministic rounding in a doubtful optimization.`
- **Evidence**: `trajectory=Verification; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 1: Two decode authorities—spec interpretation vs on-disk metadata strings—disagree.; Exploit 10: All-NaN edge chunk short-circuits validation in one client.`
- **Why hard**: `Wrong-format/wrong-order decode under plausible metadata.`
- **Main collapse risk**: `Format-war territory; RC6 if spec version chatter dominates.`


#### 5. `Checkpoint resume loads optimizer state but not LR warmup schedule cursor`
- **Status**: `ready`
- **Source**: `Option B #6`
- **Topology**: `distributed training + cosine schedule + AMP scaler`
- **Symptom**: `Resume-from-checkpoint reproduces loss curve shape until step 500 then diverges; team blames “non-determinism” while GPUs are deterministic mode on.`
- **Discoveries**: `Checkpoint stores RNG for dataloaders but not internal step counter used by custom warmup wrapper.; 'GradScaler' state serializes while fused Adam kernel version changed between builds.; Profiler shows LR discontinuity exactly at resume boundary visible only on rank 0 logs.`
- **Evidence**: `trajectory=Coherence; command_level=edge-cases; cluster=Long-Horizon-Coherence`
- **Exploits**: `Exploit 4: Early resume hook order reapplies defaults that silently overwrite warmup cursor from checkpoint file.; Exploit 5: Monitoring overlays loss only, not LR schedule parity vs pre-interrupt reference run.`
- **Why hard**: `Long-horizon training state threading across checkpoint bundles.`
- **Main collapse risk**: `Framework churn; pin torch version or make framework-agnostic “scheduler cursor” fable.`


#### 6. `NetCDF unlimited dimension append races HDF5 chunk cache visibility`
- **Status**: `ready`
- **Source**: `Option B #8`
- **Topology**: `NetCDF-4 + HDF5 chunk cache + concurrent writers`
- **Symptom**: `Readers see occasional stale last timestep despite successful writer flush logs in a forecast pipeline; corruption checks pass.`
- **Discoveries**: `Writer calls 'nc_sync' while reader mmap caches chunk via independent handle flags.; 'h5stat' shows allocated space growth but last slab not visible until file close on writer side in some library builds.; NFS client attribute cache interacts badly with NetCDF file layout expectations.`
- **Evidence**: `trajectory=Coherence; command_level=not-waiting; cluster=Long-Horizon-Coherence`
- **Exploits**: `Exploit 8: Orchestration marks forecast “published” when upload completes, not when readers observe new extent metadata.; Exploit 1: File size truth via 'stat' disagrees with dataset dimension length metadata momentarily.`
- **Why hard**: `Multi-source-of-truth between filesystem metadata and dataset internal dims.`
- **Main collapse risk**: `IO library + NFS interaction cliché unless evidence is mandated.`


#### 7. `SymPy codegen float cast inserts at wrong AST depth for Jacobian`
- **Status**: `ready`
- **Source**: `Option B #9`
- **Topology**: `symbolic codegen + finite differences + mixed precision`
- **Symptom**: `Auto-generated sensitivity matrices match finite differences in unit tests yet fail implicit timestepper stability only at large Δt; bisect lands on sympy upgrade.`
- **Discoveries**: `'ccode' printer inserts 'double' casts that change derivative grouping for nested divisions.; 'lambdify' module list order picks 'numpy' functions with different rounding at branch cuts.; Reference Jacobian computed in extended precision offline disagrees with generated C only beyond 1e-8.`
- **Evidence**: `trajectory=Verification; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 3: CI compares Jacobians against finite diff with step too large masking subtle mis-group.; Exploit 5: Stability test reports “max eigenvalue < 1” using numpy eig on noisy matrix without verification norm.`
- **Why hard**: `Plausible-but-wrong linearization from codegen policy drift.`
- **Main collapse risk**: `Niche CAS; position as generic “codegen cast depth” story.`


#### 8. `CuBLASLt heuristic selection differs by driver but JSON log claims same algo id`
- **Status**: `ready`
- **Source**: `Option B #11`
- **Topology**: `matmul autotune + cublasLt + checkpointed kernels`
- **Symptom**: `Deterministic CUDA seeds yield bitwise different reductions on A100 pools after driver rollout; CI golden tests flaky only on nightlies.`
- **Discoveries**: `Autotune cache keyed by problem size misses streaming multiprocessor count skew on MIG slices.; 'CUDA_MODULE_LOADING=EAGER' changes heuristic ordering without changing logged “selected algo.”; 'ncu' shows different shared memory carveouts though high-level API returns same descriptor id integer.`
- **Evidence**: `trajectory=Verification; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 1: Logged algo id truth vs executed microkernel truth diverges across drivers.; Exploit 6: Regression harness checksums output only on subset of tensor positions missing tail aggregation sensitivity.`
- **Why hard**: `GPU reduction ordering non-associativity under heuristic churn.`
- **Main collapse risk**: `Hardware dependence; use small reproducible matmul with required log pack.`


#### 9. `SciPy ODE solver tolerances interact with Jacobian sparsity pattern updates`
- **Status**: `ready`
- **Source**: `Option B #12`
- **Topology**: `BDF + sparse Jacobian + event detection`
- **Symptom**: `Integrator misses an event crossing exactly when Jacobian sparsity pattern grows mid-simulation; tightening rtol alone does not fix.`
- **Discoveries**: `'solve_ivp' event function sign flips between accepted steps straddling sparsity rebuild window.; Finite difference Jacobian color groups stale after new couplings appear.; 'DOP853' reference run disagrees only after event, not before, implicating localized step reject logic.`
- **Evidence**: `trajectory=Execution; command_level=edge-cases; cluster=Long-Horizon-Coherence`
- **Exploits**: `Exploit 4: Early sparsity pattern commitment predates dynamic coupling discovery from chemical kinetics branch.; Exploit 5: Verification chart tracks step counts, not event time error vs reference.`
- **Why hard**: `Timestepper event logic coupled to Jacobian structure lifecycle.`
- **Main collapse risk**: `SciPy version coupling; abstract to generic BDF+events.`


#### 10. `CVXPY DCP discipline passes but numerical solver hits infeasible certificate`
- **Status**: `ready`
- **Source**: `Option B #14`
- **Topology**: `disciplined convex + solver scaling + presolve`
- **Symptom**: `Model passes DCP checks and solved yesterday; today fails infeasible with identical parameters file; team suspects “solver bug.”`
- **Discoveries**: `Automatic scaling divides by near-zero coefficient introduced by symbolic rewrite ordering change.; 'Parameter' value cast to float64 truncates rational introduced in new sympy simplify path.; 'solver_stats' reports presolve removed constraints silently differing between ECOS versions.`
- **Evidence**: `trajectory=Coherence; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 1: Mathematical convex certificate vs numerical realize feasibility diverge after rewrite.; Exploit 5: Notebook “still feasible” checks 'problem.status' on relaxedProblem not original.`
- **Why hard**: `Split between symbolic discipline and numeric realization policy.`
- **Main collapse risk**: `Optimization modeling niche.`


#### 11. `CGAL mesh criteria satisfied in float but violated in exact kernel post-filter`
- **Status**: `ready`
- **Source**: `Option B #15`
- **Topology**: `exact predicates + mesh refinement + filter failures`
- **Symptom**: `Surface mesh passes quality report yet volumetric tetgen step aborts; reports disagree on shortest edge length by epsilon near coplanar facets.`
- **Discoveries**: `Predicate filter statistics show rising exact computation calls only after incremental insert batch 17.; 'double' coordinates read from STEP file differ at bit level from CAD expected values used in oracle tests.; CGAL trace levels show orientation tests flipping sign under perturbation smaller than reporting epsilon.`
- **Evidence**: `trajectory=Verification; command_level=edge-cases; cluster=Adversarial-Creative-Reasoning`
- **Exploits**: `Exploit 3: Quality report samples circumradius on subset of simplices missing sliver class.; Exploit 6: Pass criterion uses filtered predicate while failure path uses exact kernel without bridging logs.`
- **Why hard**: `Geometric robustness: two correctness notions (float report vs exact kernel).`
- **Main collapse risk**: `CGAL-heavy; RC6 on product geometry kernel jargon.`


#### 12. `AMG coarse operator near-singular after boundary DOF reorder`
- **Status**: `ready`
- **Source**: `Option B #17`
- **Topology**: `AMG coarse solve + dirichlet masks + permutation`
- **Symptom**: `Linear solve “converges” in fewer iterations yet solution drift versus fine-grid projection grows when boundary DOFs are renumbered for cache friendliness.`
- **Discoveries**: `Coarse matrix becomes near-singular in nullspace consistent with rigid motions after mask permutation.; Python notebooks show stable residual norms while a direct coarse check in MATLAB disagrees.; 'numpy.linalg.cond' on extracted coarse blocks spikes only on ranks owning fractured subdomains.`
- **Evidence**: `trajectory=Verification; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 3: Iteration count-only regression misses coarse-grid fidelity.; Exploit 5: Dashboard tracks wall time reduction, not physics invariants of coarse correction.`
- **Why hard**: `Misleading iteration metrics when coarse solve quality silently degrades.`
- **Main collapse risk**: `PDE stack specific; keep coarse matrix excerpts as artifacts.`


#### 13. `Torch Dynamo export captures graph before gradient scaling hook runs`
- **Status**: `ready`
- **Source**: `Option B #18`
- **Topology**: `torch.compile + GradScaler + custom backward`
- **Symptom**: `Exported ONNX matches eager forward but training diverges only when compile enabled; loss scale logs look normal.`
- **Discoveries**: `Dynamo graph partition places scaler updates outside the region fused with backward.; 'aot_autograd' metadata shows different decomps for AMP casts when dtype promotion order shifts.; 'torch._dynamo.explain' output omits side-effectful hooks registered after compile.`
- **Evidence**: `trajectory=Coherence; command_level=edge-cases; cluster=Long-Horizon-Coherence`
- **Exploits**: `Exploit 4: Compile cache keyed on source hash ignores runtime hook registration order changed by import side effects.; Exploit 8: Export script returns after ONNX bytes written, not after scaler state quiesced.`
- **Why hard**: `Long-horizon training correctness under graph capture vs eager side effects.`
- **Main collapse risk**: `Torch churn; pin versions or abstract to “graph capture vs AMP hooks.”`


#### 14. `JAX jit treats mutable shape policy as static after partial update`
- **Status**: `ready`
- **Source**: `Option B #20`
- **Topology**: `JAX jit + static arguments + Python container shapes`
- **Symptom**: `Gradients silently zero for a submodule only when batch size crosses a threshold; 'jax.check_grads' missed because it used a smaller batch.`
- **Discoveries**: `Static argnums still treats a shape policy dataclass as static while internal list fields mutated.; 'jax.make_jaxpr' shows different batch axes than runtime 'pmap' shard rules expect.; 'inspect.signature' of wrapped function hides which args became static after partial.`
- **Evidence**: `trajectory=Verification; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 4: First successful jit trace bakes static metadata that later policy object edits should invalidate but does not.; Exploit 3: Unit test uses 'vmap' width 1 masking batched branch divergence.`
- **Why hard**: `Premature trace reuse treats mutable policy as static.`
- **Main collapse risk**: `JAX API drift; pin jaxlib or keep symptom-level.`


#### 15. `PETSc flexible GMRES + shell preconditioner context goes stale across timesteps`
- **Status**: `ready`
- **Source**: `Option B #21`
- **Topology**: `flexible Krylov + PCSHELL + language interop handles`
- **Symptom**: `Nonlinear outer loop stalls only when reusing a shell preconditioner across timesteps; allocating fresh each step masks at prohibitive memory cost.`
- **Discoveries**: `Fortran/C interop pointer cache holds stale matrix handles not nulled on PDE operator resize.; Printed iteration counts plateau while an independent 'MatMult' residual probe grows.; True residual monitor flag documented but off in production config templates.`
- **Evidence**: `trajectory=Coherence; command_level=edge-cases; cluster=Long-Horizon-Coherence`
- **Exploits**: `Exploit 4: First timestep commits shell context layout invalidated by later geometry update.; Exploit 5: Fleet dashboard tracks outer Newton iterations only, not inner flexible Krylov drift.`
- **Why hard**: `Hidden coupling between handle lifetime and iterative shell contracts.`
- **Main collapse risk**: `Library+interop niche; retell with abstract “shell PC + stale ctx.”`


#### 16. `Numba prange reduction order shifts on heterogeneous NUMA hosts`
- **Status**: `ready`
- **Source**: `Option B #22`
- **Topology**: `numba parallel + thread partition + first-touch NUMA`
- **Symptom**: `Monte Carlo estimator mean shifts when the same job lands on different node generations though RNG seed fixed; CI pool is uniform.`
- **Discoveries**: `Chunk scheduler assigns work before observing live thread count on node.; Page first-touch migrates pages changing reduction tree parallelism across domains.; Thread env for JIT workers set in slurm prolog differs from job script body on some sites.`
- **Evidence**: `trajectory=Verification; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 1: Fixed seed does not imply identical FP reduction order across schedulers.; Exploit 6: Validator hashes final scalar only, not stratum sums risk policy demands.`
- **Why hard**: `FP non-associativity meets runtime scheduling differences across metal.`
- **Main collapse risk**: `Heterogeneous HPC; declare homogeneity or provide schedule traces.`


#### 17. `Discrete adjoint checkpoint stride invalid once stiff turbulence model enabled`
- **Status**: `ready`
- **Source**: `Option B #24`
- **Topology**: `adjoint PDE + turbulence closure + checkpointing`
- **Symptom**: `Constrained optimization violates physics limits though gradient passes small finite-diff audit; appears only with expensive closure on.`
- **Discoveries**: `Checkpoints omit fast turbulence variables assumed “slow” in laminar-derived documentation.; Validation suite uses cheaper closure than production configuration referenced.; Line search accepts steps based on incomplete Lagrangian omitting active production penalties.`
- **Evidence**: `trajectory=Execution; command_level=edge-cases; cluster=Long-Horizon-Coherence`
- **Exploits**: `Exploit 4: Stride chosen pre-stiffness invalid after closure activates.; Exploit 5: Suite compares drag only, not active inequality functionals.`
- **Why hard**: `Adjoint correctness requires recorded state to cover stiff modes actually evolved.`
- **Main collapse risk**: `CFD stack; keep abstract formulation in final instruction.`


#### 18. `Serving batch layout rewrite drifts from SavedModel signature layout`
- **Status**: `ready`
- **Source**: `Option B #26`
- **Topology**: `inference server + batching + layout fusion`
- **Symptom**: `Batched GPU requests yield logits outside tolerance versus CPU singles; singles match golden.`
- **Discoveries**: `Graph optimizer picks different layout passes past batch-size thresholds.; MetaGraph tag tensors share names but not internal layout metadata consumers assume.; CLI inspect shows public NHWC while GPU kernels use internal transpose temps.`
- **Evidence**: `trajectory=Coherence; command_level=edge-cases; cluster=Complex-System-Builds`
- **Exploits**: `Exploit 1: Signature contract and runtime fused-graph contract diverge under batching.; Exploit 6: Canary exercises singles only, never batched GPU path.`
- **Why hard**: `Variant ladder between single and batched optimized subgraphs.`
- **Main collapse risk**: `ML serving coupling; supply minimal model tarball + logs.`


#### 19. `HMC divergent transitions fall under thinning window in posterior ingest`
- **Status**: `ready`
- **Source**: `Option B #27`
- **Topology**: `Stan-style HMC + warmup windows + thinned CSV ingest`
- **Symptom**: `Credible intervals tighten suspiciously post-toolchain bump though split-'Rhat' ok; bursts of divergences align with window edges lost in ingest.`
- **Discoveries**: `Divergence booleans land on rows dropped by downstream default thin.; Step-size adaptation windows restart with mass matrix misaligned to new data subset.; Dashboard drops warmup rows but not linked divergence flags when merging.`
- **Evidence**: `trajectory=Verification; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 5: Exec summary cites 'Rhat' without divergent rate per window.; Exploit 3: Golden test compares posterior mean on thinned draws hiding explosions.`
- **Why hard**: `MCMC verification must time-align diagnostics with kept samples.`
- **Main collapse risk**: `Stats stack niche; define CSV column contract.`


#### 20. `Cached patch IDs in solver post hooks after dynamic mesh topo change`
- **Status**: `ready`
- **Source**: `Option B #29`
- **Topology**: `dynamic mesh + surface writers + patch map cache`
- **Symptom**: `Boundary forces wrong after refinement though volume slices look fine in viz.`
- **Discoveries**: `Hook registered patch indices at init; topo change reorders patches without refresh.; Bulk mesh checks pass while surface restricted outputs address wrong subset.; Control dictionary load order applies hooks before topo refresh.`
- **Evidence**: `trajectory=Coherence; command_level=edge-cases; cluster=Complex-System-Builds`
- **Exploits**: `Exploit 4: Early hook binds names resolved before dynamic event reorders them.; Exploit 6: QA averages volume metrics missing boundary objectives.`
- **Why hard**: `Wrong-location artifact: boundary truth diverges from volume truth.`
- **Main collapse risk**: `CFD framework naming; abstract in final task.`


#### 21. `ODE third-party callback composition order flips under load order`
- **Status**: `ready`
- **Source**: `Option B #31`
- **Topology**: `ODE + event callbacks + library load order`
- **Symptom**: `Hybrid system misses jumps when two packages register continuous callbacks; 'tstops' sequence appears complete in solution struct.`
- **Discoveries**: `Load order changes callback prepend/append behavior when precompile caches stale across minor language releases.; Passing 'callback=' kwarg replaces full set unless explicitly composed.; 'reinit!' path retains defaults that doc example assumes cleared.`
- **Evidence**: `trajectory=Execution; command_level=edge-cases; cluster=Complex-System-Builds`
- **Exploits**: `Exploit 7: Removing one package’s callbacks fixes ordering but deletes unrelated guard another supplied.; Exploit 4: First solve seeds default callbacks surviving 'reinit!' unexpectedly.`
- **Why hard**: `Compositional coupling of solver extension points.`
- **Main collapse risk**: `Language ecosystem ordering; pin lockfiles in harness.`


#### 22. `PETSc SNES line search accepts step violating physical bounds`
- **Status**: `refined`
- **Source**: `Option B repairable seed retained with status refined (review strengthening notes in Option B artifact)`
- **Topology**: `nonlinear solve + variable bounds + custom line search`
- **Symptom**: `PDE solves “converge” yet downstream coupled flux calculation hits NaNs; occurs only when Jacobian lagging toggled on.`
- **Discoveries**: `SNES reports 'CONVERGED_FNORM_RELATIVE' while 'VecMax' shows state vector exceeded bounds by epsilon dependent on lag.; Custom monitoring hook prints fnorm from work vector not committed solution vector.; '-snes_converged_reason' strings differ between PETSc minor versions for same phenomenon.`
- **Evidence**: `trajectory=Execution; command_level=edge-cases; cluster=Long-Horizon-Coherence`
- **Exploits**: `Exploit 5: Dashboard tracks nonlinear iteration count, not bound slack invariants.; Exploit 7: Disabling Jacobian lag restores stability but blows runtime budget forbidden by story.`
- **Why hard**: `Coupled physics authority vs optimizer bookkeeping vectors.`
- **Main collapse risk**: `Library-specific; pin PETSc version or generalize to NLsolve story.`


#### 23. `FEniCS facet integrals pick wrong measure after mesh refinement + ghost layer mismatch`
- **Status**: `refined`
- **Source**: `Option B repairable seed retained with status refined (review strengthening notes in Option B artifact)`
- **Topology**: `DG FEM + ghost cells + facet numbering`
- **Symptom**: `Energy norm looks stable in serial but leaks mass in parallel after adaptive refinement; 'dolfin' version unchanged.`
- **Discoveries**: `'mesh.num_entities' differs across ranks for facets on partition boundary post-refinement.; A user-defined facet measure uses cached markers from pre-refinement topology.; 'PETSc' partitioner seed changed when SLURM job id parity flips.`
- **Evidence**: `trajectory=Execution; command_level=edge-cases; cluster=Complex-System-Builds`
- **Exploits**: `Exploit 8: Adaptivity “finishes” macro log line before ghost layer exchange completes.; Exploit 3: Serial regression test on coarse mesh misses parallel-only facet orientation bug.`
- **Why hard**: `Geometry/policy change + parallel ghost layer coherence.`
- **Main collapse risk**: `FEM stack expert; constrain mesh sizes or generalize story.`


#### 24. `AMG strength threshold drops near-null couplings on rotated grid`
- **Status**: `refined`
- **Source**: `Option B repairable seed retained with status refined (review strengthening notes in Option B artifact)`
- **Topology**: `AMG coarsening + anisotropy + strength threshold`
- **Symptom**: `Solver iterations double when rotating structured grid 45° even though PDE unchanged; operator spectrum estimates look similar in cheap notebooks.`
- **Discoveries**: `Strength threshold calibrated on axis-aligned case zeroes weak couplings crucial after rotation.; 'hypre' logging levels hide aggressive coarsening decisions unless compiled debug.; Null-space vectors supplied for elasticity mismatch rotated boundary orientation assumptions.`
- **Evidence**: `trajectory=Execution; command_level=edge-cases; cluster=Complex-System-Builds`
- **Exploits**: `Exploit 4: Early parameter file chooses strength params before geometry rotation parameter ingested.; Exploit 7: Fallback to direct coarse solve “fixes” rotation case but violates memory budget storyline.`
- **Why hard**: `Numerical policy authority vs operator structure under coordinate transforms.`
- **Main collapse risk**: `Library-specific; generalize to “AMG strength params vs anisotropy.”`


#### 25. `Pandas groupby + nullable dtypes changes sum identity vs R baseline`
- **Status**: `refined`
- **Source**: `Option B repairable seed retained with status refined (review strengthening notes in Option B artifact)`
- **Topology**: `nullable integers + groupby reductions + NA propagation`
- **Symptom**: `Migration script validates row counts but finance variance vs R jumps at month boundaries when NA column introduced upstream silently.`
- **Discoveries**: `'sum' min_count semantics differ when all-NaN groups appear after join.; 'dtype' promotion adds 'Int64' path changing accumulator width vs numpy defaults.; Quick viz uses 'fillna(0)' masking absence of NA policy tests.`
- **Evidence**: `trajectory=Verification; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 3: QA compares means only on filtered subsets missing empty groups.; Exploit 6: Executive dashboard hashes intermediate Parquet without schema nullable flags.`
- **Why hard**: `Statistical-policy split across toolchain versions.`
- **Main collapse risk**: `Data science “gotcha”; elevate with contract tests story.`


#### 26. `Kokkos MDRangePolicy tile size vs wider SIMD without retune`
- **Status**: `refined`
- **Source**: `Option B repairable seed retained with status refined (review strengthening notes in Option B artifact)`
- **Topology**: `Kokkos parallel dispatch + tile SIMD + occupancy`
- **Symptom**: `Same kernels port from Zen3 to Zen4; validation tolerances fail only on dot products fused in one launch; 'nvcc' path unaffected.`
- **Discoveries**: `Tile sizes tuned for old L2 footprint cause partial vector lanes to accumulate junk on wider SIMD.; 'KOKKOS_OPT_LEVEL' environment differs between batch and interactive partitions.; 'perf stat' shows increased 'simd_int' retired mismatching expected reduction tree depth.`
- **Evidence**: `trajectory=Execution; command_level=edge-cases; cluster=Complex-System-Builds`
- **Exploits**: `Exploit 4: Early policy header sets tile sizes before reading hardware json topology in driver.; Exploit 7: Forcing serial reduction “passes” tests but invalidates performance contract storyline.`
- **Why hard**: `Operator fusion reduction ordering under SIMD width policy shift.`
- **Main collapse risk**: `Kokkos-specific; generalize to “SIMD tile policy drift.”`


#### 27. `In situ ghost cell tags collide with renamed adaptor fields`
- **Status**: `refined`
- **Source**: `Option B repairable seed retained with status refined (review strengthening notes in Option B artifact)`
- **Topology**: `in situ viz + ghost cell arrays + conduit naming`
- **Symptom**: `ParaView shows seams on partitioned grids only after a Catalyst adaptor version bump; solvers claim ghost exchange still bitwise identical.`
- **Discoveries**: `VTK array name for ghost flags now collides with a user field named 'vtkGhostType' substring match in regex exporter.; Byte order of int tags differs across adaptor builds though simulation endian fixed.; 'pvbatch' screenshot tests miss edge pixels reviewers dismiss as compression.`
- **Evidence**: `trajectory=Execution; command_level=edge-cases; cluster=Complex-System-Builds`
- **Exploits**: `Exploit 1: Solver ghost-bit truth and visualization interpretation of same bits diverge.; Exploit 6: Nightly image diff threshold masks systematic one-pixel bias along partitions.`
- **Why hard**: `Wrong-place artifact: correct simulation tensors visualized with mis-bound metadata.`
- **Main collapse risk**: `Viz stack coupling; supply small VTU + expected color map.`


#### 28. `Arrow Flight nested nullability drifts on “compatible” schema upgrade`
- **Status**: `refined`
- **Source**: `Option B repairable seed retained with status refined (review strengthening notes in Option B artifact)`
- **Topology**: `Arrow flight + nested structs + schema fingerprint`
- **Symptom**: `Training job sees new null rows though server logs claim backward-compatible schema rollout.`
- **Discoveries**: `Nested child nullability flips without bumping top-level semantic version string clients parse.; Client cast defaults promote children differently across pyarrow minor bumps.; Golden tests compare flattened parquet missing nested field stability keys.`
- **Evidence**: `trajectory=Coherence; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 1: “Compatible” server judgment and client null semantics diverge on nested paths.; Exploit 3: Row-count parity misses nested null explosion.`
- **Why hard**: `Schema-compatible bytes decode to different logical null sets.`
- **Main collapse risk**: `Arrow churn; require hex schema fingerprints in task artifacts.`


#### 29. `Replica-exchange restart desynchronizes energy ledger versus coordinates`
- **Status**: `refined`
- **Source**: `Option B repairable seed retained with status refined (review strengthening notes in Option B artifact)`
- **Topology**: `replica exchange + checkpoint RNG + unit consistency`
- **Symptom**: `After preempt, restarted run logs swap acceptances but WHAM reweighting disagrees with uninterrupted baseline thermodynamics.`
- **Discoveries**: `RNG reseed path differs on minor version without operators noticing.; Energy log column units reinterpreted after refactor in analysis notebook.; Restored replica ladder file predates final geometry constraints file in bundle.`
- **Evidence**: `trajectory=Verification; command_level=edge-cases; cluster=Long-Horizon-Coherence`
- **Exploits**: `Exploit 8: Resume tool treats appended frames as thermodynamically consistent without energy cross-check.; Exploit 1: Parser-computed energy disagrees with independent coords recomputation post-restart.`
- **Why hard**: `Stochastic MC machinery + checkpoint coherence.`
- **Main collapse risk**: `MD lore; use supplied tabular excerpts not live clusters.`


#### 30. `Coupled climate components desync when adaptive dt breaks lcm subcycling`
- **Status**: `refined`
- **Source**: `Option B repairable seed retained with status refined (review strengthening notes in Option B artifact)`
- **Topology**: `multi-physics coupling + adaptive timestep + calendar libs`
- **Symptom**: `Coupled run stable in logs yet tracers drift versus reference; appears when atmosphere adopts adaptive dt breaking lcm with ocean step after calendar lib update.`
- **Discoveries**: `Two calendar helpers round coupling exchange timestamps differently across leap policy.; Coupling assumes lcm relation silently false after adaptivity enables mid-run.; Field dumps show aligned timestamps while accumulator skips periodic commits.`
- **Evidence**: `trajectory=Execution; command_level=edge-cases; cluster=Long-Horizon-Coherence`
- **Exploits**: `Exploit 4: lcm schedule chosen before adaptive policy activates.; Exploit 8: “Coupling complete” logged when atmosphere advanced, not ocean applied flux.`
- **Why hard**: `Long-horizon coherence across mismatched integration clocks.`
- **Main collapse risk**: `Domain stack specific; keep lcm/calendar symptoms generic.`


#### 31. `Silent namelist typo flips microphysics suite on warm restart`
- **Status**: `refined`
- **Source**: `Option B repairable seed retained with status refined (review strengthening notes in Option B artifact)`
- **Topology**: `Fortran namelist + silent defaults + restart metadata`
- **Symptom**: `Forecast scores degrade after whitespace-only “no science” edit; parser accepts unknown key without error under ops I/O wrapper.`
- **Discoveries**: `IOSTAT handling swallows unknown keys depending on preprocessor defines.; Restart carries microphysics id inconsistent with cold-start namelist semantics.; Physics banner prints only under verbose rank0 flag off in production.`
- **Evidence**: `trajectory=Verification; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 6: Golden suite compares reflectivity imagery not microphysics tracers.; Exploit 5: Approval hashes file before automated whitespace normalization job.`
- **Why hard**: `Physics identity drifts silently across restart vs namelist intent.`
- **Main collapse risk**: `Domain model specific; generalize wording in final task.`


#### 32. `Cyclic symmetry harmonic metadata out of sync after sector mesh morph`
- **Status**: `refined`
- **Source**: `Option B repairable seed retained with status refined (review strengthening notes in Option B artifact)`
- **Topology**: `cyclic FE symmetry + morphed sector mesh + harmonic indices`
- **Symptom**: `Modal test matches reference unmorphed; after CAD tweak, sector coupling introduces spurious damping though mesh QC passes.`
- **Discoveries**: `Phase definition file references pre-morph node numbering while mesh db current.; Solver output binaries internally consistent yet disagree with postprocessor sector map.; Report generator rounds sector count biasing inferred phase increment.`
- **Evidence**: `trajectory=Coherence; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 1: Mesh geometric truth and harmonic expansion metadata disagree transiently.; Exploit 3: Regression compares first mode image not sector energy splits.`
- **Why hard**: `Multi-authority FE model across mesh vs cyclic boundary data.`
- **Main collapse risk**: `Commercial CAE jargon; neutralize in final instruction.`


#### 33. `Tucker tensor ALS stagnates when core initial guess orthogonality breaks silently`
- **Status**: `replacement`
- **Source**: `Generated to fill bank; 'scientific-computing' subsystem diversity`
- **Topology**: `tensor decomposition + alternating least squares + orthogonality`
- **Symptom**: `decomposition ‘converges’ in few iterations with fit metric flat while held-out reconstruction error blows up compared to reference numpy baseline on toy slice.`
- **Discoveries**: `Orthogonality constraints checked in Frobenius norm while mode matricization uses different scaling.; Random init uses rng stream restarted after first mode swipe desyncs factor orders.; Stochastic line search accepts steps violating rank feasibility until penalty too late.`
- **Evidence**: `trajectory=Verification; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 3: Unit test compares fit metric on training tensor only, not independent slice.; Exploit 5: Dashboard charts iteration count, not orthogonality residual norms.`
- **Why hard**: `Plausible convergence metrics on wrong subspace without NaNs.`
- **Main collapse risk**: `Numerical weeds; require reconstruction oracle on micro tensor.`


#### 34. `Exawind+Nalu coupling surface gradient lag after mesh motion substep`
- **Status**: `replacement`
- **Source**: `Generated to fill bank; 'scientific-computing' subsystem diversity`
- **Topology**: `FSI coupling + overset + field transfer`
- **Symptom**: `Stable coupled solve starts shedding spurious vorticity after enabling mesh motion every N steps; uncoupled solvers match reference.`
- **Discoveries**: `Transfer algorithm uses displacement from t but traction from t−Δt without documented stagger.; Overset donor cell ids cached across regrid smaller than cg motion amplitude.; Coupling logger prints ‘exchange ok’ when only halo sync completed, not volume conservation check.`
- **Evidence**: `trajectory=Execution; command_level=not-waiting; cluster=Long-Horizon-Coherence`
- **Exploits**: `Exploit 8: Coupling pipeline marks timestep complete when atmosphere advanced, not ocean received matching flux snapshot.; Exploit 4: Early fixed exchange cadence chosen before adaptive motion subcycling enabled.`
- **Why hard**: `Multi-code coupling with temporal skew on moving interfaces.`
- **Main collapse risk**: `Stack-branded; neutralize names in instruction; keep flux lag symptoms.`
- **RC6 discipline**: `RC6: strip vendor code names from final task text;`


#### 35. `RDKit aromaticity model toggles kekulization for same SMILES across versions`
- **Status**: `replacement`
- **Source**: `Generated to fill bank; 'scientific-computing' subsystem diversity`
- **Topology**: `SMILES parsing + aromaticity perception + reaction mapping`
- **Symptom**: `Registered reaction mapping yields different product inchis on upgrade with ‘no chemistry changes’ in release notes; QA only compared canonical smiles string equality.`
- **Discoveries**: `Aromatic perception for fused heterocycles uses different DFS start after perf patch.; Kekulization failure falls back to alternate form only logged at debug level.; InChI layer compares tautomer-agnostic while pipeline stores tautomer-specific keys in warehouse.`
- **Evidence**: `trajectory=Coherence; command_level=edge-cases; cluster=Robust-Verification`
- **Exploits**: `Exploit 1: String identity of inputs and graph-based identity diverge post-upgrade.; Exploit 6: QA hashes SMILES not InChI key layers tied to aromatic model.`
- **Why hard**: `Cheminformatics identity under perception policy drift.`
- **Main collapse risk**: `Library churn; pin versions or multi-perception oracle.`


#### 36. `Protein MD replica exchange with PLUMED METAD bias file path mismatch on restart`
- **Status**: `replacement`
- **Source**: `Generated to fill bank; 'scientific-computing' subsystem diversity`
- **Topology**: `metadynamics + REST + checkpoint paths`
- **Symptom**: `After checkpoint, free energy surfaces look smoother but contradict umbrella samples; WHAM weights show abrupt kink only on restarted leg.`
- **Discoveries**: `PLUMED reads hills file relative path that differs after slurm stageout changes cwd.; Gromacs '-rerun' mode reparses bias with different grid spacing default when omitted.; HILLS print precision truncation loses crest ids mapping to replica indices.`
- **Evidence**: `trajectory=Verification; command_level=edge-cases; cluster=Long-Horizon-Coherence`
- **Exploits**: `Exploit 8: Resume script treats trajectory continuation as bias continuation without file hash check.; Exploit 3: Validation compares PMF pngs only, not per-replica bias accumulators.`
- **Why hard**: `Enhanced sampling coherence across filesystem-relative artifacts.`
- **Main collapse risk**: `MD package coupling; use table excerpts not live HPC.`
- **RC6 discipline**: `RC6: avoid mandating named MD engine flags in learner instruction;`


#### 37. `AllenNLP multi-task heads share encoder but adaptive loss weights freeze wrong task`
- **Status**: `replacement`
- **Source**: `Generated to fill bank; 'scientific-computing' subsystem diversity`
- **Topology**: `multi-task learning + uncertainty weighting + scheduler`
- **Symptom**: `Primary metric regresses while auxiliary task soars; gradient norms look healthy; bisect implicates training script order not model graph.`
- **Discoveries**: `Homoscedastic uncertainty parameters marked non-trainable after warm start deserialization.; Learning rate scheduler steps on combined loss while weights for tasks on different step cadence.; 'torch.compile' drops side-effect ops registering task-specific hooks on first graph capture.`
- **Evidence**: `trajectory=Coherence; command_level=edge-cases; cluster=Complex-System-Builds`
- **Exploits**: `Exploit 4: First forward pass captures graph with auxiliary loss weight=1 frozen thereafter.; Exploit 7: Disabling compile ‘fixes’ training but violates latency contract storyline.`
- **Why hard**: `Training machinery couples tasks through mutating loss orchestration, not architecture.`
- **Main collapse risk**: `Framework-named; abstract to multi-task weight + compile interaction.`
