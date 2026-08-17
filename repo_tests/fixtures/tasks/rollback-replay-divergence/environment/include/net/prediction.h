#pragma once

#include "engine/types.h"
#include "sim/input_stage.h"

#include <array>

namespace net {

class Predictor {
 public:
  void reset();
  void observe_confirmed(eng::Tick tick, eng::PlayerIndex who, std::int8_t dx);
  [[nodiscard]] std::int8_t predicted_or(eng::Tick tick, eng::PlayerIndex who, std::int8_t staged_dx,
                                           bool remote_slot_present) const;

 private:
  std::array<std::int8_t, eng::kPlayerCount> last_confirmed_{};
};

}  // namespace net
