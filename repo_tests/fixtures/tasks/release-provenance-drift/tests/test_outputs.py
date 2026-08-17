"""Integration checks for the mixed Rust/native provenance pipeline under /app."""

from __future__ import annotations

import ctypes
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import tomllib
from pathlib import Path

import pytest

APP = Path("/app")
HARNESS = APP / "ci" / "harness"
PKG_BIN = APP / "out" / "pkg" / "bin"
PKG_SO = PKG_BIN / "libplugin_core.so"
SEAL_PATH = APP / "out" / "pkg" / "seal.json"
LOADER = APP / "out" / "loader"
RELEASE_SO = APP / "target" / "release" / "libplugin_core.so"
DEBUG_SO = APP / "target" / "debug" / "libplugin_core.so"
STEP_MAP = {
    "build_and_load": str(HARNESS / "build_and_load.sh"),
    "partial_edit_rust": str(HARNESS / "partial_edit_rust.sh"),
    "partial_edit_template": str(HARNESS / "partial_edit_template.sh"),
    "remove_plugin": str(HARNESS / "remove_plugin.sh"),
}


def _apply_pristine(pristine_tree: dict[str, str]) -> None:
    shutil.rmtree(APP / "build" / "cpp", ignore_errors=True)
    (APP / "plugin-core" / "src" / "lib.rs").write_text(pristine_tree["lib_rs"], encoding="utf-8")
    (APP / "codegen" / "templates" / "ffi.rs.tpl").write_text(pristine_tree["tpl"], encoding="utf-8")
    (APP / "cpp-bridge" / "src" / "legacy.cpp").write_text(pristine_tree["legacy_cpp"], encoding="utf-8")
    (APP / "cpp-bridge" / "CMakeLists.txt").write_text(pristine_tree["cmake_txt"], encoding="utf-8")
    (APP / "stage_graph" / "stage_layout.json").write_text(pristine_tree["layout"], encoding="utf-8")


@pytest.fixture(scope="session")
def pristine_tree() -> dict[str, str]:
    return {
        "lib_rs": (APP / "plugin-core" / "src" / "lib.rs").read_text(encoding="utf-8"),
        "tpl": (APP / "codegen" / "templates" / "ffi.rs.tpl").read_text(encoding="utf-8"),
        "legacy_cpp": (APP / "cpp-bridge" / "src" / "legacy.cpp").read_text(encoding="utf-8"),
        "cmake_txt": (APP / "cpp-bridge" / "CMakeLists.txt").read_text(encoding="utf-8"),
        "layout": (APP / "stage_graph" / "stage_layout.json").read_text(encoding="utf-8"),
    }


@pytest.fixture(autouse=True)
def reset_tree(pristine_tree: dict[str, str]) -> None:
    _apply_pristine(pristine_tree)
    yield
    _apply_pristine(pristine_tree)


