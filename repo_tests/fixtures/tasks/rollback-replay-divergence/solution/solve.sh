#!/usr/bin/env bash
set -euo pipefail

cd /app

# Fix 1 (TB_TIMELINE_MODE): tick_driver.cpp
# - The mode-2 snapshot branch mistakenly calls capture_pre_merge; it must
#   capture post-apply (after fold_entropy) so rollback snapshots reflect
#   the fully-applied world state.
# - The mode-2 apply-delta branch applies player 1 before player 0, which
#   diverges from the canonical order; swap to player 0 then player 1.
python3 - <<'PYEOF'
import pathlib

p = pathlib.Path("/app/src/sim/tick_driver.cpp")
src = p.read_text()

# Fix snapshot capture: replace stub (pre_merge in both branches) with
# mode-1 keeping pre_merge and mode-2 omitting the pre-merge block
# (capture moves to post-apply below).
src = src.replace(
    "#if TB_TIMELINE_MODE == 1\n"
    "  snapshots_.capture_pre_merge(world, tick);\n"
    "#else\n"
    "  snapshots_.capture_pre_merge(world, tick);\n"
    "#endif",
    "#if TB_TIMELINE_MODE == 1\n"
    "  snapshots_.capture_pre_merge(world, tick);\n"
    "#endif",
)

# Fix apply-delta order in mode-2 branch.
src = src.replace(
    "#if TB_TIMELINE_MODE == 1\n"
    "  world.apply_delta(static_cast<eng::PlayerIndex>(1), merged.staged[1].dx, rng_);\n"
    "  world.apply_delta(static_cast<eng::PlayerIndex>(0), merged.staged[0].dx, rng_);\n"
    "#else\n"
    "  world.apply_delta(static_cast<eng::PlayerIndex>(1), merged.staged[1].dx, rng_);\n"
    "  world.apply_delta(static_cast<eng::PlayerIndex>(0), merged.staged[0].dx, rng_);\n"
    "#endif",
    "#if TB_TIMELINE_MODE == 1\n"
    "  world.apply_delta(static_cast<eng::PlayerIndex>(1), merged.staged[1].dx, rng_);\n"
    "  world.apply_delta(static_cast<eng::PlayerIndex>(0), merged.staged[0].dx, rng_);\n"
    "#else\n"
    "  world.apply_delta(static_cast<eng::PlayerIndex>(0), merged.staged[0].dx, rng_);\n"
    "  world.apply_delta(static_cast<eng::PlayerIndex>(1), merged.staged[1].dx, rng_);\n"
    "#endif",
)

# Add post-apply snapshot capture for mode-2 after fold_entropy.
src = src.replace(
    "  world.fold_entropy(rng_);\n\n  LoggedTick",
    "  world.fold_entropy(rng_);\n\n"
    "#if TB_TIMELINE_MODE == 2\n"
    "  snapshots_.capture_post_apply(world, tick);\n"
    "#endif\n\n"
    "  LoggedTick",
)

p.write_text(src)
PYEOF

# Fix 2 (TB_REEXEC_MODE): session.cpp
# - The mode-2 catch_up_from_queue branch spuriously draws two RNG values
#   before each replayed tick; these draws must be removed so the RNG
#   sequence during catch-up matches a live run.
python3 - <<'PYEOF'
import pathlib

p = pathlib.Path("/app/src/net/session.cpp")
src = p.read_text()

src = src.replace(
    "#if TB_REEXEC_MODE == 1\n"
    "    (void)driver.rng().world.draw_u32();\n"
    "    (void)driver.rng().net.draw_u32();\n"
    "#else\n"
    "    (void)driver.rng().world.draw_u32();\n"
    "    (void)driver.rng().net.draw_u32();\n"
    "#endif",
    "#if TB_REEXEC_MODE == 1\n"
    "    (void)driver.rng().world.draw_u32();\n"
    "    (void)driver.rng().net.draw_u32();\n"
    "#endif",
)

p.write_text(src)
PYEOF

# Fix 3 (TB_REEXEC_MODE): decoder.cpp
# - The mode-2 rows_to_inputs branch ignores the presence mask by always
#   setting remote_slot_present to true and zeroing absent-player dx via
#   a ternary; the correct behaviour passes the mask bits through directly
#   and unconditionally forwards the stored dx values.
python3 - <<'PYEOF'
import pathlib

p = pathlib.Path("/app/src/replay/decoder.cpp")
src = p.read_text()

src = src.replace(
    "#if TB_REEXEC_MODE == 1\n"
    "    tin.remote_slot_present[0] = true;\n"
    "    tin.remote_slot_present[1] = true;\n"
    "    tin.staged[0].dx = have0 ? r.p0 : static_cast<std::int8_t>(0);\n"
    "    tin.staged[1].dx = have1 ? r.p1 : static_cast<std::int8_t>(0);\n"
    "#else\n"
    "    tin.remote_slot_present[0] = true;\n"
    "    tin.remote_slot_present[1] = true;\n"
    "    tin.staged[0].dx = have0 ? r.p0 : static_cast<std::int8_t>(0);\n"
    "    tin.staged[1].dx = have1 ? r.p1 : static_cast<std::int8_t>(0);\n"
    "#endif",
    "#if TB_REEXEC_MODE == 1\n"
    "    tin.remote_slot_present[0] = true;\n"
    "    tin.remote_slot_present[1] = true;\n"
    "    tin.staged[0].dx = have0 ? r.p0 : static_cast<std::int8_t>(0);\n"
    "    tin.staged[1].dx = have1 ? r.p1 : static_cast<std::int8_t>(0);\n"
    "#else\n"
    "    tin.remote_slot_present[0] = have0;\n"
    "    tin.remote_slot_present[1] = have1;\n"
    "    tin.staged[0].dx = r.p0;\n"
    "    tin.staged[1].dx = r.p1;\n"
    "#endif",
)

p.write_text(src)
PYEOF

cmake -S /app -B /app/build -DCMAKE_BUILD_TYPE=Release \
  -DTB_TIMELINE_MODE=2 -DTB_REEXEC_MODE=2

cmake --build /app/build -j2

mkdir -p /app/bin
install -m 0755 /app/build/netplay_matrix /app/bin/netplay_matrix

mkdir -p /app/output
/app/bin/netplay_matrix --out /app/output --pack /app/data/seed_scenarios.json
