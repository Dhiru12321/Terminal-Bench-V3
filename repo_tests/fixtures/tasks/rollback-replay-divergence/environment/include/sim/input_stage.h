#pragma once

#include "engine/types.h"

#include <array>

namespace sim {

struct PlayerInput {
  std::int8_t dx = 0;
};

struct TickInputs {
  eng::Tick tick = 0;
  std::array<PlayerInput, eng::kPlayerCount> staged{};
  bool remote_slot_present[eng::kPlayerCount] = {true, true};
};

}  // namespace sim