def _run(cmd: list[str], check: bool = True, **kwargs: object) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    extra = kwargs.pop("env", None)
    if isinstance(extra, dict):
        env.update(extra)
    return subprocess.run(
        cmd,
        cwd=str(APP),
        text=True,
        capture_output=True,
        check=check,
        env=env,
        **kwargs,
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_seal() -> dict[str, object]:
    return json.loads(SEAL_PATH.read_text(encoding="utf-8"))


def _expected_bundle_names() -> set[str]:
    layout = json.loads((APP / "stage_graph" / "stage_layout.json").read_text(encoding="utf-8"))
    release = layout["release"]
    return set(release["rust"]) | set(release["cpp"])


def _load_plugin_exports(path: Path) -> dict[str, str]:
    fd, temp_name = tempfile.mkstemp(suffix=".so")
    os.close(fd)
    temp_path = Path(temp_name)
    temp_path.write_bytes(path.read_bytes())
    try:
        lib = ctypes.CDLL(str(temp_path))

        def read_string(name: str, len_name: str) -> str:
            ptr_fn = getattr(lib, name)
            len_fn = getattr(lib, len_name)
            ptr_fn.restype = ctypes.c_void_p
            len_fn.restype = ctypes.c_size_t
            ptr = ptr_fn()
            size = int(len_fn())
            return ctypes.string_at(ptr, size).decode("utf-8")

        return {
            "epoch": read_string("plugin_epoch", "plugin_epoch_len"),
            "build_note": read_string("plugin_build_note", "plugin_build_note_len"),
            "profile_tag": read_string("plugin_profile_tag", "plugin_profile_tag_len"),
        }
    finally:
        temp_path.unlink(missing_ok=True)


def _bundle_snapshot() -> dict[str, object]:
    seal = _read_seal()
    exports = _load_plugin_exports(PKG_SO)
    files = seal["files"]
    assert isinstance(files, dict)
    return {
        "epoch": seal["epoch"],
        "plugin_epoch": exports["epoch"],
        "build_note": exports["build_note"],
        "profile_tag": exports["profile_tag"],
        "plugin_hash": _sha256(PKG_SO),
        "release_hash": _sha256(RELEASE_SO),
        "debug_hash": _sha256(DEBUG_SO),
        "seal_hash": files["libplugin_core.so"],
        "names": set(files),
    }


def _assert_seal_hashes_match_binaries() -> None:
    seal = _read_seal()
    files = seal.get("files")
    assert isinstance(files, dict)
    for name, expected_hash in files.items():
        assert isinstance(expected_hash, str) and expected_hash
        path = PKG_BIN / name
        assert _sha256(path) == expected_hash


def _assert_release_bundle_coherent() -> dict[str, object]:
    snapshot = _bundle_snapshot()
    assert snapshot["epoch"] == snapshot["plugin_epoch"]
    assert snapshot["plugin_hash"] == snapshot["seal_hash"]
    assert snapshot["plugin_hash"] == snapshot["release_hash"]
    assert snapshot["plugin_hash"] != snapshot["debug_hash"]
    assert snapshot["profile_tag"] == "release-profile"
    assert snapshot["names"] == _expected_bundle_names()
    _assert_seal_hashes_match_binaries()
    return snapshot


def _assert_incremental_not_globally_disabled() -> None:
    cfg = tomllib.loads((APP / ".cargo" / "config.toml").read_text(encoding="utf-8"))
    build_cfg = cfg.get("build")
    if isinstance(build_cfg, dict) and "incremental" in build_cfg:
        assert build_cfg["incremental"] is not False
    env_cfg = cfg.get("env")
    if isinstance(env_cfg, dict) and "CARGO_INCREMENTAL" in env_cfg:
        assert str(env_cfg["CARGO_INCREMENTAL"]) != "0"

    workspace_toml = (APP / "Cargo.toml").read_text(encoding="utf-8").lower()
    assert "incremental = false" not in workspace_toml

    for root in [APP / "stage_graph", APP / "ship_seal", APP / "ci" / "harness"]:
        for script in sorted(root.glob("*.sh")):
            text = script.read_text(encoding="utf-8")
            assert "CARGO_INCREMENTAL=0" not in text
            assert "--config build.incremental=false" not in text
            assert "cargo clean" not in text


def test_baseline_bundle_tracks_release_profile_and_manifest_values() -> None:
    """Baseline packaging must ship the release library and a self-consistent seal."""
    _run(["bash", str(HARNESS / "build_and_load.sh")], check=True)
    snapshot = _assert_release_bundle_coherent()
    assert snapshot["build_note"].startswith("surface-anchor-")


def test_rust_surface_edit_moves_epoch_and_keeps_release_bundle_coherent() -> None:
    """A release-only Rust source edit must move the epoch and the packaged release bytes."""
    _run(["bash", str(HARNESS / "build_and_load.sh")], check=True)
    before = _bundle_snapshot()
    _run(["bash", str(HARNESS / "partial_edit_rust.sh")], check=True)
    after = _assert_release_bundle_coherent()
    assert before["build_note"] != after["build_note"]
    assert before["plugin_hash"] != after["plugin_hash"]
    assert before["epoch"] != after["epoch"]


def test_template_edit_moves_epoch_and_keeps_release_bundle_coherent() -> None:
    """A release-only template edit must move the epoch and the packaged release bytes."""
    _run(["bash", str(HARNESS / "build_and_load.sh")], check=True)
    before = _bundle_snapshot()
    _run(["bash", str(HARNESS / "partial_edit_template.sh")], check=True)
    after = _assert_release_bundle_coherent()
    assert before["build_note"] != after["build_note"]
    assert before["plugin_hash"] != after["plugin_hash"]
    assert before["epoch"] != after["epoch"]


def test_layout_change_moves_epoch_and_drops_removed_native_outputs() -> None:
    """Layout changes must move the epoch and remove stale native outputs from the package."""
    _run(["bash", str(HARNESS / "build_and_load.sh")], check=True)
    before = _bundle_snapshot()
    _run(["bash", str(HARNESS / "remove_plugin.sh")], check=True)
    after = _assert_release_bundle_coherent()
    assert before["epoch"] != after["epoch"]
    assert "liblegacy.so" not in after["names"]
    assert "stale_ghost.so" not in after["names"]
    assert after["names"] == {"libplugin_core.so", "libcpp_bridge.so"}


def test_loader_rejects_debug_binary_swapped_after_packaging() -> None:
    """Swapping a debug binary into the packaged drop must be rejected by the loader."""
    _run(["bash", str(HARNESS / "build_and_load.sh")], check=True)
    seal = _read_seal()
    assert _sha256(DEBUG_SO) != seal["files"]["libplugin_core.so"]
    shutil.copy2(DEBUG_SO, PKG_SO)
    result = _run([str(LOADER), str(PKG_SO), str(SEAL_PATH)], check=False)
    assert result.returncode != 0
    assert "hash mismatch" in result.stderr


def test_sequence_scenarios_stay_coherent_in_isolation(pristine_tree: dict[str, str]) -> None:
    """Every declared harness sequence must end in the same coherent release bundle state."""
    sequences = json.loads((APP / "ci" / "sequences.json").read_text(encoding="utf-8"))["sequences"]
    for sequence in sequences:
        _apply_pristine(pristine_tree)
        for step in sequence["steps"]:
            _run(["bash", STEP_MAP[step]], check=True)
        snapshot = _assert_release_bundle_coherent()
        epoch = snapshot["epoch"]
        assert isinstance(epoch, str) and len(epoch) == 24
        assert epoch == epoch.lower() and all(c in "0123456789abcdef" for c in epoch)


def test_single_subsystem_regressions() -> None:
    """Each known-bad subsystem snapshot must break at least one targeted probe."""
    _run(["bash", str(APP / "ci" / "test_partial_fix_matrix.sh")], check=True)
    snapshot = _assert_release_bundle_coherent()
    assert snapshot["plugin_hash"] == snapshot["release_hash"]


def test_incremental_path_without_clean_and_without_global_disable() -> None:
    """The happy path must succeed without cargo clean and without disabling incremental builds."""
    env = dict(os.environ)
    env["PATH"] = f"/app/ci/fake_bin:{env['PATH']}"
    _run(["bash", str(HARNESS / "build_and_load.sh")], check=True, env=env)
    snapshot = _assert_release_bundle_coherent()
    assert snapshot["plugin_hash"] == snapshot["seal_hash"]
    _assert_incremental_not_globally_disabled()
