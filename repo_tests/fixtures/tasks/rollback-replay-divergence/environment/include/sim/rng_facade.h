#pragma once

#include <cstdint>

namespace sim {

class RngStream {
 public:
  void reset(std::uint64_t seed);
  [[nodiscard]] std::uint32_t draw_u32();
  [[nodiscard]] std::uint64_t total_draws() const { return draws_; }

 private:
  std::uint64_t state_ = 0;
  std::uint64_t draws_ = 0;
};

struct RngFacade {
  RngStream world;
  RngStream net;

  void seed_all(std::uint64_t base_seed);
};

}  // namespace sim
