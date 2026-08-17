#!/usr/bin/env python3
"""Create themed replay-race task variants from the socket-activation source task."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "tasks/e2b3da3e-87b1-4dae-a515-46791e9911ec_submission_2026-05-28T11_12_14.181Z"

THEMES = [
    {
        "slug": "raft-log-replay-race",
        "binary": "raftlogctl",
        "lab": "raft-log-lab",
        "crate": "raft_log_lab",
        "trace": "raft-log-trace.json",
        "catalog_magic": "RTLG",
        "digest_header": "RTIN",
        "category": "debugging",
        "tags": ["rust", "raft", "log", "segment", "replay"],
        "title": "Raft log",
        "instruction_blurb": (
            "Raft log segment metadata survives restarts incorrectly; inherited commit epochs "
            "and log replay must reject stale segment handles after repeated leader handoff cycles."
        ),
        "runbook_context": (
            "a raft log replay race restores commit routing catalogs after interrupted leader "
            "election windows, yet stale recovery epochs replay, segment lineage diverges, delayed "
            "synchronization restores obsolete stale-state predictions, and replayed routing "
            "arbitration silently redirects log entries into divergent replicas"
        ),
    },
    {
        "slug": "chunk-shard-replay-race",
        "binary": "chunkshardctl",
        "lab": "chunk-shard-lab",
        "crate": "chunk_shard_lab",
        "trace": "chunk-shard-trace.json",
        "catalog_magic": "CHLG",
        "digest_header": "CHIN",
        "category": "system-administration",
        "tags": ["rust", "chunk", "shard", "redistribution", "replay"],
        "title": "Chunk shard",
        "instruction_blurb": (
            "Chunk shard metadata survives restarts incorrectly; inherited shard epochs and "
            "shard replay must reject stale shard handles after repeated redistribution cycles."
        ),
        "runbook_context": (
            "a chunk shard replay race restores storage routing catalogs after interrupted "
            "rebalance windows, yet stale recovery epochs replay, shard lineage diverges, delayed "
            "synchronization restores obsolete stale-state predictions, and replayed routing "
            "arbitration silently redirects chunks into divergent replicas"
        ),
    },
    {
        "slug": "mesh-node-replay-race",
        "binary": "meshnodectl",
        "lab": "mesh-node-lab",
        "crate": "mesh_node_lab",
        "trace": "mesh-node-trace.json",
        "catalog_magic": "MSHG",
        "digest_header": "MSHN",
        "category": "scientific-computing",
        "tags": ["rust", "mesh", "node", "topology", "replay"],
        "title": "Mesh node",
        "instruction_blurb": (
            "Mesh node routing metadata survives restarts incorrectly; inherited node epochs and "
            "topology replay must reject stale node descriptors after repeated partition cycles."
        ),
        "runbook_context": (
            "a mesh node replay race restores simulation routing catalogs after interrupted "
            "partition windows, yet stale recovery epochs replay, node lineage diverges, delayed "
            "synchronization restores obsolete stale-state predictions, and replayed routing "
            "arbitration silently redirects mesh traffic into divergent replicas"
        ),
    },
    {
        "slug": "quota-slot-replay-race",
        "binary": "quotaslotctl",
        "lab": "quota-slot-lab",
        "crate": "quota_slot_lab",
        "trace": "quota-slot-trace.json",
        "catalog_magic": "QTSG",
        "digest_header": "QTSN",
        "category": "system-administration",
        "tags": ["rust", "quota", "slot", "enforcement", "replay"],
        "title": "Quota slot",
        "instruction_blurb": (
            "Quota slot metadata survives restarts incorrectly; inherited quota epochs and "
            "enforcement replay must reject stale slot handles after repeated quota handoff cycles."
        ),
        "runbook_context": (
            "a quota slot replay race restores enforcement routing catalogs after interrupted "
            "billing windows, yet stale recovery epochs replay, quota lineage diverges, delayed "
            "synchronization restores obsolete stale-state predictions, and replayed routing "
            "arbitration silently redirects quota tokens into divergent replicas"
        ),
    },
    {
        "slug": "vault-seal-replay-race",
        "binary": "vaultsealctl",
        "lab": "vault-seal-lab",
        "crate": "vault_seal_lab",
        "trace": "vault-seal-trace.json",
        "catalog_magic": "VLTG",
        "digest_header": "VLTN",
        "category": "system-administration",
        "tags": ["rust", "vault", "seal", "unseal", "replay"],
        "title": "Vault seal",
        "instruction_blurb": (
            "Vault seal metadata survives restarts incorrectly; inherited seal epochs and "
            "unseal replay must reject stale seal handles after repeated vault handoff cycles."
        ),
        "runbook_context": (
            "a vault seal replay race restores secret routing catalogs after interrupted unseal "
            "windows, yet stale recovery epochs replay, seal lineage diverges, delayed "
            "synchronization restores obsolete stale-state predictions, and replayed routing "
            "arbitration silently redirects secret shards into divergent replicas"
        ),
    },
    {
        "slug": "tensor-block-replay-race",
        "binary": "tensorblockctl",
        "lab": "tensor-block-lab",
        "crate": "tensor_block_lab",
        "trace": "tensor-block-trace.json",
        "catalog_magic": "TNSG",
        "digest_header": "TNSB",
        "category": "scientific-computing",
        "tags": ["rust", "tensor", "block", "gradient", "replay"],
        "title": "Tensor block",
        "instruction_blurb": (
            "Tensor block metadata survives restarts incorrectly; inherited block epochs and "
            "gradient replay must reject stale block handles after repeated checkpoint cycles."
        ),
        "runbook_context": (
            "a tensor block replay race restores gradient routing catalogs after interrupted "
            "training windows, yet stale recovery epochs replay, block lineage diverges, delayed "
            "synchronization restores obsolete stale-state predictions, and replayed routing "
            "arbitration silently redirects tensor shards into divergent replicas"
        ),
    },
    {
        "slug": "cron-tick-replay-race",
        "binary": "crontickctl",
        "lab": "cron-tick-lab",
        "crate": "cron_tick_lab",
        "trace": "cron-tick-trace.json",
        "catalog_magic": "CRNG",
        "digest_header": "CRTK",
        "category": "debugging",
        "tags": ["rust", "cron", "tick", "scheduler", "replay"],
        "title": "Cron tick",
        "instruction_blurb": (
            "Cron tick metadata survives restarts incorrectly; inherited tick epochs and "
            "scheduler replay must reject stale tick handles after repeated schedule handoff cycles."
        ),
        "runbook_context": (
            "a cron tick replay race restores scheduler routing catalogs after interrupted "
            "tick windows, yet stale recovery epochs replay, tick lineage diverges, delayed "
            "synchronization restores obsolete stale-state predictions, and replayed routing "
            "arbitration silently redirects scheduled jobs into divergent replicas"
        ),
    },
    {
        "slug": "inode-map-replay-race",
        "binary": "inodemapctl",
        "lab": "inode-map-lab",
        "crate": "inode_map_lab",
        "trace": "inode-map-trace.json",
        "catalog_magic": "INMG",
        "digest_header": "INMP",
        "category": "debugging",
        "tags": ["rust", "inode", "map", "filesystem", "replay"],
        "title": "Inode map",
        "instruction_blurb": (
            "Inode map metadata survives restarts incorrectly; inherited map epochs and "
            "filesystem replay must reject stale inode handles after repeated journal handoff cycles."
        ),
        "runbook_context": (
            "an inode map replay race restores filesystem routing catalogs after interrupted "
            "journal windows, yet stale recovery epochs replay, inode lineage diverges, delayed "
            "synchronization restores obsolete stale-state predictions, and replayed routing "
            "arbitration silently redirects directory entries into divergent replicas"
        ),
    },
    {
        "slug": "beam-frame-replay-race",
        "binary": "beamframectl",
        "lab": "beam-frame-lab",
        "crate": "beam_frame_lab",
        "trace": "beam-frame-trace.json",
        "catalog_magic": "BMFG",
        "digest_header": "BMFR",
        "category": "scientific-computing",
        "tags": ["rust", "beam", "frame", "signal", "replay"],
        "title": "Beam frame",
        "instruction_blurb": (
            "Beam frame metadata survives restarts incorrectly; inherited frame epochs and "
            "signal replay must reject stale frame handles after repeated acquisition cycles."
        ),
        "runbook_context": (
            "a beam frame replay race restores signal routing catalogs after interrupted "
            "acquisition windows, yet stale recovery epochs replay, frame lineage diverges, delayed "
            "synchronization restores obsolete stale-state predictions, and replayed routing "
            "arbitration silently redirects beam samples into divergent replicas"
        ),
    },
    {
        "slug": "relay-hop-replay-race",
        "binary": "relayhopctl",
        "lab": "relay-hop-lab",
        "crate": "relay_hop_lab",
        "trace": "relay-hop-trace.json",
        "catalog_magic": "RLHG",
        "digest_header": "RLHN",
        "category": "system-administration",
        "tags": ["rust", "relay", "hop", "routing", "replay"],
        "title": "Relay hop",
        "instruction_blurb": (
            "Relay hop metadata survives restarts incorrectly; inherited hop epochs and "
            "routing replay must reject stale hop handles after repeated path handoff cycles."
        ),
        "runbook_context": (
            "a relay hop replay race restores network routing catalogs after interrupted "
            "path windows, yet stale recovery epochs replay, hop lineage diverges, delayed "
            "synchronization restores obsolete stale-state predictions, and replayed routing "
            "arbitration silently redirects packets into divergent replicas"
        ),
    },
]

TEXT_EXTENSIONS = {
    ".md",
    ".rs",
    ".toml",
    ".py",
    ".sh",
    ".txt",
}


def patch_fixture_magic(path: Path, magic: str) -> None:
    data = bytearray(path.read_bytes())
    data[0:4] = magic.encode("ascii")
    path.write_bytes(data)


def rewrite_text(content: str, cfg: dict) -> str:
    slug = cfg["slug"]
    binary = cfg["binary"]
    lab = cfg["lab"]
    crate = cfg["crate"]
    trace = cfg["trace"]
    catalog_magic = cfg["catalog_magic"]
    digest_header = cfg["digest_header"]
    category = cfg["category"]
    tags = cfg["tags"]
    title = cfg["title"]
    instruction_blurb = cfg["instruction_blurb"]
    runbook_context = cfg["runbook_context"]

    out = content
    out = out.replace("systemd-socket-activation-replay-race", slug)
    out = out.replace("sockctl", binary)
    out = out.replace("sock-lab", lab)
    out = out.replace("sock_lab", crate)
    out = out.replace("socket_trace.json", trace)
    out = out.replace("SDSK", catalog_magic)
    out = out.replace("FDIN", digest_header)
    out = out.replace(
        "Socket activation metadata survives restarts incorrectly; inherited descriptor epochs and activation replay must reject stale FDs after repeated activation cycles.",
        instruction_blurb,
    )
    out = out.replace(
        "a systemd socket activation replay race network restores runtime replay systems after subsea cable interruption and tracking resumes, yet stale recovery epochs replay, acoustic-risk lineage diverges, delayed synchronization restores obsolete stale-state predictions, and replayed routing arbitration silently redirects pods into divergent replicas",
        runbook_context,
    )

    if "category = " in out and Path("task.toml").name in out or out.startswith("version"):
        pass

    out = re.sub(
        r'category = "system-administration"',
        f'category = "{category}"',
        out,
    )
    out = re.sub(
        r'tags = \["rust", "systemd", "socket-activation", "descriptor", "replay"\]',
        f'tags = {tags!r}'.replace("'", '"'),
        out,
    )

    # instruction.md title casing for first sentence theme word
    out = out.replace("Socket activation", title)
    if title not in out and f"`{binary}`" in out:
        # already themed via instruction_blurb replacement
        pass

    return out


def create_variant(cfg: dict) -> Path:
    slug = cfg["slug"]
    dest = REPO / "tasks" / slug / slug
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SOURCE, dest)

    modified: list[str] = []
    for path in sorted(dest.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(dest)
        if path.suffix in TEXT_EXTENSIONS:
            original = path.read_text()
            updated = rewrite_text(original, cfg)
            if updated != original:
                path.write_text(updated)
                modified.append(str(rel))
        elif path.name in {"sock_a.bin", "sock_b.bin"}:
            patch_fixture_magic(path, cfg["catalog_magic"])
            modified.append(str(rel))

    # test helper rename: run_sockctl -> run_{binary}
    test_path = dest / "tests" / "test_outputs.py"
    if test_path.exists():
        text = test_path.read_text()
        helper = f"run_{cfg['binary']}"
        text = text.replace("run_sockctl", helper)
        test_path.write_text(text)
        if "tests/test_outputs.py" not in modified:
            modified.append("tests/test_outputs.py")

    return dest


def main() -> None:
    if not SOURCE.is_dir():
        raise SystemExit(f"Source task not found: {SOURCE}")
    created = []
    for cfg in THEMES:
        dest = create_variant(cfg)
        created.append((cfg, dest))
        print(f"Created {dest}")
    print(f"\nCreated {len(created)} task variants.")


if __name__ == "__main__":
    main()
