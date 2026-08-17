#pragma once

#include <algorithm>
#include <cstdint>

namespace eng {

inline std::int32_t clamp_axis(std::int32_t v, std::int32_t lo, std::int32_t hi) {
  return std::max(lo, std::min(hi, v));
}

}  // namespace eng
