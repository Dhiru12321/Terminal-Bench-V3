Python helpers live under `/app`.

Operators see an intermittent wedge tied to abrupt outages. Many workers restart in one tight window near host bring-up completion. Downstream roles drift unusable. Supervision marks those roles active anyway. Single-worker sequential restarts behave normally.

Readiness signals can disagree with the supervisory view: brief busy-resource noise wraps diagnostic buffers and ages out; openness-style checks keep reporting success. The readiness path also needs corroboration from persisted coordination metadata, not from a listen stub alone.

Scratch uses tmpfs-class storage plus advisory serialization around one gate pathname. Automation may remove that gate mid compaction; callers can keep expecting the working copy file. Compaction paths should not drop the guarded working copy under active gate ownership.

Kernel reload notifications overlap inaugural startup traffic. Reload-tagged bytes merged with the body marker belong in persisted coordination metadata with the inaugural seal, not stranded ahead of it.

Epoch counters in coordination metadata stay monotonic across mid-wave scrubs. Later seals advance earlier committed values instead of winding them backward.

Repair concurrent batch startup together with reload interleavings. Limit edits to `/app` with absolute paths.

Publish `/app/output/coherence.json` with booleans `handles_ok`, `tail_ok`, and `facet_ok` describing batch-path alignment, sequential stability, and reload or compaction fences respectively.

Deterministic replay scaffolding sits under `/app/fixtures`. Bundled JSON transcripts live under `/app/fixtures/transcripts`.
