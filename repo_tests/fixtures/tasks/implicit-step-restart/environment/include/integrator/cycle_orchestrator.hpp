#pragma once

#include <array>
#include <string>

#include "control/error_controller.hpp"
#include "events/localization.hpp"
#include "harness/app_config.hpp"
#include "harness/interrupt_schedule.hpp"
#include "integrator/butcher.hpp"
#include "integrator/stage_cache.hpp"
#include "nonlinear/embedded_driver.hpp"
#include "persistence/reader.hpp"
#include "persistence/writer.hpp"

struct ScheduleResult {
  bool ok{false};
  double final_time{};
  std::array<double, 3> final_y{};
  int accepted_steps{0};
  int rejected_steps{0};
  int newton_iterations{0};
  double event_time{0.0};
  bool had_event{false};
};

struct GoldenRecorder {
  bool on{false};
  std::string* out{nullptr};
};

class CycleOrchestrator {
 public:
  void configure(const AppConfig& cfg, const butcher::Tableau& tab);

  void set_schedule(ScheduleId sid) { schedule_ = sid; }

  void set_hooks_enabled(bool on) { hooks_enabled_ = on; }

  void set_golden(GoldenRecorder g) { golden_ = g; }

  [[nodiscard]] ScheduleId schedule() const { return schedule_; }

  [[nodiscard]] bool schedule_hooks() const { return hooks_enabled_; }

  ScheduleResult run_with_interrupt(const std::string& bundle_path, BundleWriter& writer,
                                    BundleReader& reader);

  ScheduleResult run_uninterrupted();

 private:
  static void fill_bundle(BundlePayload& snap, double t_anchor, const std::array<double, 3>& y_anchor,
                          double h_work, int acc, int rej, int stage_idx,
                          const std::array<double, 3>& k1, const std::array<double, 3>& k2,
                          const NewtonPersist& np, const ErrorController& ec, const EventState& evst);

  AppConfig cfg_{};
  butcher::Tableau tab_{};
  ScheduleId schedule_{ScheduleId::A};
  GoldenRecorder golden_{};
  bool hooks_enabled_{true};

  void emit_step_line(double t, const std::array<double, 3>& y, bool accepted);
};
