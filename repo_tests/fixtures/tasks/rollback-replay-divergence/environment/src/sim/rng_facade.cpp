#include "sim/rng_facade.h"

namespace sim {

static std::uint64_t splitmix64(std::uint64_t& state) {
  std::uint64_t z = (state += 0x9E3779B97F4A7C15ULL);
  z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
  z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
  return z ^ (z >> 31);
}

void RngStream::reset(std::uint64_t seed) {
  state_ = seed == 0 ? 0xD1CEULL : seed;
  draws_ = 0;
}

std::uint32_t RngStream::draw_u32() {
  ++draws_;
  return static_cast<std::uint32_t>(splitmix64(state_) & 0xFFFFFFFFu);
}

void RngFacade::seed_all(std::uint64_t base_seed) {
  world.reset(base_seed * 0xC6A4A7935BD1E995ULL + 1);
  net.reset(base_seed * 0xD6E8FEB866B1B965ULL + 3);
}

}  // namespace sim
