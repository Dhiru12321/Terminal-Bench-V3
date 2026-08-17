#pragma once

#include "engine/types.h"
#include "game/world.h"

#include <vector>

namespace sim {

struct WorldSnap {
  eng::Tick tick = 0;
  std::array<std::int32_t, eng::kPlayerCount> pos{};
  std::uint64_t entropy_mix = 0;
};

class SnapshotRing {
 public:
  void configure(eng::Tick span);
  void capture_pre_merge(const game::World& world, eng::Tick tick);
  void capture_post_apply(const game::World& world, eng::Tick tick);
  [[nodiscard]] bool empty() const { return ring_.empty(); }
  [[nodiscard]] const WorldSnap& latest() const { return ring_.back(); }

 private:
  std::vector<WorldSnap> ring_{};
  eng::Tick span_ = eng::kRollbackSpan;
};

}  // namespace sim
