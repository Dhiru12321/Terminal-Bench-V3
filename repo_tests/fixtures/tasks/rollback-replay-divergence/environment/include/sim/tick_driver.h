#pragma once

#include "game/world.h"
#include "net/prediction.h"
#include "sim/command_log.h"
#include "sim/input_merge.h"
#include "sim/rng_facade.h"
#include "sim/snapshot.h"

namespace sim {

class TickDriver {
 public:
  void reset(std::uint64_t seed);
  void run_tick(eng::Tick tick, const TickInputs& incoming, game::World& world);

  [[nodiscard]] const CommandLog& log() const { return log_; }
  [[nodiscard]] net::Predictor& predictor() { return pred_; }
  [[nodiscard]] const net::Predictor& predictor() const { return pred_; }
  [[nodiscard]] sim::RngFacade& rng() { return rng_; }
  [[nodiscard]] const sim::RngFacade& rng() const { return rng_; }

 private:
  net::Predictor pred_{};
  SnapshotRing snapshots_{};
  CommandLog log_{};
  sim::RngFacade rng_{};
};

}  // namespace sim
