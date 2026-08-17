You are working in `/app` on a Python simulator for hierarchical charge accounting across shards. Upper-level aggregates disagree with on-box-style totals. Re-homing shifts blame between shards. Stale attach paths linger across configuration refresh with an active side channel.

Use `/app` only. Subsystem roots are listed in `/app/docs/catalog_paths.txt`. JSON timelines live in `/app/fixtures`. Optional checks: `python3 /app/runner/entry.py noop` or `replay --fixture <basename>`.

Write `/app/output/charge_view.json` with booleans `handles_ok`, `aligned_ok`, `skew_ok`. `handles_ok`: attach ids track the layout generation through refresh bumps. `aligned_ok`: both reader scalars match for one replay. `skew_ok`: `replay_order_a.json` and `replay_order_b.json` yield identical shard totals. Set all three true together only if those properties hold for the bundled replays.

Write `/app/output/stage.done` in the same pass as a coherent `charge_view.json`.
