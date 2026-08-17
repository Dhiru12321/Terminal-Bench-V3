#pragma once

#include "engine/hashable_state.h"
#include "engine/types.h"
#include "sim/input_stage.h"

#include <string>
#include <vector>

namespace sim {

struct LoggedTick {
  eng::Tick tick = 0;
  std::array<std::int8_t, eng::kPlayerCount> merged_dx{};
  std::array<std::int32_t, eng::kPlayerCount> positions{};
  std::int32_t entropy_mix = 0;
};

class CommandLog {
 public:
  void append(const LoggedTick& row);
  [[nodiscard]] const std::vector<LoggedTick>& rows() const { return rows_; }
  [[nodiscard]] std::string tail_projection(std::size_t last_n) const;

 private:
  std::vector<LoggedTick> rows_{};
};

}  // namespace sim
