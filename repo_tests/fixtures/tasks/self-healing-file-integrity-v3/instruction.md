You are working in `/app` on a self-healing file integrity monitor where some changes are legitimate operator drift and some are tampering. Work deterministically and keep changes on container-local paths only.

Read `/app/policy/corpus.txt`, `/app/policy/report_digest_contract.txt`, `/app/readme_lexicon.txt`, `/app/state/ledger.json`, `/app/pristine`, and `/app/monitored`. Compute digests from actual file contents. Treat `/app/decoys` as unrelated noise, not monitored corpus.

Signal completion of each segment before starting the next by writing that segment’s marker file first, then continuing.

### Part 1 — Inventory and ledger baseline

Create `/app/output/scan_inventory.json` and `/app/output/milestone_1.done`.

The inventory must expose files (the monitored-path listing) and policy_digest (the policy anchor derived from corpus bytes). It must satisfy `output_contract.toml` and the field spellings in `readme_lexicon`. Path membership must align with a recursive scan of `/app/monitored` that honors the ledger’s ignore patterns (scratch under `tmp/` illustrates what gets skipped). Decoys must not appear in the monitored listing. The policy anchor on the inventory must match the digest recipe for `/app/policy/corpus.txt` given in `report_digest_contract.txt`. If you delete a file later during healing, the captured inventory may still mention its absolute path from when it existed.

Before editing `/app/state/ledger.json`, record the current `baseline_version` as `baseline_version_before` for the downstream report. Advance `baseline_version` to 2, attach the policy anchor digest beside it, and keep per-path records as an object keyed by absolute paths as described in `report_digest_contract.txt`.

### Part 2 — Detection alerts

Create `/app/state/alerts.json` and `/app/output/milestone_2.done`.

Persist alerts as JSON whose root value is an array of objects (not an object containing an array). Produce three alerts for `/app/monitored/bin/agent.sh`, `/app/monitored/conf/system.conf`, and `/app/monitored/bin/injector.sh`. Each alert includes path, classification, recommended_action, and the live-byte digest field naming from readme_lexicon for alerts. Two concern tampering on established paths; one concerns an added executable. Alert digest conventions differ from integrity-report rows; both are covered in `report_digest_contract.txt`.

### Part 3 — Remediation and integrity report

Repair from `/app/pristine`, remove unauthorized executables, preserve operator-approved documentation drift, append `/app/state/actions.log`, write `/app/output/integrity_report.json`, then `/app/output/milestone_3.done`. Preserve file modes when copying. When you accept retained drift, refresh ledger hashes so they stay faithful to bytes on disk afterward.

Shape the integrity report with top-level scan_id, total_files_scanned, ignored_files, legitimate_changes, malicious_changes, healed_files, unresolved_files, baseline_version_before, baseline_version_after, status, and file_results properties. Each file_results row includes action alongside classification and digest columns described in readme_lexicon. Keep policy_digest off the report root per report_digest_contract.txt. Log-line wording, counters, terminal status, and the scan fingerprint tying the report back to the phase-one inventory and policy anchor are all defined in `report_digest_contract.txt`.
