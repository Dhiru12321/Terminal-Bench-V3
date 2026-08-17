#pragma once

#include <cstdint>

namespace eng {

using Tick = std::int32_t;
using PlayerIndex = std::int8_t;

constexpr int kPlayerCount = 2;
constexpr Tick kRollbackSpan = 6;

}  // namespace eng
