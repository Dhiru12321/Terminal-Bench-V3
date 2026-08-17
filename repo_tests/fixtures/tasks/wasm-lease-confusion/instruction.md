`/app/output/lease_report.json` shows execution gates and lease listing out of sync after restart-aware replay and restore. Align the sandbox Rust reconcile path so listing and exec share one reconciled verdict for every bundled lease scenario.

Produce a deterministic JSON array: order and cardinality follow `/app/fixtures/scenario_index.json` rows, one entry per opaque scenario id without duplicates or spill fields. Restart epoch comes from `/app/fixtures/replay_profile.toml`. Each entry carries scenario, booleans can_execute and listed (equal on every line), restart_epoch as an integer, and status summarizing simultaneous grant plus listing (consistent_allow), simultaneous denial plus hidden listing (consistent_deny), or mismatch (divergent, which coherent repairs remove). Acceptance follows `/app/fixtures/leases.json` epochs and flags against that restart stamp—not scenario spellings.

Do not rely on internet access or external services.
