#include "sim/input_merge.h"

namespace sim {

TickInputs InputMerge::reconcile(eng::Tick tick, const TickInputs& staged, net::Predictor& pred) {
  TickInputs out = staged;
  for (int i = 0; i < eng::kPlayerCount; ++i) {
    const auto who = static_cast<eng::PlayerIndex>(i);
    const bool present = staged.remote_slot_present[i];
    const std::int8_t base = staged.staged[i].dx;
    out.staged[i].dx = pred.predicted_or(tick, who, base, present);
    if (present) {
      pred.observe_confirmed(tick, who, staged.staged[i].dx);
    }
  }
  return out;
}

}  // namespace sim
