#pragma once

#include "engine/types.h"
#include "game/world.h"
#include "sim/tick_driver.h"

#include <cstdint>
#include <vector>

namespace net {

struct FramedTick {
  eng::Tick tick = 0;
  std::int8_t p0 = 0;
  std::int8_t p1 = 0;
  std::uint8_t presence = 3;
};

class Session {
 public:
  void reset(std::uint64_t seed);
  void push_remote_frame(const FramedTick& frame);
  void catch_up_from_queue(eng::Tick through, sim::TickDriver& driver, game::World& world);

  [[nodiscard]] std::uint64_t seed() const { return seed_; }

 private:
  std::uint64_t seed_ = 0;
  std::vector<FramedTick> catch_queue_{};
};

}  // namespace net
