The Rust project under /app runs a reload pipeline whose /app/output/reload_report.json and /app/output/probe_trace.json disagree with generation reality. Make those two files line up with /app/data/scenarios: one entry per scenario file, matching keys, no missing rows, no duplicates.

At completion, ordinary rows show one shared generation figure across the row’s generation slots and matching positive booleans on report versus trace. Lagged-reload rows that converge behave like ordinary rows.

Rows where live-read generation stops short of the committed endpoint keep the report’s overall success flag raised while both surfaces show verifier rejection; generation slots reflect committed versus live-read endpoints from that scenario’s JSON. The two files stay paired: shared committed figures, report live-read column aligned to trace observed column, boolean gates aligned row-by-row.
