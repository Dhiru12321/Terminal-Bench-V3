# task-implementations

Historical implementation plans, one per task, written while those tasks were
being built under Terminus 2nd Edition. They are kept as a record of how a task
was reasoned through, not as templates.

Do not copy the `task.toml` blocks or the packaging checklists out of these
files. They predate Terminus 3 and still show retired keys (`version`,
`codebase_size`, `number_of_milestones`, `subcategories`, `allow_internet`,
the minute-based time estimates), Edition 2 category names, and the
`easy`/`medium`/`hard` tiers. None of those parse or pass CI any more, and the
files were deliberately left unedited rather than rewritten, because rewriting
them would misrepresent decisions that were made under the older rules.

For the current shape, start from `default-template/`. For current policy, see
`.cursor/rules/task-creation.mdc` and `docs/`. What remains genuinely useful
here is the reasoning: how each plan picked a failure mode, chose what to reveal
in the instruction, and designed verification around it.
