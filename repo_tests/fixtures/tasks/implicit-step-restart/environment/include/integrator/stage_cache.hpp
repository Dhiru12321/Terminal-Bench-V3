#pragma once

#include <array>

struct StageCache {
  std::array<double, 3> k1{};
  std::array<double, 3> k2{};
  int current_stage{0};
  void reset_stage();
};
