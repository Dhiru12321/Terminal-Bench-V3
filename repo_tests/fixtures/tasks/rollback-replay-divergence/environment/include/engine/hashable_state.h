#pragma once

#include "engine/types.h"

#include <array>
#include <cstdint>
#include <string>

namespace eng {

struct CanonicalProjection {
  Tick tick = 0;
  std::array<std::int32_t, kPlayerCount> pos{};
  std::uint64_t entropy_fold = 0;

  [[nodiscard]] std::string pack_line() const {
    std::string s;
    s.reserve(96);
    s += std::to_string(static_cast<int>(tick));
    s.push_back('|');
    s += std::to_string(pos[0]);
    s.push_back('|');
    s += std::to_string(pos[1]);
    s.push_back('|');
    s += std::to_string(static_cast<unsigned long long>(entropy_fold));
    return s;
  }
};

}  // namespace eng
