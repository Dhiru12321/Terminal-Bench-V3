#include "net/prediction.h"

namespace net {

void Predictor::reset() {
  last_confirmed_.fill(0);
}

void Predictor::observe_confirmed(eng::Tick, eng::PlayerIndex who, std::int8_t dx) {
  last_confirmed_[static_cast<int>(who)] = dx;
}

std::int8_t Predictor::predicted_or(eng::Tick, eng::PlayerIndex who, std::int8_t staged_dx,
                                    bool remote_slot_present) const {
  const int idx = static_cast<int>(who);
  if (remote_slot_present) {
    return staged_dx;
  }
  return last_confirmed_[idx];
}

}  // namespace net
