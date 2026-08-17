# new_rules

Two different kinds of document live here, and they are maintained differently.

## `upstream/`

A verbatim copy of the Terminus 3 documentation, kept in the section layout the
upstream site publishes. `upstream/INDEX.md` is the table of contents.

This is reference material, not repo policy. Do not hand-edit it: when the
upstream docs change, replace the directory wholesale so the copy stays a
faithful snapshot and diffs stay readable. Anything that has to *bind* — a rule
an agent must follow or a check that must fire — belongs in `.cursor/rules/`,
`docs/`, or an enforcement script, with the upstream doc cited as its source.

Where this repo is stricter than upstream, the repo wins; `docs/HARD_BUT_FAIR_AUTHORING.md`
is the clearest example.

## `hard-task-ideas*.md`

Repo-authored seed banks, generated during idea generation and kept for reuse and
calibration. These are drafts to mine, not commitments: an idea here has not been
through Step 2a, and its stated tier is a target rather than a measurement.
Difficulty is only real once the platform has measured it.
