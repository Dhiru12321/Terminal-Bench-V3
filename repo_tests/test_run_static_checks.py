from __future__ import annotations

import contextlib
import io
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts import run_static_checks
from repo_tests.cases import COMMON_STATIC_PASS_MESSAGES, FIXTURE_TASKS_DIR, STATIC_CHECK_EXPECTATIONS

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "run_static_checks"


class RunStaticChecksRegressionTest(unittest.TestCase):
    """Pin repo-level static checker results for the checked-in benchmark fixtures."""

    def copy_fixture(self, fixture_name: str, tmpdir: str) -> Path:
        fixture_dir = FIXTURES_DIR / fixture_name
        task_dir = Path(tmpdir) / fixture_name
        shutil.copytree(fixture_dir, task_dir)
        return task_dir

    def test_fixture_tasks_keep_pinned_static_check_results(self) -> None:
        for task_name, expected in STATIC_CHECK_EXPECTATIONS.items():
            with self.subTest(task=task_name):
                reporter = run_static_checks.run_checks(FIXTURE_TASKS_DIR / task_name)
                self.assertEqual(reporter.failures, [])
                self.assertEqual(reporter.warnings, expected["warnings"])
                for message in COMMON_STATIC_PASS_MESSAGES:
                    self.assertIn(message, reporter.passes)

    def test_cli_exit_code_stays_successful_for_fixture_tasks(self) -> None:
        for task_name in STATIC_CHECK_EXPECTATIONS:
            with self.subTest(task=task_name):
                stdout = io.StringIO()
                with contextlib.redirect_stdout(stdout):
                    exit_code = run_static_checks.main(
                        ["--task-dir", str(FIXTURE_TASKS_DIR / task_name), "--version", "terminus_3"]
                    )
                self.assertEqual(exit_code, 0)
                self.assertIn("PASS", stdout.getvalue())

    def test_reward_json_footer_is_rejected(self) -> None:
        fixture = FIXTURE_TASKS_DIR / "implicit-step-restart"
        with tempfile.TemporaryDirectory() as tmpdir:
            task_dir = Path(tmpdir) / fixture.name
            shutil.copytree(fixture, task_dir)

            test_sh = task_dir / "tests" / "test.sh"
            content = test_sh.read_text(encoding="utf-8")
            test_sh.write_text(
                content.replace("/logs/verifier/reward.txt", "/logs/verifier/reward.json"),
                encoding="utf-8",
            )

            reporter = run_static_checks.run_checks(task_dir)

        self.assertIn(
            "tests/test.sh must emit /logs/verifier/reward.txt; reward.json is not a supported reward sink",
            reporter.failures,
        )

    def test_default_template_test_sh_matches_canonical_prefix(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        test_sh = (repo_root / "default-template" / "tests" / "test.sh").read_text(encoding="utf-8")
        substantive_lines = run_static_checks.substantive_shell_lines(test_sh)
        mismatches = run_static_checks.test_sh_prefix_mismatches(substantive_lines)
        self.assertEqual(mismatches, [])

    def test_internal_harness_path_leak_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            task_dir = self.copy_fixture("public-contract-standard", tmpdir)
            instruction_path = task_dir / "instruction.md"
            instruction_path.write_text(
                instruction_path.read_text(encoding="utf-8")
                + "\nDo not touch `/app/.state/private-cache.bin` while preparing the output.\n",
                encoding="utf-8",
            )

            reporter = run_static_checks.run_checks(task_dir, {"output_contract"})

        self.assertIn(
            "instruction.md must not mention internal_harness_files unless they are also declared in user_visible_outputs: /app/.state/private-cache.bin",
            reporter.failures,
        )

    def test_internal_harness_path_is_allowed_when_it_is_also_user_visible(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            task_dir = self.copy_fixture("public-contract-standard", tmpdir)
            contract_path = task_dir / "output_contract.toml"
            contract_path.write_text(
                contract_path.read_text(encoding="utf-8").replace(
                    'internal_harness_files = [\n  "/app/.state/private-cache.bin",\n]',
                    'internal_harness_files = [\n  "/app/out/report.json",\n]',
                ),
                encoding="utf-8",
            )

            reporter = run_static_checks.run_checks(task_dir, {"output_contract"})

        self.assertEqual(reporter.failures, [])
        self.assertIn("output contract matches the declared user-visible outputs and schema checks", reporter.passes)

    def test_milestone_word_in_instruction_emits_nonblocking_warning(self) -> None:
        """Terminus 3 removed milestone tasks, so the word now reads as a
        leftover from the previous edition. The checker surfaces it as a
        warning so authors rephrase before submit, but must not fail: the
        wording alone does not make the task invalid."""
        with tempfile.TemporaryDirectory() as tmpdir:
            task_dir = self.copy_fixture("public-contract-standard", tmpdir)
            instruction_path = task_dir / "instruction.md"
            instruction_path.write_text(
                "For the current milestone, write `/app/out/report.json` as JSON with "
                "`checksum` and `status` fields. Later milestones reuse the same file.\n",
                encoding="utf-8",
            )

            reporter = run_static_checks.run_checks(task_dir, {"instruction"})

        self.assertEqual(reporter.failures, [])
        milestone_warnings = [
            warning for warning in reporter.warnings
            if "instruction.md contains the word 'milestone'" in warning
        ]
        self.assertEqual(len(milestone_warnings), 1, reporter.warnings)
        self.assertIn("2 occurrence(s)", milestone_warnings[0])

    def test_milestone_word_warning_is_silent_when_instruction_uses_neutral_wording(self) -> None:
        """Authors who rephrase 'milestone' as 'step' should not see the
        warning; the check looks at prose only."""
        with tempfile.TemporaryDirectory() as tmpdir:
            task_dir = self.copy_fixture("public-contract-standard", tmpdir)
            instruction_path = task_dir / "instruction.md"
            instruction_path.write_text(
                "For the current step, write `/app/out/report.json` as JSON with `checksum` and "
                "`status` fields.\n",
                encoding="utf-8",
            )

            reporter = run_static_checks.run_checks(task_dir, {"instruction"})

        self.assertEqual(reporter.failures, [])
        milestone_warnings = [
            warning for warning in reporter.warnings
            if "instruction.md contains the word 'milestone'" in warning
        ]
        self.assertEqual(milestone_warnings, [])

    def test_milestone_word_warning_ignores_underscored_identifiers(self) -> None:
        """Identifiers like `milestone_count` must not trigger the warning —
        the underscore prevents `\\b` from matching, and the rule targets prose
        usage of the word, not field-name references."""
        with tempfile.TemporaryDirectory() as tmpdir:
            task_dir = self.copy_fixture("public-contract-standard", tmpdir)
            instruction_path = task_dir / "instruction.md"
            instruction_path.write_text(
                "Write `/app/out/report.json` as JSON with `checksum` and `status` fields. "
                "The `milestone_count` field is a leftover identifier, not user-facing.\n",
                encoding="utf-8",
            )

            reporter = run_static_checks.run_checks(task_dir, {"instruction"})

        self.assertEqual(reporter.failures, [])
        milestone_warnings = [
            warning for warning in reporter.warnings
            if "instruction.md contains the word 'milestone'" in warning
        ]
        self.assertEqual(milestone_warnings, [])

    def test_steps_directory_is_rejected_as_milestone_layout(self) -> None:
        """Terminus 3 dropped milestone tasks; a leftover steps/ tree is the
        clearest signal a task was carried over without being migrated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            task_dir = self.copy_fixture("public-contract-standard", tmpdir)
            (task_dir / "steps" / "milestone_1" / "tests").mkdir(parents=True)

            reporter = run_static_checks.run_checks(task_dir, {"task_structure"})

        self.assertIn(
            "steps/ is a milestone-task layout and is not supported in Terminus 3",
            reporter.failures,
        )

    def test_oracle_knob_discoverability_warns_when_flag_is_invisible(self) -> None:
        """A knob referenced by solve.sh but absent from instruction.md
        AND absent from every comment/doc under environment/ must warn.

        Reproduces the rollback-replay-divergence failure mode: the oracle
        flips two CMake cache variables the agent cannot discover, so agents
        rewrite the source and lose the conditional-compilation ladder the
        grader depends on."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = FIXTURE_TASKS_DIR / "rollback-replay-divergence"
            task_dir = Path(tmpdir) / "rollback-replay-divergence"
            shutil.copytree(source, task_dir)
            shutil.rmtree(task_dir / "environment" / "build", ignore_errors=True)

            instruction = task_dir / "instruction.md"
            instruction.write_text(
                instruction.read_text(encoding="utf-8")
                .replace("`TB_TIMELINE_MODE`", "the timeline knob")
                .replace("`TB_REEXEC_MODE`", "the re-exec knob"),
                encoding="utf-8",
            )
            cmake = task_dir / "environment" / "CMakeLists.txt"
            lines = cmake.read_text(encoding="utf-8").splitlines(keepends=True)
            cmake.write_text(
                "".join(
                    line for line in lines
                    if not line.lstrip().startswith("#")
                ),
                encoding="utf-8",
            )

            reporter = run_static_checks.run_checks(
                task_dir, {"oracle_knob_discoverability"}
            )

        warnings = [w for w in reporter.warnings if "build knobs" in w]
        self.assertEqual(len(warnings), 1, reporter.warnings)
        self.assertIn("TB_TIMELINE_MODE", warnings[0])
        self.assertIn("TB_REEXEC_MODE", warnings[0])

    def test_oracle_knob_discoverability_passes_when_flag_is_named_in_instruction(self) -> None:
        """Mentioning the knob in instruction.md alone clears the check even if
        the environment/ sources have no comment for it."""
        reporter = run_static_checks.run_checks(
            FIXTURE_TASKS_DIR / "rollback-replay-divergence",
            {"oracle_knob_discoverability"},
        )
        self.assertEqual(reporter.failures, [])
        self.assertIn(
            "build knobs required by solve.sh and tests are discoverable from instruction.md or environment/",
            reporter.passes,
        )

    def test_oracle_knob_discoverability_ignores_standard_cmake_knobs(self) -> None:
        """Standard CMake / compiler knobs (CMAKE_BUILD_TYPE, CC, CFLAGS, ...)
        must never trigger the check, even if they never appear in
        instruction.md. Tasks that only use standard knobs report a clean
        'no bespoke build knobs required' pass."""
        reporter = run_static_checks.run_checks(
            FIXTURE_TASKS_DIR / "byzantine-storage-rebalance",
            {"oracle_knob_discoverability"},
        )
        self.assertEqual(reporter.failures, [])
        self.assertEqual([], [w for w in reporter.warnings if "build knobs" in w])

    def test_oracle_path_discoverability_warns_when_install_path_is_invisible(self) -> None:
        """Reproduces the rollback-replay-divergence v4 failure mode: agents
        built the binary, ran it, produced the correct SIGNOFF digests, and
        still failed every test because nothing told them to install the
        binary at /app/bin/netplay_matrix. The check must catch this by
        warning that the test-required path is undocumented."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = FIXTURE_TASKS_DIR / "rollback-replay-divergence"
            task_dir = Path(tmpdir) / "rollback-replay-divergence"
            shutil.copytree(source, task_dir)
            shutil.rmtree(task_dir / "environment" / "bin", ignore_errors=True)
            shutil.rmtree(task_dir / "environment" / "build", ignore_errors=True)

            instruction = task_dir / "instruction.md"
            instruction.write_text(
                instruction.read_text(encoding="utf-8")
                .replace("install it at `/app/bin/netplay_matrix`", "install the binary")
                .replace("`/app/bin/netplay_matrix`", "the binary"),
                encoding="utf-8",
            )

            reporter = run_static_checks.run_checks(
                task_dir, {"oracle_path_discoverability"}
            )

        warnings = [w for w in reporter.warnings if "agent must create" in w]
        self.assertEqual(len(warnings), 1, reporter.warnings)
        self.assertIn("/app/bin/netplay_matrix", warnings[0])

    def test_oracle_path_discoverability_passes_when_path_is_named_in_instruction(self) -> None:
        """Positive case on the patched fixture: every absolute /app path the
        tests resolve is either in the shipped tree, under a standard build-
        output prefix, or named in instruction.md / environment/."""
        reporter = run_static_checks.run_checks(
            FIXTURE_TASKS_DIR / "rollback-replay-divergence",
            {"oracle_path_discoverability"},
        )
        self.assertEqual(reporter.failures, [])
        self.assertIn(
            "agent-target paths declared in tests/ are discoverable from instruction.md or environment/",
            reporter.passes,
        )

    def test_oracle_path_discoverability_accepts_string_literals_in_source(self) -> None:
        """Paths mentioned only as quoted string literals in source files
        (e.g. ``const DefaultPath = \"/app/config/foo.yaml\"`` in Go,
        ``std::string work_dir = \"/app/work\"`` in C++) are discoverable —
        the agent can grep for them. This distinguishes paths from build
        knobs, where bare-code references don't count.

        Specifically: byzantine-storage-rebalance documents
        /app/config/sim_defaults.yaml only via a Go string-literal
        constant; the check must not warn on it."""
        reporter = run_static_checks.run_checks(
            FIXTURE_TASKS_DIR / "byzantine-storage-rebalance",
            {"oracle_path_discoverability"},
        )
        self.assertEqual(reporter.failures, [])
        self.assertEqual([], [w for w in reporter.warnings if "agent must create" in w])

    def test_oracle_path_discoverability_skips_standard_build_output_dirs(self) -> None:
        """Paths under /app/build/ (cmake), /app/target/ (cargo), /app/dist/
        and similar standard build-tool output directories are managed by
        the agent's toolchain and don't need to be documented in
        instruction.md."""
        reporter = run_static_checks.run_checks(
            FIXTURE_TASKS_DIR / "release-provenance-drift",
            {"oracle_path_discoverability"},
        )
        self.assertEqual(reporter.failures, [])
        warnings_with_build_dirs = [
            w for w in reporter.warnings
            if "/app/build/" in w or "/app/target/" in w
        ]
        self.assertEqual(warnings_with_build_dirs, [])

    def test_instruction_test_vocabulary_catches_extended_assertion_shapes(self) -> None:
        """The vocabulary check must catch all four assertion shapes:
        ``X == LITERAL``, ``X.startswith(LITERAL)``, ``LITERAL in X``,
        and ``len(X) == NUMBER`` — for any X reading an instruction-named
        field. Reproduces the release-provenance-drift gap where
        ``len(snapshot["epoch"]) == 24`` was tested but never documented."""
        with tempfile.TemporaryDirectory() as tmpdir:
            task_dir = Path(tmpdir) / "vocab_test"
            task_dir.mkdir()
            (task_dir / "instruction.md").write_text(
                "Output a `result` field. The status field is also part of the contract.\n"
            )
            tests = task_dir / "tests"
            tests.mkdir()
            (tests / "test_outputs.py").write_text(
                "def test_a():\n"
                "    obj = {}\n"
                "    assert obj['result'] == 'undocumented_value'\n"
                "    assert obj['result'].startswith('undocumented_prefix')\n"
                "    assert obj['result'].endswith('undocumented_suffix')\n"
                "    assert 'undocumented_substring' in obj['result']\n"
                "    assert len(obj['result']) == 42\n"
            )

            named_fields = run_static_checks._instruction_named_fields(
                (task_dir / "instruction.md").read_text(encoding="utf-8")
            )
            findings = run_static_checks._literal_assertions_on_named_fields(
                tests / "test_outputs.py", named_fields
            )

        literals_found = {literal for _, _, literal in findings}
        self.assertIn("undocumented_value", literals_found)         # ==
        self.assertIn("undocumented_prefix", literals_found)        # startswith
        self.assertIn("undocumented_suffix", literals_found)        # endswith
        self.assertIn("undocumented_substring", literals_found)     # in
        self.assertIn("42", literals_found)                         # len ==

    def test_instruction_test_vocabulary_passes_when_extended_literals_are_documented(self) -> None:
        """Counterpart to the negative test: when each literal IS named in
        instruction.md, no warning fires across all four assertion shapes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            task_dir = Path(tmpdir) / "vocab_pass"
            task_dir.mkdir()
            (task_dir / "instruction.md").write_text(
                "The `result` field equals 'documented_value', begins with "
                "'documented_prefix', ends with 'documented_suffix', contains "
                "the substring 'documented_substring', and has length 42.\n"
            )
            tests = task_dir / "tests"
            tests.mkdir()
            (tests / "test_outputs.py").write_text(
                "def test_a():\n"
                "    obj = {}\n"
                "    assert obj['result'] == 'documented_value'\n"
                "    assert obj['result'].startswith('documented_prefix')\n"
                "    assert obj['result'].endswith('documented_suffix')\n"
                "    assert 'documented_substring' in obj['result']\n"
                "    assert len(obj['result']) == 42\n"
            )

            named_fields = run_static_checks._instruction_named_fields(
                (task_dir / "instruction.md").read_text(encoding="utf-8")
            )
            findings = run_static_checks._literal_assertions_on_named_fields(
                tests / "test_outputs.py", named_fields
            )
            instruction_text = (task_dir / "instruction.md").read_text(encoding="utf-8")
            undocumented = [
                (field, literal) for _, field, literal in findings
                if literal not in instruction_text
            ]

        self.assertEqual(undocumented, [])

    def test_timeout_coherence_warns_when_subprocess_timeouts_exceed_verifier(self) -> None:
        """Reproduces the implicit-step-restart v6 failure mode: tests/
        declare explicit ``subprocess.run(..., timeout=N)`` ceilings on
        each cmake step (180+180+60+120+120+30 = 690s), but the verifier
        budget was 600s. The check must sum those literals and warn when
        the sum exceeds verifier.timeout_sec — that's the real wall-time
        ceiling, not the build-site count."""
        with tempfile.TemporaryDirectory() as tmpdir:
            task_dir = Path(tmpdir) / "tsum"
            task_dir.mkdir()
            (task_dir / "task.toml").write_text(
                'artifacts = ["/app/output.txt"]\n'
                "[metadata]\n"
                'author_name = "anonymous"\n'
                'author_email = "anonymous"\n'
                'difficulty = "advanced"\n'
                'category = "Software"\n'
                'subcategory = "Systems"\n'
                'tags = []\n'
                'languages = ["c++"]\n'
                "expert_time_estimate_hours = 1\n"
                "[agent]\n"
                "timeout_sec = 1800\n"
                "[verifier]\n"
                "timeout_sec = 600\n"
                "[environment]\n"
                "build_timeout_sec = 600\n"
                "cpus = 2\n"
                "memory_mb = 4096\n"
                "storage_mb = 10240\n"
            )
            tests = task_dir / "tests"
            tests.mkdir()
            # Tests with explicit per-call timeouts summing > verifier
            (tests / "test_outputs.py").write_text(
                "import subprocess\n"
                "def test_x():\n"
                "    subprocess.run(['cmake', '-S', '.', '-B', 'build'], timeout=180)\n"
                "    subprocess.run(['cmake', '--build', 'build'], timeout=180)\n"
                "    subprocess.run(['./bin'], timeout=60)\n"
                "    subprocess.run(['cmake', '-S', 'p', '-B', 'pb'], timeout=120)\n"
                "    subprocess.run(['cmake', '--build', 'pb'], timeout=120)\n"
                "    subprocess.run(['./pb/probe'], timeout=30)\n"
            )

            reporter = run_static_checks.run_checks(task_dir, {"timeout_coherence"})

        sum_warnings = [w for w in reporter.warnings if "exceeds verifier" in w]
        self.assertEqual(len(sum_warnings), 1, reporter.warnings)
        self.assertIn("690s", sum_warnings[0])
        self.assertIn("600s", sum_warnings[0])

    def test_timeout_coherence_passes_when_subprocess_timeout_sum_fits_verifier(self) -> None:
        """Counterpart positive: same six subprocesses, verifier raised to
        900s, the sum (690s) fits under it, and the new rule stays silent."""
        with tempfile.TemporaryDirectory() as tmpdir:
            task_dir = Path(tmpdir) / "tfit"
            task_dir.mkdir()
            (task_dir / "task.toml").write_text(
                'artifacts = ["/app/output.txt"]\n'
                "[metadata]\n"
                'author_name = "anonymous"\n'
                'author_email = "anonymous"\n'
                'difficulty = "advanced"\n'
                'category = "Software"\n'
                'subcategory = "Systems"\n'
                'tags = []\n'
                'languages = ["c++"]\n'
                "expert_time_estimate_hours = 1\n"
                "[agent]\n"
                "timeout_sec = 1800\n"
                "[verifier]\n"
                "timeout_sec = 900\n"
                "[environment]\n"
                "build_timeout_sec = 600\n"
                "cpus = 2\n"
                "memory_mb = 4096\n"
                "storage_mb = 10240\n"
            )
            tests = task_dir / "tests"
            tests.mkdir()
            (tests / "test_outputs.py").write_text(
                "import subprocess\n"
                "def test_x():\n"
                "    subprocess.run(['cmake', '-S', '.', '-B', 'build'], timeout=180)\n"
                "    subprocess.run(['cmake', '--build', 'build'], timeout=180)\n"
                "    subprocess.run(['./bin'], timeout=60)\n"
                "    subprocess.run(['cmake', '-S', 'p', '-B', 'pb'], timeout=120)\n"
                "    subprocess.run(['cmake', '--build', 'pb'], timeout=120)\n"
                "    subprocess.run(['./pb/probe'], timeout=30)\n"
            )

            reporter = run_static_checks.run_checks(task_dir, {"timeout_coherence"})

        sum_warnings = [w for w in reporter.warnings if "exceeds verifier" in w]
        self.assertEqual(sum_warnings, [])

    def test_environment_hidden_instructions_passes_on_realistic_environment_prose(self) -> None:
        """Realistic environment context — descriptive prose about how the
        system behaves, what the tests consume, what the public API does — must
        not trigger the hidden-instructions check. The shipped fixture
        environments are all in this style and must stay PASS."""
        with tempfile.TemporaryDirectory() as tmpdir:
            task_dir = self.copy_fixture("public-contract-standard", tmpdir)
            env_dir = task_dir / "environment"
            env_dir.mkdir(exist_ok=True)
            (env_dir / "README.md").write_text(
                "# Widget Service\n\n"
                "The widget service exposes an HTTP API for inspecting "
                "registered widgets. The user-agent header is forwarded to "
                "downstream callers. Diagnostic output is consumed by the "
                "verifier and should remain deterministic.\n",
                encoding="utf-8",
            )
            reporter = run_static_checks.run_checks(task_dir, {"environment_hidden_instructions"})

        self.assertEqual(reporter.failures, [], reporter.failures)
        self.assertIn(
            "environment/ contains no hidden-instruction patterns",
            reporter.passes,
        )

    def test_environment_hidden_instructions_fails_on_solver_directed_phrase(self) -> None:
        """A markdown file inside environment/ that contains explicit
        solver-direction phrasing ('Claude should call ...') must FAIL the
        new check. This is the canonical failure mode the upstream
        instruction-eval is trying to prevent."""
        with tempfile.TemporaryDirectory() as tmpdir:
            task_dir = self.copy_fixture("public-contract-standard", tmpdir)
            env_dir = task_dir / "environment"
            env_dir.mkdir(exist_ok=True)
            (env_dir / "NOTES.md").write_text(
                "# Implementation notes\n\n"
                "Claude should call `widget.recompute()` after every state "
                "transition; otherwise the cache becomes stale.\n",
                encoding="utf-8",
            )
            reporter = run_static_checks.run_checks(task_dir, {"environment_hidden_instructions"})

        hidden_failures = [
            failure for failure in reporter.failures
            if "hidden-instruction content" in failure
        ]
        self.assertEqual(len(hidden_failures), 1, reporter.failures)
        self.assertIn("environment/NOTES.md", hidden_failures[0])
        self.assertIn("solver-direction phrase", hidden_failures[0])

    def test_environment_hidden_instructions_fails_on_solution_reveal_phrase(self) -> None:
        """'The fix is to ...' / 'to solve this task ...' phrasing inside
        environment/ is a solution-reveal even when no AI brand name is named.
        These need to FAIL because they short-circuit the engineering
        challenge — the agent reads the answer instead of doing the work."""
        with tempfile.TemporaryDirectory() as tmpdir:
            task_dir = self.copy_fixture("public-contract-standard", tmpdir)
            env_dir = task_dir / "environment"
            env_dir.mkdir(exist_ok=True)
            # Plain Python file: only solver-direction patterns apply, prose
            # patterns (HINT/STEP) don't, but solution-reveal IS a solver-
            # direction pattern and must fire even in source-code comments.
            (env_dir / "core.py").write_text(
                "# The fix is to swap the lock acquisition order in `commit`.\n"
                "def commit():\n"
                "    pass\n",
                encoding="utf-8",
            )
            reporter = run_static_checks.run_checks(task_dir, {"environment_hidden_instructions"})

        hidden_failures = [
            failure for failure in reporter.failures
            if "hidden-instruction content" in failure
        ]
        self.assertEqual(len(hidden_failures), 1, reporter.failures)
        self.assertIn("environment/core.py", hidden_failures[0])

    def test_environment_hidden_instructions_fails_on_walkthrough_in_markdown(self) -> None:
        """Markdown files inside environment/ with `STEP 1:` / `HINT:` line
        lead-ins or the literal word `walkthrough` are walkthroughs by any
        reasonable definition; these are exactly what the upstream rule
        prohibits."""
        with tempfile.TemporaryDirectory() as tmpdir:
            task_dir = self.copy_fixture("public-contract-standard", tmpdir)
            env_dir = task_dir / "environment"
            env_dir.mkdir(exist_ok=True)
            (env_dir / "GUIDE.md").write_text(
                "# Step-by-step walkthrough\n\n"
                "STEP 1: open `core.py` and locate the `commit` function.\n"
                "STEP 2: change the lock acquisition order.\n"
                "STEP 3: rerun the tests.\n",
                encoding="utf-8",
            )
            reporter = run_static_checks.run_checks(task_dir, {"environment_hidden_instructions"})

        hidden_failures = [
            failure for failure in reporter.failures
            if "hidden-instruction content" in failure
        ]
        self.assertEqual(len(hidden_failures), 1, reporter.failures)
        self.assertIn("environment/GUIDE.md", hidden_failures[0])
        self.assertIn("prescriptive prose marker", hidden_failures[0])

    def test_environment_hidden_instructions_does_not_fire_on_todo_in_source_code(self) -> None:
        """Plain `# TODO: handle empty input` style comments inside source
        code are a normal idiom and must NOT trip the prose-only patterns.
        The prose patterns (HINT/STEP) are scoped to .md/.txt/.rst/.markdown
        files specifically because TODO/FIXME/HINT in comments are routine."""
        with tempfile.TemporaryDirectory() as tmpdir:
            task_dir = self.copy_fixture("public-contract-standard", tmpdir)
            env_dir = task_dir / "environment"
            env_dir.mkdir(exist_ok=True)
            (env_dir / "core.py").write_text(
                "# TODO: handle empty input gracefully\n"
                "# HINT: the iterator may yield None\n"
                "# STEP 1: this is a comment header for a unit, not a walkthrough\n"
                "def normalize(items):\n"
                "    return [item for item in items if item]\n",
                encoding="utf-8",
            )
            reporter = run_static_checks.run_checks(task_dir, {"environment_hidden_instructions"})

        self.assertEqual(reporter.failures, [], reporter.failures)

    def test_environment_hidden_instructions_does_not_fire_on_user_agent_or_software_agent(self) -> None:
        """The word 'agent' in production senses (user-agent, HTTP agent,
        software agent, agent registration) is intentionally not flagged.
        Banning it would create false positives across most realistic
        web-service tasks; the rule only bans solver-direction phrasing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            task_dir = self.copy_fixture("public-contract-standard", tmpdir)
            env_dir = task_dir / "environment"
            env_dir.mkdir(exist_ok=True)
            (env_dir / "transport.py").write_text(
                '"""HTTP transport layer.\n\n'
                "The user agent header is forwarded to downstream services.\n"
                "Each registered agent must implement the `dispatch()` protocol.\n"
                'The agent registry is keyed by agent ID.\n"""\n',
                encoding="utf-8",
            )
            reporter = run_static_checks.run_checks(task_dir, {"environment_hidden_instructions"})

        self.assertEqual(reporter.failures, [], reporter.failures)

    def test_environment_hidden_instructions_skipped_when_no_environment_dir(self) -> None:
        """Tasks without an environment/ directory (rare but legal during
        scaffolding) must produce a skip-style PASS, not a failure. The
        public-contract-standard fixture happens to ship without one, which
        exercises this path naturally."""
        with tempfile.TemporaryDirectory() as tmpdir:
            task_dir = self.copy_fixture("public-contract-standard", tmpdir)
            self.assertFalse((task_dir / "environment").exists())

            reporter = run_static_checks.run_checks(task_dir, {"environment_hidden_instructions"})

        self.assertEqual(reporter.failures, [])
        self.assertIn(
            "environment/ hidden-instruction check skipped (no environment/ directory)",
            reporter.passes,
        )


class DockerfileBestPracticesTest(unittest.TestCase):
    def test_scratch_from_is_digest_exempt(self) -> None:
        self.assertTrue(run_static_checks.docker_image_is_scratch("scratch"))
        self.assertTrue(run_static_checks.docker_image_is_sanctioned_runtime_base("scratch"))

    def test_canonical_runtime_base_digests(self) -> None:
        from scripts import canonical_base_images

        canonical = (
            "python:3.13-slim-bookworm@sha256:"
            "01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb"
        )
        self.assertTrue(canonical_base_images.docker_image_is_canonical_base(canonical))
        self.assertTrue(run_static_checks.docker_image_is_canonical_base(canonical))
        self.assertTrue(
            canonical_base_images.docker_image_is_canonical_base(
                "debian:bookworm-slim@sha256:4724b8cc51e33e398f0e2e15e18d5ec2851ff0c2280647e1310bc1642182655d"
            )
        )
        self.assertFalse(
            canonical_base_images.docker_image_is_canonical_base(
                "golang:1.22-bookworm@sha256:1f298b0c9fecdf504389a0329236f948cc04a566a2bb32337207cbaaa2f8177c"
            )
        )
        self.assertFalse(
            canonical_base_images.docker_image_is_canonical_base(
                "python:3.11-slim-bookworm@sha256:"
                "139020233cc412efe4c8135b0efe1c7569dcbc9051f1c8f68a3c3a9dd7f2ce67"
            )
        )

    def test_latest_tag_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            task_dir = Path(tmpdir) / "task"
            shutil.copytree(FIXTURE_TASKS_DIR / "byzantine-storage-rebalance", task_dir)
            dockerfile = task_dir / "environment" / "Dockerfile"
            dockerfile.write_text(
                dockerfile.read_text(encoding="utf-8").replace(
                    "golang:1.22-bookworm@sha256:",
                    "golang:latest@sha256:",
                ),
                encoding="utf-8",
            )
            reporter = run_static_checks.run_checks(task_dir, {"dockerfile"})

        self.assertTrue(
            any("must not use the :latest tag" in failure for failure in reporter.failures)
        )

    def test_missing_digest_fails_except_scratch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            task_dir = Path(tmpdir) / "task"
            shutil.copytree(FIXTURE_TASKS_DIR / "byzantine-storage-rebalance", task_dir)
            dockerfile = task_dir / "environment" / "Dockerfile"
            dockerfile.write_text(
                "FROM golang:1.22-bookworm\nWORKDIR /app\n",
                encoding="utf-8",
            )
            reporter = run_static_checks.run_checks(task_dir, {"dockerfile"})

        self.assertTrue(
            any("must be pinned by digest" in failure for failure in reporter.failures)
        )

    def test_unpinned_requirements_fail_without_lockfile(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            task_dir = Path(tmpdir) / "task"
            shutil.copytree(FIXTURE_TASKS_DIR / "byzantine-storage-rebalance", task_dir)
            (task_dir / "environment" / "requirements.txt").write_text(
                "requests\nflask>=2.0\n",
                encoding="utf-8",
            )
            reporter = run_static_checks.run_checks(task_dir, {"dockerfile"})

        self.assertTrue(
            any("requirements.txt must pin exact versions" in failure for failure in reporter.failures)
        )

    def test_cargo_lock_required_when_cargo_toml_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            task_dir = Path(tmpdir) / "task"
            shutil.copytree(FIXTURE_TASKS_DIR / "release-provenance-drift", task_dir)
            (task_dir / "environment" / "Cargo.lock").unlink()
            reporter = run_static_checks.run_checks(task_dir, {"dockerfile"})

        self.assertIn(
            "environment/Cargo.toml requires environment/Cargo.lock for reproducible Rust builds",
            reporter.failures,
        )
