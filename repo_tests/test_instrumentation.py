"""Regression tests for the per-task authoring instrumentation modules.

Spec: docs/exec-plans/instrumentation.md.

These tests exercise:

  * metrics_collector — JSONL counter writes (record_exit, record_marker)
    and aggregation (aggregate). Schema is {tool, outcome, timestamp_ns,
    run_id}; run_id falls back to "adhoc" when TB3_METRICS_RUN_ID is
    unset, and aggregate() reports "no Step 2b PASS yet" when
    t_first_step2b_pass_ns is absent.
  * validation_log — append_metrics_block atomicity and missing-spec
    graceful skip. (Filled in by unit 2.)
  * task_integrity — explicit EXCLUDED_DOTFILES exclusion. (Unit 3.)
  * validate_submission_zip — .step2b-metrics.jsonl FORBIDDEN_ROOT_FILES
    rejection. (Unit 4.)
  * scripts/check-task.sh — TB3_METRICS_RUN_ID export and wall-clock
    markers. (Unit 5.)
  * run_static_checks / collapse_check — env-gated FAIL/WARN hooks.
    (Units 6-7.)
  * approve_task — --emit-metrics flag, dirty-flag counter, final block
    emission. (Unit 8.)
  * End-to-end synthetic authoring loop. (Unit 9.)

Per the exec-plan's binding deferrals, this work unit:
  * Emits cni_references_fired = [] (no extraction).
  * Emits draft_commitments_diff = null (no parser).
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path
from unittest import mock

import zipfile

from scripts import approve_task
from scripts import collapse_check
from scripts import metrics_collector
from scripts import run_static_checks
from scripts import task_integrity
from scripts import validate_submission_zip
from scripts import validation_log
from repo_tests.cases import FIXTURE_TASKS_DIR


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "check-task.sh"


class _MetricsEnvCleaner(unittest.TestCase):
    """Mixin: clean TB3_METRICS_* env vars before each test, restore after."""

    _ENV_VARS = (
        metrics_collector.TASK_DIR_ENV,
        metrics_collector.RUN_ID_ENV,
    )

    def setUp(self) -> None:
        super().setUp()
        self._saved_env = {name: os.environ.get(name) for name in self._ENV_VARS}
        for name in self._ENV_VARS:
            os.environ.pop(name, None)
        self.addCleanup(self._restore_env)

    def _restore_env(self) -> None:
        for name, value in self._saved_env.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


class MetricsCollectorRecordExitTest(_MetricsEnvCleaner):
    def test_record_exit_writes_required_fields(self) -> None:
        """JSONL records must carry exactly {tool, outcome, timestamp_ns,
        run_id}. The schema is binding (exec-plan Change Surface, §
        scripts/metrics_collector.py)."""
        with tempfile.TemporaryDirectory() as tmp:
            task_dir = Path(tmp)
            os.environ[metrics_collector.TASK_DIR_ENV] = str(task_dir)
            os.environ[metrics_collector.RUN_ID_ENV] = "abcd1234"

            metrics_collector.record_exit("run_static_checks", "PASS")

            metrics_path = task_dir / metrics_collector.METRICS_FILE_NAME
            self.assertTrue(metrics_path.exists())
            lines = [
                line for line in metrics_path.read_text().splitlines() if line
            ]
            self.assertEqual(len(lines), 1)
            record = json.loads(lines[0])
            self.assertEqual(
                set(record.keys()),
                {"tool", "outcome", "timestamp_ns", "run_id"},
            )
            self.assertEqual(record["tool"], "run_static_checks")
            self.assertEqual(record["outcome"], "PASS")
            self.assertEqual(record["run_id"], "abcd1234")
            self.assertIsInstance(record["timestamp_ns"], int)
            self.assertGreater(record["timestamp_ns"], 0)

    def test_records_without_run_id_env_var_use_adhoc_sentinel(self) -> None:
        """Reviewer one-shot or CI smoke-test: TB3_METRICS_TASK_DIR is set
        but TB3_METRICS_RUN_ID is not — record run_id="adhoc".

        Pinned by exec-plan Tests §
        test_records_without_run_id_env_var_use_adhoc_sentinel.
        """
        with tempfile.TemporaryDirectory() as tmp:
            task_dir = Path(tmp)
            os.environ[metrics_collector.TASK_DIR_ENV] = str(task_dir)
            self.assertNotIn(metrics_collector.RUN_ID_ENV, os.environ)

            metrics_collector.record_exit("collapse_check", "PASS")

            metrics_path = task_dir / metrics_collector.METRICS_FILE_NAME
            record = json.loads(metrics_path.read_text().splitlines()[0])
            self.assertEqual(record["run_id"], metrics_collector.ADHOC_RUN_ID)
            self.assertEqual(record["run_id"], "adhoc")

    def test_record_exit_no_op_when_task_dir_env_unset(self) -> None:
        """Without TB3_METRICS_TASK_DIR, reviewer one-shot CLI invocations
        must not write counters anywhere — no leakage to CWD."""
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            old_cwd = os.getcwd()
            try:
                os.chdir(cwd)
                metrics_collector.record_exit("run_static_checks", "FAIL")
            finally:
                os.chdir(old_cwd)

            for path in cwd.rglob("*"):
                self.assertNotEqual(
                    path.name,
                    metrics_collector.METRICS_FILE_NAME,
                    f"counter file leaked to CWD: {path}",
                )

    def test_record_exit_appends_does_not_replace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            task_dir = Path(tmp)
            os.environ[metrics_collector.TASK_DIR_ENV] = str(task_dir)
            os.environ[metrics_collector.RUN_ID_ENV] = "run01"

            metrics_collector.record_exit("run_static_checks", "FAIL")
            metrics_collector.record_exit("run_static_checks", "PASS")

            metrics_path = task_dir / metrics_collector.METRICS_FILE_NAME
            lines = [
                line for line in metrics_path.read_text().splitlines() if line
            ]
            self.assertEqual(len(lines), 2)
            outcomes = [json.loads(line)["outcome"] for line in lines]
            self.assertEqual(outcomes, ["FAIL", "PASS"])

    def test_record_exit_accepts_str_task_dir(self) -> None:
        """Regression: callers may pass `task_dir` as a `str` (the
        idiomatic Python "accept str | Path" contract). Before the
        normalization fix, a str crashed at
        `target_dir.is_dir()` with `AttributeError: 'str' object
        has no attribute 'is_dir'`. Pin acceptance of both types so
        a real-world smoke test (`metrics_collector.record_exit(
        ..., task_dir=some_str)`) cannot regress."""
        with tempfile.TemporaryDirectory() as tmp:
            os.environ[metrics_collector.RUN_ID_ENV] = "str-input"

            metrics_collector.record_exit(
                "run_static_checks", "PASS", task_dir=tmp
            )

            metrics_path = (
                Path(tmp) / metrics_collector.METRICS_FILE_NAME
            )
            self.assertTrue(metrics_path.exists())
            record = json.loads(metrics_path.read_text().splitlines()[0])
            self.assertEqual(record["tool"], "run_static_checks")
            self.assertEqual(record["outcome"], "PASS")
            self.assertEqual(record["run_id"], "str-input")

    def test_concurrent_appends_do_not_corrupt_jsonl(self) -> None:
        """Two-plus subprocesses calling record_exit in a tight loop must
        produce a file that parses as valid JSONL with every record
        present. POSIX O_APPEND is atomic for writes < PIPE_BUF; each
        record line is well under 200 bytes.

        Pinned by exec-plan Tests §
        test_concurrent_appends_do_not_corrupt_jsonl.
        """
        with tempfile.TemporaryDirectory() as tmp:
            task_dir = Path(tmp)
            env = os.environ.copy()
            env[metrics_collector.TASK_DIR_ENV] = str(task_dir)
            env[metrics_collector.RUN_ID_ENV] = "race"

            n_per_proc = 50
            runner = (
                f"import sys; sys.path.insert(0, {str(REPO_ROOT)!r}); "
                f"from scripts import metrics_collector; "
                f"[metrics_collector.record_exit('tool_'+sys.argv[1], 'PASS_'+str(i)) "
                f"for i in range({n_per_proc})]"
            )

            labels = ("a", "b", "c", "d")
            procs = [
                subprocess.Popen(
                    [sys.executable, "-c", runner, label],
                    env=env,
                )
                for label in labels
            ]
            for proc in procs:
                self.assertEqual(proc.wait(), 0)

            metrics_path = task_dir / metrics_collector.METRICS_FILE_NAME
            lines = [
                line for line in metrics_path.read_text().splitlines() if line
            ]
            self.assertEqual(len(lines), len(labels) * n_per_proc)
            for line in lines:
                record = json.loads(line)
                self.assertEqual(
                    set(record.keys()),
                    {"tool", "outcome", "timestamp_ns", "run_id"},
                )


class MetricsCollectorMarkerTest(_MetricsEnvCleaner):
    def test_record_marker_writes_marker_record(self) -> None:
        """Wall-clock markers ride the same JSONL schema, surfaced as
        tool='marker' with the marker name in the outcome field."""
        with tempfile.TemporaryDirectory() as tmp:
            task_dir = Path(tmp)
            os.environ[metrics_collector.TASK_DIR_ENV] = str(task_dir)
            os.environ[metrics_collector.RUN_ID_ENV] = "loop"

            metrics_collector.record_marker(
                metrics_collector.MARKER_FIRST_INVOCATION
            )

            metrics_path = task_dir / metrics_collector.METRICS_FILE_NAME
            record = json.loads(metrics_path.read_text().splitlines()[0])
            self.assertEqual(record["tool"], metrics_collector.MARKER_TOOL)
            self.assertEqual(
                record["outcome"],
                metrics_collector.MARKER_FIRST_INVOCATION,
            )
            self.assertEqual(record["run_id"], "loop")
            self.assertIsInstance(record["timestamp_ns"], int)

    def test_record_marker_accepts_str_task_dir(self) -> None:
        """Regression: callers may pass `task_dir` as a `str`. Before
        the normalization fix, record_marker delegated through
        record_exit, which crashed at `target_dir.is_dir()` for str
        inputs. Pin acceptance of both types."""
        with tempfile.TemporaryDirectory() as tmp:
            os.environ[metrics_collector.RUN_ID_ENV] = "str-marker"

            metrics_collector.record_marker(
                metrics_collector.MARKER_FIRST_PASS, task_dir=tmp
            )

            metrics_path = (
                Path(tmp) / metrics_collector.METRICS_FILE_NAME
            )
            self.assertTrue(metrics_path.exists())
            record = json.loads(metrics_path.read_text().splitlines()[0])
            self.assertEqual(record["tool"], metrics_collector.MARKER_TOOL)
            self.assertEqual(
                record["outcome"], metrics_collector.MARKER_FIRST_PASS
            )
            self.assertEqual(record["run_id"], "str-marker")


class MetricsCollectorAggregateTest(_MetricsEnvCleaner):
    def test_aggregate_groups_records_by_run_id(self) -> None:
        """Aggregation must group events by run_id so successive authoring
        loops over the same task dir remain distinguishable. (Exec-plan
        Change Surface § scripts/metrics_collector.py.)"""
        with tempfile.TemporaryDirectory() as tmp:
            task_dir = Path(tmp)
            os.environ[metrics_collector.TASK_DIR_ENV] = str(task_dir)

            os.environ[metrics_collector.RUN_ID_ENV] = "loop1"
            metrics_collector.record_exit("run_static_checks", "FAIL")
            metrics_collector.record_exit("run_static_checks", "PASS")

            os.environ[metrics_collector.RUN_ID_ENV] = "loop2"
            metrics_collector.record_exit("run_static_checks", "PASS")

            payload = metrics_collector.aggregate(task_dir)
            self.assertIn("loop1", payload["runs"])
            self.assertIn("loop2", payload["runs"])
            self.assertEqual(payload["run_static_checks_fail"], 1)

    def test_aggregate_reports_no_pass_when_second_marker_absent(self) -> None:
        """Phase C never green during the captured window:
        t_first_step2b_pass_ns is never written. aggregate() must surface
        the literal "no Step 2b PASS yet" sentinel rather than crashing
        or emitting 0.

        Pinned by exec-plan Tests §
        test_aggregate_reports_no_pass_when_second_marker_absent.
        """
        with tempfile.TemporaryDirectory() as tmp:
            task_dir = Path(tmp)
            os.environ[metrics_collector.TASK_DIR_ENV] = str(task_dir)
            os.environ[metrics_collector.RUN_ID_ENV] = "fail-forever"

            metrics_collector.record_marker(
                metrics_collector.MARKER_FIRST_INVOCATION
            )

            payload = metrics_collector.aggregate(task_dir)
            duration = payload["wall_clock_first_preflight_to_first_pass_ns"]
            self.assertEqual(duration, metrics_collector.NO_PASS_SENTINEL)
            self.assertEqual(duration, "no Step 2b PASS yet")
            self.assertNotEqual(duration, 0)

    def test_aggregate_returns_duration_when_both_markers_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            task_dir = Path(tmp)
            os.environ[metrics_collector.TASK_DIR_ENV] = str(task_dir)
            os.environ[metrics_collector.RUN_ID_ENV] = "complete"

            metrics_collector.record_marker(
                metrics_collector.MARKER_FIRST_INVOCATION,
                timestamp_ns=1_000_000_000,
            )
            metrics_collector.record_marker(
                metrics_collector.MARKER_FIRST_PASS,
                timestamp_ns=4_000_000_000,
            )

            payload = metrics_collector.aggregate(task_dir)
            self.assertEqual(
                payload["wall_clock_first_preflight_to_first_pass_ns"],
                3_000_000_000,
            )

    def test_aggregate_handles_empty_metrics_file(self) -> None:
        """No counter file means a fresh task dir; aggregate must not
        crash and must still emit the deferred-field sentinels."""
        with tempfile.TemporaryDirectory() as tmp:
            task_dir = Path(tmp)
            payload = metrics_collector.aggregate(task_dir)
            self.assertEqual(payload["run_static_checks_fail"], 0)
            self.assertEqual(payload["run_static_checks_warn"], 0)
            self.assertEqual(payload["collapse_check_fail"], 0)
            self.assertEqual(payload["dirty_flag"], 0)
            self.assertEqual(
                payload["wall_clock_first_preflight_to_first_pass_ns"],
                metrics_collector.NO_PASS_SENTINEL,
            )

    def test_aggregate_accepts_str_task_dir(self) -> None:
        """Regression: callers may pass `task_dir` as a `str` (e.g. a
        shell smoke test:
        `python3 -c 'from scripts import metrics_collector;
        print(metrics_collector.aggregate("tasks/<name>"))'`).
        Before the normalization fix, this crashed at
        `target = task_dir / METRICS_FILE_NAME` with
        `TypeError: unsupported operand type(s) for /: 'str' and 'str'`.
        Pin acceptance of both types — the empty-task-dir path
        already returns a well-formed sentinel dict, so str input
        must produce the same result Path input would."""
        with tempfile.TemporaryDirectory() as tmp:
            payload = metrics_collector.aggregate(tmp)

            self.assertEqual(payload["task_dir"], str(Path(tmp)))
            self.assertEqual(payload["run_static_checks_fail"], 0)
            self.assertEqual(
                payload["wall_clock_first_preflight_to_first_pass_ns"],
                metrics_collector.NO_PASS_SENTINEL,
            )

    def test_aggregate_str_and_path_produce_equivalent_payload(
        self,
    ) -> None:
        """Stronger pin: passing the same task dir as `str` vs `Path`
        must yield byte-identical aggregation output. This prevents a
        future "accept str but normalize lossy" regression (e.g. a
        normalize step that drops a trailing slash and changes the
        echoed `task_dir` string in the payload)."""
        with tempfile.TemporaryDirectory() as tmp:
            os.environ[metrics_collector.TASK_DIR_ENV] = tmp
            os.environ[metrics_collector.RUN_ID_ENV] = "loop"
            metrics_collector.record_exit("run_static_checks", "PASS")
            metrics_collector.record_marker(
                metrics_collector.MARKER_FIRST_INVOCATION,
                timestamp_ns=1_000_000_000,
            )
            metrics_collector.record_marker(
                metrics_collector.MARKER_FIRST_PASS,
                timestamp_ns=2_000_000_000,
            )

            via_str = metrics_collector.aggregate(tmp)
            via_path = metrics_collector.aggregate(Path(tmp))
            self.assertEqual(via_str, via_path)

    def test_aggregate_yields_deferred_fields_per_exec_plan(self) -> None:
        """Binding deferrals: cni_references_fired = [] and
        draft_commitments_diff = null in every aggregate(). This unit
        must not invent or extract them."""
        with tempfile.TemporaryDirectory() as tmp:
            task_dir = Path(tmp)
            payload = metrics_collector.aggregate(task_dir)
            self.assertEqual(payload["cni_references_fired"], [])
            self.assertIsNone(payload["draft_commitments_diff"])

    def test_aggregate_counts_each_tool_outcome_correctly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            task_dir = Path(tmp)
            os.environ[metrics_collector.TASK_DIR_ENV] = str(task_dir)
            os.environ[metrics_collector.RUN_ID_ENV] = "counts"

            metrics_collector.record_exit("run_static_checks", "FAIL")
            metrics_collector.record_exit("run_static_checks", "FAIL")
            metrics_collector.record_exit("run_static_checks", "WARN")
            metrics_collector.record_exit("run_static_checks", "PASS")
            metrics_collector.record_exit("collapse_check", "FAIL")
            metrics_collector.record_exit("collapse_check", "PASS")
            metrics_collector.record_exit("approve_task", "dirty_flag")
            metrics_collector.record_exit("approve_task", "dirty_flag")

            payload = metrics_collector.aggregate(task_dir)
            self.assertEqual(payload["run_static_checks_fail"], 2)
            self.assertEqual(payload["run_static_checks_warn"], 1)
            self.assertEqual(payload["collapse_check_fail"], 1)
            self.assertEqual(payload["dirty_flag"], 2)


class ValidationLogAppendTest(unittest.TestCase):
    """append_metrics_block(spec_path, block_text) — exec-plan §
    scripts/validation_log.py. Reads current `<task-name>-validation-log.md`,
    appends the rendered block, writes atomically (tmp + rename).
    Skips with a stderr note when the spec markdown is missing.
    """

    def _setup_specs_dir(
        self, tmp_root: Path, task_name: str = "foo"
    ) -> tuple[Path, Path]:
        specs_dir = tmp_root / "specs"
        specs_dir.mkdir()
        spec_path = specs_dir / f"{task_name}.md"
        log_path = specs_dir / f"{task_name}-validation-log.md"
        return spec_path, log_path

    def test_append_creates_log_when_absent(self) -> None:
        """No prior validation log; the helper creates it with the
        rendered block."""
        with tempfile.TemporaryDirectory() as tmp:
            spec_path, log_path = self._setup_specs_dir(Path(tmp))
            spec_path.write_text("# Foo spec\n", encoding="utf-8")

            block = "## Per-task authoring metrics\n- count: 0\n"
            result = validation_log.append_metrics_block(spec_path, block)

            self.assertTrue(result)
            self.assertTrue(log_path.exists())
            content = log_path.read_text(encoding="utf-8")
            self.assertIn("## Per-task authoring metrics", content)
            self.assertIn("- count: 0", content)

    def test_append_does_not_replace_existing_log(self) -> None:
        """Append, not replace: prior log content must survive verbatim
        and the new block must follow it."""
        with tempfile.TemporaryDirectory() as tmp:
            spec_path, log_path = self._setup_specs_dir(Path(tmp))
            spec_path.write_text("# Foo spec\n", encoding="utf-8")
            prior = "# Validation log\n\n## Attempt 1\n- prior entry\n"
            log_path.write_text(prior, encoding="utf-8")

            block = "## Per-task authoring metrics\n- count: 0\n"
            result = validation_log.append_metrics_block(spec_path, block)

            self.assertTrue(result)
            content = log_path.read_text(encoding="utf-8")
            self.assertIn("## Attempt 1", content)
            self.assertIn("- prior entry", content)
            self.assertIn("## Per-task authoring metrics", content)
            self.assertLess(
                content.index("Attempt 1"),
                content.index("Per-task authoring metrics"),
            )

    def test_metrics_block_skipped_when_spec_missing(self) -> None:
        """Grandfathered task with no specs/<task-name>.md: helper must
        return False, log a stderr note, and not create the log file.

        Pinned by exec-plan Tests § test_metrics_block_skipped_when_spec_missing
        (the skip-helper half; the approve_task end-to-end half lands
        in unit 8).
        """
        with tempfile.TemporaryDirectory() as tmp:
            spec_path, log_path = self._setup_specs_dir(Path(tmp))

            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                result = validation_log.append_metrics_block(
                    spec_path, "## Per-task authoring metrics\n"
                )

            self.assertFalse(result)
            self.assertFalse(log_path.exists())
            err = stderr.getvalue()
            self.assertIn("validation_log", err)
            self.assertIn(spec_path.name, err)

    def test_append_uses_tmp_then_rename(self) -> None:
        """Atomicity contract: the helper writes a tmp file in the same
        directory as the log and renames it into place. os.replace must
        be called exactly once with the tmp path as src and the log path
        as dst."""
        with tempfile.TemporaryDirectory() as tmp:
            spec_path, log_path = self._setup_specs_dir(Path(tmp))
            spec_path.write_text("# Foo spec\n", encoding="utf-8")

            calls: list[tuple[str, str]] = []
            real_replace = os.replace

            def tracking_replace(src, dst, *a, **kw):
                calls.append((str(src), str(dst)))
                return real_replace(src, dst, *a, **kw)

            with mock.patch.object(os, "replace", side_effect=tracking_replace):
                validation_log.append_metrics_block(
                    spec_path, "## Block\n"
                )

            self.assertEqual(len(calls), 1, calls)
            src, dst = calls[0]
            self.assertEqual(dst, str(log_path))
            self.assertNotEqual(src, str(log_path))
            self.assertEqual(Path(src).parent, log_path.parent)

    def test_append_does_not_leave_tmp_artifact_on_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            spec_path, log_path = self._setup_specs_dir(Path(tmp))
            spec_path.write_text("# Foo spec\n", encoding="utf-8")

            validation_log.append_metrics_block(spec_path, "## Block\n")

            stragglers = sorted(
                p.name
                for p in log_path.parent.iterdir()
                if p.name not in {spec_path.name, log_path.name}
            )
            self.assertEqual(stragglers, [])

    def test_append_preserves_prior_log_when_replace_fails(self) -> None:
        """If os.replace raises (cross-filesystem rename, permission
        error, etc.), the prior log content must remain intact and the
        helper must surface the failure rather than silently dropping
        the block. Either the fcntl fallback succeeds (log gets the new
        block + prior content preserved) or the helper raises and the
        prior log is unchanged."""
        with tempfile.TemporaryDirectory() as tmp:
            spec_path, log_path = self._setup_specs_dir(Path(tmp))
            spec_path.write_text("# Foo spec\n", encoding="utf-8")
            prior = "# Validation log\n\n## Attempt 1\n- prior entry\n"
            log_path.write_text(prior, encoding="utf-8")

            with mock.patch.object(
                os,
                "replace",
                side_effect=OSError(18, "Invalid cross-device link"),
            ):
                try:
                    validation_log.append_metrics_block(
                        spec_path, "## Block\n"
                    )
                except OSError:
                    pass

            content = log_path.read_text(encoding="utf-8")
            self.assertIn("## Attempt 1", content)
            self.assertIn("- prior entry", content)


class TaskIntegrityExcludedDotfilesTest(unittest.TestCase):
    """`scripts/task_integrity.py` must expose an explicit EXCLUDED_DOTFILES
    constant naming the two harness-local dotfiles, and exclude them
    *in addition* to the generic dotfile rule. Defense-in-depth: if a
    future refactor narrows or removes the generic dotfile rule, the
    explicit names remain excluded from the checksum manifest."""

    def test_excluded_dotfiles_constant_pinned(self) -> None:
        """The named tuple is part of the module's contract; pin it so
        a future drift surfaces as a test failure rather than as a
        silent change in manifest behavior."""
        self.assertEqual(
            task_integrity.EXCLUDED_DOTFILES,
            (".step2b-checksum", ".step2b-metrics.jsonl"),
        )

    def test_task_integrity_excludes_step2b_dotfiles_explicitly(
        self,
    ) -> None:
        """Pin the explicit EXCLUDED_DOTFILES exclusion: even when the
        generic dotfile rule is monkeypatched to a no-op, the named
        files must still be excluded from the manifest. Real task
        files (instruction.md, task.toml, etc.) remain tracked.

        Pinned by exec-plan Tests §
        test_task_integrity_excludes_step2b_dotfiles_explicitly.
        """
        with tempfile.TemporaryDirectory() as tmp:
            task_dir = Path(tmp)
            (task_dir / "instruction.md").write_text("body\n")
            (task_dir / "task.toml").write_text('artifacts = ["/app/output.txt"]\n')
            (task_dir / ".step2b-checksum").write_text("{}\n")
            (task_dir / ".step2b-metrics.jsonl").write_text(
                '{"tool":"run_static_checks","outcome":"PASS",'
                '"timestamp_ns":1,"run_id":"x"}\n'
            )

            with mock.patch.object(
                task_integrity,
                "_is_dotfile_part",
                return_value=False,
            ):
                tracked = task_integrity.iter_task_files(task_dir)

            tracked_names = {p.name for p in tracked}
            self.assertNotIn(".step2b-checksum", tracked_names)
            self.assertNotIn(".step2b-metrics.jsonl", tracked_names)
            self.assertIn("instruction.md", tracked_names)
            self.assertIn("task.toml", tracked_names)

    def test_metrics_jsonl_excluded_from_manifest_normally(self) -> None:
        """Belt-and-suspenders: the named files are also excluded by the
        generic dotfile rule — the manifest must not contain them in the
        normal (un-patched) case."""
        with tempfile.TemporaryDirectory() as tmp:
            task_dir = Path(tmp)
            (task_dir / "instruction.md").write_text("body\n")
            (task_dir / "task.toml").write_text('artifacts = ["/app/output.txt"]\n')
            (task_dir / ".step2b-metrics.jsonl").write_text(
                '{"tool":"x","outcome":"y","timestamp_ns":1,"run_id":"r"}\n'
            )

            sentinel = task_integrity.write_step2b_checksum(task_dir)
            manifest = json.loads(sentinel.read_text())

            self.assertNotIn(".step2b-metrics.jsonl", manifest)
            self.assertNotIn(".step2b-checksum", manifest)
            self.assertIn("instruction.md", manifest)
            self.assertIn("task.toml", manifest)


def _build_minimal_zip_bytes(extra_members: dict[str, bytes]) -> bytes:
    """Build an in-memory zip that satisfies validate_submission_zip's
    required-files contract, plus any extra members the test wants to
    inject. Mirrors `_build_minimal_zip` in test_validate_submission_zip."""
    base_members = {
        "instruction.md": b"Repair the imaginary widget.\n",
        "task.toml": b'artifacts = ["/app/output.txt"]\nname = "widget"\n',
        "environment/Dockerfile": b"FROM scratch\n",
        "solution/solve.sh": b"#!/usr/bin/env bash\n",
        "tests/Dockerfile": b"FROM scratch\nCOPY . /tests/\n",
        "tests/test.sh": b"#!/usr/bin/env bash\n",
        "tests/test_outputs.py": b"def test_widget():\n    assert True\n",
    }
    base_members.update(extra_members)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, payload in base_members.items():
            archive.writestr(name, payload)
    return buffer.getvalue()


class ValidateSubmissionZipMetricsFileTest(unittest.TestCase):
    """`.step2b-metrics.jsonl` must be rejected at the archive root by
    scripts/validate_submission_zip.py — same defense-in-depth pattern as
    `.step2b-checksum`. The generic dotfile filter already keeps it out
    of the source manifest at packaging time, but listing the name in
    FORBIDDEN_ROOT_FILES makes the rejection explicit and survives any
    future change to the implicit filter."""

    def test_metrics_file_in_forbidden_root_files_constant(self) -> None:
        """Pin the constant entry so a future drift surfaces as a test
        failure, not as a silent change in packaging behavior."""
        self.assertIn(
            ".step2b-metrics.jsonl",
            validate_submission_zip.FORBIDDEN_ROOT_FILES,
        )

    def test_metrics_file_at_archive_root_is_rejected(self) -> None:
        """Mirror of test_step2b_checksum_at_archive_root_is_rejected:
        a fixture archive with `.step2b-metrics.jsonl` at the root must
        be rejected with a forbidden-root-file failure that names the
        offending file.

        Pinned by exec-plan Tests §
        test_metrics_file_at_archive_root_is_rejected.
        """
        payload_bytes = _build_minimal_zip_bytes(
            {
                ".step2b-metrics.jsonl": (
                    b'{"tool":"run_static_checks","outcome":"PASS",'
                    b'"timestamp_ns":1,"run_id":"abc"}\n'
                )
            }
        )
        with tempfile.TemporaryDirectory() as tmp:
            zip_path = Path(tmp) / "fixture.zip"
            zip_path.write_bytes(payload_bytes)
            payload = validate_submission_zip.build_report(zip_path)

        self.assertFalse(payload["valid"], payload)
        self.assertIn(
            "forbidden archive-root file(s) present: .step2b-metrics.jsonl",
            payload["failures"],
        )


def _seed_min_task(task_dir: Path) -> None:
    """Minimum task tree that satisfies validate_submission_zip on the
    Phase B tmp zip. Mirrors the helper in test_check_task_sh.py."""
    files = {
        "instruction.md": "Test task body.\n",
        "task.toml": 'artifacts = ["/app/output.txt"]\nname = "min-task"\n',
        "environment/Dockerfile": "FROM scratch\n",
        "solution/solve.sh": "#!/usr/bin/env bash\nexit 0\n",
        "tests/Dockerfile": "FROM scratch\nCOPY . /tests/\n",
        "tests/test.sh": "#!/usr/bin/env bash\n",
        "tests/test_outputs.py": "def test_min():\n    assert True\n",
    }
    for rel, content in files.items():
        target = task_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)


class CheckTaskShInstrumentationTest(unittest.TestCase):
    """Regression tests for the instrumentation half of
    scripts/check-task.sh: per-invocation TB3_METRICS_RUN_ID export,
    `t_first_check_task_invocation_ns` marker on first Phase A entry,
    and `t_first_step2b_pass_ns` marker on Phase C completion. Phase A
    tools are stubbed; Phase B + Phase C use the real repo modules.
    """

    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="check-task-instr-test-"))
        self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)

        scripts_dir = self.tmpdir / "scripts"
        scripts_dir.mkdir()

        for stub in (
            "scripts/run_static_checks.py",
            "scripts/collapse_check.py",
            "scripts/task_runtime_deps.py",
        ):
            (self.tmpdir / stub).write_text("import sys\nsys.exit(0)\n")

        for real in (
            "scripts/validate_submission_zip.py",
            "scripts/task_integrity.py",
            "scripts/metrics_collector.py",
        ):
            shutil.copy(REPO_ROOT / real, self.tmpdir / real)

        self.script_local = scripts_dir / "check-task.sh"
        shutil.copy(SCRIPT_PATH, self.script_local)
        self.script_local.chmod(0o755)

        self.task_dir = self.tmpdir / "tasks" / "synth"
        self.task_dir.mkdir(parents=True)
        _seed_min_task(self.task_dir)

    def _run(
        self,
        task_path: str = "tasks/synth",
        env_extra: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        for var in (
            metrics_collector.TASK_DIR_ENV,
            metrics_collector.RUN_ID_ENV,
        ):
            env.pop(var, None)
        if env_extra:
            env.update(env_extra)
        return subprocess.run(
            ["bash", "scripts/check-task.sh", task_path],
            cwd=str(self.tmpdir),
            capture_output=True,
            text=True,
            env=env,
        )

    def _read_metrics(self) -> list[dict[str, object]]:
        path = self.task_dir / metrics_collector.METRICS_FILE_NAME
        if not path.exists():
            return []
        return [
            json.loads(line)
            for line in path.read_text().splitlines()
            if line.strip()
        ]

    def test_check_task_sh_writes_first_invocation_marker(self) -> None:
        """First Phase A entry must produce a
        `t_first_check_task_invocation_ns` marker in
        .step2b-metrics.jsonl with a valid run_id (not 'adhoc')."""
        result = self._run()
        self.assertEqual(result.returncode, 0, result.stderr)

        records = self._read_metrics()
        first_invocation = [
            r
            for r in records
            if r.get("tool") == metrics_collector.MARKER_TOOL
            and r.get("outcome") == metrics_collector.MARKER_FIRST_INVOCATION
        ]
        self.assertEqual(len(first_invocation), 1, records)
        self.assertNotEqual(
            first_invocation[0]["run_id"],
            metrics_collector.ADHOC_RUN_ID,
            "check-task.sh must export a real run_id, not 'adhoc'",
        )
        self.assertIsInstance(first_invocation[0]["timestamp_ns"], int)
        self.assertGreater(first_invocation[0]["timestamp_ns"], 0)

    def test_wall_clock_markers_populate(self) -> None:
        """End-to-end synthetic run: assert
        `t_first_check_task_invocation_ns` and `t_first_step2b_pass_ns`
        are both present in the counter file and the former is ≤ the
        latter.

        Pinned by exec-plan Tests § test_wall_clock_markers_populate.
        """
        result = self._run()
        self.assertEqual(result.returncode, 0, result.stderr)

        records = self._read_metrics()
        marker_records = {
            r["outcome"]: r
            for r in records
            if r.get("tool") == metrics_collector.MARKER_TOOL
        }
        self.assertIn(
            metrics_collector.MARKER_FIRST_INVOCATION, marker_records
        )
        self.assertIn(metrics_collector.MARKER_FIRST_PASS, marker_records)
        self.assertLessEqual(
            marker_records[metrics_collector.MARKER_FIRST_INVOCATION][
                "timestamp_ns"
            ],
            marker_records[metrics_collector.MARKER_FIRST_PASS][
                "timestamp_ns"
            ],
        )
        self.assertEqual(
            marker_records[metrics_collector.MARKER_FIRST_INVOCATION][
                "run_id"
            ],
            marker_records[metrics_collector.MARKER_FIRST_PASS]["run_id"],
            "both markers in the same invocation must share a run_id",
        )

    def test_pass_marker_absent_when_phase_a_fails(self) -> None:
        """If Phase A FAILs, `t_first_step2b_pass_ns` must not be
        written. Demotion review's missing-second-marker case
        (`aggregate()` returns NO_PASS_SENTINEL) depends on this
        invariant — see exec-plan Change Surface § scripts/metrics_collector.py
        and Tests § test_aggregate_reports_no_pass_when_second_marker_absent.
        """
        (self.tmpdir / "scripts/run_static_checks.py").write_text(
            "import sys\nsys.exit(1)\n"
        )

        result = self._run()
        self.assertNotEqual(result.returncode, 0)

        records = self._read_metrics()
        marker_outcomes = [
            r["outcome"]
            for r in records
            if r.get("tool") == metrics_collector.MARKER_TOOL
        ]
        self.assertIn(
            metrics_collector.MARKER_FIRST_INVOCATION, marker_outcomes
        )
        self.assertNotIn(
            metrics_collector.MARKER_FIRST_PASS, marker_outcomes
        )

    def test_run_id_changes_between_invocations(self) -> None:
        """Two consecutive invocations must produce different run_ids
        so aggregate() can group events into separate authoring loops."""
        first = self._run()
        self.assertEqual(first.returncode, 0, first.stderr)
        run_ids_after_first = sorted(
            {
                r["run_id"]
                for r in self._read_metrics()
                if r.get("tool") == metrics_collector.MARKER_TOOL
            }
        )
        self.assertEqual(len(run_ids_after_first), 1)

        second = self._run()
        self.assertEqual(second.returncode, 0, second.stderr)
        run_ids_after_second = sorted(
            {
                r["run_id"]
                for r in self._read_metrics()
                if r.get("tool") == metrics_collector.MARKER_TOOL
            }
        )
        self.assertEqual(len(run_ids_after_second), 2, run_ids_after_second)

    def test_run_id_env_var_visible_to_phase_a_tools(self) -> None:
        """check-task.sh must export TB3_METRICS_RUN_ID for the duration
        of its run; Phase A tools (and any subprocess they spawn) must
        see it. Stub scripts/run_static_checks.py to write the env var to a
        sentinel file and assert non-empty."""
        sentinel = self.tmpdir / "rsc_env.txt"
        (self.tmpdir / "scripts/run_static_checks.py").write_text(
            "import os, sys\n"
            f"open({str(sentinel)!r}, 'w').write("
            "'task_dir='+(os.environ.get('TB3_METRICS_TASK_DIR') or '')+'\\n'+"
            "'run_id='+(os.environ.get('TB3_METRICS_RUN_ID') or '')+'\\n')\n"
            "sys.exit(0)\n"
        )

        result = self._run()
        self.assertEqual(result.returncode, 0, result.stderr)

        captured = sentinel.read_text()
        self.assertIn("task_dir=tasks/synth", captured)
        run_id_line = [
            line for line in captured.splitlines() if line.startswith("run_id=")
        ]
        self.assertEqual(len(run_id_line), 1)
        run_id_value = run_id_line[0].split("=", 1)[1]
        self.assertNotEqual(run_id_value, "")
        self.assertNotEqual(run_id_value, metrics_collector.ADHOC_RUN_ID)


def _read_metrics(task_dir: Path) -> list[dict]:
    """Helper used by the per-tool hook tests."""
    path = task_dir / metrics_collector.METRICS_FILE_NAME
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text().splitlines()
        if line.strip()
    ]


def _make_reporter(*, failures=0, warnings=0, passes=1) -> "run_static_checks.Reporter":
    """Build a Reporter in a controlled state for hook-outcome tests.

    The hook reads `reporter.has_failures()` / `reporter.warnings` to
    derive FAIL/WARN/PASS; mocking the reporter directly isolates the
    hook test from fixture brittleness (several baseline fixtures have
    pre-existing static-check failures, so we can't rely on a "clean"
    fixture for the PASS path).
    """
    reporter = run_static_checks.Reporter()
    for i in range(passes):
        reporter.ok(f"synthetic pass message {i}")
    for i in range(warnings):
        reporter.warn(f"synthetic warning {i}")
    for i in range(failures):
        reporter.fail(f"synthetic failure {i}")
    return reporter


class RunStaticChecksHookTest(_MetricsEnvCleaner):
    """Env-gated FAIL/WARN/PASS hook in scripts/run_static_checks.py.

    The hook is a try/finally wrapper in main() that records the
    check outcome to .step2b-metrics.jsonl when TB3_METRICS_TASK_DIR
    is set; otherwise it's a no-op so reviewer one-shots and CI
    spot-checks don't accidentally pollute a counter file.

    Tests mock `run_static_checks.run_checks` so the outcome is
    derived from a controlled Reporter rather than from any specific
    fixture's pinned static-check state.
    """

    def _invoke_main_with_reporter(
        self, task_dir: Path, reporter
    ) -> int:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            with mock.patch.object(
                run_static_checks, "run_checks", return_value=reporter
            ):
                return run_static_checks.main(
                    [
                        "--task-dir",
                        str(task_dir),
                        "--version",
                        "terminus_3",
                    ]
                )

    def test_records_pass_outcome(self) -> None:
        """Reporter with no failures and no warnings → outcome=PASS,
        exit code 0."""
        with tempfile.TemporaryDirectory() as tmp:
            task_dir = Path(tmp)
            os.environ[metrics_collector.TASK_DIR_ENV] = str(task_dir)
            os.environ[metrics_collector.RUN_ID_ENV] = "pass-loop"

            exit_code = self._invoke_main_with_reporter(
                task_dir, _make_reporter()
            )
            self.assertEqual(exit_code, 0)

            tool_records = [
                r
                for r in _read_metrics(task_dir)
                if r.get("tool") == "run_static_checks"
            ]
            self.assertEqual(len(tool_records), 1)
            self.assertEqual(tool_records[0]["outcome"], "PASS")
            self.assertEqual(tool_records[0]["run_id"], "pass-loop")

    def test_records_warn_outcome(self) -> None:
        """Reporter with warnings but no failures → outcome=WARN, exit
        code still 0 (WARN is informational; only failures fail the
        CLI)."""
        with tempfile.TemporaryDirectory() as tmp:
            task_dir = Path(tmp)
            os.environ[metrics_collector.TASK_DIR_ENV] = str(task_dir)
            os.environ[metrics_collector.RUN_ID_ENV] = "warn-loop"

            exit_code = self._invoke_main_with_reporter(
                task_dir, _make_reporter(warnings=2)
            )
            self.assertEqual(exit_code, 0)

            tool_records = [
                r
                for r in _read_metrics(task_dir)
                if r.get("tool") == "run_static_checks"
            ]
            self.assertEqual(len(tool_records), 1)
            self.assertEqual(tool_records[0]["outcome"], "WARN")
            self.assertEqual(tool_records[0]["run_id"], "warn-loop")

    def test_records_fail_outcome(self) -> None:
        """Reporter with failures (regardless of warnings) →
        outcome=FAIL, exit code 1."""
        with tempfile.TemporaryDirectory() as tmp:
            task_dir = Path(tmp)
            os.environ[metrics_collector.TASK_DIR_ENV] = str(task_dir)
            os.environ[metrics_collector.RUN_ID_ENV] = "fail-loop"

            exit_code = self._invoke_main_with_reporter(
                task_dir, _make_reporter(failures=1, warnings=1)
            )
            self.assertEqual(exit_code, 1)

            tool_records = [
                r
                for r in _read_metrics(task_dir)
                if r.get("tool") == "run_static_checks"
            ]
            self.assertEqual(len(tool_records), 1)
            self.assertEqual(tool_records[0]["outcome"], "FAIL")
            self.assertEqual(tool_records[0]["run_id"], "fail-loop")

    def test_no_op_when_task_dir_env_unset(self) -> None:
        """Reviewer one-shot path: TB3_METRICS_TASK_DIR is unset, so
        running scripts/run_static_checks.py against a task must not create a
        metrics file in the task dir or anywhere else.

        Half of exec-plan Tests § test_no_opt_in_leaves_no_counter
        (the run_static_checks half; the collapse_check half lands in
        unit 7).
        """
        with tempfile.TemporaryDirectory() as tmp:
            task_dir = Path(tmp)
            self.assertNotIn(
                metrics_collector.TASK_DIR_ENV, os.environ
            )

            exit_code = self._invoke_main_with_reporter(
                task_dir, _make_reporter()
            )
            self.assertEqual(exit_code, 0)

            self.assertFalse(
                (
                    task_dir / metrics_collector.METRICS_FILE_NAME
                ).exists()
            )

    def test_does_not_record_when_task_dir_arg_invalid(self) -> None:
        """Usage errors (return code 2: missing task dir or wrong
        --version) must not record a metric — only actual check
        invocations do."""
        os.environ[metrics_collector.TASK_DIR_ENV] = "/nonexistent"
        os.environ[metrics_collector.RUN_ID_ENV] = "usage-err"

        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(
            stderr
        ):
            exit_code = run_static_checks.main(
                [
                    "--task-dir",
                    "/nonexistent/task/dir",
                    "--version",
                    "terminus_3",
                ]
            )
        self.assertEqual(exit_code, 2)

    def test_run_static_checks_hook_counts_fail_then_pass(self) -> None:
        """Two invocations with TB3_METRICS_TASK_DIR and
        TB3_METRICS_RUN_ID set, first FAIL then PASS; assert counter
        file has both records with matching timestamp_ns order, each
        tagged with the exported run_id.

        Pinned by exec-plan Tests §
        test_run_static_checks_hook_counts_fail_then_pass.
        """
        with tempfile.TemporaryDirectory() as tmp:
            task_dir = Path(tmp)
            os.environ[metrics_collector.TASK_DIR_ENV] = str(task_dir)
            os.environ[metrics_collector.RUN_ID_ENV] = "loop"

            self.assertEqual(
                self._invoke_main_with_reporter(
                    task_dir, _make_reporter(failures=1)
                ),
                1,
            )
            self.assertEqual(
                self._invoke_main_with_reporter(
                    task_dir, _make_reporter()
                ),
                0,
            )

            tool_records = [
                r
                for r in _read_metrics(task_dir)
                if r.get("tool") == "run_static_checks"
            ]
            self.assertEqual(len(tool_records), 2, tool_records)
            self.assertEqual(
                [r["outcome"] for r in tool_records], ["FAIL", "PASS"]
            )
            for record in tool_records:
                self.assertEqual(record["run_id"], "loop")
            self.assertLessEqual(
                tool_records[0]["timestamp_ns"],
                tool_records[1]["timestamp_ns"],
            )


def _make_collapse_report(*, fails: int = 0, warns: int = 0) -> dict:
    """Build a collapse_check report dict in a controlled fails/warns
    state. The hook only reads `report["fails"]` so the rest of the
    structure can be a minimal stub."""
    return {
        "oracle_targets": [],
        "oracle_loc_non_boilerplate": 0,
        "touched_roots": [],
        "frontier_concentration": {
            "dominant_root": None,
            "dominant_root_share": 0.0,
        },
        "results": [],
        "fails": fails,
        "warns": warns,
    }


class CollapseCheckHookTest(_MetricsEnvCleaner):
    """Env-gated FAIL/PASS hook in scripts/collapse_check.py.

    Same pattern as run_static_checks but with no WARN tier per
    exec-plan: outcome ∈ {"FAIL", "PASS"}. A WARN-only run records
    PASS because the metric `collapse_check_failures_before_first_pass`
    only counts hard failures.

    Tests mock `collapse_check.build_report` so the outcome is
    derived from a controlled report dict rather than from any
    specific fixture's pinned collapse state.
    """

    def _invoke_main_with_report(
        self, task_dir: Path, report: dict
    ) -> int:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            with mock.patch.object(
                collapse_check, "build_report", return_value=report
            ):
                return collapse_check.main([str(task_dir)])

    def test_records_pass_outcome(self) -> None:
        """Report with no fails and no warns → outcome=PASS, exit 0."""
        with tempfile.TemporaryDirectory() as tmp:
            task_dir = Path(tmp)
            os.environ[metrics_collector.TASK_DIR_ENV] = str(task_dir)
            os.environ[metrics_collector.RUN_ID_ENV] = "pass-loop"

            exit_code = self._invoke_main_with_report(
                task_dir, _make_collapse_report()
            )
            self.assertEqual(exit_code, 0)

            tool_records = [
                r
                for r in _read_metrics(task_dir)
                if r.get("tool") == "collapse_check"
            ]
            self.assertEqual(len(tool_records), 1)
            self.assertEqual(tool_records[0]["outcome"], "PASS")
            self.assertEqual(tool_records[0]["run_id"], "pass-loop")

    def test_warn_only_collapse_records_pass(self) -> None:
        """Report with warns but no fails → outcome=PASS (no WARN
        tier in collapse). Exit code is 2 (WARN) but the metric
        records PASS because the counter only tracks hard failures
        gating Step 2b. Pins the no-WARN-tier semantics from the
        exec-plan Change Surface § scripts/collapse_check.py bullet."""
        with tempfile.TemporaryDirectory() as tmp:
            task_dir = Path(tmp)
            os.environ[metrics_collector.TASK_DIR_ENV] = str(task_dir)
            os.environ[metrics_collector.RUN_ID_ENV] = "warn-loop"

            exit_code = self._invoke_main_with_report(
                task_dir, _make_collapse_report(warns=2)
            )
            self.assertEqual(exit_code, 2)

            tool_records = [
                r
                for r in _read_metrics(task_dir)
                if r.get("tool") == "collapse_check"
            ]
            self.assertEqual(len(tool_records), 1)
            self.assertEqual(tool_records[0]["outcome"], "PASS")
            self.assertEqual(tool_records[0]["run_id"], "warn-loop")

    def test_records_fail_outcome(self) -> None:
        """Report with fails ≥ 1 → outcome=FAIL, exit 1."""
        with tempfile.TemporaryDirectory() as tmp:
            task_dir = Path(tmp)
            os.environ[metrics_collector.TASK_DIR_ENV] = str(task_dir)
            os.environ[metrics_collector.RUN_ID_ENV] = "fail-loop"

            exit_code = self._invoke_main_with_report(
                task_dir, _make_collapse_report(fails=1, warns=1)
            )
            self.assertEqual(exit_code, 1)

            tool_records = [
                r
                for r in _read_metrics(task_dir)
                if r.get("tool") == "collapse_check"
            ]
            self.assertEqual(len(tool_records), 1)
            self.assertEqual(tool_records[0]["outcome"], "FAIL")
            self.assertEqual(tool_records[0]["run_id"], "fail-loop")

    def test_no_op_when_task_dir_env_unset(self) -> None:
        """Reviewer one-shot path. Other half of exec-plan Tests §
        test_no_opt_in_leaves_no_counter (the run_static_checks half
        is in unit 6); together they cover both Phase A tools.
        """
        with tempfile.TemporaryDirectory() as tmp:
            task_dir = Path(tmp)
            self.assertNotIn(
                metrics_collector.TASK_DIR_ENV, os.environ
            )

            exit_code = self._invoke_main_with_report(
                task_dir, _make_collapse_report()
            )
            self.assertEqual(exit_code, 0)

            self.assertFalse(
                (
                    task_dir / metrics_collector.METRICS_FILE_NAME
                ).exists()
            )

    def test_does_not_record_when_task_dir_arg_invalid(self) -> None:
        """Usage errors (collapse_check returns 1 if task_dir is not
        a directory) must not record a metric. Note: collapse's
        usage-error exit code (1) collides with the FAIL exit code,
        which is exactly why the hook records based on
        `report["fails"]` rather than the exit code — see exec-plan
        rationale."""
        os.environ[metrics_collector.TASK_DIR_ENV] = "/nonexistent"
        os.environ[metrics_collector.RUN_ID_ENV] = "usage-err"

        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(
            stderr
        ):
            exit_code = collapse_check.main(["/nonexistent/task/dir"])
        self.assertEqual(exit_code, 1)

    def test_collapse_check_hook_counts_fail(self) -> None:
        """Two invocations with TB3_METRICS_TASK_DIR and
        TB3_METRICS_RUN_ID set, first FAIL then PASS; assert counter
        file has both records with matching timestamp_ns order, each
        tagged with the exported run_id.

        Pinned by exec-plan Tests § test_collapse_check_hook_counts_fail.
        """
        with tempfile.TemporaryDirectory() as tmp:
            task_dir = Path(tmp)
            os.environ[metrics_collector.TASK_DIR_ENV] = str(task_dir)
            os.environ[metrics_collector.RUN_ID_ENV] = "loop"

            self.assertEqual(
                self._invoke_main_with_report(
                    task_dir, _make_collapse_report(fails=1)
                ),
                1,
            )
            self.assertEqual(
                self._invoke_main_with_report(
                    task_dir, _make_collapse_report()
                ),
                0,
            )

            tool_records = [
                r
                for r in _read_metrics(task_dir)
                if r.get("tool") == "collapse_check"
            ]
            self.assertEqual(len(tool_records), 2, tool_records)
            self.assertEqual(
                [r["outcome"] for r in tool_records], ["FAIL", "PASS"]
            )
            for record in tool_records:
                self.assertEqual(record["run_id"], "loop")
            self.assertLessEqual(
                tool_records[0]["timestamp_ns"],
                tool_records[1]["timestamp_ns"],
            )


def _build_clean_static_reporter() -> "run_static_checks.Reporter":
    reporter = run_static_checks.Reporter()
    reporter.ok("synthetic clean run")
    return reporter


def _build_clean_collapse_report() -> dict[str, object]:
    return {
        "oracle_targets": ["src/main.cc"],
        "oracle_loc_non_boilerplate": 42,
        "touched_roots": ["src"],
        "frontier_concentration": {
            "dominant_root": "src",
            "dominant_root_share": 0.5,
            "root_counts": {"src": 1},
        },
        "results": [],
        "fails": 0,
        "warns": 0,
    }


def _zip_from_source(task_dir: Path, zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(task_dir.rglob("*")):
            if not path.is_file():
                continue
            rel = Path(path.relative_to(task_dir).as_posix())
            if approve_task.should_skip_packaged_path(rel):
                continue
            archive.write(path, arcname=rel.as_posix())


class ApproveTaskMetricsTest(_MetricsEnvCleaner):
    """Metrics emission and dirty-flag counter in scripts/approve_task.py.

    Pinned by exec-plan Tests § test_metrics_block_lands_on_successful_approval,
    test_dirty_flag_counter_increments_on_stale_sentinel,
    test_metrics_block_skipped_when_spec_missing,
    test_draft_commitments_diff_is_null_initially, and
    test_aggregate_reports_no_pass_when_second_marker_absent.

    The fixture is `implicit-step-restart` (already used by
    test_approve_task_dirty_flag.py); Phase A validators are mocked
    so we exercise only the metrics + dirty-flag branches of
    build_report.
    """

    fixture_name = "implicit-step-restart"

    def setUp(self) -> None:
        super().setUp()
        self.tmpdir_obj = tempfile.TemporaryDirectory(
            prefix="approve-metrics-"
        )
        self.addCleanup(self.tmpdir_obj.cleanup)
        self.tmp_root = Path(self.tmpdir_obj.name)
        fixture = FIXTURE_TASKS_DIR / self.fixture_name
        self.task_dir = self.tmp_root / fixture.name
        shutil.copytree(fixture, self.task_dir)
        self.zip_path = self.tmp_root / f"{fixture.name}.zip"
        self.spec_path = (
            self.tmp_root / "specs" / f"{fixture.name}.md"
        )
        self.spec_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_path = self.spec_path.with_name(
            f"{fixture.name}-validation-log.md"
        )

    def _build_clean_zip(self) -> None:
        _zip_from_source(self.task_dir, self.zip_path)

    def _build_report_with_phase_a_mocked(self, **kwargs):
        with mock.patch.object(
            approve_task.run_static_checks,
            "run_checks",
            return_value=_build_clean_static_reporter(),
        ), mock.patch.object(
            approve_task.collapse_check,
            "build_report",
            return_value=_build_clean_collapse_report(),
        ):
            return approve_task.build_report(
                self.task_dir,
                self.zip_path,
                skip_verifier_health=True,
                **kwargs,
            )

    def _read_metric_records(self) -> list[dict]:
        return _read_metrics(self.task_dir)

    def test_emit_metrics_default_off_for_build_report(self) -> None:
        """Library callers default to emit_metrics=False; existing
        fixtures need no edit. Pin per exec-plan § Effect on existing
        fixtures and tasks."""
        task_integrity.write_step2b_checksum(self.task_dir)
        self._build_clean_zip()
        self.spec_path.write_text("# Spec\n\nbody\n", encoding="utf-8")

        payload = self._build_report_with_phase_a_mocked()

        self.assertTrue(payload["approved"], payload["blocking_failures"])
        self.assertFalse(self.log_path.exists())

    def test_emit_metrics_true_writes_validation_log(self) -> None:
        """When emit_metrics=True and the spec markdown exists, a
        metrics block is appended to <task-name>-validation-log.md."""
        task_integrity.write_step2b_checksum(self.task_dir)
        self._build_clean_zip()
        self.spec_path.write_text("# Spec\n\nbody\n", encoding="utf-8")

        payload = self._build_report_with_phase_a_mocked(
            emit_metrics=True, spec_path=self.spec_path
        )

        self.assertTrue(payload["approved"], payload["blocking_failures"])
        self.assertTrue(self.log_path.exists())
        self.assertIn(
            "## Per-task authoring metrics",
            self.log_path.read_text(encoding="utf-8"),
        )

    def test_dirty_flag_counter_increments_on_stale_sentinel(
        self,
    ) -> None:
        """exec-plan Tests §
        test_dirty_flag_counter_increments_on_stale_sentinel.

        Preflight, modify a task file, approve; assert the counter
        file has at least one
        {tool: approve_task, outcome: dirty_flag, ...} record carrying
        a run_id matching the preflight's exported TB3_METRICS_RUN_ID.
        """
        task_integrity.write_step2b_checksum(self.task_dir)
        (self.task_dir / "instruction.md").write_text(
            "edited after preflight\n", encoding="utf-8"
        )
        self._build_clean_zip()

        os.environ[metrics_collector.RUN_ID_ENV] = "preflight-abc"

        payload = self._build_report_with_phase_a_mocked()

        self.assertFalse(payload["approved"], payload["blocking_failures"])
        records = self._read_metric_records()
        dirty = [
            r
            for r in records
            if r.get("tool") == "approve_task"
            and r.get("outcome") == "dirty_flag"
        ]
        self.assertGreaterEqual(len(dirty), 1, records)
        self.assertEqual(dirty[0]["run_id"], "preflight-abc")

    def test_dirty_flag_uses_adhoc_when_run_id_env_unset(self) -> None:
        """If approve_task is invoked outside a preflight loop and
        TB3_METRICS_RUN_ID is unset, the dirty_flag record uses the
        'adhoc' sentinel rather than crashing or omitting the field.
        Mirrors the metrics_collector adhoc-fallback contract."""
        task_integrity.write_step2b_checksum(self.task_dir)
        (self.task_dir / "instruction.md").write_text(
            "edited\n", encoding="utf-8"
        )
        self._build_clean_zip()
        self.assertNotIn(metrics_collector.RUN_ID_ENV, os.environ)

        payload = self._build_report_with_phase_a_mocked()

        self.assertFalse(payload["approved"])
        records = self._read_metric_records()
        dirty = [
            r
            for r in records
            if r.get("tool") == "approve_task"
            and r.get("outcome") == "dirty_flag"
        ]
        self.assertGreaterEqual(len(dirty), 1)
        self.assertEqual(
            dirty[0]["run_id"], metrics_collector.ADHOC_RUN_ID
        )

    def test_metrics_block_lands_on_successful_approval(self) -> None:
        """exec-plan Tests § test_metrics_block_lands_on_successful_approval.

        Synthetic tasks/<fixture>/ plus specs/<fixture>.md; seed the
        counter file with a realistic preflight loop (FAIL→PASS for
        run_static_checks, PASS for collapse_check, both wall-clock
        markers); run approve_task.build_report against the resulting
        zip; assert specs/<fixture>-validation-log.md now contains a
        `## Per-task authoring metrics` heading with all eight bullets
        present.
        """
        task_integrity.write_step2b_checksum(self.task_dir)
        self._build_clean_zip()
        self.spec_path.write_text("# Spec\n\nbody\n", encoding="utf-8")

        metrics_collector.record_marker(
            metrics_collector.MARKER_FIRST_INVOCATION,
            task_dir=self.task_dir,
            run_id="loop-1",
            timestamp_ns=1_000_000_000,
        )
        metrics_collector.record_exit(
            "run_static_checks",
            "FAIL",
            task_dir=self.task_dir,
            run_id="loop-1",
            timestamp_ns=2_000_000_000,
        )
        metrics_collector.record_exit(
            "run_static_checks",
            "PASS",
            task_dir=self.task_dir,
            run_id="loop-1",
            timestamp_ns=3_000_000_000,
        )
        metrics_collector.record_exit(
            "collapse_check",
            "PASS",
            task_dir=self.task_dir,
            run_id="loop-1",
            timestamp_ns=4_000_000_000,
        )
        metrics_collector.record_marker(
            metrics_collector.MARKER_FIRST_PASS,
            task_dir=self.task_dir,
            run_id="loop-1",
            timestamp_ns=5_000_000_000,
        )

        payload = self._build_report_with_phase_a_mocked(
            emit_metrics=True, spec_path=self.spec_path
        )

        self.assertTrue(payload["approved"], payload["blocking_failures"])
        self.assertTrue(self.log_path.exists())
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn("## Per-task authoring metrics", log_text)

        for prefix in (
            "- count of scripts/run_static_checks.py FAIL exits before first PASS",
            "- count of scripts/run_static_checks.py WARN-only exits before approval",
            "- count of scripts/collapse_check.py FAIL exits before first PASS",
            "- count of dirty-flag triggers",
            "- wall-clock time from first preflight to first preflight PASS",
            "- wall-clock time from first Step 2b PASS to scripts/approve_task.py exit 0",
            "- list of CNI references that fired during the authoring",
            "- whether the spec's Initial Draft Commitments matched the final file set",
        ):
            self.assertIn(prefix, log_text)

        self.assertRegex(
            log_text,
            r"FAIL exits before first PASS:\s*1",
        )
        self.assertRegex(
            log_text,
            r"first preflight to first preflight PASS:\s*4\.00s",
        )

    def test_metrics_block_skipped_when_spec_missing(self) -> None:
        """exec-plan Tests § test_metrics_block_skipped_when_spec_missing.

        Grandfathered task with no specs/<task-name>.md; assert
        approve_task.build_report still exits with approved=True and
        logs a stderr note; counter file logic still runs (block
        skipped, not failed).
        """
        task_integrity.write_step2b_checksum(self.task_dir)
        self._build_clean_zip()
        self.assertFalse(self.spec_path.exists())

        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            payload = self._build_report_with_phase_a_mocked(
                emit_metrics=True, spec_path=self.spec_path
            )

        self.assertTrue(payload["approved"], payload["blocking_failures"])
        self.assertFalse(self.log_path.exists())
        self.assertIn(
            "validation_log: skipping metrics block",
            stderr.getvalue(),
        )

    def test_draft_commitments_diff_is_null_initially(self) -> None:
        """exec-plan Tests § test_draft_commitments_diff_is_null_initially.

        Successful approval produces a metrics block whose
        draft_commitments_diff field is `null`. Pin until the
        deferred parser ships in a follow-up exec-plan.
        """
        task_integrity.write_step2b_checksum(self.task_dir)
        self._build_clean_zip()
        self.spec_path.write_text("# Spec\n\nbody\n", encoding="utf-8")

        payload = self._build_report_with_phase_a_mocked(
            emit_metrics=True, spec_path=self.spec_path
        )
        self.assertTrue(payload["approved"], payload["blocking_failures"])
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn("draft_commitments_diff", log_text)
        # The literal "null" must follow the draft_commitments_diff
        # label, i.e. no value parsed yet.
        idx = log_text.index("draft_commitments_diff")
        tail = log_text[idx:].splitlines()[0]
        self.assertIn("null", tail, tail)

    def test_aggregate_reports_no_pass_when_second_marker_absent(
        self,
    ) -> None:
        """exec-plan Tests §
        test_aggregate_reports_no_pass_when_second_marker_absent.

        End-to-end synthetic run with Phase C stubbed to FAIL forever
        so t_first_step2b_pass_ns is never written; assert aggregate()
        returns the literal string 'no Step 2b PASS yet' for the
        wall-clock duration field, does not raise, and does not emit
        0; assert the rendered metrics block surfaces that literal in
        place of a duration.
        """
        task_integrity.write_step2b_checksum(self.task_dir)
        self._build_clean_zip()
        self.spec_path.write_text("# Spec\n\nbody\n", encoding="utf-8")

        metrics_collector.record_marker(
            metrics_collector.MARKER_FIRST_INVOCATION,
            task_dir=self.task_dir,
            run_id="loop-x",
        )

        aggregated = metrics_collector.aggregate(self.task_dir)
        self.assertEqual(
            aggregated["wall_clock_first_preflight_to_first_pass_ns"],
            metrics_collector.NO_PASS_SENTINEL,
        )
        self.assertNotEqual(
            aggregated["wall_clock_first_preflight_to_first_pass_ns"], 0
        )

        payload = self._build_report_with_phase_a_mocked(
            emit_metrics=True, spec_path=self.spec_path
        )
        self.assertTrue(payload["approved"], payload["blocking_failures"])
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn(
            metrics_collector.NO_PASS_SENTINEL, log_text, log_text
        )

    def test_failed_approval_does_not_emit_metrics_block(self) -> None:
        """A blocking failure (any) suppresses metrics-block emission.
        The block represents a successful authoring; failure runs are
        not part of the success record. The dirty-flag counter is
        still incremented (that's its whole purpose), but the spec
        log is not touched.
        """
        # No checksum written → blocking failure.
        self._build_clean_zip()
        self.spec_path.write_text("# Spec\n\nbody\n", encoding="utf-8")

        payload = self._build_report_with_phase_a_mocked(
            emit_metrics=True, spec_path=self.spec_path
        )

        self.assertFalse(payload["approved"], payload["blocking_failures"])
        self.assertFalse(self.log_path.exists())

    def test_main_cli_default_emits_metrics(self) -> None:
        """CLI main() defaults to emit_metrics=True. With a synthetic
        spec available via monkeypatched approve_task.REPO_ROOT, the
        validation log is written without an explicit --emit-metrics
        flag."""
        task_integrity.write_step2b_checksum(self.task_dir)
        self._build_clean_zip()
        self.spec_path.write_text("# Spec\n\nbody\n", encoding="utf-8")

        stdout = io.StringIO()
        with mock.patch.object(
            approve_task, "REPO_ROOT", self.tmp_root
        ), mock.patch.object(
            approve_task.run_static_checks,
            "run_checks",
            return_value=_build_clean_static_reporter(),
        ), mock.patch.object(
            approve_task.collapse_check,
            "build_report",
            return_value=_build_clean_collapse_report(),
        ), contextlib.redirect_stdout(stdout):
            exit_code = approve_task.main(
                [
                    "--task-dir",
                    str(self.task_dir),
                    "--zip",
                    str(self.zip_path),
                    "--skip-verifier-health",
                ]
            )

        self.assertEqual(exit_code, 0, stdout.getvalue())
        self.assertTrue(self.log_path.exists())

    def test_main_cli_no_emit_metrics_flag_skips_emission(self) -> None:
        """`--no-emit-metrics` opts the CLI out of validation-log
        emission. Useful for CI smoke-tests / one-shot reviewer
        approvals where the spec log is not the relevant artifact."""
        task_integrity.write_step2b_checksum(self.task_dir)
        self._build_clean_zip()
        self.spec_path.write_text("# Spec\n\nbody\n", encoding="utf-8")

        stdout = io.StringIO()
        with mock.patch.object(
            approve_task, "REPO_ROOT", self.tmp_root
        ), mock.patch.object(
            approve_task.run_static_checks,
            "run_checks",
            return_value=_build_clean_static_reporter(),
        ), mock.patch.object(
            approve_task.collapse_check,
            "build_report",
            return_value=_build_clean_collapse_report(),
        ), contextlib.redirect_stdout(stdout):
            exit_code = approve_task.main(
                [
                    "--task-dir",
                    str(self.task_dir),
                    "--zip",
                    str(self.zip_path),
                    "--skip-verifier-health",
                    "--no-emit-metrics",
                ]
            )

        self.assertEqual(exit_code, 0, stdout.getvalue())
        self.assertFalse(self.log_path.exists())


class EndToEndAuthoringTest(unittest.TestCase):
    """Full synthetic authoring loop end-to-end.

    Covers the integration surfaces that the per-tool unit tests
    cannot: scripts/check-task.sh as a real subprocess writing
    .step2b-metrics.jsonl through the real metrics_collector,
    Phase A tools recording their outcomes through the env-var-gated
    hooks, Phase B's zip-command excluding the metrics file, and
    approve_task.build_report aggregating the recorded events into
    the rendered validation-log block.

    Phase A static/collapse tools are stubbed (the instrumentation
    code path is what we're testing, not whether the byzantine
    fixture passes collapse audit). The stubs record metrics like
    the real hooks would so the aggregator sees realistic input.

    Pinned by exec-plan Tests § test_metrics_block_lands_on_successful_approval
    (the integration shape of it; the in-process unit-8 variant is
    the surgical pin) and §
    test_metrics_file_excluded_from_submission_zip.
    """

    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="e2e-authoring-"))
        self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)
        scripts_dir = self.tmpdir / "scripts"
        scripts_dir.mkdir()

        for real in (
            "scripts/metrics_collector.py",
            "scripts/validation_log.py",
            "scripts/task_integrity.py",
            "scripts/validate_submission_zip.py",
        ):
            shutil.copy(REPO_ROOT / real, self.tmpdir / real)

        # Phase A stubs that mirror the real env-gated hooks: when
        # TB3_METRICS_TASK_DIR is set, record a PASS; otherwise no-op.
        # This keeps the integration test independent of the heavy
        # static/collapse rules while still exercising the metric
        # write path.
        stub_template = (
            "import os, sys\n"
            "if os.environ.get('TB3_METRICS_TASK_DIR'):\n"
            "    import metrics_collector\n"
            "    metrics_collector.record_exit({tool!r}, 'PASS')\n"
            "sys.exit(0)\n"
        )
        (self.tmpdir / "scripts/run_static_checks.py").write_text(
            stub_template.format(tool="run_static_checks")
        )
        (self.tmpdir / "scripts/collapse_check.py").write_text(
            stub_template.format(tool="collapse_check")
        )

        script_local = scripts_dir / "check-task.sh"
        shutil.copy(SCRIPT_PATH, script_local)
        script_local.chmod(0o755)

        self.task_dir = self.tmpdir / "tasks" / "synth"
        self.task_dir.mkdir(parents=True)
        _seed_min_task(self.task_dir)

        self.spec_path = self.tmpdir / "specs" / "synth.md"
        self.spec_path.parent.mkdir(parents=True, exist_ok=True)
        self.spec_path.write_text(
            "# Synth spec\n\nbody\n", encoding="utf-8"
        )
        self.log_path = self.spec_path.with_name(
            "synth-validation-log.md"
        )

        self.zip_path = self.tmpdir / "synth.zip"

    def _run_preflight(
        self, env_extra: dict[str, str] | None = None
    ) -> "subprocess.CompletedProcess[str]":
        env = os.environ.copy()
        for var in (
            metrics_collector.TASK_DIR_ENV,
            metrics_collector.RUN_ID_ENV,
        ):
            env.pop(var, None)
        if env_extra:
            env.update(env_extra)
        return subprocess.run(
            ["bash", "scripts/check-task.sh", "tasks/synth"],
            cwd=str(self.tmpdir),
            capture_output=True,
            text=True,
            env=env,
        )

    def _build_zip_from_task(self) -> None:
        """Mirror the source-manifest filter (approve_task's
        should_skip_packaged_path) so the zip approve_task verifies
        matches what the source tree contains. This is the same
        transformation Phase B applies."""
        with zipfile.ZipFile(
            self.zip_path, "w", compression=zipfile.ZIP_DEFLATED
        ) as archive:
            for path in sorted(self.task_dir.rglob("*")):
                if not path.is_file():
                    continue
                rel = Path(path.relative_to(self.task_dir).as_posix())
                if approve_task.should_skip_packaged_path(rel):
                    continue
                archive.write(path, arcname=rel.as_posix())

    def _read_metric_records(self) -> list[dict]:
        path = self.task_dir / metrics_collector.METRICS_FILE_NAME
        if not path.exists():
            return []
        return [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def test_full_authoring_loop_writes_metrics_block(self) -> None:
        """End-to-end happy path:

        1. Run scripts/check-task.sh (real script, real metrics_collector,
           stubbed Phase A that records PASS for both tools).
        2. Verify .step2b-metrics.jsonl has 2 markers + 2 tool exits
           sharing one run_id.
        3. Build a clean zip from the synthetic task tree.
        4. Run approve_task.build_report in-process with Phase A mocks
           clean and REPO_ROOT redirected to the tmpdir.
        5. Assert the validation log contains the rendered metrics
           block with all eight bullets and value-pinned counts.
        """
        result = self._run_preflight()
        self.assertEqual(result.returncode, 0, result.stderr)

        records = self._read_metric_records()
        self.assertGreater(len(records), 0)

        marker_outcomes = sorted(
            r["outcome"]
            for r in records
            if r.get("tool") == metrics_collector.MARKER_TOOL
        )
        self.assertEqual(
            marker_outcomes,
            sorted(
                [
                    metrics_collector.MARKER_FIRST_INVOCATION,
                    metrics_collector.MARKER_FIRST_PASS,
                ]
            ),
        )

        tool_records = [
            r
            for r in records
            if r.get("tool") in {"run_static_checks", "collapse_check"}
        ]
        self.assertEqual(len(tool_records), 2, tool_records)
        self.assertTrue(
            all(r["outcome"] == "PASS" for r in tool_records),
            tool_records,
        )

        run_ids = {r["run_id"] for r in records}
        self.assertEqual(len(run_ids), 1, run_ids)
        preflight_run_id = next(iter(run_ids))
        self.assertNotEqual(
            preflight_run_id, metrics_collector.ADHOC_RUN_ID
        )

        self._build_zip_from_task()

        with mock.patch.object(
            approve_task, "REPO_ROOT", self.tmpdir
        ), mock.patch.object(
            approve_task.run_static_checks,
            "run_checks",
            return_value=_build_clean_static_reporter(),
        ), mock.patch.object(
            approve_task.collapse_check,
            "build_report",
            return_value=_build_clean_collapse_report(),
        ):
            payload = approve_task.build_report(
                self.task_dir,
                self.zip_path,
                skip_verifier_health=True,
                emit_metrics=True,
            )

        self.assertTrue(payload["approved"], payload["blocking_failures"])
        self.assertTrue(
            self.log_path.exists(),
            f"validation log missing at {self.log_path}",
        )
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn("## Per-task authoring metrics", log_text)

        for prefix in (
            "- count of scripts/run_static_checks.py FAIL exits before first PASS",
            "- count of scripts/run_static_checks.py WARN-only exits before approval",
            "- count of scripts/collapse_check.py FAIL exits before first PASS",
            "- count of dirty-flag triggers",
            "- wall-clock time from first preflight to first preflight PASS",
            "- wall-clock time from first Step 2b PASS to scripts/approve_task.py exit 0",
            "- list of CNI references that fired during the authoring",
            "- whether the spec's Initial Draft Commitments matched the final file set",
        ):
            self.assertIn(prefix, log_text, log_text)

        # The Phase A stubs reported PASS, so FAIL counts must be 0.
        # The preflight succeeded so dirty_flag count must be 0.
        # The wall-clock duration must be a numeric duration, not the
        # NO_PASS_SENTINEL string.
        self.assertRegex(log_text, r"FAIL exits before first PASS:\s*0")
        self.assertRegex(
            log_text,
            r"dirty-flag triggers .*?:\s*0",
        )
        self.assertNotIn(metrics_collector.NO_PASS_SENTINEL, log_text)

    def test_metrics_file_excluded_from_submission_zip(self) -> None:
        """exec-plan Tests § test_metrics_file_excluded_from_submission_zip.

        Phase B's `zip -x '.*'` invocation must exclude
        .step2b-metrics.jsonl from the produced archive (the generic
        dotfile glob covers it, but a regression here would let the
        metric file leak into Harbor submissions). Override
        scripts/validate_submission_zip.py with a snapshot stub that copies
        the precheck zip before the script's EXIT trap removes it,
        then inspect the snapshot.
        """
        snapshot_path = self.tmpdir / "snapshot.zip"
        (self.tmpdir / "scripts/validate_submission_zip.py").write_text(
            "import shutil, sys\n"
            f"shutil.copy(sys.argv[1], {str(snapshot_path)!r})\n"
            "sys.exit(0)\n"
        )

        metric_file = self.task_dir / metrics_collector.METRICS_FILE_NAME
        metric_file.write_text(
            '{"tool":"run_static_checks","outcome":"PASS",'
            '"timestamp_ns":1,"run_id":"abc"}\n',
            encoding="utf-8",
        )

        result = self._run_preflight()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(
            snapshot_path.exists(),
            f"snapshot missing; preflight output: {result.stdout}",
        )

        with zipfile.ZipFile(snapshot_path) as archive:
            names = archive.namelist()

        self.assertNotIn(
            metrics_collector.METRICS_FILE_NAME,
            names,
            f"Phase B leaked metric file into zip: {names}",
        )
        self.assertIn(
            "instruction.md",
            names,
            f"Phase B unexpectedly excluded a required file: {names}",
        )


if __name__ == "__main__":
    unittest.main()
