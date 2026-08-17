"""Doc-size caps for the v2.1 always-on / agent-requested orientation files.

These caps are a load-bearing part of the v2.1 rollout: when always-on or
agent-requested rule files grow without bound, agents skim them and the rule
stops firing reliably. Each cap below has a documented rationale in
`docs/exec-plans/harness-v2.1-rollout.md` and `tb3-repo-agent-harness_plan-v2.1.md`
§§ 1, 2, 8.

The caps are intentionally annoying to bump. The right escalation when a cap
is hit is one of:
  - Demote a bullet to a deeper rule (see CNI.md demotion policy).
  - Shorten an existing bullet.
  - Write an exec-plan justifying the raise.
Bumping the cap silently defeats the rollout; that's what these tests prevent.
"""

from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

AGENTS_MD = REPO_ROOT / "AGENTS.md"
ARCHITECTURE_MD = REPO_ROOT / "docs" / "ARCHITECTURE.md"
CRITICAL_RULE_MDC = REPO_ROOT / ".cursor" / "rules" / "00-authoring-critical.mdc"

AGENTS_BYTE_CAP = 1500
AGENTS_LINE_ADVISORY = 50
ARCHITECTURE_LINE_CAP = 100
CRITICAL_RULE_BYTE_CAP = 4096

# Phrases that mark policy/rule prose; codemap content must point at owning
# files instead of restating the rules. The list is taken verbatim from
# `docs/exec-plans/harness-v2.1-rollout.md` (Tests section, the
# `test_architecture_contains_no_rule_content` bullet). Match is
# case-sensitive so that legitimate code identifiers like
# `FORBIDDEN_ROOT_FILES` (the Python constant in `scripts/validate_submission_zip.py`,
# referenced in the codemap as the file's owned constant) do not false-
# positive on the lowercase rule-prose word `forbidden`.
ARCHITECTURE_FORBIDDEN_PHRASES = (
    "alwaysApply:",
    "should not",
    "must not",
    "forbidden",
)


class DocSizeCapsTest(unittest.TestCase):
    def test_agents_md_within_byte_cap(self) -> None:
        """`AGENTS.md` is the only always-on routing file. Hard cap is
        1500 bytes (binding) so agents do not skim it. See plan §1."""
        size = len(AGENTS_MD.read_bytes())
        self.assertLessEqual(
            size,
            AGENTS_BYTE_CAP,
            f"AGENTS.md is {size} bytes; cap is {AGENTS_BYTE_CAP}. "
            "Shorten a bullet or demote one to .cursor/rules/00-authoring-critical.mdc.",
        )

    def test_agents_md_within_line_advisory(self) -> None:
        """The 50-line advisory is the secondary cap (the byte cap is
        primary). Documented as advisory because line counts are
        informally helpful but not the binding constraint — the byte cap
        is what catches semantic bloat regardless of formatting choice."""
        line_count = len(AGENTS_MD.read_text(encoding="utf-8").splitlines())
        self.assertLessEqual(
            line_count,
            AGENTS_LINE_ADVISORY,
            f"AGENTS.md has {line_count} lines; advisory cap is {AGENTS_LINE_ADVISORY}.",
        )

    def test_architecture_within_line_cap(self) -> None:
        """`docs/ARCHITECTURE.md` is the codemap. Hard cap is 100 lines
        so it stays a one-page map and not a tutorial. See plan §8."""
        line_count = len(
            ARCHITECTURE_MD.read_text(encoding="utf-8").splitlines()
        )
        self.assertLessEqual(
            line_count,
            ARCHITECTURE_LINE_CAP,
            f"docs/ARCHITECTURE.md has {line_count} lines; cap is "
            f"{ARCHITECTURE_LINE_CAP}. The codemap is not the place for "
            "tutorials or policy — link to the owning file instead.",
        )

    def test_architecture_contains_no_rule_content(self) -> None:
        """`docs/ARCHITECTURE.md` is a codemap, not a rulebook. Rule prose
        belongs in `.cursor/rules/*.mdc` or `REPO_CONVENTIONS.md`. The
        forbidden-phrase list is documented in the rollout exec-plan;
        match is case-sensitive so that code identifiers like
        `FORBIDDEN_ROOT_FILES` (a Python constant whose owning file is
        named in the codemap) do not false-positive on the lowercase
        rule-prose word `forbidden`."""
        content = ARCHITECTURE_MD.read_text(encoding="utf-8")
        for phrase in ARCHITECTURE_FORBIDDEN_PHRASES:
            with self.subTest(phrase=phrase):
                self.assertNotIn(
                    phrase,
                    content,
                    f"docs/ARCHITECTURE.md must not contain rule-prose "
                    f"phrase '{phrase}' (move it to a *.mdc rule or to "
                    "REPO_CONVENTIONS.md).",
                )

    def test_critical_rule_within_byte_cap(self) -> None:
        """`.cursor/rules/00-authoring-critical.mdc` is the agent-
        requested expanded discipline. Hard cap is 4096 bytes so it
        stays scannable in one read; same load-bearing logic as the
        AGENTS.md byte cap. See plan §2."""
        size = len(CRITICAL_RULE_MDC.read_bytes())
        self.assertLessEqual(
            size,
            CRITICAL_RULE_BYTE_CAP,
            f"00-authoring-critical.mdc is {size} bytes; cap is "
            f"{CRITICAL_RULE_BYTE_CAP}. Demote a bullet to a deeper rule "
            "or shorten an existing one (see plan §2 / CNI demotion policy).",
        )


if __name__ == "__main__":
    unittest.main()
