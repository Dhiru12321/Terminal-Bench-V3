#pragma once

#include "engine/hashable_state.h"
#include "engine/types.h"
#include "sim/rng_facade.h"

#include <array>

namespace game {

class World {
 public:
  void reset();
  void apply_delta(eng::PlayerIndex who, std::int8_t dx, sim::RngFacade& rng);
  void fold_entropy(sim::RngFacade& rng);

  [[nodiscard]] eng::CanonicalProjection canon_at(eng::Tick tick) const;

  [[nodiscard]] std::int32_t pos(eng::PlayerIndex p) const { return pos_[static_cast<int>(p)]; }

 private:
  std::array<std::int32_t, eng::kPlayerCount> pos_{};
  std::uint64_t entropy_mix_ = 0;
};

}  // namespace game
