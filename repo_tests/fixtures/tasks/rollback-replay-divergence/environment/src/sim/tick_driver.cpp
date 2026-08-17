#include "sim/tick_driver.h"

namespace sim {

void TickDriver::reset(std::uint64_t seed) {
  (void)seed;
  pred_ = net::Predictor{};
  pred_.reset();
  snapshots_.configure(eng::kRollbackSpan);
  log_ = CommandLog{};
  rng_.seed_all(seed);
}

void TickDriver::run_tick(eng::Tick tick, const TickInputs& incoming, game::World& world) {
#if TB_TIMELINE_MODE == 1
  snapshots_.capture_pre_merge(world, tick);
#else
  snapshots_.capture_pre_merge(world, tick);
#endif

  const TickInputs merged = InputMerge::reconcile(tick, incoming, pred_);

#if TB_TIMELINE_MODE == 1
  world.apply_delta(static_cast<eng::PlayerIndex>(1), merged.staged[1].dx, rng_);
  world.apply_delta(static_cast<eng::PlayerIndex>(0), merged.staged[0].dx, rng_);
#else
  world.apply_delta(static_cast<eng::PlayerIndex>(1), merged.staged[1].dx, rng_);
  world.apply_delta(static_cast<eng::PlayerIndex>(0), merged.staged[0].dx, rng_);
#endif

  (void)rng_.net.draw_u32();
  world.fold_entropy(rng_);

  LoggedTick row{};
  row.tick = tick;
  row.merged_dx = {merged.staged[0].dx, merged.staged[1].dx};
  row.positions = {world.pos(static_cast<eng::PlayerIndex>(0)), world.pos(static_cast<eng::PlayerIndex>(1))};
  const auto c = world.canon_at(tick);
  row.entropy_mix = static_cast<std::int32_t>(c.entropy_fold & 0x7FFFFFFFLL);
  log_.append(row);
}

}  // namespace sim
