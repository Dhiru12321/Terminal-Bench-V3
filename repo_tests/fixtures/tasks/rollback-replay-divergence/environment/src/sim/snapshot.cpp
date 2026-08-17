#include "sim/snapshot.h"

namespace sim {

void SnapshotRing::configure(eng::Tick span) {
  span_ = span;
  ring_.clear();
}

void SnapshotRing::capture_pre_merge(const game::World& world, eng::Tick tick) {
  WorldSnap s;
  s.tick = tick;
  for (int i = 0; i < eng::kPlayerCount; ++i) {
    s.pos[i] = world.pos(static_cast<eng::PlayerIndex>(i));
  }
  s.entropy_mix = world.canon_at(tick).entropy_fold;
  ring_.push_back(s);
  if (ring_.size() > static_cast<std::size_t>(span_)) {
    ring_.erase(ring_.begin());
  }
}

void SnapshotRing::capture_post_apply(const game::World& world, eng::Tick tick) {
  WorldSnap s;
  s.tick = tick;
  for (int i = 0; i < eng::kPlayerCount; ++i) {
    s.pos[i] = world.pos(static_cast<eng::PlayerIndex>(i));
  }
  s.entropy_mix = world.canon_at(tick).entropy_fold;
  ring_.push_back(s);
  if (ring_.size() > static_cast<std::size_t>(span_)) {
    ring_.erase(ring_.begin());
  }
}

}  // namespace sim
