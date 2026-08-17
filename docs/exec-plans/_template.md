# <change-name>

## Goal

One sentence. What does this change do?

## Trigger

Which CNI item, reviewer feedback, repeated failure, or upstream
policy update is this responding to? Cite specific instances.

## Change surface

Files touched, lines added/removed, new constants/patterns introduced.

## False-positive risk

Walk through the patterns/checks added. For each, name the closest
*legitimate* construct that could match it and explain why the design
doesn't false-positive on it. (For example, the milestone warning had
to handle `milestone_count` as a code identifier; the hidden-instruction
check had to handle `# TODO:` in source comments.)

## Effect on existing fixtures and tasks

Run the new check against `repo_tests/fixtures/tasks/` and `tasks/`. List
how each task is affected. If any fixture or task changes status, justify.

## Tests

List the regression tests added. Each test should pin one of:
- The intended FAIL/WARN behavior.
- A specific false-positive guard.
- A specific edge case.

## Rollback

If this change has to be reverted, what's the procedure? Specifically:
which fixtures need to revert, which tasks need to be unblocked, which
documentation needs updating.

## Verification done

- [ ] All real tasks under `tasks/` pass with the new check.
- [ ] All fixtures pass.
- [ ] Pre-existing test failures in baseline are unchanged.
- [ ] `repo_tests/cases.py` updated if pass-message set changed.
- [ ] REPO_CONVENTIONS.md and commands.md updated.
