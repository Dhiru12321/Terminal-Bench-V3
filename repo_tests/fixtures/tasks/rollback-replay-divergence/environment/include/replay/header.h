#pragma once

#include <cstdint>

namespace replay {

struct ContainerHeader {
  std::uint32_t magic = 0x524C4244;  // RLBD
  std::uint32_t format_revision = 2;
  std::uint64_t seed = 0;
  std::uint32_t tick_span = 0;
  std::uint32_t flags = 0;
};

}  // namespace replay
