#pragma once

#include "net/prediction.h"
#include "sim/input_stage.h"

namespace sim {

struct InputMerge {
  static TickInputs reconcile(eng::Tick tick, const TickInputs& staged, net::Predictor& pred);
};

}  // namespace sim
