#pragma once

#include <array>

struct EventState {
  bool active{false};
  double t_lo{};
  double t_hi{};
  double g_lo{};
  double g_hi{};
  std::array<double, 3> y_lo{};
  std::array<double, 3> y_hi{};
  bool locked{false};
  double event_time{};
  int shrink_pass{0};
};

class EventLocalization {
 public:
  void configure(int component, double target) {
    component_ = component;
    target_ = target;
  }

  double g_value(double t, const std::array<double, 3>& y) const;

  void begin_bracket(double t0, const std::array<double, 3>& y0, double t1,
                     const std::array<double, 3>& y1, EventState& st);

  void shrink(double t_mid, const std::array<double, 3>& y_mid, EventState& st);

  bool converged(const EventState& st, double tol) const {
    return st.locked && (st.t_hi - st.t_lo) < tol;
  }

 private:
  int component_{0};
  double target_{0.0};
};
