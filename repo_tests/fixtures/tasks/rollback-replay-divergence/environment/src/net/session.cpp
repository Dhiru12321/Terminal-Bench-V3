#include "net/session.h"

#include "sim/input_stage.h"

namespace net {

void Session::reset(std::uint64_t seed) {
  seed_ = seed;
  catch_queue_.clear();
}

void Session::push_remote_frame(const FramedTick& frame) {
  catch_queue_.push_back(frame);
}

void Session::catch_up_from_queue(eng::Tick through, sim::TickDriver& driver, game::World& world) {
  for (const auto& ft : catch_queue_) {
    if (ft.tick > through) {
      break;
    }
    sim::TickInputs tin{};
    tin.tick = ft.tick;
    tin.staged[0].dx = ft.p0;
    tin.staged[1].dx = ft.p1;
    tin.remote_slot_present[0] = (ft.presence & 1u) != 0;
    tin.remote_slot_present[1] = (ft.presence & 2u) != 0;

#if TB_REEXEC_MODE == 1
    (void)driver.rng().world.draw_u32();
    (void)driver.rng().net.draw_u32();
#else
    (void)driver.rng().world.draw_u32();
    (void)driver.rng().net.draw_u32();
#endif
    driver.run_tick(ft.tick, tin, world);
  }
}

}  // namespace net
