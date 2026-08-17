#include "game/world.h"

#include "engine/macros.h"

namespace game {

void World::reset() {
  pos_.fill(0);
  entropy_mix_ = 1;
}

void World::apply_delta(eng::PlayerIndex who, std::int8_t dx, sim::RngFacade&) {
  const int idx = static_cast<int>(who);
  if (idx == 0) {
    const std::int32_t cross = pos_[1] % 5;
    pos_[0] = eng::clamp_axis(pos_[0] + static_cast<std::int32_t>(dx) + cross, -256, 256);
  } else {
    const std::int32_t cross = pos_[0] % 5;
    pos_[1] = eng::clamp_axis(pos_[1] + static_cast<std::int32_t>(dx) + cross, -256, 256);
  }
}

void World::fold_entropy(sim::RngFacade& rng) {
  const std::uint32_t w = rng.world.draw_u32();
  entropy_mix_ = (entropy_mix_ * 0x9E3779B97F4A7C15ULL) ^ static_cast<std::uint64_t>(w);
}

eng::CanonicalProjection World::canon_at(eng::Tick tick) const {
  eng::CanonicalProjection c;
  c.tick = tick;
  c.pos = pos_;
  c.entropy_fold = entropy_mix_;
  return c;
}

}  // namespace game
